"""Security tests for SSRF prevention, DNS rebinding mitigation, and destination pinning."""

import ipaddress
from unittest.mock import patch

from packages.scanner.safety.resolver import (
    SafeDestinationResolver,
    is_ip_prohibited,
    unwrap_ipv4_mapped,
)


def test_public_ips_permitted() -> None:
    """Verify that legitimate globally routable public IPs are allowed."""
    public_v4 = ipaddress.ip_address("93.184.216.34")
    prohibited, reason = is_ip_prohibited(public_v4, allow_test_targets_only=False)
    assert prohibited is False
    assert "globally routable" in reason

    public_v6 = ipaddress.ip_address("2606:2800:220:1:248:1893:25c8:1946")
    prohibited, _ = is_ip_prohibited(public_v6, allow_test_targets_only=False)
    assert prohibited is False


def test_cloud_metadata_blocked() -> None:
    """Verify that cloud metadata IP (169.254.169.254) is strictly blocked."""
    meta_ip = ipaddress.ip_address("169.254.169.254")
    prohibited, reason = is_ip_prohibited(meta_ip)
    assert prohibited is True
    assert "cloud metadata" in reason


def test_rfc1918_private_ips_blocked() -> None:
    """Verify that RFC 1918 subnets (10/8, 172.16/12, 192.168/16) are rejected."""
    for raw in ["10.0.0.1", "10.254.254.254", "172.16.0.1", "172.31.255.255", "192.168.1.1"]:
        ip = ipaddress.ip_address(raw)
        prohibited, reason = is_ip_prohibited(ip)
        assert prohibited is True
        assert "prohibited subnet" in reason or "private network" in reason


def test_loopback_blocked() -> None:
    """Verify that loopback addresses are blocked in production mode."""
    for raw in ["127.0.0.1", "127.0.1.1", "::1"]:
        ip = ipaddress.ip_address(raw)
        prohibited, reason = is_ip_prohibited(ip, allow_loopback_for_tests=False)
        assert prohibited is True
        assert "loopback" in reason or "prohibited subnet" in reason


def test_ipv6_unique_local_and_link_local_blocked() -> None:
    """Verify that IPv6 ULA (fc00::/7) and link-local (fe80::/10) are blocked."""
    ula = ipaddress.ip_address("fd00::1")
    prohibited, _ = is_ip_prohibited(ula)
    assert prohibited is True

    ll = ipaddress.ip_address("fe80::1")
    prohibited, _ = is_ip_prohibited(ll)
    assert prohibited is True


def test_ipv4_mapped_ipv6_unwrapping_and_blocking() -> None:
    """Verify that IPv4-mapped IPv6 addresses representing prohibited targets are unwrapped and blocked."""
    mapped_loopback = ipaddress.ip_address("::ffff:127.0.0.1")
    unwrapped = unwrap_ipv4_mapped(mapped_loopback)
    assert isinstance(unwrapped, ipaddress.IPv4Address)
    assert str(unwrapped) == "127.0.0.1"

    prohibited, reason = is_ip_prohibited(mapped_loopback)
    assert prohibited is True
    assert "loopback" in reason or "prohibited subnet" in reason

    mapped_metadata = ipaddress.ip_address("::ffff:169.254.169.254")
    prohibited, reason = is_ip_prohibited(mapped_metadata)
    assert prohibited is True
    assert "cloud metadata" in reason


def test_resolver_rejects_mixed_dns_answers() -> None:
    """Verify that if DNS returns both public and private records, the destination is rejected."""
    resolver = SafeDestinationResolver(allow_test_targets_only=False)

    # Mock getaddrinfo returning both public IP and a private 10.0.0.1 IP (simulating DNS rebinding or internal leak)
    mock_addrs = [
        (2, 1, 6, "", ("93.184.216.34", 443)),
        (2, 1, 6, "", ("10.0.0.1", 443)),
    ]

    with patch("socket.getaddrinfo", return_value=mock_addrs):
        result = resolver.resolve_destination("rebind.example.com")
        assert result.is_safe is False
        assert result.selected_ip is None
        assert "contains prohibited address 10.0.0.1" in (result.rejection_reason or "")


