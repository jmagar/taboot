"""Tests for custom retrieval prompts with inline citations."""

import pytest

from packages.retrieval.context.prompts import get_qa_prompt_template, get_synthesis_prompt


@pytest.mark.unit
def test_qa_prompt_template_has_citation_instructions():
    """Test that QA prompt template includes citation formatting instructions."""
    prompt_template = get_qa_prompt_template()

    assert prompt_template is not None
    assert "[1]" in prompt_template or "citation" in prompt_template.lower()
    assert "source" in prompt_template.lower()


@pytest.mark.unit
def test_synthesis_prompt_requires_inline_citations():
    """Test that synthesis prompt enforces inline citation format."""
    prompt = get_synthesis_prompt()

    assert "[1]" in prompt or "[2]" in prompt
    assert "Sources:" in prompt or "source list" in prompt.lower()


@pytest.mark.unit
def test_synthesis_prompt_specifies_format():
    """Test that synthesis prompt specifies citation format clearly."""
    prompt = get_synthesis_prompt()

    # Should specify numeric inline citations
    assert "numeric" in prompt.lower() or "[1]" in prompt
    # Should specify source list format
    assert "source" in prompt.lower()
