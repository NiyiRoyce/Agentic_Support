# document ingestion
"""Document ingestion service."""

from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from knowledge.vector_store import Document
from knowledge.ingestion.chunking import TextChunker


class DocumentIngestor:
    """Service for ingesting documents into the knowledge base."""

    def __init__(self, chunker: Optional[TextChunker] = None):
        """Initialize ingestor."""
        self.chunker = chunker or TextChunker()

    def ingest_text_file(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Ingest a text file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Get file metadata
            file_info = Path(file_path)
            file_metadata = {
                "source": str(file_path),
                "filename": file_info.name,
                "file_size": file_info.stat().st_size,
                "ingested_at": datetime.utcnow().isoformat(),
            }

            if metadata:
                file_metadata.update(metadata)

            # Chunk the content
            chunks = self.chunker.chunk_text(content)

            # Create documents
            documents = []
            for i, chunk in enumerate(chunks):
                doc_id = f"{file_info.stem}_chunk_{i}"
                doc = Document(
                    id=doc_id,
                    content=chunk,
                    metadata={
                        **file_metadata,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                    }
                )
                documents.append(doc)

            return documents

        except Exception as e:
            print(f"Error ingesting file {file_path}: {e}")
            return []

    def ingest_directory(self, directory_path: str, file_pattern: str = "*.txt", metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Ingest all files in a directory matching the pattern."""
        path = Path(directory_path)
        if not path.exists() or not path.is_dir():
            print(f"Directory {directory_path} does not exist")
            return []

        all_documents = []

        for file_path in path.glob(file_pattern):
            if file_path.is_file():
                docs = self.ingest_text_file(str(file_path), metadata)
                all_documents.extend(docs)

        return all_documents

    def ingest_text_content(self, content: str, source_id: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Ingest raw text content."""
        content_metadata = {
            "source": source_id,
            "ingested_at": datetime.utcnow().isoformat(),
        }

        if metadata:
            content_metadata.update(metadata)

        # Chunk the content
        chunks = self.chunker.chunk_text(content)

        # Create documents
        documents = []
        for i, chunk in enumerate(chunks):
            doc_id = f"{source_id}_chunk_{i}"
            doc = Document(
                id=doc_id,
                content=chunk,
                metadata={
                    **content_metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                }
            )
            documents.append(doc)

        return documents