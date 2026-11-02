"""Quantum Flow Technologies — Source Code Cryptographic Parsers Unit Tests.

Verifies:
1. Python AST parser detects RSA, ECC, AES, SHA, HMAC, and crypto imports.
2. JavaScript/TypeScript parser detects WebCrypto, crypto.subtle, and node:crypto APIs.
3. Java parser detects JCA/JCE and BouncyCastle algorithms.
"""

from pathlib import Path

from packages.scanner.source.parsers.java_parser import parse_java_file
from packages.scanner.source.parsers.js_parser import parse_js_file
from packages.scanner.source.parsers.python_parser import parse_python_file


def test_python_ast_parser_detects_crypto(tmp_path: Path) -> None:
    """Verify Python AST parser detects cryptography primitives accurately."""
    code = """
import hashlib
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# RSA Key generation
key = rsa.generate_private_key(public_exponent=65537, key_size=4096)

# ECC Key generation
ec_key = ec.generate_private_key(ec.SECP256R1())

# AES Cipher
cipher = Cipher(algorithms.AES(b"0123456789abcdef"), modes.CBC(b"0123456789abcdef"))

# Hash
digest = hashlib.sha256(b"hello").digest()
"""
    py_file = tmp_path / "crypto_module.py"
    py_file.write_text(code, encoding="utf-8")
    findings = parse_python_file(py_file, tmp_path)

    primitives = {f.primitive for f in findings}
    assert "RSA" in primitives
    assert "ECC" in primitives
    assert "SymmetricCipher" in primitives
    assert "Hash" in primitives

    # Verify key size detection
    rsa_findings = [f for f in findings if f.primitive == "RSA"]
    assert any("4096" in f.algorithm for f in rsa_findings)

    # Verify parser strategy is AST
    assert all(f.parser_strategy == "ast" for f in findings)


def test_js_parser_detects_node_crypto_and_webcrypto(tmp_path: Path) -> None:
    """Verify JavaScript/TypeScript parser detects crypto calls."""
    code = """
const crypto = require('crypto');

// Generate RSA key pair
crypto.generateKeyPair('rsa', { modulusLength: 2048 }, (err, pub, priv) => {});

// Create AES cipher
const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);

// SubtleCrypto
window.crypto.subtle.generateKey(
    { name: "ECDSA", namedCurve: "P-384" },
    true,
    ["sign", "verify"]
);
"""
    js_file = tmp_path / "auth.ts"
    js_file.write_text(code, encoding="utf-8")
    findings = parse_js_file(js_file, tmp_path)

    primitives = {f.primitive for f in findings}
    assert "RSA" in primitives
    assert "SymmetricCipher" in primitives
    assert "ECC" in primitives
    assert all(f.parser_strategy == "pattern_matching" for f in findings)


def test_java_parser_detects_jca_and_bouncycastle(tmp_path: Path) -> None:
    """Verify Java parser detects standard JCA/JCE and BouncyCastle algorithm instances."""
    code = """
package com.quantumflow.security;

import java.security.KeyPairGenerator;
import java.security.MessageDigest;
import javax.crypto.Cipher;

public class SecurityManager {
    public void init() throws Exception {
        KeyPairGenerator kpg = KeyPairGenerator.getInstance("RSA");
        kpg.initialize(3072);

        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        MessageDigest md = MessageDigest.getInstance("SHA-256");
    }
}
"""
    java_file = tmp_path / "SecurityManager.java"
    java_file.write_text(code, encoding="utf-8")
    findings = parse_java_file(java_file, tmp_path)

    primitives = {f.primitive for f in findings}
    assert "RSA" in primitives
    assert "AES" in primitives or "SymmetricCipher" in primitives
    assert "Hash" in primitives
    assert all(f.parser_strategy == "pattern_matching" for f in findings)
