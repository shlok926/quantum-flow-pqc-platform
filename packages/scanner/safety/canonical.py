"""Quantum Flow Technologies — Observation Evidence Canonicalization & Cryptographic Integrity.

Provides RFC 8785-aligned canonical JSON serialization and SHA-256 integrity verification
for Cryptographic Bill of Materials (CBOM) observation evidence payloads.
"""

import hashlib
import hmac
import json
from typing import Any


def canonicalize_payload(payload: dict[str, Any]) -> bytes:
    """Serialize evidence payload into deterministic canonical UTF-8 JSON bytes.

    Principles:
    - Strictly sorted dictionary keys (recursive).
    - Compact delimiters with no extraneous whitespace (',', ':').
    - Native UTF-8 characters without ASCII escape sequences.
    - Deterministic representation independent of dictionary insertion order.
    """
    if not isinstance(payload, dict):
        raise TypeError(f"Evidence payload must be a dict, got {type(payload).__name__}")

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def compute_canonical_evidence_sha256(payload: dict[str, Any]) -> str:
    """Compute the SHA-256 hexadecimal digest of canonical serialized evidence bytes.

    Returns:
        str: 64-character lowercase hexadecimal SHA-256 digest.
    """
    canonical_bytes = canonicalize_payload(payload)
    return hashlib.sha256(canonical_bytes).hexdigest().lower()


def verify_evidence_integrity(payload: dict[str, Any], stored_sha256: str) -> bool:
    """Verify that an evidence payload matches a previously recorded SHA-256 digest.

    Uses constant-time comparison to protect against timing discrepancies.

    Returns:
        bool: True if computed canonical hash strictly matches stored_sha256.
    """
    if not stored_sha256 or len(stored_sha256.strip()) != 64:
        return False

    computed = compute_canonical_evidence_sha256(payload)
    return hmac.compare_digest(computed, stored_sha256.strip().lower())
