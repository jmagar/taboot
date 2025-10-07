from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest
from llama_index.core import Document as LlamaDocument
from llama_index.core.schema import TextNode

from llamacrawl.ingestion.pipeline import IngestionPipeline
from llamacrawl.models.document import Document, DocumentMetadata
from llamacrawl.readers.firecrawl import FirecrawlReader


class StubRedisClient:
    """Minimal Redis client stub for pipeline testing."""

    def __init__(self) -> None:
        self.dlq: list[dict[str, Any]] = []
        self.cursors: dict[str, str] = {}
        self.client = SimpleNamespace()  # placeholder for compatibility

    def push_to_dlq(self, *, source: str, doc_data: dict[str, Any], error: str) -> None:
        self.dlq.append({"source": source, "doc_data": doc_data, "error": error})

    def set_cursor(self, source: str, cursor: str) -> None:
        self.cursors[source] = cursor

    @contextmanager
    def with_lock(self, _key: str, ttl: int, blocking_timeout: int = 0) -> Any:  # noqa: ARG002
        yield "stub-lock"


class StubDeduplicator:
    """Returns all provided documents as new while tracking updates."""

    def __init__(self, *, remove_punctuation: bool = False, **_: Any) -> None:  # noqa: FBT002
        self.remove_punctuation = remove_punctuation
        self.updated: dict[str, list[str]] = defaultdict(list)

    def get_deduplicated_documents(
        self, source: str, documents: list[Document]
    ) -> tuple[list[Document], list[Document]]:
        # Upstream dedupe handles cross-run comparisons; intra-run dedupe is tested separately
        return documents, []

    def update_hashes_batch(self, source: str, documents: list[Document]) -> None:
        self.updated[source].extend(doc.doc_id for doc in documents)


