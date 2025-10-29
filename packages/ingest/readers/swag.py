"""SWAG reverse proxy config parser.

Parses nginx configuration files from SWAG (Secure Web Application Gateway)
to extract comprehensive proxy configuration entities.

Per tasks.md Phase 4 (T195-T197): Updated to output new entity types:
- SwagConfigFile (root config entity)
- Proxy (proxy configuration)
- ProxyRoute (routing rules with upstream details)
- LocationBlock (location directive blocks)
- UpstreamConfig (upstream variable configuration)
- ProxyHeader (HTTP header directives)

Design:
- Parses nginx config syntax without external dependencies
- Extracts server blocks with listen, server_name, and location directives
- Identifies proxy_pass directives and upstream variables
- Detects TLS/SSL, auth directives, and header configuration
- Returns structured Pydantic entities for all configuration aspects

Performance: Deterministic regex-based parsing, target ≥50 pages/sec (Tier A).
"""

import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TypedDict

from packages.schemas.swag import (
    LocationBlock,
    Proxy,
    ProxyHeader,
    ProxyRoute,
    SwagConfigFile,
    UpstreamConfig,
)

logger = logging.getLogger(__name__)

# Extractor metadata
EXTRACTOR_VERSION = "2.0.0"
EXTRACTION_TIER: Literal["A", "B", "C"] = "A"
EXTRACTION_METHOD = "nginx_parser"
EXTRACTION_CONFIDENCE = 1.0


class SwagReaderError(Exception):
    """Base exception for SwagReader errors."""

    pass


class ParsedConfig(TypedDict):
    """Result of parsing SWAG nginx config with new entity types."""

    config_files: list[SwagConfigFile]
    proxies: list[Proxy]
    proxy_routes: list[ProxyRoute]
    location_blocks: list[LocationBlock]
    upstream_configs: list[UpstreamConfig]
    proxy_headers: list[ProxyHeader]


