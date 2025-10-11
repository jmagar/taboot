"""Shared CLI context utilities."""

from __future__ import annotations

from dataclasses import dataclass

from rich.console import Console

from llamacrawl.config import Config


@dataclass(slots=True)
class CLIState:
    """State object stored on the Typer context."""

    config: Config
    console: Console
    config_source: str
    log_level: str
