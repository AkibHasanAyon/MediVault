from django.contrib import admin
from .models import Clinic, ClinicAssistantProfile, ClinicDoctorAssociation

@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'contact_phone', 'is_active', 'created_at')
    search_fields = ('name', 'branch', 'contact_phone')
    list_filter = ('is_active',)

@admin.register(ClinicAssistantProfile)
class ClinicAssistantProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'clinic', 'desk_serial', 'is_active')
    search_fields = ('user__full_name', 'user__phone_number', 'clinic__name')

@admin.register(ClinicDoctorAssociation)
class ClinicDoctorAssociationAdmin(admin.ModelAdmin):
    list_display = ('clinic', 'doctor', 'chamber_number', 'session_days', 'session_start_time', 'session_end_time')

