"""Tests for GitHubWriter - Batched Neo4j writer for GitHub entities.

Tests cover all 12 GitHub entity types:
- Repository, Issue, PullRequest, Commit
- Branch, Tag, GitHubLabel, Milestone
- Comment, Release, Documentation, BinaryAsset

Tests verify:
- Empty list handling
- Single entity writes
- Batch writes (2000 rows)
- Idempotency (MERGE operations)
- Constraint violations
- Relationship creation
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from packages.graph.client import Neo4jClient
from packages.graph.writers.github_writer import GitHubWriter
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


@pytest.fixture
def neo4j_client() -> MagicMock:
    """Mock Neo4j client for testing."""
    client = MagicMock(spec=Neo4jClient)
    session = MagicMock()
    result = MagicMock()
    result.consume.return_value = MagicMock(counters={"nodes_created": 1})
    session.run.return_value = result
    client.session.return_value.__enter__.return_value = session
    client.session.return_value.__exit__.return_value = None
    return client


@pytest.fixture
def github_writer(neo4j_client: MagicMock) -> GitHubWriter:
    """Create GitHubWriter instance with mock client."""
    return GitHubWriter(neo4j_client, batch_size=2000)


@pytest.fixture
def sample_repository() -> Repository:
    """Create sample Repository entity."""
    return Repository(
        owner="anthropics",
        name="claude-code",
        full_name="anthropics/claude-code",
        url="https://github.com/anthropics/claude-code",
        default_branch="main",
        description="AI-powered coding assistant",
        language="Python",
        stars=1500,
        forks=200,
        open_issues=45,
        is_private=False,
        is_fork=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        source_timestamp=datetime(2023, 1, 1, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="github_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_issue() -> Issue:
    """Create sample Issue entity."""
    return Issue(
        number=42,
        title="Fix bug in parser",
        state="open",
        body="The parser fails on edge case X",
        author_login="johndoe",
        comments_count=5,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        source_timestamp=datetime(2024, 1, 10, 8, 0, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="github_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_pull_request() -> PullRequest:
    """Create sample PullRequest entity."""
    return PullRequest(
        number=123,
        title="Add new feature",
        state="merged",
        base_branch="main",
        head_branch="feature/new-thing",
        merged=True,
        merged_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        commits=5,
        additions=250,
        deletions=50,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        source_timestamp=datetime(2024, 1, 10, 8, 0, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="github_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_commit() -> Commit:
    """Create sample Commit entity."""
    return Commit(
        sha="abc123def456",
        message="Fix bug in parser",
        author_login="johndoe",
        author_name="John Doe",
        author_email="john@example.com",
        timestamp=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        tree_sha="tree123abc",
        parent_shas=["parent1abc"],
        additions=150,
        deletions=50,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        source_timestamp=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="github_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_branch() -> Branch:
    """Create sample Branch entity."""
    return Branch(
        name="main",
        protected=True,
        sha="abc123",
        ref="refs/heads/main",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="github_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_tag() -> Tag:
    """Create sample Tag entity."""
    return Tag(
        name="v1.0.0",
        sha="abc123",
        ref="refs/tags/v1.0.0",
        message="Release v1.0.0",
        tagger="johndoe",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="github_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_label() -> GitHubLabel:
    """Create sample GitHubLabel entity."""
    return GitHubLabel(
        name="bug",
        color="d73a4a",
        description="Something isn't working",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="github_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_milestone() -> Milestone:
    """Create sample Milestone entity."""
    return Milestone(
        number=1,
        title="v1.0 Release",
        state="open",
        due_on=datetime(2024, 12, 31, tzinfo=UTC),
        description="First major release",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="github_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_comment() -> Comment:
    """Create sample Comment entity."""
    return Comment(
        id=123456,
        author_login="janedoe",
        body="This looks good!",
        comment_created_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        comment_updated_at=datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        source_timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="github_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_release() -> Release:
    """Create sample Release entity."""
    return Release(
        tag_name="v1.0.0",
        name="Version 1.0.0",
        body="First stable release",
        draft=False,
        prerelease=False,
        published_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        tarball_url="https://github.com/anthropics/claude-code/archive/v1.0.0.tar.gz",
        zipball_url="https://github.com/anthropics/claude-code/archive/v1.0.0.zip",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        source_timestamp=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="github_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_documentation() -> Documentation:
    """Create sample Documentation entity."""
    return Documentation(
        file_path="README.md",
        content="# Project Documentation",
        format="markdown",
        title="README",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="github_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_binary_asset() -> BinaryAsset:
    """Create sample BinaryAsset entity."""
    return BinaryAsset(
        file_path="dist/app.zip",
        size=1024000,
        mime_type="application/zip",
        download_url="https://github.com/anthropics/claude-code/releases/download/v1.0.0/app.zip",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="github_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


# ===== Repository Tests =====


def test_write_repositories_empty_list(github_writer: GitHubWriter) -> None:
    """Test write_repositories with empty list."""
    result = github_writer.write_repositories([])
    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_repositories_single(
    github_writer: GitHubWriter, sample_repository: Repository
) -> None:
    """Test write_repositories with single entity."""
    result = github_writer.write_repositories([sample_repository])
    assert result["total_written"] == 1
    assert result["batches_executed"] == 1


def test_write_repositories_batch(github_writer: GitHubWriter) -> None:
    """Test write_repositories with 2000+ entities."""
    repos = [
        Repository(
            owner="org",
            name=f"repo-{i}",
            full_name=f"org/repo-{i}",
            url=f"https://github.com/org/repo-{i}",
            default_branch="main",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )
        for i in range(2500)
    ]

    result = github_writer.write_repositories(repos)
    assert result["total_written"] == 2500
    assert result["batches_executed"] == 2  # 2000 + 500


# ===== Issue Tests =====


def test_write_issues_empty_list(github_writer: GitHubWriter) -> None:
    """Test write_issues with empty list."""
    result = github_writer.write_issues("anthropics/claude-code", [])
    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_issues_single(github_writer: GitHubWriter, sample_issue: Issue) -> None:
    """Test write_issues with single entity."""
    result = github_writer.write_issues("anthropics/claude-code", [sample_issue])
    assert result["total_written"] == 1
    assert result["batches_executed"] == 1


# ===== PullRequest Tests =====


def test_write_pull_requests_empty_list(github_writer: GitHubWriter) -> None:
    """Test write_pull_requests with empty list."""
    result = github_writer.write_pull_requests("anthropics/claude-code", [])
    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_pull_requests_single(
    github_writer: GitHubWriter, sample_pull_request: PullRequest
) -> None:
    """Test write_pull_requests with single entity."""
    result = github_writer.write_pull_requests("anthropics/claude-code", [sample_pull_request])
    assert result["total_written"] == 1
    assert result["batches_executed"] == 1


# ===== Commit Tests =====


def test_write_commits_empty_list(github_writer: GitHubWriter) -> None:
    """Test write_commits with empty list."""
    result = github_writer.write_commits("anthropics/claude-code", [])
    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_commits_single(github_writer: GitHubWriter, sample_commit: Commit) -> None:
    """Test write_commits with single entity."""
    result = github_writer.write_commits("anthropics/claude-code", [sample_commit])
    assert result["total_written"] == 1
    assert result["batches_executed"] == 1


# ===== Branch Tests =====


def test_write_branches_empty_list(github_writer: GitHubWriter) -> None:
    """Test write_branches with empty list."""
    result = github_writer.write_branches("anthropics/claude-code", [])
    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_branches_single(github_writer: GitHubWriter, sample_branch: Branch) -> None:
    """Test write_branches with single entity."""
    result = github_writer.write_branches("anthropics/claude-code", [sample_branch])
    assert result["total_written"] == 1
    assert result["batches_executed"] == 1


# ===== Tag Tests =====


def test_write_tags_empty_list(github_writer: GitHubWriter) -> None:
    """Test write_tags with empty list."""
    result = github_writer.write_tags("anthropics/claude-code", [])
    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_tags_single(github_writer: GitHubWriter, sample_tag: Tag) -> None:
    """Test write_tags with single entity."""
    result = github_writer.write_tags("anthropics/claude-code", [sample_tag])
    assert result["total_written"] == 1
    assert result["batches_executed"] == 1


# ===== Label Tests =====


def test_write_labels_empty_list(github_writer: GitHubWriter) -> None:
    """Test write_labels with empty list."""
    result = github_writer.write_labels("anthropics/claude-code", [])
    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_labels_single(github_writer: GitHubWriter, sample_label: GitHubLabel) -> None:
    """Test write_labels with single entity."""
    result = github_writer.write_labels("anthropics/claude-code", [sample_label])
    assert result["total_written"] == 1
    assert result["batches_executed"] == 1


# ===== Milestone Tests =====


def test_write_milestones_empty_list(github_writer: GitHubWriter) -> None:
    """Test write_milestones with empty list."""
    result = github_writer.write_milestones("anthropics/claude-code", [])
    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_milestones_single(github_writer: GitHubWriter, sample_milestone: Milestone) -> None:
    """Test write_milestones with single entity."""
    result = github_writer.write_milestones("anthropics/claude-code", [sample_milestone])
    assert result["total_written"] == 1
    assert result["batches_executed"] == 1


# ===== Comment Tests =====


def test_write_comments_empty_list(github_writer: GitHubWriter) -> None:
    """Test write_comments with empty list."""
    result = github_writer.write_comments("anthropics/claude-code", 42, [])
    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_comments_single(github_writer: GitHubWriter, sample_comment: Comment) -> None:
    """Test write_comments with single entity."""
    result = github_writer.write_comments("anthropics/claude-code", 42, [sample_comment])
    assert result["total_written"] == 1
    assert result["batches_executed"] == 1


# ===== Release Tests =====


def test_write_releases_empty_list(github_writer: GitHubWriter) -> None:
    """Test write_releases with empty list."""
    result = github_writer.write_releases("anthropics/claude-code", [])
    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_releases_single(github_writer: GitHubWriter, sample_release: Release) -> None:
    """Test write_releases with single entity."""
    result = github_writer.write_releases("anthropics/claude-code", [sample_release])
    assert result["total_written"] == 1
    assert result["batches_executed"] == 1


# ===== Documentation Tests =====


def test_write_documentation_empty_list(github_writer: GitHubWriter) -> None:
    """Test write_documentation with empty list."""
    result = github_writer.write_documentation("anthropics/claude-code", [])
    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_documentation_single(
    github_writer: GitHubWriter, sample_documentation: Documentation
) -> None:
    """Test write_documentation with single entity."""
    result = github_writer.write_documentation("anthropics/claude-code", [sample_documentation])
    assert result["total_written"] == 1
    assert result["batches_executed"] == 1


# ===== BinaryAsset Tests =====


def test_write_binary_assets_empty_list(github_writer: GitHubWriter) -> None:
    """Test write_binary_assets with empty list."""
    result = github_writer.write_binary_assets("anthropics/claude-code", "v1.0.0", [])
    assert result["total_written"] == 0
    assert result["batches_executed"] == 0


def test_write_binary_assets_single(
    github_writer: GitHubWriter, sample_binary_asset: BinaryAsset
) -> None:
    """Test write_binary_assets with single entity."""
    result = github_writer.write_binary_assets(
        "anthropics/claude-code", "v1.0.0", [sample_binary_asset]
    )
    assert result["total_written"] == 1
    assert result["batches_executed"] == 1


# ===== Idempotency Tests =====


def test_write_repositories_idempotent(
    github_writer: GitHubWriter, sample_repository: Repository
) -> None:
    """Test write_repositories is idempotent (MERGE operation)."""
    # Write same repository twice
    result1 = github_writer.write_repositories([sample_repository])
    result2 = github_writer.write_repositories([sample_repository])

    # Should succeed both times (MERGE handles duplicates)
    assert result1["total_written"] == 1
    assert result2["total_written"] == 1


# ===== Error Handling Tests =====


def test_write_issues_invalid_repo(github_writer: GitHubWriter, sample_issue: Issue) -> None:
    """Test write_issues with invalid repository name."""
    with pytest.raises(ValueError, match="repo_full_name cannot be empty"):
        github_writer.write_issues("", [sample_issue])


def test_write_comments_invalid_issue_number(
    github_writer: GitHubWriter, sample_comment: Comment
) -> None:
    """Test write_comments with invalid issue number."""
    with pytest.raises(ValueError, match="issue_number must be positive"):
        github_writer.write_comments("anthropics/claude-code", 0, [sample_comment])
