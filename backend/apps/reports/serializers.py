from rest_framework import serializers
from .models import MonthlyHealthReport

class MonthlyHealthReportSerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = MonthlyHealthReport
        fields = [
            'id',
            'patient',
            'report_year',
            'report_month',
            'report_title',
            'glucose_readings_count',
            'glucose_average_mmol',
            'bp_readings_count',
            'danger_alerts_count',
            'adherence_percentage',
            'ai_summary_narrative',
            'pdf_url',
            'created_at',
        ]
        read_only_fields = ['id', 'patient', 'created_at']

    def get_pdf_url(self, obj) -> str | None:
        if obj.pdf_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
            return obj.pdf_file.url
        return None


class GenerateReportInputSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2020, max_value=2050, required=True)
    month = serializers.IntegerField(min_value=1, max_value=12, required=True)

