"""Quantum Flow Technologies — Assessment REST API PostgreSQL 16 Integration Workflow Tests.

Validates the complete end-to-end HTTP API lifecycle:
- Atomic assessment creation & durable job enqueueing
- Background worker execution & live polling
- Cryptographic report verification (is_hash_verified)
- Cooperative cancellation & partial evidence snapshot
- Bounded retries with execution attempt provenance
Against a live PostgreSQL 16 database.
"""

import os
import socket
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from packages.scanner.tls.collector import (
    BoundedTLSCollector,
    CertificateEvidence,
    TLSCollectionResult,
    TLSEndpointEvidence,
)
from services.api.app.db.models.target import AuthorisationStatus, Target, TargetStatus
from services.api.app.db.session import get_db
from services.api.app.main import app
from services.worker.app.worker import AutonomousWorker

PG_ASYNC_URL = os.getenv(
    "DATABASE_URL_ASYNC",
    "postgresql+asyncpg://quantumflow:quantumflow_secret_dev@localhost:5434/quantumflow_db",
)


def _create_mock_tls_result(hostname: str, success: bool = True) -> TLSCollectionResult:
    """Helper to generate deterministic TLS inspection evidence."""
    if not success:
        return TLSCollectionResult(
            success=False,
            target_hostname=hostname,
            pinned_ip="127.0.0.1",
            endpoint_evidence=None,
            certificate_evidence=None,
            error_message="Simulated connection timeout during handshake",
        )

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
    """Create async engine connected to PostgreSQL 16 database."""
    engine = create_async_engine(
        PG_ASYNC_URL,
        pool_pre_ping=True,
        echo=False,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def pg_session_maker(pg_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create session maker bound to PostgreSQL 16."""
    return async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def pg_client(
    pg_session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncClient, None]:
    """Provide AsyncClient wired to PostgreSQL 16."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with pg_session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=cast(Any, app))
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def verified_target(
    pg_session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[Target, None]:
    """Seed an authorized and verified Target in PostgreSQL 16."""
    target_id = uuid.uuid4()
    hostname = f"api-test-{uuid.uuid4().hex[:8]}.quantumflow.internal"

    async with pg_session_maker() as session:
        target = Target(
            id=target_id,
            hostname=hostname,
            display_name="API Integration Target",
            status=TargetStatus.VERIFIED.value,
            authorisation_status=AuthorisationStatus.CONFIRMED.value,
            authorised_by="security-auditor@quantumflow.internal",
            verification_token=f"qf-verify={uuid.uuid4()}",
        )
        session.add(target)
        await session.commit()

    yield target

    async with pg_session_maker() as session:
        # Step 1 RESTRICT foreign key protection requires orderly cascade cleanup
        await session.execute(
            text(
                "DELETE FROM assessment_observations WHERE assessment_id IN (SELECT id FROM assessments WHERE target_id = :id)"
            ),
            {"id": target_id},
        )
        await session.execute(
            text(
                "DELETE FROM assessment_assets WHERE assessment_id IN (SELECT id FROM assessments WHERE target_id = :id)"
            ),
            {"id": target_id},
        )
        await session.execute(
            text(
                "DELETE FROM risk_assessments WHERE assessment_id IN (SELECT id FROM assessments WHERE target_id = :id)"
            ),
            {"id": target_id},
        )
        await session.execute(
            text("DELETE FROM discovery_jobs WHERE target_id = :id"),
            {"id": target_id},
        )
        await session.execute(
            text("DELETE FROM assessments WHERE target_id = :id"),
            {"id": target_id},
        )
        await session.execute(
            text("DELETE FROM observations WHERE target_id = :id"),
            {"id": target_id},
        )
        await session.execute(
            text("DELETE FROM targets WHERE id = :id"),
            {"id": target_id},
        )
        await session.commit()


@pytest.mark.asyncio
class TestAssessmentAPIWorkflow:
    """Integration tests for Assessment REST API backed by PostgreSQL 16."""

    async def test_end_to_end_assessment_api_lifecycle(
        self,
        pg_client: AsyncClient,
        pg_session_maker: async_sessionmaker[AsyncSession],
        verified_target: Target,
    ) -> None:
        """Test complete workflow: create -> inspect jobs -> worker run -> report verify."""
        mock_tls = _create_mock_tls_result(verified_target.hostname, success=True)

        with patch.object(BoundedTLSCollector, "inspect_target", return_value=mock_tls):
            # 1. Create Assessment via API
            create_resp = await pg_client.post(
                "/api/v1/assessments",
                json={
                    "title": "API Workflow PQC Assessment",
                    "target_id": str(verified_target.id),
                    "discovery_sources": ["network_tls"],
                    "extra_params": {"env": "staging", "suite": "api_wf"},
                },
            )
            assert create_resp.status_code == 201
            assessment_data = create_resp.json()
            assessment_id = assessment_data["id"]
            assert create_resp.headers["Location"] == f"/api/v1/assessments/{assessment_id}"
            assert assessment_data["status"] == "queued"

            # 2. Inspect Child Jobs
            jobs_resp = await pg_client.get(f"/api/v1/assessments/{assessment_id}/jobs")
            assert jobs_resp.status_code == 200
            jobs_data = jobs_resp.json()
            assert jobs_data["total_jobs"] == 1
            assert jobs_data["jobs"][0]["status"] == "queued"
            job_id = jobs_data["jobs"][0]["id"]

            # 3. Report returns 409 Conflict while active
            report_early = await pg_client.get(f"/api/v1/assessments/{assessment_id}/report")
            assert report_early.status_code == 409

            # 4. Autonomous Worker processes the job with active heartbeat
            worker = AutonomousWorker(
                worker_id="test-wf-worker-1",
                session_maker=pg_session_maker,
            )
            await worker.process_job(uuid.UUID(job_id))

            # 5. Poll Assessment via API: should be COMPLETED
            detail_resp = await pg_client.get(f"/api/v1/assessments/{assessment_id}")
            assert detail_resp.status_code == 200
            detail_data = detail_resp.json()
            assert detail_data["status"] == "completed"
            assert detail_data["progress_percent"] == 100
            assert detail_data["report_snapshot_hash"] is not None

            # 6. Fetch Report: status 200, is_hash_verified == True
            report_resp = await pg_client.get(f"/api/v1/assessments/{assessment_id}/report")
            assert report_resp.status_code == 200
            report_data = report_resp.json()
            assert report_data["status"] == "completed"
            assert report_data["is_hash_verified"] is True
            assert report_data["is_immutable"] is True
            assert report_data["report_snapshot"]["title"] == "API Workflow PQC Assessment"

            # 7. List Assessments via API
            list_resp = await pg_client.get(
                f"/api/v1/assessments?target_id={verified_target.id}&status=completed"
            )
            assert list_resp.status_code == 200
            list_data = list_resp.json()
            assert list_data["total"] >= 1
            assert any(item["id"] == assessment_id for item in list_data["items"])

    async def test_cancellation_workflow_via_api(
        self,
        pg_client: AsyncClient,
        pg_session_maker: async_sessionmaker[AsyncSession],
        verified_target: Target,
    ) -> None:
        """Test that cancelling an assessment halts execution and freezes partial snapshot."""
        # 1. Create Assessment
        create_resp = await pg_client.post(
            "/api/v1/assessments",
            json={
                "title": "Cancellation Test",
                "target_id": str(verified_target.id),
                "discovery_sources": ["network_tls"],
                "extra_params": {"suite": "cancel_test"},
            },
        )
        assert create_resp.status_code == 201
        assessment_id = create_resp.json()["id"]

        # 2. Cancel via API
        cancel_resp = await pg_client.post(
            f"/api/v1/assessments/{assessment_id}/cancel",
            json={"reason": "Emergency operator shutdown"},
        )
        assert cancel_resp.status_code == 200
        cancel_data = cancel_resp.json()
        assert cancel_data["status"] == "cancelled"
        assert cancel_data["error_summary"] == "Emergency operator shutdown"

        # 3. Report is available for cancelled assessment
        report_resp = await pg_client.get(f"/api/v1/assessments/{assessment_id}/report")
        assert report_resp.status_code == 200
        assert report_resp.json()["status"] == "cancelled"
        assert report_resp.json()["is_hash_verified"] is True

        # 4. Cancelling again returns 400
        cancel_again = await pg_client.post(
            f"/api/v1/assessments/{assessment_id}/cancel",
            json={"reason": "Repeated stop"},
        )
        assert cancel_again.status_code == 400

    async def test_retry_workflow_via_api(
        self,
        pg_client: AsyncClient,
        pg_session_maker: async_sessionmaker[AsyncSession],
        verified_target: Target,
    ) -> None:
        """Test retrying a failed assessment resets to queued and records provenance."""
        # 1. Create assessment with mock failure
        mock_fail = _create_mock_tls_result(verified_target.hostname, success=False)

        with patch.object(BoundedTLSCollector, "inspect_target", return_value=mock_fail):
            create_resp = await pg_client.post(
                "/api/v1/assessments",
                json={
                    "title": "Retry Workflow Test",
                    "target_id": str(verified_target.id),
                    "discovery_sources": ["network_tls"],
                    "extra_params": {"suite": "retry_wf"},
                },
            )
            assert create_resp.status_code == 201
            assessment_id = create_resp.json()["id"]

            # Fetch child job and process via worker to fail the job
            child_jobs = (await pg_client.get(f"/api/v1/assessments/{assessment_id}/jobs")).json()
            fail_job_id = child_jobs["jobs"][0]["id"]

            worker = AutonomousWorker(session_maker=pg_session_maker)
            await worker.process_job(uuid.UUID(fail_job_id))

            # Verify assessment failed
            detail_resp = await pg_client.get(f"/api/v1/assessments/{assessment_id}")
            assert detail_resp.json()["status"] == "failed"

        # 2. Retry Assessment via API
        retry_resp = await pg_client.post(f"/api/v1/assessments/{assessment_id}/retry")
        assert retry_resp.status_code == 200
        retried_data = retry_resp.json()
        assert retried_data["status"] == "queued"
        assert retried_data["progress_percent"] == 0

        # Verify execution attempt was logged
        attempts = retried_data["collector_results"].get("execution_attempts", [])
        assert len(attempts) == 1
        assert attempts[0]["status_before_retry"] == "failed"

        # 3. Child job was reset to queued
        jobs_resp = await pg_client.get(f"/api/v1/assessments/{assessment_id}/jobs")
        assert jobs_resp.json()["jobs"][0]["status"] == "queued"
