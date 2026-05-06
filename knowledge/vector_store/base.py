# vector store base interfaces
"""Base interfaces for vector stores."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Document:
    """Represents a document chunk stored in the vector store."""

    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None


@dataclass
class SearchResult:
    """Result of a vector search."""

    document: Document
    score: float


class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    async def add_documents(self, documents: List[Document]) -> bool:
        """Add documents to the vector store."""
        pass

    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search for similar documents using vector similarity."""
        pass

    @abstractmethod
    async def delete(self, document_ids: List[str]) -> bool:
        """Delete documents by IDs."""
        pass

    @abstractmethod
    async def count(self) -> int:
        """Get total number of documents."""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all documents."""
        pass

    @abstractmethod
    async def get_all_documents(self) -> List[Document]:
        """Retrieve all documents from the store."""
        pass
