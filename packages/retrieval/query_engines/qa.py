"""QA query engine with retrieval, synthesis, and citation formatting."""

import time
from dataclasses import dataclass
from typing import Any

from llama_index.llms.ollama import Ollama

from packages.retrieval.context.prompts import format_source_list, get_qa_prompt_template
from packages.retrieval.retrievers.hybrid import HybridRetriever


@dataclass
class QAConfig:
    """Configuration for QA query engine."""

    qdrant_url: str
    qdrant_collection: str
    neo4j_uri: str
    neo4j_username: str
    neo4j_password: str
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen3:4b"
    llm_temperature: float = 0.0
    tei_embedding_url: str | None = None


class QAQueryEngine:
    """Query engine with hybrid retrieval and citation formatting."""

    def __init__(self, config: QAConfig) -> None:
        """Initialize QA query engine.

        Args:
            config: QA configuration object

        """
        self.config = config

        # Initialize hybrid retriever
        self.retriever = HybridRetriever(
            qdrant_url=config.qdrant_url,
            qdrant_collection=config.qdrant_collection,
            neo4j_uri=config.neo4j_uri,
            neo4j_username=config.neo4j_username,
            neo4j_password=config.neo4j_password,
            tei_embedding_url=config.tei_embedding_url,
        )

        # Initialize LLM
        self.llm = Ollama(
            base_url=config.ollama_base_url,
            model=config.llm_model,
            temperature=config.llm_temperature,
            context_window=4096,  # Limit KV cache to reasonable size (avoid 36GB allocation)
        )

        self.prompt_template = get_qa_prompt_template()

    def query(
        self,
        question: str,
        top_k: int = 20,
        rerank_top_n: int = 5,
        source_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Execute query with retrieval and synthesis.

        Args:
            question: User question
            top_k: Candidates from vector search
            rerank_top_n: Chunks after reranking
            source_types: Filter by source types

        Returns:
            Query response with answer, sources, and latency breakdown

        """
        start_time = time.time()
        latency_breakdown = {}

        # Step 1: Retrieval
        retrieval_start = time.time()
        retrieval_results = self.retriever.retrieve(
            query=question,
            top_k=top_k,
            rerank_top_n=rerank_top_n,
            source_types=source_types,
        )
        latency_breakdown["retrieval_ms"] = int((time.time() - retrieval_start) * 1000)

        # Extract context from results
        context = self._build_context(retrieval_results)

        # Extract sources
        sources = self._extract_sources(retrieval_results)

        # Step 2: Synthesis
        synthesis_start = time.time()
        prompt = self.prompt_template.format(
            context_str=context,
            query_str=question,
        )

        response = self.llm.complete(prompt)
        answer = response.text.strip()
        latency_breakdown["synthesis_ms"] = int((time.time() - synthesis_start) * 1000)

        # Step 3: Format citations
        formatted_sources = self.format_sources(sources)
        final_answer = f"{answer}\n\n{formatted_sources}"

        total_latency_ms = int((time.time() - start_time) * 1000)

        return {
            "answer": final_answer,
            "sources": sources,
            "latency_ms": total_latency_ms,
            "latency_breakdown": latency_breakdown,
            "vector_count": len(retrieval_results[0]["vector_results"]) if retrieval_results else 0,
            "graph_count": len(retrieval_results[0]["graph_results"]) if retrieval_results else 0,
        }

    def _build_context(self, retrieval_results: list[dict[str, Any]]) -> str:
        """Build context string from retrieval results."""
        if not retrieval_results:
            return ""

        result = retrieval_results[0]
        vector_results = result.get("vector_results", [])

        context_parts = []
        for idx, chunk in enumerate(vector_results, start=1):
            content = chunk.get("content", "")
            source_url = chunk.get("source_url", "unknown")
            section = chunk.get("section", "")

            context_parts.append(
                f"[{idx}] ({source_url} - {section}):\n{content}\n",
            )

        return "\n".join(context_parts)

    def _extract_sources(
        self,
        retrieval_results: list[dict[str, Any]],
    ) -> list[tuple[str, str]]:
        """Extract (title, url) tuples from results."""
        if not retrieval_results:
            return []

        result = retrieval_results[0]
        vector_results = result.get("vector_results", [])

        sources = []
        seen_urls = set()

        for chunk in vector_results:
            url = chunk.get("source_url", "")
            section = chunk.get("section", "Document")

            if url and url not in seen_urls:
                sources.append((section, url))
                seen_urls.add(url)

        return sources

    def format_sources(self, sources: list[tuple[str, str]]) -> str:
        """Format source list with citations."""
        return format_source_list(sources)

    def close(self) -> None:
        """Close retriever connections."""
        self.retriever.close()
