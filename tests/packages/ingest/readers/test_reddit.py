"""Tests for RedditReader.

Tests Reddit post/comment ingestion using LlamaIndex RedditReader.
Following TDD methodology (RED-GREEN-REFACTOR).
"""

from datetime import datetime, UTC
from unittest.mock import MagicMock, patch

import pytest
from llama_index.core import Document

from packages.schemas.reddit import RedditComment, RedditPost, Subreddit


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


class TestRedditEntityExtraction:
    """Integration tests for Reddit entity extraction (T204).

    Tests extraction of Subreddit, RedditPost, and RedditComment entities from
    Reddit API responses. Following Phase 4 pattern: integration test → update → verify.
    """

    def test_extract_subreddit_from_document(self) -> None:
        """Test extracting Subreddit entity from Document metadata.

        Per tasks.md: RedditReader should output new entity types (Subreddit, RedditPost, RedditComment).
        """
        from packages.ingest.readers.reddit import RedditReader

        # Mock LlamaIndex RedditReader to return controlled data
        with patch("packages.ingest.readers.reddit.LlamaRedditReader") as mock_reader_class:
            mock_doc = Document(
                text="Welcome to r/Python",
                metadata={
                    "subreddit": "python",
                    "display_name": "Python",
                    "description": "News about the dynamic, interpreted programming language Python.",
                    "subscribers": 1500000,
                    "created_utc": 1201219200.0,  # 2008-01-25 00:00:00 UTC
                    "over_18": False,
                },
            )

            mock_reader_instance = MagicMock()
            mock_reader_instance.load_data.return_value = [mock_doc]
            mock_reader_class.return_value = mock_reader_instance

            reader = RedditReader(
                client_id="test-id", client_secret="test-secret", user_agent="test-agent"
            )
            entities = reader.extract_entities(subreddit="python", limit=1)

            # Verify Subreddit entity extracted
            assert "subreddits" in entities
            subreddits = entities["subreddits"]
            assert len(subreddits) == 1
            assert isinstance(subreddits[0], Subreddit)

            subreddit = subreddits[0]
            assert subreddit.name == "python"
            assert subreddit.display_name == "Python"
            assert subreddit.description == "News about the dynamic, interpreted programming language Python."
            assert subreddit.subscribers == 1500000
            assert subreddit.over_18 is False
            assert subreddit.extraction_tier == "A"
            assert subreddit.confidence == 1.0

    def test_extract_reddit_post_from_document(self) -> None:
        """Test extracting RedditPost entity from Document metadata."""
        from packages.ingest.readers.reddit import RedditReader

        with patch("packages.ingest.readers.reddit.LlamaRedditReader") as mock_reader_class:
            mock_doc = Document(
                text="How to learn Python? I'm new to programming.",
                metadata={
                    "subreddit": "python",
                    "post_id": "abc123",
                    "title": "How to learn Python?",
                    "selftext": "I'm new to programming and want to learn Python. Any suggestions?",
                    "score": 150,
                    "num_comments": 42,
                    "created_utc": 1704110400.0,  # 2024-01-01 10:00:00 UTC
                    "url": "https://reddit.com/r/python/comments/abc123/how_to_learn_python/",
                    "permalink": "/r/python/comments/abc123/how_to_learn_python/",
                    "is_self": True,
                    "over_18": False,
                    "gilded": 2,
                },
            )

            mock_reader_instance = MagicMock()
            mock_reader_instance.load_data.return_value = [mock_doc]
            mock_reader_class.return_value = mock_reader_instance

            reader = RedditReader(
                client_id="test-id", client_secret="test-secret", user_agent="test-agent"
            )
            entities = reader.extract_entities(subreddit="python", limit=1)

            # Verify RedditPost entity extracted
            assert "posts" in entities
            posts = entities["posts"]
            assert len(posts) == 1
            assert isinstance(posts[0], RedditPost)

            post = posts[0]
            assert post.post_id == "abc123"
            assert post.title == "How to learn Python?"
            assert post.selftext == "I'm new to programming and want to learn Python. Any suggestions?"
            assert post.score == 150
            assert post.num_comments == 42
            assert post.is_self is True
            assert post.over_18 is False
            assert post.gilded == 2
            assert post.extraction_tier == "A"
            assert post.confidence == 1.0

    def test_extract_reddit_comment_from_document(self) -> None:
        """Test extracting RedditComment entity from Document metadata."""
        from packages.ingest.readers.reddit import RedditReader

        with patch("packages.ingest.readers.reddit.LlamaRedditReader") as mock_reader_class:
            mock_doc = Document(
                text="Great question! I recommend starting with the official Python tutorial.",
                metadata={
                    "subreddit": "python",
                    "comment_id": "def456",
                    "body": "Great question! I recommend starting with the official Python tutorial.",
                    "score": 25,
                    "created_utc": 1704114000.0,  # 2024-01-01 11:00:00 UTC
                    "permalink": "/r/python/comments/abc123/how_to_learn_python/def456/",
                    "parent_id": "abc123",
                    "depth": 1,
                    "gilded": 1,
                    "edited": False,
                },
            )

            mock_reader_instance = MagicMock()
            mock_reader_instance.load_data.return_value = [mock_doc]
            mock_reader_class.return_value = mock_reader_instance

            reader = RedditReader(
                client_id="test-id", client_secret="test-secret", user_agent="test-agent"
            )
            entities = reader.extract_entities(subreddit="python", limit=1)

            # Verify RedditComment entity extracted
            assert "comments" in entities
            comments = entities["comments"]
            assert len(comments) == 1
            assert isinstance(comments[0], RedditComment)

            comment = comments[0]
            assert comment.comment_id == "def456"
            assert comment.body == "Great question! I recommend starting with the official Python tutorial."
            assert comment.score == 25
            assert comment.parent_id == "abc123"
            assert comment.depth == 1
            assert comment.gilded == 1
            assert comment.edited is False
            assert comment.extraction_tier == "A"
            assert comment.confidence == 1.0

    def test_extract_entities_handles_multiple_documents(self) -> None:
        """Test extracting entities from multiple documents of different types."""
        from packages.ingest.readers.reddit import RedditReader

        with patch("packages.ingest.readers.reddit.LlamaRedditReader") as mock_reader_class:
            mock_docs = [
                # Subreddit info
                Document(
                    text="Python subreddit",
                    metadata={
                        "subreddit": "python",
                        "display_name": "Python",
                        "subscribers": 1500000,
                        "created_utc": 1201219200.0,
                    },
                ),
                # Post
                Document(
                    text="Post title",
                    metadata={
                        "subreddit": "python",
                        "post_id": "post1",
                        "title": "Test Post",
                        "score": 100,
                        "num_comments": 10,
                    },
                ),
                # Comment
                Document(
                    text="Comment text",
                    metadata={
                        "subreddit": "python",
                        "comment_id": "comment1",
                        "body": "Comment text",
                        "score": 5,
                        "parent_id": "post1",
                    },
                ),
            ]

            mock_reader_instance = MagicMock()
            mock_reader_instance.load_data.return_value = mock_docs
            mock_reader_class.return_value = mock_reader_instance

            reader = RedditReader(
                client_id="test-id", client_secret="test-secret", user_agent="test-agent"
            )
            entities = reader.extract_entities(subreddit="python", limit=10)

            # Verify all entity types extracted
            assert "subreddits" in entities
            assert "posts" in entities
            assert "comments" in entities
            assert len(entities["subreddits"]) >= 1
            assert len(entities["posts"]) >= 1
            assert len(entities["comments"]) >= 1

    def test_extract_entities_sets_temporal_fields(self) -> None:
        """Test that temporal tracking fields are set on all entities."""
        from packages.ingest.readers.reddit import RedditReader

        with patch("packages.ingest.readers.reddit.LlamaRedditReader") as mock_reader_class:
            mock_doc = Document(
                text="Test post",
                metadata={
                    "subreddit": "python",
                    "post_id": "test123",
                    "title": "Test",
                    "created_utc": 1704110400.0,
                },
            )

            mock_reader_instance = MagicMock()
            mock_reader_instance.load_data.return_value = [mock_doc]
            mock_reader_class.return_value = mock_reader_instance

            reader = RedditReader(
                client_id="test-id", client_secret="test-secret", user_agent="test-agent"
            )
            entities = reader.extract_entities(subreddit="python", limit=1)

            post = entities["posts"][0]

            # Verify temporal fields present
            assert post.created_at is not None
            assert isinstance(post.created_at, datetime)
            assert post.updated_at is not None
            assert isinstance(post.updated_at, datetime)
            assert post.source_timestamp is not None
            assert isinstance(post.source_timestamp, datetime)

    def test_extract_entities_returns_empty_on_no_documents(self) -> None:
        """Test that extract_entities returns empty lists when no documents found."""
        from packages.ingest.readers.reddit import RedditReader

        with patch("packages.ingest.readers.reddit.LlamaRedditReader") as mock_reader_class:
            mock_reader_instance = MagicMock()
            mock_reader_instance.load_data.return_value = []
            mock_reader_class.return_value = mock_reader_instance

            reader = RedditReader(
                client_id="test-id", client_secret="test-secret", user_agent="test-agent"
            )
            entities = reader.extract_entities(subreddit="python", limit=1)

            assert entities["subreddits"] == []
            assert entities["posts"] == []
            assert entities["comments"] == []
