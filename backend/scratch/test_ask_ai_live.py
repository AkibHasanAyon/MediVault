import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
import django
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from apps.accounts.models import User
from apps.ai_services.views import AskAIView

user = User.objects.get(phone_number="+8801799955959") # Tania Lima
factory = APIRequestFactory()
view = AskAIView.as_view()

request = factory.post('/api/v1/ai/ask/', {
    "question": "amr lab test report er besophil eta ki jinish? eta diye ki bujhi? r amr etar result kmn ashse?"
}, format='json')
force_authenticate(request, user=user)

response = view(request)
print("Status code:", response.status_code)

with open("scratch/ask_ai_test_response.txt", "w", encoding="utf-8") as f:
    f.write(response.data.get("answer", ""))

print("Wrote answer to scratch/ask_ai_test_response.txt")

