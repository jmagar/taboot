"""GitHub repository reader for ingesting code, issues, and PRs.

This module implements GitHubReader that loads data from GitHub repositories including:
- Repository files (code, documentation)
- Issues with comments
- Pull requests with reviews

Key features:
- Incremental sync using `since` parameter for issues
- PR search via GitHub Search API for timestamp filtering
- File extension filtering
- GitHub-specific metadata extraction (repo, author, issue/PR numbers)
"""

import hashlib
import os
from datetime import UTC, datetime
from typing import Any

from github import Auth, Github, GithubException
from llama_index.readers.github import (
    GithubClient,
    GithubRepositoryReader,
)

from llamacrawl.models.document import Document, DocumentMetadata
from llamacrawl.readers.base import BaseReader
from llamacrawl.storage.redis import RedisClient
from llamacrawl.utils.retry import retry_with_backoff


class GitHubReader(BaseReader):
    """GitHub repository reader extending BaseReader.

    Loads repository files, issues, and pull requests from GitHub.
    Supports incremental sync using timestamps for issues and Search API for PRs.

    Attributes:
        github_client: LlamaIndex GithubClient for repository file access
        github_issues_client: LlamaIndex client for issues
        pygithub_client: PyGithub client for PR search and advanced queries
        repositories: List of repository identifiers (owner/name format)
        file_extensions: Optional list of file extensions to include (e.g., ['.py', '.md']).
                        None (default) loads all files, trusting .gitignore for exclusions.
        include_issues: Whether to load issues
        include_prs: Whether to load pull requests
    """

    def __init__(
        self,
        source_name: str,
        config: dict[str, Any],
        redis_client: RedisClient,
    ):
        """Initialize GitHub reader with authentication and configuration.

        Args:
            source_name: Name of the data source (typically 'github')
            config: Source-specific configuration from config.yaml
            redis_client: Redis client for state management

        Raises:
            ValueError: If GITHUB_TOKEN is missing or configuration is invalid
        """
        super().__init__(source_name, config, redis_client)

        # Validate credentials
        self.validate_credentials(["GITHUB_TOKEN"])

        # Initialize GitHub clients (lazy - created on first use)
        self._github_client: GithubClient | None = None
        self._pygithub_client: Github | None = None

        # Extract configuration
        configured_targets = [
            repo for repo in config.get("repositories", []) if repo and repo.strip()
        ]
        if not configured_targets:
            raise ValueError(
                "GitHub reader requires at least one repository or owner in config"
            )

        self.configured_targets = configured_targets
        self.owner_targets = [target for target in configured_targets if "/" not in target]
        self.repositories = self._resolve_repository_targets(configured_targets)
        if not self.repositories:
            raise ValueError(
                "GitHub reader could not resolve any repositories from configured targets "
                f"{configured_targets}"
            )

        self.file_extensions = config.get("file_extensions")
        self.include_issues = config.get("include_issues", True)
        self.include_prs = config.get("include_prs", True)

        self.logger.info(
            f"Initialized GitHubReader for {len(self.repositories)} repositories",
            extra={
                "source": self.source_name,
                "configured_targets": self.configured_targets,
                "expanded_owner_targets": self.owner_targets,
                "repositories": self.repositories,
                "include_issues": self.include_issues,
                "include_prs": self.include_prs,
            },
        )

    def get_api_client(self) -> GithubClient:
        """Lazy initialization of LlamaIndex GitHub client.

        Returns:
            GithubClient instance for repository file access
        """
        if self._github_client is None:
            github_token = os.environ["GITHUB_TOKEN"]
            self._github_client = GithubClient(github_token=github_token, verbose=False)
            self.logger.debug("Initialized LlamaIndex GithubClient")
        return self._github_client

    def _get_pygithub_client(self) -> Github:
        """Lazy initialization of PyGithub client for advanced queries.

        Returns:
            PyGithub Github instance for PR search and advanced features
        """
        if self._pygithub_client is None:
            github_token = os.environ["GITHUB_TOKEN"]
            auth = Auth.Token(github_token)
            self._pygithub_client = Github(auth=auth)
            self.logger.debug("Initialized PyGithub client")
        return self._pygithub_client

    def _resolve_repository_targets(self, targets: list[str]) -> list[str]:
        """Expand owner entries to concrete repository identifiers."""
        resolved: list[str] = []
        seen: set[str] = set()
        owners: list[str] = []

        for target in targets:
            identifier = target.strip()
            if not identifier:
                continue
            if "/" in identifier:
                if identifier not in seen:
                    seen.add(identifier)
                    resolved.append(identifier)
            else:
                owners.append(identifier)

        if not owners:
            return resolved

        for owner in owners:
            owner_repositories = self._fetch_owner_repositories(owner)
            if not owner_repositories:
                self.logger.warning(
                    f"No repositories found for owner {owner}",
                    extra={"source": self.source_name, "owner": owner},
                )
                continue

            self.logger.info(
                f"Expanded owner {owner} to {len(owner_repositories)} repositories",
                extra={
                    "source": self.source_name,
                    "owner": owner,
                    "expanded_count": len(owner_repositories),
                },
            )
            for repo_identifier in owner_repositories:
                if repo_identifier not in seen:
                    seen.add(repo_identifier)
                    resolved.append(repo_identifier)

        return resolved

    def _fetch_owner_repositories(self, owner: str) -> list[str]:
        """Fetch repositories for a given owner, handling users and organizations."""
        client = self._get_pygithub_client()

        try:
            account = client.get_user(owner)
        except GithubException as user_error:
            status = getattr(user_error, "status", None)
            if status != 404:
                self.logger.error(
                    f"Failed to look up GitHub user {owner}",
                    extra={
                        "source": self.source_name,
                        "owner": owner,
                        "status": status,
                    },
                )
                return []
            try:
                account = client.get_organization(owner)
            except GithubException as org_error:
                self.logger.error(
                    f"Failed to look up GitHub owner {owner}",
                    extra={
                        "source": self.source_name,
                        "owner": owner,
                        "status": getattr(org_error, "status", None),
                    },
                )
                return []
        else:
            if getattr(account, "type", None) == "Organization":
                try:
                    account = client.get_organization(owner)
                except GithubException:
                    # Fall back to NamedUser if we cannot get Organization object
                    pass

        try:
            repo_iterator = (
                account.get_repos(type="all")
                if getattr(account, "type", None) == "Organization"
                else account.get_repos(type="owner")
            )
        except GithubException as repos_error:
            self.logger.error(
                f"Failed to list repositories for owner {owner}",
                extra={
                    "source": self.source_name,
                    "owner": owner,
                    "status": getattr(repos_error, "status", None),
                },
            )
            return []
        except TypeError:
            repo_iterator = account.get_repos()

        repositories: list[str] = []
        try:
            for repository in repo_iterator:
                repositories.append(repository.full_name)
        except GithubException as iteration_error:
            self.logger.error(
                f"GitHub API error while iterating repositories for {owner}",
                extra={
                    "source": self.source_name,
                    "owner": owner,
                    "status": getattr(iteration_error, "status", None),
                },
            )
            return []

        return repositories

    def supports_incremental_sync(self) -> bool:
        """GitHub reader supports incremental sync.

        Returns:
            True - GitHub API supports since parameter for issues and Search API for PRs
        """
        return True

    def _get_default_branch(self, owner: str, repo_name: str) -> str | None:
        """Detect the default branch for a repository.

        Tries in order: main, master, then the repository's default branch.

        Args:
            owner: Repository owner
            repo_name: Repository name

        Returns:
            Branch name if found, None if repository is empty or inaccessible
        """
        try:
            gh = self._get_pygithub_client()
            repo = gh.get_repo(f"{owner}/{repo_name}")

            # Try common branches first
            for branch_name in ["main", "master"]:
                try:
                    repo.get_branch(branch_name)
                    return branch_name
                except GithubException:
                    continue

            # Fall back to repository default branch
            default_branch: str | None = repo.default_branch
            if default_branch:
                return default_branch

            # Repository is empty
            return None

        except GithubException as e:
            self.logger.warning(
                f"Could not access repository {owner}/{repo_name}",
                extra={
                    "source": self.source_name,
                    "repo": f"{owner}/{repo_name}",
                    "error": str(e),
                    "status": e.status,
                },
            )
            return None

    @retry_with_backoff(max_attempts=5, initial_delay=2.0, max_delay=60.0)
    def _load_repository_files(
        self,
        owner: str,
        repo_name: str,
    ) -> list[Document]:
        """Load repository files filtered by extensions.

        Args:
            owner: Repository owner (username or organization)
            repo_name: Repository name

        Returns:
            List of Document objects representing repository files

        Raises:
            GithubException: On GitHub API errors (rate limit, auth, etc.)
        """
        documents: list[Document] = []

        try:
            # Detect default branch
            branch = self._get_default_branch(owner, repo_name)
            if not branch:
                self.logger.warning(
                    f"Repository {owner}/{repo_name} is empty or has no accessible branches",
                    extra={
                        "source": self.source_name,
                        "repo": f"{owner}/{repo_name}",
                    },
                )
                return documents

            # Initialize file reader with optional extension filters
            reader_kwargs = {
                "github_client": self.get_api_client(),
                "owner": owner,
                "repo": repo_name,
                "use_parser": False,
                "verbose": False,
                # GitHub API occasionally stalls on blob fetches; give it more time and retries.
                "timeout": 20,
                "retries": 3,
                "concurrent_requests": 3,
                "fail_on_error": False,
            }

            # Only filter if extensions are explicitly configured
            if self.file_extensions:
                reader_kwargs["filter_file_extensions"] = (
                    self.file_extensions,
                    GithubRepositoryReader.FilterType.INCLUDE,
                )

            reader = GithubRepositoryReader(**reader_kwargs)

            # Load files from detected branch
            llamaindex_docs = reader.load_data(branch=branch)

            # Convert LlamaIndex documents to our Document model
            for doc in llamaindex_docs:
                # Extract file path from metadata
                file_path = doc.metadata.get("file_path", "unknown")
                default_name = file_path.split("/")[-1] if file_path else "unknown"
                file_name = doc.metadata.get("file_name", default_name)

                # Compute content hash
                content_hash = hashlib.sha256(doc.text.encode("utf-8")).hexdigest()

                # Create Document with GitHub-specific metadata
                document = Document(
                    doc_id=f"github_{owner}_{repo_name}_file_{file_path}",
                    title=f"{owner}/{repo_name}: {file_name}",
                    content=doc.text,
                    content_hash=content_hash,
                    metadata=DocumentMetadata(
                        source_type="github",
                        source_url=f"https://github.com/{owner}/{repo_name}/blob/{branch}/{file_path}",
                        timestamp=datetime.now(UTC),
                        extra={
                            "repo_owner": owner,
                            "repo_name": repo_name,
                            "file_path": file_path,
                            "file_name": file_name,
                            "branch": branch,
                            "content_type": "file",
                        },
                    ),
                )
                documents.append(document)

            self.logger.info(
                f"Loaded {len(documents)} files from {owner}/{repo_name}",
                extra={
                    "source": self.source_name,
                    "repo": f"{owner}/{repo_name}",
                    "file_count": len(documents),
                },
            )

        except GithubException as e:
            if e.status == 403:
                self.logger.error(
                    f"Rate limit or permission error loading files from {owner}/{repo_name}",
                    extra={
                        "source": self.source_name,
                        "repo": f"{owner}/{repo_name}",
                        "error": str(e),
                        "status": e.status,
                    },
                )
            raise
        except Exception as e:
            self.logger.error(
                f"Error loading repository files from {owner}/{repo_name}",
                extra={
                    "source": self.source_name,
                    "repo": f"{owner}/{repo_name}",
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

        return documents

    @retry_with_backoff(max_attempts=5, initial_delay=2.0, max_delay=60.0)
    def _load_issues(
        self,
        owner: str,
        repo_name: str,
        since: datetime | None = None,
    ) -> list[Document]:
        """Load issues using since parameter for incremental sync.

        Args:
            owner: Repository owner
            repo_name: Repository name
            since: Only load issues updated after this timestamp (for incremental sync)

        Returns:
            List of Document objects representing issues and their comments
        """
        documents = []

        try:
            # Get PyGithub repository
            gh = self._get_pygithub_client()
            repo = gh.get_repo(f"{owner}/{repo_name}")

            # Fetch issues with since parameter (filters by updated_at)
            if since:
                issues = repo.get_issues(state="all", since=since)
            else:
                issues = repo.get_issues(state="all")

            # Track latest updated timestamp for cursor update
            latest_updated: datetime | None = None

            for issue in issues:
                # Skip pull requests (they appear in issues endpoint but have different handling)
                if issue.pull_request is not None:
                    continue

                # Combine issue body with comments
                content_parts = [
                    f"Title: {issue.title}",
                    f"State: {issue.state}",
                    f"Author: {issue.user.login if issue.user else 'unknown'}",
                    f"Created: {issue.created_at.isoformat()}",
                    f"Updated: {issue.updated_at.isoformat()}",
                    f"\nBody:\n{issue.body or '(no description)'}",
                ]

                # Add comments
                comments = issue.get_comments()
                comment_count = 0
                for comment in comments:
                    content_parts.append(
                        f"\n---\nComment by {comment.user.login if comment.user else 'unknown'} "
                        f"on {comment.created_at.isoformat()}:\n{comment.body}"
                    )
                    comment_count += 1

                content = "\n".join(content_parts)
                content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

                # Create document
                document = Document(
                    doc_id=f"github_{owner}_{repo_name}_issue_{issue.number}",
                    title=f"{owner}/{repo_name} Issue #{issue.number}: {issue.title}",
                    content=content,
                    content_hash=content_hash,
                    metadata=DocumentMetadata(
                        source_type="github",
                        source_url=issue.html_url,
                        timestamp=issue.updated_at.replace(tzinfo=UTC),
                        extra={
                            "repo_owner": owner,
                            "repo_name": repo_name,
                            "issue_number": issue.number,
                            "author": issue.user.login if issue.user else "unknown",
                            "state": issue.state,
                            "labels": [label.name for label in issue.labels],
                            "comments": comment_count,
                            "content_type": "issue",
                        },
                    ),
                )
                documents.append(document)

                # Track latest updated timestamp
                if latest_updated is None or issue.updated_at > latest_updated:
                    latest_updated = issue.updated_at

            # Update cursor with latest timestamp
            if latest_updated and documents:
                cursor = latest_updated.replace(tzinfo=UTC).isoformat()
                self.set_last_cursor(f"{owner}/{repo_name}/issues:{cursor}")

            self.logger.info(
                f"Loaded {len(documents)} issues from {owner}/{repo_name}",
                extra={
                    "source": self.source_name,
                    "repo": f"{owner}/{repo_name}",
                    "issue_count": len(documents),
                    "since": since.isoformat() if since else "all",
                },
            )

        except GithubException as e:
            if e.status == 403:
                self.logger.error(
                    f"Rate limit or permission error loading issues from {owner}/{repo_name}",
                    extra={
                        "source": self.source_name,
                        "repo": f"{owner}/{repo_name}",
                        "error": str(e),
                        "status": e.status,
                    },
                )
            raise
        except Exception as e:
            self.logger.error(
                f"Error loading issues from {owner}/{repo_name}",
                extra={
                    "source": self.source_name,
                    "repo": f"{owner}/{repo_name}",
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

        return documents

    @retry_with_backoff(max_attempts=5, initial_delay=2.0, max_delay=60.0)
    def _load_pull_requests(
        self,
        owner: str,
        repo_name: str,
        since: datetime | None = None,
    ) -> list[Document]:
        """Load pull requests using GitHub Search API for timestamp filtering.

        Note: PR List API doesn't support `since` parameter, so we use Search API
        with query: "repo:owner/name is:pr updated:>=YYYY-MM-DD"

        Args:
            owner: Repository owner
            repo_name: Repository name
            since: Only load PRs updated after this timestamp (for incremental sync)

        Returns:
            List of Document objects representing pull requests

        Note:
            Search API has lower rate limit (30 requests/minute)
        """
        documents = []

        try:
            gh = self._get_pygithub_client()

            # Build search query
            if since:
                since_date = since.strftime("%Y-%m-%d")
                query = f"repo:{owner}/{repo_name} is:pr updated:>={since_date}"
            else:
                query = f"repo:{owner}/{repo_name} is:pr"

            # Search for PRs using Search API
            search_results = gh.search_issues(query=query, sort="updated", order="desc")

            # Track latest updated timestamp
            latest_updated: datetime | None = None

            for issue in search_results:
                # Get full PR object
                pr = issue.as_pull_request()

                # Combine PR details
                content_parts = [
                    f"Title: {pr.title}",
                    f"State: {pr.state}",
                    f"Author: {pr.user.login if pr.user else 'unknown'}",
                    f"Created: {pr.created_at.isoformat()}",
                    f"Updated: {pr.updated_at.isoformat() if pr.updated_at else 'unknown'}",
                    f"Merged: {pr.merged}",
                    f"\nBody:\n{pr.body or '(no description)'}",
                ]

                # Add review comments if available
                try:
                    comments = pr.get_comments()
                    comment_count = 0
                    for idx, comment in enumerate(comments, start=1):
                        author = comment.user.login if comment.user else "unknown"
                        content_parts.append(
                            f"\n---\nReview comment by {author} "
                            f"on {comment.created_at.isoformat()}:\n{comment.body}"
                        )
                        comment_count = idx
                except Exception:
                    # Some PRs may have restricted access to comments
                    comment_count = 0

                content = "\n".join(content_parts)
                content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

                # Create document
                document = Document(
                    doc_id=f"github_{owner}_{repo_name}_pr_{pr.number}",
                    title=f"{owner}/{repo_name} PR #{pr.number}: {pr.title}",
                    content=content,
                    content_hash=content_hash,
                    metadata=DocumentMetadata(
                        source_type="github",
                        source_url=pr.html_url,
                        timestamp=pr.updated_at.replace(tzinfo=UTC) if pr.updated_at else datetime.now(UTC),
                        extra={
                            "repo_owner": owner,
                            "repo_name": repo_name,
                            "pr_number": pr.number,
                            "author": pr.user.login if pr.user else "unknown",
                            "state": pr.state,
                            "merged": pr.merged,
                            "comments": comment_count,
                            "content_type": "pull_request",
                        },
                    ),
                )
                documents.append(document)

                # Track latest updated timestamp
                if pr.updated_at and (latest_updated is None or pr.updated_at > latest_updated):
                    latest_updated = pr.updated_at

            # Update cursor with latest timestamp
            if latest_updated and documents:
                cursor = latest_updated.replace(tzinfo=UTC).isoformat()
                self.set_last_cursor(f"{owner}/{repo_name}/prs:{cursor}")

            self.logger.info(
                f"Loaded {len(documents)} pull requests from {owner}/{repo_name}",
                extra={
                    "source": self.source_name,
                    "repo": f"{owner}/{repo_name}",
                    "pr_count": len(documents),
                    "since": since.isoformat() if since else "all",
                },
            )

        except GithubException as e:
            if e.status == 403:
                self.logger.warning(
                    f"Rate limit hit while loading PRs from {owner}/{repo_name} "
                    f"(Search API: 30 req/min)",
                    extra={
                        "source": self.source_name,
                        "repo": f"{owner}/{repo_name}",
                        "error": str(e),
                        "status": e.status,
                    },
                )
            raise
        except Exception as e:
            self.logger.error(
                f"Error loading pull requests from {owner}/{repo_name}",
                extra={
                    "source": self.source_name,
                    "repo": f"{owner}/{repo_name}",
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

        return documents

    def load_data(self, **kwargs: Any) -> list[Document]:
        """Load documents from configured GitHub repositories.

        Loads repository files, issues, and pull requests based on configuration.
        Supports incremental sync by retrieving last cursor from Redis and using
        timestamp-based filtering.

        Args:
            **kwargs: Optional overrides (not typically used)

        Returns:
            List of Document objects from all configured repositories

        Raises:
            GithubException: On GitHub API errors
            ValueError: On configuration errors
        """
        all_documents: list[Document] = []

        for repo_identifier in self.repositories:
            # Parse repository identifier (format: owner/name)
            if "/" not in repo_identifier:
                self.logger.error(
                    f"Invalid repository identifier: {repo_identifier}",
                    extra={"source": self.source_name, "repo": repo_identifier},
                )
                continue

            owner, repo_name = repo_identifier.split("/", 1)

            self.logger.info(
                f"Loading data from {owner}/{repo_name}",
                extra={
                    "source": self.source_name,
                    "repo": repo_identifier,
                    "include_files": True,
                    "include_issues": self.include_issues,
                    "include_prs": self.include_prs,
                },
            )

            # Load repository files
            try:
                files = self._load_repository_files(owner, repo_name)
                all_documents.extend(files)
            except Exception as e:
                self.logger.error(
                    f"Failed to load files from {owner}/{repo_name}",
                    extra={
                        "source": self.source_name,
                        "repo": repo_identifier,
                        "error": str(e),
                    },
                )

            # Load issues if enabled
            if self.include_issues:
                try:
                    # Get last cursor for issues
                    cursor = self.redis_client.get_cursor(f"{owner}/{repo_name}/issues")
                    since = datetime.fromisoformat(cursor.split(":")[-1]) if cursor else None

                    issues = self._load_issues(owner, repo_name, since=since)
                    all_documents.extend(issues)
                except Exception as e:
                    self.logger.error(
                        f"Failed to load issues from {owner}/{repo_name}",
                        extra={
                            "source": self.source_name,
                            "repo": repo_identifier,
                            "error": str(e),
                        },
                    )

            # Load pull requests if enabled
            if self.include_prs:
                try:
                    # Get last cursor for PRs
                    cursor = self.redis_client.get_cursor(f"{owner}/{repo_name}/prs")
                    since = datetime.fromisoformat(cursor.split(":")[-1]) if cursor else None

                    prs = self._load_pull_requests(owner, repo_name, since=since)
                    all_documents.extend(prs)
                except Exception as e:
                    self.logger.error(
                        f"Failed to load pull requests from {owner}/{repo_name}",
                        extra={
                            "source": self.source_name,
                            "repo": repo_identifier,
                            "error": str(e),
                        },
                    )

        # Log summary
        self.log_load_summary(
            total_fetched=len(all_documents),
            repositories=len(self.repositories),
        )

        return all_documents
