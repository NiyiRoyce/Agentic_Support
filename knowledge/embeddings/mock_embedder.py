# Mock embedder for testing
"""Mock embedder for testing without API keys."""

from typing import List
import hashlib

from knowledge.embeddings.base import Embedder


class MockEmbedder(Embedder):
    """Mock embedder that generates deterministic embeddings for testing."""

    def __init__(self, dimension: int = 1536):
        """Initialize mock embedder."""
        self._dimension = dimension

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings."""
        embeddings = []
        for text in texts:
            # Create deterministic embedding based on text hash
            hash_obj = hashlib.md5(text.encode())
            hash_int = int(hash_obj.hexdigest(), 16)
            
            # Generate pseudo-random but deterministic vector
            embedding = []
            for i in range(self._dimension):
                # Use hash to seed a simple PRNG-like sequence
                value = ((hash_int + i) % 1000) / 500.0 - 1.0  # Range [-1, 1]
                embedding.append(value)
            
            embeddings.append(embedding)
        
        return embeddings

    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a single query."""
        embeddings = await self.embed_texts([query])
        return embeddings[0]

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension