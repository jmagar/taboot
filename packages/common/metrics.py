"""Metrics collection system for Taboot platform.

Tracks extraction metrics using Redis backend per FR-033:
- Windows/sec throughput
- Tier hit ratios (A/B/C)
- LLM p95 latency
- Cache hit rate
- DB throughput (edges/min)

All metrics are persisted in Redis with atomic operations.
"""

import time

from pydantic import BaseModel, Field
from redis import asyncio as aioredis

from packages.common.logging import get_logger

logger = get_logger(__name__)


class MetricsSnapshot(BaseModel):
    """Snapshot of current metrics state.

    Attributes:
        total_windows: Total windows processed across all tiers.
        tier_a_windows: Windows processed by Tier A (deterministic).
        tier_b_windows: Windows processed by Tier B (spaCy).
        tier_c_windows: Windows processed by Tier C (LLM).
        tier_a_ratio: Fraction of windows processed by Tier A (0.0-1.0).
        tier_b_ratio: Fraction of windows processed by Tier B (0.0-1.0).
        tier_c_ratio: Fraction of windows processed by Tier C (0.0-1.0).
        cache_hits: Total cache hits (Tier C).
        cache_misses: Total cache misses (Tier C).
        cache_hit_rate: Cache hit rate (0.0-1.0).
        db_writes_total: Total database edges/nodes written.
        db_write_operations: Number of DB write operations.
        tier_c_p50: Tier C median latency (ms).
        tier_c_p95: Tier C 95th percentile latency (ms).
        tier_c_p99: Tier C 99th percentile latency (ms).
        windows_per_second: Windows processed per second.
        db_edges_per_minute: Database edges written per minute.
        timestamp: Unix timestamp of snapshot.
    """

    total_windows: int = Field(..., ge=0, description="Total windows processed")
    tier_a_windows: int = Field(..., ge=0, description="Tier A windows")
    tier_b_windows: int = Field(..., ge=0, description="Tier B windows")
    tier_c_windows: int = Field(..., ge=0, description="Tier C windows")
    tier_a_ratio: float = Field(..., ge=0.0, le=1.0, description="Tier A ratio")
    tier_b_ratio: float = Field(..., ge=0.0, le=1.0, description="Tier B ratio")
    tier_c_ratio: float = Field(..., ge=0.0, le=1.0, description="Tier C ratio")
    cache_hits: int = Field(..., ge=0, description="Cache hits")
    cache_misses: int = Field(..., ge=0, description="Cache misses")
    cache_hit_rate: float = Field(..., ge=0.0, le=1.0, description="Cache hit rate")
    db_writes_total: int = Field(..., ge=0, description="Total DB writes")
    db_write_operations: int = Field(..., ge=0, description="DB write operations")
    tier_c_p50: float = Field(..., ge=0.0, description="Tier C p50 latency (ms)")
    tier_c_p95: float = Field(..., ge=0.0, description="Tier C p95 latency (ms)")
    tier_c_p99: float = Field(..., ge=0.0, description="Tier C p99 latency (ms)")
    windows_per_second: float = Field(..., ge=0.0, description="Windows per second")
    db_edges_per_minute: float = Field(..., ge=0.0, description="DB edges per minute")
    timestamp: float = Field(..., description="Snapshot timestamp")