def test_resolver_pins_safe_ip_deterministically() -> None:
    """Verify that multiple safe public IPs are accepted and one is pinned deterministically."""
    resolver = SafeDestinationResolver(allow_test_targets_only=False)

    mock_addrs = [
        (2, 1, 6, "", ("93.184.216.34", 443)),
        (2, 1, 6, "", ("93.184.216.35", 443)),
    ]

    with patch("socket.getaddrinfo", return_value=mock_addrs):
        result = resolver.resolve_destination("multi.example.com")
        assert result.is_safe is True
        assert result.selected_ip == "93.184.216.34"
        assert len(result.resolved_ips) == 2


def test_resolver_handles_empty_or_failed_dns() -> None:
    """Verify safe handling when DNS returns no records or fails."""
    resolver = SafeDestinationResolver()

    with patch("socket.getaddrinfo", return_value=[]):
        result = resolver.resolve_destination("empty.example.com")
        assert result.is_safe is False
        assert "no A or AAAA records" in (result.rejection_reason or "")

    import socket as sock

    with patch("socket.getaddrinfo", side_effect=sock.gaierror("Name or service not known")):
        result = resolver.resolve_destination("nxdomain.example.com")
        assert result.is_safe is False
        assert "DNS resolution failed" in (result.rejection_reason or "")


def test_resolver_timeout_enforced() -> None:
    """Verify that slow or hanging DNS queries trigger an enforceable application-level timeout."""
    import time

    def slow_resolve(hostname: str) -> list:
        time.sleep(0.3)
        return [(2, 1, 6, "", ("93.184.216.34", 443))]

    resolver = SafeDestinationResolver(dns_timeout_seconds=0.05)
    with (
        resolver,
        patch.object(resolver, "_raw_resolve_addrinfo", side_effect=slow_resolve),
    ):
        result = resolver.resolve_destination("slow.example.com")
        assert result.is_safe is False
        assert result.selected_ip is None
        assert result.resolved_ips == []
        assert "timed out after 0.1s" in (result.rejection_reason or "")


def test_resolver_capacity_exhaustion_protection() -> None:
    """Verify that saturated concurrency queue rejects new requests to protect resolver capacity."""
    # Create resolver with small thread pool and small concurrency limit
    with SafeDestinationResolver(dns_timeout_seconds=0.5, max_resolver_threads=2) as resolver:
        # Drain all concurrency slots
        for _ in range(4):  # max_resolver_threads * 2 = 4
            assert resolver._concurrency_limiter.acquire(blocking=False) is True

        # Next query must be rejected immediately without calling getaddrinfo
        result = resolver.resolve_destination("busy.example.com")
        assert result.is_safe is False
        assert result.selected_ip is None
        assert "capacity exhausted" in (result.rejection_reason or "")

        # Release drained slots
        for _ in range(4):
            resolver._concurrency_limiter.release()


def test_no_connection_attempt_after_dns_timeout() -> None:
    """Verify that BoundedTLSCollector aborts cleanly without opening a socket when DNS times out."""
    import time

    from packages.scanner.tls.collector import BoundedTLSCollector

    def hanging_resolve(hostname: str) -> list:
        time.sleep(0.2)
        return [(2, 1, 6, "", ("93.184.216.34", 443))]

    resolver = SafeDestinationResolver(dns_timeout_seconds=0.05)
    collector = BoundedTLSCollector(resolver=resolver)
    with (
        resolver,
        patch.object(resolver, "_raw_resolve_addrinfo", side_effect=hanging_resolve),
        patch("socket.socket.connect") as mock_connect,
    ):
        result = collector.inspect_target("hanging.example.com")
        assert result.success is False
        assert result.error_code == "SSRF_DESTINATION_REJECTED"
        assert "timed out" in (result.error_message or "")
        # Critical safety check: Socket connect was never attempted!
        mock_connect.assert_not_called()
