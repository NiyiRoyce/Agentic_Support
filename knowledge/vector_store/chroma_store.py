"""ChromaDB vector store implementation."""

import asyncio
from typing import List, Dict, Any, Optional, cast, Sequence, Mapping

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
        self.collection_name = collection_name
        self.persist_directory = persist_directory

        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "AI Support Agent Knowledge Base"},
        )

    async def add_documents(self, documents: List[Document]) -> bool:
        """Add documents to the vector store with embeddings."""
        try:
            if not documents:
                return True

            # Filter to only documents with embeddings
            docs_with_embeddings = [
                doc for doc in documents if doc.embedding is not None
            ]

            if not docs_with_embeddings:
                return True

            ids = [doc.id for doc in docs_with_embeddings]
            embeddings: List[Sequence[float]] = [
                cast(Sequence[float], doc.embedding) for doc in docs_with_embeddings
            ]
            metadatas: List[Dict[str, Any]] = [
                doc.metadata or {} for doc in docs_with_embeddings
            ]
            documents_text = [doc.content for doc in docs_with_embeddings]

            await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self.collection.add(
                    ids=ids,
                    embeddings=embeddings,  # type: ignore[arg-type]
                    metadatas=metadatas,  # type: ignore[arg-type]
                    documents=documents_text,
                ),
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
        """Search for similar documents using vector similarity."""
        try:
            results = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self.collection.query(
                    query_embeddings=[cast(Sequence[float], query_embedding)],  # type: ignore[arg-type]
                    n_results=limit,
                    where=metadata_filter,
                    include=["documents", "metadatas", "distances"],
                ),
            )

            search_results: List[SearchResult] = []

            ids_list = results.get("ids")
            documents_list = results.get("documents")
            metadatas_list = results.get("metadatas")
            distances_list = results.get("distances")

            # Guard against empty results
            if not ids_list or not ids_list[0]:
                return []

            ids = ids_list[0] if ids_list else []
            documents = documents_list[0] if documents_list else []
            metadatas = metadatas_list[0] if metadatas_list else []
            distances = distances_list[0] if distances_list else []

            for i, doc_id in enumerate(ids):
                if i >= len(documents) or i >= len(metadatas) or i >= len(distances):
                    continue

                doc_content = documents[i] or ""

                # Convert metadata Mapping to dict for compatibility
                metadata: Dict[str, Any] = {}
                if metadatas[i] is not None:
                    meta_item = metadatas[i]
                    if isinstance(meta_item, dict):
                        metadata = meta_item
                    else:
                        # Cast Mapping to dict
                        metadata = dict(cast(Mapping[str, Any], meta_item))

                doc = Document(
                    id=doc_id,
                    content=doc_content,
                    metadata=metadata,
                    embedding=None,
                )

                distance = distances[i]
                score = 1.0 - float(distance)

                search_results.append(SearchResult(document=doc, score=score))

            return search_results

        except Exception as e:
            print(f"Error searching: {e}")
            return []

    async def delete(self, document_ids: List[str]) -> bool:
        try:
            await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self.collection.delete(ids=document_ids),
            )
            return True
        except Exception as e:
            print(f"Error deleting documents: {e}")
            return False

    async def count(self) -> int:
        try:
            return int(self.collection.count())
        except Exception:
            return 0

    async def clear(self) -> bool:
        try:
            await asyncio.get_running_loop().run_in_executor(
                None, lambda: self.collection.delete()
            )
            return True
        except Exception as e:
            print(f"Error clearing collection: {e}")
            return False

    async def get_all_documents(self) -> List[Document]:
        """Retrieve all documents from the store."""
        try:
            results = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self.collection.get(
                    include=["documents", "metadatas", "embeddings"]
                ),
            )

            documents: List[Document] = []

            ids = results.get("ids")
            docs = results.get("documents")
            metas = results.get("metadatas")
            embeds = results.get("embeddings")

            # Guard against empty or missing ids
            if not ids:
                return []

            for i, doc_id in enumerate(ids):
                # Ensure all indices are in bounds
                if docs is None or i >= len(docs):
                    continue
                if metas is None or i >= len(metas):
                    continue

                doc_content = docs[i] or ""

                # Convert metadata Mapping to dict for compatibility
                metadata: Dict[str, Any] = {}
                if metas[i] is not None:
                    meta_item = metas[i]
                    if isinstance(meta_item, dict):
                        metadata = meta_item
                    else:
                        # Cast Mapping to dict
                        metadata = dict(cast(Mapping[str, Any], meta_item))

                embedding: Optional[List[float]] = None
                if embeds and i < len(embeds) and embeds[i] is not None:
                    embedding = cast(List[float], embeds[i])

                documents.append(
                    Document(
                        id=doc_id,
                        content=doc_content,
                        metadata=metadata,
                        embedding=embedding,
                    )
                )

            return documents

        except Exception as e:
            print(f"Error getting all documents: {e}")
            return []

    async def update_embeddings(self, documents: List[Document]) -> bool:
        """Update document embeddings."""
        try:
            if not documents:
                return True

            # Filter to only documents with embeddings
            docs_with_embeddings = [
                doc for doc in documents if doc.embedding is not None
            ]

            if not docs_with_embeddings:
                return True

            ids = [doc.id for doc in docs_with_embeddings]
            embeddings: List[Sequence[float]] = [
                cast(Sequence[float], doc.embedding) for doc in docs_with_embeddings
            ]

            await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self.collection.update(
                    ids=ids,
                    embeddings=embeddings,  # type: ignore[arg-type]
                ),
            )
            return True

        except Exception as e:
            print(f"Error updating embeddings: {e}")
            return False
