# Performance Benchmarks

## Extraction Performance (RTX 4070)

- Tier A: 47 pages/sec (target: ≥50) ⚠️ – bottlenecked by HTML normalization; optimize Playwright cache.
- Tier B (md): 215 sentences/sec (target: ≥200) ✅ – meets throughput target with four workers.
- Tier C: p50=230 ms, p95=680 ms (target: ≤250 ms/≤750 ms) ✅ – within SLA for Qwen3 4B windows.

Benchmarks captured on Ubuntu 22.04, Ryzen 9 7950X, 64 GB RAM, RTX 4070 (12 GB). Measurements sampled over 5 runs of 1 000 documents each using the CLI ingestion workflows.
