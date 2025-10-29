"""Tailscale entity schemas.

Entities extracted from Tailscale API for mesh VPN infrastructure.
"""

from packages.schemas.tailscale.tailscale_acl import TailscaleACL
from packages.schemas.tailscale.tailscale_device import TailscaleDevice
from packages.schemas.tailscale.tailscale_network import TailscaleNetwork

__all__ = [
    "TailscaleDevice",
    "TailscaleNetwork",
    "TailscaleACL",
]
