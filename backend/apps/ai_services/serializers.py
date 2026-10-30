from rest_framework import serializers
from .models import AIConversation, AIMessage

class AIMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIMessage
        fields = [
            'id',
            'conversation',
            'sender',
            'content',
            'cited_document_ids',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class AIConversationSerializer(serializers.ModelSerializer):
    messages = AIMessageSerializer(many=True, read_only=True)
    messages_count = serializers.IntegerField(source='messages.count', read_only=True)

    class Meta:
        model = AIConversation
        fields = [
            'id',
            'patient',
            'title',
            'language',
            'messages_count',
            'messages',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'patient', 'created_at', 'updated_at']


class AskAIQuestionInputSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField(required=False, allow_null=True)
    question = serializers.CharField(max_length=2000, required=True)
    language = serializers.ChoiceField(choices=[('bn', 'Bangla'), ('en', 'English')], default='bn')

