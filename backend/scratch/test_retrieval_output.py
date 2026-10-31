import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
import django
django.setup()

from apps.ai_services.rag_retriever import RAGRetriever

patient_id = "51e2833b-f93b-4299-835d-8d8afd0641ea"
query = "amr lab test report er besophil eta ki jinish? eta diye ki bujhi? r amr etar result kmn ashse?"

retriever = RAGRetriever()
chunks = retriever.retrieve_context(patient_id=patient_id, query_text=query, top_k=4)

print(f"Retrieved {len(chunks)} chunks:")
for i, c in enumerate(chunks):
    print(f"\n--- CHUNK {i+1} [{c['title']}] ---")
    print(c['content'][:400])
    if "basophil" in c['content'].lower() or "0/cmm" in c['content'].lower():
        print("  >>> SUCCESS: FOUND BASOPHIL IN CHUNK! <<<")

