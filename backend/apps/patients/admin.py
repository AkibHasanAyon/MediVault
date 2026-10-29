from django.contrib import admin
from .models import PatientProfile, FamilyMember

class FamilyMemberInline(admin.TabularInline):
    model = FamilyMember
    extra = 0

@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'blood_group', 'gender', 'emergency_contact_phone', 'created_at')
    search_fields = ('user__phone_number', 'user__full_name')
    list_filter = ('blood_group', 'gender')
    inlines = [FamilyMemberInline]

@admin.register(FamilyMember)
class FamilyMemberAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'relationship', 'primary_account', 'blood_group', 'gender')
    search_fields = ('full_name', 'primary_account__user__full_name')
    list_filter = ('relationship', 'blood_group', 'gender')

