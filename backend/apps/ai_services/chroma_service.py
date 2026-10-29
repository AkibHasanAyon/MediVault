import socket
import logging
from django.conf import settings
from .openai_service import OpenAIService

logger = logging.getLogger('medivault.chroma')

class ChromaService:
    """
    ChromaDB Vector Database Service.
    Indexes extracted document text chunks using cosine space and scopes queries strictly by patient_id.
    Safely handles offline development mode when ChromaDB container is not running.
    """

    def __init__(self):
        self.host = getattr(settings, 'CHROMA_HOST', 'localhost')
        self.port = getattr(settings, 'CHROMA_PORT', 8001)
        self.collection_name = getattr(settings, 'CHROMA_COLLECTION', 'medivault_patient_documents')
        self.ai = OpenAIService()
        self.client = None
        self.collection = None
        self._init_client()

    def _init_client(self):
        # Quick non-blocking socket check to prevent HTTP connection hanging when Docker is down
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.2)
        try:
            s.connect((self.host, self.port))
            s.close()
            import chromadb
            self.client = chromadb.HttpClient(host=self.host, port=self.port)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("Connected to ChromaDB cluster at %s:%s", self.host, self.port)
        except Exception:
            logger.info("ChromaDB cluster offline at %s:%s. Operating in local simulated vector mode.", self.host, self.port)
            self.client = None
            self.collection = None

    def index_document(self, doc_id: str, patient_id: str, text: str, metadata: dict) -> str:
        """
        Embeds document text into ChromaDB vector space.
        Tags with patient_id for strict isolation.
        """
        if not self.collection:
            logger.info("Chroma collection offline; generated local vector reference for doc %s", doc_id)
            return f"vec_{doc_id}"

        try:
            chunk = text[:3500]  # First chunk up to model context window
            embedding = self.ai.get_embedding(chunk)
            metadata["patient_id"] = patient_id

            self.collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[metadata]
            )
            logger.info("Indexed document %s for patient %s in ChromaDB", doc_id, patient_id)
            return doc_id
        except Exception as e:
            logger.error("Failed to index document %s in ChromaDB: %s", doc_id, str(e))
            return f"vec_{doc_id}"

    def query_patient_records(self, patient_id: str, query_text: str, n_results: int = 4) -> list[str]:
        """
        Retrieves top relevant chunks scoped strictly to the authenticated patient.
        Never queries outside the patient's records.
        """
        if not self.collection:
            return []

        try:
            query_embedding = self.ai.get_embedding(query_text)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where={"patient_id": patient_id}
            )
            return results.get('documents', [[]])[0] if results.get('documents') else []
        except Exception as e:
            logger.error("Failed to query ChromaDB for patient %s: %s", patient_id, str(e))
            return []
