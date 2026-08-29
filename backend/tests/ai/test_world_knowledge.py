"""Tests for the World Knowledge retrieval layer."""

from app.ai.world_knowledge.embedding import LocalHashEmbeddingProvider
from app.ai.world_knowledge.retrieval import KnowledgeRetrieval
from app.schemas.knowledge import KnowledgeDocument


def test_embedding_provider_is_deterministic_and_has_vector_length():
    """Embedding provider should return a stable vector for the same text."""
    provider = LocalHashEmbeddingProvider(dimensions=16)
    vector_a = provider.generate_embedding("transformer attention mechanism")
    vector_b = provider.generate_embedding("transformer attention mechanism")

    assert len(vector_a) == 16
    assert vector_a == vector_b


def test_retrieval_chunks_documents_and_returns_hits():
    """Retrieval should split document content into chunks and rank the relevant chunk highest."""
    doc = KnowledgeDocument(
        id="doc-1",
        title="Transformers",
        content=(
            "Transformers use self-attention to model token relationships. "
            "The encoder-decoder architecture enables sequence-to-sequence tasks. "
            "Multi-head attention allows the model to attend to different parts of the input."
        ),
        source="internal-knowledge",
        metadata={"domain": "nlp"},
    )

    retriever = KnowledgeRetrieval()
    retriever.index_documents([doc])
    results = retriever.retrieve("What is self-attention in transformers?", limit=3)

    assert len(results) >= 1
    assert results[0].title == "Transformers"
    assert results[0].score >= 0.0
    assert results[0].source == "internal-knowledge"


def test_retrieval_can_build_context_from_results():
    """Retrieval should provide structured context ready to be passed to an LLM."""
    doc = KnowledgeDocument(
        id="doc-2",
        title="BERT",
        content="BERT is a bidirectional encoder trained with masked language modeling.",
        source="documentation",
        metadata={"domain": "nlp"},
    )

    retriever = KnowledgeRetrieval()
    retriever.index_documents([doc])
    results = retriever.retrieve("What is BERT?", limit=2)
    context = retriever.build_context(results)

    assert "BERT" in context
    assert "documentation" in context
