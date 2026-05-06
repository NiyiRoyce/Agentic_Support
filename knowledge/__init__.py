"""Knowledge module for RAG and knowledge management."""

# Vector store
from knowledge.vector_store.base import VectorStore, Document, SearchResult
from knowledge.vector_store.chroma_store import ChromaVectorStore

# Embeddings
from knowledge.embeddings.base import Embedder
from knowledge.embeddings.openai_embedder import OpenAIEmbedder

# Retrieval
from knowledge.retrieval.retriever import KnowledgeRetriever

__all__ = [
    # Vector Store
    "VectorStore",
    "Document",
    "SearchResult",
    "ChromaVectorStore",
    # Embeddings
    "Embedder",
    "OpenAIEmbedder",
    # Retrieval
    "KnowledgeRetriever",
]
