"""IngestYouTubeUseCase - Core orchestration for YouTube video ingestion.

Orchestrates the complete ingestion pipeline:
YoutubeReader → Normalizer → Chunker → Embedder → QdrantWriter
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from llama_index.core import Document as LlamaDocument

from packages.ingest.chunker import Chunker
from packages.ingest.embedder import Embedder
from packages.ingest.normalizer import Normalizer
from packages.ingest.readers.youtube import YoutubeReader
from packages.schemas.models import Chunk, SourceType
from packages.vector.writer import QdrantWriter

logger = logging.getLogger(__name__)


class IngestYouTubeUseCase:
    """Use case for ingesting YouTube video transcripts into Qdrant vector store.

    Orchestrates the full ingestion pipeline with error handling.
    NO framework dependencies - only imports from adapter packages.

    Attributes:
        youtube_reader: YoutubeReader adapter for loading transcripts.
        normalizer: Normalizer adapter for text normalization.
        chunker: Chunker adapter for semantic chunking.
        embedder: Embedder adapter for text embedding.
        qdrant_writer: QdrantWriter adapter for vector storage.
    """

    def __init__(
        self,
        youtube_reader: YoutubeReader,
        normalizer: Normalizer,
        chunker: Chunker,
        embedder: Embedder,
        qdrant_writer: QdrantWriter,
    ) -> None:
        """Initialize IngestYouTubeUseCase with all dependencies.

        Args:
            youtube_reader: YoutubeReader instance for loading transcripts.
            normalizer: Normalizer instance for text normalization.
            chunker: Chunker instance for semantic chunking.
            embedder: Embedder instance for text embedding.
            qdrant_writer: QdrantWriter instance for vector storage.
        """
        self.youtube_reader = youtube_reader
        self.normalizer = normalizer
        self.chunker = chunker
        self.embedder = embedder
        self.qdrant_writer = qdrant_writer

        logger.info("Initialized IngestYouTubeUseCase")

    def execute(self, urls: list[str]) -> dict[str, int]:
        """Execute the full ingestion pipeline for YouTube video URLs.

        Pipeline flow:
        1. YoutubeReader.load_data(urls) → docs[]
        2. For each doc:
           a. Normalizer.normalize(doc.text) → markdown
           b. Chunker.chunk_document(markdown_doc) → chunks[]
        3. Embedder.embed_texts([chunk.text for all chunks]) → embeddings[]
        4. QdrantWriter.upsert_batch(chunks, embeddings)
        5. Return stats

        Args:
            urls: List of YouTube video URLs to ingest.

        Returns:
            dict: Statistics with keys:
                - videos_processed: Number of videos processed
                - chunks_created: Total number of chunks created

        Raises:
            ConnectionError: If YouTube API or vector store connection fails.
            ValueError: If invalid YouTube URL provided.
        """
        logger.info(f"Starting YouTube ingestion for {len(urls)} video(s)")

        # Step 1: Load transcripts
        docs = self.youtube_reader.load_data(video_urls=urls)
        logger.info(f"Loaded {len(docs)} transcripts")

        if not docs:
            logger.info("No transcripts to process")
            return {"videos_processed": 0, "chunks_created": 0}

        # Step 2: Process each document
        all_chunks: list[Chunk] = []
        for doc in docs:
            chunks = self._process_document(doc)
            all_chunks.extend(chunks)

        logger.info(f"Created {len(all_chunks)} chunks from {len(docs)} videos")

        # Step 3: Embed all chunks in batch
        if all_chunks:
            logger.info(f"Embedding {len(all_chunks)} chunks")
            chunk_texts = [chunk.content for chunk in all_chunks]
            embeddings = self.embedder.embed_texts(chunk_texts)

            # Step 4: Upsert to Qdrant
            logger.info(f"Upserting {len(all_chunks)} chunks to Qdrant")
            self.qdrant_writer.upsert_batch(all_chunks, embeddings)

        logger.info(f"Completed YouTube ingestion: {len(docs)} videos, {len(all_chunks)} chunks")

        return {"videos_processed": len(docs), "chunks_created": len(all_chunks)}

    def _process_document(self, doc: LlamaDocument) -> list[Chunk]:
        """Process a single YouTube video document through the pipeline.

        Args:
            doc: LlamaDocument containing video transcript.

        Returns:
            list[Chunk]: Processed chunks with metadata.
        """
        # Step 2a: Normalize text to Markdown
        markdown = self.normalizer.normalize(doc.text)

        # Filter metadata to only essential fields needed for chunking/retrieval
        # This prevents LlamaIndex SentenceSplitter from failing when metadata
        # serialization exceeds chunk_size (512 tokens)
        filtered_metadata = {}
        if doc.metadata:
            # Only keep fields that are: (1) needed for retrieval or (2) small
            allowed_keys = {"video_url", "title", "channel", "duration"}
            filtered_metadata = {
                k: v for k, v in doc.metadata.items()
                if k in allowed_keys and isinstance(v, (str, int, float, bool))
            }

        # Create a new Document with normalized text
        normalized_doc = LlamaDocument(
            text=markdown,
            metadata=filtered_metadata,
        )

        # Step 2b: Chunk the normalized document
        chunk_docs = self.chunker.chunk_document(normalized_doc)

        # Convert LlamaIndex Documents to Chunk models
        chunks: list[Chunk] = []
        doc_id = uuid4()  # One doc_id per video
        ingested_at = int(datetime.now(UTC).timestamp())
        source_url = doc.metadata.get("video_url", "") if doc.metadata else ""

        for chunk_doc in chunk_docs:
            # Extract metadata
            chunk_index = chunk_doc.metadata.get("chunk_index", 0)

            # Calculate token count (rough estimate: split by whitespace)
            token_count = len(chunk_doc.text.split())
            token_count = max(1, min(token_count, 512))  # Clamp to [1, 512]

            # Create Chunk model
            chunk = Chunk(
                chunk_id=uuid4(),
                doc_id=doc_id,
                content=chunk_doc.text,
                section=None,
                position=chunk_index,
                token_count=token_count,
                source_url=source_url,
                source_type=SourceType.YOUTUBE,
                ingested_at=ingested_at,
                tags=None,
            )
            chunks.append(chunk)

        return chunks


# Export public API
__all__ = ["IngestYouTubeUseCase"]
