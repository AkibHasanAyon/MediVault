import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
import django
django.setup()

from apps.documents.models import MedicalDocument
from apps.ai_services.rag_retriever import RAGRetriever

retriever = RAGRetriever()
docs = MedicalDocument.objects.all()
print(f"Indexing {docs.count()} existing documents into RAG Knowledgebase...")
for d in docs:
    retriever.index_document(d)
    print(f"Indexed Doc: {d.id} - {d.title}")

print("All existing documents indexed successfully!")

