"""Unit tests for assessment report exporters (RFC 4180 CRLF CSV and Executive Markdown).

Verifies:
1. CSV RFC 4180 strict CRLF (\\r\\n) record delimiters.
2. Complete spreadsheet formula-injection mitigation across standard and exotic prefixes
   (Unicode whitespace, BOM, DEL, control characters).
3. Raw snapshot and evidence invariance (no in-place mutation).
4. Executive Markdown report structure, metrics, distinct scanner mechanisms,
   and NIST remediation roadmap.
"""

from copy import deepcopy

import pytest

from packages.reports.exporter import (
    export_assessment_csv,
    export_assessment_markdown_report,
    sanitize_csv_field,
)


@pytest.fixture
def sample_snapshot() -> dict:
    """Fixture providing a representative assessment report snapshot."""
    return {
        "assessment_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "title": "Quantum Risk Assessment for api.example.com",
        "status": "completed",
        "target_snapshot": {
            "id": "target-uuid-1234",
            "hostname": "api.example.com",
            "environment": "production",
            "business_criticality": "critical",
        },
        "started_at": "2026-11-03T09:00:00Z",
        "completed_at": "2026-11-03T09:05:00Z",
        "methodology_version": "QFT-RISK-v1.0",
        "engine_version": "v1.0.0",
        "report_snapshot_hash": "a" * 64,
        "risk_summary": {
            "max_asset_qvi": 850,
            "overall_score": 850,
            "risk_category": "critical",
            "critical_risk_count": 1,
            "high_risk_count": 1,
            "medium_risk_count": 1,
            "low_risk_count": 0,
            "guarded_risk_count": 0,
        },
        "assets": [
            {
                "asset_key": "cert:sha256:abcd1234ef",
                "asset_type": "certificate",
                "display_name": "api.example.com Leaf TLS Certificate",
                "algorithm_family": "RSA",
                "algorithm_name": "RSA-2048",
                "cryptographic_purpose": "authentication",
                "locator": "api.example.com:443",
                "business_criticality": "critical",
                "classification": "OBSERVED",
                "confidence_score": 1.0,
                "risk_score": 850,
                "risk_category": "critical",
                "quantum_threat_type": "shor_factorisation",
                "remediation_priority": "critical",
                "parameters": {
                    "subject_dn": "CN=api.example.com",
                    "issuer_dn": "CN=Let's Encrypt Authority X3",
                    "valid_from": "2026-01-01T00:00:00Z",
                    "valid_until": "2026-04-01T00:00:00Z",
                },
            },
            {
                "asset_type": "protocol",
                "asset_key": "tls:protocol:1.3",
                "display_name": "TLS 1.3 Endpoint Session",
                "algorithm_family": "TLS",
                "algorithm_name": "TLS_AES_256_GCM_SHA384",
                "cryptographic_purpose": "secure_channel",
                "locator": "api.example.com:443",
                "business_criticality": "high",
                "classification": "OBSERVED",
                "confidence_score": 0.95,
                "risk_score": 350,
                "risk_category": "low",
                "quantum_threat_type": "grover_search",
                "remediation_priority": "low",
                "parameters": {
                    "protocol_version": "1.3",
                    "cipher_suite": "TLS_AES_256_GCM_SHA384",
                },
            },
            {
                "asset_type": "algorithm",
                "asset_key": "src:py:crypto_jwt_sign",
                "display_name": "JWT Token Signing Routine",
                "algorithm_family": "ECC",
                "algorithm_name": "ECDSA-P256",
                "cryptographic_purpose": "digital_signature",
                "locator": "src/auth/jwt_service.py:42",
                "business_criticality": "high",
                "classification": "OBSERVED",
                "confidence_score": 0.90,
                "risk_score": 720,
                "risk_category": "high",
                "quantum_threat_type": "shor_discrete_log",
                "remediation_priority": "high",
                "parameters": {
                    "curve": "P-256",
                },
            },
        ],
        "relationships": [
            {
                "source_asset_key": "tls:protocol:1.3",
                "target_asset_key": "cert:sha256:abcd1234ef",
                "relationship": "authenticates_with",
            }
        ],
        "recommendations": [
            {
                "priority": "critical",
                "category": "algorithm_migration",
                "title": "Migrate RSA-2048 to NIST ML-DSA / ML-KEM",
                "description": "Upgrade TLS certificate and authentication keys to quantum-resistant algorithms per FIPS 204.",
            }
        ],
    }


