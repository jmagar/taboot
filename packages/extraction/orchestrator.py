"""Extraction orchestrator coordinating Tier A → B → C execution.

Orchestrates the complete extraction pipeline with state management in Redis.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from redis.asyncio import Redis

from packages.extraction.tier_a.patterns import EntityPatternMatcher
from packages.extraction.tier_b.window_selector import WindowSelector
from packages.extraction.tier_c.llm_client import TierCLLMClient
from packages.extraction.types import CodeBlock, ExtractionWindow, Table
from packages.schemas.models import ExtractionJob, ExtractionState

logger = logging.getLogger(__name__)


class TierAParser(Protocol):
    """Protocol for Tier A parser with deterministic extraction methods."""

    def parse_code_blocks(self, content: str) -> list[CodeBlock]:
        """Extract fenced code blocks from markdown content.

        Args:
            content: Markdown text content.

        Returns:
            list[CodeBlock]: List of code blocks with language and code.
        """
        ...

    def parse_tables(self, content: str) -> list[Table]:
        """Extract markdown tables from content.

        Args:
            content: Markdown text content.

        Returns:
            list[Table]: List of tables with headers and rows.
        """
        ...


class ExtractionOrchestrator:
    """Orchestrates multi-tier extraction pipeline (Tier A → B → C).

    Coordinates deterministic extraction (Tier A), spaCy NLP window selection (Tier B),
    and LLM extraction (Tier C) with Redis state tracking.

    Attributes:
        tier_a_parser: Parser module for code blocks and tables.
        tier_a_patterns: Pattern matcher for known entities.
        window_selector: Tier B window selector.
        llm_client: Tier C LLM client.
        redis_client: Redis client for state management.
    """

    MAX_RETRIES = 3

    def __init__(
        self,
        tier_a_parser: TierAParser,
        tier_a_patterns: EntityPatternMatcher,
        window_selector: WindowSelector,
        llm_client: TierCLLMClient,
        redis_client: Redis[Any],
    ) -> None:
        """Initialize ExtractionOrchestrator.

        Args:
            tier_a_parser: Parser module with parse_code_blocks and parse_tables.
            tier_a_patterns: EntityPatternMatcher for pattern matching.
            window_selector: WindowSelector for Tier B.
            llm_client: TierCLLMClient for Tier C.
            redis_client: Redis client (async) for state management.
        """
        self.tier_a_parser = tier_a_parser
        self.tier_a_patterns = tier_a_patterns
        self.window_selector = window_selector
        self.llm_client = llm_client
        self.redis_client = redis_client

        logger.info("Initialized ExtractionOrchestrator")

    async def process_document(self, doc_id: UUID, content: str) -> ExtractionJob:
        """Process a document through the full extraction pipeline.

        Pipeline flow:
        1. Create ExtractionJob (state=PENDING)
        2. Run Tier A → transition to TIER_A_DONE
        3. Run Tier B → transition to TIER_B_DONE
        4. Run Tier C → transition to TIER_C_DONE
        5. Finalize → transition to COMPLETED (or FAILED on error)

        Args:
            doc_id: Document UUID.
            content: Document text content.

        Returns:
            ExtractionJob: Job with final state and metrics.
        """
        # Step 1: Create job in PENDING state
        job = self._create_job(doc_id)
        await self._update_state(job.job_id, ExtractionState.PENDING, job)
        logger.info(f"Created extraction job {job.job_id} for doc {doc_id}")

        retry_count = 0

        while retry_count <= self.MAX_RETRIES:
            try:
                # Step 2: Run Tier A
                tier_a_triples = await self._run_tier_a(content)
                job = job.model_copy(update={"tier_a_triples": tier_a_triples})
                await self._update_state(job.job_id, ExtractionState.TIER_A_DONE, job)
                logger.info(f"Tier A complete: {tier_a_triples} triples")

                # Step 3: Run Tier B
                tier_b_windows = await self._run_tier_b(content)
                job = job.model_copy(update={"tier_b_windows": len(tier_b_windows)})
                await self._update_state(job.job_id, ExtractionState.TIER_B_DONE, job)
                logger.info(f"Tier B complete: {len(tier_b_windows)} windows")

                # Step 4: Run Tier C
                tier_c_triples = await self._run_tier_c(tier_b_windows)
                job = job.model_copy(update={"tier_c_triples": tier_c_triples})
                await self._update_state(job.job_id, ExtractionState.TIER_C_DONE, job)
                logger.info(f"Tier C complete: {tier_c_triples} triples")

                # Step 5: Transition to COMPLETED
                job = job.model_copy(
                    update={
                        "state": ExtractionState.COMPLETED,
                        "completed_at": datetime.now(UTC),
                    }
                )
                await self._update_state(job.job_id, ExtractionState.COMPLETED, job)
                logger.info(
                    f"Extraction job {job.job_id} completed: "
                    f"tier_a={job.tier_a_triples}, tier_b={job.tier_b_windows}, "
                    f"tier_c={job.tier_c_triples}"
                )

                return job

            except Exception as e:
                retry_count += 1
                logger.error(
                    f"Extraction job {job.job_id} failed "
                    f"(retry {retry_count}/{self.MAX_RETRIES}): {e}",
                    exc_info=True,
                )

                # Update retry count
                job = job.model_copy(update={"retry_count": retry_count})

                # If max retries reached, transition to FAILED
                if retry_count >= self.MAX_RETRIES:
                    error_entry = {
                        "error": str(e),
                        "timestamp": datetime.now(UTC).isoformat(),
                        "retry_count": retry_count,
                    }

                    job = job.model_copy(
                        update={
                            "state": ExtractionState.FAILED,
                            "completed_at": datetime.now(UTC),
                            "errors": error_entry,
                        }
                    )
                    await self._update_state(job.job_id, ExtractionState.FAILED, job)
                    logger.error(f"Extraction job {job.job_id} failed after {retry_count} retries")
                    return job

        # Should never reach here, but fallback to FAILED state
        job = job.model_copy(
            update={
                "state": ExtractionState.FAILED,
                "completed_at": datetime.now(UTC),
            }
        )
        return job

    def _create_job(self, doc_id: UUID) -> ExtractionJob:
        """Create a new ExtractionJob in PENDING state.

        Args:
            doc_id: Document UUID.

        Returns:
            ExtractionJob: Job in PENDING state.
        """
        return ExtractionJob(
            job_id=uuid4(),
            doc_id=doc_id,
            state=ExtractionState.PENDING,
            tier_a_triples=0,
            tier_b_windows=0,
            tier_c_triples=0,
            started_at=datetime.now(UTC),
            retry_count=0,
        )

    async def _run_tier_a(self, content: str) -> int:
        """Run Tier A deterministic extraction.

        Args:
            content: Document text content.

        Returns:
            int: Count of triples extracted.
        """
        # Parse code blocks and tables
        code_blocks = self.tier_a_parser.parse_code_blocks(content)
        tables = self.tier_a_parser.parse_tables(content)

        # Find entity patterns
        pattern_matches = self.tier_a_patterns.find_matches(content)

        # Count triples: each pattern match is a potential triple
        # (In a real implementation, this would create actual Triple objects)
        triple_count = len(pattern_matches)

        logger.debug(
            f"Tier A: {len(code_blocks)} code blocks, {len(tables)} tables, "
            f"{len(pattern_matches)} pattern matches → {triple_count} triples"
        )

        return triple_count

    async def _run_tier_b(self, content: str) -> list[ExtractionWindow]:
        """Run Tier B spaCy NLP extraction to select micro-windows.

        Args:
            content: Document text content.

        Returns:
            list[ExtractionWindow]: Selected windows for Tier C processing.
        """
        # Use window selector to create micro-windows
        windows = self.window_selector.select_windows(content)

        logger.debug(f"Tier B: selected {len(windows)} windows")

        return windows

    async def _run_tier_c(self, windows: list[ExtractionWindow]) -> int:
        """Run Tier C LLM extraction on windows.

        Args:
            windows: List of windows from Tier B.

        Returns:
            int: Count of triples extracted.
        """
        if not windows:
            return 0

        # Extract window content strings
        window_contents = [w["content"] for w in windows]

        # Run batched LLM extraction
        results = await self.llm_client.batch_extract(window_contents)

        # Count total triples
        triple_count = sum(len(result.triples) for result in results)

        logger.debug(f"Tier C: processed {len(windows)} windows → {triple_count} triples")

        return triple_count

    async def _update_state(
        self, job_id: UUID, new_state: ExtractionState, job: ExtractionJob
    ) -> None:
        """Update extraction job state in Redis.

        Args:
            job_id: Job UUID.
            new_state: New extraction state.
            job: Current job object.
        """
        # Store job state in Redis
        # Key format: extraction_job:{job_id}
        key = f"extraction_job:{job_id}"
        value = job.model_dump_json()

        await self.redis_client.set(key, value)

        logger.debug(f"Updated state for job {job_id}: {new_state.value}")


# Export public API
__all__ = ["ExtractionOrchestrator"]
