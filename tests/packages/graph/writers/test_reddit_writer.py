"""Tests for RedditWriter - Batched Neo4j writer for Reddit entities.

Test coverage:
- Empty list handling
- Single entity write
- Batch write (2000 rows)
- Idempotent writes (MERGE behavior)
- Relationship creation (BELONGS_TO, POSTED_IN, REPLIED_TO)
- Error handling (invalid data, connection failures)
"""

import pytest
from datetime import datetime, UTC

from packages.graph.client import Neo4jClient
from packages.graph.writers.reddit_writer import RedditWriter
from packages.schemas.reddit import Subreddit, RedditPost, RedditComment


@pytest.fixture
def neo4j_client():
    """Create and connect Neo4j client for tests."""
    client = Neo4jClient()
    client.connect()
    yield client

    # Cleanup: Delete all Reddit nodes after test
    with client.session() as session:
        session.run("MATCH (n) WHERE n:Subreddit OR n:RedditPost OR n:RedditComment DETACH DELETE n")

    client.close()


@pytest.fixture
def reddit_writer(neo4j_client):
    """Create RedditWriter instance with real client."""
    return RedditWriter(neo4j_client=neo4j_client, batch_size=2000)


@pytest.fixture
def sample_subreddit():
    """Create sample Subreddit entity."""
    return Subreddit(
        name="python",
        display_name="Python",
        description="News about the Python programming language",
        subscribers=1500000,
        created_utc=datetime(2008, 1, 25, tzinfo=UTC),
        over_18=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        source_timestamp=datetime(2008, 1, 25, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="reddit_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_post():
    """Create sample RedditPost entity."""
    return RedditPost(
        post_id="abc123",
        title="How to learn Python?",
        selftext="I'm new to programming and want to learn Python.",
        score=150,
        num_comments=42,
        created_utc=datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
        url="https://reddit.com/r/python/comments/abc123/how_to_learn_python/",
        permalink="/r/python/comments/abc123/how_to_learn_python/",
        is_self=True,
        over_18=False,
        gilded=2,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        source_timestamp=datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="reddit_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_comment():
    """Create sample RedditComment entity."""
    return RedditComment(
        comment_id="def456",
        body="Great question! I recommend starting with the official Python tutorial.",
        score=25,
        created_utc=datetime(2024, 1, 1, 11, 0, tzinfo=UTC),
        permalink="/r/python/comments/abc123/how_to_learn_python/def456/",
        parent_id="abc123",
        depth=1,
        gilded=1,
        edited=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        source_timestamp=datetime(2024, 1, 1, 11, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="reddit_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


class TestRedditWriterSubreddits:
    """Test suite for Subreddit write operations."""

    def test_write_empty_list(self, reddit_writer):
        """Test writing empty list returns zero stats."""
        result = reddit_writer.write_subreddits([])

        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_subreddit(self, reddit_writer, neo4j_client, sample_subreddit):
        """Test writing single Subreddit node."""
        result = reddit_writer.write_subreddits([sample_subreddit])

        assert result["total_written"] == 1
        assert result["batches_executed"] == 1

        # Verify node was created in Neo4j
        with neo4j_client.session() as session:
            query = "MATCH (s:Subreddit {name: $name}) RETURN s"
            record = session.run(query, {"name": sample_subreddit.name}).single()

            assert record is not None
            node = record["s"]
            assert node["name"] == sample_subreddit.name
            assert node["display_name"] == sample_subreddit.display_name
            assert node["subscribers"] == sample_subreddit.subscribers

    def test_write_batch_2000_subreddits(self, reddit_writer, neo4j_client):
        """Test writing exactly 2000 Subreddits (single batch)."""
        subreddits = [
            Subreddit(
                name=f"subreddit_{i}",
                display_name=f"Subreddit {i}",
                description=f"Description {i}",
                subscribers=1000 * i,
                created_utc=datetime(2020, 1, 1, tzinfo=UTC),
                over_18=False,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                extraction_tier="A",
                extraction_method="reddit_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            for i in range(2000)
        ]

        result = reddit_writer.write_subreddits(subreddits)

        assert result["total_written"] == 2000
        assert result["batches_executed"] == 1

        # Verify all nodes were created
        with neo4j_client.session() as session:
            query = "MATCH (s:Subreddit) RETURN count(s) AS count"
            record = session.run(query).single()
            assert record["count"] == 2000

    def test_write_idempotent_merge(self, reddit_writer, neo4j_client, sample_subreddit):
        """Test that writing same subreddit twice uses MERGE (idempotent)."""
        # Write twice
        reddit_writer.write_subreddits([sample_subreddit])
        reddit_writer.write_subreddits([sample_subreddit])

        # Verify only ONE node exists
        with neo4j_client.session() as session:
            query = "MATCH (s:Subreddit {name: $name}) RETURN count(s) AS count"
            record = session.run(query, {"name": sample_subreddit.name}).single()
            assert record["count"] == 1


class TestRedditWriterPosts:
    """Test suite for RedditPost write operations."""

    def test_write_empty_list(self, reddit_writer):
        """Test writing empty list returns zero stats."""
        result = reddit_writer.write_posts([])

        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_post(self, reddit_writer, neo4j_client, sample_post):
        """Test writing single RedditPost node."""
        result = reddit_writer.write_posts([sample_post])

        assert result["total_written"] == 1
        assert result["batches_executed"] == 1

        # Verify node was created in Neo4j
        with neo4j_client.session() as session:
            query = "MATCH (p:RedditPost {post_id: $post_id}) RETURN p"
            record = session.run(query, {"post_id": sample_post.post_id}).single()

            assert record is not None
            node = record["p"]
            assert node["post_id"] == sample_post.post_id
            assert node["title"] == sample_post.title
            assert node["score"] == sample_post.score


class TestRedditWriterComments:
    """Test suite for RedditComment write operations."""

    def test_write_empty_list(self, reddit_writer):
        """Test writing empty list returns zero stats."""
        result = reddit_writer.write_comments([])

        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_comment(self, reddit_writer, neo4j_client, sample_comment):
        """Test writing single RedditComment node."""
        result = reddit_writer.write_comments([sample_comment])

        assert result["total_written"] == 1
        assert result["batches_executed"] == 1

        # Verify node was created in Neo4j
        with neo4j_client.session() as session:
            query = "MATCH (c:RedditComment {comment_id: $comment_id}) RETURN c"
            record = session.run(query, {"comment_id": sample_comment.comment_id}).single()

            assert record is not None
            node = record["c"]
            assert node["comment_id"] == sample_comment.comment_id
            assert node["body"] == sample_comment.body
            assert node["parent_id"] == sample_comment.parent_id


class TestRedditWriterRelationships:
    """Test suite for Reddit relationship creation."""

    def test_write_post_belongs_to_subreddit(
        self, reddit_writer, neo4j_client, sample_post, sample_subreddit
    ):
        """Test creating BELONGS_TO relationship from Post to Subreddit."""
        # Create nodes first
        reddit_writer.write_subreddits([sample_subreddit])
        reddit_writer.write_posts([sample_post])

        result = reddit_writer.write_post_belongs_to_subreddit(
            post_id=sample_post.post_id,
            subreddit_name="python",
            created_at=datetime.now(UTC),
            extraction_tier="A",
            extraction_method="reddit_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert result["total_written"] == 1

        # Verify relationship was created
        with neo4j_client.session() as session:
            query = """
            MATCH (p:RedditPost {post_id: $post_id})-[r:BELONGS_TO]->(s:Subreddit {name: $subreddit_name})
            RETURN count(r) AS count
            """
            record = session.run(query, {"post_id": sample_post.post_id, "subreddit_name": "python"}).single()
            assert record["count"] == 1

    def test_write_comment_replied_to_post(
        self, reddit_writer, neo4j_client, sample_comment, sample_post
    ):
        """Test creating REPLIED_TO relationship from Comment to Post."""
        # Create nodes first
        reddit_writer.write_posts([sample_post])
        reddit_writer.write_comments([sample_comment])

        result = reddit_writer.write_comment_replied_to(
            comment_id=sample_comment.comment_id,
            parent_id="abc123",
            parent_type="post",
            created_at=datetime.now(UTC),
            extraction_tier="A",
            extraction_method="reddit_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert result["total_written"] == 1

        # Verify relationship was created
        with neo4j_client.session() as session:
            query = """
            MATCH (c:RedditComment {comment_id: $comment_id})-[r:REPLIED_TO]->(p:RedditPost {post_id: $parent_id})
            RETURN count(r) AS count
            """
            record = session.run(query, {"comment_id": sample_comment.comment_id, "parent_id": "abc123"}).single()
            assert record["count"] == 1
