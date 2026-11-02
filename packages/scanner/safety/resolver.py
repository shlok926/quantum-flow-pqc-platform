"""Quantum Flow Technologies — SSRF and DNS Rebinding Safety Engine.

Provides deep destination address inspection, anti-rebinding IP pinning,
and strict rejection of prohibited IP address classes.
"""

import dataclasses
import ipaddress
import socket
import threading
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any, Final

# RFC 5737 IPv4 Testnets
RFC_5737_NETWORKS: Final[list[ipaddress.IPv4Network]] = [
    ipaddress.IPv4Network("192.0.2.0/24"),  # TEST-NET-1
    ipaddress.IPv4Network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.IPv4Network("203.0.113.0/24"),  # TEST-NET-3
]

# RFC 3849 IPv6 Documentation Network
RFC_3849_NETWORK: Final[ipaddress.IPv6Network] = ipaddress.IPv6Network("2001:db8::/32")

# Cloud Instance Metadata IPv4 (AWS, GCP, Azure, DigitalOcean)
METADATA_IPV4: Final[ipaddress.IPv4Address] = ipaddress.IPv4Address("169.254.169.254")

# Reserved / Special-Use IPv4 Ranges
PROHIBITED_IPV4_NETWORKS: Final[list[ipaddress.IPv4Network]] = [
    ipaddress.IPv4Network("0.0.0.0/8"),  # Current network ("this" host)
    ipaddress.IPv4Network("10.0.0.0/8"),  # RFC 1918 Private
    ipaddress.IPv4Network("100.64.0.0/10"),  # RFC 6598 Shared Address Space (Carrier-grade NAT)
    ipaddress.IPv4Network("127.0.0.0/8"),  # RFC 1122 Loopback
    ipaddress.IPv4Network("169.254.0.0/16"),  # RFC 3927 Link-Local & Metadata
    ipaddress.IPv4Network("172.16.0.0/12"),  # RFC 1918 Private
    ipaddress.IPv4Network("192.0.0.0/24"),  # IETF Protocol Assignments
    ipaddress.IPv4Network("192.168.0.0/16"),  # RFC 1918 Private
    ipaddress.IPv4Network("198.18.0.0/15"),  # RFC 2544 Benchmarking
    ipaddress.IPv4Network("224.0.0.0/4"),  # RFC 5771 Multicast
    ipaddress.IPv4Network("240.0.0.0/4"),  # RFC 1112 Reserved for future use
    ipaddress.IPv4Network("255.255.255.255/32"),  # Broadcast
]

# Prohibited IPv6 Ranges
PROHIBITED_IPV6_NETWORKS: Final[list[ipaddress.IPv6Network]] = [
    ipaddress.IPv6Network("::/128"),  # Unspecified
    ipaddress.IPv6Network("::1/128"),  # Loopback
    ipaddress.IPv6Network("100::/64"),  # Discard prefix (RFC 6666)
    ipaddress.IPv6Network("fc00::/7"),  # Unique Local Address (ULA)
    ipaddress.IPv6Network("fe80::/10"),  # Link-Local Unicast
    ipaddress.IPv6Network("ff00::/8"),  # Multicast
]


class ResolutionSecurityError(Exception):
    """Raised when destination resolution violates safety boundaries."""


@dataclasses.dataclass(frozen=True)
class ResolutionResult:
    """Structured result of DNS resolution and destination validation."""

    original_hostname: str
    resolved_ips: list[str]
    selected_ip: str | None
    resolved_at: datetime
    is_safe: bool
    rejection_reason: str | None = None


