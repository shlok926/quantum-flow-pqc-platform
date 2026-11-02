"""Quantum Flow Technologies — Cryptographic Algorithm & Quantum Threat Catalogue.

Categorises cryptographic algorithms and primitives into Shor-vulnerable,
Grover security margin, classical weak, or PQC-standardised categories.
"""

from typing import Any

ALGORITHM_CATALOGUE: dict[str, dict[str, Any]] = {
    # --------------------------------------------------------------------------
    # Shor-Vulnerable Public Key Primitives (Factoring & Discrete Logarithms)
    # --------------------------------------------------------------------------
    "RSA-1024": {
        "family": "RSA",
        "threat_type": "shor_vulnerable",
        "quantum_susceptibility_rating": 5,
        "classical_security_bits": 80,
        "quantum_security_bits": 0,
        "is_pqc": False,
        "summary": "RSA-1024 is vulnerable to Shor's algorithm and already deprecated classically.",
    },
    "RSA-2048": {
        "family": "RSA",
        "threat_type": "shor_vulnerable",
        "quantum_susceptibility_rating": 4,
        "classical_security_bits": 112,
        "quantum_security_bits": 0,
        "is_pqc": False,
        "summary": "RSA-2048 is completely breakable by polynomial-time Shor's factoring on a CRQC.",
    },
    "RSA-3072": {
        "family": "RSA",
        "threat_type": "shor_vulnerable",
        "quantum_susceptibility_rating": 4,
        "classical_security_bits": 128,
        "quantum_security_bits": 0,
        "is_pqc": False,
        "summary": "RSA-3072 provides 128-bit classical security but is completely vulnerable to Shor's algorithm.",
    },
    "RSA-4096": {
        "family": "RSA",
        "threat_type": "shor_vulnerable",
        "quantum_susceptibility_rating": 4,
        "classical_security_bits": 140,
        "quantum_security_bits": 0,
        "is_pqc": False,
        "summary": "RSA-4096 provides high classical strength but offers zero security against Shor's algorithm.",
    },
    "ECDSA-SECP256R1": {
        "family": "ECC",
        "threat_type": "shor_vulnerable",
        "quantum_susceptibility_rating": 4,
        "classical_security_bits": 128,
        "quantum_security_bits": 0,
        "is_pqc": False,
        "summary": "ECDSA over secp256r1 is completely compromised by Shor's discrete logarithm algorithm.",
    },
    "ECDSA-SECP384R1": {
        "family": "ECC",
        "threat_type": "shor_vulnerable",
        "quantum_susceptibility_rating": 4,
        "classical_security_bits": 192,
        "quantum_security_bits": 0,
        "is_pqc": False,
        "summary": "ECDSA over secp384r1 is completely compromised by Shor's discrete logarithm algorithm.",
    },
    "ECDH-X25519": {
        "family": "ECC",
        "threat_type": "shor_vulnerable",
        "quantum_susceptibility_rating": 4,
        "classical_security_bits": 128,
        "quantum_security_bits": 0,
        "is_pqc": False,
        "summary": "X25519 key exchange relies on Curve25519 discrete log, completely vulnerable to Shor.",
    },
    # --------------------------------------------------------------------------
    # Symmetric Ciphers & Hashes (Grover Quadratic Speedup Margin)
    # --------------------------------------------------------------------------
    "AES-128": {
        "family": "AES",
        "threat_type": "grover_margin",
        "quantum_susceptibility_rating": 2,
        "classical_security_bits": 128,
        "quantum_security_bits": 64,
        "is_pqc": False,
        "summary": "Grover's algorithm reduces effective search space to 64 bits; migration to AES-256 recommended.",
    },
    "AES-256": {
        "family": "AES",
        "threat_type": "grover_margin",
        "quantum_susceptibility_rating": 1,
        "classical_security_bits": 256,
        "quantum_security_bits": 128,
        "is_pqc": False,
        "summary": "AES-256 retains 128 bits of quantum security under Grover's algorithm; safe quantum security margin.",
    },
    "SHA-256": {
        "family": "SHA-2",
        "threat_type": "grover_margin",
        "quantum_susceptibility_rating": 1,
        "classical_security_bits": 256,
        "quantum_security_bits": 128,
        "is_pqc": False,
        "summary": "SHA-256 retains adequate collision and preimage resistance under Grover/BHT quantum bounds.",
    },
    "SHA-384": {
        "family": "SHA-2",
        "threat_type": "grover_margin",
        "quantum_susceptibility_rating": 1,
        "classical_security_bits": 384,
        "quantum_security_bits": 192,
        "is_pqc": False,
        "summary": "SHA-384 provides strong quantum security margins.",
    },
    "SHA-512": {
        "family": "SHA-2",
        "threat_type": "grover_margin",
        "quantum_susceptibility_rating": 1,
        "classical_security_bits": 512,
        "quantum_security_bits": 256,
        "is_pqc": False,
        "summary": "SHA-512 provides maximum quantum security margins against Grover's algorithm.",
    },
    "MD5": {
        "family": "LegacyHash",
        "threat_type": "classical_weak",
        "quantum_susceptibility_rating": 5,
        "classical_security_bits": 0,
        "quantum_security_bits": 0,
        "is_pqc": False,
        "summary": "MD5 is completely broken classically and cryptographically insecure.",
    },
    "SHA-1": {
        "family": "LegacyHash",
        "threat_type": "classical_weak",
        "quantum_susceptibility_rating": 4,
        "classical_security_bits": 60,
        "quantum_security_bits": 0,
        "is_pqc": False,
        "summary": "SHA-1 collision resistance is broken classically and obsolete.",
    },
    # --------------------------------------------------------------------------
    # Post-Quantum Cryptography (NIST Standardised FIPS 203, 204, 205)
    # --------------------------------------------------------------------------
    "ML-KEM-768": {
        "family": "ML-KEM",
        "threat_type": "pqc_recognised",
        "quantum_susceptibility_rating": 0,
        "classical_security_bits": 192,
        "quantum_security_bits": 192,
        "is_pqc": True,
        "summary": "NIST FIPS 203 standardized module-lattice key encapsulation mechanism (Category 3).",
    },
    "ML-KEM-1024": {
        "family": "ML-KEM",
        "threat_type": "pqc_recognised",
        "quantum_susceptibility_rating": 0,
        "classical_security_bits": 256,
        "quantum_security_bits": 256,
        "is_pqc": True,
        "summary": "NIST FIPS 203 standardized module-lattice key encapsulation mechanism (Category 5).",
    },
    "ML-DSA-65": {
        "family": "ML-DSA",
        "threat_type": "pqc_recognised",
        "quantum_susceptibility_rating": 0,
        "classical_security_bits": 192,
        "quantum_security_bits": 192,
        "is_pqc": True,
        "summary": "NIST FIPS 204 standardized module-lattice digital signature algorithm (Category 3).",
    },
}


