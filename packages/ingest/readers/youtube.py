"""YouTube transcript reader using LlamaIndex.

Implements YouTube video transcript ingestion via LlamaIndex YoutubeTranscriptReader.
Per research.md: Use LlamaIndex readers for standardized Document abstraction.

Extracts structured entities:
- Video: video_id, title, url, duration, views, published_at, description, language
- Channel: channel_id, channel_name, channel_url, subscribers, verified
- Transcript: transcript_id, video_id, language, auto_generated, content
"""

import logging
import re
from datetime import UTC, datetime

from llama_index.core import Document
from llama_index.readers.youtube_transcript import YoutubeTranscriptReader as LlamaYoutubeReader

from packages.schemas.youtube import Channel, Transcript, Video

logger = logging.getLogger(__name__)

EXTRACTOR_VERSION = "1.0.0"


class YoutubeReaderError(Exception):
    """Base exception for YoutubeReader errors."""

    pass


class YoutubeReader:
    """YouTube transcript reader using LlamaIndex YoutubeTranscriptReader.

    Implements ingestion of video transcripts from YouTube and extraction of
    structured entities (Video, Channel, Transcript).
    """

    def __init__(self, max_retries: int = 3) -> None:
        """Initialize YoutubeReader.

        Args:
            max_retries: Maximum number of retry attempts (default: 3).
        """
        self.max_retries = max_retries
        logger.info(f"Initialized YoutubeReader (max_retries={max_retries})")

    def load_data(
        self, video_urls: list[str]
    ) -> dict[str, list[Video] | list[Channel] | list[Transcript]]:
        """Load transcripts from YouTube videos and extract structured entities.

        Args:
            video_urls: List of YouTube video URLs (e.g., ['https://www.youtube.com/watch?v=...'])

        Returns:
            dict with keys:
                - "videos": list[Video] - Video entities
                - "channels": list[Channel] - Channel entities
                - "transcripts": list[Transcript] - Transcript entities

        Raises:
            ValueError: If video_urls is empty or contains invalid URLs.
            YoutubeReaderError: If loading fails after all retries.
        """
        if not video_urls:
            raise ValueError("video_urls cannot be empty")

        # Validate URLs and extract video IDs
        video_ids = []
        for url in video_urls:
            if not url.startswith(("https://www.youtube.com/", "https://youtu.be/")):
                raise ValueError(f"Invalid YouTube URL: {url}")
            video_id = self._extract_video_id(url)
            if not video_id:
                raise ValueError(f"Could not extract video ID from URL: {url}")
            video_ids.append(video_id)

        logger.info(f"Loading transcripts from {len(video_urls)} YouTube videos")

        # Create reader
        reader = LlamaYoutubeReader()

        # Retry logic
        last_error: Exception | None = None
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
                        doc.metadata["video_id"] = video_ids[i]

                logger.info(f"Loaded {len(docs)} transcript documents")

                # Extract entities from documents
                videos, channels, transcripts = self._extract_entities(docs, video_urls, video_ids)

                return {"videos": videos, "channels": channels, "transcripts": transcripts}

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    backoff = 2**attempt
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                        f"Retrying in {backoff}s..."
                    )
                else:
                    logger.error(f"All {self.max_retries} attempts failed: {e}")

        # All retries exhausted
        raise YoutubeReaderError(
            f"Failed to load YouTube videos after {self.max_retries} attempts"
        ) from last_error

    def _extract_video_id(self, url: str) -> str | None:
        """Extract video ID from YouTube URL.

        Args:
            url: YouTube video URL (e.g., 'https://www.youtube.com/watch?v=dQw4w9WgXcQ')

        Returns:
            str: Video ID or None if extraction fails.
        """
        # Pattern 1: https://www.youtube.com/watch?v=VIDEO_ID
        match = re.search(r"[?&]v=([^&]+)", url)
        if match:
            return match.group(1)

        # Pattern 2: https://youtu.be/VIDEO_ID
        match = re.search(r"youtu\.be/([^?]+)", url)
        if match:
            return match.group(1)

        return None

    def _extract_entities(
        self, docs: list[Document], video_urls: list[str], video_ids: list[str]
    ) -> tuple[list[Video], list[Channel], list[Transcript]]:
        """Extract Video, Channel, and Transcript entities from LlamaIndex documents.

        Args:
            docs: List of LlamaIndex Document objects with text and metadata.
            video_urls: Original list of video URLs.
            video_ids: Extracted video IDs.

        Returns:
            Tuple of (videos, channels, transcripts) entity lists.
        """
        videos: list[Video] = []
        channels: list[Channel] = []
        transcripts: list[Transcript] = []

        now = datetime.now(UTC)

        # Process each document
        for i, doc in enumerate(docs):
            video_id = video_ids[i] if i < len(video_ids) else ""
            video_url = video_urls[i] if i < len(video_urls) else ""

            # Extract video metadata (from Document metadata or defaults)
            metadata = doc.metadata or {}
            title = metadata.get("title", f"Video {video_id}")
            duration = metadata.get("duration", 0)
            views = metadata.get("views", 0)
            description = metadata.get("description")
            language = metadata.get("language", "en")
            published_at = metadata.get("published_at", now)

            # Convert published_at to datetime if needed
            if not isinstance(published_at, datetime):
                published_at = now

            # Create Video entity
            video = Video(
                video_id=video_id,
                title=title,
                url=video_url,
                duration=duration,
                views=views,
                published_at=published_at,
                description=description,
                language=language,
                created_at=now,
                updated_at=now,
                source_timestamp=published_at,
                extraction_tier="A",
                extraction_method="llamaindex_youtube_reader",
                confidence=1.0,
                extractor_version=EXTRACTOR_VERSION,
            )
            videos.append(video)

            # Extract channel metadata
            channel_id = metadata.get("channel_id", f"UCxxxxxxxx{i:08d}")
            channel_name = metadata.get("channel_name", "Unknown Channel")
            channel_url = metadata.get(
                "channel_url", f"https://www.youtube.com/channel/{channel_id}"
            )
            subscribers = metadata.get("subscribers")
            verified = metadata.get("verified", False)

            # Create Channel entity
            channel = Channel(
                channel_id=channel_id,
                channel_name=channel_name,
                channel_url=channel_url,
                subscribers=subscribers,
                verified=verified,
                created_at=now,
                updated_at=now,
                source_timestamp=None,
                extraction_tier="A",
                extraction_method="llamaindex_youtube_reader",
                confidence=1.0,
                extractor_version=EXTRACTOR_VERSION,
            )
            channels.append(channel)

            # Create Transcript entity
            transcript_id = f"{video_id}_{language}"
            auto_generated = metadata.get("auto_generated", True)
            content = doc.text or ""

            transcript = Transcript(
                transcript_id=transcript_id,
                video_id=video_id,
                language=language,
                auto_generated=auto_generated,
                content=content,
                created_at=now,
                updated_at=now,
                source_timestamp=None,
                extraction_tier="A",
                extraction_method="llamaindex_youtube_transcript",
                confidence=1.0,
                extractor_version=EXTRACTOR_VERSION,
            )
            transcripts.append(transcript)

        logger.info(
            f"Extracted {len(videos)} videos, {len(channels)} channels, "
            f"{len(transcripts)} transcripts"
        )

        return videos, channels, transcripts
