import io
import base64
import logging
import qrcode
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from apps.prescriptions.models import Prescription

logger = logging.getLogger('medivault.prescriptions')

class PrescriptionPDFBuilder:
    """
    Renders clinic-branded digital prescriptions into vector PDFs.
    Uses WeasyPrint when system C-libraries are present, and falls back to
    clean ReportLab formatting for pure-Python environments.
    """

    @classmethod
    def generate_pdf(cls, prescription: Prescription) -> bytes:
        doctor = prescription.doctor
        patient = prescription.patient
        clinic = prescription.clinic

        # 1. Generate verification QR code
        qr_text = f"medivault://rx?id={prescription.id}&doc={doctor.bmdc_number}&date={prescription.created_at.strftime('%Y-%m-%d')}"
        qr_img = qrcode.make(qr_text, box_size=4, border=1)
        buf_qr = io.BytesIO()
        qr_img.save(buf_qr, format="PNG")
        qr_base64 = f"data:image/png;base64,{base64.b64encode(buf_qr.getvalue()).decode('utf-8')}"

        # 2. Build context
        medications = list(prescription.medications.all())
        target_name = prescription.family_member.full_name if prescription.family_member else patient.user.full_name

        context = {
            "prescription_id": str(prescription.id)[:8].upper(),
            "doctor_name": f"Dr. {doctor.user.full_name}",
            "doctor_specialties": doctor.specialties or "General Physician",
            "bmdc_number": doctor.bmdc_number or "N/A",
            "clinic_name": clinic.name if clinic else "Chamber Consultation",
            "clinic_branch": clinic.branch if clinic else "",
            "clinic_address": clinic.address if clinic else "",
            "clinic_phone": clinic.contact_phone if clinic else "",
            "patient_name": target_name,
            "patient_age": str(patient.date_of_birth) if patient.date_of_birth else "N/A",
            "blood_group": patient.blood_group,
            "known_allergies": patient.known_allergies or "None reported",
            "prescription_date": prescription.created_at.strftime('%d-%b-%Y'),
            "chief_complaints": prescription.chief_complaints,
            "clinical_findings": prescription.clinical_findings,
            "diagnosis": prescription.diagnosis,
            "medications": medications,
            "follow_up_date": str(prescription.follow_up_date) if prescription.follow_up_date else None,
            "follow_up_notes": prescription.follow_up_notes,
            "qr_base64": qr_base64,
        }

        html_content = render_to_string('prescriptions/prescription_layout.html', context)

        # 3. Render PDF
        pdf_bytes = cls._render_pdf(html_content, context)

        # 4. Save to prescription.pdf_file
        filename = f"rx_{prescription.id}_{prescription.created_at.strftime('%Y%m%d')}.pdf"
        prescription.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
        logger.info("Generated and saved PDF for prescription %s", prescription.id)
        return pdf_bytes

    @classmethod
    def _render_pdf(cls, html_content: str, context: dict) -> bytes:
        try:
            import weasyprint
            return weasyprint.HTML(string=html_content).write_pdf()
        except Exception as e:
            logger.info("WeasyPrint unavailable (%s); using ReportLab for prescription PDF.", str(e))
            return cls._render_reportlab_fallback(context)

    @classmethod
    def _render_reportlab_fallback(cls, context: dict) -> bytes:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('DocName', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#0f172a'))
        quals_style = ParagraphStyle('DocQuals', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#334155'))
        body_style = ParagraphStyle('RxBody', parent=styles['Normal'], fontSize=9.5, leading=14, textColor=colors.HexColor('#1e293b'))
        section_style = ParagraphStyle('RxSection', parent=styles['Heading2'], fontSize=11, textColor=colors.HexColor('#0284c7'))

        # Doctor Header
        story.append(Paragraph(context['doctor_name'], title_style))
        story.append(Paragraph(f"{context['doctor_specialties']} | BM&DC: {context['bmdc_number']}", quals_style))
        if context['clinic_name']:
            story.append(Paragraph(f"Chamber: {context['clinic_name']} ({context['clinic_branch']})", quals_style))
        story.append(Spacer(1, 10))

        # Patient Info Table
        patient_data = [
            [f"Patient: {context['patient_name']}", f"Age: {context['patient_age']}", f"Blood: {context['blood_group']}", f"Date: {context['prescription_date']}"],
            [f"Allergies: {context['known_allergies']}", "", "", f"Rx #: {context['prescription_id']}"]
        ]
        t_pat = Table(patient_data, colWidths=[150, 100, 100, 170])
        t_pat.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_pat)
        story.append(Spacer(1, 12))

        # Clinical Diagnosis
        if context['diagnosis']:
            story.append(Paragraph(f"<b>Diagnosis (Dx):</b> {context['diagnosis']}", body_style))
        if context['chief_complaints']:
            story.append(Paragraph(f"<b>Chief Complaints:</b> {context['chief_complaints']}", body_style))
        story.append(Spacer(1, 12))

        # Rx Medications
        story.append(Paragraph("<b>℞ Prescribed Medications:</b>", section_style))
        story.append(Spacer(1, 6))

        med_rows = [["#", "Medicine", "Dosage & Frequency", "Duration", "Instructions"]]
        for idx, med in enumerate(context['medications'], 1):
            med_rows.append([
                str(idx),
                f"{med.brand_name} {med.strength} ({med.dosage_form})",
                f"{med.frequency} - {med.timing_relation}",
                f"{med.duration_days} days",
                med.special_instructions or "As directed"
            ])

        t_meds = Table(med_rows, colWidths=[20, 160, 140, 70, 130])
        t_meds.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        story.append(t_meds)
        story.append(Spacer(1, 16))

        # Advice & Follow-Up
        if context['follow_up_notes'] or context['follow_up_date']:
            f_text = f"<b>Next Follow-Up / Advice:</b> {context['follow_up_notes'] or 'Return as advised'}"
            if context['follow_up_date']:
                f_text += f" (Due Date: {context['follow_up_date']})"
            story.append(Paragraph(f_text, body_style))
            story.append(Spacer(1, 15))

        # Footer
        footer_text = "Verified Digital Prescription · MediVault Health Bangladesh · Call 999 in acute emergencies."
        story.append(Paragraph(footer_text, ParagraphStyle('Foot', parent=styles['Italic'], fontSize=7.5, textColor=colors.HexColor('#94a3b8'))))

        doc.build(story)
        return buffer.getvalue()

