import io
import calendar
import logging
from datetime import date, datetime
from decimal import Decimal
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from django.db.models import Avg

from apps.reports.models import MonthlyHealthReport
from apps.patients.models import PatientProfile
from apps.health_logs.models import BloodGlucoseLog, BloodPressureLog, DangerAlert
from apps.medications.models import Medication
from apps.medications.services.adherence import AdherenceEngine
from apps.ai_services.openai_service import OpenAIService
from apps.ai_services.prompts import MONTHLY_REPORT_NARRATIVE_PROMPT

logger = logging.getLogger('medivault.reports')

class MonthlyReportBuilder:
    """
    Constructs deterministic monthly health analytics, synthesizes AI clinical summaries,
    and generates multi-page vector PDF reports.
    """

    @classmethod
    def generate_monthly_report(cls, patient: PatientProfile, year: int, month: int) -> MonthlyHealthReport:
        month_name = calendar.month_name[month]
        _, num_days = calendar.monthrange(year, month)
        start_date = date(year, month, 1)
        end_date = date(year, month, num_days)

        # 1. Deterministic health metrics
        glucose_qs = BloodGlucoseLog.objects.filter(patient=patient, recorded_at__date__range=(start_date, end_date))
        glucose_count = glucose_qs.count()
        avg_glucose_agg = glucose_qs.aggregate(avg=Avg('glucose_value_mmol'))['avg']
        avg_glucose = round(float(avg_glucose_agg), 1) if avg_glucose_agg else None

        bp_qs = BloodPressureLog.objects.filter(patient=patient, recorded_at__date__range=(start_date, end_date))
        bp_count = bp_qs.count()

        danger_count = DangerAlert.objects.filter(patient=patient, created_at__date__range=(start_date, end_date)).count()

        adherence_stats = AdherenceEngine.calculate_overall_patient_adherence(patient, days=30)
        adherence_pct = Decimal(str(adherence_stats.get('overall_adherence_percentage', 100.0)))

        active_meds = list(Medication.objects.filter(patient=patient, is_active=True))

        # 2. AI clinical narrative generation
        ai_prompt = (
            f"Patient: {patient.user.full_name}, Period: {month_name} {year}\n"
            f"Vitals: {glucose_count} glucose logs (Average: {avg_glucose or 'N/A'} mmol/L); {bp_count} BP readings.\n"
            f"Danger Alerts: {danger_count} incidents.\n"
            f"Medication Adherence: {adherence_pct}%\n"
            f"Active Medications: {[m.name + ' ' + m.strength for m in active_meds]}\n"
        )

        ai_narrative = ""
        ai = OpenAIService()
        if ai.is_api_configured():
            try:
                from openai import OpenAI
                client = OpenAI(api_key=ai.api_key)
                res = client.chat.completions.create(
                    model=ai.model,
                    temperature=0.3,
                    messages=[
                        {"role": "system", "content": MONTHLY_REPORT_NARRATIVE_PROMPT},
                        {"role": "user", "content": ai_prompt}
                    ]
                )
                ai_narrative = res.choices[0].message.content.strip()
            except Exception as e:
                logger.error("Failed to generate monthly report AI narrative: %s", str(e))

        if not ai_narrative:
            ai_narrative = (
                f"During {month_name} {year}, you recorded {glucose_count} blood glucose measurements with an average "
                f"of {avg_glucose or 'unrecorded'} mmol/L and logged {bp_count} blood pressure readings. "
                f"Your medication adherence rate was {adherence_pct}%. "
                f"Continue maintaining consistent tracking and discuss these trends during your next consultation."
            )

        # 3. Render HTML
        context = {
            "report_title": f"Monthly Health Summary — {month_name} {year}",
            "generated_date": timezone.now().strftime('%d %B %Y, %I:%M %p'),
            "patient_name": patient.user.full_name,
            "patient_phone": patient.user.phone_number,
            "blood_group": patient.blood_group,
            "known_allergies": patient.known_allergies or "None reported",
            "month_name": month_name,
            "year": year,
            "avg_glucose": avg_glucose,
            "glucose_readings_count": glucose_count,
            "bp_readings_count": bp_count,
            "adherence_percentage": adherence_pct,
            "danger_alerts_count": danger_count,
            "ai_summary_narrative": ai_narrative,
            "active_medications": active_meds,
        }

        html_content = render_to_string('reports/monthly_report.html', context)

        # 4. Convert to PDF (WeasyPrint with ReportLab fallback)
        pdf_bytes = cls._render_pdf(html_content, context)

        # 5. Persist MonthlyHealthReport
        filename = f"report_{patient.id}_{year}_{month:02d}.pdf"
        report, _ = MonthlyHealthReport.objects.update_or_create(
            patient=patient,
            report_year=year,
            report_month=month,
            defaults={
                "report_title": f"Health Report - {month_name} {year}",
                "glucose_readings_count": glucose_count,
                "glucose_average_mmol": Decimal(str(avg_glucose)) if avg_glucose else None,
                "bp_readings_count": bp_count,
                "danger_alerts_count": danger_count,
                "adherence_percentage": adherence_pct,
                "ai_summary_narrative": ai_narrative,
            }
        )
        report.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
        logger.info("Successfully generated monthly health report for patient %s (%s-%02d)", patient.id, year, month)
        return report

    @classmethod
    def _render_pdf(cls, html_content: str, context: dict) -> bytes:
        """
        Attempts to generate vector PDF via WeasyPrint.
        Falls back cleanly to ReportLab when native Pango/Cairo C-libraries are missing.
        """
        try:
            import weasyprint
            return weasyprint.HTML(string=html_content).write_pdf()
        except Exception as e:
            logger.info("WeasyPrint unavailable (%s); generating report via ReportLab engine.", str(e))
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

        title_style = ParagraphStyle('ReportTitle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#0284c7'))
        body_style = ParagraphStyle('ReportBody', parent=styles['Normal'], fontSize=10, leading=14, textColor=colors.HexColor('#1e293b'))
        header_style = ParagraphStyle('ReportSection', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#0f172a'))

        story.append(Paragraph(f"MediVault — {context['report_title']}", title_style))
        story.append(Spacer(1, 10))

        # Patient Info
        patient_info = (
            f"<b>Patient:</b> {context['patient_name']} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Phone:</b> {context['patient_phone']} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Blood Group:</b> {context['blood_group']}"
        )
        story.append(Paragraph(patient_info, body_style))
        story.append(Spacer(1, 15))

        # Metrics Table
        metrics_data = [
            ["Avg Glucose", "Glucose Logs", "BP Readings", "Med Adherence"],
            [f"{context['avg_glucose'] or '--'} mmol/L", str(context['glucose_readings_count']), str(context['bp_readings_count']), f"{context['adherence_percentage']}%"]
        ]
        t = Table(metrics_data, colWidths=[130, 130, 130, 130])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ]))
        story.append(t)
        story.append(Spacer(1, 15))

        # Clinical AI Narrative
        story.append(Paragraph("Clinical AI Summary", header_style))
        story.append(Spacer(1, 5))
        story.append(Paragraph(context['ai_summary_narrative'], body_style))
        story.append(Spacer(1, 20))

        # Disclaimer
        disclaimer = "CONFIDENTIAL. Generated by MediVault AI for clinical consultation with your licensed physician."
        story.append(Paragraph(disclaimer, ParagraphStyle('Disclaimer', parent=styles['Italic'], fontSize=8, textColor=colors.HexColor('#94a3b8'))))

        doc.build(story)
        return buffer.getvalue()

