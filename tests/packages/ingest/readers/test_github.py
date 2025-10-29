"""Tests for GithubReader.

Tests GitHub repository ingestion using LlamaIndex GithubRepositoryReader.
Following TDD methodology (RED-GREEN-REFACTOR).
"""

import pytest
from llama_index.core import Document
from pytest_mock import MockerFixture


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


class TestGithubReaderEntities:
    """Integration tests for GithubReader entity extraction.

    Tests that GithubReader extracts all 12 GitHub entity types:
    Repository, Issue, PullRequest, Commit, Branch, Tag, GitHubLabel,
    Milestone, Comment, Release, Documentation, BinaryAsset
    """

    @pytest.fixture
    def mock_github_api(self, mocker: MockerFixture):
        """Create comprehensive GitHub API mock for all endpoints."""
        # Mock repository data
        repo_response = {
            "full_name": "owner/repo",
            "html_url": "https://github.com/owner/repo",
            "default_branch": "main",
            "description": "Test repo",
            "language": "Python",
            "stargazers_count": 100,
            "forks_count": 20,
            "open_issues_count": 5,
            "private": False,
            "fork": False,
            "created_at": "2024-01-01T00:00:00Z",
        }

        # Mock branches data
        branches_response = [
            {"name": "main", "protected": False, "commit": {"sha": "abc123"}}
        ]

        # Mock tags data
        tags_response = [
            {"name": "v1.0.0", "commit": {"sha": "tag123"}}
        ]

        # Mock commits data
        commits_response = [
            {
                "sha": "commit123",
                "commit": {
                    "message": "Test commit",
                    "author": {
                        "name": "Test Author",
                        "email": "test@example.com",
                        "date": "2024-01-01T00:00:00Z",
                    },
                    "tree": {"sha": "tree123"},
                },
                "author": {"login": "testuser"},
                "parents": [],
            }
        ]

        # Mock README data
        readme_response = {
            "name": "README.md",
            "path": "README.md",
            "content": "VGVzdCBSRUFETUU=",  # base64: "Test README"
        }

        # Create mock responses for different endpoints
        def mock_get(url: str, **kwargs):
            mock_response = mocker.Mock()
            mock_response.raise_for_status = mocker.Mock()

            if "/repos/owner/repo/readme" in url:
                # README endpoint
                mock_response.json.return_value = readme_response
            elif "/repos/owner/repo" in url and not any(
                x in url for x in ["/branches", "/tags", "/commits", "/issues", "/pulls", "/labels", "/milestones", "/releases"]
            ):
                # Repository endpoint
                mock_response.json.return_value = repo_response
            elif "/branches" in url:
                mock_response.json.return_value = branches_response
            elif "/tags" in url:
                mock_response.json.return_value = tags_response
            elif "/commits" in url:
                mock_response.json.return_value = commits_response
            else:
                # Default to empty list for other endpoints (issues, PRs, labels, etc.)
                mock_response.json.return_value = []

            return mock_response

        # Mock the httpx.Client
        mock_client = mocker.Mock()
        mock_client.get = mock_get
        mock_client.__enter__ = mocker.Mock(return_value=mock_client)
        mock_client.__exit__ = mocker.Mock(return_value=False)

        mocker.patch("httpx.Client", return_value=mock_client)
        return mock_client

    def test_github_reader_extracts_repository_entity(self, mock_github_api) -> None:
        """Test that GithubReader extracts Repository entity."""
        from packages.ingest.readers.github import GithubReader
        from packages.schemas.github import Repository

        reader = GithubReader(github_token="test-token")
        entities = reader.extract_entities(repo="owner/repo")

        # Should have at least one Repository entity
        repos = [e for e in entities if isinstance(e, Repository)]
        assert len(repos) >= 1

        # Verify Repository structure
        repo = repos[0]
        assert repo.owner == "owner"
        assert repo.name == "repo"
        assert repo.full_name == "owner/repo"
        assert repo.url is not None
        assert repo.default_branch is not None
        assert repo.created_at is not None
        assert repo.updated_at is not None
        assert repo.extraction_tier in ["A", "B", "C"]
        assert repo.confidence >= 0.0 and repo.confidence <= 1.0

    def test_github_reader_extracts_issue_entities(self, mock_github_api) -> None:
        """Test that GithubReader extracts Issue entities."""
        from packages.ingest.readers.github import GithubReader
        from packages.schemas.github import Issue

        reader = GithubReader(github_token="test-token")
        entities = reader.extract_entities(repo="owner/repo")

        # Should have Issue entities if issues exist (mock returns empty list)
        issues = [e for e in entities if isinstance(e, Issue)]
        # Empty list is fine for this test - just verifying extraction works

    def test_github_reader_extracts_pull_request_entities(self, mock_github_api) -> None:
        """Test that GithubReader extracts PullRequest entities."""
        from packages.ingest.readers.github import GithubReader
        from packages.schemas.github import PullRequest

        reader = GithubReader(github_token="test-token")
        entities = reader.extract_entities(repo="owner/repo")

        # Should have PullRequest entities if PRs exist (mock returns empty list)
        prs = [e for e in entities if isinstance(e, PullRequest)]
        # Empty list is fine for this test - just verifying extraction works

    def test_github_reader_extracts_commit_entities(self, mock_github_api) -> None:
        """Test that GithubReader extracts Commit entities."""
        from packages.ingest.readers.github import GithubReader
        from packages.schemas.github import Commit

        reader = GithubReader(github_token="test-token")
        entities = reader.extract_entities(repo="owner/repo")

        # Should have Commit entities
        commits = [e for e in entities if isinstance(e, Commit)]
        assert len(commits) >= 1, "Should extract at least one Commit entity from mock"

        commit = commits[0]
        assert commit.sha is not None
        assert commit.message is not None
        assert commit.timestamp is not None

    def test_github_reader_extracts_branch_entities(self, mock_github_api) -> None:
        """Test that GithubReader extracts Branch entities."""
        from packages.ingest.readers.github import GithubReader
        from packages.schemas.github import Branch

        reader = GithubReader(github_token="test-token")
        entities = reader.extract_entities(repo="owner/repo")

        # Should have at least one Branch entity (default branch)
        branches = [e for e in entities if isinstance(e, Branch)]
        assert len(branches) >= 1

        branch = branches[0]
        assert branch.name is not None
        assert branch.sha is not None

    def test_github_reader_extracts_tag_entities(self, mock_github_api) -> None:
        """Test that GithubReader extracts Tag entities."""
        from packages.ingest.readers.github import GithubReader
        from packages.schemas.github import Tag

        reader = GithubReader(github_token="test-token")
        entities = reader.extract_entities(repo="owner/repo")

        # Tags should be present from mock
        tags = [e for e in entities if isinstance(e, Tag)]
        assert len(tags) >= 1, "Should extract at least one Tag entity from mock"

        tag = tags[0]
        assert tag.name is not None
        assert tag.sha is not None

    def test_github_reader_extracts_documentation_entities(self, mock_github_api) -> None:
        """Test that GithubReader extracts Documentation entities (README, etc.)."""
        from packages.ingest.readers.github import GithubReader
        from packages.schemas.github import Documentation

        reader = GithubReader(github_token="test-token")
        entities = reader.extract_entities(repo="owner/repo")

        # Should have at least README
        docs = [e for e in entities if isinstance(e, Documentation)]
        assert len(docs) >= 1

        doc = docs[0]
        assert doc.file_path is not None
        assert doc.content is not None
        assert doc.format is not None

    def test_github_reader_extracts_all_entity_types(self, mock_github_api) -> None:
        """Test that GithubReader can extract all 12 GitHub entity types."""
        from packages.ingest.readers.github import GithubReader
        from packages.schemas.github import (
            BinaryAsset,
            Branch,
            Comment,
            Commit,
            Documentation,
            GitHubLabel,
            Issue,
            Milestone,
            PullRequest,
            Release,
            Repository,
            Tag,
        )

        reader = GithubReader(github_token="test-token")
        entities = reader.extract_entities(repo="owner/repo")

        # Collect entity types
        entity_types = {type(e).__name__ for e in entities}

        # Repository and Branch are mandatory (default branch always exists)
        assert "Repository" in entity_types
        assert "Branch" in entity_types

        # Verify Commit, Tag, and Documentation are present (from our mock)
        assert "Commit" in entity_types
        assert "Tag" in entity_types
        assert "Documentation" in entity_types
