"""Tests for WebReader.

Tests Firecrawl-based web crawling using LlamaIndex SimpleWebPageReader.
Following TDD methodology (RED-GREEN-REFACTOR).
"""

import pytest
from llama_index.core import Document


class TestWebReader:
    """Tests for the WebReader class."""

    def test_web_reader_loads_single_url(self) -> None:
        """Test that WebReader can load a single URL."""
        from packages.ingest.readers.web import WebReader

        reader = WebReader(firecrawl_url="http://taboot-crawler:3002", firecrawl_api_key="test-key")
        docs = reader.load_data(url="https://example.com", limit=1)

        assert len(docs) == 1
        assert isinstance(docs[0], Document)
        assert docs[0].text is not None
        assert len(docs[0].text) > 0
        assert docs[0].metadata["source_url"] == "https://example.com"

    def test_web_reader_respects_limit(self) -> None:
        """Test that WebReader respects the limit parameter."""
        from packages.ingest.readers.web import WebReader

        reader = WebReader(firecrawl_url="http://taboot-crawler:3002", firecrawl_api_key="test-key")
        docs = reader.load_data(url="https://example.com/docs", limit=3)

        assert len(docs) <= 3

    def test_web_reader_validates_url_format(self) -> None:
        """Test that WebReader validates URL format."""
        from packages.ingest.readers.web import WebReader

        reader = WebReader(firecrawl_url="http://taboot-crawler:3002", firecrawl_api_key="test-key")

        with pytest.raises(ValueError, match="Invalid URL"):
            reader.load_data(url="not-a-url", limit=1)

    def test_web_reader_handles_empty_url(self) -> None:
        """Test that WebReader rejects empty URLs."""
        from packages.ingest.readers.web import WebReader

        reader = WebReader(firecrawl_url="http://taboot-crawler:3002", firecrawl_api_key="test-key")

        with pytest.raises(ValueError, match="URL"):
            reader.load_data(url="", limit=1)

    def test_web_reader_requires_firecrawl_url(self) -> None:
        """Test that WebReader requires firecrawl_url parameter."""
        from packages.ingest.readers.web import WebReader

        with pytest.raises(TypeError):
            WebReader()  # Missing required firecrawl_url

    def test_web_reader_returns_document_list(self) -> None:
        """Test that WebReader returns a list of Document objects."""
        from packages.ingest.readers.web import WebReader

        reader = WebReader(firecrawl_url="http://taboot-crawler:3002", firecrawl_api_key="test-key")
        docs = reader.load_data(url="https://example.com", limit=1)

        assert isinstance(docs, list)
        assert all(isinstance(doc, Document) for doc in docs)
