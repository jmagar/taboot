"""Async command wrapper for Typer CLI.

Provides decorator to wrap async commands for synchronous Typer interface.
This eliminates the need for repetitive asyncio.run() boilerplate in command definitions.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

T = TypeVar("T")


def async_command(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to wrap async commands for Typer CLI.

    Typer requires synchronous command functions, but many Taboot operations
    are async (Neo4j queries, Qdrant searches, Redis operations, etc.).
    This decorator bridges the gap by running async functions in an event loop.

    Usage:
        @app.command()
        @async_command
        async def my_command(arg: str) -> None:
            await async_operation(arg)

    Args:
        func: Async function to wrap.

    Returns:
        Synchronous wrapper function that executes the async function.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return asyncio.run(func(*args, **kwargs))

    return wrapper


__all__ = ["async_command"]