def test_sanitize_csv_field_standard_triggers() -> None:
    """Verify standard formula triggers '=', '+', '-', '@', '|', '%' are sanitized."""
    assert sanitize_csv_field("=1+1") == "'=1+1"
    assert sanitize_csv_field("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert sanitize_csv_field("-5*2") == "'-5*2"
    assert sanitize_csv_field("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert sanitize_csv_field("|powershell -c calc") == "'|powershell -c calc"
    assert sanitize_csv_field("%COMSPEC%") == "'%COMSPEC%"


def test_sanitize_csv_field_whitespace_and_control_chars() -> None:
    """Verify formula triggers preceded by spaces, tabs, newlines, and control characters."""
    assert sanitize_csv_field("   =calc") == "'   =calc"
    assert sanitize_csv_field("\t+cmd") == "'\t+cmd"
    assert sanitize_csv_field("\r\n-calc") == "'\r\n-calc"
    assert sanitize_csv_field("\x1b|calc") == "'\x1b|calc"
    assert sanitize_csv_field("\x00@SUM") == "'\x00@SUM"


def test_sanitize_csv_field_unicode_whitespace_and_bom() -> None:
    """Verify formula triggers preceded by Unicode spaces (NBSP, ZWSP, ideographic) and BOM."""
    assert sanitize_csv_field("\u00a0=1+1") == "'\u00a0=1+1"  # Non-breaking space
    assert sanitize_csv_field("\u200b+1+1") == "'\u200b+1+1"  # Zero-width space
    assert sanitize_csv_field("\u3000-1-1") == "'\u3000-1-1"  # Ideographic space
    assert sanitize_csv_field("\ufeff@SUM") == "'\ufeff@SUM"  # Byte Order Mark (BOM)
    assert sanitize_csv_field("\x7f%ENV%") == "'\x7f%ENV%"  # DEL character


def test_sanitize_csv_field_benign_values_preserved() -> None:
    """Verify benign strings and numeric values are unchanged."""
    assert sanitize_csv_field("RSA-2048") == "RSA-2048"
    assert sanitize_csv_field("TLS_AES_256_GCM_SHA384") == "TLS_AES_256_GCM_SHA384"
    assert sanitize_csv_field("normal text with spaces") == "normal text with spaces"
    assert sanitize_csv_field(None) == ""
    assert sanitize_csv_field(2048) == "2048"
    assert sanitize_csv_field(128.5) == "128.5"


def test_export_assessment_csv_rfc4180_crlf(sample_snapshot: dict) -> None:
    """Verify CSV exporter strictly uses RFC 4180 CRLF (\\r\\n) record terminators."""
    csv_text = export_assessment_csv(sample_snapshot)

    # Must contain \r\n
    assert "\r\n" in csv_text

    # All record splits must strictly use \r\n (no stray bare \n)
    lines = csv_text.split("\r\n")
    # Last line after terminal \r\n is empty string
    assert lines[-1] == ""
    content_lines = lines[:-1]

    # Exactly 4 lines: 1 header + 3 assets
    assert len(content_lines) == 4

    # Validate 16 expected headers
    headers = [h.strip('"') for h in content_lines[0].split(",")]
    assert len(headers) == 16
    assert headers[0] == "Assessment ID"
    assert headers[1] == "Target Hostname"
    assert headers[2] == "Asset Key"
    assert headers[6] == "Algorithm Name"
    assert headers[12] == "QVI Risk Score"
    assert headers[13] == "Risk Category"
    assert headers[14] == "Quantum Threat Type"
    assert headers[15] == "Remediation Priority"


def test_export_assessment_csv_sanitizes_injection_without_mutating_source(
    sample_snapshot: dict,
) -> None:
    """Verify malicious fields in snapshot are sanitized in CSV output while raw snapshot remains untouched."""
    snapshot_copy = deepcopy(sample_snapshot)
    # Inject formula prefixes into asset
    snapshot_copy["assets"][0]["display_name"] = "=HYPERLINK('http://malicious.com')"
    snapshot_copy["assets"][0]["algorithm_name"] = "+RSA-2048"
    snapshot_copy["assets"][0]["locator"] = "\u00a0@SUM(1)"

    original_display_name = snapshot_copy["assets"][0]["display_name"]
    original_algo_name = snapshot_copy["assets"][0]["algorithm_name"]
    original_locator = snapshot_copy["assets"][0]["locator"]

    csv_text = export_assessment_csv(snapshot_copy)

    # Verify CSV has sanitized prefixes
    assert "'=HYPERLINK" in csv_text
    assert "'+RSA-2048" in csv_text
    assert "'\u00a0@SUM(1)" in csv_text

    # Verify raw snapshot was NOT mutated
    assert snapshot_copy["assets"][0]["display_name"] == original_display_name
    assert snapshot_copy["assets"][0]["algorithm_name"] == original_algo_name
    assert snapshot_copy["assets"][0]["locator"] == original_locator


def test_export_assessment_markdown_report_structure(sample_snapshot: dict) -> None:
    """Verify Executive Markdown report contains all required sections and accurate metrics."""
    md = export_assessment_markdown_report(sample_snapshot, stored_hash="a" * 64)

    # 1. Document Control & Integrity
    assert "# Quantum Flow — Post-Quantum Cryptographic Assessment Report" in md
    assert "**Assessment ID:** `3fa85f64-5717-4562-b3fc-2c963f66afa6`" in md
    assert (
        "Canonical Snapshot Digest SHA-256: `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`"
        in md
    )
    assert "not an asymmetric digital signature" in md

    # 2. Executive Summary Metrics
    assert "**Maximum Asset QVI:** **850 / 1000**" in md
    assert "Asset Risk Distribution" in md
    assert "| **CRITICAL** (800–1000) | 1 |" in md
    assert "| **HIGH** (600–799) | 1 |" in md

    # 3. Discovery Mechanisms (Python AST vs Heuristic Distinction)
    assert "Native Python AST parsing (`ast.parse` and `ast.NodeVisitor`)" in md
    assert "JavaScript / TypeScript Discovery:" in md
    assert "heuristic pattern matching (not AST parsing)" in md
    assert "Java Discovery:" in md
    assert "Dependency Manifest Scanning:" in md

    # 4. Shor and Grover Analysis
    assert "Shor's Algorithm Vulnerability:" in md
    assert "Grover's Algorithm Speedup:" in md
    assert "128-bit symmetric key provides an effective ~64-bit security margin" in md

    # 5. NIST Standards Roadmap
    assert "FIPS 203 (ML-KEM)" in md
    assert "FIPS 204 (ML-DSA)" in md
    assert "FIPS 205 (SLH-DSA)" in md

    # 6. Governance Disclaimer
    assert (
        "Absence of discovery evidence from unexamined sources does NOT constitute proof of post-quantum safety."
        in md
    )