class StubLlamaPipeline:
    """Stub for LlamaIndex ingestion pipeline capturing batch calls."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def run(
        self,
        documents: list[LlamaDocument],
        show_progress: bool = False,  # noqa: FBT001, ARG002
        num_workers: int | None = None,
    ) -> list[TextNode]:
        self.calls.append({"count": len(documents), "num_workers": num_workers})
        nodes: list[TextNode] = []
        for doc in documents:
            ref_doc_id = doc.metadata.get("doc_id")
            node = TextNode(text=doc.text, id_=f"node-{ref_doc_id}", ref_doc_id=ref_doc_id)
            node.embedding = [float(len(doc.text))]
            node.metadata = {"doc_id": ref_doc_id}
            nodes.append(node)
        return nodes


class StubEmbedding:
    def __init__(self, batch_size: int) -> None:
        self.embed_batch_size = batch_size


def _make_document(doc_id: str, content: str, url: str) -> Document:
    metadata = DocumentMetadata(
        source_type="firecrawl",
        source_url=url,
        timestamp=datetime.now(timezone.utc),
        extra={},
    )
    return Document(
        doc_id=doc_id,
        title=f"Title {doc_id}",
        content=content,
        content_hash=f"hash-{content}",
        metadata=metadata,
    )


@pytest.fixture
def stub_config() -> Any:
    ingestion = SimpleNamespace(
        chunk_size=256,
        chunk_overlap=32,
        batch_size=2,
        pipeline_workers=2,
        embedding_batch_size=8,
    )
    graph = SimpleNamespace(
        auto_extract_entities=False,
        extraction_model="stub-model",
        max_triplets_per_chunk=5,
        extraction_strategy="simple",
        entity_types=[],
        allowed_relation_types=None,
        allowed_entity_types=None,
        include_implicit_relations=False,
    )
    vector_store = SimpleNamespace(
        collection_name="stub-collection",
        upsert_batch_size=128,
        upsert_parallel=1,
        upsert_max_retries=1,
    )
    return SimpleNamespace(
        ingestion=ingestion,
        graph=graph,
        vector_store=vector_store,
        redis_url="redis://stub",
        ollama_url="http://ollama",
    )


def test_ingestion_batches_and_deduplicates(monkeypatch: pytest.MonkeyPatch, stub_config: Any) -> None:
    monkeypatch.setattr(
        "llamacrawl.ingestion.pipeline.IngestionPipeline._initialize_llama_pipeline",
        lambda self: None,
    )
    monkeypatch.setattr(
        "llamacrawl.ingestion.pipeline.DocumentDeduplicator",
        StubDeduplicator,
    )

    redis_client = StubRedisClient()
    qdrant_client = SimpleNamespace(collection_name="stub", client=SimpleNamespace())
    neo4j_client = SimpleNamespace()
    embed_model = StubEmbedding(batch_size=stub_config.ingestion.embedding_batch_size)

    pipeline = IngestionPipeline(
        config=stub_config,
        redis_client=redis_client,
        qdrant_client=qdrant_client,
        neo4j_client=neo4j_client,
        embed_model=embed_model,
    )

    stub_llama = StubLlamaPipeline()
    pipeline.llama_pipeline = stub_llama
    pipeline._extract_entities_to_neo4j = lambda *args, **kwargs: None

    docs = [
        _make_document("a", "alpha", "https://example.com/a"),
        _make_document("b", "beta", "https://example.com/b"),
        _make_document("c", "alpha", "https://example.com/c"),  # duplicate content
        _make_document("d", "delta", "https://example.com/d"),
    ]

    summary = pipeline.ingest_documents("firecrawl", docs)

    assert summary.total == 4
    # one duplicate removed inside the batch (content hash 'alpha')
    assert summary.processed == 3
    assert summary.deduplicated == 1
    # batch size is 2 so we expect two pipeline calls
    assert [call["count"] for call in stub_llama.calls] == [2, 1]
    assert all(call["num_workers"] == stub_config.ingestion.pipeline_workers for call in stub_llama.calls)


def test_firecrawl_reader_applies_filters_and_trims_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class StubFirecrawlSDK:
        def __init__(self, *, params: dict[str, Any], mode: str = "crawl", **_: Any) -> None:
            captured.setdefault("instances", []).append({"mode": mode, "params": params})

        def load_data(self, url: str | None = None, **_: Any) -> list[LlamaDocument]:  # noqa: ARG002
            metadata = {
                "url": url or "https://example.com",
                "title": "Example",
                "description": "desc",
                "keywords": ["very", "long", "keyword", "list", "for", "test"],
                "ogImage": "https://example.com/img.png",
                "redundant": "x" * 5000,
            }
            return [LlamaDocument(text="content", metadata=metadata)]

    monkeypatch.setattr(
        "llamacrawl.readers.firecrawl.FireCrawlWebReader",
        StubFirecrawlSDK,
    )

    reader = FirecrawlReader(
        source_name="firecrawl",
        config={
            "formats": ["markdown"],
            "include_paths": ["/docs/**"],
            "exclude_paths": ["/blog/**"],
            "concurrency": 5,
            "max_retries": 1,
            "retry_delay_ms": 500,
            "timeout_ms": 10000,
        },
        redis_client=StubRedisClient(),
    )

    docs = reader.load_data(url="https://example.com/start", mode="crawl", limit=10, max_depth=2)

    assert docs and docs[0].metadata.extra["firecrawl_metadata"]["description"] == "desc"
    trimmed_value = docs[0].metadata.extra["firecrawl_metadata"].get("redundant")
    assert isinstance(trimmed_value, str) and len(trimmed_value) <= reader.max_metadata_chars + 3

    params = captured["instances"][0]["params"]
    assert params["includePaths"] == ["/docs/**"]
    assert params["excludePaths"] == ["/blog/**"]
    assert params["concurrency"] == 5
    assert params["maxRetries"] == 1
    assert params["retryDelay"] == 500
    assert params["timeout"] == 10000
    assert params["scrape_options"]["formats"] == ["markdown"]
