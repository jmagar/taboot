"""Token counting utilities using tiktoken for accurate token estimation.

Provides tiktoken-based token counting with encoder caching for performance.
Used across ingestion and extraction pipelines for accurate token counting.
"""

import tiktoken

# Global encoder cache to avoid repeated initialization
_ENCODER_CACHE: dict[str, tiktoken.Encoding] = {}


def count_tokens(text: str, model: str = "cl100k_base") -> int:
    """Count tokens using tiktoken.

    Args:
        text: Input text to count.
        model: Encoding name (cl100k_base for GPT-3.5/4, p50k_base for older models).

    Returns:
        int: Exact token count.
    """
    if model not in _ENCODER_CACHE:
        _ENCODER_CACHE[model] = tiktoken.get_encoding(model)

    encoder = _ENCODER_CACHE[model]
    return len(encoder.encode(text))


# Export public API
__all__ = ["count_tokens"]
