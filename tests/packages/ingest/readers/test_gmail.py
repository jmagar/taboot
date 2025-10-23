"""Tests for GmailReader.

Tests Gmail message ingestion using LlamaIndex GmailReader.
Following TDD methodology (RED-GREEN-REFACTOR).
"""

import pytest
from llama_index.core import Document


class TestGmailReader:
    """Tests for the GmailReader class."""

    def test_gmail_reader_loads_messages(self) -> None:
        """Test that GmailReader can load Gmail messages."""
        from packages.ingest.readers.gmail import GmailReader

        reader = GmailReader(credentials_path="/path/to/credentials.json")
        docs = reader.load_data(query="is:unread", limit=10)

        assert isinstance(docs, list)
        assert len(docs) <= 10
        assert all(isinstance(doc, Document) for doc in docs)

    def test_gmail_reader_validates_credentials_path(self) -> None:
        """Test that GmailReader validates credentials path."""
        from packages.ingest.readers.gmail import GmailReader

        with pytest.raises(ValueError, match="credentials_path"):
            GmailReader(credentials_path="")

    def test_gmail_reader_handles_empty_query(self) -> None:
        """Test that GmailReader allows empty query (all messages)."""
        from packages.ingest.readers.gmail import GmailReader

        reader = GmailReader(credentials_path="/path/to/credentials.json")
        # Empty query should not raise error
        docs = reader.load_data(query="", limit=1)
        assert isinstance(docs, list)

    def test_gmail_reader_respects_limit(self) -> None:
        """Test that GmailReader respects the limit parameter."""
        from packages.ingest.readers.gmail import GmailReader

        reader = GmailReader(credentials_path="/path/to/credentials.json")
        docs = reader.load_data(query="is:unread", limit=5)

        assert len(docs) <= 5

    def test_gmail_reader_includes_metadata(self) -> None:
        """Test that GmailReader includes email metadata."""
        from packages.ingest.readers.gmail import GmailReader

        reader = GmailReader(credentials_path="/path/to/credentials.json")
        docs = reader.load_data(query="is:unread", limit=1)

        if docs:
            assert docs[0].metadata is not None
            assert "source_type" in docs[0].metadata
            assert docs[0].metadata["source_type"] == "gmail"
