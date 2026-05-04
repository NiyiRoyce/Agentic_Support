#!/usr/bin/env python3
# rebuild vector index script

"""Script to rebuild the vector index from existing documents."""

import asyncio
import sys
from pathlib import Path
import argparse

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge.vector_store import ChromaVectorStore
from knowledge.ingestion import DocumentIngestor
from knowledge.embeddings import OpenAIEmbedder
from config import settings


async def main():
    """Rebuild vector index."""
    parser = argparse.ArgumentParser(description="Rebuild vector index")
    parser.add_argument(
        "--docs-path",
        default="./docs",
        help="Path to documentation directory"
    )
    parser.add_argument(
        "--pattern",
        default="*.md",
        help="File pattern for documents"
    )

    args = parser.parse_args()

    print("Rebuilding vector index...")

    # Initialize components
    vector_store = ChromaVectorStore(persist_directory=settings.rag_vector_store_path)
    embedder = OpenAIEmbedder(api_key=settings.openai_api_key)
    ingestor = DocumentIngestor(
        vector_store=vector_store,
        embedder=embedder,
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap
    )

    # Clear existing index
    print("Clearing existing index...")
    await vector_store.clear()

    # Check if docs path exists
    docs_path = Path(args.docs_path)
    if not docs_path.exists():
        print(f"Docs path {docs_path} does not exist. Creating sample docs...")
        docs_path.mkdir(parents=True, exist_ok=True)
        # Create sample docs
        create_sample_docs(docs_path)

    # Re-ingest all documents
    print(f"Ingesting documents from {docs_path}...")
    success_count = await ingestor.ingest_directory(
        directory_path=str(docs_path),
        file_pattern=args.pattern
    )

    # Verify
    final_count = await vector_store.count()
    print(f"Rebuild completed. Ingested {success_count} documents, total in index: {final_count}")

    return 0


def create_sample_docs(docs_path: Path):
    """Create sample documentation files for testing."""
    sample_files = {
        "api.md": "# API Documentation\n\nThis is the API documentation for the AI Support Agent.\n\n## Endpoints\n\n- GET /health\n- POST /api/v1/chat\n\n## Authentication\n\nUse API key in headers.",
        "architecture.md": "# Architecture\n\n## Components\n\n- FastAPI app\n- Orchestration router\n- Agent implementations\n- Knowledge base with RAG\n- Memory store\n\n## Data Flow\n\nUser request -> Intent classification -> Agent execution -> Response",
        "deployment.md": "# Deployment\n\n## Requirements\n\n- Python 3.12+\n- Redis for memory\n- ChromaDB for vectors\n\n## Steps\n\n1. Install dependencies\n2. Set environment variables\n3. Run migrations\n4. Start server"
    }

    for filename, content in sample_files.items():
        (docs_path / filename).write_text(content)


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
