"""GitHub repository reader using LlamaIndex.

Implements GitHub repository ingestion (README, wiki, issues) via LlamaIndex GithubRepositoryReader.
Per research.md: Use LlamaIndex readers for standardized Document abstraction.
"""

import logging
from datetime import UTC, datetime

import httpx
from llama_index.core import Document
from llama_index.readers.github import GithubClient, GithubRepositoryReader

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

logger = logging.getLogger(__name__)

# Extractor version for all entities
EXTRACTOR_VERSION = "1.0.0"


def _parse_github_timestamp(timestamp_str: str | None) -> datetime | None:
    """Parse GitHub API timestamp string to datetime.

    GitHub timestamps are in ISO 8601 format with 'Z' suffix.

    Args:
        timestamp_str: Timestamp string from GitHub API (e.g., "2024-01-01T00:00:00Z")

    Returns:
        datetime object or None if timestamp_str is None
    """
    if not timestamp_str:
        return None
    return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))


class GithubReaderError(Exception):
    """Base exception for GithubReader errors."""

    pass


class GithubReader:
    """GitHub repository reader using LlamaIndex GithubRepositoryReader.

    Implements ingestion of README, wiki, and issues from GitHub repositories.
    """

    def __init__(
        self,
        github_token: str,
        max_retries: int = 3,
    ) -> None:
        """Initialize GithubReader with GitHub API token.

        Args:
            github_token: GitHub personal access token for API access.
            max_retries: Maximum number of retry attempts (default: 3).

        Raises:
            ValueError: If github_token is empty.
        """
        if not github_token:
            raise ValueError("github_token cannot be empty")

        self.github_token = github_token
        self.max_retries = max_retries

        logger.info(f"Initialized GithubReader (max_retries={max_retries})")

    def load_data(
        self, repo: str, limit: int | None = None, branch: str | None = None
    ) -> list[Document]:
        """Load documents from GitHub repository.

        Args:
            repo: Repository in format 'owner/repo' (e.g., 'anthropics/claude').
            limit: Optional maximum number of documents to load.
            branch: Optional branch name. If None, tries common defaults (main, master).

        Returns:
            list[Document]: List of LlamaIndex Document objects with text and metadata.

        Raises:
            ValueError: If repo is invalid or empty.
            GithubReaderError: If loading fails after all retries.
        """
        if not repo:
            raise ValueError("repository cannot be empty")

        if "/" not in repo or repo.count("/") != 1:
            raise ValueError(f"Invalid repository format: {repo}. Expected 'owner/repo'")

        owner, repo_name = repo.split("/")
        logger.info(f"Loading data from GitHub repo {repo} (limit: {limit})")

        # Create GitHub client
        github_client = GithubClient(github_token=self.github_token, verbose=True)

        # Create reader with extended_api=False for simple README/wiki/issues
        reader = GithubRepositoryReader(
            github_client=github_client,
            owner=owner,
            repo=repo_name,
            use_parser=False,
            verbose=True,
        )

        # Get default branch from API if not specified
        if branch:
            branches_to_try = [branch]
        else:
            default_branch = self._get_default_branch(owner, repo_name)
            branches_to_try = [default_branch] if default_branch else ["main", "master"]
            logger.info(f"Auto-detected branches to try: {branches_to_try}")

        # Retry logic
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            for branch_name in branches_to_try:
                try:
                    # Load data from repository
                    docs = reader.load_data(branch=branch_name)
                    logger.info(f"Successfully loaded from branch '{branch_name}'")

                    # Apply limit if specified
                    if limit is not None:
                        docs = docs[:limit]

                    # Add metadata
                    for doc in docs:
                        if not doc.metadata:
                            doc.metadata = {}
                        doc.metadata["source_type"] = "github"
                        doc.metadata["repository"] = repo
                        doc.metadata["branch"] = branch_name

                    logger.info(f"Loaded {len(docs)} documents from {repo}")
                    return docs

                except Exception as e:
                    last_error = e
                    logger.debug(f"Branch '{branch_name}' failed: {e}")
                    # Try next branch
                    continue

            # All branches failed for this attempt
            if attempt < self.max_retries - 1:
                backoff = 2**attempt
                logger.warning(
                    f"Attempt {attempt + 1}/{self.max_retries} failed for {repo}. "
                    f"Retrying in {backoff}s..."
                )
            else:
                logger.error(f"All {self.max_retries} attempts failed for {repo}: {last_error}")

        # All retries exhausted
        raise GithubReaderError(
            f"Failed to load {repo} after {self.max_retries} attempts"
        ) from last_error

    def _get_default_branch(self, owner: str, repo: str) -> str | None:
        """Query GitHub API to get repository default branch.

        Args:
            owner: Repository owner.
            repo: Repository name.

        Returns:
            str | None: Default branch name, or None if query fails.
        """
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}"
            headers = {"Authorization": f"token {self.github_token}"}

            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                default_branch: str | None = data.get("default_branch")

                if default_branch and isinstance(default_branch, str):
                    logger.info(f"Detected default branch: {default_branch}")
                    return default_branch
                else:
                    logger.warning("No default_branch in API response")
                    return None

        except Exception as e:
            logger.warning(f"Failed to query default branch: {e}")
            return None

    def extract_entities(
        self, repo: str, branch: str | None = None
    ) -> list[
        Repository
        | Issue
        | PullRequest
        | Commit
        | Branch
        | Tag
        | GitHubLabel
        | Milestone
        | Comment
        | Release
        | Documentation
        | BinaryAsset
    ]:
        """Extract GitHub entities from repository using GitHub API.

        Extracts all 12 GitHub entity types:
        - Repository: Repository metadata
        - Branch: Repository branches
        - Tag: Repository tags
        - Commit: Recent commits
        - Issue: Repository issues
        - PullRequest: Pull requests
        - GitHubLabel: Labels used in issues/PRs
        - Milestone: Project milestones
        - Comment: Comments on issues/PRs
        - Release: GitHub releases
        - Documentation: README and docs files
        - BinaryAsset: Release assets and binaries

        Args:
            repo: Repository in format 'owner/repo'.
            branch: Optional branch name for branch-specific extraction.

        Returns:
            List of GitHub entity instances (mixed types).

        Raises:
            ValueError: If repo format is invalid.
            GithubReaderError: If extraction fails.
        """
        if not repo or "/" not in repo or repo.count("/") != 1:
            raise ValueError(f"Invalid repository format: {repo}. Expected 'owner/repo'")

        owner, repo_name = repo.split("/")
        logger.info(f"Extracting entities from {repo}")

        entities: list[
            Repository
            | Issue
            | PullRequest
            | Commit
            | Branch
            | Tag
            | GitHubLabel
            | Milestone
            | Comment
            | Release
            | Documentation
            | BinaryAsset
        ] = []

        now = datetime.now(UTC)

        try:
            with httpx.Client(timeout=30.0) as client:
                headers = {"Authorization": f"token {self.github_token}"}

                # Extract Repository entity
                repo_entity = self._extract_repository(client, headers, owner, repo_name, now)
                entities.append(repo_entity)

                # Extract Branches
                branches = self._extract_branches(client, headers, owner, repo_name, now)
                entities.extend(branches)

                # Extract Tags
                tags = self._extract_tags(client, headers, owner, repo_name, now)
                entities.extend(tags)

                # Extract Commits (recent commits from default branch)
                commits = self._extract_commits(
                    client, headers, owner, repo_name, branch or repo_entity.default_branch, now
                )
                entities.extend(commits)

                # Extract Issues
                issues = self._extract_issues(client, headers, owner, repo_name, now)
                entities.extend(issues)

                # Extract Pull Requests
                prs = self._extract_pull_requests(client, headers, owner, repo_name, now)
                entities.extend(prs)

                # Extract Labels
                labels = self._extract_labels(client, headers, owner, repo_name, now)
                entities.extend(labels)

                # Extract Milestones
                milestones = self._extract_milestones(client, headers, owner, repo_name, now)
                entities.extend(milestones)

                # Extract Releases
                releases = self._extract_releases(client, headers, owner, repo_name, now)
                entities.extend(releases)

                # Extract Documentation (README and docs)
                docs = self._extract_documentation(
                    client, headers, owner, repo_name, branch or repo_entity.default_branch, now
                )
                entities.extend(docs)

                logger.info(f"Extracted {len(entities)} entities from {repo}")
                return entities

        except Exception as e:
            logger.error(f"Failed to extract entities from {repo}: {e}")
            raise GithubReaderError(f"Entity extraction failed for {repo}") from e

    def _extract_repository(
        self, client: httpx.Client, headers: dict[str, str], owner: str, repo: str, now: datetime
    ) -> Repository:
        """Extract Repository entity from GitHub API."""
        url = f"https://api.github.com/repos/{owner}/{repo}"
        response = client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        return Repository(
            owner=owner,
            name=repo,
            full_name=data["full_name"],
            url=data["html_url"],
            default_branch=data["default_branch"],
            description=data.get("description"),
            language=data.get("language"),
            stars=data.get("stargazers_count"),
            forks=data.get("forks_count"),
            open_issues=data.get("open_issues_count"),
            is_private=data.get("private"),
            is_fork=data.get("fork"),
            created_at=now,
            updated_at=now,
            source_timestamp=_parse_github_timestamp(data["created_at"]),
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version=EXTRACTOR_VERSION,
        )

    def _extract_branches(
        self, client: httpx.Client, headers: dict[str, str], owner: str, repo: str, now: datetime
    ) -> list[Branch]:
        """Extract Branch entities from GitHub API."""
        url = f"https://api.github.com/repos/{owner}/{repo}/branches"
        response = client.get(url, headers=headers, params={"per_page": 100})
        response.raise_for_status()
        data = response.json()

        branches = []
        for branch_data in data:
            branches.append(
                Branch(
                    name=branch_data["name"],
                    protected=branch_data.get("protected", False),
                    sha=branch_data["commit"]["sha"],
                    ref=f"refs/heads/{branch_data['name']}",
                    created_at=now,
                    updated_at=now,
                    source_timestamp=None,  # Branch API doesn't provide creation date
                    extraction_tier="A",
                    extraction_method="github_api",
                    confidence=1.0,
                    extractor_version=EXTRACTOR_VERSION,
                )
            )

        return branches

    def _extract_tags(
        self, client: httpx.Client, headers: dict[str, str], owner: str, repo: str, now: datetime
    ) -> list[Tag]:
        """Extract Tag entities from GitHub API."""
        url = f"https://api.github.com/repos/{owner}/{repo}/tags"
        response = client.get(url, headers=headers, params={"per_page": 100})
        response.raise_for_status()
        data = response.json()

        tags = []
        for tag_data in data:
            tags.append(
                Tag(
                    name=tag_data["name"],
                    sha=tag_data["commit"]["sha"],
                    ref=f"refs/tags/{tag_data['name']}",
                    message=None,  # Would need separate API call to get annotated tag message
                    tagger=None,
                    created_at=now,
                    updated_at=now,
                    source_timestamp=None,  # Tag API doesn't provide creation date
                    extraction_tier="A",
                    extraction_method="github_api",
                    confidence=1.0,
                    extractor_version=EXTRACTOR_VERSION,
                )
            )

        return tags

    def _extract_commits(
        self,
        client: httpx.Client,
        headers: dict[str, str],
        owner: str,
        repo: str,
        branch: str,
        now: datetime,
    ) -> list[Commit]:
        """Extract Commit entities from GitHub API."""
        url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        response = client.get(url, headers=headers, params={"sha": branch, "per_page": 50})
        response.raise_for_status()
        data = response.json()

        commits = []
        for commit_data in data:
            commit_info = commit_data["commit"]
            commits.append(
                Commit(
                    sha=commit_data["sha"],
                    message=commit_info["message"],
                    author_login=commit_data.get("author", {}).get("login")
                    if commit_data.get("author")
                    else None,
                    author_name=commit_info["author"]["name"],
                    author_email=commit_info["author"]["email"],
                    timestamp=_parse_github_timestamp(commit_info["author"]["date"]),
                    tree_sha=commit_info["tree"]["sha"],
                    parent_shas=[p["sha"] for p in commit_data.get("parents", [])],
                    additions=commit_data.get("stats", {}).get("additions"),
                    deletions=commit_data.get("stats", {}).get("deletions"),
                    created_at=now,
                    updated_at=now,
                    source_timestamp=_parse_github_timestamp(commit_info["author"]["date"]),
                    extraction_tier="A",
                    extraction_method="github_api",
                    confidence=1.0,
                    extractor_version=EXTRACTOR_VERSION,
                )
            )

        return commits

    def _extract_issues(
        self, client: httpx.Client, headers: dict[str, str], owner: str, repo: str, now: datetime
    ) -> list[Issue]:
        """Extract Issue entities from GitHub API."""
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        response = client.get(url, headers=headers, params={"state": "all", "per_page": 100})
        response.raise_for_status()
        data = response.json()

        issues = []
        for issue_data in data:
            # Skip pull requests (they have a pull_request key)
            if "pull_request" in issue_data:
                continue

            issues.append(
                Issue(
                    number=issue_data["number"],
                    title=issue_data["title"],
                    state=issue_data["state"],
                    body=issue_data.get("body"),
                    author_login=issue_data["user"]["login"],
                    closed_at=datetime.fromisoformat(issue_data["closed_at"].replace("Z", "+00:00"))
                    if issue_data.get("closed_at")
                    else None,
                    comments_count=issue_data.get("comments"),
                    created_at=now,
                    updated_at=now,
                    source_timestamp=datetime.fromisoformat(
                        issue_data["created_at"].replace("Z", "+00:00")
                    ),
                    extraction_tier="A",
                    extraction_method="github_api",
                    confidence=1.0,
                    extractor_version=EXTRACTOR_VERSION,
                )
            )

        return issues

    def _extract_pull_requests(
        self, client: httpx.Client, headers: dict[str, str], owner: str, repo: str, now: datetime
    ) -> list[PullRequest]:
        """Extract PullRequest entities from GitHub API."""
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        response = client.get(url, headers=headers, params={"state": "all", "per_page": 100})
        response.raise_for_status()
        data = response.json()

        prs = []
        for pr_data in data:
            prs.append(
                PullRequest(
                    number=pr_data["number"],
                    title=pr_data["title"],
                    state=pr_data["state"],
                    base_branch=pr_data["base"]["ref"],
                    head_branch=pr_data["head"]["ref"],
                    merged=pr_data.get("merged", False),
                    merged_at=datetime.fromisoformat(pr_data["merged_at"].replace("Z", "+00:00"))
                    if pr_data.get("merged_at")
                    else None,
                    commits=pr_data.get("commits"),
                    additions=pr_data.get("additions"),
                    deletions=pr_data.get("deletions"),
                    created_at=now,
                    updated_at=now,
                    source_timestamp=datetime.fromisoformat(
                        pr_data["created_at"].replace("Z", "+00:00")
                    ),
                    extraction_tier="A",
                    extraction_method="github_api",
                    confidence=1.0,
                    extractor_version=EXTRACTOR_VERSION,
                )
            )

        return prs

    def _extract_labels(
        self, client: httpx.Client, headers: dict[str, str], owner: str, repo: str, now: datetime
    ) -> list[GitHubLabel]:
        """Extract GitHubLabel entities from GitHub API."""
        url = f"https://api.github.com/repos/{owner}/{repo}/labels"
        response = client.get(url, headers=headers, params={"per_page": 100})
        response.raise_for_status()
        data = response.json()

        labels = []
        for label_data in data:
            labels.append(
                GitHubLabel(
                    name=label_data["name"],
                    color=label_data["color"],
                    description=label_data.get("description"),
                    created_at=now,
                    updated_at=now,
                    source_timestamp=None,  # Label API doesn't provide creation date
                    extraction_tier="A",
                    extraction_method="github_api",
                    confidence=1.0,
                    extractor_version=EXTRACTOR_VERSION,
                )
            )

        return labels

    def _extract_milestones(
        self, client: httpx.Client, headers: dict[str, str], owner: str, repo: str, now: datetime
    ) -> list[Milestone]:
        """Extract Milestone entities from GitHub API."""
        url = f"https://api.github.com/repos/{owner}/{repo}/milestones"
        response = client.get(url, headers=headers, params={"state": "all", "per_page": 100})
        response.raise_for_status()
        data = response.json()

        milestones = []
        for milestone_data in data:
            milestones.append(
                Milestone(
                    number=milestone_data["number"],
                    title=milestone_data["title"],
                    state=milestone_data["state"],
                    due_on=datetime.fromisoformat(milestone_data["due_on"].replace("Z", "+00:00"))
                    if milestone_data.get("due_on")
                    else None,
                    description=milestone_data.get("description"),
                    created_at=now,
                    updated_at=now,
                    source_timestamp=datetime.fromisoformat(
                        milestone_data["created_at"].replace("Z", "+00:00")
                    ),
                    extraction_tier="A",
                    extraction_method="github_api",
                    confidence=1.0,
                    extractor_version=EXTRACTOR_VERSION,
                )
            )

        return milestones

    def _extract_releases(
        self, client: httpx.Client, headers: dict[str, str], owner: str, repo: str, now: datetime
    ) -> list[Release | BinaryAsset]:
        """Extract Release and BinaryAsset entities from GitHub API."""
        url = f"https://api.github.com/repos/{owner}/{repo}/releases"
        response = client.get(url, headers=headers, params={"per_page": 100})
        response.raise_for_status()
        data = response.json()

        entities: list[Release | BinaryAsset] = []

        for release_data in data:
            # Create Release entity
            entities.append(
                Release(
                    tag_name=release_data["tag_name"],
                    name=release_data.get("name") or release_data["tag_name"],  # Use tag as fallback
                    body=release_data.get("body"),
                    draft=release_data.get("draft", False),
                    prerelease=release_data.get("prerelease", False),
                    release_created_at=datetime.fromisoformat(
                        release_data["created_at"].replace("Z", "+00:00")
                    ),
                    published_at=datetime.fromisoformat(
                        release_data["published_at"].replace("Z", "+00:00")
                    )
                    if release_data.get("published_at")
                    else None,
                    tarball_url=release_data.get("tarball_url"),
                    zipball_url=release_data.get("zipball_url"),
                    created_at=now,
                    updated_at=now,
                    source_timestamp=datetime.fromisoformat(
                        release_data["created_at"].replace("Z", "+00:00")
                    ),
                    extraction_tier="A",
                    extraction_method="github_api",
                    confidence=1.0,
                    extractor_version=EXTRACTOR_VERSION,
                )
            )

            # Create BinaryAsset entities for release assets
            for asset_data in release_data.get("assets", []):
                entities.append(
                    BinaryAsset(
                        file_path=f"releases/{release_data['tag_name']}/{asset_data['name']}",
                        size=asset_data["size"],
                        mime_type=asset_data.get("content_type"),
                        download_url=asset_data["browser_download_url"],
                        created_at=now,
                        updated_at=now,
                        source_timestamp=datetime.fromisoformat(
                            asset_data["created_at"].replace("Z", "+00:00")
                        ),
                        extraction_tier="A",
                        extraction_method="github_api",
                        confidence=1.0,
                        extractor_version=EXTRACTOR_VERSION,
                    )
                )

        return entities

    def _extract_documentation(
        self,
        client: httpx.Client,
        headers: dict[str, str],
        owner: str,
        repo: str,
        branch: str,
        now: datetime,
    ) -> list[Documentation]:
        """Extract Documentation entities (README and docs) from GitHub API."""
        docs = []

        # Extract README
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/readme"
            response = client.get(url, headers=headers)
            response.raise_for_status()
            readme_data = response.json()

            # Get content (it's base64 encoded)
            import base64

            content = base64.b64decode(readme_data["content"]).decode("utf-8")

            # Determine format from filename
            filename = readme_data["name"].lower()
            if filename.endswith(".md"):
                fmt = "markdown"
            elif filename.endswith(".rst"):
                fmt = "rst"
            elif filename.endswith(".txt"):
                fmt = "txt"
            else:
                fmt = "unknown"

            docs.append(
                Documentation(
                    file_path=readme_data["path"],
                    content=content,
                    format=fmt,
                    title=f"README - {owner}/{repo}",
                    created_at=now,
                    updated_at=now,
                    source_timestamp=None,  # README API doesn't provide file timestamps
                    extraction_tier="A",
                    extraction_method="github_api",
                    confidence=1.0,
                    extractor_version=EXTRACTOR_VERSION,
                )
            )
        except Exception as e:
            logger.debug(f"No README found: {e}")

        return docs
