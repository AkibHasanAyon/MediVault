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
        r'(কি\s*ওষুধ|কী\s*ওষুধ|কোন\s*ওষুধ|খাওয়া\s*উচিত|খাওয়া\s*উচিত)',
        r'(রোগ\s*নির্ণয়|আমার\s*কী\s*হয়েছে|আমার\s*কি\s*হয়েছে)',
        r'(what\s+medicine\s+should\s+i\s+take|what\s+drug\s+should|prescribe\s+me|diagnose\s+me)',
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
        lang = data.get('language', 'bn')
        conv_id = data.get('conversation_id')

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
                language=lang
            )

        # 1. Check for unsafe medical prescription / diagnosis request
        if self.is_unsafe_medical_request(question):
            logger.info("Medical safety refusal triggered for user question: %s", question)
            refusal_text = (
                "আমি একটি এআই স্বাস্থ্য সহকারী, কোনো ডাক্তার নই। আমি কোনো রোগ নির্ণয় বা নতুন ওষুধ সুপারিশ করতে পারি না। "
                "অনুগ্রহ করে সঠিক পরামর্শ এবং প্রেসক্রিপশনের জন্য একজন নিবন্ধিত ডাক্তারের সাথে যোগাযোগ করুন।"
                if lang == 'bn' else
                "I am an AI health assistant, not a doctor. I cannot diagnose conditions, prescribe new medications, "
                "or modify dosages. Please consult a licensed physician for clinical guidance."
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

        # 2. Retrieve relevant document chunks via RAG
        retriever = RAGRetriever()
        chunks = retriever.retrieve_context(patient_id=str(patient.id), query_text=question, top_k=4)

        context_blocks = []
        cited_ids = []
        for c in chunks:
            if c.get("document_id"):
                cited_ids.append(c["document_id"])
            context_blocks.append(f"Document [{c['title']} | Date: {c.get('date')}]:\n{c['content']}")

        context_str = "\n\n---\n\n".join(context_blocks) if context_blocks else "No matching health documents found for this patient."

        # 3. Build multi-turn context (last 5 messages)
        recent_messages = conversation.messages.order_by('-created_at')[:5]
        history = []
        for m in reversed(list(recent_messages)):
            role = "user" if m.sender == AIMessage.Sender.USER else "assistant"
            history.append({"role": role, "content": m.content})

        # Append current user prompt with injected RAG context
        prompt_with_context = (
            f"CONTEXT FROM PATIENT HEALTH RECORDS:\n{context_str}\n\n"
            f"PATIENT QUESTION: {question}\n\n"
            f"Remember: Answer solely based on the context. If not mentioned in records, say it is not found. "
            f"Respond in {'Bangla' if lang == 'bn' else 'English'}."
        )
        history.append({"role": "user", "content": prompt_with_context})

        # 4. Generate grounded response using OpenAI GPT-4o-mini
        ai_service = OpenAIService()
        answer = ""
        if ai_service.is_api_configured():
            try:
                from openai import OpenAI
                client = OpenAI(api_key=ai_service.api_key)
                completion = client.chat.completions.create(
                    model=ai_service.model,
                    temperature=0.2,
                    messages=[
                        {"role": "system", "content": ASK_AI_SYSTEM_PROMPT},
                        *history
                    ]
                )
                answer = completion.choices[0].message.content.strip()
            except Exception as e:
                logger.error("OpenAI API call failed in AskAIView: %s", str(e))

        if not answer:
            # Fallback deterministic answer when offline
            if context_blocks:
                answer = (
                    f"আপনার আপলোডকৃত রেকর্ড অনুযায়ী:\n{chunks[0]['content'][:200]}..."
                    if lang == 'bn' else
                    f"According to your uploaded records:\n{chunks[0]['content'][:200]}..."
                )
            else:
                answer = (
                    "আপনার আপলোডকৃত রেকর্ডে এই তথ্যটি পাওয়া যায়নি। অনুগ্রহ করে আপনার ডাক্তারের সাথে পরামর্শ করুন।"
                    if lang == 'bn' else
                    "This information was not found in your uploaded records. Please consult your doctor."
                )

        # 5. Persist user and assistant messages
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

