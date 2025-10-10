import asyncio
import time
from collections.abc import AsyncGenerator

import pytest

pytest.importorskip("claude_agent_sdk")

from llama_index.core.llms import CompletionResponse

from llamacrawl.llms import ClaudeAgentLLM


def test_stream_complete_yields_incrementally(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure stream_complete yields deltas as they arrive without full buffering."""

    delay_seconds = 0.1

    async def fake_async_stream_complete(
        self: ClaudeAgentLLM, prompt: str
    ) -> AsyncGenerator[CompletionResponse, None]:
        yield CompletionResponse(text="h", delta="h")
        await asyncio.sleep(delay_seconds)
        yield CompletionResponse(text="hi", delta="i")

    monkeypatch.setattr(
        ClaudeAgentLLM,
        "_async_stream_complete",
        fake_async_stream_complete,
    )

    llm = ClaudeAgentLLM()
    generator = llm.stream_complete("hello")

    start = time.perf_counter()
    first = next(generator)
    first_elapsed = time.perf_counter() - start

    assert first.delta == "h"
    assert first_elapsed < delay_seconds

    second = next(generator)
    assert second.delta == "i"

    with pytest.raises(StopIteration):
        next(generator)
