"""Interpreter-wide patches and warning fixes for third-party deps.

Python automatically imports ``sitecustomize`` (if present on ``sys.path``)
after the standard library `site` initialization. We use this hook to apply
monkey patches that silence deprecation warnings emitted by dependencies
without requiring upstream fixes or runtime filters.
"""

from __future__ import annotations

from typing import Any


def _patch_llama_index_spider_reader() -> None:
    """Convert legacy Pydantic Config usage in LlamaIndex SpiderWebReader.

    LlamaIndex's ``SpiderWebReader`` still defines the Pydantic v1-style
    ``Config`` inner class which triggers a ``PydanticDeprecatedSince20``
    warning under Pydantic v2. We replace it with an explicit ``ConfigDict``
    and drop the legacy attribute so the warning disappears without altering
    library behaviour.
    """
    try:
        from llama_index.readers.web.spider_web.base import SpiderWebReader
    except Exception:
        return

    try:
        from pydantic import ConfigDict
    except Exception:
        return

    # Build a model config equivalent to the old Config settings.
    config_dict: dict[str, Any] = {"extra": "allow", "use_enum_values": True}
    SpiderWebReader.model_config = ConfigDict(**config_dict)

    # Remove the deprecated Config inner class if present.
    if hasattr(SpiderWebReader, "Config"):
        try:
            delattr(SpiderWebReader, "Config")
        except AttributeError:
            pass


_patch_llama_index_spider_reader()

