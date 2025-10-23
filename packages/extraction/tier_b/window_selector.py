"""Tier B window selector for Tier C LLM processing."""

import re
from typing import Any


class WindowSelector:
    """Select micro-windows (≤512 tokens) for Tier C LLM extraction.

    Uses sentence boundaries and token counting to create
    appropriate-sized windows for LLM processing.
    """

    def __init__(self, max_tokens: int = 512):
        """Initialize window selector.

        Args:
            max_tokens: Maximum tokens per window (default 512).
        """
        self.max_tokens = max_tokens

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation: ~1.3 tokens per word).

        Args:
            text: Input text.

        Returns:
            int: Estimated token count.
        """
        words = len(text.split())
        return int(words * 1.3)

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences.

        Args:
            text: Input text.

        Returns:
            list[str]: Sentences.
        """
        # Simple sentence splitting on period, question mark, exclamation
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def select_windows(self, text: str) -> list[dict[str, Any]]:
        """Select micro-windows from text for Tier C processing.

        Args:
            text: Input text to process.

        Returns:
            list[dict[str, Any]]: Windows with content, token_count, start, end.
        """
        if not text:
            return []

        sentences = self._split_into_sentences(text)
        windows = []
        current_window = []
        current_tokens = 0
        current_start = 0

        for sentence in sentences:
            sentence_tokens = self._estimate_tokens(sentence)

            # If single sentence exceeds limit, split by words
            if sentence_tokens > self.max_tokens:
                words = sentence.split()
                word_window = []
                word_tokens = 0

                for word in words:
                    word_token_count = int(1.3)  # Approximate 1 word = 1.3 tokens
                    if word_tokens + word_token_count > self.max_tokens and word_window:
                        window_text = " ".join(word_window)
                        windows.append({
                            "content": window_text,
                            "token_count": word_tokens,
                            "start": current_start,
                            "end": current_start + len(window_text),
                        })
                        current_start += len(window_text) + 1
                        word_window = []
                        word_tokens = 0

                    word_window.append(word)
                    word_tokens += word_token_count

                # Add final word window
                if word_window:
                    window_text = " ".join(word_window)
                    windows.append({
                        "content": window_text,
                        "token_count": word_tokens,
                        "start": current_start,
                        "end": current_start + len(window_text),
                    })
                    current_start += len(window_text) + 1
                continue

            # If adding this sentence exceeds limit, save current window
            if current_tokens + sentence_tokens > self.max_tokens and current_window:
                window_text = " ".join(current_window)
                windows.append({
                    "content": window_text,
                    "token_count": current_tokens,
                    "start": current_start,
                    "end": current_start + len(window_text),
                })
                current_window = []
                current_tokens = 0
                current_start += len(window_text) + 1

            # Add sentence to current window
            current_window.append(sentence)
            current_tokens += sentence_tokens

        # Add final window
        if current_window:
            window_text = " ".join(current_window)
            windows.append({
                "content": window_text,
                "token_count": current_tokens,
                "start": current_start,
                "end": current_start + len(window_text),
            })

        return windows
