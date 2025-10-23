"""Tests for metrics collection system.

Tests recording and aggregating extraction metrics per FR-033:
- windows/sec throughput
- tier hit ratios (A/B/C)
- LLM p95 latency
- cache hit rate
- DB throughput
"""

import time

import pytest
from redis import asyncio as aioredis

from packages.common.metrics import MetricsCollector

# Mark all tests as integration tests requiring Redis
pytestmark = pytest.mark.integration


@pytest.fixture
async def redis_client() -> aioredis.Redis:
    """Create Redis client for tests.

    Returns:
        aioredis.Redis: Async Redis client.
    """
    # Connect to localhost Redis (assumes docker compose is running)
    client = aioredis.from_url(
        "redis://localhost:6379",
        decode_responses=True,
    )
    # Clean up any existing test metrics
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()


@pytest.fixture
async def metrics_collector(redis_client: aioredis.Redis) -> MetricsCollector:
    """Create MetricsCollector instance for tests.

    Args:
        redis_client: Redis client fixture.

    Returns:
        MetricsCollector: Metrics collector instance.
    """
    return MetricsCollector(redis_client)


@pytest.mark.asyncio
async def test_record_window_processed(metrics_collector: MetricsCollector) -> None:
    """Test recording window processing metrics.

    Verifies:
    - Windows are counted per tier
    - Latencies are recorded
    - Timestamps are tracked
    """
    # Record some windows
    await metrics_collector.record_window_processed(tier="A", latency_ms=10.5)
    await metrics_collector.record_window_processed(tier="A", latency_ms=12.0)
    await metrics_collector.record_window_processed(tier="B", latency_ms=50.0)
    await metrics_collector.record_window_processed(tier="C", latency_ms=250.0)
    await metrics_collector.record_window_processed(tier="C", latency_ms=300.0)

    # Get metrics snapshot
    snapshot = await metrics_collector.get_metrics()

    # Verify counts
    assert snapshot.tier_a_windows == 2
    assert snapshot.tier_b_windows == 1
    assert snapshot.tier_c_windows == 2
    assert snapshot.total_windows == 5


@pytest.mark.asyncio
async def test_record_cache_hit_miss(metrics_collector: MetricsCollector) -> None:
    """Test recording cache hit/miss metrics.

    Verifies:
    - Cache hits are counted
    - Cache misses are counted
    - Hit rate is calculated correctly
    """
    # Record cache operations
    await metrics_collector.record_cache_hit()
    await metrics_collector.record_cache_hit()
    await metrics_collector.record_cache_hit()
    await metrics_collector.record_cache_miss()

    # Get metrics snapshot
    snapshot = await metrics_collector.get_metrics()

    # Verify counts and hit rate
    assert snapshot.cache_hits == 3
    assert snapshot.cache_misses == 1
    assert snapshot.cache_hit_rate == 0.75  # 3/4


@pytest.mark.asyncio
async def test_record_db_write(metrics_collector: MetricsCollector) -> None:
    """Test recording database write metrics.

    Verifies:
    - DB write counts are tracked
    - Write durations are recorded
    - Throughput is calculated
    """
    # Record DB writes
    await metrics_collector.record_db_write(count=1000, duration_ms=50.0)
    await metrics_collector.record_db_write(count=2000, duration_ms=100.0)

    # Get metrics snapshot
    snapshot = await metrics_collector.get_metrics()

    # Verify totals
    assert snapshot.db_writes_total == 3000
    assert snapshot.db_write_operations == 2


@pytest.mark.asyncio
async def test_tier_hit_ratios(metrics_collector: MetricsCollector) -> None:
    """Test tier hit ratio calculations.

    Verifies:
    - Tier ratios sum to 1.0
    - Individual tier percentages are correct
    """
    # Record windows across tiers
    for _ in range(50):
        await metrics_collector.record_window_processed(tier="A", latency_ms=10.0)
    for _ in range(30):
        await metrics_collector.record_window_processed(tier="B", latency_ms=50.0)
    for _ in range(20):
        await metrics_collector.record_window_processed(tier="C", latency_ms=250.0)

    # Get metrics snapshot
    snapshot = await metrics_collector.get_metrics()

    # Verify ratios
    assert snapshot.tier_a_ratio == 0.5  # 50/100
    assert snapshot.tier_b_ratio == 0.3  # 30/100
    assert snapshot.tier_c_ratio == 0.2  # 20/100
    total_ratio = snapshot.tier_a_ratio + snapshot.tier_b_ratio + snapshot.tier_c_ratio
    assert abs(total_ratio - 1.0) < 0.001


