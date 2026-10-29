from django.contrib import admin
from .models import MedicalDocument, DocumentEntity

class DocumentEntityInline(admin.TabularInline):
    model = DocumentEntity
    extra = 0

@admin.register(MedicalDocument)
class MedicalDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'patient', 'document_type', 'document_date', 'processing_status', 'user_confirmed')
    list_filter = ('document_type', 'processing_status', 'user_confirmed')
    search_fields = ('title', 'patient__user__full_name', 'issuing_doctor_name')
    inlines = [DocumentEntityInline]

@admin.register(DocumentEntity)
class DocumentEntityAdmin(admin.ModelAdmin):
    list_display = ('entity_name', 'entity_type', 'entity_value', 'unit', 'is_abnormal', 'provenance')
    list_filter = ('entity_type', 'is_abnormal', 'provenance')
    search_fields = ('entity_name', 'entity_value')

