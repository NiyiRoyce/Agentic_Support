# schemas for knowledge agent
"""Schemas for Knowledge Agent."""

from typing import Optional, List
from pydantic import BaseModel, Field


class KnowledgeQuery(BaseModel):
    """Query for knowledge retrieval."""
    question: str = Field(description="User's question")
    filters: dict = Field(
        default_factory=dict,
        description="Filters for knowledge search"
    )
    max_results: int = Field(
        default=5,
        description="Maximum number of results to retrieve"
    )


class KnowledgeSource(BaseModel):
    """A single knowledge source/document."""
    content: str = Field(description="Document content")
    source: str = Field(description="Source identifier")
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Relevance score"
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class KnowledgeResponse(BaseModel):
    """Response from knowledge agent."""
    answer: str = Field(description="Generated answer")
    sources: List[KnowledgeSource] = Field(
        default_factory=list,
        description="Sources used for answer"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in answer"
    )
    requires_human: bool = Field(
        default=False,
        description="Whether question requires human expertise"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Reasoning behind the answer"
    )


class KnowledgeAgentInput(BaseModel):
    """Input for Knowledge Agent."""
    user_question: str
    conversation_history: List[dict] = Field(default_factory=list)
    filters: dict = Field(default_factory=dict)


class KnowledgeAgentOutput(BaseModel):
    """Output from Knowledge Agent."""
    answer: str
    sources_used: List[str]
    confidence: float
    requires_human: bool
    reasoning: Optional[str] = None