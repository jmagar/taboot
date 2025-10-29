"""Tests for YouTubeWriter - Batched Neo4j writer for YouTube entities.

Test coverage:
- Empty list handling
- Single entity write
- Batch write (2000 rows)
- Idempotent writes (MERGE behavior)
- Relationship creation (UPLOADED_BY, HAS_TRANSCRIPT)
"""

import pytest
from datetime import datetime, UTC

from packages.graph.client import Neo4jClient
from packages.graph.writers.youtube_writer import YouTubeWriter
from packages.schemas.youtube import Video, Channel, Transcript


@pytest.fixture
def neo4j_client():
    """Create and connect Neo4j client for tests."""
    client = Neo4jClient()
    client.connect()
    yield client

    # Cleanup: Delete all YouTube nodes after test
    with client.session() as session:
        session.run("MATCH (n) WHERE n:Channel OR n:Video OR n:Transcript DETACH DELETE n")

    client.close()


@pytest.fixture
def youtube_writer(neo4j_client):
    """Create YouTubeWriter instance with real client."""
    return YouTubeWriter(neo4j_client=neo4j_client, batch_size=2000)


@pytest.fixture
def sample_channel():
    """Create sample Channel entity."""
    return Channel(
        channel_id="UCxxxxxxxxxxxxx",
        channel_name="Tech Channel",
        channel_url="https://www.youtube.com/channel/UCxxxxxxxxxxxxx",
        subscribers=1000000,
        verified=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="youtube_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_video():
    """Create sample Video entity."""
    return Video(
        video_id="dQw4w9WgXcQ",
        title="Never Gonna Give You Up",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        duration=212,
        views=1400000000,
        published_at=datetime(2009, 10, 25, tzinfo=UTC),
        description="Rick Astley - Never Gonna Give You Up",
        language="en",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        source_timestamp=datetime(2009, 10, 25, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="youtube_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_transcript():
    """Create sample Transcript entity."""
    return Transcript(
        transcript_id="dQw4w9WgXcQ_en",
        video_id="dQw4w9WgXcQ",
        language="en",
        auto_generated=False,
        content="Never gonna give you up, never gonna let you down...",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="youtube_transcript_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


class TestYouTubeWriterChannels:
    """Test suite for Channel write operations."""

    def test_write_empty_list(self, youtube_writer):
        """Test writing empty list returns zero stats."""
        result = youtube_writer.write_channels([])

        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_channel(self, youtube_writer, neo4j_client, sample_channel):
        """Test writing single Channel node."""
        result = youtube_writer.write_channels([sample_channel])

        assert result["total_written"] == 1
        assert result["batches_executed"] == 1

        # Verify node was created in Neo4j
        with neo4j_client.session() as session:
            query = "MATCH (c:Channel {channel_id: $channel_id}) RETURN c"
            record = session.run(query, {"channel_id": sample_channel.channel_id}).single()

            assert record is not None
            node = record["c"]
            assert node["channel_id"] == sample_channel.channel_id
            assert node["channel_name"] == sample_channel.channel_name
            assert node["subscribers"] == sample_channel.subscribers
            assert node["verified"] == sample_channel.verified

    def test_write_batch_2000_channels(self, youtube_writer, neo4j_client):
        """Test writing exactly 2000 Channels (single batch)."""
        channels = [
            Channel(
                channel_id=f"UCxxxxxxxxxxxx{i:04d}",
                channel_name=f"Channel {i}",
                channel_url=f"https://www.youtube.com/channel/UCxxxxxxxxxxxx{i:04d}",
                subscribers=1000 * i,
                verified=i % 2 == 0,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                extraction_tier="A",
                extraction_method="youtube_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            for i in range(2000)
        ]

        result = youtube_writer.write_channels(channels)

        assert result["total_written"] == 2000
        assert result["batches_executed"] == 1

        # Verify all nodes were created
        with neo4j_client.session() as session:
            query = "MATCH (c:Channel) RETURN count(c) AS count"
            record = session.run(query).single()
            assert record["count"] == 2000

    def test_write_idempotent_merge(self, youtube_writer, neo4j_client, sample_channel):
        """Test that writing same channel twice uses MERGE (idempotent)."""
        # Write twice
        youtube_writer.write_channels([sample_channel])
        youtube_writer.write_channels([sample_channel])

        # Verify only ONE node exists
        with neo4j_client.session() as session:
            query = "MATCH (c:Channel {channel_id: $channel_id}) RETURN count(c) AS count"
            record = session.run(query, {"channel_id": sample_channel.channel_id}).single()
            assert record["count"] == 1


class TestYouTubeWriterVideos:
    """Test suite for Video write operations."""

    def test_write_empty_list(self, youtube_writer):
        """Test writing empty list returns zero stats."""
        result = youtube_writer.write_videos([])

        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_video(self, youtube_writer, neo4j_client, sample_video):
        """Test writing single Video node."""
        result = youtube_writer.write_videos([sample_video])

        assert result["total_written"] == 1
        assert result["batches_executed"] == 1

        # Verify node was created in Neo4j
        with neo4j_client.session() as session:
            query = "MATCH (v:Video {video_id: $video_id}) RETURN v"
            record = session.run(query, {"video_id": sample_video.video_id}).single()

            assert record is not None
            node = record["v"]
            assert node["video_id"] == sample_video.video_id
            assert node["title"] == sample_video.title
            assert node["duration"] == sample_video.duration
            assert node["views"] == sample_video.views


class TestYouTubeWriterTranscripts:
    """Test suite for Transcript write operations."""

    def test_write_empty_list(self, youtube_writer):
        """Test writing empty list returns zero stats."""
        result = youtube_writer.write_transcripts([])

        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_transcript(self, youtube_writer, neo4j_client, sample_transcript):
        """Test writing single Transcript node."""
        result = youtube_writer.write_transcripts([sample_transcript])

        assert result["total_written"] == 1
        assert result["batches_executed"] == 1

        # Verify node was created in Neo4j
        with neo4j_client.session() as session:
            query = "MATCH (t:Transcript {transcript_id: $transcript_id}) RETURN t"
            record = session.run(query, {"transcript_id": sample_transcript.transcript_id}).single()

            assert record is not None
            node = record["t"]
            assert node["transcript_id"] == sample_transcript.transcript_id
            assert node["video_id"] == sample_transcript.video_id
            assert node["language"] == sample_transcript.language
            assert node["auto_generated"] == sample_transcript.auto_generated


class TestYouTubeWriterRelationships:
    """Test suite for YouTube relationship creation."""

    def test_write_video_uploaded_by_channel(
        self, youtube_writer, neo4j_client, sample_video, sample_channel
    ):
        """Test creating UPLOADED_BY relationship from Video to Channel."""
        # Create nodes first
        youtube_writer.write_channels([sample_channel])
        youtube_writer.write_videos([sample_video])

        result = youtube_writer.write_video_uploaded_by_channel(
            video_id=sample_video.video_id,
            channel_id="UCxxxxxxxxxxxxx",
            created_at=datetime.now(UTC),
            extraction_tier="A",
            extraction_method="youtube_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert result["total_written"] == 1

        # Verify relationship was created
        with neo4j_client.session() as session:
            query = """
            MATCH (v:Video {video_id: $video_id})-[r:UPLOADED_BY]->(c:Channel {channel_id: $channel_id})
            RETURN count(r) AS count
            """
            record = session.run(query, {"video_id": sample_video.video_id, "channel_id": "UCxxxxxxxxxxxxx"}).single()
            assert record["count"] == 1

    def test_write_video_has_transcript(
        self, youtube_writer, neo4j_client, sample_video, sample_transcript
    ):
        """Test creating HAS_TRANSCRIPT relationship from Video to Transcript."""
        # Create nodes first
        youtube_writer.write_videos([sample_video])
        youtube_writer.write_transcripts([sample_transcript])

        result = youtube_writer.write_video_has_transcript(
            video_id=sample_transcript.video_id,
            transcript_id=sample_transcript.transcript_id,
            created_at=datetime.now(UTC),
            extraction_tier="A",
            extraction_method="youtube_transcript_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert result["total_written"] == 1

        # Verify relationship was created
        with neo4j_client.session() as session:
            query = """
            MATCH (v:Video {video_id: $video_id})-[r:HAS_TRANSCRIPT]->(t:Transcript {transcript_id: $transcript_id})
            RETURN count(r) AS count
            """
            record = session.run(query, {"video_id": sample_transcript.video_id, "transcript_id": sample_transcript.transcript_id}).single()
            assert record["count"] == 1
