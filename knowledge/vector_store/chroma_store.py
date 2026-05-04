# ChromaDB vector store implementation
"""ChromaDB vector store implementation."""

import asyncio
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings

from knowledge.vector_store.base import VectorStore, Document, SearchResult


class ChromaVectorStore(VectorStore):
    """ChromaDB-based vector store implementation."""

    def __init__(
        self,
        collection_name: str = "knowledge_base",
        persist_directory: str = "./vector_store",
    ):
        """Initialize ChromaDB client."""
        self.collection_name = collection_name
        self.persist_directory = persist_directory

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "AI Support Agent Knowledge Base"}
        )

    async def add_documents(self, documents: List[Document]) -> bool:
        """Add documents to the vector store."""
        try:
            ids = [doc.id for doc in documents]
            embeddings = [doc.embedding for doc in documents if doc.embedding]
            metadatas = [doc.metadata for doc in documents]
            documents_text = [doc.content for doc in documents]

            # Run in thread pool since ChromaDB is synchronous
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents_text,
                )
            )
            return True
        except Exception as e:
            print(f"Error adding documents: {e}")
            return False

    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search for similar documents."""
        try:
            # Run in thread pool
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit,
                    where=metadata_filter,
                    include=["documents", "metadatas", "distances"]
                )
            )

            search_results = []
            if results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    # Reconstruct document
                    doc = Document(
                        id=doc_id,
                        content=results["documents"][0][i],
                        metadata=results["metadatas"][0][i],
                        embedding=None,  # Not returned by query
                    )

                    # ChromaDB returns cosine distance, convert to similarity score
                    distance = results["distances"][0][i]
                    score = 1.0 - distance  # Convert distance to similarity

                    search_results.append(SearchResult(document=doc, score=score))

            return search_results
        except Exception as e:
            print(f"Error searching: {e}")
            return []

    async def delete(self, document_ids: List[str]) -> bool:
        """Delete documents by IDs."""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.collection.delete(ids=document_ids)
            )
            return True
        except Exception as e:
            print(f"Error deleting documents: {e}")
            return False

    async def count(self) -> int:
        """Get total number of documents."""
        try:
            return self.collection.count()
        except Exception:
            return 0

    async def clear(self) -> bool:
        """Clear all documents."""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self.collection.delete
            )
            return True
        except Exception as e:
            print(f"Error clearing collection: {e}")
            return False

    async def get_all_documents(self) -> List[Document]:
        """Get all documents in the store."""
        try:
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.collection.get(include=["documents", "metadatas", "embeddings"])
            )

            documents = []
            if results["ids"]:
                for i, doc_id in enumerate(results["ids"]):
                    doc = Document(
                        id=doc_id,
                        content=results["documents"][i],
                        metadata=results["metadatas"][i],
                        embedding=results["embeddings"][i] if results["embeddings"] else None,
                    )
                    documents.append(doc)

            return documents
        except Exception as e:
            print(f"Error getting all documents: {e}")
            return []

    async def update_embeddings(self, documents: List[Document]) -> bool:
        """Update embeddings for existing documents."""
        try:
            ids = [doc.id for doc in documents]
            embeddings = [doc.embedding for doc in documents if doc.embedding]

            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.collection.update(ids=ids, embeddings=embeddings)
            )
            return True
        except Exception as e:
            print(f"Error updating embeddings: {e}")
            return False