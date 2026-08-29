"""Knowledge schemas for retrieval and source metadata."""

from typing import Any

from pydantic import BaseModel, Field


class KnowledgeDocument(BaseModel):
    """Document that may be used as knowledge context."""

    id: str = Field(..., description="Stable document identifier")
    title: str = Field(..., description="Document or section title")
    content: str = Field(..., description="The full document content")
    source: str = Field(
        ..., description="Source type, such as internal_knowledge or documentation"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata such as domain, category, or source URL",
    )


class RetrievedKnowledge(BaseModel):
    """A retrieved knowledge hit with source metadata and ranking score."""

    id: str = Field(..., description="Chunk or document identifier")
    title: str = Field(..., description="Chunk title or document title")
    content: str = Field(..., description="Retrieved content")
    source: str = Field(..., description="Source category")
    score: float = Field(..., description="Relevance score from retrieval")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Associated metadata for the retrieved chunk",
    )