"""World Knowledge retrieval service."""

from __future__ import annotations

from app.ai.world_knowledge.embedding import EmbeddingProvider, LocalHashEmbeddingProvider
from app.schemas.knowledge import KnowledgeDocument, RetrievedKnowledge


class KnowledgeRetrieval:
    """Minimal retrieval layer for document chunking, embedding, and ranking."""

    def __init__(self, embedding_provider: EmbeddingProvider | None = None):
        self.embedding_provider = embedding_provider or LocalHashEmbeddingProvider()
        self.documents: list[KnowledgeDocument] = []
        self.chunks: list[tuple[str, str, KnowledgeDocument]] = []

    def index_documents(self, documents: list[KnowledgeDocument]) -> None:
        """Index knowledge documents by splitting them into chunks."""
        self.documents = list(documents)
        self.chunks = []

        for document in self.documents:
            chunks = self.chunk_text(document.content, chunk_size=250, overlap=50)
            for index, chunk in enumerate(chunks):
                self.chunks.append((f"{document.id}:{index}", chunk, document))

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 250, overlap: int = 50) -> list[str]:
        """Split text into chunks while preserving readability."""
        if not text.strip():
            return []

        normalized = " ".join(text.split())
        if len(normalized) <= chunk_size:
            return [normalized]

        chunks: list[str] = []
        start = 0
        while start < len(normalized):
            end = min(len(normalized), start + chunk_size)
            chunk = normalized[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end == len(normalized):
                break
            start = max(0, end - overlap)
        return chunks

    def retrieve(self, query: str, limit: int = 5) -> list[RetrievedKnowledge]:
        """Retrieve the most relevant chunks for a query using deterministic similarity."""
        if not self.chunks:
            return []

        query_vector = self.embedding_provider.generate_embedding(query)
        hits: list[RetrievedKnowledge] = []

        for chunk_id, chunk_text, document in self.chunks:
            chunk_vector = self.embedding_provider.generate_embedding(chunk_text)
            score = self._similarity(query_vector, chunk_vector)
            hits.append(
                RetrievedKnowledge(
                    id=chunk_id,
                    title=document.title,
                    content=chunk_text,
                    source=document.source,
                    score=score,
                    metadata=document.metadata,
                )
            )

        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:limit]

    @staticmethod
    def _similarity(vector_a: list[float], vector_b: list[float]) -> float:
        """Compute a simple cosine-style similarity between vectors."""
        if not vector_a or not vector_b or len(vector_a) != len(vector_b):
            return 0.0

        dot = sum(a * b for a, b in zip(vector_a, vector_b))
        norm_a = (sum(a * a for a in vector_a)) ** 0.5
        norm_b = (sum(b * b for b in vector_b)) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def build_context(results: list[RetrievedKnowledge]) -> str:
        """Build a plain-text context string from retrieval results."""
        sections: list[str] = []
        for result in results:
            sections.append(
                f"[Source: {result.source}] {result.title}\n{result.content}\n"
            )
        return "\n".join(sections)