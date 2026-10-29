from django.contrib import admin
from .models import Appointment, QueueEntry, PreAppointmentSummary, FollowUpReminder

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'clinic', 'scheduled_date', 'slot_time', 'status')
    list_filter = ('status', 'scheduled_date')
    search_fields = ('patient__user__full_name', 'doctor__user__full_name')

@admin.register(QueueEntry)
class QueueEntryAdmin(admin.ModelAdmin):
    list_display = ('token_display', 'clinic', 'doctor', 'patient', 'queue_date', 'state', 'estimated_wait_minutes')
    list_filter = ('state', 'queue_date', 'clinic')
    search_fields = ('token_display', 'patient__user__full_name')

@admin.register(PreAppointmentSummary)
class PreAppointmentSummaryAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'primary_concern')

@admin.register(FollowUpReminder)
class FollowUpReminderAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'due_date', 'milestone_stage', 'is_dispatched')
    list_filter = ('milestone_stage', 'is_dispatched', 'due_date')

