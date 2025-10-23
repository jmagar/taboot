"""Tests for RedditReader.

Tests Reddit post/comment ingestion using LlamaIndex RedditReader.
Following TDD methodology (RED-GREEN-REFACTOR).
"""

import pytest
from llama_index.core import Document


class TestRedditReader:
    """Tests for the RedditReader class."""

    def test_reddit_reader_loads_subreddit(self) -> None:
        """Test that RedditReader can load posts from a subreddit."""
        from packages.ingest.readers.reddit import RedditReader

        reader = RedditReader(
            client_id="test-id", client_secret="test-secret", user_agent="test-agent"
        )
        docs = reader.load_data(subreddit="python", limit=10)

        assert isinstance(docs, list)
        assert len(docs) <= 10
        assert all(isinstance(doc, Document) for doc in docs)

    def test_reddit_reader_validates_subreddit(self) -> None:
        """Test that RedditReader validates subreddit name."""
        from packages.ingest.readers.reddit import RedditReader

        reader = RedditReader(
            client_id="test-id", client_secret="test-secret", user_agent="test-agent"
        )

        with pytest.raises(ValueError, match="subreddit"):
            reader.load_data(subreddit="", limit=10)

    def test_reddit_reader_requires_credentials(self) -> None:
        """Test that RedditReader requires Reddit API credentials."""
        from packages.ingest.readers.reddit import RedditReader

        with pytest.raises(ValueError, match="client_id"):
            RedditReader(client_id="", client_secret="secret", user_agent="agent")

        with pytest.raises(ValueError, match="client_secret"):
            RedditReader(client_id="id", client_secret="", user_agent="agent")

        with pytest.raises(ValueError, match="user_agent"):
            RedditReader(client_id="id", client_secret="secret", user_agent="")

    def test_reddit_reader_respects_limit(self) -> None:
        """Test that RedditReader respects the limit parameter."""
        from packages.ingest.readers.reddit import RedditReader

        reader = RedditReader(
            client_id="test-id", client_secret="test-secret", user_agent="test-agent"
        )
        docs = reader.load_data(subreddit="python", limit=5)

        assert len(docs) <= 5

    def test_reddit_reader_includes_metadata(self) -> None:
        """Test that RedditReader includes post metadata."""
        from packages.ingest.readers.reddit import RedditReader

        reader = RedditReader(
            client_id="test-id", client_secret="test-secret", user_agent="test-agent"
        )
        docs = reader.load_data(subreddit="python", limit=1)

        if docs:
            assert docs[0].metadata is not None
            assert "source_type" in docs[0].metadata
            assert docs[0].metadata["source_type"] == "reddit"
