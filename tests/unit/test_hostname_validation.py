"""Tests for strict hostname normalization and RFC 1123 DNS validation."""

import pytest

from packages.scanner.safety.hostname import (
    HostnameValidationError,
    normalize_hostname,
)


def test_valid_hostnames() -> None:
    """Verify that syntactically valid domain names normalize to lowercase ASCII."""
    assert normalize_hostname("example.com") == "example.com"
    assert normalize_hostname("EXAMPLE.COM") == "example.com"
    assert normalize_hostname("  Sub.Domain.co.uk  ") == "sub.domain.co.uk"
    assert normalize_hostname("quantum-flow.org") == "quantum-flow.org"
    assert normalize_hostname("a1.b2.c3.xyz") == "a1.b2.c3.xyz"


def test_trailing_dot_stripped() -> None:
    """Verify that standard DNS root trailing dot is safely stripped."""
    assert normalize_hostname("example.com.") == "example.com"
    assert normalize_hostname("sub.example.org.") == "sub.example.org"


def test_idna_punycode_conversion() -> None:
    """Verify that internationalized domain names (IDN) convert to ASCII punycode."""
    assert normalize_hostname("münchen.de") == "xn--mnchen-3ya.de"
    assert normalize_hostname("bücher.example") == "xn--bcher-kva.example"


def test_reject_url_schemes() -> None:
    """Verify that URL schemes are strictly rejected."""
    for scheme in ["http://", "https://", "ftp://", "tls://"]:
        with pytest.raises(HostnameValidationError, match="scheme"):
            normalize_hostname(f"{scheme}example.com")


def test_reject_paths_and_delimiters() -> None:
    """Verify that paths, query parameters, fragments, and userinfo are rejected."""
    with pytest.raises(HostnameValidationError, match="path"):
        normalize_hostname("example.com/api/v1")
    with pytest.raises(HostnameValidationError, match="query"):
        normalize_hostname("example.com?query=1")
    with pytest.raises(HostnameValidationError, match="query"):
        normalize_hostname("example.com#section")
    with pytest.raises(HostnameValidationError, match="userinfo"):
        normalize_hostname("admin:secret@example.com")


def test_reject_port_numbers() -> None:
    """Verify that port suffixes are strictly rejected."""
    with pytest.raises(HostnameValidationError, match="port"):
        normalize_hostname("example.com:443")
    with pytest.raises(HostnameValidationError, match="port"):
        normalize_hostname("example.com:8443")


def test_reject_ip_literals() -> None:
    """Verify that IPv4 and IPv6 literals are rejected as registered domain names."""
    with pytest.raises(HostnameValidationError, match="IP literal"):
        normalize_hostname("192.0.2.1")
    with pytest.raises(HostnameValidationError, match="IP literal"):
        normalize_hostname("127.0.0.1")
    with pytest.raises(HostnameValidationError, match="IPv6 literal"):
        normalize_hostname("::1")
    with pytest.raises(HostnameValidationError, match="IPv6 literal"):
        normalize_hostname("[2001:db8::1]")


def test_reject_single_label_hostnames() -> None:
    """Verify that unqualified single-label hosts like localhost are rejected."""
    with pytest.raises(HostnameValidationError, match="at least two labels"):
        normalize_hostname("localhost")
    with pytest.raises(HostnameValidationError, match="at least two labels"):
        normalize_hostname("intranet")


def test_reject_invalid_labels_and_hyphens() -> None:
    """Verify that invalid characters, empty labels, and hyphens at boundaries are rejected."""
    with pytest.raises(HostnameValidationError, match="hyphen"):
        normalize_hostname("-example.com")
    with pytest.raises(HostnameValidationError, match="hyphen"):
        normalize_hostname("example-.com")
    with pytest.raises(HostnameValidationError, match="empty labels"):
        normalize_hostname("example..com")
    with pytest.raises(HostnameValidationError, match="invalid characters"):
        normalize_hostname("ex@mple.com")


def test_reject_excessive_lengths() -> None:
    """Verify enforcement of 63-character label limits and 253-character FQDN limit."""
    long_label = "a" * 64
    with pytest.raises(HostnameValidationError, match="exceeds maximum allowed length"):
        normalize_hostname(f"{long_label}.com")

    # Exceeding total length
    long_domain = ".".join(["a" * 50 for _ in range(6)])  # 300+ chars
    with pytest.raises(HostnameValidationError, match="exceeds RFC 1035 limit"):
        normalize_hostname(long_domain)
