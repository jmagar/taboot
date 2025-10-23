"""Tests for GithubReader.

Tests GitHub repository ingestion using LlamaIndex GithubRepositoryReader.
Following TDD methodology (RED-GREEN-REFACTOR).
"""

import pytest
from llama_index.core import Document


class TestGithubReader:
    """Tests for the GithubReader class."""

    def test_github_reader_loads_repo(self) -> None:
        """Test that GithubReader can load a repository."""
        from packages.ingest.readers.github import GithubReader

        reader = GithubReader(github_token="test-token")
        docs = reader.load_data(repo="owner/repo", limit=10)

        assert isinstance(docs, list)
        assert len(docs) <= 10
        assert all(isinstance(doc, Document) for doc in docs)

    def test_github_reader_validates_repo_format(self) -> None:
        """Test that GithubReader validates repo format (owner/repo)."""
        from packages.ingest.readers.github import GithubReader

        reader = GithubReader(github_token="test-token")

        with pytest.raises(ValueError, match="Invalid repository format"):
            reader.load_data(repo="invalid-repo", limit=10)

    def test_github_reader_handles_empty_repo(self) -> None:
        """Test that GithubReader rejects empty repo."""
        from packages.ingest.readers.github import GithubReader

        reader = GithubReader(github_token="test-token")

        with pytest.raises(ValueError, match="repository"):
            reader.load_data(repo="", limit=10)

    def test_github_reader_requires_token(self) -> None:
        """Test that GithubReader requires github_token parameter."""
        from packages.ingest.readers.github import GithubReader

        with pytest.raises(ValueError, match="github_token"):
            GithubReader(github_token="")

    def test_github_reader_respects_limit(self) -> None:
        """Test that GithubReader respects the limit parameter."""
        from packages.ingest.readers.github import GithubReader

        reader = GithubReader(github_token="test-token")
        docs = reader.load_data(repo="owner/repo", limit=5)

        assert len(docs) <= 5

    def test_github_reader_includes_metadata(self) -> None:
        """Test that GithubReader includes repository metadata."""
        from packages.ingest.readers.github import GithubReader

        reader = GithubReader(github_token="test-token")
        docs = reader.load_data(repo="owner/repo", limit=1)

        if docs:
            assert docs[0].metadata is not None
            assert "source_type" in docs[0].metadata
            assert docs[0].metadata["source_type"] == "github"
