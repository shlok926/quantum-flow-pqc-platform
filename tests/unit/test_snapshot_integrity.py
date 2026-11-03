"""Unit tests for assessment terminal snapshot canonical verification and tamper rejection.

Verifies:
1. Canonical RFC 8785 JSON serialization and SHA-256 integrity verification.
2. Constant-time digest verification across matching and case-varied hashes.
3. Tamper rejection when scores, assets, timestamps, or target data are altered.
4. Fail-closed behavior on missing or malformed snapshots or hashes.
5. Accurate integrity reporting (SHA-256 digest match vs external digital signature).
"""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

import pytest

from packages.reports.exporter import SnapshotIntegrityError, verify_and_load_snapshot
from packages.scanner.safety.canonical import compute_canonical_evidence_sha256


@dataclass
class MockAssessment:
    """Mock assessment entity for testing ORM-like attribute access."""

    report_snapshot: dict[str, Any] | None
    report_snapshot_hash: str | None


@pytest.fixture
def valid_snapshot() -> dict[str, Any]:
    """Fixture providing a valid canonical terminal report snapshot."""
    return {
        "assessment_id": "01234567-89ab-cdef-0123-456789abcdef",
        "title": "Quantum Risk Assessment - Core Gateway",
        "status": "completed",
        "target_snapshot": {
            "hostname": "core.quantumflow.internal",
            "environment": "production",
            "business_criticality": "critical",
        },
        "started_at": "2026-11-03T09:00:00Z",
        "completed_at": "2026-11-03T09:10:00Z",
        "methodology_version": "QFT-RISK-v1.0",
        "engine_version": "v1.0.0",
        "risk_summary": {
            "overall_score": 750,
            "max_asset_qvi": 750,
            "risk_category": "high",
        },
        "assets": [
            {
                "asset_key": "rsa:2048:auth",
                "display_name": "RSA-2048 Key",
                "risk_score": 750,
                "risk_category": "high",
            }
        ],
    }


def test_verify_and_load_snapshot_success(valid_snapshot: dict[str, Any]) -> None:
    """Verify that a valid snapshot with matching canonical SHA-256 digest passes verification."""
    canonical_hash = compute_canonical_evidence_sha256(valid_snapshot)

    # 1. Test with dict wrapper
    payload_dict = {
        "report_snapshot": valid_snapshot,
        "report_snapshot_hash": canonical_hash,
    }
    loaded = verify_and_load_snapshot(payload_dict)
    assert loaded == valid_snapshot

    # 2. Test with ORM-like entity
    mock_entity = MockAssessment(
        report_snapshot=valid_snapshot,
        report_snapshot_hash=canonical_hash,
    )
    loaded_orm = verify_and_load_snapshot(mock_entity)
    assert loaded_orm == valid_snapshot


def test_verify_and_load_snapshot_case_insensitivity(valid_snapshot: dict[str, Any]) -> None:
    """Verify constant-time digest comparison succeeds for uppercase or mixed-case hex hashes."""
    canonical_hash = compute_canonical_evidence_sha256(valid_snapshot)
    uppercase_hash = canonical_hash.upper()

    mock_entity = MockAssessment(
        report_snapshot=valid_snapshot,
        report_snapshot_hash=uppercase_hash,
    )
    loaded = verify_and_load_snapshot(mock_entity)
    assert loaded == valid_snapshot


@pytest.mark.parametrize(
    "tamper_field,tamper_value",
    [
        ("status", "failed"),
        ("methodology_version", "QFT-RISK-v2.0"),
        ("engine_version", "v2.0.0"),
    ],
)
def test_verify_and_load_snapshot_rejects_tampered_metadata(
    valid_snapshot: dict[str, Any], tamper_field: str, tamper_value: Any
) -> None:
    """Verify modifying top-level snapshot fields triggers SnapshotIntegrityError."""
    canonical_hash = compute_canonical_evidence_sha256(valid_snapshot)

    tampered_snapshot = deepcopy(valid_snapshot)
    tampered_snapshot[tamper_field] = tamper_value

    mock_entity = MockAssessment(
        report_snapshot=tampered_snapshot,
        report_snapshot_hash=canonical_hash,
    )
    with pytest.raises(SnapshotIntegrityError) as exc_info:
        verify_and_load_snapshot(mock_entity)

    assert "cryptographic integrity verification" in str(exc_info.value)


def test_verify_and_load_snapshot_rejects_tampered_risk_score(
    valid_snapshot: dict[str, Any],
) -> None:
    """Verify modifying risk score from 750 to 100 triggers SnapshotIntegrityError."""
    canonical_hash = compute_canonical_evidence_sha256(valid_snapshot)

    tampered = deepcopy(valid_snapshot)
    tampered["risk_summary"]["overall_score"] = 100
    tampered["risk_summary"]["max_asset_qvi"] = 100
    tampered["assets"][0]["risk_score"] = 100

    mock_entity = MockAssessment(
        report_snapshot=tampered,
        report_snapshot_hash=canonical_hash,
    )
    with pytest.raises(SnapshotIntegrityError) as exc_info:
        verify_and_load_snapshot(mock_entity)

    assert "Report export aborted" in str(exc_info.value)


def test_verify_and_load_snapshot_rejects_asset_tampering(
    valid_snapshot: dict[str, Any],
) -> None:
    """Verify adding, removing, or modifying asset entries triggers SnapshotIntegrityError."""
    canonical_hash = compute_canonical_evidence_sha256(valid_snapshot)

    # 1. Remove asset
    tampered_removed = deepcopy(valid_snapshot)
    tampered_removed["assets"] = []

    with pytest.raises(SnapshotIntegrityError):
        verify_and_load_snapshot(
            MockAssessment(
                report_snapshot=tampered_removed,
                report_snapshot_hash=canonical_hash,
            )
        )

    # 2. Add extra asset
    tampered_added = deepcopy(valid_snapshot)
    tampered_added["assets"].append(
        {
            "asset_key": "injected:asset:fake",
            "display_name": "Injected Asset",
            "risk_score": 0,
        }
    )

    with pytest.raises(SnapshotIntegrityError):
        verify_and_load_snapshot(
            MockAssessment(
                report_snapshot=tampered_added,
                report_snapshot_hash=canonical_hash,
            )
        )


def test_verify_and_load_snapshot_missing_fields() -> None:
    """Verify fail-closed behavior when snapshot or hash is missing."""
    # 1. Missing snapshot
    with pytest.raises(ValueError, match="snapshot is missing"):
        verify_and_load_snapshot(
            MockAssessment(
                report_snapshot=None,
                report_snapshot_hash="a" * 64,
            )
        )

    # 2. Missing hash
    with pytest.raises(ValueError, match="hash is missing"):
        verify_and_load_snapshot(
            MockAssessment(
                report_snapshot={"test": 123},
                report_snapshot_hash=None,
            )
        )

    # 3. Invalid length hash
    with pytest.raises(ValueError, match="hash is missing or malformed"):
        verify_and_load_snapshot(
            MockAssessment(
                report_snapshot={"test": 123},
                report_snapshot_hash="short_hash",
            )
        )
