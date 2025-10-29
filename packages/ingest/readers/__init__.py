"""Ingestion readers for various sources."""

from packages.ingest.readers.docker_compose import (
    DockerComposeError,
    DockerComposeReader,
    InvalidPortError,
    InvalidYAMLError,
)
from packages.ingest.readers.swag import ParsedConfig, SwagReader, SwagReaderError
from packages.ingest.readers.tailscale import (
    InvalidIPError,
    TailscaleAPIError,
    TailscaleError,
    TailscaleReader,
)
from packages.ingest.readers.web import WebReader, WebReaderError

__all__ = [
    "DockerComposeError",
    "DockerComposeReader",
    "InvalidIPError",
    "InvalidPortError",
    "InvalidYAMLError",
    "ParsedConfig",
    "SwagReader",
    "SwagReaderError",
    "TailscaleAPIError",
    "TailscaleError",
    "TailscaleReader",
    "WebReader",
    "WebReaderError",
]
