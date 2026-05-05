# knowledge retriever
"""Knowledge base retrieval service."""

from typing import List, Dict, Any, Optional
from knowledge.vector_store import VectorStore, Document
from knowledge.embeddings import Embedder


class KnowledgeRetriever:
    """Service for retrieving knowledge from vector store."""

    def __init__(
        self,
        vector_store: VectorStore,
        embedder: Embedder,
        max_results: int = 5,
        score_threshold: float = 0.7,
    ):
        """Initialize retriever."""
        self.vector_store = vector_store
        self.embedder = embedder
        self.max_results = max_results
        self.score_threshold = score_threshold

    async def retrieve(self, query: str, metadata_filter: Optional[Dict[str, Any]] = None) -> List[str]:
        """Retrieve relevant knowledge chunks for a query."""
        try:
            # Generate embedding for query
            query_embedding = await self.embedder.embed_query(query)

            # Search vector store
            results = await self.vector_store.search(
                query_embedding=query_embedding,
                limit=self.max_results * 2,  # Get more results for filtering
                metadata_filter=metadata_filter,
            )

            # Filter by score threshold and limit results
            filtered_results = [
                result for result in results
                if result.score >= self.score_threshold
            ][:self.max_results]

            # If no results pass threshold, fallback to returning all stored documents
            if not filtered_results:
                try:
                    all_docs = await self.vector_store.get_all_documents()
                    return [d.content for d in all_docs]
                except Exception:
                    pass

            # Extract content
            chunks = [result.document.content for result in filtered_results]

            return chunks

        except Exception as e:
            print(f"Error retrieving knowledge: {e}")
            return []

    async def add_documents(self, documents: List[Document]) -> bool:
        """Add documents to the knowledge base."""
        try:
            # Generate embeddings for documents that don't have them
            docs_to_embed = [doc for doc in documents if doc.embedding is None]

            if docs_to_embed:
                texts = [doc.content for doc in docs_to_embed]
                embeddings = await self.embedder.embed_texts(texts)

                # Update documents with embeddings
                for doc, embedding in zip(docs_to_embed, embeddings):
                    doc.embedding = embedding

            # Add to vector store
            return await self.vector_store.add_documents(documents)

        except Exception as e:
            print(f"Error adding documents: {e}")
            return False

    async def clear_knowledge_base(self) -> bool:
        """Clear all knowledge base content."""
        try:
            return await self.vector_store.clear()
        except Exception as e:
            print(f"Error clearing knowledge base: {e}")
            return False