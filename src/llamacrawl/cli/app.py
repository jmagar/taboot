"""Typer application wiring for the LlamaCrawl CLI."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from llamacrawl.config import load_config
from llamacrawl.utils.logging import get_logger, setup_logging

from .commands import register_commands
from .context import CLIState
from .firecrawl import register_firecrawl_commands

app = typer.Typer(
    name="llamacrawl",
    help="Multi-source RAG pipeline built on LlamaIndex",
    add_completion=False,
    no_args_is_help=True,
)

console = Console()
logger = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_ENV = _PROJECT_ROOT / ".env"
_DEFAULT_CONFIG = _PROJECT_ROOT / "config.yaml"


def _initialize_state(
    *,
    config_path: Path | None,
    log_level_override: str | None,
) -> CLIState:
    """Load configuration and prepare CLI state."""
    config_source = "default paths"

    if config_path:
        env_file = config_path.parent / ".env"
        config = load_config(env_file=env_file, config_file=config_path)
        config_source = str(config_path)
    else:
        try:
            config = load_config(env_file=_DEFAULT_ENV, config_file=_DEFAULT_CONFIG)
            config_source = str(_DEFAULT_CONFIG)
        except FileNotFoundError:
            # Fall back to cwd to preserve legacy behavior
            config = load_config()
            config_source = "default paths"

    effective_log_level = (
        log_level_override.upper() if log_level_override else config.logging.level.upper()
    )
    setup_logging(
        log_level=effective_log_level,
        log_format=config.logging.format,
        log_sensitive_data=config.logging.log_sensitive_data,
    )
    logger.info(
        "Configuration loaded",
        extra={
            "config_source": config_source,
            "log_level": effective_log_level,
            "log_format": config.logging.format,
        },
    )
    return CLIState(
        config=config,
        console=console,
        config_source=config_source,
        log_level=effective_log_level,
    )


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    config_path: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Path to config.yaml file",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    log_level: Annotated[
        str | None,
        typer.Option(
            "--log-level",
            "-l",
            help="Override LOG_LEVEL environment variable (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        ),
    ] = None,
) -> None:
    """Global options and CLI initialization."""
    if ctx.invoked_subcommand is None or ctx.invoked_subcommand == "version":
        return

    if ctx.obj is None:
        try:
            ctx.obj = _initialize_state(
                config_path=config_path,
                log_level_override=log_level,
            )
        except FileNotFoundError as error:
            console.print(f"[bold red]Configuration Error:[/bold red] {error}")
            raise typer.Exit(code=2) from error
        except ValueError as error:
            console.print(f"[bold red]Configuration Validation Error:[/bold red] {error}")
            raise typer.Exit(code=2) from error
        except Exception as error:
            if not logging.getLogger().handlers:
                setup_logging(log_format="text")
            console.print(f"[bold red]Unexpected Error:[/bold red] {error}")
            logger.exception("Failed to load configuration")
            raise typer.Exit(code=1) from error


def run() -> None:
    """Entrypoint wrapper with defensive error handling."""
    try:
        app()
    except typer.Exit:
        raise
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Interrupted by user[/bold yellow]")
        logger.info("Application interrupted by user (Ctrl+C)")
        raise SystemExit(130) from None
    except Exception as error:  # pragma: no cover - defensive
        console.print(f"\n[bold red]Unexpected Error:[/bold red] {error}")
        logger.exception("Unexpected error in CLI")
        raise SystemExit(1) from error


def _register() -> None:
    register_commands(app)
    register_firecrawl_commands(app)


_register()
