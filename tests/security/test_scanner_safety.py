"""Security tests for scanner safety constraints and RFC 5737/3849 boundaries."""

from packages.scanner.safety.validator import is_safe_test_target


def test_rfc5737_testnet_allowed() -> None:
    """Verify that RFC 5737 testnet IPs are allowed under test-target policy."""
    # TEST-NET-1
    allowed, msg = is_safe_test_target("192.0.2.1", allow_test_targets_only=True)
    assert allowed is True
    assert "permitted documentation testnet" in msg

    # TEST-NET-2
    allowed, _ = is_safe_test_target("198.51.100.42", allow_test_targets_only=True)
    assert allowed is True

    # TEST-NET-3
    allowed, _ = is_safe_test_target("203.0.113.254", allow_test_targets_only=True)
    assert allowed is True


def test_rfc3849_ipv6_testnet_allowed() -> None:
    """Verify that RFC 3849 documentation IPv6 addresses are permitted."""
    allowed, msg = is_safe_test_target("2001:db8::1", allow_test_targets_only=True)
    assert allowed is True
    assert "permitted documentation testnet" in msg


def test_cloud_metadata_ip_blocked() -> None:
    """Verify that AWS/GCP/Azure instance metadata (169.254.169.254) is always blocked."""
    allowed, msg = is_safe_test_target("169.254.169.254", allow_test_targets_only=False)
    assert allowed is False
    assert "cloud instance metadata service" in msg


def test_arbitrary_public_target_rejected_under_test_mode() -> None:
    """Verify that public internet IP addresses are rejected when test-only mode is active."""
    # Cloudflare DNS IP
    allowed, msg = is_safe_test_target("1.1.1.1", allow_test_targets_only=True)
    assert allowed is False
    assert "ALLOW_TEST_TARGETS_ONLY=True" in msg

    # Google DNS IP
    allowed, msg = is_safe_test_target("8.8.8.8", allow_test_targets_only=True)
    assert allowed is False
    assert "ALLOW_TEST_TARGETS_ONLY=True" in msg


def test_private_network_blocked_when_disabled() -> None:
    """Verify that RFC 1918 private addresses are blocked when allow_private_networks=False."""
    allowed, msg = is_safe_test_target(
        "10.0.0.1",
        allow_test_targets_only=False,
        allow_private_networks=False,
    )
    assert allowed is False
    assert "private/link-local subnet" in msg


def test_empty_host_rejected() -> None:
    """Verify that empty host strings are rejected."""
    allowed, msg = is_safe_test_target("   ")
    assert allowed is False
    assert "cannot be empty" in msg
