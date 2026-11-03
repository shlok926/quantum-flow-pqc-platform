"""Quantum Flow Technologies — Assessment Orchestrator PostgreSQL 16 Integration Tests.

Validates end-to-end durable execution, cooperative cancellation, worker leasing/recovery,
CBOM correlation, 0-1000 QVI risk persistence, canonical snapshot verification,
and PostgreSQL trigger immutability against a live PostgreSQL 16 database.
"""

import os
import socket
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from packages.scanner.safety.canonical import compute_canonical_evidence_sha256
from packages.scanner.tls.collector import (
    BoundedTLSCollector,
    CertificateEvidence,
    TLSCollectionResult,
    TLSEndpointEvidence,
)
from services.api.app.db.models.assessment import (
    AssessmentStatus,
)
from services.api.app.db.models.assessment_asset import AssessmentAsset
from services.api.app.db.models.discovery_job import DiscoveryJob, JobStatus, JobType
from services.api.app.db.models.risk_assessment import RiskAssessment
from services.api.app.db.models.target import Target, TargetStatus
from services.api.app.services.assessment_service import (
    AssessmentService,
    DuplicateActiveAssessmentError,
)
from services.api.app.services.job_service import JobService

PG_ASYNC_URL = os.getenv(
    "DATABASE_URL_ASYNC",
    "postgresql+asyncpg://quantumflow:quantumflow_secret_dev@localhost:5434/quantumflow_db",
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
    if not _is_db_reachable(PG_ASYNC_URL):
        pytest.skip("PostgreSQL async test database is not available on port 5434")


@pytest_asyncio.fixture
async def pg_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create async engine connected to PostgreSQL 16 test database."""
    engine = create_async_engine(
        PG_ASYNC_URL,
        pool_pre_ping=True,
        echo=False,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def pg_db(pg_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated AsyncSession connected to PostgreSQL 16."""
    session_factory = async_sessionmaker(
        bind=pg_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


def _create_mock_tls_result(hostname: str) -> TLSCollectionResult:
    """Helper to generate deterministic TLS inspection evidence."""
    mock_cert = MagicMock(spec=CertificateEvidence)
    mock_cert.subject_dn = f"CN={hostname}"
    mock_cert.issuer_dn = "CN=QuantumFlow Enterprise CA"
    mock_cert.serial_number_hex = "11223344AABBCCDD"
    mock_cert.valid_from = datetime.now(UTC)
    mock_cert.valid_to = datetime.now(UTC) + timedelta(days=365)
    mock_cert.sha256_fingerprint = (
        "0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF"
    )
    mock_cert.public_key_algorithm = "RSA"
    mock_cert.public_key_size_bits = 2048
    mock_cert.signature_algorithm = "sha256WithRSAEncryption"

    mock_endpoint = MagicMock(spec=TLSEndpointEvidence)
    mock_endpoint.negotiated_protocol = "TLSv1.3"
    mock_endpoint.negotiated_cipher_name = "TLS_AES_256_GCM_SHA384"
    mock_endpoint.negotiated_cipher_bits = 256

    return TLSCollectionResult(
        success=True,
        target_hostname=hostname,
        pinned_ip="127.0.0.1",
        endpoint_evidence=mock_endpoint,
        certificate_evidence=mock_cert,
    )


# ------------------------------------------------------------------------------
# 1. Successful Multi-Source Assessment
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pg_multi_source_assessment_success(pg_db: AsyncSession) -> None:
    """Verify end-to-end multi-source assessment on PostgreSQL 16."""
    target = Target(
        hostname=f"pg-multi-{uuid.uuid4().hex[:8]}.internal",
        display_name="PG Multi Target",
        status=TargetStatus.VERIFIED.value,
        authorisation_status="confirmed",
        verification_token=f"tok_{uuid.uuid4().hex[:12]}",
    )
    pg_db.add(target)
    await pg_db.commit()

    assessment = await AssessmentService.create_assessment(
        db=pg_db,
        title="PostgreSQL Multi-Source Audit",
        target_id=target.id,
        discovery_sources=["network_tls", "config_import"],
    )

    mock_tls = _create_mock_tls_result(target.hostname)
    with patch.object(BoundedTLSCollector, "inspect_target", return_value=mock_tls):
        executed = await AssessmentService.execute_assessment(
            db=pg_db,
            assessment_id=assessment.id,
            input_payload={
                "config_type": "nginx",
                "config_content": "ssl_protocols TLSv1.2 TLSv1.3;\nssl_ciphers HIGH:!aNULL:!MD5;",
            },
        )

    assert executed.status == AssessmentStatus.COMPLETED.value
    assert executed.progress_stage == "COMPLETED"
    assert executed.progress_percent == 100
    assert executed.completed_at is not None
    assert executed.collector_results["network_tls"]["status"] == "success"
    assert executed.collector_results["config_import"]["status"] == "success"
    assert executed.report_snapshot is not None
    assert executed.report_snapshot_hash is not None


# ------------------------------------------------------------------------------
# 2. Partial Collector Failure
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pg_partial_collector_failure(pg_db: AsyncSession) -> None:
    """Verify partial completion when one collector fails while another succeeds."""
    target = Target(
        hostname=f"pg-partial-{uuid.uuid4().hex[:8]}.internal",
        status=TargetStatus.VERIFIED.value,
        authorisation_status="confirmed",
        verification_token=f"tok_{uuid.uuid4().hex[:12]}",
    )
    pg_db.add(target)
    await pg_db.commit()

    assessment = await AssessmentService.create_assessment(
        db=pg_db,
        title="PostgreSQL Partial Audit",
        target_id=target.id,
        discovery_sources=["network_tls", "config_import"],
    )

    failed_tls = TLSCollectionResult(
        success=False,
        target_hostname=target.hostname,
        pinned_ip="127.0.0.1",
        endpoint_evidence=None,
        certificate_evidence=None,
        error_message="Simulated connection reset",
    )

    with patch.object(BoundedTLSCollector, "inspect_target", return_value=failed_tls):
        executed = await AssessmentService.execute_assessment(
            db=pg_db,
            assessment_id=assessment.id,
            input_payload={
                "config_type": "nginx",
                "config_content": "ssl_protocols TLSv1.3;",
            },
        )

    assert executed.status == AssessmentStatus.PARTIALLY_COMPLETED.value
    assert executed.progress_stage == "PARTIALLY_COMPLETED"
    assert "Failed collectors: network_tls" in (executed.error_summary or "")
    assert executed.collector_results["network_tls"]["status"] == "failed"
    assert executed.collector_results["config_import"]["status"] == "success"


# ------------------------------------------------------------------------------
# 3. Complete Collector Failure
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pg_complete_collector_failure(pg_db: AsyncSession) -> None:
    """Verify assessment failure when all requested collectors fail."""
    target = Target(
        hostname=f"pg-fail-{uuid.uuid4().hex[:8]}.internal",
        status=TargetStatus.VERIFIED.value,
        authorisation_status="confirmed",
        verification_token=f"tok_{uuid.uuid4().hex[:12]}",
    )
    pg_db.add(target)
    await pg_db.commit()

    assessment = await AssessmentService.create_assessment(
        db=pg_db,
        title="PostgreSQL All Failed Audit",
        target_id=target.id,
        discovery_sources=["network_tls"],
    )

    failed_tls = TLSCollectionResult(
        success=False,
        target_hostname=target.hostname,
        pinned_ip="127.0.0.1",
        endpoint_evidence=None,
        certificate_evidence=None,
        error_message="Host unreachable",
    )

    with patch.object(BoundedTLSCollector, "inspect_target", return_value=failed_tls):
        executed = await AssessmentService.execute_assessment(
            db=pg_db,
            assessment_id=assessment.id,
        )

    assert executed.status == AssessmentStatus.FAILED.value
    assert executed.progress_stage == "FAILED"
    assert "All requested discovery collectors failed" in (executed.error_summary or "")


# ------------------------------------------------------------------------------
# 4. Durable Job Creation and Worker Execution
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pg_durable_job_creation_and_worker_execution(pg_db: AsyncSession) -> None:
    """Verify durable DiscoveryJob creation and worker claiming with SELECT FOR UPDATE SKIP LOCKED."""
    target = Target(
        hostname=f"pg-worker-{uuid.uuid4().hex[:8]}.internal",
        status=TargetStatus.VERIFIED.value,
        authorisation_status="confirmed",
        verification_token=f"tok_{uuid.uuid4().hex[:12]}",
    )
    pg_db.add(target)
    await pg_db.commit()

    assessment = await AssessmentService.create_assessment(
        db=pg_db,
        title="Durable Worker Pipeline",
        target_id=target.id,
        discovery_sources=["config_import"],
    )

    # Enqueue durable jobs
    jobs = await AssessmentService.enqueue_discovery_jobs(
        db=pg_db,
        assessment_id=assessment.id,
        input_payload={"config_content": "ssl_protocols TLSv1.3;", "config_type": "nginx"},
    )
    assert len(jobs) == 1
    assert jobs[0].status == JobStatus.QUEUED.value

    # Worker claims job atomically using SELECT FOR UPDATE SKIP LOCKED
    claimed = await JobService.claim_next_job(
        db=pg_db,
        worker_id="pg-worker-node-1",
        supported_types=[JobType.CONFIG_IMPORT.value],
        lease_seconds=60,
    )
    assert claimed is not None
    assert claimed.id == jobs[0].id
    assert claimed.worker_id == "pg-worker-node-1"
    assert claimed.status == JobStatus.RUNNING.value

    # Execute claimed job
    executed_job = await AssessmentService.execute_discovery_job(
        db=pg_db,
        job_id=claimed.id,
        worker_id="pg-worker-node-1",
    )
    assert executed_job.status == JobStatus.COMPLETED.value

    # Assessment should have automatically advanced to COMPLETED
    refreshed_assessment = await AssessmentService.get_assessment(pg_db, assessment.id)
    assert refreshed_assessment is not None
    assert refreshed_assessment.status == AssessmentStatus.COMPLETED.value


# ------------------------------------------------------------------------------
# 5. Worker Crash and Zombie Recovery
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pg_worker_crash_and_zombie_recovery(pg_db: AsyncSession) -> None:
    """Verify zombie job recovery when worker crashes past lease expiration."""
    target = Target(
        hostname=f"pg-zombie-{uuid.uuid4().hex[:8]}.internal",
        status=TargetStatus.VERIFIED.value,
        authorisation_status="confirmed",
        verification_token=f"tok_{uuid.uuid4().hex[:12]}",
    )
    pg_db.add(target)
    await pg_db.commit()

    assessment = await AssessmentService.create_assessment(
        db=pg_db,
        title="Zombie Recovery Audit",
        target_id=target.id,
        discovery_sources=["config_import"],
    )

    jobs = await AssessmentService.enqueue_discovery_jobs(
        db=pg_db,
        assessment_id=assessment.id,
        input_payload={"config_content": "ssl_protocols TLSv1.3;", "config_type": "nginx"},
    )
    job = jobs[0]

    # Simulate worker claiming and crashing (expired lease)
    job.status = JobStatus.RUNNING.value
    job.worker_id = "crashed-worker-node"
    job.lease_expires_at = datetime.now(UTC) - timedelta(seconds=15)
    await pg_db.commit()

    # Run zombie recovery
    recovered_count = await JobService.recover_zombies(pg_db)
    assert recovered_count >= 1

    # Job is re-queued with incremented retry_count
    await pg_db.refresh(job)
    assert job.status == JobStatus.QUEUED.value
    assert job.worker_id is None
    assert job.retry_count == 1

    # New worker claims and completes
    claimed = await JobService.claim_next_job(
        db=pg_db,
        worker_id="healthy-worker-node",
        supported_types=[JobType.CONFIG_IMPORT.value],
    )
    assert claimed is not None
    assert claimed.id == job.id

    await AssessmentService.execute_discovery_job(
        pg_db, claimed.id, worker_id="healthy-worker-node"
    )
    refreshed = await AssessmentService.get_assessment(pg_db, assessment.id)
    assert refreshed is not None
    assert refreshed.status == AssessmentStatus.COMPLETED.value


# ------------------------------------------------------------------------------
# 6. Duplicate Execution Prevention
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pg_duplicate_execution_prevention(pg_db: AsyncSession) -> None:
    """Verify that concurrent duplicate assessments with matching target and scope are rejected."""
    target = Target(
        hostname=f"pg-dupe-{uuid.uuid4().hex[:8]}.internal",
        status=TargetStatus.VERIFIED.value,
        authorisation_status="confirmed",
        verification_token=f"tok_{uuid.uuid4().hex[:12]}",
    )
    pg_db.add(target)
    await pg_db.commit()

    # First active assessment
    await AssessmentService.create_assessment(
        db=pg_db,
        title="First Active Assessment",
        target_id=target.id,
        discovery_sources=["network_tls"],
    )

    # Second active assessment with exact same scope must raise DuplicateActiveAssessmentError
    with pytest.raises(DuplicateActiveAssessmentError):
        await AssessmentService.create_assessment(
            db=pg_db,
            title="Second Active Assessment",
            target_id=target.id,
            discovery_sources=["network_tls"],
        )


# ------------------------------------------------------------------------------
# 7. Cancellation During Execution
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pg_cancellation_during_execution(pg_db: AsyncSession) -> None:
    """Verify cooperative cancellation sets CANCELLED and halts child jobs."""
    target = Target(
        hostname=f"pg-cancel-{uuid.uuid4().hex[:8]}.internal",
        status=TargetStatus.VERIFIED.value,
        authorisation_status="confirmed",
        verification_token=f"tok_{uuid.uuid4().hex[:12]}",
    )
    pg_db.add(target)
    await pg_db.commit()

    assessment = await AssessmentService.create_assessment(
        db=pg_db,
        title="Cancellation Test",
        target_id=target.id,
        discovery_sources=["network_tls", "config_import"],
    )

    jobs = await AssessmentService.enqueue_discovery_jobs(pg_db, assessment.id)
    assert len(jobs) == 2

    cancelled = await AssessmentService.cancel_assessment(
        db=pg_db,
        assessment_id=assessment.id,
        reason="Manual cancellation requested",
    )
    assert cancelled.status == AssessmentStatus.CANCELLED.value
    assert cancelled.completed_at is not None

    # Child jobs are marked CANCELLED
    for j in jobs:
        refreshed_job = await pg_db.get(DiscoveryJob, j.id)
        assert refreshed_job is not None
        assert refreshed_job.status == JobStatus.CANCELLED.value

    # Subsequent execution attempts halt immediately without overwriting CANCELLED status
    res = await AssessmentService.execute_assessment(pg_db, assessment.id)
    assert res.status == AssessmentStatus.CANCELLED.value


# ------------------------------------------------------------------------------
# 8. Retry After Partial Completion
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pg_retry_after_partial_completion(pg_db: AsyncSession) -> None:
    """Verify retry on partially completed assessment resets state and records attempt history."""
    target = Target(
        hostname=f"pg-retry-{uuid.uuid4().hex[:8]}.internal",
        status=TargetStatus.VERIFIED.value,
        authorisation_status="confirmed",
        verification_token=f"tok_{uuid.uuid4().hex[:12]}",
    )
    pg_db.add(target)
    await pg_db.commit()

    assessment = await AssessmentService.create_assessment(
        db=pg_db,
        title="Retry Audit Run",
        target_id=target.id,
        discovery_sources=["config_import"],
    )

    # Set as PARTIALLY_COMPLETED
    assessment.status = AssessmentStatus.PARTIALLY_COMPLETED.value
    assessment.error_summary = "Partial collector timeout"
    await pg_db.commit()

    retried = await AssessmentService.retry_assessment(pg_db, assessment.id)
    assert retried.status == AssessmentStatus.QUEUED.value
    assert retried.retry_count == 1
    assert retried.report_snapshot is None

    attempts = retried.collector_results.get("execution_attempts", [])
    assert len(attempts) == 1
    assert attempts[0]["attempt_number"] == 1
    assert attempts[0]["status_before_retry"] == AssessmentStatus.PARTIALLY_COMPLETED.value


# ------------------------------------------------------------------------------
# 9. Evidence Idempotency
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pg_evidence_idempotency(pg_db: AsyncSession) -> None:
    """Verify that repeated discovery of identical cryptographic assets reuses existing records."""
    target = Target(
        hostname=f"pg-idem-{uuid.uuid4().hex[:8]}.internal",
        status=TargetStatus.VERIFIED.value,
        authorisation_status="confirmed",
        verification_token=f"tok_{uuid.uuid4().hex[:12]}",
    )
    pg_db.add(target)
    await pg_db.commit()

    mock_tls = _create_mock_tls_result(target.hostname)

    # Assessment Run 1
    a1 = await AssessmentService.create_assessment(
        db=pg_db,
        title="Run 1",
        target_id=target.id,
        discovery_sources=["network_tls"],
        extra_params={"run": 1},
    )
    with patch.object(BoundedTLSCollector, "inspect_target", return_value=mock_tls):
        await AssessmentService.execute_assessment(pg_db, a1.id)

    # Assessment Run 2 (distinct scope parameter)
    a2 = await AssessmentService.create_assessment(
        db=pg_db,
        title="Run 2",
        target_id=target.id,
        discovery_sources=["network_tls"],
        extra_params={"run": 2},
    )
    with patch.object(BoundedTLSCollector, "inspect_target", return_value=mock_tls):
        await AssessmentService.execute_assessment(pg_db, a2.id)

    # Both assessments should reference the exact same underlying CryptographicAsset rows
    stmt1 = select(AssessmentAsset.asset_id).where(AssessmentAsset.assessment_id == a1.id)
    stmt2 = select(AssessmentAsset.asset_id).where(AssessmentAsset.assessment_id == a2.id)
    assets1 = set((await pg_db.scalars(stmt1)).all())
    assets2 = set((await pg_db.scalars(stmt2)).all())

    assert len(assets1) >= 1
    assert assets1 == assets2  # Deduplicated across runs!


# ------------------------------------------------------------------------------
# 10. CBOM and Risk Persistence (Composite Foreign Key)
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pg_cbom_and_risk_persistence(pg_db: AsyncSession) -> None:
    """Verify composite foreign key (id, assessment_id, asset_id) linking AssessmentAsset and RiskAssessment."""
    target = Target(
        hostname=f"pg-risk-{uuid.uuid4().hex[:8]}.internal",
        status=TargetStatus.VERIFIED.value,
        authorisation_status="confirmed",
        verification_token=f"tok_{uuid.uuid4().hex[:12]}",
    )
    pg_db.add(target)
    await pg_db.commit()

    assessment = await AssessmentService.create_assessment(
        db=pg_db,
        title="Risk Persistence Audit",
        target_id=target.id,
        discovery_sources=["config_import"],
    )

    executed = await AssessmentService.execute_assessment(
        db=pg_db,
        assessment_id=assessment.id,
        input_payload={"config_content": "ssl_protocols TLSv1.3;", "config_type": "nginx"},
    )
    assert executed.status == AssessmentStatus.COMPLETED.value

    # Verify composite foreign key on assessment_assets
    stmt = select(AssessmentAsset).where(AssessmentAsset.assessment_id == assessment.id)
    aa_rows = (await pg_db.scalars(stmt)).all()
    assert len(aa_rows) >= 1

    for aa in aa_rows:
        assert aa.risk_assessment_id is not None
        # Verify matching RiskAssessment row in database
        risk_row = await pg_db.get(RiskAssessment, aa.risk_assessment_id)
        assert risk_row is not None
        assert risk_row.assessment_id == aa.assessment_id
        assert risk_row.asset_id == aa.asset_id


# ------------------------------------------------------------------------------
# 11. Snapshot / Canonical SHA-256 Hash Verification
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pg_snapshot_hash_verification(pg_db: AsyncSession) -> None:
    """Verify canonical RFC 8785 JSON serialization and SHA-256 digest match."""
    target = Target(
        hostname=f"pg-hash-{uuid.uuid4().hex[:8]}.internal",
        status=TargetStatus.VERIFIED.value,
        authorisation_status="confirmed",
        verification_token=f"tok_{uuid.uuid4().hex[:12]}",
    )
    pg_db.add(target)
    await pg_db.commit()

    assessment = await AssessmentService.create_assessment(
        db=pg_db,
        title="Hash Verification Run",
        target_id=target.id,
        discovery_sources=["config_import"],
    )

    executed = await AssessmentService.execute_assessment(
        db=pg_db,
        assessment_id=assessment.id,
        input_payload={"config_content": "ssl_protocols TLSv1.3;", "config_type": "nginx"},
    )

    snapshot = executed.report_snapshot
    stored_hash = executed.report_snapshot_hash

    assert snapshot is not None
    assert stored_hash is not None

    # Recompute independently using RFC 8785 canonical digest
    recomputed_hash = compute_canonical_evidence_sha256(snapshot)
    assert recomputed_hash == stored_hash


# ------------------------------------------------------------------------------
# 12. Terminal Snapshot Immutability (PL/pgSQL Trigger Enforcement)
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pg_terminal_snapshot_immutability(pg_db: AsyncSession) -> None:
    """Verify PostgreSQL trigger trg_protect_terminal_assessment_snapshot rejects modifications."""
    target = Target(
        hostname=f"pg-immut-{uuid.uuid4().hex[:8]}.internal",
        status=TargetStatus.VERIFIED.value,
        authorisation_status="confirmed",
        verification_token=f"tok_{uuid.uuid4().hex[:12]}",
    )
    pg_db.add(target)
    await pg_db.commit()

    assessment = await AssessmentService.create_assessment(
        db=pg_db,
        title="Immutability Verification",
        target_id=target.id,
        discovery_sources=["config_import"],
    )

    executed = await AssessmentService.execute_assessment(
        db=pg_db,
        assessment_id=assessment.id,
        input_payload={"config_content": "ssl_protocols TLSv1.3;", "config_type": "nginx"},
    )
    assert executed.status == AssessmentStatus.COMPLETED.value
    assert executed.report_snapshot_hash is not None

    # Attempting to modify report_snapshot via SQL UPDATE must raise PL/pgSQL trigger exception
    with pytest.raises(DBAPIError) as exc_info:
        await pg_db.execute(
            text(
                "UPDATE assessments SET report_snapshot = '{\"tampered\": true}'::jsonb WHERE id = :aid"
            ),
            {"aid": executed.id},
        )
        await pg_db.commit()

    assert "Terminal assessment report snapshot and canonical hash are immutable" in str(
        exc_info.value
    )
