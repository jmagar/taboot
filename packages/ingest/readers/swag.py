"""SWAG reverse proxy config parser.

Parses nginx configuration files from SWAG (Secure Web Application Gateway)
to extract Proxy nodes and ROUTES_TO relationships.

Per research.md: Use deterministic parsing for structured config sources.
Per data-model.md: Extract Proxy nodes with ROUTES_TO relationships containing
host, path, tls, and target service information.

Design:
- Parses nginx config syntax without external dependencies
- Extracts server blocks with listen, server_name, and location directives
- Identifies proxy_pass directives to determine routing targets
- Detects TLS/SSL from listen directive (e.g., "listen 443 ssl")
- Returns structured Proxy nodes and RouteInfo relationships

Performance: Deterministic regex-based parsing, target ≥50 pages/sec (Tier A).
"""

import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

from packages.schemas.models import Proxy, ProxyType

logger = logging.getLogger(__name__)


class SwagReaderError(Exception):
    """Base exception for SwagReader errors."""

    pass


class RouteInfo(TypedDict):
    """Route information extracted from nginx config.

    Represents a ROUTES_TO relationship between Proxy and Service.
    """

    host: str
    path: str
    target_service: str
    tls: bool


class ParsedConfig(TypedDict):
    """Result of parsing SWAG nginx config."""

    proxies: list[Proxy]
    routes: list[RouteInfo]


