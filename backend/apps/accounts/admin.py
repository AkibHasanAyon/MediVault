from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('phone_number', 'email', 'full_name', 'role', 'is_phone_verified', 'is_staff', 'created_at')
    list_filter = ('role', 'is_phone_verified', 'is_staff', 'is_active', 'preferred_language')
    search_fields = ('phone_number', 'email', 'full_name')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'email', 'preferred_language')}),
        ('Role & Verification', {'fields': ('role', 'is_phone_verified', 'is_email_verified')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at', 'last_login')
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'full_name', 'role', 'password', 'is_phone_verified'),
        }),
    )