class MetricsCollector:
    """Metrics collector with Redis backend.

    Uses Redis for atomic counters and sorted sets for latency percentiles.
    All operations are async and thread-safe.
    """

    # Redis key prefixes
    KEY_PREFIX = "taboot:metrics"
    TIER_COUNTER = f"{KEY_PREFIX}:tier:{{tier}}:count"
    TIER_LATENCIES = f"{KEY_PREFIX}:tier:{{tier}}:latencies"
    CACHE_HITS = f"{KEY_PREFIX}:cache:hits"
    CACHE_MISSES = f"{KEY_PREFIX}:cache:misses"
    DB_WRITES_TOTAL = f"{KEY_PREFIX}:db:writes:total"
    DB_WRITE_OPS = f"{KEY_PREFIX}:db:writes:ops"
    DB_WRITE_DURATIONS = f"{KEY_PREFIX}:db:write:durations"
    FIRST_WINDOW_TIME = f"{KEY_PREFIX}:window:first_time"

    def __init__(self, redis_client: aioredis.Redis) -> None:
        """Initialize metrics collector.

        Args:
            redis_client: Async Redis client for persistence.
        """
        self._redis = redis_client

    async def record_window_processed(self, tier: str, latency_ms: float) -> None:
        """Record a window processing event.

        Args:
            tier: Extraction tier ("A", "B", or "C").
            latency_ms: Processing latency in milliseconds.

        Raises:
            ValueError: If tier is not "A", "B", or "C".
        """
        if tier not in ("A", "B", "C"):
            raise ValueError(f"Invalid tier: {tier}. Must be 'A', 'B', or 'C'")

        # Increment tier counter
        counter_key = self.TIER_COUNTER.format(tier=tier)
        await self._redis.incr(counter_key)

        # Record latency in sorted set (score = latency, member = timestamp:latency)
        latencies_key = self.TIER_LATENCIES.format(tier=tier)
        timestamp = time.time()
        member = f"{timestamp}:{latency_ms}"
        await self._redis.zadd(latencies_key, {member: latency_ms})

        # Record first window time if not set
        await self._redis.setnx(self.FIRST_WINDOW_TIME, timestamp)

        logger.debug(
            "Recorded window processing",
            extra={"tier": tier, "latency_ms": latency_ms},
        )

    async def record_cache_hit(self) -> None:
        """Record a cache hit event."""
        await self._redis.incr(self.CACHE_HITS)
        logger.debug("Recorded cache hit")

    async def record_cache_miss(self) -> None:
        """Record a cache miss event."""
        await self._redis.incr(self.CACHE_MISSES)
        logger.debug("Recorded cache miss")

    async def record_db_write(self, count: int, duration_ms: float) -> None:
        """Record a database write operation.

        Args:
            count: Number of edges/nodes written.
            duration_ms: Write operation duration in milliseconds.

        Raises:
            ValueError: If count is negative or duration_ms is negative.
        """
        if count < 0:
            raise ValueError(f"Invalid count: {count}. Must be non-negative")
        if duration_ms < 0.0:
            raise ValueError(f"Invalid duration_ms: {duration_ms}. Must be non-negative")

        # Increment total writes
        await self._redis.incrby(self.DB_WRITES_TOTAL, count)

        # Increment operation count
        await self._redis.incr(self.DB_WRITE_OPS)

        # Record duration in sorted set
        timestamp = time.time()
        member = f"{timestamp}:{duration_ms}:{count}"
        await self._redis.zadd(self.DB_WRITE_DURATIONS, {member: timestamp})

        logger.debug(
            "Recorded DB write",
            extra={"count": count, "duration_ms": duration_ms},
        )

    async def get_metrics(self) -> MetricsSnapshot:
        """Get current metrics snapshot.

        Returns:
            MetricsSnapshot: Current metrics state.
        """
        # Get tier counters
        tier_a_count = await self._get_counter(self.TIER_COUNTER.format(tier="A"))
        tier_b_count = await self._get_counter(self.TIER_COUNTER.format(tier="B"))
        tier_c_count = await self._get_counter(self.TIER_COUNTER.format(tier="C"))
        total_windows = tier_a_count + tier_b_count + tier_c_count

        # Calculate tier ratios
        tier_a_ratio = tier_a_count / total_windows if total_windows > 0 else 0.0
        tier_b_ratio = tier_b_count / total_windows if total_windows > 0 else 0.0
        tier_c_ratio = tier_c_count / total_windows if total_windows > 0 else 0.0

        # Get cache metrics
        cache_hits = await self._get_counter(self.CACHE_HITS)
        cache_misses = await self._get_counter(self.CACHE_MISSES)
        total_cache_ops = cache_hits + cache_misses
        cache_hit_rate = cache_hits / total_cache_ops if total_cache_ops > 0 else 0.0

        # Get DB metrics
        db_writes_total = await self._get_counter(self.DB_WRITES_TOTAL)
        db_write_ops = await self._get_counter(self.DB_WRITE_OPS)

        # Get Tier C percentiles
        tier_c_latencies = await self._get_sorted_set_values(self.TIER_LATENCIES.format(tier="C"))
        tier_c_p50 = self._calculate_percentile(tier_c_latencies, 50) if tier_c_latencies else 0.0
        tier_c_p95 = self._calculate_percentile(tier_c_latencies, 95) if tier_c_latencies else 0.0
        tier_c_p99 = self._calculate_percentile(tier_c_latencies, 99) if tier_c_latencies else 0.0

        # Calculate throughput (windows/sec)
        windows_per_second = await self._calculate_windows_per_second(total_windows)

        # Calculate DB throughput (edges/min)
        db_edges_per_minute = await self._calculate_db_edges_per_minute()

        return MetricsSnapshot(
            total_windows=total_windows,
            tier_a_windows=tier_a_count,
            tier_b_windows=tier_b_count,
            tier_c_windows=tier_c_count,
            tier_a_ratio=tier_a_ratio,
            tier_b_ratio=tier_b_ratio,
            tier_c_ratio=tier_c_ratio,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            cache_hit_rate=cache_hit_rate,
            db_writes_total=db_writes_total,
            db_write_operations=db_write_ops,
            tier_c_p50=tier_c_p50,
            tier_c_p95=tier_c_p95,
            tier_c_p99=tier_c_p99,
            windows_per_second=windows_per_second,
            db_edges_per_minute=db_edges_per_minute,
            timestamp=time.time(),
        )

    async def _get_counter(self, key: str) -> int:
        """Get counter value from Redis.

        Args:
            key: Redis key.

        Returns:
            int: Counter value (0 if not exists).
        """
        value = await self._redis.get(key)
        return int(value) if value is not None else 0

    async def _get_sorted_set_values(self, key: str) -> list[float]:
        """Get all values from a sorted set.

        Args:
            key: Redis sorted set key.

        Returns:
            list[float]: List of scores (values) from the sorted set.
        """
        # Get all members with scores
        members_with_scores = await self._redis.zrange(key, 0, -1, withscores=True)

        # Extract scores (latencies)
        return [float(score) for _, score in members_with_scores]

    def _calculate_percentile(self, values: list[float], percentile: int) -> float:
        """Calculate percentile from sorted values.

        Args:
            values: List of values (unsorted).
            percentile: Percentile to calculate (0-100).

        Returns:
            float: Percentile value.
        """
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = int(len(sorted_values) * (percentile / 100.0))
        # Clamp index to valid range
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]

    async def _calculate_windows_per_second(self, total_windows: int) -> float:
        """Calculate windows per second throughput.

        Args:
            total_windows: Total windows processed.

        Returns:
            float: Windows per second.
        """
        if total_windows == 0:
            return 0.0

        # Get first window timestamp
        first_time_str = await self._redis.get(self.FIRST_WINDOW_TIME)
        if first_time_str is None:
            return 0.0

        first_time = float(first_time_str)
        current_time = time.time()
        elapsed_seconds = current_time - first_time

        if elapsed_seconds <= 0.0:
            return 0.0

        return total_windows / elapsed_seconds

    async def _calculate_db_edges_per_minute(self) -> float:
        """Calculate database edges per minute throughput.

        Returns:
            float: Edges per minute.
        """
        # Get all DB write events from sorted set
        members_with_scores = await self._redis.zrange(
            self.DB_WRITE_DURATIONS, 0, -1, withscores=True
        )

        if not members_with_scores:
            return 0.0

        # Parse members to extract count and timestamp
        total_edges = 0
        min_timestamp = float("inf")
        max_timestamp = 0.0

        for member, _timestamp_score in members_with_scores:
            # Member format: "timestamp:duration_ms:count"
            parts = member.split(":")
            if len(parts) == 3:
                timestamp = float(parts[0])
                count = int(parts[2])
                total_edges += count
                min_timestamp = min(min_timestamp, timestamp)
                max_timestamp = max(max_timestamp, timestamp)

        if total_edges == 0 or min_timestamp == float("inf"):
            return 0.0

        elapsed_minutes = (max_timestamp - min_timestamp) / 60.0
        if elapsed_minutes <= 0.0:
            # All writes happened at once, use 1 second as minimum
            elapsed_minutes = 1.0 / 60.0

        return total_edges / elapsed_minutes


# Export public API
__all__ = ["MetricsCollector", "MetricsSnapshot"]
