from django.contrib import admin
from .models import ConsultationShare, ShareAuditLog

@admin.register(ConsultationShare)
class ConsultationShareAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'is_active', 'expires_at', 'created_at')
    list_filter = ('is_active', 'expires_at')
    search_fields = ('patient__user__full_name', 'doctor__user__full_name')

@admin.register(ShareAuditLog)
class ShareAuditLogAdmin(admin.ModelAdmin):
    list_display = ('share', 'doctor', 'ip_address', 'action_summary', 'created_at')
    search_fields = ('doctor__user__full_name', 'action_summary')

