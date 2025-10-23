"""Tests for YoutubeReader.

Tests YouTube transcript ingestion using LlamaIndex YoutubeTranscriptReader.
Following TDD methodology (RED-GREEN-REFACTOR).
"""

import pytest
from llama_index.core import Document


class TestYoutubeReader:
    """Tests for the YoutubeReader class."""

    def test_youtube_reader_loads_video(self) -> None:
        """Test that YoutubeReader can load video transcript."""
        from packages.ingest.readers.youtube import YoutubeReader

        reader = YoutubeReader()
        docs = reader.load_data(video_urls=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"])

        assert isinstance(docs, list)
        assert len(docs) >= 1
        assert all(isinstance(doc, Document) for doc in docs)

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

    def test_youtube_reader_loads_multiple_videos(self) -> None:
        """Test that YoutubeReader can load multiple videos."""
        from packages.ingest.readers.youtube import YoutubeReader

        reader = YoutubeReader()
        docs = reader.load_data(
            video_urls=[
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "https://www.youtube.com/watch?v=oHg5SJYRHA0",
            ]
        )

        assert isinstance(docs, list)
        assert len(docs) >= 2

    def test_youtube_reader_includes_metadata(self) -> None:
        """Test that YoutubeReader includes video metadata."""
        from packages.ingest.readers.youtube import YoutubeReader

        reader = YoutubeReader()
        docs = reader.load_data(video_urls=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"])

        if docs:
            assert docs[0].metadata is not None
            assert "source_type" in docs[0].metadata
            assert docs[0].metadata["source_type"] == "youtube"
