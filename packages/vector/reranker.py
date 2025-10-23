"""Reranking using Qwen3-Reranker-0.6B via SentenceTransformers."""

from typing import List
import torch
from sentence_transformers import CrossEncoder


class Reranker:
    """Rerank search results using cross-encoder model."""

    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-Reranker-0.6B",
        device: str = "auto",
        batch_size: int = 16
    ):
        """
        Initialize reranker with cross-encoder model.

        Args:
            model_name: HuggingFace model identifier
            device: Device to use ('cpu', 'cuda', 'auto')
            batch_size: Batch size for reranking
        """
        self.model_name = model_name
        self.batch_size = batch_size

        # Determine device
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        # Load cross-encoder model
        self.model = CrossEncoder(
            model_name=model_name,
            device=self.device,
            max_length=512
        )

        # Configure padding token for batch processing
        if self.model.tokenizer.pad_token is None:
            self.model.tokenizer.pad_token = self.model.tokenizer.eos_token
            self.model.tokenizer.pad_token_id = self.model.tokenizer.eos_token_id

        # Update model config to use padding token
        if hasattr(self.model.model, 'config'):
            self.model.model.config.pad_token_id = self.model.tokenizer.pad_token_id

    def rerank(
        self,
        query: str,
        passages: List[str],
        top_n: int = 5
    ) -> List[float]:
        """
        Rerank passages by relevance to query.

        Args:
            query: Query string
            passages: List of passage texts
            top_n: Number of top passages to return

        Returns:
            List of relevance scores for top_n passages
        """
        if not passages:
            return []

        # Create query-passage pairs
        pairs = [[query, passage] for passage in passages]

        # Score pairs in batches
        scores = self.model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False
        )

        # Get top-n scores
        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:top_n]

        return [float(scores[i]) for i in top_indices]

    def rerank_with_indices(
        self,
        query: str,
        passages: List[str],
        top_n: int = 5
    ) -> List[tuple[int, float]]:
        """
        Rerank passages and return indices with scores.

        Args:
            query: Query string
            passages: List of passage texts
            top_n: Number of top passages to return

        Returns:
            List of (index, score) tuples for top_n passages
        """
        if not passages:
            return []

        # Create query-passage pairs
        pairs = [[query, passage] for passage in passages]

        # Score pairs
        scores = self.model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False
        )

        # Get top-n (index, score) pairs
        scored_indices = [
            (i, float(scores[i])) for i in range(len(scores))
        ]
        scored_indices.sort(key=lambda x: x[1], reverse=True)

        return scored_indices[:top_n]
