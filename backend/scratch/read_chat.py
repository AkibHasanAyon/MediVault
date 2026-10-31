import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
import django
django.setup()
from apps.ai_services.models import AIConversation

with open("scratch_chat_log.txt", "w", encoding="utf-8") as f:
    for c in AIConversation.objects.order_by('-created_at')[:3]:
        f.write(f"=== Conv: {c.id} {c.title} ===\n")
        for m in c.messages.order_by('created_at'):
            f.write(f"[{m.sender}]: {m.content}\n\n")
print("Wrote scratch_chat_log.txt")
