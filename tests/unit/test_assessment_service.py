"""Quantum Flow Technologies — Assessment Orchestrator Service Unit Tests.

Validates end-to-end multi-collector pipeline orchestration, lifecycle transitions,
cooperative cancellation, retry provenance, CBOM correlation, and immutable report snapshots.
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.scanner.tls.collector import (
    BoundedTLSCollector,
    CertificateEvidence,
    TLSCollectionResult,
    TLSEndpointEvidence,
)
from services.api.app.db.models.assessment import (
    AssessmentStage,
    AssessmentStatus,
)
from services.api.app.db.models.assessment_asset import AssessmentAsset
from services.api.app.db.models.assessment_observation import AssessmentObservation
from services.api.app.db.models.risk_assessment import RiskAssessment
from services.api.app.db.models.target import Target, TargetStatus
from services.api.app.services.assessment_service import (
    AssessmentService,
    DuplicateActiveAssessmentError,
    InvalidLifecycleTransitionError,
    MaxRetriesExceededError,
    compute_asset_counts,
    compute_risk_summary,
)


@pytest.mark.asyncio
async def test_create_assessment_lifecycle(test_db_session: AsyncSession) -> None:
    """Verify that an assessment is initialized in PENDING state with scope hash and target snapshot."""
    target = Target(
        hostname="scope-test.internal",
        display_name="Scope Test",
        status=TargetStatus.VERIFIED.value,
        authorisation_status="confirmed",
        verification_token=f"tok_{uuid.uuid4().hex[:12]}",
    )
    test_db_session.add(target)
    await test_db_session.commit()
    await test_db_session.refresh(target)

    assessment = await AssessmentService.create_assessment(
        db=test_db_session,
        title="Quarterly Cryptographic Assessment",
        target_id=target.id,
        discovery_sources=["network_tls", "static_source"],
    )

    assert assessment.id is not None
    assert assessment.status == AssessmentStatus.PENDING.value
    assert assessment.progress_stage == AssessmentStage.PENDING.value
    assert assessment.progress_percent == 0
    assert assessment.discovery_sources == ["network_tls", "static_source"]
    assert assessment.target_snapshot["hostname"] == "scope-test.internal"
    assert assessment.scope_hash is not None
    assert len(assessment.scope_hash) == 64


@pytest.mark.asyncio
async def test_duplicate_active_assessment_rejection(test_db_session: AsyncSession) -> None:
    """Verify that submitting a duplicate assessment with identical target and scope hash is rejected."""
    target = Target(
        hostname="dupe-scope.internal",
        status=TargetStatus.VERIFIED.value,
        authorisation_status="confirmed",
        verification_token=f"tok_{uuid.uuid4().hex[:12]}",
    )
    test_db_session.add(target)
    await test_db_session.commit()

    await AssessmentService.create_assessment(
        db=test_db_session,
        title="Initial Run",
        target_id=target.id,
        discovery_sources=["network_tls"],
    )

    # Second active submission with matching target and scope must fail
    with pytest.raises(DuplicateActiveAssessmentError):
        await AssessmentService.create_assessment(
            db=test_db_session,
            title="Duplicate Run",
            target_id=target.id,
            discovery_sources=["network_tls"],
        )


@pytest.mark.asyncio
async def test_cancel_assessment_preserves_evidence(test_db_session: AsyncSession) -> None:
    """Verify cooperative cancellation sets CANCELLED and generates immutable report without deleting evidence."""
    target = Target(
        hostname="cancel-test.internal",
        status=TargetStatus.VERIFIED.value,
        authorisation_status="confirmed",
        verification_token=f"tok_{uuid.uuid4().hex[:12]}",
    )
    test_db_session.add(target)
    await test_db_session.commit()

    assessment = await AssessmentService.create_assessment(
        db=test_db_session,
        title="Cancel Assessment Run",
        target_id=target.id,
        discovery_sources=["network_tls"],
    )

    cancelled = await AssessmentService.cancel_assessment(
        db=test_db_session,
        assessment_id=assessment.id,
        reason="Operator halted execution",
    )

    assert cancelled.status == AssessmentStatus.CANCELLED.value
    assert cancelled.progress_stage == AssessmentStage.CANCELLED.value
    assert cancelled.error_summary == "Operator halted execution"
    assert cancelled.completed_at is not None
    assert cancelled.report_snapshot is not None
    assert cancelled.report_snapshot_hash is not None

    # Cancelling again should raise InvalidLifecycleTransitionError
    with pytest.raises(InvalidLifecycleTransitionError):
        await AssessmentService.cancel_assessment(test_db_session, assessment.id)


@pytest.mark.asyncio
async def test_retry_assessment_provenance(test_db_session: AsyncSession) -> None:
    """Verify that retrying an assessment tracks previous attempts and increments retry_count."""
    assessment = await AssessmentService.create_assessment(
        db=test_db_session,
        title="Retry Run",
        discovery_sources=["network_tls"],
    )

    # Manually mark as failed
    assessment.status = AssessmentStatus.FAILED.value
    assessment.error_summary = "Simulated network timeout"
    await test_db_session.commit()

    retried = await AssessmentService.retry_assessment(test_db_session, assessment.id)

    assert retried.status == AssessmentStatus.QUEUED.value
    assert retried.retry_count == 1
    attempts = retried.collector_results.get("execution_attempts", [])
    assert len(attempts) == 1
    assert attempts[0]["attempt_number"] == 1
    assert attempts[0]["error_summary"] == "Simulated network timeout"

    # Exceeding retries
    retried.retry_count = 3
    retried.status = AssessmentStatus.FAILED.value
    await test_db_session.commit()

    with pytest.raises(MaxRetriesExceededError):
        await AssessmentService.retry_assessment(test_db_session, assessment.id)


@pytest.mark.asyncio
async def test_execute_assessment_full_pipeline(test_db_session: AsyncSession) -> None:
    """Verify end-to-end multi-collector execution, CBOM correlation, QVI risk evaluation, and immutable report."""
    target = Target(
        hostname="pipeline-test.internal",
        display_name="Pipeline Target",
        status=TargetStatus.VERIFIED.value,
        authorisation_status="confirmed",
        verification_token=f"tok_{uuid.uuid4().hex[:12]}",
    )
    test_db_session.add(target)
    await test_db_session.commit()

    assessment = await AssessmentService.create_assessment(
        db=test_db_session,
        title="End-to-End Audit",
        target_id=target.id,
        discovery_sources=["network_tls", "config_import"],
    )

    mock_cert = MagicMock(spec=CertificateEvidence)
    mock_cert.subject_dn = "CN=pipeline-test.internal"
    mock_cert.issuer_dn = "CN=Enterprise Internal CA"
    mock_cert.serial_number_hex = "ABCD1234"
    mock_cert.valid_from = datetime.now()
    mock_cert.valid_to = datetime.now()
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

    mock_result = TLSCollectionResult(
        success=True,
        target_hostname="pipeline-test.internal",
        pinned_ip="127.0.0.1",
        endpoint_evidence=mock_endpoint,
        certificate_evidence=mock_cert,
    )

    with patch.object(BoundedTLSCollector, "inspect_target", return_value=mock_result):
        executed = await AssessmentService.execute_assessment(
            db=test_db_session,
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
    assert executed.error_summary is None

    # Check collector outcomes
    results = executed.collector_results
    assert results["network_tls"]["status"] == "success"
    assert results["config_import"]["status"] == "success"

    # Verify observations and assets were created and linked
    stmt_obs = select(AssessmentObservation).where(
        AssessmentObservation.assessment_id == assessment.id
    )
    obs_links = (await test_db_session.scalars(stmt_obs)).all()
    assert len(obs_links) >= 2

    stmt_assets = select(AssessmentAsset).where(AssessmentAsset.assessment_id == assessment.id)
    asset_links = (await test_db_session.scalars(stmt_assets)).all()
    assert len(asset_links) >= 2

    for al in asset_links:
        assert al.asset_snapshot is not None
        assert al.risk_assessment_id is not None  # Composite FK link verified!

    # Verify RiskAssessments created
    stmt_risk = select(RiskAssessment).where(RiskAssessment.assessment_id == assessment.id)
    risks = (await test_db_session.scalars(stmt_risk)).all()
    assert len(risks) >= 2

    # Verify immutable snapshot was frozen with canonical hash
    assert executed.report_snapshot is not None
    assert executed.report_snapshot_hash is not None
    assert len(executed.report_snapshot_hash) == 64
    assert executed.risk_summary["overall_score"] > 0


@pytest.mark.asyncio
async def test_execute_assessment_partial_completion(test_db_session: AsyncSession) -> None:
    """Verify that when one collector fails, status becomes PARTIALLY_COMPLETED and errors are recorded."""
    target = Target(
        hostname="partial-test.internal",
        status=TargetStatus.VERIFIED.value,
        authorisation_status="confirmed",
        verification_token=f"tok_{uuid.uuid4().hex[:12]}",
    )
    test_db_session.add(target)
    await test_db_session.commit()

    assessment = await AssessmentService.create_assessment(
        db=test_db_session,
        title="Partial Run",
        target_id=target.id,
        discovery_sources=["network_tls", "config_import"],
    )

    failed_result = TLSCollectionResult(
        success=False,
        target_hostname="partial-test.internal",
        pinned_ip="127.0.0.1",
        endpoint_evidence=None,
        certificate_evidence=None,
        error_message="Connection timed out",
    )

    with patch.object(BoundedTLSCollector, "inspect_target", return_value=failed_result):
        executed = await AssessmentService.execute_assessment(
            db=test_db_session,
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
    assert executed.report_snapshot is not None


def test_summary_calculation_helpers() -> None:
    """Verify standalone computation of coverage, asset counts, and risk aggregations."""
    counts = compute_asset_counts(
        [
            MagicMock(asset_type="protocol", business_criticality="high"),
            MagicMock(asset_type="certificate", business_criticality="critical"),
            MagicMock(asset_type="certificate", business_criticality="critical"),
        ]
    )
    assert counts["total"] == 3
    assert counts["by_type"]["protocol"] == 1
    assert counts["by_type"]["certificate"] == 2
    assert counts["by_criticality"]["critical"] == 2

    risk_evals = [
        MagicMock(score=815, quantum_threat_type="shor_vulnerable"),
        MagicMock(score=250, quantum_threat_type="grover_margin"),
    ]
    summary = compute_risk_summary(risk_evals)
    assert summary["overall_score"] == 815
    assert summary["overall_category"] == "critical"
    assert summary["shor_vulnerable_count"] == 1
    assert summary["grover_margin_count"] == 1
    assert summary["critical_risk_count"] == 1


@pytest.mark.asyncio
async def test_durable_job_enqueuing_and_claiming(test_db_session: AsyncSession) -> None:
    """Verify that enqueue_discovery_jobs creates durable DiscoveryJobs linked via assessment_id."""
    from services.api.app.db.models.discovery_job import JobStatus, JobType
    from services.api.app.services.job_service import JobService

    target = Target(
        hostname="durable-test.internal",
        status=TargetStatus.VERIFIED.value,
        authorisation_status="confirmed",
        verification_token=f"tok_{uuid.uuid4().hex[:12]}",
    )
    test_db_session.add(target)
    await test_db_session.commit()

    assessment = await AssessmentService.create_assessment(
        db=test_db_session,
        title="Durable Worker Test",
        target_id=target.id,
        discovery_sources=["network_tls", "config_import"],
    )

    jobs = await AssessmentService.enqueue_discovery_jobs(
        db=test_db_session,
        assessment_id=assessment.id,
        input_payload={"config_content": "ssl_protocols TLSv1.3;", "config_type": "nginx"},
    )
    assert len(jobs) == 2
    types = {j.job_type for j in jobs}
    assert JobType.TLS_DISCOVERY.value in types
    assert JobType.CONFIG_IMPORT.value in types

    for j in jobs:
        assert j.assessment_id == assessment.id
        assert j.status == JobStatus.QUEUED.value

    # Test claiming via JobService with lease
    claimed = await JobService.claim_next_job(
        db=test_db_session,
        worker_id="test-worker-1",
        supported_types=[JobType.CONFIG_IMPORT.value],
        lease_seconds=60,
    )
    assert claimed is not None
    assert claimed.worker_id == "test-worker-1"
    assert claimed.status == JobStatus.RUNNING.value
    assert claimed.lease_expires_at is not None


@pytest.mark.asyncio
async def test_cancellation_halts_and_cancels_child_jobs(test_db_session: AsyncSession) -> None:
    """Verify that cancel_assessment cancels all child discovery jobs and stops execution."""
    from services.api.app.db.models.discovery_job import DiscoveryJob, JobStatus

    target = Target(
        hostname="cancel-jobs.internal",
        status=TargetStatus.VERIFIED.value,
        authorisation_status="confirmed",
        verification_token=f"tok_{uuid.uuid4().hex[:12]}",
    )
    test_db_session.add(target)
    await test_db_session.commit()

    assessment = await AssessmentService.create_assessment(
        db=test_db_session,
        title="Cancellation With Jobs",
        target_id=target.id,
        discovery_sources=["network_tls", "static_source"],
    )

    jobs = await AssessmentService.enqueue_discovery_jobs(
        db=test_db_session,
        assessment_id=assessment.id,
    )
    assert len(jobs) == 2

    # Cancel assessment
    cancelled = await AssessmentService.cancel_assessment(
        db=test_db_session,
        assessment_id=assessment.id,
        reason="Operator requested abort",
    )
    assert cancelled.status == AssessmentStatus.CANCELLED.value

    # Verify all child jobs are now CANCELLED
    for j in jobs:
        refreshed_job = await test_db_session.get(DiscoveryJob, j.id)
        assert refreshed_job is not None
        assert refreshed_job.status == JobStatus.CANCELLED.value
        assert "Operator requested abort" in (refreshed_job.error_message or "")


@pytest.mark.asyncio
async def test_first_seen_in_assessment_provenance(test_db_session: AsyncSession) -> None:
    """Verify that first_seen_in_assessment correctly attributes True to the earliest assessment and False to subsequent ones."""
    from services.api.app.db.models.cryptographic_asset import CryptographicAsset

    # Create a shared asset
    asset = CryptographicAsset(
        asset_key="cert:test-sha256-fingerprint",
        asset_type="certificate",
        display_name="Test Shared Certificate",
        algorithm_family="RSA",
        algorithm_name="RSA-2048",
        cryptographic_purpose="signature",
        parameters={"key_size": 2048},
        business_criticality="high",
    )
    test_db_session.add(asset)
    await test_db_session.commit()

    # Create Assessment 1
    a1 = await AssessmentService.create_assessment(
        db=test_db_session,
        title="First Assessment",
        discovery_sources=["network_tls"],
    )

    # Associate with Assessment 1
    aa1, is_new1 = await AssessmentService._associate_asset_to_assessment(
        db=test_db_session,
        assessment=a1,
        asset=asset,
    )
    await test_db_session.commit()

    assert is_new1 is True
    assert aa1.first_seen_in_assessment is True

    # Complete Assessment 1
    a1.status = AssessmentStatus.COMPLETED.value
    await test_db_session.commit()

    # Create Assessment 2 at a later time
    a2 = await AssessmentService.create_assessment(
        db=test_db_session,
        title="Second Assessment",
        discovery_sources=["network_tls"],
        extra_params={"batch": 2},
    )

    # Associate same asset with Assessment 2
    aa2, is_new2 = await AssessmentService._associate_asset_to_assessment(
        db=test_db_session,
        assessment=a2,
        asset=asset,
    )
    await test_db_session.commit()

    assert is_new2 is True
    # Assessment 2 MUST NOT claim first_seen_in_assessment
    assert aa2.first_seen_in_assessment is False
