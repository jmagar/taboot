"""Registration helpers for CLI commands."""

from __future__ import annotations

import typer

from . import ingest as ingest_cmd
from . import init as init_cmd
from . import query as query_cmd
from . import status as status_cmd
from . import version as version_cmd


def register_commands(app: typer.Typer) -> None:
    """Attach core command functions to the Typer application."""
    app.command()(version_cmd.version)
    app.command()(ingest_cmd.ingest)
    app.command()(query_cmd.query)
    app.command()(status_cmd.status)
    app.command()(init_cmd.init)
