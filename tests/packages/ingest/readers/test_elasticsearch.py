"""Tests for ElasticsearchReader.

Tests Elasticsearch document ingestion using LlamaIndex ElasticsearchReader.
Following TDD methodology (RED-GREEN-REFACTOR).
"""

import pytest
from llama_index.core import Document


class TestElasticsearchReader:
    """Tests for the ElasticsearchReader class."""

    def test_elasticsearch_reader_loads_documents(self) -> None:
        """Test that ElasticsearchReader can load documents."""
        from packages.ingest.readers.elasticsearch import ElasticsearchReader

        reader = ElasticsearchReader(endpoint="http://localhost:9200", index="test-index")
        docs = reader.load_data(query={"match_all": {}}, limit=10)

        assert isinstance(docs, list)
        assert len(docs) <= 10
        assert all(isinstance(doc, Document) for doc in docs)

    def test_elasticsearch_reader_validates_endpoint(self) -> None:
        """Test that ElasticsearchReader validates endpoint."""
        from packages.ingest.readers.elasticsearch import ElasticsearchReader

        with pytest.raises(ValueError, match="endpoint"):
            ElasticsearchReader(endpoint="", index="test-index")

    def test_elasticsearch_reader_validates_index(self) -> None:
        """Test that ElasticsearchReader validates index name."""
        from packages.ingest.readers.elasticsearch import ElasticsearchReader

        with pytest.raises(ValueError, match="index"):
            ElasticsearchReader(endpoint="http://localhost:9200", index="")

    def test_elasticsearch_reader_respects_limit(self) -> None:
        """Test that ElasticsearchReader respects the limit parameter."""
        from packages.ingest.readers.elasticsearch import ElasticsearchReader

        reader = ElasticsearchReader(endpoint="http://localhost:9200", index="test-index")
        docs = reader.load_data(query={"match_all": {}}, limit=5)

        assert len(docs) <= 5

    def test_elasticsearch_reader_includes_metadata(self) -> None:
        """Test that ElasticsearchReader includes document metadata."""
        from packages.ingest.readers.elasticsearch import ElasticsearchReader

        reader = ElasticsearchReader(endpoint="http://localhost:9200", index="test-index")
        docs = reader.load_data(query={"match_all": {}}, limit=1)

        if docs:
            assert docs[0].metadata is not None
            assert "source_type" in docs[0].metadata
            assert docs[0].metadata["source_type"] == "elasticsearch"