def unwrap_ipv4_mapped(
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    """Unwrap IPv4-mapped IPv6 address (e.g. ::ffff:10.0.0.1 -> 10.0.0.1) if present."""
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return ip.ipv4_mapped
    return ip


def is_ip_prohibited(
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address,
    allow_test_targets_only: bool = False,
    allow_loopback_for_tests: bool = False,
) -> tuple[bool, str]:
    """Inspect whether an IP address belongs to a prohibited or dangerous subnet.

    Returns:
        tuple[bool, str]: (is_prohibited, reason)
    """
    unwrapped = unwrap_ipv4_mapped(ip)

    # Check Cloud Metadata service
    if isinstance(unwrapped, ipaddress.IPv4Address) and unwrapped == METADATA_IPV4:
        return True, f"Destination {ip} matches prohibited cloud metadata IP (169.254.169.254)"

    # Controlled test fixture loopback allowance
    if allow_loopback_for_tests and unwrapped.is_loopback:
        return False, "Loopback permitted exclusively in local test fixture"

    # RFC 5737 / RFC 3849 Testnet handling
    in_testnet = False
    if isinstance(unwrapped, ipaddress.IPv4Address):
        in_testnet = any(unwrapped in net for net in RFC_5737_NETWORKS)
    elif isinstance(unwrapped, ipaddress.IPv6Address):
        in_testnet = unwrapped in RFC_3849_NETWORK

    if allow_test_targets_only:
        if in_testnet or (allow_loopback_for_tests and unwrapped.is_loopback):
            return False, "Target permitted within RFC 5737/3849 testnet scope"
        return (
            True,
            f"Address {ip} rejected: outside RFC 5737/3849 testnet under ALLOW_TEST_TARGETS_ONLY=True",
        )

    # In production, RFC 5737/3849 are non-routable documentation ranges and must also be prohibited
    if in_testnet:
        return True, f"Address {ip} is an unroutable documentation testnet address"

    # Check against prohibited IPv4 networks
    if isinstance(unwrapped, ipaddress.IPv4Address):
        for net in PROHIBITED_IPV4_NETWORKS:
            if unwrapped in net:
                return True, f"IPv4 address {ip} belongs to prohibited subnet {net}"

    # Check against prohibited IPv6 networks
    if isinstance(unwrapped, ipaddress.IPv6Address):
        for net6 in PROHIBITED_IPV6_NETWORKS:
            if unwrapped in net6:
                return True, f"IPv6 address {ip} belongs to prohibited subnet {net6}"

    # General sanity checks
    if unwrapped.is_private:
        return True, f"Address {ip} is a private network address"
    if unwrapped.is_loopback:
        return True, f"Address {ip} is a loopback address"
    if unwrapped.is_link_local:
        return True, f"Address {ip} is a link-local address"
    if unwrapped.is_multicast:
        return True, f"Address {ip} is a multicast address"
    if unwrapped.is_unspecified:
        return True, f"Address {ip} is an unspecified address"
    if not unwrapped.is_global:
        return True, f"Address {ip} is not globally routable"

    return False, "Address is globally routable and permitted"


class SafeDestinationResolver:
    """Resolves DNS hostnames into validated, pinned IP addresses protected against SSRF and rebinding."""

    def __init__(
        self,
        allow_test_targets_only: bool = False,
        allow_loopback_for_tests: bool = False,
        dns_timeout_seconds: float = 3.0,
        max_resolver_threads: int = 10,
    ) -> None:
        self.allow_test_targets_only = allow_test_targets_only
        self.allow_loopback_for_tests = allow_loopback_for_tests
        self.dns_timeout_seconds = dns_timeout_seconds
        self.max_resolver_threads = max_resolver_threads
        self._executor = ThreadPoolExecutor(
            max_workers=max_resolver_threads,
            thread_name_prefix="qf_dns_resolver",
        )
        # Bounded concurrency limiter: permits up to max_resolver_threads * 2 queued/active lookups
        self._concurrency_limiter = threading.Semaphore(max_resolver_threads * 2)

    def _raw_resolve_addrinfo(
        self, clean_hostname: str
    ) -> Sequence[tuple[int, int, int, str, Any]]:
        """Perform raw blocking socket.getaddrinfo lookup inside a bounded worker thread."""
        return socket.getaddrinfo(
            clean_hostname,
            443,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
        )

    def close(self) -> None:
        """Shut down the background resolver thread pool."""
        self._executor.shutdown(wait=False, cancel_futures=True)

    def __enter__(self) -> "SafeDestinationResolver":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def resolve_destination(self, hostname: str) -> ResolutionResult:
        """Resolve all A and AAAA records for hostname and validate every answer.

        Guarantees:
        - Strictly bounds lookup execution by dns_timeout_seconds.
        - Guards against thread exhaustion via concurrency limiter.
        - Discards late results from timed-out queries.
        - Rejects mixed public/private answers.
        - Rejects any destination if any single record is prohibited.
        - Selects and pins a single validated IP address for subsequent socket connection.
        """
        now = datetime.now(UTC)
        clean_hostname = hostname.strip().lower()

        # Handle local test fixture loopback aliases
        if self.allow_loopback_for_tests and clean_hostname in {"localhost", "127.0.0.1", "::1"}:
            selected = "127.0.0.1"
            return ResolutionResult(
                original_hostname=clean_hostname,
                resolved_ips=[selected],
                selected_ip=selected,
                resolved_at=now,
                is_safe=True,
            )

        # Acquire slot from concurrency limiter to prevent thread/queue exhaustion
        if not self._concurrency_limiter.acquire(blocking=False):
            return ResolutionResult(
                original_hostname=clean_hostname,
                resolved_ips=[],
                selected_ip=None,
                resolved_at=now,
                is_safe=False,
                rejection_reason="DNS resolver capacity exhausted; request rejected to prevent resource exhaustion",
            )

        resolved_addresses: set[str] = set()
        future = self._executor.submit(self._raw_resolve_addrinfo, clean_hostname)
        future.add_done_callback(lambda _: self._concurrency_limiter.release())

        try:
            addr_info = future.result(timeout=self.dns_timeout_seconds)
            for entry in addr_info:
                sockaddr = entry[4]
                ip_str = str(sockaddr[0])
                resolved_addresses.add(ip_str)
        except TimeoutError:
            future.cancel()
            return ResolutionResult(
                original_hostname=clean_hostname,
                resolved_ips=[],
                selected_ip=None,
                resolved_at=now,
                is_safe=False,
                rejection_reason=f"DNS resolution timed out after {self.dns_timeout_seconds:.1f}s",
            )
        except (socket.gaierror, socket.herror) as exc:
            return ResolutionResult(
                original_hostname=clean_hostname,
                resolved_ips=[],
                selected_ip=None,
                resolved_at=now,
                is_safe=False,
                rejection_reason=f"DNS resolution failed: {exc}",
            )
        except Exception as exc:
            return ResolutionResult(
                original_hostname=clean_hostname,
                resolved_ips=[],
                selected_ip=None,
                resolved_at=now,
                is_safe=False,
                rejection_reason=f"Unexpected DNS resolution error: {exc}",
            )

        if not resolved_addresses:
            return ResolutionResult(
                original_hostname=clean_hostname,
                resolved_ips=[],
                selected_ip=None,
                resolved_at=now,
                is_safe=False,
                rejection_reason="DNS returned no A or AAAA records",
            )

        # Inspect EVERY resolved IP address
        all_ips_ordered = sorted(resolved_addresses)
        for ip_str in all_ips_ordered:
            try:
                ip_obj = ipaddress.ip_address(ip_str)
            except ValueError:
                return ResolutionResult(
                    original_hostname=clean_hostname,
                    resolved_ips=all_ips_ordered,
                    selected_ip=None,
                    resolved_at=now,
                    is_safe=False,
                    rejection_reason=f"DNS returned invalid IP representation: '{ip_str}'",
                )

            prohibited, reason = is_ip_prohibited(
                ip_obj,
                allow_test_targets_only=self.allow_test_targets_only,
                allow_loopback_for_tests=self.allow_loopback_for_tests,
            )
            if prohibited:
                # If ANY address is prohibited, reject the entire destination (anti-mixed rebinding defense)
                return ResolutionResult(
                    original_hostname=clean_hostname,
                    resolved_ips=all_ips_ordered,
                    selected_ip=None,
                    resolved_at=now,
                    is_safe=False,
                    rejection_reason=f"DNS answer contains prohibited address {ip_str}: {reason}",
                )

        # Pin the first deterministically ordered safe IP address
        selected_ip = all_ips_ordered[0]
        return ResolutionResult(
            original_hostname=clean_hostname,
            resolved_ips=all_ips_ordered,
            selected_ip=selected_ip,
            resolved_at=now,
            is_safe=True,
            rejection_reason=None,
        )

    def revalidate_pinned_ip(self, ip_str: str) -> bool:
        """Immediately re-verify a pinned IP prior to opening a socket."""
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            prohibited, _ = is_ip_prohibited(
                ip_obj,
                allow_test_targets_only=self.allow_test_targets_only,
                allow_loopback_for_tests=self.allow_loopback_for_tests,
            )
            return not prohibited
        except ValueError:
            return False
