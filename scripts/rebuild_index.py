#!/usr/bin/env python3
# rebuild vector index script

"""Script to rebuild the vector index from existing documents."""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge.vector_store import ChromaVectorStore
from config import settings


async def main():
    """Rebuild vector index."""
    print("Rebuilding vector index...")

    # Initialize vector store
    vector_store = ChromaVectorStore(persist_directory=settings.rag_vector_store_path)

    # Clear and rebuild would typically involve re-ingesting all documents
    # For now, just check the current state
    count = await vector_store.count()
    print(f"Current document count: {count}")

    # In a full implementation, this would:
    # 1. Clear the index
    # 2. Re-ingest all source documents
    # 3. Rebuild embeddings

    print("Index rebuild completed (no-op for now)")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
