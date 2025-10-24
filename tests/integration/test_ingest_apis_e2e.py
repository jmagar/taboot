"""End-to-end integration tests for external API ingestion.

Tests the full ingestion pipeline for external sources:
GitHub, Reddit, YouTube, Gmail, Elasticsearch.

These tests require:
- Docker services running (Qdrant, TEI, Firecrawl)
- Valid API credentials in .env
"""

import pytest

# Mark all tests in this module as integration tests
pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestGithubIngestionE2E:
    """E2E tests for GitHub ingestion."""

    @pytest.mark.github
    def test_github_ingestion_creates_chunks(self) -> None:
        """Test that GitHub ingestion creates chunks in Qdrant."""
        from packages.common.config import get_config
        from packages.ingest.chunker import Chunker
        from packages.ingest.embedder import Embedder
        from packages.ingest.normalizer import Normalizer
        from packages.ingest.readers.github import GithubReader
        from packages.vector.writer import QdrantWriter

        config = get_config()

        # Create pipeline components
        github_reader = GithubReader(github_token=config.github_token)
        normalizer = Normalizer()
        chunker = Chunker()
        embedder = Embedder(tei_url=config.tei_embedding_url)
        qdrant_writer = QdrantWriter(
            url=config.qdrant_url,
            collection_name=config.collection_name,
        )

        # Load documents (limit to 1 to keep test fast)
        docs = github_reader.load_data(repo="anthropics/anthropic-sdk-python", limit=1)
        assert len(docs) >= 1

        # Normalize
        normalized_docs = [normalizer.normalize(doc.text) for doc in docs]

        # Chunk
        all_chunks = []
        for norm_doc in normalized_docs:
            all_chunks.extend(chunker.chunk(norm_doc))
        assert len(all_chunks) > 0

        # Embed
        embeddings = embedder.embed_texts([chunk.text for chunk in all_chunks])
        assert len(embeddings) == len(all_chunks)

        # Write to Qdrant
        qdrant_writer.upsert_batch(chunks=all_chunks, embeddings=embeddings)

        # Verify chunks were written (would need Qdrant query here)


class TestRedditIngestionE2E:
    """E2E tests for Reddit ingestion."""

    @pytest.mark.reddit
    def test_reddit_ingestion_creates_chunks(self) -> None:
        """Test that Reddit ingestion creates chunks in Qdrant."""
        from packages.common.config import get_config
        from packages.ingest.chunker import Chunker
        from packages.ingest.embedder import Embedder
        from packages.ingest.normalizer import Normalizer
        from packages.ingest.readers.reddit import RedditReader
        from packages.vector.writer import QdrantWriter

        config = get_config()

        reddit_reader = RedditReader(
            client_id=config.reddit_client_id,
            client_secret=config.reddit_client_secret,
            user_agent=config.reddit_user_agent,
        )
        normalizer = Normalizer()
        chunker = Chunker()
        embedder = Embedder(tei_url=config.tei_embedding_url)
        qdrant_writer = QdrantWriter(
            url=config.qdrant_url,
            collection_name=config.collection_name,
        )

        # Load posts (limit to 1 for speed)
        docs = reddit_reader.load_data(subreddit="python", limit=1)
        assert len(docs) >= 1

        # Process through pipeline
        normalized_docs = [normalizer.normalize(doc.text) for doc in docs]
        all_chunks = []
        for norm_doc in normalized_docs:
            all_chunks.extend(chunker.chunk(norm_doc))
        assert len(all_chunks) > 0

        embeddings = embedder.embed_texts([chunk.text for chunk in all_chunks])
        qdrant_writer.upsert_batch(chunks=all_chunks, embeddings=embeddings)


