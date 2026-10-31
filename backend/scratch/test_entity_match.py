import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
import django
django.setup()

from apps.ai_services.models import AIConversation
from apps.documents.models import MedicalDocument, DocumentEntity
import difflib, re

patient_id = "51e2833b-f93b-4299-835d-8d8afd0641ea"
query_text = "amr lab test report er besophil eta ki jinish? eta diye ki bujhi? r amr etar result kmn ashse?"

# Test Entity Search
query_tokens = set(re.findall(r'[a-zA-Z]+', query_text.lower()))
print("Tokens:", query_tokens)

all_entities = DocumentEntity.objects.filter(document__patient_id=patient_id)
print("Total entities for patient:", all_entities.count())

matched_entity_ids = set()
for entity in all_entities:
    e_name_lower = entity.entity_name.lower()
    # Direct substring
    if any(t in e_name_lower for t in query_tokens if len(t) > 3):
        matched_entity_ids.add(entity.id)
        print("Direct match:", entity.entity_name, entity.entity_value, entity.unit, entity.reference_range)
    # Fuzzy match on tokens
    for t in query_tokens:
        if len(t) >= 4 and difflib.get_close_matches(t, [e_name_lower], cutoff=0.7):
            matched_entity_ids.add(entity.id)
            print("Fuzzy match:", t, "->", entity.entity_name, entity.entity_value, entity.unit, entity.reference_range)

print("Matched entities count:", len(matched_entity_ids))

