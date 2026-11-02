"""Quantum Flow Technologies — Hostname Normalisation and Strict DNS Validation.

Enforces RFC 1034 / RFC 1123 DNS hostname syntax and security restrictions.
"""

import ipaddress
import re

# RFC 1123 single label regex (1-63 chars, alphanumeric with interior hyphens)
LABEL_REGEX = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)


class HostnameValidationError(ValueError):
    """Raised when an inspected domain name fails syntactic or security validation."""


def normalize_hostname(raw_hostname: str) -> str:
    """Normalize and strictly validate a fully qualified domain name.

    Rules:
    - Strips whitespace and trailing dot.
    - Converts to lowercase.
    - Rejects URL schemes, paths, ports, query strings, and embedded credentials.
    - Rejects IP literals (IPv4 and IPv6).
    - Enforces IDNA (Punycode) validation.
    - Enforces label length (1-63 chars) and total length (<= 253 chars).
    - Requires at least two labels (e.g. domain.tld).

    Returns:
        str: Normalized, lowercase ASCII hostname.

    Raises:
        HostnameValidationError: If validation fails.
    """
    if not isinstance(raw_hostname, str):
        raise HostnameValidationError("Hostname must be a string")

    cleaned = raw_hostname.strip()
    if not cleaned:
        raise HostnameValidationError("Hostname cannot be empty or blank")

    # Reject URLs with schemes
    if "://" in cleaned:
        raise HostnameValidationError(
            "Hostname must not include a URL scheme (e.g., http://, https://)"
        )

    # Reject embedded userinfo or invalid characters (@)
    if "@" in cleaned:
        raise HostnameValidationError(
            "Hostname must not contain embedded userinfo or invalid characters (@)"
        )
    if "/" in cleaned or "\\" in cleaned:
        raise HostnameValidationError("Hostname must not contain path delimiters")
    if "?" in cleaned or "#" in cleaned:
        raise HostnameValidationError("Hostname must not contain query strings or URL fragments")

    # Reject IP address literals as domain targets (check before port check so ::1 is caught as IPv6)
    try:
        # Check IPv4
        ipaddress.IPv4Address(cleaned)
        raise HostnameValidationError(
            f"IP literal '{cleaned}' is not permitted as a registered domain target"
        )
    except ipaddress.AddressValueError:
        pass

    try:
        # Check IPv6 literal (with or without brackets)
        unbracketed = cleaned.strip("[]")
        ipaddress.IPv6Address(unbracketed)
        raise HostnameValidationError(
            f"IPv6 literal '{cleaned}' is not permitted as a registered domain target"
        )
    except ipaddress.AddressValueError:
        pass

    # Reject port delimiter
    if ":" in cleaned:
        raise HostnameValidationError("Hostname must not include a port number")

    # Strip trailing dot if present (standard FQDN notation)
    if cleaned.endswith("."):
        cleaned = cleaned[:-1]

    if not cleaned:
        raise HostnameValidationError("Hostname root dot alone is not a valid target")

    # Pre-validate label lengths and empty labels prior to IDNA encoding
    raw_labels = cleaned.split(".")
    if len(raw_labels) < 2:
        raise HostnameValidationError(
            "Hostname must be a fully qualified domain name with at least two labels (e.g., example.com)"
        )

    for label in raw_labels:
        if not label:
            raise HostnameValidationError("Hostname contains consecutive empty labels (e.g., '..')")
        if len(label) > 63:
            raise HostnameValidationError(
                f"Label '{label[:15]}...' exceeds maximum allowed length of 63 characters"
            )
        if label.startswith("-") or label.endswith("-"):
            raise HostnameValidationError(f"Label '{label}' must not start or end with a hyphen")

    # Convert IDNA (Internationalized Domain Names) to ASCII punycode
    try:
        ascii_hostname = cleaned.encode("idna").decode("ascii").lower()
    except Exception as exc:
        raise HostnameValidationError(
            f"Invalid internationalized domain name (IDNA): {exc}"
        ) from exc

    # Enforce total length (RFC 1035: max 253 characters)
    if len(ascii_hostname) > 253:
        raise HostnameValidationError(
            f"Hostname length ({len(ascii_hostname)}) exceeds RFC 1035 limit of 253 characters"
        )

    labels = ascii_hostname.split(".")

    # Reject single-label local hostnames (e.g. 'localhost', 'internal')
    if len(labels) < 2:
        raise HostnameValidationError(
            "Hostname must be a fully qualified domain name with at least two labels (e.g., example.com)"
        )

    # Validate each label
    for label in labels:
        if not label:
            raise HostnameValidationError("Hostname contains consecutive empty labels (e.g., '..')")
        if len(label) > 63:
            raise HostnameValidationError(
                f"Label '{label[:15]}...' exceeds maximum allowed length of 63 characters"
            )
        if label.startswith("-") or label.endswith("-"):
            raise HostnameValidationError(f"Label '{label}' must not start or end with a hyphen")
        if not LABEL_REGEX.match(label):
            raise HostnameValidationError(
                f"Label '{label}' contains invalid characters. Only a-z, 0-9, and internal hyphens are allowed."
            )

    # Top-Level Domain (TLD) must not be purely numeric
    tld = labels[-1]
    if tld.isdigit():
        raise HostnameValidationError(f"Top-level domain '{tld}' cannot be purely numeric")

    return ascii_hostname
