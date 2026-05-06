# embeddings base interface
"""Base interface for text embedders."""

from abc import ABC, abstractmethod
from typing import List


class Embedder(ABC):
    """Abstract base class for text embedders."""

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        pass

    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a single query."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Get the embedding dimension."""
        pass
