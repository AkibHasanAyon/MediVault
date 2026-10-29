from django.contrib import admin
from .models import Medication, MedicationReminder, MedicationAdherence

class MedicationReminderInline(admin.TabularInline):
    model = MedicationReminder
    extra = 0

@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ('name', 'strength', 'dosage_pattern', 'patient', 'is_active', 'refill_remaining_doses', 'provenance')
    list_filter = ('is_active', 'provenance')
    search_fields = ('name', 'generic_name', 'patient__user__full_name')
    inlines = [MedicationReminderInline]

@admin.register(MedicationAdherence)
class MedicationAdherenceAdmin(admin.ModelAdmin):
    list_display = ('medication', 'action', 'scheduled_time', 'recorded_time', 'skip_reason')
    list_filter = ('action', 'scheduled_time')

