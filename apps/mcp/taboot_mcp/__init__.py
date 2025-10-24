"""Taboot MCP Server - Model Context Protocol integration."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("taboot-mcp")
except PackageNotFoundError:
    __version__ = "0.0.0"  # Fallback for development

__all__ = ["__version__"]