def lookup_algorithm_threat(family: str | None, name: str | None) -> dict[str, Any]:
    """Look up an algorithm's quantum threat profile in the catalogue."""
    key = (name or family or "").upper().strip()
    if key in ALGORITHM_CATALOGUE:
        return ALGORITHM_CATALOGUE[key]

    # Partial match
    for cat_key, info in ALGORITHM_CATALOGUE.items():
        if cat_key in key or key in cat_key:
            return info

    # Fallback for general families
    if "RSA" in key:
        return ALGORITHM_CATALOGUE["RSA-2048"]
    elif "EC" in key or "CURVE" in key:
        return ALGORITHM_CATALOGUE["ECDSA-SECP256R1"]
    elif "AES" in key:
        return ALGORITHM_CATALOGUE["AES-256"] if "256" in key else ALGORITHM_CATALOGUE["AES-128"]
    elif "SHA-256" in key or "SHA256" in key:
        return ALGORITHM_CATALOGUE["SHA-256"]
    elif "SHA-512" in key or "SHA512" in key:
        return ALGORITHM_CATALOGUE["SHA-512"]
    elif "KEM" in key or "KYBER" in key:
        return ALGORITHM_CATALOGUE["ML-KEM-768"]
    elif "DILITHIUM" in key or "DSA" in key:
        return ALGORITHM_CATALOGUE["ML-DSA-65"]

    return {
        "family": family or "Unknown",
        "threat_type": "unknown",
        "quantum_susceptibility_rating": 3,
        "classical_security_bits": 0,
        "quantum_security_bits": 0,
        "is_pqc": False,
        "summary": "Algorithm not recognized in catalogue; manual security assessment required.",
    }
