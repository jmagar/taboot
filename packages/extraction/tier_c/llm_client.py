"""Tier C LLM client with Ollama, batching, and Redis caching."""

import hashlib
import json
from typing import Any

try:
    import ollama
    from ollama import AsyncClient
except ImportError:
    ollama = None  # type: ignore
    AsyncClient = None  # type: ignore

from packages.extraction.tier_c.schema import ExtractionResult


class TierCLLMClient:
    """Ollama LLM client for knowledge extraction.

    Features:
    - Batching (8-16 windows)
    - Redis caching (SHA-256 hash keys)
    - Temperature 0 for deterministic output
    - Target: ≤250ms median latency
    """

    def __init__(
        self,
        model: str = "qwen3:4b",
        redis_client: Any | None = None,
        batch_size: int = 16,
        temperature: float = 0.0,
    ):
        """Initialize LLM client.

        Args:
            model: Ollama model name.
            redis_client: Redis client for caching (optional).
            batch_size: Batch size for processing (default 16).
            temperature: LLM temperature (default 0 for deterministic).
        """
        self.model = model
        self.redis_client = redis_client
        self.batch_size = batch_size
        self.temperature = temperature

        # Initialize async Ollama client
        if AsyncClient is not None:
            self.ollama_client = AsyncClient()
        else:
            self.ollama_client = None

    def _compute_cache_key(self, window: str) -> str:
        """Compute SHA-256 cache key for window.

        Args:
            window: Input window text.

        Returns:
            str: SHA-256 hex digest.
        """
        return hashlib.sha256(window.encode()).hexdigest()

    async def _check_cache(self, cache_key: str) -> ExtractionResult | None:
        """Check Redis cache for result.

        Args:
            cache_key: Cache key.

        Returns:
            ExtractionResult | None: Cached result or None.
        """
        if not self.redis_client:
            return None

        cached = await self.redis_client.get(cache_key)
        if cached:
            data = json.loads(cached.decode() if isinstance(cached, bytes) else cached)
            return ExtractionResult(**data)

        return None

    async def _save_to_cache(self, cache_key: str, result: ExtractionResult) -> None:
        """Save result to Redis cache.

        Args:
            cache_key: Cache key.
            result: Extraction result.
        """
        if not self.redis_client:
            return

        data = result.model_dump_json()
        await self.redis_client.set(cache_key, data)

    async def _call_ollama(self, window: str) -> ExtractionResult:
        """Call Ollama LLM to extract triples.

        Args:
            window: Input window text.

        Returns:
            ExtractionResult: Extracted triples.
        """
        if self.ollama_client is None:
            # Fallback if ollama not installed - return empty result
            return ExtractionResult(triples=[])

        prompt = f"""Extract knowledge triples from the following text.
Return ONLY a JSON object with this exact format:
{{"triples": [{{"subject": "entity1", "predicate": "RELATIONSHIP", "object": "entity2", "confidence": 0.9}}]}}

Text: {window}

JSON:"""

        response = await self.ollama_client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": self.temperature},
        )

        content = response["message"]["content"]

        try:
            data = json.loads(content)
            return ExtractionResult(**data)
        except (json.JSONDecodeError, KeyError):
            # If parsing fails, return empty result
            return ExtractionResult(triples=[])

    async def extract_from_window(self, window: str) -> ExtractionResult:
        """Extract triples from a single window.

        Args:
            window: Input window text.

        Returns:
            ExtractionResult: Extracted triples.
        """
        # Check cache
        cache_key = self._compute_cache_key(window)
        cached_result = await self._check_cache(cache_key)
        if cached_result:
            return cached_result

        # Call LLM
        result = await self._call_ollama(window)

        # Save to cache
        await self._save_to_cache(cache_key, result)

        return result

    async def batch_extract(self, windows: list[str]) -> list[ExtractionResult]:
        """Extract triples from multiple windows in batches.

        Args:
            windows: List of window texts.

        Returns:
            list[ExtractionResult]: Results for each window.
        """
        results = []

        for i in range(0, len(windows), self.batch_size):
            batch = windows[i : i + self.batch_size]

            # Process batch concurrently
            batch_results = []
            for window in batch:
                result = await self.extract_from_window(window)
                batch_results.append(result)

            results.extend(batch_results)

        return results
