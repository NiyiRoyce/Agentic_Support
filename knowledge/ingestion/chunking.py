# text chunking utilities
"""Text chunking utilities for document processing."""

from typing import List
import re


class TextChunker:
    """Utility for chunking text documents."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separator: str = "\n\n",
    ):
        """Initialize chunker."""
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator

    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks."""
        # First try to split by separator
        if self.separator and self.separator in text:
            sections = text.split(self.separator)
        else:
            sections = [text]

        chunks = []
        current_chunk = ""

        for section in sections:
            # If adding this section would exceed chunk size, save current chunk
            if len(current_chunk) + len(section) > self.chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # Start new chunk with overlap from previous
                overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                current_chunk = current_chunk[overlap_start:] + section
            else:
                current_chunk += section + self.separator

        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def chunk_by_sentences(self, text: str, max_sentences: int = 5) -> List[str]:
        """Chunk text by sentence boundaries."""
        # Simple sentence splitting (can be improved with NLP)
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())

        chunks = []
        current_chunk = []

        for sentence in sentences:
            current_chunk.append(sentence)

            if len(current_chunk) >= max_sentences:
                chunks.append(" ".join(current_chunk))
                # Keep some overlap
                overlap_count = min(2, len(current_chunk) // 2)
                current_chunk = current_chunk[-overlap_count:]

        # Add remaining sentences
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks
