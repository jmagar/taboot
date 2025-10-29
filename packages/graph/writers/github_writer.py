"""GitHubWriter - Batched Neo4j writer for GitHub entities.

Implements GraphWriterPort using batched UNWIND operations for high throughput.
Follows the pattern from packages/graph/writers/swag_writer.py.

Handles all 12 GitHub entity types:
- Repository, Issue, PullRequest, Commit
- Branch, Tag, GitHubLabel, Milestone
- Comment, Release, Documentation, BinaryAsset

Performance target: ≥20k edges/min with 2k-row UNWIND batches.
"""

import logging

from packages.graph.client import Neo4jClient
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


class GitHubWriter:
    """Batched Neo4j writer for GitHub entity ingestion.

    Implements GraphWriterPort interface using batched UNWIND operations.
    Ensures atomic writes and high throughput (target ≥20k edges/min).

    Attributes:
        neo4j_client: Neo4j client instance with connection pooling.
        batch_size: Number of rows per UNWIND batch (default 2000).
    """

    def __init__(self, neo4j_client: Neo4jClient, batch_size: int = 2000) -> None:
        """Initialize GitHubWriter with Neo4j client.

        Args:
            neo4j_client: Neo4j client instance (must be connected).
            batch_size: Number of rows per UNWIND batch (default 2000).
        """
        self.neo4j_client = neo4j_client
        self.batch_size = batch_size

        logger.info(f"Initialized GitHubWriter (batch_size={batch_size})")

    def write_repositories(self, repositories: list[Repository]) -> dict[str, int]:
        """Write Repository nodes to Neo4j using batched UNWIND.

        Creates or updates Repository nodes with all properties.
        Uses MERGE on unique key (full_name) for idempotency.

        Args:
            repositories: List of Repository entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total repositories written
                - batches_executed: Number of batches executed

        Raises:
            Exception: If Neo4j write operation fails.
        """
        if not repositories:
            logger.info("No repositories to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare repository parameters
        repo_params = [
            {
                "owner": r.owner,
                "name": r.name,
                "full_name": r.full_name,
                "url": r.url,
                "default_branch": r.default_branch,
                "description": r.description,
                "language": r.language,
                "stars": r.stars,
                "forks": r.forks,
                "open_issues": r.open_issues,
                "is_private": r.is_private,
                "is_fork": r.is_fork,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
                "source_timestamp": r.source_timestamp.isoformat() if r.source_timestamp else None,
                "extraction_tier": r.extraction_tier,
                "extraction_method": r.extraction_method,
                "confidence": r.confidence,
                "extractor_version": r.extractor_version,
            }
            for r in repositories
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(repo_params), self.batch_size):
                batch = repo_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MERGE (r:Repository {full_name: row.full_name})
                SET r.owner = row.owner,
                    r.name = row.name,
                    r.url = row.url,
                    r.default_branch = row.default_branch,
                    r.description = row.description,
                    r.language = row.language,
                    r.stars = row.stars,
                    r.forks = row.forks,
                    r.open_issues = row.open_issues,
                    r.is_private = row.is_private,
                    r.is_fork = row.is_fork,
                    r.created_at = row.created_at,
                    r.updated_at = row.updated_at,
                    r.source_timestamp = row.source_timestamp,
                    r.extraction_tier = row.extraction_tier,
                    r.extraction_method = row.extraction_method,
                    r.confidence = row.confidence,
                    r.extractor_version = row.extractor_version
                RETURN count(r) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote repository batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} Repository node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_issues(self, repo_full_name: str, issues: list[Issue]) -> dict[str, int]:
        """Write Issue nodes to Neo4j and create relationships to Repository.

        Creates Issue nodes and BELONGS_TO relationships from Issue to Repository.
        Uses MERGE on composite key (repo_full_name, issue_number) for idempotency.

        Args:
            repo_full_name: Full repository name (owner/repo).
            issues: List of Issue entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total issues written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If repo_full_name is empty.
            Exception: If Neo4j write operation fails.
        """
        if not repo_full_name:
            raise ValueError("repo_full_name cannot be empty")

        if not issues:
            logger.info("No issues to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare issue parameters
        issue_params = [
            {
                "repo_full_name": repo_full_name,
                "number": i.number,
                "title": i.title,
                "state": i.state,
                "body": i.body,
                "author_login": i.author_login,
                "closed_at": i.closed_at.isoformat() if i.closed_at else None,
                "comments_count": i.comments_count,
                "created_at": i.created_at.isoformat(),
                "updated_at": i.updated_at.isoformat(),
                "source_timestamp": i.source_timestamp.isoformat() if i.source_timestamp else None,
                "extraction_tier": i.extraction_tier,
                "extraction_method": i.extraction_method,
                "confidence": i.confidence,
                "extractor_version": i.extractor_version,
            }
            for i in issues
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(issue_params), self.batch_size):
                batch = issue_params[i : i + self.batch_size]

                # Create Issue nodes and relationships to Repository
                query = """
                UNWIND $rows AS row
                MATCH (r:Repository {full_name: row.repo_full_name})
                MERGE (i:Issue {repo_full_name: row.repo_full_name, number: row.number})
                SET i.title = row.title,
                    i.state = row.state,
                    i.body = row.body,
                    i.author_login = row.author_login,
                    i.closed_at = row.closed_at,
                    i.comments_count = row.comments_count,
                    i.created_at = row.created_at,
                    i.updated_at = row.updated_at,
                    i.source_timestamp = row.source_timestamp,
                    i.extraction_tier = row.extraction_tier,
                    i.extraction_method = row.extraction_method,
                    i.confidence = row.confidence,
                    i.extractor_version = row.extractor_version
                MERGE (i)-[:BELONGS_TO]->(r)
                RETURN count(i) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote issue batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} Issue node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_pull_requests(
        self, repo_full_name: str, pull_requests: list[PullRequest]
    ) -> dict[str, int]:
        """Write PullRequest nodes to Neo4j and create relationships to Repository.

        Creates PullRequest nodes and BELONGS_TO relationships from PullRequest to Repository.
        Uses MERGE on composite key (repo_full_name, pr_number) for idempotency.

        Args:
            repo_full_name: Full repository name (owner/repo).
            pull_requests: List of PullRequest entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total pull requests written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If repo_full_name is empty.
            Exception: If Neo4j write operation fails.
        """
        if not repo_full_name:
            raise ValueError("repo_full_name cannot be empty")

        if not pull_requests:
            logger.info("No pull requests to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare pull request parameters
        pr_params = [
            {
                "repo_full_name": repo_full_name,
                "number": pr.number,
                "title": pr.title,
                "state": pr.state,
                "base_branch": pr.base_branch,
                "head_branch": pr.head_branch,
                "merged": pr.merged,
                "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                "commits": pr.commits,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "created_at": pr.created_at.isoformat(),
                "updated_at": pr.updated_at.isoformat(),
                "source_timestamp": (
                    pr.source_timestamp.isoformat() if pr.source_timestamp else None
                ),
                "extraction_tier": pr.extraction_tier,
                "extraction_method": pr.extraction_method,
                "confidence": pr.confidence,
                "extractor_version": pr.extractor_version,
            }
            for pr in pull_requests
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(pr_params), self.batch_size):
                batch = pr_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MATCH (r:Repository {full_name: row.repo_full_name})
                MERGE (pr:PullRequest {repo_full_name: row.repo_full_name, number: row.number})
                SET pr.title = row.title,
                    pr.state = row.state,
                    pr.base_branch = row.base_branch,
                    pr.head_branch = row.head_branch,
                    pr.merged = row.merged,
                    pr.merged_at = row.merged_at,
                    pr.commits = row.commits,
                    pr.additions = row.additions,
                    pr.deletions = row.deletions,
                    pr.created_at = row.created_at,
                    pr.updated_at = row.updated_at,
                    pr.source_timestamp = row.source_timestamp,
                    pr.extraction_tier = row.extraction_tier,
                    pr.extraction_method = row.extraction_method,
                    pr.confidence = row.confidence,
                    pr.extractor_version = row.extractor_version
                MERGE (pr)-[:BELONGS_TO]->(r)
                RETURN count(pr) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote pull request batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} PullRequest node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_commits(self, repo_full_name: str, commits: list[Commit]) -> dict[str, int]:
        """Write Commit nodes to Neo4j and create relationships to Repository.

        Creates Commit nodes and BELONGS_TO relationships from Commit to Repository.
        Uses MERGE on unique key (sha) for idempotency.

        Args:
            repo_full_name: Full repository name (owner/repo).
            commits: List of Commit entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total commits written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If repo_full_name is empty.
            Exception: If Neo4j write operation fails.
        """
        if not repo_full_name:
            raise ValueError("repo_full_name cannot be empty")

        if not commits:
            logger.info("No commits to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare commit parameters
        commit_params = [
            {
                "repo_full_name": repo_full_name,
                "sha": c.sha,
                "message": c.message,
                "author_login": c.author_login,
                "author_name": c.author_name,
                "author_email": c.author_email,
                "timestamp": c.timestamp.isoformat(),
                "tree_sha": c.tree_sha,
                "parent_shas": c.parent_shas or [],
                "additions": c.additions,
                "deletions": c.deletions,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
                "source_timestamp": c.source_timestamp.isoformat() if c.source_timestamp else None,
                "extraction_tier": c.extraction_tier,
                "extraction_method": c.extraction_method,
                "confidence": c.confidence,
                "extractor_version": c.extractor_version,
            }
            for c in commits
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(commit_params), self.batch_size):
                batch = commit_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MATCH (r:Repository {full_name: row.repo_full_name})
                MERGE (c:Commit {sha: row.sha})
                SET c.message = row.message,
                    c.author_login = row.author_login,
                    c.author_name = row.author_name,
                    c.author_email = row.author_email,
                    c.timestamp = row.timestamp,
                    c.tree_sha = row.tree_sha,
                    c.parent_shas = row.parent_shas,
                    c.additions = row.additions,
                    c.deletions = row.deletions,
                    c.created_at = row.created_at,
                    c.updated_at = row.updated_at,
                    c.source_timestamp = row.source_timestamp,
                    c.extraction_tier = row.extraction_tier,
                    c.extraction_method = row.extraction_method,
                    c.confidence = row.confidence,
                    c.extractor_version = row.extractor_version
                MERGE (c)-[:BELONGS_TO]->(r)
                RETURN count(c) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote commit batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} Commit node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_branches(self, repo_full_name: str, branches: list[Branch]) -> dict[str, int]:
        """Write Branch nodes to Neo4j and create relationships to Repository.

        Creates Branch nodes and BELONGS_TO relationships from Branch to Repository.
        Uses MERGE on composite key (repo_full_name, name) for idempotency.

        Args:
            repo_full_name: Full repository name (owner/repo).
            branches: List of Branch entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total branches written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If repo_full_name is empty.
            Exception: If Neo4j write operation fails.
        """
        if not repo_full_name:
            raise ValueError("repo_full_name cannot be empty")

        if not branches:
            logger.info("No branches to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare branch parameters
        branch_params = [
            {
                "repo_full_name": repo_full_name,
                "name": b.name,
                "protected": b.protected,
                "sha": b.sha,
                "ref": b.ref,
                "created_at": b.created_at.isoformat(),
                "updated_at": b.updated_at.isoformat(),
                "source_timestamp": b.source_timestamp.isoformat() if b.source_timestamp else None,
                "extraction_tier": b.extraction_tier,
                "extraction_method": b.extraction_method,
                "confidence": b.confidence,
                "extractor_version": b.extractor_version,
            }
            for b in branches
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(branch_params), self.batch_size):
                batch = branch_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MATCH (r:Repository {full_name: row.repo_full_name})
                MERGE (b:Branch {repo_full_name: row.repo_full_name, name: row.name})
                SET b.protected = row.protected,
                    b.sha = row.sha,
                    b.ref = row.ref,
                    b.created_at = row.created_at,
                    b.updated_at = row.updated_at,
                    b.source_timestamp = row.source_timestamp,
                    b.extraction_tier = row.extraction_tier,
                    b.extraction_method = row.extraction_method,
                    b.confidence = row.confidence,
                    b.extractor_version = row.extractor_version
                MERGE (b)-[:BELONGS_TO]->(r)
                RETURN count(b) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote branch batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} Branch node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_tags(self, repo_full_name: str, tags: list[Tag]) -> dict[str, int]:
        """Write Tag nodes to Neo4j and create relationships to Repository.

        Creates Tag nodes and BELONGS_TO relationships from Tag to Repository.
        Uses MERGE on composite key (repo_full_name, name) for idempotency.

        Args:
            repo_full_name: Full repository name (owner/repo).
            tags: List of Tag entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total tags written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If repo_full_name is empty.
            Exception: If Neo4j write operation fails.
        """
        if not repo_full_name:
            raise ValueError("repo_full_name cannot be empty")

        if not tags:
            logger.info("No tags to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare tag parameters
        tag_params = [
            {
                "repo_full_name": repo_full_name,
                "name": t.name,
                "sha": t.sha,
                "ref": t.ref,
                "message": t.message,
                "tagger": t.tagger,
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat(),
                "source_timestamp": t.source_timestamp.isoformat() if t.source_timestamp else None,
                "extraction_tier": t.extraction_tier,
                "extraction_method": t.extraction_method,
                "confidence": t.confidence,
                "extractor_version": t.extractor_version,
            }
            for t in tags
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(tag_params), self.batch_size):
                batch = tag_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MATCH (r:Repository {full_name: row.repo_full_name})
                MERGE (t:Tag {repo_full_name: row.repo_full_name, name: row.name})
                SET t.sha = row.sha,
                    t.ref = row.ref,
                    t.message = row.message,
                    t.tagger = row.tagger,
                    t.created_at = row.created_at,
                    t.updated_at = row.updated_at,
                    t.source_timestamp = row.source_timestamp,
                    t.extraction_tier = row.extraction_tier,
                    t.extraction_method = row.extraction_method,
                    t.confidence = row.confidence,
                    t.extractor_version = row.extractor_version
                MERGE (t)-[:BELONGS_TO]->(r)
                RETURN count(t) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote tag batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} Tag node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_labels(self, repo_full_name: str, labels: list[GitHubLabel]) -> dict[str, int]:
        """Write GitHubLabel nodes to Neo4j and create relationships to Repository.

        Creates GitHubLabel nodes and BELONGS_TO relationships from GitHubLabel to Repository.
        Uses MERGE on composite key (repo_full_name, name) for idempotency.

        Args:
            repo_full_name: Full repository name (owner/repo).
            labels: List of GitHubLabel entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total labels written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If repo_full_name is empty.
            Exception: If Neo4j write operation fails.
        """
        if not repo_full_name:
            raise ValueError("repo_full_name cannot be empty")

        if not labels:
            logger.info("No labels to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare label parameters
        label_params = [
            {
                "repo_full_name": repo_full_name,
                "name": label.name,
                "color": label.color,
                "description": label.description,
                "created_at": label.created_at.isoformat(),
                "updated_at": label.updated_at.isoformat(),
                "source_timestamp": (
                    label.source_timestamp.isoformat() if label.source_timestamp else None
                ),
                "extraction_tier": label.extraction_tier,
                "extraction_method": label.extraction_method,
                "confidence": label.confidence,
                "extractor_version": label.extractor_version,
            }
            for label in labels
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(label_params), self.batch_size):
                batch = label_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MATCH (r:Repository {full_name: row.repo_full_name})
                MERGE (l:GitHubLabel {repo_full_name: row.repo_full_name, name: row.name})
                SET l.color = row.color,
                    l.description = row.description,
                    l.created_at = row.created_at,
                    l.updated_at = row.updated_at,
                    l.source_timestamp = row.source_timestamp,
                    l.extraction_tier = row.extraction_tier,
                    l.extraction_method = row.extraction_method,
                    l.confidence = row.confidence,
                    l.extractor_version = row.extractor_version
                MERGE (l)-[:BELONGS_TO]->(r)
                RETURN count(l) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote label batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} GitHubLabel node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_milestones(self, repo_full_name: str, milestones: list[Milestone]) -> dict[str, int]:
        """Write Milestone nodes to Neo4j and create relationships to Repository.

        Creates Milestone nodes and BELONGS_TO relationships from Milestone to Repository.
        Uses MERGE on composite key (repo_full_name, number) for idempotency.

        Args:
            repo_full_name: Full repository name (owner/repo).
            milestones: List of Milestone entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total milestones written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If repo_full_name is empty.
            Exception: If Neo4j write operation fails.
        """
        if not repo_full_name:
            raise ValueError("repo_full_name cannot be empty")

        if not milestones:
            logger.info("No milestones to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare milestone parameters
        milestone_params = [
            {
                "repo_full_name": repo_full_name,
                "number": m.number,
                "title": m.title,
                "state": m.state,
                "due_on": m.due_on.isoformat() if m.due_on else None,
                "description": m.description,
                "created_at": m.created_at.isoformat(),
                "updated_at": m.updated_at.isoformat(),
                "source_timestamp": m.source_timestamp.isoformat() if m.source_timestamp else None,
                "extraction_tier": m.extraction_tier,
                "extraction_method": m.extraction_method,
                "confidence": m.confidence,
                "extractor_version": m.extractor_version,
            }
            for m in milestones
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(milestone_params), self.batch_size):
                batch = milestone_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MATCH (r:Repository {full_name: row.repo_full_name})
                MERGE (m:Milestone {repo_full_name: row.repo_full_name, number: row.number})
                SET m.title = row.title,
                    m.state = row.state,
                    m.due_on = row.due_on,
                    m.description = row.description,
                    m.created_at = row.created_at,
                    m.updated_at = row.updated_at,
                    m.source_timestamp = row.source_timestamp,
                    m.extraction_tier = row.extraction_tier,
                    m.extraction_method = row.extraction_method,
                    m.confidence = row.confidence,
                    m.extractor_version = row.extractor_version
                MERGE (m)-[:BELONGS_TO]->(r)
                RETURN count(m) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote milestone batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} Milestone node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_comments(
        self, repo_full_name: str, issue_number: int, comments: list[Comment]
    ) -> dict[str, int]:
        """Write Comment nodes to Neo4j and create relationships to Issue.

        Creates Comment nodes and COMMENTS_ON relationships from Comment to Issue.
        Uses MERGE on unique key (id) for idempotency.

        Args:
            repo_full_name: Full repository name (owner/repo).
            issue_number: Issue number this comment belongs to.
            comments: List of Comment entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total comments written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If repo_full_name is empty or issue_number is invalid.
            Exception: If Neo4j write operation fails.
        """
        if not repo_full_name:
            raise ValueError("repo_full_name cannot be empty")

        if issue_number <= 0:
            raise ValueError("issue_number must be positive")

        if not comments:
            logger.info("No comments to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare comment parameters
        comment_params = [
            {
                "repo_full_name": repo_full_name,
                "issue_number": issue_number,
                "id": c.id,
                "author_login": c.author_login,
                "body": c.body,
                "comment_created_at": c.comment_created_at.isoformat(),
                "comment_updated_at": (
                    c.comment_updated_at.isoformat() if c.comment_updated_at else None
                ),
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
                "source_timestamp": c.source_timestamp.isoformat() if c.source_timestamp else None,
                "extraction_tier": c.extraction_tier,
                "extraction_method": c.extraction_method,
                "confidence": c.confidence,
                "extractor_version": c.extractor_version,
            }
            for c in comments
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(comment_params), self.batch_size):
                batch = comment_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MATCH (issue:Issue {repo_full_name: row.repo_full_name, number: row.issue_number})
                MERGE (c:Comment {id: row.id})
                SET c.author_login = row.author_login,
                    c.body = row.body,
                    c.comment_created_at = row.comment_created_at,
                    c.comment_updated_at = row.comment_updated_at,
                    c.created_at = row.created_at,
                    c.updated_at = row.updated_at,
                    c.source_timestamp = row.source_timestamp,
                    c.extraction_tier = row.extraction_tier,
                    c.extraction_method = row.extraction_method,
                    c.confidence = row.confidence,
                    c.extractor_version = row.extractor_version
                MERGE (c)-[:COMMENTS_ON]->(issue)
                RETURN count(c) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote comment batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} Comment node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_releases(self, repo_full_name: str, releases: list[Release]) -> dict[str, int]:
        """Write Release nodes to Neo4j and create relationships to Repository.

        Creates Release nodes and BELONGS_TO relationships from Release to Repository.
        Uses MERGE on composite key (repo_full_name, tag_name) for idempotency.

        Args:
            repo_full_name: Full repository name (owner/repo).
            releases: List of Release entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total releases written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If repo_full_name is empty.
            Exception: If Neo4j write operation fails.
        """
        if not repo_full_name:
            raise ValueError("repo_full_name cannot be empty")

        if not releases:
            logger.info("No releases to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare release parameters
        release_params = [
            {
                "repo_full_name": repo_full_name,
                "tag_name": r.tag_name,
                "name": r.name,
                "body": r.body,
                "draft": r.draft,
                "prerelease": r.prerelease,
                "published_at": r.published_at.isoformat() if r.published_at else None,
                "tarball_url": r.tarball_url,
                "zipball_url": r.zipball_url,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
                "source_timestamp": r.source_timestamp.isoformat() if r.source_timestamp else None,
                "extraction_tier": r.extraction_tier,
                "extraction_method": r.extraction_method,
                "confidence": r.confidence,
                "extractor_version": r.extractor_version,
            }
            for r in releases
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(release_params), self.batch_size):
                batch = release_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MATCH (repo:Repository {full_name: row.repo_full_name})
                MERGE (r:Release {repo_full_name: row.repo_full_name, tag_name: row.tag_name})
                SET r.name = row.name,
                    r.body = row.body,
                    r.draft = row.draft,
                    r.prerelease = row.prerelease,
                    r.published_at = row.published_at,
                    r.tarball_url = row.tarball_url,
                    r.zipball_url = row.zipball_url,
                    r.created_at = row.created_at,
                    r.updated_at = row.updated_at,
                    r.source_timestamp = row.source_timestamp,
                    r.extraction_tier = row.extraction_tier,
                    r.extraction_method = row.extraction_method,
                    r.confidence = row.confidence,
                    r.extractor_version = row.extractor_version
                MERGE (r)-[:BELONGS_TO]->(repo)
                RETURN count(r) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote release batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} Release node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_documentation(
        self, repo_full_name: str, documentation: list[Documentation]
    ) -> dict[str, int]:
        """Write Documentation nodes to Neo4j and create relationships to Repository.

        Creates Documentation nodes and BELONGS_TO relationships from Documentation to Repository.
        Uses MERGE on composite key (repo_full_name, file_path) for idempotency.

        Args:
            repo_full_name: Full repository name (owner/repo).
            documentation: List of Documentation entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total documentation nodes written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If repo_full_name is empty.
            Exception: If Neo4j write operation fails.
        """
        if not repo_full_name:
            raise ValueError("repo_full_name cannot be empty")

        if not documentation:
            logger.info("No documentation to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare documentation parameters
        doc_params = [
            {
                "repo_full_name": repo_full_name,
                "file_path": d.file_path,
                "content": d.content,
                "format": d.format,
                "title": d.title,
                "created_at": d.created_at.isoformat(),
                "updated_at": d.updated_at.isoformat(),
                "source_timestamp": d.source_timestamp.isoformat() if d.source_timestamp else None,
                "extraction_tier": d.extraction_tier,
                "extraction_method": d.extraction_method,
                "confidence": d.confidence,
                "extractor_version": d.extractor_version,
            }
            for d in documentation
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(doc_params), self.batch_size):
                batch = doc_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MATCH (repo:Repository {full_name: row.repo_full_name})
                MERGE (d:Documentation {
                    repo_full_name: row.repo_full_name,
                    file_path: row.file_path
                })
                SET d.content = row.content,
                    d.format = row.format,
                    d.title = row.title,
                    d.created_at = row.created_at,
                    d.updated_at = row.updated_at,
                    d.source_timestamp = row.source_timestamp,
                    d.extraction_tier = row.extraction_tier,
                    d.extraction_method = row.extraction_method,
                    d.confidence = row.confidence,
                    d.extractor_version = row.extractor_version
                MERGE (d)-[:BELONGS_TO]->(repo)
                RETURN count(d) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote documentation batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} Documentation node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}

    def write_binary_assets(
        self, repo_full_name: str, release_tag: str, assets: list[BinaryAsset]
    ) -> dict[str, int]:
        """Write BinaryAsset nodes to Neo4j and create relationships to Release.

        Creates BinaryAsset nodes and BELONGS_TO relationships from BinaryAsset to Release.
        Uses MERGE on composite key (repo_full_name, release_tag, file_path) for idempotency.

        Args:
            repo_full_name: Full repository name (owner/repo).
            release_tag: Release tag this asset belongs to.
            assets: List of BinaryAsset entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total binary assets written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If repo_full_name or release_tag is empty.
            Exception: If Neo4j write operation fails.
        """
        if not repo_full_name:
            raise ValueError("repo_full_name cannot be empty")

        if not release_tag:
            raise ValueError("release_tag cannot be empty")

        if not assets:
            logger.info("No binary assets to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare binary asset parameters
        asset_params = [
            {
                "repo_full_name": repo_full_name,
                "release_tag": release_tag,
                "file_path": a.file_path,
                "size": a.size,
                "mime_type": a.mime_type,
                "download_url": a.download_url,
                "created_at": a.created_at.isoformat(),
                "updated_at": a.updated_at.isoformat(),
                "source_timestamp": a.source_timestamp.isoformat() if a.source_timestamp else None,
                "extraction_tier": a.extraction_tier,
                "extraction_method": a.extraction_method,
                "confidence": a.confidence,
                "extractor_version": a.extractor_version,
            }
            for a in assets
        ]

        # Execute in batches
        with self.neo4j_client.session() as session:
            for i in range(0, len(asset_params), self.batch_size):
                batch = asset_params[i : i + self.batch_size]

                query = """
                UNWIND $rows AS row
                MATCH (rel:Release {repo_full_name: row.repo_full_name, tag_name: row.release_tag})
                MERGE (a:BinaryAsset {
                    repo_full_name: row.repo_full_name,
                    release_tag: row.release_tag,
                    file_path: row.file_path
                })
                SET a.size = row.size,
                    a.mime_type = row.mime_type,
                    a.download_url = row.download_url,
                    a.created_at = row.created_at,
                    a.updated_at = row.updated_at,
                    a.source_timestamp = row.source_timestamp,
                    a.extraction_tier = row.extraction_tier,
                    a.extraction_method = row.extraction_method,
                    a.confidence = row.confidence,
                    a.extractor_version = row.extractor_version
                MERGE (a)-[:BELONGS_TO]->(rel)
                RETURN count(a) AS created_count
                """

                result = session.run(query, {"rows": batch})
                summary = result.consume()

                total_written += len(batch)
                batches_executed += 1

                logger.debug(
                    f"Wrote binary asset batch {batches_executed}: "
                    f"{len(batch)} rows, "
                    f"counters={summary.counters}"
                )

        logger.info(f"Wrote {total_written} BinaryAsset node(s) in {batches_executed} batch(es)")

        return {"total_written": total_written, "batches_executed": batches_executed}


# Export public API
__all__ = ["GitHubWriter"]
