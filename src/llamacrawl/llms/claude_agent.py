"""Claude Agent SDK integration for LlamaIndex.

This module provides a custom LLM implementation that wraps the Claude Agent SDK,
allowing you to use your Claude.ai subscription instead of requiring a separate API key.

The ClaudeAgentLLM class implements LlamaIndex's CustomLLM interface and uses the
claude-agent-sdk to communicate with Claude Code's backend.
"""

import asyncio
from typing import Any

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, TextBlock
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.llms import CompletionResponse, CompletionResponseGen, CustomLLM
from llama_index.core.llms.callbacks import llm_completion_callback

from llamacrawl.utils.logging import get_logger

logger = get_logger(__name__)


class ClaudeAgentLLM(CustomLLM):
    """Custom LLM implementation using Claude Agent SDK.

    This class wraps the Claude Agent SDK to provide LLM functionality within
    LlamaIndex pipelines without requiring a separate Anthropic API key. Instead,
    it uses your Claude.ai subscription credentials.

    The implementation handles:
    - Synchronous and streaming text completion
    - Chat message formatting
    - Token counting and metadata
    - Error handling and logging

    Note:
        The Claude Agent SDK does not expose inference parameters like temperature
        or max_tokens. These attributes are stored for LlamaIndex compatibility
        but do not affect generation. The SDK uses Claude Code's default settings.

    Attributes:
        model: Claude model to use (e.g., "claude-sonnet-4-0")
        temperature: Sampling temperature (stored for compatibility, not used)
        max_tokens: Maximum tokens to generate (stored for compatibility, not used)
        context_window: Maximum context window size
    """

    model: str = "claude-sonnet-4-0"
    temperature: float = 0.1
    max_tokens: int = 4096
    context_window: int = 200000  # Claude Sonnet 4.0 has 200K context

    @property
    def is_chat_model(self) -> bool:
        """Indicate this is a chat model for LlamaIndex compatibility."""
        return True

    @property
    def metadata(self) -> dict[str, Any]:
        """Get LLM metadata.

        Returns:
            Dictionary with model metadata including context window and output size
        """
        return {
            "context_window": self.context_window,
            "num_output": self.max_tokens,
            "model_name": self.model,
        }

    @llm_completion_callback()
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        """Generate a text completion for the given prompt.

        Uses Claude Agent SDK's query() function to generate a synchronous completion.
        This method blocks until the full response is received.

        Args:
            prompt: Input text prompt
            **kwargs: Additional arguments (ignored for compatibility)

        Returns:
            CompletionResponse with generated text

        Raises:
            RuntimeError: If Claude Agent SDK query fails
        """
        logger.debug(
            "Starting Claude Agent SDK completion",
            extra={
                "prompt_length": len(prompt),
                "model": self.model,
                "temperature": self.temperature,
            },
        )

        try:
            # Run async query in sync context
            response_text = asyncio.run(self._async_complete(prompt))

            logger.info(
                "Claude Agent SDK completion successful",
                extra={"response_length": len(response_text)},
            )

            return CompletionResponse(text=response_text)

        except Exception as e:
            logger.error(
                f"Claude Agent SDK completion failed: {e}",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
            raise RuntimeError(f"Claude Agent SDK completion failed: {e}") from e

    async def _async_complete(self, prompt: str) -> str:
        """Internal async completion implementation.

        Args:
            prompt: Input text prompt

        Returns:
            Generated text response

        Note:
            Claude Agent SDK doesn't expose temperature or max_tokens parameters.
            These are stored as class attributes for LlamaIndex compatibility only.
        """
        options = ClaudeAgentOptions(
            model=self.model,
        )

        # Collect full response from streaming iterator
        response_parts: list[str] = []

        async with ClaudeSDKClient(options=options) as client:
            # Send query
            await client.query(prompt)

            # Receive response (streaming) - SDK returns typed Message objects
            async for message in client.receive_response():
                # Extract text from AssistantMessage containing TextBlock objects
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            response_parts.append(block.text)

        return "".join(response_parts)

    @llm_completion_callback()
    def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
        """Generate a streaming text completion for the given prompt.

        Uses Claude Agent SDK's streaming capabilities to yield tokens as they arrive.

        Args:
            prompt: Input text prompt
            **kwargs: Additional arguments (ignored for compatibility)

        Yields:
            CompletionResponse with incremental text and deltas

        Raises:
            RuntimeError: If Claude Agent SDK streaming fails
        """
        logger.debug(
            "Starting Claude Agent SDK streaming completion",
            extra={
                "prompt_length": len(prompt),
                "model": self.model,
                "temperature": self.temperature,
            },
        )

        try:
            # Run async streaming in sync context
            for response in asyncio.run(self._async_stream_complete(prompt)):
                yield response

        except Exception as e:
            logger.error(
                f"Claude Agent SDK streaming failed: {e}",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
            raise RuntimeError(f"Claude Agent SDK streaming failed: {e}") from e

    async def _async_stream_complete(self, prompt: str) -> list[CompletionResponse]:
        """Internal async streaming completion implementation.

        Args:
            prompt: Input text prompt

        Returns:
            List of CompletionResponse objects with incremental updates

        Note:
            Claude Agent SDK doesn't expose temperature or max_tokens parameters.
            These are stored as class attributes for LlamaIndex compatibility only.
        """
        options = ClaudeAgentOptions(
            model=self.model,
        )

        responses: list[CompletionResponse] = []
        accumulated_text = ""

        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)

            async for message in client.receive_response():
                # Extract text from AssistantMessage containing TextBlock objects
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            delta = block.text
                            accumulated_text += delta
                            responses.append(
                                CompletionResponse(text=accumulated_text, delta=delta)
                            )

        return responses

    @llm_completion_callback()
    def chat(self, messages: list[ChatMessage], **kwargs: Any) -> CompletionResponse:
        """Generate a chat completion from a conversation history.

        Formats chat messages into a single prompt and calls complete().

        Args:
            messages: List of ChatMessage objects with role and content
            **kwargs: Additional arguments (ignored for compatibility)

        Returns:
            CompletionResponse with generated text
        """
        # Format chat messages into a single prompt
        prompt = self._format_chat_messages(messages)
        return self.complete(prompt, **kwargs)

    def _format_chat_messages(self, messages: list[ChatMessage]) -> str:
        """Format chat messages into a prompt string.

        Args:
            messages: List of ChatMessage objects

        Returns:
            Formatted prompt string
        """
        formatted_parts: list[str] = []

        for message in messages:
            role = message.role
            content = message.content or ""

            if role == MessageRole.SYSTEM:
                formatted_parts.append(f"System: {content}")
            elif role == MessageRole.USER:
                formatted_parts.append(f"User: {content}")
            elif role == MessageRole.ASSISTANT:
                formatted_parts.append(f"Assistant: {content}")

        return "\n\n".join(formatted_parts)


# Export public API
__all__ = ["ClaudeAgentLLM"]
