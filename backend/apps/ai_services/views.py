import re
import logging
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import AIConversation, AIMessage
from .serializers import (
    AIConversationSerializer,
    AIMessageSerializer,
    AskAIQuestionInputSerializer,
)
from .rag_retriever import RAGRetriever
from .prompts import ASK_AI_SYSTEM_PROMPT
from .openai_service import OpenAIService

logger = logging.getLogger('medivault.ai')

class AskAIView(APIView):
    """
    Conversational Grounded RAG Assistant.
    Answers patient questions strictly referencing their uploaded clinical documents.
    Enforces zero-diagnosis and zero-dosage-change safety guardrails.
    """
    permission_classes = [permissions.IsAuthenticated]

    # Regex patterns for unsafe diagnostic / prescription inquiries
    UNSAFE_DIAGNOSIS_PATTERNS = [
        r'(?:কি|কী|কোন)\s*ওষুধ.*(?:খাব|খাওয়া|খাওয়া|উচিত)',
        r'(?:রোগ\s*নির্ণয়|আমার\s*কী\s*হয়েছে|আমার\s*কি\s*হয়েছে|ওষুধ\s*প্রেসক্রাইব)',
        r'(what\s+medicine\s+should\s+i|what\s+drug\s+should|prescribe\s+me|diagnose\s+me)',
        r'(change\s+my\s+dose|double\s+the\s+dose)',
    ]

    def is_unsafe_medical_request(self, text: str) -> bool:
        lowered = text.lower()
        for pat in self.UNSAFE_DIAGNOSIS_PATTERNS:
            if re.search(pat, lowered):
                return True
        return False

    def post(self, request):
        user = request.user
        if not hasattr(user, 'patient_profile'):
            return Response({"error": "Only registered patients can use Ask AI."}, status=status.HTTP_403_FORBIDDEN)

        serializer = AskAIQuestionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        question = data['question'].strip()
        conv_id = data.get('conversation_id')

        # Dynamically detect user's language from question to always match user's language
        has_bengali_script = bool(re.search(r'[\u0980-\u09ff]', question))
        request_lang = request.data.get('language')

        if has_bengali_script:
            lang = 'bn'
        elif request_lang in ['en', 'bn']:
            lang = request_lang
        else:
            banglish_words = {
                'amar', 'amr', 'kemon', 'achen', 'apni', 'tumi', 'osudh', 'khabo', 'korbo',
                'ki', 'kintu', 'bhalo', 'valo', 'kore', 'hoy', 'hoyeche', 'lagbe', 'bolun',
                'koto', 'keno', 'ekhon', 'shomossha', 'matha', 'betha', 'pani', 'khawa'
            }
            tokens = set(re.findall(r'[a-zA-Z]+', question.lower()))
            if len(tokens & banglish_words) >= 2 or any(w in tokens for w in ['kemon', 'achen', 'amr', 'osudh', 'khabo']):
                lang = 'banglish'
            else:
                lang = 'en'

        patient = user.patient_profile

        # Get or create conversation thread
        if conv_id:
            try:
                conversation = AIConversation.objects.get(id=conv_id, patient=patient)
            except AIConversation.DoesNotExist:
                return Response({"error": "Conversation not found or access denied."}, status=status.HTTP_404_NOT_FOUND)
        else:
            first_words = " ".join(question.split()[:5])
            conversation = AIConversation.objects.create(
                patient=patient,
                title=f"{first_words}..." if len(first_words) < len(question) else question,
                language='bn' if lang in ['bn', 'banglish'] else 'en'
            )

        # 1. Check for unsafe medical prescription / diagnosis request
        if self.is_unsafe_medical_request(question):
            logger.info("Medical safety refusal triggered for user question: %s", question)
            is_english = (lang == 'en')
            refusal_text = (
                "I am your MediVault health companion and personal assistant, not a doctor. 😊\n\n"
                "For your safety, I cannot diagnose medical conditions, recommend specific unprescribed medications, or change dosages. "
                "Please consult a registered physician for clinical diagnosis and safe prescriptions.\n\n"
                "However, I would love to help you understand your test reports, active medications, or discuss healthy lifestyle tips!"
                if is_english else
                "আমি আপনার মেডিভল্ট স্বাস্থ্য সহকারী ও বন্ধু, কিন্তু কোনো লাইসেন্সপ্রাপ্ত ডাক্তার নই। 😊\n\n"
                "আপনার নিরাপত্তার জন্য আমি কোনো রোগ নির্ণয় বা নতুন ওষুধ প্রেসক্রাইব/সুপারিশ করতে পারি না। "
                "আপনার এই লক্ষণের সঠিক চিকিৎসার জন্য অনুগ্রহ করে একজন নিবন্ধিত ডাক্তারের সাথে যোগাযোগ করুন।\n\n"
                "তবে আপনার যেকোনো টেস্ট রিপোর্ট বুঝতে, স্বাস্থ্যকর ডায়েট বা লাইফস্টাইল টিপসের বিষয়ে জানতে চাইলে আমি সবসময় আপনার পাশে আছি!"
            )

            # Record in conversation history
            AIMessage.objects.create(conversation=conversation, sender=AIMessage.Sender.USER, content=question)
            ai_msg = AIMessage.objects.create(conversation=conversation, sender=AIMessage.Sender.ASSISTANT, content=refusal_text)

            return Response({
                "success": True,
                "conversation_id": str(conversation.id),
                "answer": refusal_text,
                "is_refusal": True,
                "cited_documents": [],
                "message_id": str(ai_msg.id)
            }, status=status.HTTP_200_OK)

        # 2. Build holistic Patient Health Profile Context
        patient_summary = [f"Patient Name: {user.full_name}"]
        if patient.blood_group:
            patient_summary.append(f"Blood Group: {patient.blood_group}")
        if patient.gender:
            patient_summary.append(f"Gender: {patient.gender}")
        if patient.date_of_birth:
            patient_summary.append(f"Date of Birth: {patient.date_of_birth}")

        # Active Medications
        try:
            from apps.medications.models import PatientMedicationSchedule
            active_meds = PatientMedicationSchedule.objects.filter(patient=patient, is_active=True)
            if active_meds.exists():
                med_list = [f"- {m.brand_name} {m.dosage_pattern} ({m.timing_relation or 'as directed'})" for m in active_meds[:8]]
                patient_summary.append("Active Prescribed Medications:\n" + "\n".join(med_list))
        except Exception:
            pass

        # Recent Vitals
        try:
            from apps.health_logs.models import BloodGlucoseLog, BloodPressureLog, WeightLog
            recent_glucose = BloodGlucoseLog.objects.filter(patient=patient).order_by('-measurement_date', '-measurement_time').first()
            if recent_glucose:
                patient_summary.append(f"Latest Blood Glucose: {recent_glucose.glucose_value} mmol/L ({recent_glucose.meal_context}) on {recent_glucose.measurement_date}")

            recent_bp = BloodPressureLog.objects.filter(patient=patient).order_by('-measurement_date', '-measurement_time').first()
            if recent_bp:
                patient_summary.append(f"Latest Blood Pressure: {recent_bp.systolic}/{recent_bp.diastolic} mmHg on {recent_bp.measurement_date}")

            recent_weight = WeightLog.objects.filter(patient=patient).order_by('-measurement_date').first()
            if recent_weight:
                patient_summary.append(f"Latest Weight: {recent_weight.weight_kg} kg")
        except Exception:
            pass

        # Recent Uploaded Medical Documents & Structured Findings
        try:
            from apps.documents.models import MedicalDocument, DocumentEntity
            recent_docs = MedicalDocument.objects.filter(patient=patient).order_by('-document_date')[:5]
            if recent_docs.exists():
                docs_summary = []
                for d in recent_docs:
                    clinician = f"by {d.issuing_doctor_name}" if d.issuing_doctor_name else ""
                    clinic = f"at {d.issuing_clinic_name}" if d.issuing_clinic_name else ""
                    docs_summary.append(f"- {d.title or d.document_type} ({d.document_date}) {clinician} {clinic}".strip())
                patient_summary.append("Uploaded Health Documents:\n" + "\n".join(docs_summary))

            # Include All Recent Extracted Lab Findings across patient's documents
            recent_entities = DocumentEntity.objects.filter(
                document__patient=patient
            ).select_related('document').order_by('-document__document_date', '-created_at')[:40]
            if recent_entities.exists():
                lab_lines = []
                for e in recent_entities:
                    ref = f" (Ref: {e.reference_range})" if e.reference_range else ""
                    unit = f" {e.unit}" if e.unit else ""
                    lab_lines.append(f"- {e.entity_name}: {e.entity_value}{unit}{ref} [from {e.document.title}]")
                patient_summary.append("Recent Laboratory Findings & Measurements (From Uploaded Reports):\n" + "\n".join(lab_lines))
        except Exception:
            pass

        # 3. Retrieve relevant document chunks via RAG
        retriever = RAGRetriever()
        chunks = retriever.retrieve_context(patient_id=str(patient.id), query_text=question, top_k=4)

        context_blocks = []
        cited_ids = []
        for c in chunks:
            if c.get("document_id"):
                cited_ids.append(c["document_id"])
            context_blocks.append(f"Document [{c['title']} | Date: {c.get('date')}]:\n{c['content']}")

        context_str = "\n\n---\n\n".join(context_blocks) if context_blocks else "No specific document excerpts found."
        patient_profile_str = "\n".join(patient_summary)

        # 4. Build multi-turn context (last 6 messages)
        recent_messages = conversation.messages.order_by('-created_at')[:6]
        history = []
        for m in reversed(list(recent_messages)):
            role = "user" if m.sender == AIMessage.Sender.USER else "assistant"
            history.append({"role": role, "content": m.content})

        # Dynamic language directive based on user input
        if lang == 'en':
            lang_directive = "The patient asked in English. You MUST reply in fluent, warm, supportive English. Do NOT reply in Bangla."
        elif lang == 'bn':
            lang_directive = "The patient asked in Bangla (বাংলা). You MUST reply in warm, empathetic, fluent Bangla."
        else:
            lang_directive = "The patient asked in Banglish (Bengali in English letters). Reply warmly in fluent Bangla (or conversational Banglish with simple English medical terms)."

        # Append current user prompt with injected Patient Context & RAG
        prompt_with_context = (
            f"=== PATIENT PROFILE & HEALTH CONTEXT ===\n"
            f"{patient_profile_str}\n\n"
            f"=== RELEVANT UPLOADED DOCUMENT EXCERPTS ===\n"
            f"{context_str}\n\n"
            f"=== PATIENT'S QUESTION / MESSAGE ===\n"
            f"{question}\n\n"
            f"(Instruction: Be a warm, conversational personal health assistant and friend. "
            f"{lang_directive} "
            f"Use clean markdown formatting with clear headings, bullet points, and bold text for readability. "
            f"Do not prescribe new prescription medications.)"
        )
        history.append({"role": "user", "content": prompt_with_context})

        # 5. Generate friendly, grounded response using OpenAI GPT-4o-mini
        ai_service = OpenAIService()
        answer = ""
        if ai_service.is_api_configured():
            try:
                from openai import OpenAI
                client = OpenAI(api_key=ai_service.api_key)
                completion = client.chat.completions.create(
                    model=ai_service.model,
                    temperature=0.7,  # Friendly, natural, empathetic tone
                    messages=[
                        {"role": "system", "content": ASK_AI_SYSTEM_PROMPT},
                        *history
                    ]
                )
                answer = completion.choices[0].message.content.strip()
            except Exception as e:
                logger.error("OpenAI API call failed in AskAIView: %s", str(e))

        if not answer:
            # Fallback friendly response when offline
            q_lower = question.lower()
            is_english = (lang == 'en')
            if any(k in q_lower for k in ['hello', 'hi', 'hey', 'কেমন', 'হ্যালো', 'সালাম']):
                answer = (
                    f"Hello {user.full_name}! 😊 I am your MediVault personal health assistant and friend.\n\n"
                    "How are you feeling today? Whether you want to discuss healthy lifestyle habits, explore nutrition tips, or understand your diagnostic lab reports, I'm right here with you!"
                    if is_english else
                    f"হ্যালো {user.full_name}! 😊 আমি আপনার মেডিভল্ট ব্যক্তিগত স্বাস্থ্য সহকারী ও বন্ধু।\n\n"
                    "আপনার স্বাস্থ্য, লাইফস্টাইল বা টেস্ট রিপোর্ট সম্পর্কিত যেকোনো বিষয়ে আমাকে নির্দ্বিধায় জিজ্ঞাসা করতে পারেন। আজ আপনাকে কীভাবে সাহায্য করতে পারি?"
                )
            elif context_blocks:
                answer = (
                    f"Based on your uploaded medical records:\n\n{chunks[0]['content'][:250]}...\n\n"
                    "Please let me know if you would like me to explain any specific test results or values in detail! 😊"
                    if is_english else
                    f"আপনার আপলোডকৃত রেকর্ড অনুযায়ী:\n\n{chunks[0]['content'][:250]}...\n\n"
                    "আপনার স্বাস্থ্য বা রিপোর্ট সম্পর্কে আর কোনো বিষয় জানতে চাইলে আমাকে বলতে পারেন! 😊"
                )
            else:
                answer = (
                    f"Thank you for reaching out {user.full_name}! 😊 While there isn't a specific record uploaded for this topic in your vault yet, I'm here as your personal health assistant to share wellness tips, explain medical concepts, and support your daily health journey."
                    if is_english else
                    f"ধন্যবাদ আপনার বার্তার জন্য {user.full_name}! 😊 আপনার রেকর্ডে এই বিষয়ে সরাসরি কোনো নথি আপলোড করা নেই, তবে সাধারণ স্বাস্থ্যকর জীবনযাত্রা ও সচেতনতার জন্য আমি আপনার পাশে আছি। কোনো নির্দিষ্ট শারীরিক অসুস্থতা বা চিকিৎসার প্রয়োজনে আপনার ডাক্তারের পরামর্শ নিন।"
                )

        # 6. Persist user and assistant messages
        AIMessage.objects.create(conversation=conversation, sender=AIMessage.Sender.USER, content=question)
        ai_msg = AIMessage.objects.create(
            conversation=conversation,
            sender=AIMessage.Sender.ASSISTANT,
            content=answer,
            cited_document_ids=list(set(cited_ids))
        )
        conversation.save(update_fields=['updated_at'])

        return Response({
            "success": True,
            "conversation_id": str(conversation.id),
            "answer": answer,
            "is_refusal": False,
            "cited_documents": chunks,
            "message_id": str(ai_msg.id)
        }, status=status.HTTP_200_OK)


class AIConversationViewSet(viewsets.ModelViewSet):
    """
    Manages chat history and message threads between patient and MediVault AI.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AIConversationSerializer

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, 'patient_profile'):
            return AIConversation.objects.none()
        return AIConversation.objects.filter(patient=user.patient_profile).prefetch_related('messages')

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        conv = self.get_object()
        msgs = conv.messages.all().order_by('created_at')
        return Response({
            "success": True,
            "conversation_id": str(conv.id),
            "title": conv.title,
            "messages": AIMessageSerializer(msgs, many=True).data
        }, status=status.HTTP_200_OK)

