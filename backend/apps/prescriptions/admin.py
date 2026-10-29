from django.contrib import admin
from .models import Prescription, PrescriptionMedication, DrugInteractionRule

class PrescriptionMedicationInline(admin.TabularInline):
    model = PrescriptionMedication
    extra = 0

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'clinic', 'follow_up_date', 'created_at')
    search_fields = ('patient__user__full_name', 'doctor__user__full_name', 'diagnosis')
    inlines = [PrescriptionMedicationInline]

@admin.register(DrugInteractionRule)
class DrugInteractionRuleAdmin(admin.ModelAdmin):
    list_display = ('drug_a_generic', 'drug_b_generic', 'severity')
    list_filter = ('severity',)
    search_fields = ('drug_a_generic', 'drug_b_generic')

