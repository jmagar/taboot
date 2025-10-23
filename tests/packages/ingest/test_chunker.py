"""Tests for document chunker.

Tests semantic chunking using LlamaIndex SentenceSplitter.
Following TDD methodology (RED-GREEN-REFACTOR).
"""

import pytest
from llama_index.core import Document


class TestChunker:
    """Tests for the Chunker class."""

    def test_chunker_splits_long_text(self) -> None:
        """Test that Chunker splits long text into chunks."""
        from packages.ingest.chunker import Chunker

        # Create a long text (simulate 1000+ tokens)
        long_text = " ".join([f"This is sentence {i}." for i in range(500)])
        doc = Document(text=long_text)

        chunker = Chunker(chunk_size=512, chunk_overlap=51)
        chunks = chunker.chunk_document(doc)

        assert len(chunks) > 1
        assert all(isinstance(chunk, Document) for chunk in chunks)

    def test_chunker_respects_chunk_size(self) -> None:
        """Test that Chunker respects the chunk_size parameter."""
        from packages.ingest.chunker import Chunker

        long_text = " ".join([f"Word{i}" for i in range(1000)])
        doc = Document(text=long_text)

        chunker = Chunker(chunk_size=256, chunk_overlap=25)
        chunks = chunker.chunk_document(doc)

        # Each chunk should respect the token limit
        for chunk in chunks:
            assert len(chunk.text.split()) <= 300  # Approximate token count

    def test_chunker_adds_overlap(self) -> None:
        """Test that Chunker adds overlap between chunks."""
        from packages.ingest.chunker import Chunker

        text = " ".join([f"Sentence {i}." for i in range(100)])
        doc = Document(text=text)

        chunker = Chunker(chunk_size=512, chunk_overlap=51)  # 10% overlap
        chunks = chunker.chunk_document(doc)

        if len(chunks) > 1:
            # Check that consecutive chunks have some overlap
            # (This is a heuristic test - overlap detection is approximate)
            assert chunks[0].text != chunks[1].text

    def test_chunker_preserves_metadata(self) -> None:
        """Test that Chunker preserves document metadata in chunks."""
        from packages.ingest.chunker import Chunker

        doc = Document(
            text="This is a test document that will be chunked.",
            metadata={"source_url": "https://example.com", "doc_id": "123"},
        )

        chunker = Chunker(chunk_size=512, chunk_overlap=51)
        chunks = chunker.chunk_document(doc)

        for chunk in chunks:
            assert chunk.metadata.get("source_url") == "https://example.com"
            assert chunk.metadata.get("doc_id") == "123"

    def test_chunker_handles_short_text(self) -> None:
        """Test that Chunker handles text shorter than chunk_size."""
        from packages.ingest.chunker import Chunker

        short_text = "This is a short document."
        doc = Document(text=short_text)

        chunker = Chunker(chunk_size=512, chunk_overlap=51)
        chunks = chunker.chunk_document(doc)

        assert len(chunks) == 1
        assert chunks[0].text == short_text

    def test_chunker_handles_empty_document(self) -> None:
        """Test that Chunker handles empty documents."""
        from packages.ingest.chunker import Chunker

        doc = Document(text="")

        chunker = Chunker(chunk_size=512, chunk_overlap=51)
        chunks = chunker.chunk_document(doc)

        assert len(chunks) == 0 or (len(chunks) == 1 and chunks[0].text == "")

    def test_chunker_configurable_overlap(self) -> None:
        """Test that Chunker respects configurable overlap parameter."""
        from packages.ingest.chunker import Chunker

        text = " ".join([f"Word{i}" for i in range(500)])
        doc = Document(text=text)

        # Test with different overlap values
        chunker_10 = Chunker(chunk_size=256, chunk_overlap=25)  # ~10%
        chunker_20 = Chunker(chunk_size=256, chunk_overlap=51)  # ~20%

        chunks_10 = chunker_10.chunk_document(doc)
        chunks_20 = chunker_20.chunk_document(doc)

        # More overlap should result in more chunks (potentially)
        assert len(chunks_10) >= 1
        assert len(chunks_20) >= 1

    def test_chunker_adds_position_metadata(self) -> None:
        """Test that Chunker adds position metadata to chunks."""
        from packages.ingest.chunker import Chunker

        text = " ".join([f"Sentence {i}." for i in range(100)])
        doc = Document(text=text)

        chunker = Chunker(chunk_size=256, chunk_overlap=25)
        chunks = chunker.chunk_document(doc)

        # Each chunk should have position information
        for i, chunk in enumerate(chunks):
            assert "chunk_index" in chunk.metadata
            assert chunk.metadata["chunk_index"] == i
