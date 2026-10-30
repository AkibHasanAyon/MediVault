from django.http import FileResponse, Http404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import MonthlyHealthReport
from .serializers import (
    MonthlyHealthReportSerializer,
    GenerateReportInputSerializer,
)
from .services.pdf_builder import MonthlyReportBuilder

class MonthlyHealthReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Manages patient monthly health summary reports and vector PDF downloads.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MonthlyHealthReportSerializer

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'patient_profile'):
            return MonthlyHealthReport.objects.filter(patient=user.patient_profile)
        return MonthlyHealthReport.objects.none()

    @action(detail=False, methods=['post'], url_path='generate')
    def generate_report(self, request):
        """
        Generates a fresh monthly health summary report and PDF on demand.
        """
        user = request.user
        if not hasattr(user, 'patient_profile'):
            return Response({"error": "Only registered patients can generate reports."}, status=status.HTTP_403_FORBIDDEN)

        serializer = GenerateReportInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        patient = user.patient_profile
        report = MonthlyReportBuilder.generate_monthly_report(
            patient=patient,
            year=data['year'],
            month=data['month']
        )

        return Response({
            "success": True,
            "message": f"Monthly report for {data['year']}-{data['month']:02d} successfully generated.",
            "data": MonthlyHealthReportSerializer(report, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='download')
    def download_pdf(self, request, pk=None):
        """
        Streams the generated PDF report directly to the client.
        """
        report = self.get_object()
        if not report.pdf_file:
            raise Http404("PDF file not generated for this report.")

        return FileResponse(
            report.pdf_file.open('rb'),
            as_attachment=True,
            filename=f"MediVault_Report_{report.report_year}_{report.report_month:02d}.pdf",
            content_type='application/pdf'
        )

