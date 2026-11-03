"""Quantum Flow Technologies — Assessment Database Model & Integrity Constraint Tests.

Validates schema constraints, referential integrity, CASCADE/RESTRICT behaviors,
and snapshot immutability triggers on PostgreSQL 16.
"""

import os
import socket
import uuid
from collections.abc import Generator
from urllib.parse import urlparse

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from packages.scanner.safety.canonical import (
    compute_canonical_evidence_sha256,
    compute_canonical_scope_hash,
    verify_evidence_integrity,
)
from services.api.app.db.models import (
    Assessment,
    AssessmentAsset,
    AssessmentObservation,
    AssessmentStage,
    AssessmentStatus,
    CryptographicAsset,
    Observation,
    RiskAssessment,
    Scan,
    ScanStatus,
    Target,
)

PG_TEST_URL = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql+psycopg2://quantumflow:quantumflow_secret_dev@localhost:5434/quantumflow_db",
)


def _is_db_reachable(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 5432
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except Exception:
        return False


@pytest.fixture(scope="module", autouse=True)
def require_postgres() -> None:
    if not _is_db_reachable(PG_TEST_URL):
        pytest.skip("PostgreSQL 16 test database is not available on port 5434")


@pytest.fixture(scope="module")
def pg_engine() -> Generator[Engine, None, None]:
    """Module-level PostgreSQL engine."""
    engine = create_engine(PG_TEST_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def pg_session(pg_engine: Engine) -> Generator[Session, None, None]:
    """Provide an isolated, roll-back transaction session for each test."""
    connection = pg_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, expire_on_commit=False)

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


def create_test_target(session: Session, hostname: str | None = None) -> Target:
    """Helper to create a valid test target."""
    target = Target(
        hostname=hostname or f"target-{uuid.uuid4().hex[:8]}.example.com",
        display_name="Test Enterprise Target",
        status="ACTIVE",
        authorisation_status="VERIFIED",
        verification_token=f"tok_{uuid.uuid4().hex[:12]}",
    )
    session.add(target)
    session.flush()
    return target


def create_test_asset(session: Session, target_id: uuid.UUID | None = None) -> CryptographicAsset:
    """Helper to create a valid cryptographic asset."""
    asset = CryptographicAsset(
        target_id=target_id,
        asset_key=f"asset:rsa2048:{uuid.uuid4().hex[:10]}",
        display_name="Enterprise TLS Key",
        asset_type="ASYMMETRIC_KEY",
        algorithm_name="RSA",
        algorithm_family="RSA",
        business_criticality="HIGH",
        cryptographic_purpose="KEY_EXCHANGE",
        parameters={"key_size": 2048},
        lifecycle_status="ACTIVE",
        classification="OBSERVED",
        confidence_score=1.0,
        correlation_version="v1.0.0",
    )
    session.add(asset)
    session.flush()
    return asset


def test_valid_assessment_creation_and_state_transitions(pg_session: Session) -> None:
    """Verify standard assessment lifecycle from pending through running to completed."""
    target = create_test_target(pg_session)
    scope_hash = compute_canonical_scope_hash(str(target.id), ["tls", "source_code"])

    assessment = Assessment(
        title="Q4 Production PQC Audit",
        target_id=target.id,
        target_snapshot={"hostname": target.hostname, "port": 443},
        scope_hash=scope_hash,
        status=AssessmentStatus.PENDING.value,
        progress_stage=AssessmentStage.PENDING.value,
        progress_percent=0,
        discovery_sources=["tls", "source_code"],
    )
    pg_session.add(assessment)
    pg_session.flush()

    assert assessment.id is not None
    assert assessment.status == AssessmentStatus.PENDING.value
    assert assessment.is_active() is True
    assert assessment.is_terminal() is False

    # State transition: RUNNING (50%)
    assessment.status = AssessmentStatus.RUNNING.value
    assessment.progress_stage = AssessmentStage.CORRELATING_CBOM.value
    assessment.progress_percent = 50
    pg_session.flush()

    # State transition: COMPLETED (100%) with report snapshot
    report_data = {"qvi": 480, "findings_count": 3}
    report_hash = compute_canonical_evidence_sha256(report_data)

    assessment.status = AssessmentStatus.COMPLETED.value
    assessment.progress_stage = AssessmentStage.COMPLETED.value
    assessment.progress_percent = 100
    assessment.report_snapshot = report_data
    assessment.report_snapshot_hash = report_hash
    pg_session.flush()

    assert assessment.is_terminal() is True
    assert assessment.is_active() is False
    assert assessment.report_snapshot_hash == report_hash


def test_invalid_status_rejected_by_check_constraint(pg_session: Session) -> None:
    """Verify that statuses outside the allowed enum are rejected by PostgreSQL check constraint."""
    target = create_test_target(pg_session)
    scope_hash = compute_canonical_scope_hash(str(target.id), ["tls"])

    assessment = Assessment(
        title="Status Check Test",
        target_id=target.id,
        scope_hash=scope_hash,
        status="arbitrary_invalid_status",
        progress_stage=AssessmentStage.PENDING.value,
        progress_percent=0,
    )
    pg_session.add(assessment)

    with pytest.raises(IntegrityError) as exc_info, pg_session.begin_nested():
        pg_session.flush()

    assert "chk_assessment_status" in str(exc_info.value).lower()


def test_negative_progress_percent_rejected(pg_session: Session) -> None:
    """Verify that progress_percent < 0 is rejected by PostgreSQL check constraint."""
    target = create_test_target(pg_session)
    scope_hash = compute_canonical_scope_hash(str(target.id), ["tls"])

    assessment = Assessment(
        title="Negative Progress",
        target_id=target.id,
        scope_hash=scope_hash,
        status=AssessmentStatus.RUNNING.value,
        progress_stage=AssessmentStage.PENDING.value,
        progress_percent=-10,
    )
    pg_session.add(assessment)

    with pytest.raises(IntegrityError) as exc_info, pg_session.begin_nested():
        pg_session.flush()

    assert "chk_assessment_progress_range" in str(exc_info.value).lower()


def test_excessive_progress_percent_rejected(pg_session: Session) -> None:
    """Verify that progress_percent > 100 is rejected by PostgreSQL check constraint."""
    target = create_test_target(pg_session)
    scope_hash = compute_canonical_scope_hash(str(target.id), ["tls"])

    assessment = Assessment(
        title="Excessive Progress",
        target_id=target.id,
        scope_hash=scope_hash,
        status=AssessmentStatus.RUNNING.value,
        progress_stage=AssessmentStage.PENDING.value,
        progress_percent=120,
    )
    pg_session.add(assessment)

    with pytest.raises(IntegrityError) as exc_info, pg_session.begin_nested():
        pg_session.flush()

    assert "chk_assessment_progress_range" in str(exc_info.value).lower()


def test_cross_assessment_risk_association_rejected_by_composite_fk(pg_session: Session) -> None:
    """Verify that an assessment asset cannot reference a risk evaluation belonging to another assessment."""
    target = create_test_target(pg_session)
    asset = create_test_asset(pg_session, target.id)

    # Assessment A1
    a1 = Assessment(
        title="Assessment One",
        target_id=target.id,
        scope_hash=compute_canonical_scope_hash(str(target.id), ["tls"]),
        status=AssessmentStatus.RUNNING.value,
    )
    pg_session.add(a1)
    pg_session.flush()

    # Assessment A2
    a2 = Assessment(
        title="Assessment Two",
        target_id=target.id,
        scope_hash=compute_canonical_scope_hash(str(target.id), ["dependencies"]),
        status=AssessmentStatus.RUNNING.value,
    )
    pg_session.add(a2)
    pg_session.flush()

    # Associate asset with both assessments
    aa1 = AssessmentAsset(
        assessment_id=a1.id,
        asset_id=asset.id,
        classification="OBSERVED",
        asset_snapshot={"algorithm": "RSA-2048"},
    )
    aa2 = AssessmentAsset(
        assessment_id=a2.id,
        asset_id=asset.id,
        classification="OBSERVED",
        asset_snapshot={"algorithm": "RSA-2048"},
    )
    pg_session.add_all([aa1, aa2])
    pg_session.flush()

    # Create risk assessment R1 evaluated strictly for A1 and asset
    r1 = RiskAssessment(
        assessment_id=a1.id,
        asset_id=asset.id,
        assessment_number=1,
        status="provisional",
        score=720,
        risk_category="high",
        quantum_threat_type="shor_vulnerable",
        threat_summary="Vulnerable to Shor's algorithm",
        evidence_quality="high",
        assessment_input_hash=uuid.uuid4().hex * 2,
        engine_version="v1.0.0",
        methodology_version="QFT-RISK-v1.0",
    )
    pg_session.add(r1)
    pg_session.flush()

    # Valid link: associate R1 with AA1 (both belong to A1)
    aa1.risk_assessment_id = r1.id
    pg_session.flush()

    # Invalid cross-link: attempt to link R1 to AA2 (which belongs to A2) -> MUST FAIL
    with pytest.raises(IntegrityError) as exc_info, pg_session.begin_nested():
        aa2.risk_assessment_id = r1.id
        pg_session.flush()

    assert "fk_assessment_assets_risk_composite" in str(exc_info.value).lower()


def test_asset_deletion_restricted_when_in_assessment(pg_session: Session) -> None:
    """Verify that deleting a cryptographic asset referenced by an assessment is blocked (ON DELETE RESTRICT)."""
    target = create_test_target(pg_session)
    asset = create_test_asset(pg_session, target.id)

    assessment = Assessment(
        title="Evidence Preservation Assessment",
        target_id=target.id,
        scope_hash=compute_canonical_scope_hash(str(target.id), ["tls"]),
        status=AssessmentStatus.RUNNING.value,
    )
    pg_session.add(assessment)
    pg_session.flush()

    assoc = AssessmentAsset(
        assessment_id=assessment.id,
        asset_id=asset.id,
        classification="OBSERVED",
        asset_snapshot={"display_name": asset.display_name},
    )
    pg_session.add(assoc)
    pg_session.flush()

    # Attempt to delete the underlying asset -> PostgreSQL RESTRICT constraint rejects it
    with pytest.raises(IntegrityError) as exc_info, pg_session.begin_nested():
        pg_session.delete(asset)
        pg_session.flush()

    assert "fk_assessment_assets_asset_id_restrict" in str(exc_info.value).lower()


def test_observation_deletion_restricted_when_in_assessment(pg_session: Session) -> None:
    """Verify that deleting an observation linked to an assessment is blocked (ON DELETE RESTRICT)."""
    target = create_test_target(pg_session)

    scan = Scan(
        target_id=target.id,
        status=ScanStatus.COMPLETED.value,
        scan_type="tls_handshake",
        collector_version="v1.0.0",
    )
    pg_session.add(scan)
    pg_session.flush()

    obs = Observation(
        target_id=target.id,
        scan_id=scan.id,
        observation_type="tls_certificate",
        source="network_tls_probe",
        collector_version="v1.0.0",
        observed_value={"subject": "CN=test.internal"},
        evidence_sha256=uuid.uuid4().hex * 2,
    )
    pg_session.add(obs)
    pg_session.flush()

    assessment = Assessment(
        title="Observation Retention Assessment",
        target_id=target.id,
        scope_hash=compute_canonical_scope_hash(str(target.id), ["tls"]),
        status=AssessmentStatus.RUNNING.value,
    )
    pg_session.add(assessment)
    pg_session.flush()

    obs_assoc = AssessmentObservation(
        assessment_id=assessment.id,
        observation_id=obs.id,
    )
    pg_session.add(obs_assoc)
    pg_session.flush()

    # Attempt to delete the observation -> PostgreSQL RESTRICT constraint rejects it
    with pytest.raises(IntegrityError) as exc_info, pg_session.begin_nested():
        pg_session.delete(obs)
        pg_session.flush()

    assert "fk_assessment_observations_observation_id_restrict" in str(exc_info.value).lower()


def test_target_deletion_leaves_assessment_intact(pg_session: Session) -> None:
    """Verify that target deletion sets target_id=NULL on assessment while preserving target_snapshot."""
    target = create_test_target(pg_session)
    target_id = target.id
    target_snapshot = {
        "hostname": target.hostname,
        "port": 443,
        "environment": "production",
    }

    assessment = Assessment(
        title="Target Resilience Test",
        target_id=target_id,
        target_snapshot=target_snapshot,
        scope_hash=compute_canonical_scope_hash(str(target_id), ["tls"]),
        status=AssessmentStatus.COMPLETED.value,
        progress_percent=100,
    )
    pg_session.add(assessment)
    pg_session.flush()

    assessment_id = assessment.id

    # Delete the target
    pg_session.delete(target)
    pg_session.flush()

    # Query the assessment: target_id must be NULL, snapshot must be intact
    retrieved = pg_session.get(Assessment, assessment_id)
    assert retrieved is not None
    assert retrieved.target_id is None
    assert retrieved.target_snapshot["hostname"] == target_snapshot["hostname"]
    assert retrieved.target_snapshot["port"] == 443


def test_duplicate_active_assessment_rejected_by_partial_unique_index(pg_session: Session) -> None:
    """Verify that concurrent active assessments with identical target and scope_hash are rejected."""
    target = create_test_target(pg_session)
    scope_hash = compute_canonical_scope_hash(str(target.id), ["tls", "source_code"])

    # Active Assessment 1 (running)
    a1 = Assessment(
        title="Primary Active Run",
        target_id=target.id,
        scope_hash=scope_hash,
        status=AssessmentStatus.RUNNING.value,
    )
    pg_session.add(a1)
    pg_session.flush()

    # Active Assessment 2 (pending with identical scope) -> MUST BE REJECTED
    a2 = Assessment(
        title="Duplicate Active Run",
        target_id=target.id,
        scope_hash=scope_hash,
        status=AssessmentStatus.PENDING.value,
    )
    pg_session.add(a2)

    with pytest.raises(IntegrityError) as exc_info, pg_session.begin_nested():
        pg_session.flush()

    assert "uq_assessments_active_target_scope" in str(exc_info.value).lower()


def test_parallel_active_assessments_with_different_scopes_allowed(pg_session: Session) -> None:
    """Verify that active assessments for the same target with different scopes can run concurrently."""
    target = create_test_target(pg_session)
    scope_hash_tls = compute_canonical_scope_hash(str(target.id), ["tls"], port=443)
    scope_hash_code = compute_canonical_scope_hash(
        str(target.id), ["source_code"], repo_locator="org/repo"
    )

    a1 = Assessment(
        title="TLS Discovery Run",
        target_id=target.id,
        scope_hash=scope_hash_tls,
        status=AssessmentStatus.RUNNING.value,
    )
    a2 = Assessment(
        title="Static Source Code Run",
        target_id=target.id,
        scope_hash=scope_hash_code,
        status=AssessmentStatus.RUNNING.value,
    )
    pg_session.add_all([a1, a2])
    pg_session.flush()

    assert a1.id is not None
    assert a2.id is not None


def test_terminal_snapshot_modification_rejected_by_trigger(pg_session: Session) -> None:
    """Verify that terminal report snapshots and hashes are protected against modification by trigger."""
    target = create_test_target(pg_session)
    scope_hash = compute_canonical_scope_hash(str(target.id), ["tls"])

    assessment = Assessment(
        title="Immutability Trigger Test",
        target_id=target.id,
        scope_hash=scope_hash,
        status=AssessmentStatus.RUNNING.value,
        progress_percent=90,
    )
    pg_session.add(assessment)
    pg_session.flush()

    # Transition to terminal status with initial snapshot write
    initial_snapshot = {"qvi_score": 520, "critical_findings": 2}
    initial_hash = compute_canonical_evidence_sha256(initial_snapshot)

    assessment.status = AssessmentStatus.COMPLETED.value
    assessment.progress_percent = 100
    assessment.report_snapshot = initial_snapshot
    assessment.report_snapshot_hash = initial_hash
    pg_session.flush()

    # Attempt to tamper with report_snapshot -> PostgreSQL Trigger raises exception
    with pytest.raises(DBAPIError) as exc_info, pg_session.begin_nested():
        assessment.report_snapshot = {"qvi_score": 100, "critical_findings": 0}
        pg_session.flush()

    assert "immutable" in str(exc_info.value).lower()

    # Attempt to tamper with report_snapshot_hash -> PostgreSQL Trigger raises exception
    with pytest.raises(DBAPIError) as exc_info2, pg_session.begin_nested():
        assessment.report_snapshot_hash = "0" * 64
        pg_session.flush()

    assert "immutable" in str(exc_info2.value).lower()


def test_updating_non_snapshot_fields_on_terminal_assessment_permitted(pg_session: Session) -> None:
    """Verify that updating governance/operational fields on a terminal assessment is permitted."""
    target = create_test_target(pg_session)
    scope_hash = compute_canonical_scope_hash(str(target.id), ["tls"])

    snapshot = {"qvi_score": 600}
    snapshot_hash = compute_canonical_evidence_sha256(snapshot)

    assessment = Assessment(
        title="Operational Update Test",
        target_id=target.id,
        scope_hash=scope_hash,
        status=AssessmentStatus.COMPLETED.value,
        progress_percent=100,
        report_snapshot=snapshot,
        report_snapshot_hash=snapshot_hash,
        retry_count=0,
    )
    pg_session.add(assessment)
    pg_session.flush()

    # Updating retry_count, error_summary, or engine_version is permitted
    assessment.retry_count = 1
    assessment.error_summary = "Non-fatal warnings logged during finalization"
    pg_session.flush()

    retrieved = pg_session.get(Assessment, assessment.id)
    assert retrieved is not None
    assert retrieved.retry_count == 1
    assert retrieved.error_summary == "Non-fatal warnings logged during finalization"
    assert retrieved.report_snapshot_hash == snapshot_hash


def test_canonical_scope_hash_properties() -> None:
    """Verify deterministic RFC 8785 canonical scope hashing."""
    tid = str(uuid.uuid4())

    hash1 = compute_canonical_scope_hash(tid, ["tls", "source_code"], port=443)
    # Order of discovery sources should be normalized / sorted
    hash2 = compute_canonical_scope_hash(tid, ["source_code", "tls"], port=443)
    assert hash1 == hash2

    # Different port produces different hash
    hash3 = compute_canonical_scope_hash(tid, ["tls", "source_code"], port=8443)
    assert hash1 != hash3

    # Verification helper
    payload = {
        "target_id": tid,
        "discovery_sources": ["source_code", "tls"],
        "port": 443,
        "repo_locator": None,
        "repo_ref": None,
        "config_type": None,
        "extra_params": {},
    }
    assert verify_evidence_integrity(payload, hash1) is True
