from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.models import TimeStampedUUIDModel

class AIConversation(TimeStampedUUIDModel):
    patient = models.ForeignKey('patients.PatientProfile', on_delete=models.CASCADE, related_name='ai_conversations')
    title = models.CharField(max_length=255, default='New Health Conversation')
    language = models.CharField(max_length=5, default='bn', choices=[('bn', 'Bangla'), ('en', 'English')])

    class Meta:
        verbose_name = _('AI Conversation')
        verbose_name_plural = _('AI Conversations')
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} ({self.patient.user.full_name})"


class AIMessage(TimeStampedUUIDModel):
    class Sender(models.TextChoices):
        USER = 'USER', _('User')
        ASSISTANT = 'ASSISTANT', _('MediVault AI')

    conversation = models.ForeignKey(AIConversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=15, choices=Sender.choices)
    content = models.TextField()
    cited_document_ids = models.JSONField(default=list, blank=True, help_text=_("Array of referenced document UUIDs"))

    class Meta:
        verbose_name = _('AI Message')
        verbose_name_plural = _('AI Messages')
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.sender}] {self.content[:50]}..."

