"""Compatibility module exposing the CLI Typer app under ``apps.cli``.

The project historically referenced ``apps.cli.main`` in tests and entry points.
To keep those imports working after the CLI package moved to ``taboot_cli``,
this module re-exports the Typer application instance.
"""

from __future__ import annotations

from apps.cli.taboot_cli.main import app

__all__ = ["app"]