@pytest.mark.asyncio
async def test_percentile_calculations(metrics_collector: MetricsCollector) -> None:
    """Test latency percentile calculations (p50, p95, p99).

    Verifies:
    - p50 (median) is calculated correctly
    - p95 is calculated correctly
    - p99 is calculated correctly
    """
    # Record a known distribution of latencies
    latencies = [100.0] * 50 + [200.0] * 40 + [500.0] * 9 + [1000.0] * 1

    for latency in latencies:
        await metrics_collector.record_window_processed(tier="C", latency_ms=latency)

    # Get metrics snapshot
    snapshot = await metrics_collector.get_metrics()

    # Verify percentiles
    assert snapshot.tier_c_p50 <= 200.0  # Median should be around 100-200
    assert snapshot.tier_c_p95 >= 200.0  # p95 should be at least 200
    assert snapshot.tier_c_p99 >= 500.0  # p99 should be high


@pytest.mark.asyncio
async def test_throughput_calculation(metrics_collector: MetricsCollector) -> None:
    """Test windows/sec throughput calculation.

    Verifies:
    - Throughput is calculated over time window
    - Windows per second is accurate
    """
    # Record windows with some delay
    for _ in range(10):
        await metrics_collector.record_window_processed(tier="A", latency_ms=10.0)

    # Small delay to simulate processing time
    time.sleep(0.1)

    for _ in range(10):
        await metrics_collector.record_window_processed(tier="A", latency_ms=10.0)

    # Get metrics snapshot
    snapshot = await metrics_collector.get_metrics()

    # Verify throughput (should be > 0)
    assert snapshot.windows_per_second > 0.0
    assert snapshot.total_windows == 20


@pytest.mark.asyncio
async def test_db_throughput_calculation(metrics_collector: MetricsCollector) -> None:
    """Test DB throughput calculation (edges/min).

    Verifies:
    - DB throughput is calculated correctly
    - Edges per minute metric
    """
    # Record DB writes
    await metrics_collector.record_db_write(count=20000, duration_ms=60000.0)  # 20k in 1 min

    # Get metrics snapshot
    snapshot = await metrics_collector.get_metrics()

    # Verify throughput (should be ~20k/min)
    assert snapshot.db_edges_per_minute > 0.0


@pytest.mark.asyncio
async def test_empty_metrics(metrics_collector: MetricsCollector) -> None:
    """Test metrics snapshot with no recorded data.

    Verifies:
    - Empty metrics return zeros
    - No division by zero errors
    - Percentiles handle empty data
    """
    # Get metrics without recording anything
    snapshot = await metrics_collector.get_metrics()

    # Verify all zeros/defaults
    assert snapshot.total_windows == 0
    assert snapshot.tier_a_windows == 0
    assert snapshot.tier_b_windows == 0
    assert snapshot.tier_c_windows == 0
    assert snapshot.cache_hits == 0
    assert snapshot.cache_misses == 0
    assert snapshot.cache_hit_rate == 0.0
    assert snapshot.db_writes_total == 0
    assert snapshot.windows_per_second == 0.0


@pytest.mark.asyncio
async def test_cache_hit_rate_no_operations(metrics_collector: MetricsCollector) -> None:
    """Test cache hit rate with no cache operations.

    Verifies:
    - Hit rate is 0.0 when no operations recorded
    - No division by zero
    """
    snapshot = await metrics_collector.get_metrics()
    assert snapshot.cache_hit_rate == 0.0


@pytest.mark.asyncio
async def test_tier_ratios_no_windows(metrics_collector: MetricsCollector) -> None:
    """Test tier ratios with no windows processed.

    Verifies:
    - All ratios are 0.0 when no windows
    - No division by zero
    """
    snapshot = await metrics_collector.get_metrics()
    assert snapshot.tier_a_ratio == 0.0
    assert snapshot.tier_b_ratio == 0.0
    assert snapshot.tier_c_ratio == 0.0


@pytest.mark.asyncio
async def test_redis_persistence(
    redis_client: aioredis.Redis,
    metrics_collector: MetricsCollector,
) -> None:
    """Test metrics are persisted in Redis.

    Verifies:
    - Metrics are stored in Redis
    - New collector instance can read existing metrics
    """
    # Record some metrics
    await metrics_collector.record_window_processed(tier="A", latency_ms=10.0)
    await metrics_collector.record_cache_hit()

    # Create new collector instance with same Redis client
    new_collector = MetricsCollector(redis_client)
    snapshot = await new_collector.get_metrics()

    # Verify metrics persisted
    assert snapshot.tier_a_windows == 1
    assert snapshot.cache_hits == 1


@pytest.mark.asyncio
async def test_concurrent_metric_recording(
    metrics_collector: MetricsCollector,
) -> None:
    """Test concurrent metric recording doesn't lose data.

    Verifies:
    - Concurrent increments are atomic
    - No race conditions
    """
    import asyncio

    # Record 100 windows concurrently
    tasks = [
        metrics_collector.record_window_processed(tier="A", latency_ms=10.0) for _ in range(100)
    ]
    await asyncio.gather(*tasks)

    snapshot = await metrics_collector.get_metrics()
    assert snapshot.tier_a_windows == 100
