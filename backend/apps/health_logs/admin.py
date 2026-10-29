from django.contrib import admin
from .models import BloodGlucoseLog, BloodPressureLog, WeightLog, SymptomNote, DangerAlert

@admin.register(BloodGlucoseLog)
class BloodGlucoseLogAdmin(admin.ModelAdmin):
    list_display = ('patient', 'family_member', 'glucose_value_mmol', 'reading_type', 'is_danger', 'recorded_at')
    list_filter = ('reading_type', 'is_danger', 'recorded_at')
    search_fields = ('patient__user__full_name', 'patient__user__phone_number')

@admin.register(BloodPressureLog)
class BloodPressureLogAdmin(admin.ModelAdmin):
    list_display = ('patient', 'family_member', 'systolic_mmHg', 'diastolic_mmHg', 'pulse_bpm', 'is_crisis', 'recorded_at')
    list_filter = ('is_crisis', 'recorded_at')
    search_fields = ('patient__user__full_name',)

@admin.register(WeightLog)
class WeightLogAdmin(admin.ModelAdmin):
    list_display = ('patient', 'weight_kg', 'calculated_bmi', 'recorded_at')

@admin.register(SymptomNote)
class SymptomNoteAdmin(admin.ModelAdmin):
    list_display = ('patient', 'symptom_tags', 'severity', 'recorded_at')
    list_filter = ('severity',)

@admin.register(DangerAlert)
class DangerAlertAdmin(admin.ModelAdmin):
    list_display = ('patient', 'alert_type', 'trigger_value', 'is_acknowledged', 'notification_dispatched', 'created_at')
    list_filter = ('alert_type', 'is_acknowledged', 'notification_dispatched')

