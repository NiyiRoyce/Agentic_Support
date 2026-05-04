"""Integration tests for RAG flow."""

import pytest
import asyncio
import tempfile
from pathlib import Path

from knowledge.vector_store import ChromaVectorStore
from knowledge.embeddings import OpenAIEmbedder
from knowledge.ingestion import DocumentIngestor
from knowledge.retrieval import KnowledgeRetriever
from config import settings


@pytest.fixture
async def temp_vector_store():
    """Create temporary vector store for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        store = ChromaVectorStore(persist_directory=temp_dir)
        yield store
        # Cleanup
        await store.clear()


@pytest.fixture
async def embedder():
    """Create embedder (mock if no API key)."""
    if settings.openai_api_key:
        return OpenAIEmbedder(api_key=settings.openai_api_key)
    else:
        # Use mock embedder for testing
        from knowledge.embeddings.mock_embedder import MockEmbedder
        return MockEmbedder()


@pytest.fixture
async def ingestor(temp_vector_store, embedder):
    """Create document ingestor."""
    return DocumentIngestor(
        vector_store=temp_vector_store,
        embedder=embedder,
        chunk_size=500,
        chunk_overlap=50
    )


@pytest.fixture
async def retriever(temp_vector_store, embedder):
    """Create knowledge retriever."""
    return KnowledgeRetriever(
        vector_store=temp_vector_store,
        embedder=embedder
    )


@pytest.mark.asyncio
async def test_full_rag_flow(ingestor, retriever):
    """Test complete RAG flow: ingest -> index -> retrieve."""
    # Create test documents
    test_docs = {
        "doc1.md": "# Test Document 1\n\nThis is a test document about AI support agents.",
        "doc2.md": "# Test Document 2\n\nAI agents help with customer support automation."
    }

    with tempfile.TemporaryDirectory() as docs_dir:
        docs_path = Path(docs_dir)

        # Write test files
        for filename, content in test_docs.items():
            (docs_path / filename).write_text(content)

        # Ingest documents
        ingested_count = await ingestor.ingest_directory(str(docs_path), "*.md")
        assert ingested_count == 2

        # Check documents in store
        count = await ingestor.vector_store.count()
        assert count == 2

        # Retrieve relevant information
        query = "AI support agents"
        results = await retriever.retrieve(query, limit=2)

        assert len(results) > 0
        assert any("AI support agents" in result.document.content for result in results)

        # Test with different query
        query2 = "customer support automation"
        results2 = await retriever.retrieve(query2, limit=2)

        assert len(results2) > 0
        assert any("customer support" in result.document.content for result in results2)


@pytest.mark.asyncio
async def test_retrieval_scoring(retriever, ingestor):
    """Test that retrieval returns relevant results with proper scoring."""
    # Add specific test documents
    test_content = [
        "The capital of France is Paris.",
        "Berlin is the capital of Germany.",
        "Machine learning is a subset of artificial intelligence.",
        "Python is a programming language used for data science."
    ]

    documents = []
    for i, content in enumerate(test_content):
        from knowledge.vector_store.base import Document
        doc = Document(
            id=f"test_doc_{i}",
            content=content,
            metadata={"source": f"test_{i}.txt"}
        )
        documents.append(doc)

    # Add to store with embeddings
    await ingestor.vector_store.add_documents(documents)

    # Query for geography
    results = await retriever.retrieve("What is the capital of France?", limit=3)

    # Should return Paris document with high score
    assert len(results) > 0
    top_result = results[0]
    assert "Paris" in top_result.document.content
    assert top_result.score > 0.5  # Assuming good similarity


@pytest.mark.asyncio
async def test_empty_retrieval(retriever):
    """Test retrieval when no documents exist."""
    results = await retriever.retrieve("test query")
    assert results == []