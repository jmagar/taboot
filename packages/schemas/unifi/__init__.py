"""Unifi entity schemas.

Represents entities extracted from Unifi Controller API.
"""

from packages.schemas.unifi.firewall_rule import FirewallRule
from packages.schemas.unifi.nat_rule import NATRule
from packages.schemas.unifi.port_forwarding_rule import PortForwardingRule
from packages.schemas.unifi.traffic_route import TrafficRoute
from packages.schemas.unifi.traffic_rule import TrafficRule
from packages.schemas.unifi.unifi_client import UnifiClient
from packages.schemas.unifi.unifi_device import UnifiDevice
from packages.schemas.unifi.unifi_network import UnifiNetwork
from packages.schemas.unifi.unifi_site import UnifiSite

__all__ = [
    "FirewallRule",
    "NATRule",
    "PortForwardingRule",
    "TrafficRoute",
    "TrafficRule",
    "UnifiClient",
    "UnifiDevice",
    "UnifiNetwork",
    "UnifiSite",
]