class SwagReader:
    """SWAG reverse proxy config parser.

    Parses nginx configuration files to extract proxy routing information.
    Implements deterministic parsing for structured SWAG configs.
    """

    def __init__(self, proxy_name: str = "swag") -> None:
        """Initialize SwagReader.

        Args:
            proxy_name: Name for the Proxy node (default: "swag").
        """
        self.proxy_name = proxy_name
        logger.info(f"Initialized SwagReader (proxy_name={proxy_name})")

    def parse_file(self, config_path: str) -> ParsedConfig:
        """Parse nginx config from file.

        Args:
            config_path: Path to nginx config file.

        Returns:
            ParsedConfig: Dictionary with 'proxies' and 'routes' keys.

        Raises:
            ValueError: If config_path is empty or invalid.
            SwagReaderError: If file cannot be read or parsed.
        """
        if not config_path:
            raise ValueError("config_path cannot be empty")

        if not isinstance(config_path, str | Path):
            raise ValueError(f"config_path must be str or Path, got {type(config_path)}")

        try:
            path = Path(config_path)
            if not path.exists():
                raise SwagReaderError(f"Config file not found: {config_path}")

            if not path.is_file():
                raise SwagReaderError(f"Path is not a file: {config_path}")

            content = path.read_text(encoding="utf-8")
            logger.info(f"Loaded config from {config_path} ({len(content)} bytes)")

            return self.parse_config(content)

        except SwagReaderError:
            raise
        except ValueError:
            raise
        except Exception as e:
            raise SwagReaderError(f"Failed to read config file {config_path}: {e}") from e

    def parse_config(self, config: str) -> ParsedConfig:
        """Parse nginx config string.

        Args:
            config: Nginx configuration content.

        Returns:
            ParsedConfig: Dictionary with 'proxies' and 'routes' keys.

        Raises:
            SwagReaderError: If config parsing fails.
        """
        if not config or not config.strip():
            # Empty config - return default proxy with no routes
            now = datetime.now(UTC)
            proxy = Proxy(
                name=self.proxy_name,
                proxy_type=ProxyType.SWAG,
                created_at=now,
                updated_at=now,
                metadata={"source": "swag_config"},
            )
            return ParsedConfig(proxies=[proxy], routes=[])

        try:
            # Parse server blocks
            server_blocks = self._extract_server_blocks(config)

            if not server_blocks:
                # No server blocks found - return default proxy with no routes
                now = datetime.now(UTC)
                proxy = Proxy(
                    name=self.proxy_name,
                    proxy_type=ProxyType.SWAG,
                    created_at=now,
                    updated_at=now,
                    metadata={"source": "swag_config"},
                )
                return ParsedConfig(proxies=[proxy], routes=[])

            # Extract routes from all server blocks
            routes: list[RouteInfo] = []
            for server_block in server_blocks:
                routes.extend(self._parse_server_block(server_block))

            # Create single Proxy node
            now = datetime.now(UTC)
            proxy = Proxy(
                name=self.proxy_name,
                proxy_type=ProxyType.SWAG,
                created_at=now,
                updated_at=now,
                metadata={"source": "swag_config", "server_blocks": len(server_blocks)},
            )

            logger.info(f"Parsed config: {len(server_blocks)} server blocks, {len(routes)} routes")

            return ParsedConfig(proxies=[proxy], routes=routes)

        except Exception as e:
            raise SwagReaderError(f"Failed to parse nginx config: {e}") from e

    def _extract_server_blocks(self, config: str) -> list[str]:
        """Extract server blocks from nginx config.

        Args:
            config: Nginx configuration content.

        Returns:
            list[str]: List of server block contents.

        Raises:
            SwagReaderError: If config syntax is invalid (mismatched braces).
        """
        server_blocks: list[str] = []
        depth = 0
        current_block = []
        in_server = False

        lines = config.split("\n")
        for line in lines:
            stripped = line.strip()

            # Check for server block start
            if "server" in stripped and "{" in stripped:
                in_server = True
                depth = 1
                current_block = [line]
                continue

            if in_server:
                current_block.append(line)

                # Track brace depth
                depth += stripped.count("{")
                depth -= stripped.count("}")

                # Validate depth doesn't go negative
                if depth < 0:
                    raise SwagReaderError("Invalid nginx syntax: mismatched closing braces")

                # Server block complete
                if depth == 0:
                    server_blocks.append("\n".join(current_block))
                    current_block = []
                    in_server = False

        # Check for unclosed blocks
        if in_server or depth != 0:
            raise SwagReaderError("Invalid nginx syntax: unclosed server block")

        return server_blocks

    def _parse_server_block(self, server_block: str) -> list[RouteInfo]:
        """Parse a single server block to extract routes.

        Args:
            server_block: Server block content.

        Returns:
            list[RouteInfo]: List of extracted routes.
        """
        routes: list[RouteInfo] = []

        # Extract server_name
        server_name = self._extract_server_name(server_block)
        if not server_name:
            logger.debug("No server_name found in server block, skipping")
            return routes

        # Detect TLS (check for 'ssl' in listen directive)
        tls = self._detect_tls(server_block)

        # Extract location blocks
        location_blocks = self._extract_location_blocks(server_block)

        for location_path, location_content in location_blocks:
            # Extract proxy_pass
            proxy_pass = self._extract_proxy_pass(location_content)
            if not proxy_pass:
                continue

            # Extract service name from proxy_pass
            target_service = self._extract_service_name(proxy_pass)

            # Create route
            route = RouteInfo(
                host=server_name,
                path=location_path,
                target_service=target_service,
                tls=tls,
            )
            routes.append(route)
            logger.debug(
                f"Extracted route: {server_name}{location_path} -> {target_service} (tls={tls})"
            )

        return routes

    def _extract_server_name(self, server_block: str) -> str | None:
        """Extract server_name from server block.

        Args:
            server_block: Server block content.

        Returns:
            str | None: Server name if found, None otherwise.

        Note:
            If multiple server names are listed, returns the first one.
            Example: "server_name api.example.com www.example.com;" returns "api.example.com"
        """
        match = re.search(r"server_name\s+([^;]+);", server_block)
        if match:
            # Take first server name if multiple are listed
            server_names = match.group(1).strip().split()
            if not server_names:
                return None

            # Validate hostname format (basic check)
            hostname = server_names[0]
            if not hostname or hostname == "_":
                # "_" is nginx's catch-all default server
                logger.debug("Skipping catch-all server_name '_'")
                return None

            return hostname
        return None

    def _detect_tls(self, server_block: str) -> bool:
        """Detect if TLS/SSL is enabled in server block.

        Args:
            server_block: Server block content.

        Returns:
            bool: True if SSL is enabled, False otherwise.
        """
        # Check for 'ssl' keyword in listen directives
        return bool(re.search(r"listen\s+[^;]*\bssl\b", server_block))

    def _extract_location_blocks(self, server_block: str) -> list[tuple[str, str]]:
        """Extract location blocks from server block.

        Args:
            server_block: Server block content.

        Returns:
            list[tuple[str, str]]: List of (path, content) tuples.
        """
        location_blocks: list[tuple[str, str]] = []
        depth = 0
        current_location: tuple[str, list[str]] | None = None

        lines = server_block.split("\n")
        for line in lines:
            stripped = line.strip()

            # Check for location block start
            if stripped.startswith("location"):
                # Extract path (everything between 'location' and '{')
                path_match = re.match(r"location\s+(~\s+)?([^{]+)\s*{", stripped)
                if path_match:
                    path = path_match.group(2).strip()
                    current_location = (path, [line])
                    depth = 1
                    continue

            if current_location is not None:
                current_location[1].append(line)

                # Track brace depth
                depth += stripped.count("{")
                depth -= stripped.count("}")

                # Location block complete
                if depth == 0:
                    path, content_lines = current_location
                    location_blocks.append((path, "\n".join(content_lines)))
                    current_location = None

        return location_blocks

    def _extract_proxy_pass(self, location_content: str) -> str | None:
        """Extract proxy_pass directive from location block.

        Args:
            location_content: Location block content.

        Returns:
            str | None: Proxy pass URL if found, None otherwise.
        """
        match = re.search(r"proxy_pass\s+([^;]+);", location_content)
        if match:
            return match.group(1).strip()
        return None

    def _extract_service_name(self, proxy_pass: str) -> str:
        """Extract service name from proxy_pass URL.

        Supports various proxy_pass formats:
        - http://service:8080 -> service
        - http://service:8080/ -> service
        - http://service -> service
        - https://service:443 -> service
        - http://10.0.0.5:8080 -> 10.0.0.5
        - http://localhost:3000 -> localhost

        Args:
            proxy_pass: Proxy pass URL (e.g., "http://api-service:8080").

        Returns:
            str: Service name extracted from URL.

        Raises:
            ValueError: If proxy_pass is empty or invalid.
        """
        if not proxy_pass:
            raise ValueError("proxy_pass cannot be empty")

        # Remove protocol (http:// or https://)
        url = re.sub(r"^https?://", "", proxy_pass)

        if not url:
            raise ValueError(f"Invalid proxy_pass URL: {proxy_pass}")

        # Extract hostname (everything before : or /)
        match = re.match(r"([^:/]+)", url)
        if match:
            hostname = match.group(1).strip()
            if hostname:
                return hostname

        # If no match, raise error (fail fast)
        raise ValueError(f"Could not extract service name from proxy_pass: {proxy_pass}")
