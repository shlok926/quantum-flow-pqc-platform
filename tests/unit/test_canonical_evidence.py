"""Unit tests for RFC 8785-aligned canonical JSON serialization and SHA-256 integrity verification."""

from packages.scanner.safety.canonical import (
    canonicalize_payload,
    compute_canonical_evidence_sha256,
    verify_evidence_integrity,
)


def test_canonicalize_payload_deterministic_key_ordering() -> None:
    """Verify that dictionaries with different insertion orders yield identical canonical bytes and hashes."""
    dict_a = {"z": 100, "a": "first", "m": [1, 2, 3], "nested": {"k2": True, "k1": False}}
    dict_b = {"a": "first", "nested": {"k1": False, "k2": True}, "m": [1, 2, 3], "z": 100}

    bytes_a = canonicalize_payload(dict_a)
    bytes_b = canonicalize_payload(dict_b)
    assert bytes_a == bytes_b

    hash_a = compute_canonical_evidence_sha256(dict_a)
    hash_b = compute_canonical_evidence_sha256(dict_b)
    assert hash_a == hash_b
    assert len(hash_a) == 64


def test_altered_payload_produces_different_hash() -> None:
    """Verify that altering any value in the payload produces a completely different hash."""
    base = {"target": "example.com", "port": 443, "cipher": "TLS_AES_256_GCM_SHA384"}
    tampered = {"target": "example.com", "port": 443, "cipher": "TLS_AES_128_GCM_SHA256"}

    hash_base = compute_canonical_evidence_sha256(base)
    hash_tampered = compute_canonical_evidence_sha256(tampered)
    assert hash_base != hash_tampered


def test_verify_evidence_integrity() -> None:
    """Verify constant-time verification of matching and tampered evidence."""
    payload = {"hostname": "api.example.com", "protocol": "TLSv1.3", "key_size": 2048}
    digest = compute_canonical_evidence_sha256(payload)

    # Valid matching payload
    assert verify_evidence_integrity(payload, digest) is True
    assert verify_evidence_integrity(payload, digest.upper()) is True

    # Tampered payload
    tampered_payload = {"hostname": "api.example.com", "protocol": "TLSv1.3", "key_size": 1024}
    assert verify_evidence_integrity(tampered_payload, digest) is False

    # Invalid digest strings
    assert verify_evidence_integrity(payload, "") is False
    assert verify_evidence_integrity(payload, "invalid_short_hash") is False
