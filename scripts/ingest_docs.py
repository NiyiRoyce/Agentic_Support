#!/usr/bin/env python3
# document ingestion script

"""Script to ingest documents into the knowledge base."""

import asyncio
import sys
from pathlib import Path
import argparse

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge.ingestion import DocumentIngestor, TextChunker
from knowledge.retrieval import KnowledgeRetriever
from knowledge.vector_store import ChromaVectorStore
from knowledge.embeddings import OpenAIEmbedder
from config import settings


async def main():
    """Main ingestion function."""
    parser = argparse.ArgumentParser(description="Ingest documents into knowledge base")
    parser.add_argument(
        "path",
        help="Path to file or directory to ingest"
    )
    parser.add_argument(
        "--pattern",
        default="*.txt",
        help="File pattern for directory ingestion (default: *.txt)"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing knowledge base before ingesting"
    )
    parser.add_argument(
        "--metadata",
        type=str,
        help="Additional metadata as key=value pairs (comma-separated)"
    )

    args = parser.parse_args()

    # Parse metadata
    metadata = {}
    if args.metadata:
        for pair in args.metadata.split(","):
            key, value = pair.split("=", 1)
            metadata[key.strip()] = value.strip()

    # Initialize components
    if not settings.openai_api_key:
        print("Error: OPENAI_API_KEY not set")
        return 1

    vector_store = ChromaVectorStore(persist_directory=settings.rag_vector_store_path)
    embedder = OpenAIEmbedder(api_key=settings.openai_api_key)
    retriever = KnowledgeRetriever(
        vector_store=vector_store,
        embedder=embedder,
        max_results=settings.rag_max_results,
        score_threshold=settings.rag_score_threshold,
    )

    chunker = TextChunker(
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
    )
    ingestor = DocumentIngestor(chunker=chunker)

    # Clear if requested
    if args.clear:
        print("Clearing existing knowledge base...")
        await retriever.clear_knowledge_base()

    # Ingest documents
    path = Path(args.path)
    if path.is_file():
        print(f"Ingesting file: {path}")
        documents = ingestor.ingest_text_file(str(path), metadata)
    elif path.is_dir():
        print(f"Ingesting directory: {path} (pattern: {args.pattern})")
        documents = ingestor.ingest_directory(str(path), args.pattern, metadata)
    else:
        print(f"Error: Path {path} does not exist")
        return 1

    if not documents:
        print("No documents found to ingest")
        return 1

    print(f"Found {len(documents)} document chunks to ingest")

    # Add to knowledge base
    print("Generating embeddings and adding to vector store...")
    success = await retriever.add_documents(documents)

    if success:
        print(f"Successfully ingested {len(documents)} chunks")
        return 0
    else:
        print("Failed to ingest documents")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
