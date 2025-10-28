"""End-to-end integration tests for external API ingestion.

Tests the full ingestion pipeline for external sources:
GitHub, Reddit, YouTube, Gmail, Elasticsearch.

These tests require:
- Docker services running (Qdrant, TEI, Firecrawl)
- Valid API credentials in .env
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from llama_index.core import Document as LlamaDocument

from packages.common.config import TabootConfig, get_config
from packages.ingest.chunker import Chunker
from packages.ingest.embedder import Embedder
from packages.ingest.normalizer import Normalizer
from packages.schemas.models import Chunk, SourceType
from packages.vector.writer import QdrantWriter

# Mark all tests in this module as integration tests
pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _normalize_documents(
    docs: Sequence[LlamaDocument], normalizer: Normalizer
) -> list[LlamaDocument]:
    """Normalize LlamaIndex documents while preserving metadata."""

    normalized: list[LlamaDocument] = []
    for doc in docs:
        metadata = doc.metadata.copy() if doc.metadata else {}
        normalized_text = normalizer.normalize(doc.text)
        normalized.append(LlamaDocument(text=normalized_text, metadata=metadata))
    return normalized


def _chunk_documents(
    docs: Sequence[LlamaDocument], *, chunker: Chunker, source_type: SourceType
) -> list[Chunk]:
    """Convert normalized documents into Chunk models for Qdrant writes."""

    chunks: list[Chunk] = []
    ingested_at = int(datetime.now(UTC).timestamp())
    for doc in docs:
        doc_id = uuid4()
        chunk_docs = chunker.chunk_document(doc)

        for index, chunk_doc in enumerate(chunk_docs):
            metadata = chunk_doc.metadata or {}
            source_url = str(
                metadata.get("source_url")
                or metadata.get("url")
                or metadata.get("source")
                or f"{source_type.value}://{doc_id}"
            )
            chunk = Chunk(
                chunk_id=uuid4(),
                doc_id=doc_id,
                content=chunk_doc.text,
                section=None,
                position=index,
                token_count=max(1, len(chunk_doc.text.split())),
                source_url=source_url,
                source_type=source_type,
                ingested_at=ingested_at,
                tags=None,
            )
            chunks.append(chunk)

    return chunks


def _run_pipeline(
    *,
    docs: Sequence[LlamaDocument],
    source_type: SourceType,
    config: TabootConfig,
) -> list[Chunk]:
    """Execute normalization, chunking, embedding, and Qdrant upsert."""

    normalizer = Normalizer()
    chunker = Chunker()
    embedder = Embedder(tei_url=config.tei_embedding_url)
    qdrant_writer = QdrantWriter(
        url=config.qdrant_url,
        collection_name=config.collection_name,
    )

    try:
        normalized_docs = _normalize_documents(docs, normalizer)
        chunks = _chunk_documents(normalized_docs, chunker=chunker, source_type=source_type)
        if not chunks:
            return []

        embeddings = embedder.embed_texts([chunk.content for chunk in chunks])
        qdrant_writer.upsert_batch(chunks=chunks, embeddings=embeddings)
        return chunks
    finally:
        embedder.close()
        qdrant_writer.close()


class TestGithubIngestionE2E:
    """E2E tests for GitHub ingestion."""

    @pytest.mark.github
    def test_github_ingestion_creates_chunks(self) -> None:
        """Test that GitHub ingestion creates chunks in Qdrant."""
        from packages.ingest.readers.github import GithubReader

        config = get_config()
        github_token = config.github_token.get_secret_value() if config.github_token else None
        if not github_token:
            pytest.skip("GitHub token not configured")

        github_reader = GithubReader(github_token=github_token)
        docs = github_reader.load_data(repo="anthropics/anthropic-sdk-python", limit=1)
        assert len(docs) >= 1

        chunks = _run_pipeline(docs=docs, source_type=SourceType.GITHUB, config=config)
        assert len(chunks) > 0


class TestRedditIngestionE2E:
    """E2E tests for Reddit ingestion."""

    @pytest.mark.reddit
    def test_reddit_ingestion_creates_chunks(self) -> None:
        """Test that Reddit ingestion creates chunks in Qdrant."""
        from packages.ingest.readers.reddit import RedditReader

        config = get_config()
        client_id = config.reddit_client_id
        client_secret = (
            config.reddit_client_secret.get_secret_value()
            if config.reddit_client_secret is not None
            else None
        )

        if not client_id or not client_secret:
            pytest.skip("Reddit credentials not configured")

        reddit_reader = RedditReader(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=config.reddit_user_agent,
        )

        docs = reddit_reader.load_data(subreddit="python", limit=1)
        assert len(docs) >= 1

        chunks = _run_pipeline(docs=docs, source_type=SourceType.REDDIT, config=config)
        assert len(chunks) > 0


class TestYoutubeIngestionE2E:
    """E2E tests for YouTube ingestion."""

    @pytest.mark.youtube
    def test_youtube_ingestion_creates_chunks(self) -> None:
        """Test that YouTube ingestion creates chunks in Qdrant."""
        from packages.ingest.readers.youtube import YoutubeReader

        config = get_config()
        youtube_reader = YoutubeReader()

        docs = youtube_reader.load_data(
            video_urls=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
        )
        assert len(docs) >= 1

        chunks = _run_pipeline(docs=docs, source_type=SourceType.YOUTUBE, config=config)
        assert len(chunks) > 0


class TestGmailIngestionE2E:
    """E2E tests for Gmail ingestion."""

    @pytest.mark.gmail
    def test_gmail_ingestion_creates_chunks(self) -> None:
        """Test that Gmail ingestion creates chunks in Qdrant."""
        from packages.ingest.readers.gmail import GmailReader

        config = get_config()
        credentials_path = getattr(config, "gmail_credentials_path", None)
        if not credentials_path:
            pytest.skip("Gmail credentials path not configured")

        gmail_reader = GmailReader(credentials_path=credentials_path)
        docs = gmail_reader.load_data(query="is:unread", limit=1)
        assert len(docs) >= 1

        chunks = _run_pipeline(docs=docs, source_type=SourceType.GMAIL, config=config)
        assert len(chunks) > 0


class TestElasticsearchIngestionE2E:
    """E2E tests for Elasticsearch ingestion."""

    @pytest.mark.elasticsearch
    def test_elasticsearch_ingestion_creates_chunks(self) -> None:
        """Test that Elasticsearch ingestion creates chunks in Qdrant."""
        from packages.ingest.readers.elasticsearch import ElasticsearchReader

        config = get_config()
        if not config.elasticsearch_url:
            pytest.skip("Elasticsearch endpoint not configured")

        elasticsearch_reader = ElasticsearchReader(
            endpoint=config.elasticsearch_url,
            index="test-index",
        )

        docs = elasticsearch_reader.load_data(query={"match_all": {}}, limit=1)
        assert len(docs) >= 1

        chunks = _run_pipeline(
            docs=docs,
            source_type=SourceType.ELASTICSEARCH,
            config=config,
        )
        assert len(chunks) > 0
