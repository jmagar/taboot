"""Custom prompts for retrieval with inline citation formatting."""



def get_qa_prompt_template() -> str:
    """
    Get QA prompt template for answer synthesis with inline citations.

    Returns:
        Prompt template string with citation format instructions
    """
    template = """
Context information is below.
---------------------
{context_str}
---------------------

Using the context information above, answer the following question.

IMPORTANT: Use inline numeric citations [1], [2], etc. for each fact you state.
After your answer, provide a "Sources:" section listing all cited sources.

Question: {query_str}

Answer with inline citations:
"""
    return template.strip()


def get_synthesis_prompt() -> str:
    """
    Get synthesis prompt for combining retrieved chunks into coherent answer.

    Returns:
        Prompt with citation requirements
    """
    prompt = """
You are a technical documentation assistant. Your task is to synthesize information
from multiple sources to answer the user's question accurately.

CITATION REQUIREMENTS:
1. Use inline numeric citations [1], [2], [3] after each statement
2. Only cite information actually present in the provided context
3. Do not make unsupported claims or add information not in sources
4. After your answer, add a "Sources:" section with numbered list:
   - Format: [N] Title (URL)
   - Include all sources you cited

EXAMPLE FORMAT:
The API service exposes port 8080 [1] and uses JWT authentication [2].

Sources:
[1] API Service Documentation (https://docs.example.com/api)
[2] Security Configuration Guide (https://docs.example.com/security)
"""
    return prompt.strip()


def format_source_list(sources: list[tuple[str, str]]) -> str:
    """
    Format source list for citation section.

    Args:
        sources: List of (title, url) tuples

    Returns:
        Formatted source list string
    """
    if not sources:
        return ""

    lines = ["", "Sources:"]
    for idx, (title, url) in enumerate(sources, start=1):
        lines.append(f"[{idx}] {title} ({url})")

    return "\n".join(lines)
