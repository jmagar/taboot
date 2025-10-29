"""Tests for YoutubeReader.

Tests YouTube transcript ingestion using LlamaIndex YoutubeTranscriptReader.
Following TDD methodology (RED-GREEN-REFACTOR).
"""

import pytest
from llama_index.core import Document


class TestYoutubeReader:
    """Tests for the YoutubeReader class."""

    def test_youtube_reader_loads_video_with_mock(self) -> None:
        """Test that YoutubeReader can load video transcript and extract entities.

        Updated for new API: load_data() now returns dict with entities,
        not list[Document]. Uses mocking to avoid API dependency.
        """
        from unittest.mock import MagicMock, patch

        from llama_index.core import Document

        from packages.ingest.readers.youtube import YoutubeReader

        # Mock LlamaIndex YoutubeTranscriptReader
        mock_doc = Document(text="Sample transcript", metadata={})

        with patch(
            "packages.ingest.readers.youtube.LlamaYoutubeReader"
        ) as mock_reader_class:
            mock_reader_instance = MagicMock()
            mock_reader_instance.load_data.return_value = [mock_doc]
            mock_reader_class.return_value = mock_reader_instance

            reader = YoutubeReader()
            result = reader.load_data(
                video_urls=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
            )

            # New API returns dict with entities
            assert isinstance(result, dict)
            assert "videos" in result
            assert "channels" in result
            assert "transcripts" in result
            assert len(result["videos"]) == 1
            assert len(result["channels"]) == 1
            assert len(result["transcripts"]) == 1

    def test_youtube_reader_extracts_entities_from_mock(self) -> None:
        """Test that YoutubeReader extracts Video, Channel, and Transcript entities.

        Integration test for T207: YouTubeReader should return structured entities
        instead of raw LlamaIndex Documents. Uses mocking to avoid API dependency.
        """
        from datetime import datetime
        from unittest.mock import MagicMock, patch

        from llama_index.core import Document

        from packages.ingest.readers.youtube import YoutubeReader
        from packages.schemas.youtube import Channel, Transcript, Video

        # Mock LlamaIndex YoutubeTranscriptReader
        mock_doc = Document(
            text="Never gonna give you up, never gonna let you down...",
            metadata={
                "video_id": "dQw4w9WgXcQ",
                "title": "Never Gonna Give You Up",
                "duration": 212,
                "views": 1400000000,
                "description": "Rick Astley - Never Gonna Give You Up",
                "language": "en",
                "channel_id": "UCuAXFkgsw1L7xaCfnd5JJOw",
                "channel_name": "Rick Astley",
                "channel_url": "https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw",
                "auto_generated": False,
            },
        )

        with patch(
            "packages.ingest.readers.youtube.LlamaYoutubeReader"
        ) as mock_reader_class:
            mock_reader_instance = MagicMock()
            mock_reader_instance.load_data.return_value = [mock_doc]
            mock_reader_class.return_value = mock_reader_instance

            reader = YoutubeReader()
            result = reader.load_data(
                video_urls=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
            )

            # Result should be a dict with entities, not list of Documents
            assert isinstance(result, dict)
            assert "videos" in result
            assert "channels" in result
            assert "transcripts" in result

            # Check Video entities
            videos = result["videos"]
            assert isinstance(videos, list)
            assert len(videos) == 1
            assert all(isinstance(v, Video) for v in videos)

            # Verify Video fields
            video = videos[0]
            assert video.video_id == "dQw4w9WgXcQ"
            assert video.title == "Never Gonna Give You Up"
            assert video.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            assert video.duration == 212
            assert video.views == 1400000000
            assert video.description == "Rick Astley - Never Gonna Give You Up"
            assert video.language == "en"
            assert isinstance(video.published_at, datetime)
            assert isinstance(video.created_at, datetime)
            assert isinstance(video.updated_at, datetime)
            assert video.extraction_tier == "A"
            assert video.extraction_method == "llamaindex_youtube_reader"
            assert video.confidence == 1.0
            assert video.extractor_version == "1.0.0"

            # Check Channel entities
            channels = result["channels"]
            assert isinstance(channels, list)
            assert len(channels) == 1
            assert all(isinstance(c, Channel) for c in channels)

            # Verify Channel fields
            channel = channels[0]
            assert channel.channel_id == "UCuAXFkgsw1L7xaCfnd5JJOw"
            assert channel.channel_name == "Rick Astley"
            assert (
                channel.channel_url
                == "https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw"
            )
            assert isinstance(channel.created_at, datetime)
            assert isinstance(channel.updated_at, datetime)
            assert channel.extraction_tier == "A"
            assert channel.extraction_method == "llamaindex_youtube_reader"
            assert channel.confidence == 1.0

            # Check Transcript entities
            transcripts = result["transcripts"]
            assert isinstance(transcripts, list)
            assert len(transcripts) == 1
            assert all(isinstance(t, Transcript) for t in transcripts)

            # Verify Transcript fields
            transcript = transcripts[0]
            assert transcript.video_id == "dQw4w9WgXcQ"
            assert transcript.transcript_id == "dQw4w9WgXcQ_en"
            assert transcript.language == "en"
            assert transcript.content == "Never gonna give you up, never gonna let you down..."
            assert transcript.auto_generated is False
            assert isinstance(transcript.created_at, datetime)
            assert isinstance(transcript.updated_at, datetime)
            assert transcript.extraction_tier == "A"
            assert transcript.extraction_method == "llamaindex_youtube_transcript"
            assert transcript.confidence == 1.0

    def test_youtube_reader_validates_url(self) -> None:
        """Test that YoutubeReader validates YouTube URL format."""
        from packages.ingest.readers.youtube import YoutubeReader

        reader = YoutubeReader()

        with pytest.raises(ValueError, match="Invalid YouTube URL"):
            reader.load_data(video_urls=["not-a-youtube-url"])

    def test_youtube_reader_handles_empty_urls(self) -> None:
        """Test that YoutubeReader rejects empty URL list."""
        from packages.ingest.readers.youtube import YoutubeReader

        reader = YoutubeReader()

        with pytest.raises(ValueError, match="video_urls"):
            reader.load_data(video_urls=[])

    def test_youtube_reader_loads_multiple_videos_with_mock(self) -> None:
        """Test that YoutubeReader can load multiple videos.

        Updated for new API: load_data() now returns dict with entities.
        Uses mocking to avoid API dependency.
        """
        from unittest.mock import MagicMock, patch

        from llama_index.core import Document

        from packages.ingest.readers.youtube import YoutubeReader

        # Mock LlamaIndex YoutubeTranscriptReader
        mock_docs = [
            Document(text="Transcript 1", metadata={}),
            Document(text="Transcript 2", metadata={}),
        ]

        with patch(
            "packages.ingest.readers.youtube.LlamaYoutubeReader"
        ) as mock_reader_class:
            mock_reader_instance = MagicMock()
            mock_reader_instance.load_data.return_value = mock_docs
            mock_reader_class.return_value = mock_reader_instance

            reader = YoutubeReader()
            result = reader.load_data(
                video_urls=[
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "https://www.youtube.com/watch?v=oHg5SJYRHA0",
                ]
            )

            # New API returns dict with entities
            assert isinstance(result, dict)
            assert len(result["videos"]) == 2
            assert len(result["channels"]) == 2
            assert len(result["transcripts"]) == 2

    def test_youtube_reader_entity_metadata(self) -> None:
        """Test that extracted entities include proper metadata.

        Updated for new API: verifies entity metadata instead of Document metadata.
        Uses mocking to avoid API dependency.
        """
        from unittest.mock import MagicMock, patch

        from llama_index.core import Document

        from packages.ingest.readers.youtube import YoutubeReader

        # Mock with metadata
        mock_doc = Document(
            text="Sample transcript",
            metadata={
                "title": "Test Video",
                "duration": 120,
                "language": "en",
            },
        )

        with patch(
            "packages.ingest.readers.youtube.LlamaYoutubeReader"
        ) as mock_reader_class:
            mock_reader_instance = MagicMock()
            mock_reader_instance.load_data.return_value = [mock_doc]
            mock_reader_class.return_value = mock_reader_instance

            reader = YoutubeReader()
            result = reader.load_data(
                video_urls=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
            )

            # Verify entity metadata
            video = result["videos"][0]
            assert video.title == "Test Video"
            assert video.duration == 120
            assert video.language == "en"
            assert video.extraction_tier == "A"
            assert video.confidence == 1.0
