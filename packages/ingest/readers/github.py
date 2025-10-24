"""GitHub repository reader using LlamaIndex.

Implements GitHub repository ingestion (README, wiki, issues) via LlamaIndex GithubRepositoryReader.
Per research.md: Use LlamaIndex readers for standardized Document abstraction.
"""

import logging

from llama_index.core import Document
from llama_index.readers.github import GithubClient, GithubRepositoryReader

logger = logging.getLogger(__name__)


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

    def load_data(self, repo: str, limit: int | None = None, branch: str | None = None) -> list[Document]:
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
            raise ValueError(
                f"Invalid repository format: {repo}. Expected 'owner/repo'"
            )

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
                logger.error(
                    f"All {self.max_retries} attempts failed for {repo}: {last_error}"
                )

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
        import httpx

        try:
            url = f"https://api.github.com/repos/{owner}/{repo}"
            headers = {"Authorization": f"token {self.github_token}"}

            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                default_branch = data.get("default_branch")

                if default_branch:
                    logger.info(f"Detected default branch: {default_branch}")
                    return default_branch
                else:
                    logger.warning("No default_branch in API response")
                    return None

        except Exception as e:
            logger.warning(f"Failed to query default branch: {e}")
            return None
