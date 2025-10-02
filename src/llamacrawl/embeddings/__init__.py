"""Embedding models for LlamaCrawl.

This package provides custom embedding integrations for use with LlamaIndex,
including TEI (Text Embeddings Inference) support for self-hosted models
and reranking capabilities.
"""

from llamacrawl.embeddings.reranker import TEIRerank
from llamacrawl.embeddings.tei import TEIEmbedding

__all__ = ["TEIEmbedding", "TEIRerank"]
