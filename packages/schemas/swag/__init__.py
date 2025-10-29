"""SWAG entity schemas.

Entities extracted from SWAG nginx configuration files.
"""

from packages.schemas.swag.location_block import LocationBlock
from packages.schemas.swag.proxy import Proxy
from packages.schemas.swag.proxy_header import ProxyHeader
from packages.schemas.swag.proxy_route import ProxyRoute
from packages.schemas.swag.swag_config_file import SwagConfigFile
from packages.schemas.swag.upstream_config import UpstreamConfig

__all__ = [
    "LocationBlock",
    "Proxy",
    "ProxyHeader",
    "ProxyRoute",
    "SwagConfigFile",
    "UpstreamConfig",
]
