#!/usr/bin/env python3
# backfill embeddings script

"""Script to backfill embeddings for documents missing them."""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge.vector_store import ChromaVectorStore
from knowledge.embeddings import OpenAIEmbedder
from config import settings


async def main():
    """Backfill embeddings for documents without them."""
    print("Starting embedding backfill...")

    # Initialize components
    vector_store = ChromaVectorStore(persist_directory=settings.rag_vector_store_path)
    embedder = OpenAIEmbedder(api_key=settings.openai_api_key)

    # Get all documents
    all_docs = await vector_store.get_all_documents()
    print(f"Found {len(all_docs)} documents")

    # Find documents without embeddings
    docs_without_embeddings = [doc for doc in all_docs if not doc.embedding]
    print(f"Found {len(docs_without_embeddings)} documents without embeddings")

    if not docs_without_embeddings:
        print("No documents need backfill")
        return 0

    # Generate embeddings
    texts = [doc.content for doc in docs_without_embeddings]
    print(f"Generating embeddings for {len(texts)} documents...")

    embeddings = await embedder.embed_texts(texts)

    # Update documents with embeddings
    updated_docs = []
    for doc, embedding in zip(docs_without_embeddings, embeddings):
        doc.embedding = embedding
        updated_docs.append(doc)

    # Update in vector store
    success = await vector_store.update_embeddings(updated_docs)
    print(f"Backfill completed. Updated {len(updated_docs)} documents")

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
