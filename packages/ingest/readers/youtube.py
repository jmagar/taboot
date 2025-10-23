"""YouTube transcript reader using LlamaIndex.

Implements YouTube video transcript ingestion via LlamaIndex YoutubeTranscriptReader.
Per research.md: Use LlamaIndex readers for standardized Document abstraction.
"""

import logging
from typing import Optional

from llama_index.core import Document
from llama_index.readers.youtube_transcript import YoutubeTranscriptReader as LlamaYoutubeReader

logger = logging.getLogger(__name__)


class YoutubeReaderError(Exception):
    """Base exception for YoutubeReader errors."""

    pass


class YoutubeReader:
    """YouTube transcript reader using LlamaIndex YoutubeTranscriptReader.

    Implements ingestion of video transcripts from YouTube.
    """

    def __init__(self, max_retries: int = 3) -> None:
        """Initialize YoutubeReader.

        Args:
            max_retries: Maximum number of retry attempts (default: 3).
        """
        self.max_retries = max_retries
        logger.info(f"Initialized YoutubeReader (max_retries={max_retries})")

    def load_data(self, video_urls: list[str]) -> list[Document]:
        """Load transcripts from YouTube videos.

        Args:
            video_urls: List of YouTube video URLs (e.g., ['https://www.youtube.com/watch?v=...'])

        Returns:
            list[Document]: List of LlamaIndex Document objects with text and metadata.

        Raises:
            ValueError: If video_urls is empty or contains invalid URLs.
            YoutubeReaderError: If loading fails after all retries.
        """
        if not video_urls:
            raise ValueError("video_urls cannot be empty")

        # Validate URLs
        for url in video_urls:
            if not url.startswith(("https://www.youtube.com/", "https://youtu.be/")):
                raise ValueError(f"Invalid YouTube URL: {url}")

        logger.info(f"Loading transcripts from {len(video_urls)} YouTube videos")

        # Create reader
        reader = LlamaYoutubeReader()

        # Retry logic
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                # Load transcripts
                docs = reader.load_data(ytlinks=video_urls)

                # Add metadata
                for i, doc in enumerate(docs):
                    if not doc.metadata:
                        doc.metadata = {}
                    doc.metadata["source_type"] = "youtube"
                    if i < len(video_urls):
                        doc.metadata["video_url"] = video_urls[i]

                logger.info(f"Loaded {len(docs)} transcript documents")
                return docs

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    backoff = 2**attempt
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                        f"Retrying in {backoff}s..."
                    )
                else:
                    logger.error(
                        f"All {self.max_retries} attempts failed: {e}"
                    )

        # All retries exhausted
        raise YoutubeReaderError(
            f"Failed to load YouTube videos after {self.max_retries} attempts"
        ) from last_error