class SwagReader:
    """SWAG reverse proxy config parser.

    Parses nginx configuration files to extract comprehensive proxy
    configuration entities following Phase 4 requirements.
    """

    def __init__(self, proxy_name: str = "swag", config_path: str | None = None) -> None:
        """Initialize SwagReader.

        Args:
            proxy_name: Name for the Proxy node (default: "swag").
            config_path: Path to config file (used for entity metadata).
        """
        self.proxy_name = proxy_name
        self.config_path = config_path or "/config/nginx/site-confs/default"
        logger.info(f"Initialized SwagReader (proxy_name={proxy_name}, path={config_path})")

    def parse_file(self, config_path: str) -> ParsedConfig:
        """Parse nginx config from file.

        Args:
            config_path: Path to nginx config file.

        Returns:
            ParsedConfig: Dictionary with all entity type lists.

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

            # Get file mtime for source_timestamp
            file_stat = path.stat()
            source_timestamp = datetime.fromtimestamp(file_stat.st_mtime, UTC)

            content = path.read_text(encoding="utf-8")
            logger.info(f"Loaded config from {config_path} ({len(content)} bytes)")

            # Update config_path for entities
            self.config_path = str(path)

            return self.parse_config(content, source_timestamp=source_timestamp)

        except SwagReaderError:
            raise
        except ValueError:
            raise
        except Exception as e:
            raise SwagReaderError(f"Failed to read config file {config_path}: {e}") from e

    def parse_config(
        self, config: str, source_timestamp: datetime | None = None
    ) -> ParsedConfig:
        """Parse nginx config string.

        Args:
            config: Nginx configuration content.
            source_timestamp: Optional source file modification time.

        Returns:
            ParsedConfig: Dictionary with all entity type lists.

        Raises:
            SwagReaderError: If config parsing fails.
        """
        now = datetime.now(UTC)

        # Initialize result structure
        result: ParsedConfig = {
            "config_files": [],
            "proxies": [],
            "proxy_routes": [],
            "location_blocks": [],
            "upstream_configs": [],
            "proxy_headers": [],
        }

        # Create SwagConfigFile entity
        config_file = SwagConfigFile(
            file_path=self.config_path,
            version=None,  # Could extract from comments if present
            parsed_at=now,
            created_at=now,
            updated_at=now,
            source_timestamp=source_timestamp,
            extraction_tier=EXTRACTION_TIER,
            extraction_method=EXTRACTION_METHOD,
            confidence=EXTRACTION_CONFIDENCE,
            extractor_version=EXTRACTOR_VERSION,
        )
        result["config_files"].append(config_file)

        # Create Proxy entity
        proxy = Proxy(
            name=self.proxy_name,
            proxy_type="swag",
            config_path=self.config_path,
            created_at=now,
            updated_at=now,
            source_timestamp=source_timestamp,
            extraction_tier=EXTRACTION_TIER,
            extraction_method=EXTRACTION_METHOD,
            confidence=EXTRACTION_CONFIDENCE,
            extractor_version=EXTRACTOR_VERSION,
        )
        result["proxies"].append(proxy)

        if not config or not config.strip():
            # Empty config - return with just config_file and proxy
            return result

        try:
            # Extract server-level headers (add_header directives)
            server_headers = self._extract_server_headers(config, now, source_timestamp)
            result["proxy_headers"].extend(server_headers)

            # Parse server blocks
            server_blocks = self._extract_server_blocks(config)

            if not server_blocks:
                # No server blocks found - return with config_file and proxy only
                return result

            # Extract entities from all server blocks
            for server_block in server_blocks:
                self._parse_server_block(server_block, result, now, source_timestamp)

            logger.info(
                f"Parsed config: {len(result['config_files'])} config_files, "
                f"{len(result['proxies'])} proxies, {len(result['proxy_routes'])} routes, "
                f"{len(result['location_blocks'])} locations, "
                f"{len(result['upstream_configs'])} upstreams, "
                f"{len(result['proxy_headers'])} headers"
            )

            return result

        except Exception as e:
            raise SwagReaderError(f"Failed to parse nginx config: {e}") from e

    def _extract_server_headers(
        self, config: str, now: datetime, source_timestamp: datetime | None
    ) -> list[ProxyHeader]:
        """Extract server-level header directives (add_header).

        Args:
            config: Full nginx configuration.
            now: Current timestamp.
            source_timestamp: Optional source file modification time.

        Returns:
            list[ProxyHeader]: List of extracted header entities.
        """
        headers: list[ProxyHeader] = []

        # Match add_header directives (outside server blocks)
        # Pattern: add_header Name "Value";
        pattern = r'add_header\s+([^\s]+)\s+"([^"]+)"\s*;'

        for match in re.finditer(pattern, config):
            header_name = match.group(1)
            header_value = match.group(2)

            header = ProxyHeader(
                header_name=header_name,
                header_value=header_value,
                header_type="add_header",
                created_at=now,
                updated_at=now,
                source_timestamp=source_timestamp,
                extraction_tier=EXTRACTION_TIER,
                extraction_method=EXTRACTION_METHOD,
                confidence=EXTRACTION_CONFIDENCE,
                extractor_version=EXTRACTOR_VERSION,
            )
            headers.append(header)

        return headers

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

    def _parse_server_block(
        self,
        server_block: str,
        result: ParsedConfig,
        now: datetime,
        source_timestamp: datetime | None,
    ) -> None:
        """Parse a single server block and extract all entity types.

        Modifies result dictionary in-place by adding extracted entities.

        Args:
            server_block: Server block content.
            result: Result dictionary to populate.
            now: Current timestamp.
            source_timestamp: Optional source file modification time.
        """
        # Extract server_name
        server_name = self._extract_server_name(server_block)
        if not server_name:
            logger.debug("No server_name found in server block, skipping")
            return

        # Detect TLS (check for 'ssl' in listen directive)
        tls = self._detect_tls(server_block)

        # Extract upstream variables
        upstream = self._extract_upstream_variables(server_block)
        if upstream:
            # Extract values with proper types
            app = str(upstream["app"])
            port = int(upstream["port"])
            proto = str(upstream["proto"])

            # Create UpstreamConfig entity
            upstream_config = UpstreamConfig(
                app=app,
                port=port,
                proto=proto,
                created_at=now,
                updated_at=now,
                source_timestamp=source_timestamp,
                extraction_tier=EXTRACTION_TIER,
                extraction_method=EXTRACTION_METHOD,
                confidence=EXTRACTION_CONFIDENCE,
                extractor_version=EXTRACTOR_VERSION,
            )
            result["upstream_configs"].append(upstream_config)

            # Create ProxyRoute entity
            proxy_route = ProxyRoute(
                server_name=server_name,
                upstream_app=app,
                upstream_port=port,
                upstream_proto=proto,
                tls_enabled=tls,
                created_at=now,
                updated_at=now,
                source_timestamp=source_timestamp,
                extraction_tier=EXTRACTION_TIER,
                extraction_method=EXTRACTION_METHOD,
                confidence=EXTRACTION_CONFIDENCE,
                extractor_version=EXTRACTOR_VERSION,
            )
            result["proxy_routes"].append(proxy_route)

        # Extract location blocks
        location_blocks = self._extract_location_blocks(server_block)

        for location_path, location_content in location_blocks:
            # Check for auth_request directive
            auth_enabled = "auth_request" in location_content
            auth_type = "authelia" if auth_enabled else None

            # Extract proxy_pass
            proxy_pass = self._extract_proxy_pass(location_content)

            # Create LocationBlock entity
            location_block = LocationBlock(
                path=location_path,
                proxy_pass_url=proxy_pass,
                auth_enabled=auth_enabled,
                auth_type=auth_type,
                created_at=now,
                updated_at=now,
                source_timestamp=source_timestamp,
                extraction_tier=EXTRACTION_TIER,
                extraction_method=EXTRACTION_METHOD,
                confidence=EXTRACTION_CONFIDENCE,
                extractor_version=EXTRACTOR_VERSION,
            )
            result["location_blocks"].append(location_block)

            # Extract proxy_set_header directives from location
            location_headers = self._extract_location_headers(
                location_content, now, source_timestamp
            )
            result["proxy_headers"].extend(location_headers)

    def _extract_upstream_variables(
        self, server_block: str
    ) -> dict[str, str] | dict[str, str | int] | None:
        """Extract upstream variables from server block.

        Args:
            server_block: Server block content.

        Returns:
            dict with keys: "app" (str), "port" (int), "proto" (str), or None.
        """
        # Pattern: set $upstream_app value;
        app_match = re.search(r"set\s+\$upstream_app\s+([^;]+);", server_block)
        port_match = re.search(r"set\s+\$upstream_port\s+([^;]+);", server_block)
        proto_match = re.search(r"set\s+\$upstream_proto\s+([^;]+);", server_block)

        if not (app_match and port_match and proto_match):
            return None

        try:
            app = app_match.group(1).strip()
            port_str = port_match.group(1).strip()
            proto = proto_match.group(1).strip()

            # Convert port to int
            port_int = int(port_str)

            # Return dict with proper types
            return {"app": app, "port": port_int, "proto": proto}
        except (ValueError, AttributeError):
            return None

    def _extract_location_headers(
        self, location_content: str, now: datetime, source_timestamp: datetime | None
    ) -> list[ProxyHeader]:
        """Extract proxy_set_header directives from location block.

        Args:
            location_content: Location block content.
            now: Current timestamp.
            source_timestamp: Optional source file modification time.

        Returns:
            list[ProxyHeader]: List of extracted header entities.
        """
        headers: list[ProxyHeader] = []

        # Pattern: proxy_set_header Name value;
        pattern = r"proxy_set_header\s+([^\s]+)\s+([^;]+);"

        for match in re.finditer(pattern, location_content):
            header_name = match.group(1).strip()
            header_value = match.group(2).strip()

            header = ProxyHeader(
                header_name=header_name,
                header_value=header_value,
                header_type="proxy_set_header",
                created_at=now,
                updated_at=now,
                source_timestamp=source_timestamp,
                extraction_tier=EXTRACTION_TIER,
                extraction_method=EXTRACTION_METHOD,
                confidence=EXTRACTION_CONFIDENCE,
                extractor_version=EXTRACTOR_VERSION,
            )
            headers.append(header)

        return headers

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
        - http://localhost:4211 -> localhost

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
