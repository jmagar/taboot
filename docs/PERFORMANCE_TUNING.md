# Performance Tuning Guide (T173-T175)

This document provides guidance on tuning Taboot for optimal performance on your hardware.

## Batch Size Optimization

### Tier C LLM Batching (T173)

**Current Configuration**: 8-16 windows per batch
**Target**: ≤250ms median latency, ≤750ms p95

**Tuning Parameters** ([packages/extraction/tier_c/llm_client.py](../packages/extraction/tier_c/llm_client.py)):
```python
BATCH_SIZE = 8  # Default, increase for better GPU utilization
MAX_BATCH_SIZE = 16  # Upper limit to prevent OOM
```

**How to Tune**:
1. Monitor GPU memory usage: `nvidia-smi -l 1`
2. Monitor inference latency in extraction logs
3. Increase batch size if:
   - GPU memory < 80% utilized
   - Latency p95 < 500ms
4. Decrease batch size if:
   - GPU OOM errors occur
   - Latency p95 > 750ms

**Optimal Settings by GPU**:
- RTX 4070 (12GB): 12-16 windows
- RTX 3090 (24GB): 16-24 windows
- RTX 3060 (12GB): 8-12 windows
- CPU-only: 4-8 windows

---

### Neo4j Batch Writes (T174)

**Current Configuration**: 2,000-row UNWIND batches
**Target**: ≥20,000 edges/min throughput

**Tuning Parameters** ([packages/graph/writers/batched.py](../packages/graph/writers/batched.py)):
```python
BATCH_SIZE = 2000  # Rows per UNWIND operation
```

**How to Tune**:
1. Monitor Neo4j write throughput in logs
2. Check Neo4j heap usage: `CALL dbms.queryJmx('java.lang:type=Memory')`
3. Increase batch size if:
   - Neo4j heap < 80% utilized
   - Write throughput < 15k edges/min
4. Decrease batch size if:
   - Neo4j heap warnings appear
   - Transaction timeouts occur

**Optimal Settings**:
- Default (4GB heap): 2,000 rows
- Large (8GB heap): 3,000-4,000 rows
- Extra Large (16GB heap): 5,000-6,000 rows

---

### Qdrant Vector Upserts (T175)

**Current Configuration**: Auto-batching by Qdrant client
**Target**: ≥5,000 vectors/sec

**Tuning Parameters** ([packages/vector/writer.py](../packages/vector/writer.py)):
```python
UPSERT_BATCH_SIZE = 100  # Vectors per upsert call
```

**How to Tune**:
1. Monitor Qdrant throughput: check collection stats
2. Monitor HNSW indexing queue: `GET /collections/{name}`
3. Increase batch size if:
   - Network latency is low (<5ms)
   - Qdrant CPU < 70%
4. Decrease batch size if:
   - High network latency (>20ms)
   - Qdrant indexing queue grows

**Optimal Settings**:
- Local deployment: 200-500 vectors
- Remote deployment (<10ms latency): 100-200 vectors
- Remote deployment (>10ms latency): 50-100 vectors

---

## General Performance Guidelines

### GPU Memory Management

Monitor GPU memory usage to prevent OOM:

```bash
# Watch GPU utilization
nvidia-smi -l 1

# If GPU memory >90%, reduce:
# - Tier C batch size (8 → 6)
# - TEI batch size (if applicable)
# - Qdrant HNSW ef_construct (200 → 150)
```

### CPU Optimization

For CPU-bound operations (Tier A, Tier B):

```bash
# Check CPU usage
htop

# If CPU maxed out:
# - Reduce worker concurrency
# - Increase Tier A/B batch sizes to reduce overhead
# - Consider scaling horizontally (multiple workers)
```

### Network Optimization

For distributed deployments:

```bash
# Test latency
ping -c 10 <qdrant-host>
ping -c 10 <neo4j-host>

# If latency >10ms:
# - Reduce batch sizes to prevent timeouts
# - Increase connection pool sizes
# - Enable compression (Qdrant gRPC, Neo4j bolt)
```

---

## Monitoring & Benchmarking

### Key Metrics to Track

1. **Tier C Latency**: p50, p95, p99 from logs
2. **Neo4j Write Throughput**: edges/min from metrics
3. **Qdrant Upsert Throughput**: vectors/sec from Qdrant stats
4. **GPU Memory**: % utilization from nvidia-smi
5. **Cache Hit Rate**: % from Redis INFO stats

### Running Benchmarks

```bash
# Extract 100 documents and measure performance
uv run apps/cli extract pending --limit 100

# Check metrics
uv run apps/cli extract status

# Target values (RTX 4070):
# - Tier A: ≥50 pages/sec
# - Tier B: ≥200 sentences/sec
# - Tier C: ≤250ms median, ≤750ms p95
# - Neo4j: ≥20k edges/min
# - Qdrant: ≥5k vectors/sec
```

---

## Troubleshooting

### Slow Tier C Performance

**Symptoms**: p95 latency >750ms

**Solutions**:
1. Reduce batch size: 16 → 8
2. Check Ollama GPU utilization
3. Verify Qwen3-4B model loaded correctly
4. Check Redis cache hit rate (should be >60%)

### Neo4j Write Bottleneck

**Symptoms**: Write throughput <15k edges/min

**Solutions**:
1. Increase batch size: 2k → 3k rows
2. Check Neo4j heap size (min 4GB recommended)
3. Verify APOC plugin installed
4. Check index/constraint creation completed

### Qdrant Indexing Lag

**Symptoms**: Search results delayed, indexing queue grows

**Solutions**:
1. Reduce upsert batch size: 100 → 50
2. Check Qdrant CPU/memory usage
3. Consider increasing `ef_construct` for better quality
4. Enable disk-backed storage for large collections

---

## Production Recommendations

For production deployments:

1. **Start Conservative**: Use default batch sizes initially
2. **Monitor for 24h**: Collect baseline metrics
3. **Tune Incrementally**: Adjust one parameter at a time
4. **Validate Performance**: Re-run benchmarks after each change
5. **Document Changes**: Track tuning decisions in ops runbook

**Never** tune multiple parameters simultaneously - you won't know which change caused the impact.
