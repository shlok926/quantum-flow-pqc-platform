"""Quantum Flow Technologies — Scanner Safety & Target Verification.

Enforces strict boundaries against unauthorized, non-testnet, or dangerous target scanning.
"""

import ipaddress
import socket
from typing import Final

# RFC 5737 IPv4 Testnet Addresses
RFC_5737_NETWORKS: Final[list[ipaddress.IPv4Network]] = [
    ipaddress.IPv4Network("192.0.2.0/24"),  # TEST-NET-1
    ipaddress.IPv4Network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.IPv4Network("203.0.113.0/24"),  # TEST-NET-3
]

# RFC 3849 IPv6 Documentation Network
RFC_3849_NETWORK: Final[ipaddress.IPv6Network] = ipaddress.IPv6Network("2001:db8::/32")

# Cloud Provider Metadata Service (AWS/GCP/Azure)
METADATA_IP: Final[ipaddress.IPv4Address] = ipaddress.IPv4Address("169.254.169.254")


class TargetSafetyViolation(Exception):
    """Raised when an inspected target violates scanner safety policies."""


def is_safe_test_target(
    host: str,
    allow_test_targets_only: bool = True,
    allow_private_networks: bool = False,
) -> tuple[bool, str]:
    """Validate whether an endpoint host is safe to scan according to policy.

    Args:
        host: Hostname or IP address to inspect.
        allow_test_targets_only: When True, rejects any target outside RFC 5737/3849 testnets.
        allow_private_networks: When False, strictly blocks RFC 1918 and link-local ranges.

    Returns:
        tuple[bool, str]: (is_allowed, reason_message)
    """
    clean_host = host.strip().lower()
    if not clean_host:
        return False, "Target host cannot be empty"

    # Normalize localhost aliases
    if clean_host in {"localhost", "127.0.0.1", "::1"}:
        return True, "Local loopback target permitted for internal testing"

    # Attempt to resolve IP address if given as hostname
    try:
        ip = ipaddress.ip_address(clean_host)
    except ValueError:
        try:
            # Resolve single A record
            resolved = socket.gethostbyname(clean_host)
            ip = ipaddress.ip_address(resolved)
        except (socket.gaierror, socket.herror) as exc:
            return False, f"Failed to resolve hostname: {exc}"

    # Check Cloud Metadata (Critical SSRF prevention)
    if isinstance(ip, ipaddress.IPv4Address) and ip == METADATA_IP:
        return (
            False,
            "Access to cloud instance metadata service (169.254.169.254) is strictly prohibited",
        )

    # Check RFC 5737 / RFC 3849 Testnets
    in_testnet = False
    if isinstance(ip, ipaddress.IPv4Address):
        in_testnet = any(ip in net for net in RFC_5737_NETWORKS)
    elif isinstance(ip, ipaddress.IPv6Address):
        in_testnet = ip in RFC_3849_NETWORK

    # Strict Testnet Mode Enforcement
    if allow_test_targets_only:
        if in_testnet or ip.is_loopback:
            return True, f"Target IP {ip} is within permitted documentation testnet"
        return (
            False,
            f"Target IP {ip} is not in RFC 5737 / RFC 3849 testnet (ALLOW_TEST_TARGETS_ONLY=True)",
        )

    # Check Private Networks (RFC 1918)
    if not allow_private_networks and (ip.is_private or ip.is_link_local):
        return (
            False,
            f"Target IP {ip} is within private/link-local subnet and private scanning is disabled",
        )

    return True, f"Target IP {ip} conforms to scanning safety rules"
