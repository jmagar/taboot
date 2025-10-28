# Evaluation Plan

How we measure retrieval quality and latency over time.

## Datasets

* **Seed set:** 200 Q&A pairs derived from your homelab docs, configs, and issues.
* **Augmented set:** synthetic questions with answerable spans, validated manually.
* Store in `datasets/` with `question`, `answers[]`, `doc_ids[]`.

## Metrics

* **Retrieval:** nDCG@k, MRR@k, Recall@k (k=5,10,20).
* **Latency:** search p50/p95, rerank latency, end-to-end time to first token.
* **Graph:** hit rate for entity-aware queries vs vector-only.

## Procedure

1. Build index snapshot `S_t`.
2. Run queries Q over `S_t` with settings `{ef_search, top_k, rerank_k}`.
3. Score with ground truth.
4. Record `{metrics, settings, commit_sha}` to `eval_runs/`.

## Ablations

* TEI embedding model variants.
* Reranker on/off and model choice.
* Chunk sizes 400/800/1200.
* Graph expansion depth 0/1/2.

## SLAs

* Search p95 < 200ms (pre-rerank).
* End-to-end answer generation < 3s p95 for typical questions.

## Reporting

* Generate HTML report per run with trend charts.
* Gate merges in CI if recall@10 drops > 5% from baseline.
