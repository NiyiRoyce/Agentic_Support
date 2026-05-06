# OpenAI embeddings implementation
"""OpenAI embeddings implementation."""

from typing import List
from openai import AsyncOpenAI

from knowledge.embeddings.base import Embedder


class OpenAIEmbedder(Embedder):
    """OpenAI embeddings using text-embedding-3-small."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        """Initialize OpenAI embedder."""
        self.api_key = api_key
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key)
        self._dimension = 1536  # text-embedding-3-small dimension

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        try:
            response = await self.client.embeddings.create(
                input=texts, model=self.model
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            raise RuntimeError(f"Failed to generate embeddings: {e}")

    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a single query."""
        embeddings = await self.embed_texts([query])
        return embeddings[0]

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension
