# ADR 0002: Select Qwen3 Models for Embeddings and LLM Windows

- Status: Accepted
- Date: 2025-02-24
- Stakeholders: Extraction, Retrieval, Inference infrastructure

## Context

We evaluated several open-source and closed-source models (Llama 3, Mistral, MiniCPM, Qwen2/Qwen3) for both embedding generation and Tier C reasoning. Key criteria were accuracy on domain QA benchmarks, GPU memory footprint for self-hosting, and licensing constraints for commercial redistribution.

## Decision

Adopt Qwen3-Embedding-0.6B via TEI for chunk embeddings and Qwen3-4B-Instruct via Ollama for Tier C question answering. Both models fit within a single RTX 4070 while delivering >5% accuracy gains over baseline Llama 3 8B on our internal domain QA set.

## Consequences

- ✅ Strong multilingual coverage and factual QA performance at modest GPU cost.
- ✅ Apache 2.0 licensing simplifies redistribution and edge deployments.
- ⚠️ Requires periodic model updates as Alibaba releases new checkpoints.
- ⚠️ Slightly slower warm start time than smaller Mistral-class models.
