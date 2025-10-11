"""Answer synthesis module for LlamaCrawl RAG pipeline.

This module implements the AnswerSynthesizer class that takes retrieved documents
and synthesizes a coherent answer using Ollama LLM with inline citations and
source attribution.

The synthesizer:
1. Formats context from retrieved documents with source numbers
2. Builds a prompt with system instructions and context
3. Calls Ollama API for answer generation
4. Adds inline citations [1][2] referencing source documents
5. Creates SourceAttribution objects for each document
6. Returns QueryResult with answer, sources, and metadata
"""

import time
from datetime import datetime
from typing import Any

from llamacrawl.config import Config
from llamacrawl.llms import ClaudeAgentLLM
from llamacrawl.models.document import QueryResult, SourceAttribution
from llamacrawl.utils.logging import get_logger

logger = get_logger(__name__)


class AnswerSynthesizer:
    """Synthesize answers from retrieved documents using Claude Agent SDK.

    This class takes retrieved documents with scores and generates a coherent
    answer with inline citations and source attribution. It uses Claude Agent SDK
    via a custom LlamaIndex LLM wrapper, allowing use of Claude.ai subscription.

    The synthesizer handles:
    - Context formatting with source numbering
    - Prompt engineering for citation-based responses
    - LLM API calls with retry logic
    - Citation parsing and validation
    - Source attribution object creation
    - Response formatting into QueryResult model

    Attributes:
        config: Configuration object with Claude settings
        llm: ClaudeAgentLLM instance
        model_name: Name of Claude model to use (e.g., "claude-sonnet-4-0")
        max_input_tokens: Maximum number of tokens for context
    """

    def __init__(self, config: Config):
        """Initialize AnswerSynthesizer with Claude Agent SDK.

        Args:
            config: Configuration object with Claude model settings

        Raises:
            ValueError: If Claude configuration is invalid
        """
        self.config = config
        self.model_name = config.query.synthesis_model
        self.max_input_tokens = config.query.max_input_tokens

        logger.info(
            "Initializing AnswerSynthesizer",
            extra={
                "model": self.model_name,
                "max_input_tokens": self.max_input_tokens,
            },
        )

        # Initialize Claude Agent SDK LLM
        try:
            self.llm = ClaudeAgentLLM(
                model=self.model_name,
                max_tokens=self.max_input_tokens,
            )

            logger.info("AnswerSynthesizer initialized successfully")

        except Exception as e:
            logger.error(
                f"Failed to initialize Claude Agent LLM: {e}",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
            raise ValueError(f"Failed to initialize Claude Agent LLM: {e}") from e

    def synthesize(
        self,
        query_text: str,
        retrieved_docs: list[dict[str, Any]],
        include_snippets: bool | None = None,
    ) -> QueryResult:
        """Synthesize answer from query and retrieved documents.

        Pipeline steps:
        1. Format context from documents (include snippets if enabled)
        2. Build prompt with system instructions and context
        3. Call Ollama API for answer synthesis
        4. Parse response and validate citations
        5. Create SourceAttribution objects for each document
        6. Return QueryResult with answer, sources, and metadata

        Args:
            query_text: Original user query
            retrieved_docs: List of retrieved documents from query engine
                Each dict should have: doc_id, title, content, source_type,
                source_url, score, timestamp, metadata
            include_snippets: Whether to include snippets in sources (overrides config)

        Returns:
            QueryResult with synthesized answer, source attributions, and metadata

        Example:
            >>> synthesizer = AnswerSynthesizer(config)
            >>> result = synthesizer.synthesize(
            ...     "How does authentication work?",
            ...     retrieved_docs=[{...}]
            ... )
            >>> print(result.answer)
            "Authentication is handled via OAuth [1][2]..."
        """
        start_time = time.time()

        logger.info(
            "Starting answer synthesis",
            extra={
                "query": query_text,
                "num_docs": len(retrieved_docs),
            },
        )

        # Use config default if not overridden
        include_snippets = (
            include_snippets if include_snippets is not None else self.config.query.include_snippets
        )

        # Handle empty results
        if not retrieved_docs:
            logger.warning("No documents provided for synthesis")
            return QueryResult(
                answer="I couldn't find any relevant information to answer your question.",
                sources=[],
                query_time_ms=int((time.time() - start_time) * 1000),
                retrieved_docs=0,
                reranked_docs=0,
            )

        # Stage 1: Format context from documents
        stage_start = time.time()
        logger.debug("Stage 1: Formatting context from documents")

        context = self._format_context(retrieved_docs)
        truncated_context = self._truncate_context(context, self.max_input_tokens)

        context_time = (time.time() - stage_start) * 1000
        logger.debug(
            "Context formatted",
            extra={
                "num_sources": len(retrieved_docs),
                "context_length": len(truncated_context),
                "time_ms": context_time,
            },
        )

        # Stage 2: Build prompt
        stage_start = time.time()
        logger.debug("Stage 2: Building prompt")

        prompt = self._build_prompt(query_text, truncated_context)

        prompt_time = (time.time() - stage_start) * 1000
        logger.debug(
            "Prompt built",
            extra={
                "prompt_length": len(prompt),
                "time_ms": prompt_time,
            },
        )

        # Stage 3: Call Claude Agent SDK for synthesis
        stage_start = time.time()
        logger.debug("Stage 3: Calling Claude Agent LLM for synthesis")

        try:
            response = self.llm.complete(prompt)
            answer_text = response.text

            synthesis_time = (time.time() - stage_start) * 1000
            logger.info(
                "Synthesis completed",
                extra={
                    "answer_length": len(answer_text),
                    "time_ms": synthesis_time,
                },
            )

        except Exception as e:
            logger.error(
                f"Claude Agent synthesis failed: {e}",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
            # Return error message to user
            return QueryResult(
                answer=f"I encountered an error while generating the answer: {str(e)}",
                sources=[],
                query_time_ms=int((time.time() - start_time) * 1000),
                retrieved_docs=len(retrieved_docs),
                reranked_docs=len(retrieved_docs),
            )

        # Stage 4: Create source attributions
        stage_start = time.time()
        logger.debug("Stage 4: Creating source attributions")

        sources = self._create_source_attributions(
            retrieved_docs, include_snippets=include_snippets
        )

        attribution_time = (time.time() - stage_start) * 1000
        logger.debug(
            "Source attributions created",
            extra={
                "num_sources": len(sources),
                "time_ms": attribution_time,
            },
        )

        # Create QueryResult
        total_time = int((time.time() - start_time) * 1000)

        result = QueryResult(
            answer=answer_text,
            sources=sources,
            query_time_ms=total_time,
            retrieved_docs=len(retrieved_docs),
            reranked_docs=len(retrieved_docs),
        )

        logger.info(
            f"Answer synthesis completed in {total_time}ms",
            extra={
                "total_time_ms": total_time,
                "num_sources": len(sources),
                "answer_length": len(answer_text),
            },
        )

        return result

    def stream_synthesize(
        self,
        query_text: str,
        retrieved_docs: list[dict[str, Any]],
    ) -> tuple[Any, list[dict[str, Any]]]:
        """Stream answer synthesis token by token.

        Same as synthesize() but yields tokens as they arrive from Claude.
        Returns a generator that yields text deltas.

        Args:
            query_text: Original user query
            retrieved_docs: List of retrieved documents from query engine

        Yields:
            Text deltas from Claude (strings to print immediately)

        Returns:
            Tuple of (delta_generator, retrieved_docs) for CLI to use
        """
        logger.info(
            "Starting streaming answer synthesis",
            extra={
                "query": query_text,
                "num_docs": len(retrieved_docs),
            },
        )

        # Handle empty results
        if not retrieved_docs:
            logger.warning("No documents provided for synthesis")
            yield "I couldn't find any relevant information to answer your question."
            return

        # Stage 1: Format context from documents
        context = self._format_context(retrieved_docs)
        truncated_context = self._truncate_context(context, self.max_input_tokens)

        # Stage 2: Build prompt
        prompt = self._build_prompt(query_text, truncated_context)

        # Stage 3: Stream from Claude Agent SDK
        logger.debug("Stage 3: Streaming from Claude Agent LLM")

        try:
            # Use stream_complete to get deltas
            for chunk in self.llm.stream_complete(prompt):
                if chunk.delta:  # Only yield if there's new text
                    yield chunk.delta

            logger.info("Streaming synthesis completed")

        except Exception as e:
            logger.error(
                f"Claude Agent streaming synthesis failed: {e}",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
            yield f"\n\nI encountered an error while generating the answer: {str(e)}"

    def _format_context(self, retrieved_docs: list[dict[str, Any]]) -> str:
        """Format retrieved documents into context string with source numbers.

        Each document is formatted as:
        [N] Title: <title>
        Source: <source_type> - <source_url>
        Content: <content>

        Args:
            retrieved_docs: List of retrieved document dictionaries

        Returns:
            Formatted context string with numbered sources
        """
        context_parts: list[str] = []

        for idx, doc in enumerate(retrieved_docs, start=1):
            title = doc.get("title", "Untitled")
            source_type = doc.get("source_type", "unknown")
            source_url = doc.get("source_url", "")
            content = doc.get("content", "")

            # Format each source with number
            source_section = f"[{idx}] Title: {title}\n"
            source_section += f"Source: {source_type}"
            if source_url:
                source_section += f" - {source_url}"
            source_section += f"\nContent: {content}\n"

            context_parts.append(source_section)

        return "\n---\n\n".join(context_parts)

    def _truncate_context(self, context: str, max_tokens: int) -> str:
        """Truncate context to fit within token limit while preserving most relevant content.

        This is a simple character-based approximation (4 chars ≈ 1 token).
        For production, consider using tiktoken or similar tokenizer.

        Args:
            context: Full context string
            max_tokens: Maximum number of tokens allowed

        Returns:
            Truncated context string
        """
        # Rough approximation: 4 characters per token
        max_chars = max_tokens * 4

        if len(context) <= max_chars:
            return context

        logger.warning(
            f"Context truncated from {len(context)} to {max_chars} chars",
            extra={
                "original_length": len(context),
                "truncated_length": max_chars,
                "max_tokens": max_tokens,
            },
        )

        # Truncate and add ellipsis
        return context[:max_chars] + "\n\n[Context truncated due to length...]"

    def _build_prompt(self, query_text: str, context: str) -> str:
        """Build prompt for Claude with system instructions, context, and query.

        The prompt instructs the model to:
        - Answer based on provided context only
        - Cite sources using [1], [2], etc.
        - Be concise and accurate
        - Admit if information is not in the context

        Args:
            query_text: User's query
            context: Formatted context from retrieved documents

        Returns:
            Complete prompt string for LLM
        """
        system_prompt = """You are a helpful assistant that answers \
questions based on the provided context.

IMPORTANT INSTRUCTIONS:
1. Answer the question using ONLY the information from the context below
2. Cite your sources using inline citations like [1], [2], etc. that \
correspond to the numbered sources in the context
3. If multiple sources support a claim, cite all of them: [1][2]
4. Be concise and accurate
5. If the answer is not in the context, say "I don't have enough \
information to answer this question based on the provided sources."
6. Do not make up information or use knowledge outside the provided context

"""

        user_prompt = f"""Context:

{context}

---

Question: {query_text}

Answer (remember to cite sources using [1], [2], etc.):"""

        return system_prompt + user_prompt

    def _create_source_attributions(
        self, retrieved_docs: list[dict[str, Any]], include_snippets: bool = True
    ) -> list[SourceAttribution]:
        """Create SourceAttribution objects from retrieved documents.

        Args:
            retrieved_docs: List of retrieved document dictionaries
            include_snippets: Whether to include content snippets (default: True)

        Returns:
            List of SourceAttribution objects
        """
        sources: list[SourceAttribution] = []

        for doc in retrieved_docs:
            # Extract snippet if enabled
            snippet = ""
            if include_snippets:
                snippet = self._extract_snippet(
                    doc.get("content", ""), self.config.query.snippet_length
                )

            # Parse timestamp
            timestamp_str = doc.get("timestamp", "")
            try:
                if isinstance(timestamp_str, str):
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                else:
                    # Assume it's already a datetime object
                    timestamp = timestamp_str
            except (ValueError, AttributeError):
                # Fallback to current time if parsing fails
                timestamp = datetime.now()
                logger.warning(
                    f"Failed to parse timestamp: {timestamp_str}, using current time",
                    extra={"doc_id": doc.get("doc_id"), "timestamp_str": timestamp_str},
                )

            # Create SourceAttribution
            source = SourceAttribution(
                doc_id=doc.get("doc_id", ""),
                source_type=doc.get("source_type", "unknown"),
                title=doc.get("title", "Untitled"),
                url=doc.get("source_url", ""),
                score=float(doc.get("score", 0.0)),
                snippet=snippet,
                timestamp=timestamp,
            )
            sources.append(source)

        return sources

    def _extract_snippet(self, content: str, max_length: int = 200) -> str:
        """Extract a short snippet from content.

        Tries to extract a complete sentence if possible, otherwise truncates
        at word boundary.

        Args:
            content: Full content text
            max_length: Maximum snippet length in characters (default: 200)

        Returns:
            Content snippet (100-200 chars)
        """
        if not content:
            return ""

        # If content is short enough, return as-is
        if len(content) <= max_length:
            return content

        # Try to find sentence boundary within limit
        truncated = content[:max_length]

        # Look for sentence ending (., !, ?)
        for delimiter in [".", "!", "?"]:
            last_sentence_end = truncated.rfind(delimiter)
            if last_sentence_end > max_length // 2:  # Must be at least halfway through
                return content[: last_sentence_end + 1].strip()

        # No sentence boundary found, truncate at word boundary
        last_space = truncated.rfind(" ")
        if last_space > 0:
            return content[:last_space].strip() + "..."

        # Fallback: hard truncate
        return truncated.strip() + "..."


# Export public API
__all__ = ["AnswerSynthesizer"]
