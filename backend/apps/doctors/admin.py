from django.contrib import admin
from .models import DoctorProfile

@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bmdc_registration_number', 'primary_specialty', 'is_verified_practitioner', 'consultation_fee')
    search_fields = ('user__phone_number', 'user__full_name', 'bmdc_registration_number', 'primary_specialty')
    list_filter = ('is_verified_practitioner', 'primary_specialty')