class TestYoutubeIngestionE2E:
    """E2E tests for YouTube ingestion."""

    @pytest.mark.youtube
    def test_youtube_ingestion_creates_chunks(self) -> None:
        """Test that YouTube ingestion creates chunks in Qdrant."""
        from packages.common.config import get_config
        from packages.ingest.chunker import Chunker
        from packages.ingest.embedder import Embedder
        from packages.ingest.normalizer import Normalizer
        from packages.ingest.readers.youtube import YoutubeReader
        from packages.vector.writer import QdrantWriter

        config = get_config()

        youtube_reader = YoutubeReader()
        normalizer = Normalizer()
        chunker = Chunker()
        embedder = Embedder(tei_url=config.tei_embedding_url)
        qdrant_writer = QdrantWriter(
            url=config.qdrant_url,
            collection_name=config.collection_name,
        )

        # Load transcript (using a short video for speed)
        docs = youtube_reader.load_data(video_urls=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"])
        assert len(docs) >= 1

        # Process through pipeline
        normalized_docs = [normalizer.normalize(doc.text) for doc in docs]
        all_chunks = []
        for norm_doc in normalized_docs:
            all_chunks.extend(chunker.chunk(norm_doc))
        assert len(all_chunks) > 0

        embeddings = embedder.embed_texts([chunk.text for chunk in all_chunks])
        qdrant_writer.upsert_batch(chunks=all_chunks, embeddings=embeddings)


class TestGmailIngestionE2E:
    """E2E tests for Gmail ingestion."""

    @pytest.mark.gmail
    def test_gmail_ingestion_creates_chunks(self) -> None:
        """Test that Gmail ingestion creates chunks in Qdrant."""
        from packages.common.config import get_config
        from packages.ingest.chunker import Chunker
        from packages.ingest.embedder import Embedder
        from packages.ingest.normalizer import Normalizer
        from packages.ingest.readers.gmail import GmailReader
        from packages.vector.writer import QdrantWriter

        config = get_config()

        gmail_reader = GmailReader(credentials_path=config.gmail_credentials_path)
        normalizer = Normalizer()
        chunker = Chunker()
        embedder = Embedder(tei_url=config.tei_embedding_url)
        qdrant_writer = QdrantWriter(
            url=config.qdrant_url,
            collection_name=config.collection_name,
        )

        # Load emails (limit to 1 for speed)
        docs = gmail_reader.load_data(query="is:unread", limit=1)
        assert len(docs) >= 1

        # Process through pipeline
        normalized_docs = [normalizer.normalize(doc.text) for doc in docs]
        all_chunks = []
        for norm_doc in normalized_docs:
            all_chunks.extend(chunker.chunk(norm_doc))
        assert len(all_chunks) > 0

        embeddings = embedder.embed_texts([chunk.text for chunk in all_chunks])
        qdrant_writer.upsert_batch(chunks=all_chunks, embeddings=embeddings)


class TestElasticsearchIngestionE2E:
    """E2E tests for Elasticsearch ingestion."""

    @pytest.mark.elasticsearch
    def test_elasticsearch_ingestion_creates_chunks(self) -> None:
        """Test that Elasticsearch ingestion creates chunks in Qdrant."""
        from packages.common.config import get_config
        from packages.ingest.chunker import Chunker
        from packages.ingest.embedder import Embedder
        from packages.ingest.normalizer import Normalizer
        from packages.ingest.readers.elasticsearch import ElasticsearchReader
        from packages.vector.writer import QdrantWriter

        config = get_config()

        elasticsearch_reader = ElasticsearchReader(
            endpoint=config.elasticsearch_url,
            index="test-index",
        )
        normalizer = Normalizer()
        chunker = Chunker()
        embedder = Embedder(tei_url=config.tei_embedding_url)
        qdrant_writer = QdrantWriter(
            url=config.qdrant_url,
            collection_name=config.collection_name,
        )

        # Load documents (limit to 1 for speed)
        docs = elasticsearch_reader.load_data(query={"match_all": {}}, limit=1)
        assert len(docs) >= 1

        # Process through pipeline
        normalized_docs = [normalizer.normalize(doc.text) for doc in docs]
        all_chunks = []
        for norm_doc in normalized_docs:
            all_chunks.extend(chunker.chunk(norm_doc))
        assert len(all_chunks) > 0

        embeddings = embedder.embed_texts([chunk.text for chunk in all_chunks])
        qdrant_writer.upsert_batch(chunks=all_chunks, embeddings=embeddings)
