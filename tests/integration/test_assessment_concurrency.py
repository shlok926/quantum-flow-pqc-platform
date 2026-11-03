"""Quantum Flow Technologies — Assessment Concurrency, Race Condition & Recovery Tests.

Validates multi-worker concurrency, database-level row locking, cooperative
cancellation races, duplicate submission serialization, and zombie recovery
against a live PostgreSQL 16 database.
"""

import asyncio
import os
import socket
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import patch
from urllib.parse import urlparse

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from services.api.app.db.models.assessment import Assessment, AssessmentStatus
from services.api.app.db.models.discovery_job import DiscoveryJob, JobStatus, JobType
from services.api.app.db.models.target import AuthorisationStatus, Target, TargetStatus
from services.api.app.db.session import get_db
from services.api.app.main import app
from services.api.app.services.assessment_service import AssessmentService
from services.api.app.services.job_service import JobService
from services.worker.app.worker import AutonomousWorker

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
async def concurrency_target(
    pg_session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[Target, None]:
    """Seed target domain for concurrency testing."""
    target_id = uuid.uuid4()
    hostname = f"concurrency-{uuid.uuid4().hex[:8]}.quantumflow.internal"

    async with pg_session_maker() as session:
        target = Target(
            id=target_id,
            hostname=hostname,
            display_name="Concurrency Target",
            status=TargetStatus.VERIFIED.value,
            authorisation_status=AuthorisationStatus.CONFIRMED.value,
            verification_token=f"qf-verify={uuid.uuid4()}",
        )
        session.add(target)
        await session.commit()

    yield target

    async with pg_session_maker() as session:
        # Cascade cleanup
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
class TestAssessmentConcurrency:
    """Validate concurrency controls, race conditions, and worker leasing."""

    async def test_concurrent_duplicate_assessment_creation(
        self,
        pg_client: AsyncClient,
        concurrency_target: Target,
    ) -> None:
        """Two simultaneous creation requests with identical scope serialize correctly."""
        payload = {
            "title": "Concurrent Audit",
            "target_id": str(concurrency_target.id),
            "discovery_sources": ["network_tls"],
            "extra_params": {"batch": "concurrency_race_1"},
        }

        # Issue two concurrent creation requests simultaneously
        resp1, resp2 = await asyncio.gather(
            pg_client.post("/api/v1/assessments", json=payload),
            pg_client.post("/api/v1/assessments", json=payload),
        )

        status_codes = sorted([resp1.status_code, resp2.status_code])
        # Exactly one succeeds (201), the other is rejected with 409 Conflict
        assert status_codes == [201, 409]

    async def test_multi_worker_skip_locked_claiming(
        self,
        pg_session_maker: async_sessionmaker[AsyncSession],
        concurrency_target: Target,
    ) -> None:
        """Multiple concurrent workers claiming from queue claim distinct jobs without collisions."""
        async with pg_session_maker() as db:
            assessment = Assessment(
                title="Multi-Worker Claiming Test",
                target_id=concurrency_target.id,
                target_snapshot={"hostname": concurrency_target.hostname},
                scope_hash=uuid.uuid4().hex,
                status=AssessmentStatus.QUEUED.value,
                discovery_sources=["network_tls", "config_import"],
            )
            db.add(assessment)
            await db.flush()

            job1 = DiscoveryJob(
                job_type=JobType.TLS_DISCOVERY.value,
                target_id=concurrency_target.id,
                assessment_id=assessment.id,
                input_params={},
                status=JobStatus.QUEUED.value,
            )
            job2 = DiscoveryJob(
                job_type=JobType.CONFIG_IMPORT.value,
                target_id=concurrency_target.id,
                assessment_id=assessment.id,
                input_params={},
                status=JobStatus.QUEUED.value,
            )
            db.add_all([job1, job2])
            await db.commit()

        # Launch two concurrent workers claiming simultaneously
        async def claim_with_worker(wid: str) -> uuid.UUID | None:
            async with pg_session_maker() as session:
                claimed = await JobService.claim_next_job(session, worker_id=wid, lease_seconds=60)
                return claimed.id if claimed else None

        claimed_ids = await asyncio.gather(
            claim_with_worker("worker-alpha"),
            claim_with_worker("worker-beta"),
        )

        assert len(claimed_ids) == 2
        assert claimed_ids[0] is not None
        assert claimed_ids[1] is not None
        # Must claim two distinct jobs
        assert claimed_ids[0] != claimed_ids[1]

    async def test_active_collector_vs_cancellation_race(
        self,
        pg_session_maker: async_sessionmaker[AsyncSession],
        pg_client: AsyncClient,
        concurrency_target: Target,
    ) -> None:
        """Simulate worker collector completing while cancellation commits; late writes discarded."""
        create_resp = await pg_client.post(
            "/api/v1/assessments",
            json={
                "title": "Cancellation Race Test",
                "target_id": str(concurrency_target.id),
                "discovery_sources": ["network_tls"],
                "extra_params": {"race": "cancellation"},
            },
        )
        assert create_resp.status_code == 201
        assessment_id = uuid.UUID(create_resp.json()["id"])

        # Fetch child job
        child_jobs = (await pg_client.get(f"/api/v1/assessments/{assessment_id}/jobs")).json()
        job_id = uuid.UUID(child_jobs["jobs"][0]["id"])

        # Cancel assessment BEFORE or DURING collector persistence
        async with pg_session_maker() as db:
            await AssessmentService.cancel_assessment(
                db, assessment_id, reason="Concurrent cancel race"
            )

        # Worker attempts to execute discovery job for the cancelled assessment
        async with pg_session_maker() as db:
            executed_job = await AssessmentService.execute_discovery_job(
                db=db,
                job_id=job_id,
                worker_id="racing-worker",
            )

        # Job must be cancelled and late evidence must not overwrite terminal cancelled status
        assert executed_job.status == JobStatus.CANCELLED.value

        async with pg_session_maker() as db:
            refreshed_assessment = await AssessmentService.get_assessment(db, assessment_id)
            assert refreshed_assessment is not None
            assert refreshed_assessment.status == AssessmentStatus.CANCELLED.value
            assert refreshed_assessment.report_snapshot_hash is not None

    async def test_zombie_lease_recovery_by_worker(
        self,
        pg_session_maker: async_sessionmaker[AsyncSession],
        concurrency_target: Target,
    ) -> None:
        """Expired worker leases are autonomously recovered and re-queued."""
        now = datetime.now(UTC)
        past = now - timedelta(seconds=120)

        async with pg_session_maker() as db:
            assessment = Assessment(
                title="Zombie Recovery Test",
                target_id=concurrency_target.id,
                target_snapshot={"hostname": concurrency_target.hostname},
                scope_hash=uuid.uuid4().hex,
                status=AssessmentStatus.RUNNING.value,
                discovery_sources=["config_import"],
            )
            db.add(assessment)
            await db.flush()

            zombie_job = DiscoveryJob(
                job_type=JobType.CONFIG_IMPORT.value,
                target_id=concurrency_target.id,
                assessment_id=assessment.id,
                input_params={},
                status=JobStatus.RUNNING.value,
                worker_id="dead-worker-pid-9999",
                started_at=past,
                lease_expires_at=past + timedelta(seconds=60),
                retry_count=0,
                max_retries=3,
            )
            db.add(zombie_job)
            await db.commit()
            zombie_job_id = zombie_job.id

        # Autonomous worker runs check_zombies
        worker = AutonomousWorker(
            worker_id="healthy-worker",
            session_maker=pg_session_maker,
            zombie_check_interval_seconds=0.0,
        )
        recovered = await worker.check_zombies()
        assert recovered >= 1

        # Verify job is back in queued status with incremented retry_count
        async with pg_session_maker() as db:
            recovered_job = await JobService.get_job(db, zombie_job_id)
            assert recovered_job is not None
            assert recovered_job.status == JobStatus.QUEUED.value
            assert recovered_job.worker_id is None
            assert recovered_job.retry_count == 1
            assert "Recovered from dead worker" in (recovered_job.error_message or "")

    async def test_simultaneous_enqueue_discovery_jobs_uniqueness(
        self,
        pg_session_maker: async_sessionmaker[AsyncSession],
        concurrency_target: Target,
    ) -> None:
        """Concurrent calls to enqueue_discovery_jobs on the same assessment produce zero duplicate jobs."""
        async with pg_session_maker() as db:
            assessment = Assessment(
                title="Concurrent Enqueue Uniqueness Test",
                target_id=concurrency_target.id,
                target_snapshot={"hostname": concurrency_target.hostname},
                scope_hash=uuid.uuid4().hex,
                status=AssessmentStatus.QUEUED.value,
                discovery_sources=["network_tls", "static_source", "config_import"],
            )
            db.add(assessment)
            await db.commit()
            assessment_id = assessment.id

        # Three coroutines concurrently invoking enqueue_discovery_jobs with independent sessions
        async def call_enqueue() -> list[DiscoveryJob]:
            async with pg_session_maker() as session:
                return await AssessmentService.enqueue_discovery_jobs(session, assessment_id)

        await asyncio.gather(
            call_enqueue(),
            call_enqueue(),
            call_enqueue(),
        )

        async with pg_session_maker() as db:
            jobs_stmt = select(DiscoveryJob).where(DiscoveryJob.assessment_id == assessment_id)
            all_jobs = list((await db.scalars(jobs_stmt)).all())

        # Exactly 3 jobs (one per requested source: tls, source, config), ZERO duplicate job_types
        assert len(all_jobs) == 3
        job_types = [j.job_type for j in all_jobs]
        assert len(set(job_types)) == 3
        assert set(job_types) == {
            JobType.TLS_DISCOVERY.value,
            JobType.SOURCE_ANALYSIS.value,
            JobType.CONFIG_IMPORT.value,
        }

    async def test_concurrent_retry_serialization(
        self,
        pg_client: AsyncClient,
        pg_session_maker: async_sessionmaker[AsyncSession],
        concurrency_target: Target,
    ) -> None:
        """Two concurrent retry API requests serialize cleanly: exactly one succeeds, one returns 400."""
        # 1. Create failed assessment with child jobs
        async with pg_session_maker() as db:
            assessment = Assessment(
                title="Concurrent Retry Test",
                target_id=concurrency_target.id,
                target_snapshot={"hostname": concurrency_target.hostname},
                scope_hash=uuid.uuid4().hex,
                status=AssessmentStatus.FAILED.value,
                progress_stage="FAILED",
                progress_percent=100,
                discovery_sources=["network_tls"],
                error_summary="Collector timed out",
                retry_count=0,
                max_retries=3,
            )
            db.add(assessment)
            await db.flush()

            job = DiscoveryJob(
                job_type=JobType.TLS_DISCOVERY.value,
                target_id=concurrency_target.id,
                assessment_id=assessment.id,
                input_params={},
                status=JobStatus.FAILED.value,
                error_message="TLS connection failed",
            )
            db.add(job)
            await db.commit()
            assessment_id = assessment.id

        # 2. Issue two concurrent retry requests
        resp1, resp2 = await asyncio.gather(
            pg_client.post(f"/api/v1/assessments/{assessment_id}/retry"),
            pg_client.post(f"/api/v1/assessments/{assessment_id}/retry"),
        )

        statuses = sorted([resp1.status_code, resp2.status_code])
        # Exactly one succeeds (200 OK), the second sees queued status and returns 400 Bad Request
        assert statuses == [200, 400]

        async with pg_session_maker() as db:
            refreshed = await AssessmentService.get_assessment(db, assessment_id)
            assert refreshed is not None
            assert refreshed.status == AssessmentStatus.QUEUED.value
            assert refreshed.retry_count == 1

            # Verify no duplicate child job was created
            jobs_stmt = select(DiscoveryJob).where(DiscoveryJob.assessment_id == assessment_id)
            jobs = list((await db.scalars(jobs_stmt)).all())
            assert len(jobs) == 1
            assert jobs[0].status == JobStatus.QUEUED.value

    async def test_heartbeat_renewal_during_collector_execution(
        self,
        pg_session_maker: async_sessionmaker[AsyncSession],
        concurrency_target: Target,
    ) -> None:
        """Verify that heartbeat task actively renews lease in background during execution."""
        async with pg_session_maker() as db:
            assessment = Assessment(
                title="Heartbeat Test",
                target_id=concurrency_target.id,
                target_snapshot={"hostname": concurrency_target.hostname},
                scope_hash=uuid.uuid4().hex,
                status=AssessmentStatus.RUNNING.value,
                discovery_sources=["config_import"],
            )
            db.add(assessment)
            await db.flush()

            job = DiscoveryJob(
                job_type=JobType.CONFIG_IMPORT.value,
                target_id=concurrency_target.id,
                assessment_id=assessment.id,
                input_params={},
                status=JobStatus.QUEUED.value,
            )
            db.add(job)
            await db.commit()
            job_id = job.id

        worker = AutonomousWorker(
            worker_id="heartbeat-worker-test",
            session_maker=pg_session_maker,
            lease_seconds=3,
            heartbeat_interval_seconds=0.3,
        )

        def _slow_parse(content: str) -> list[Any]:
            time.sleep(1.0)
            return []

        with patch(
            "packages.scanner.config.importer.ConfigImporter.parse_nginx",
            side_effect=_slow_parse,
        ):
            # Claim job
            async with pg_session_maker() as db:
                claimed = await JobService.claim_next_job(
                    db, worker_id=worker.worker_id, lease_seconds=3
                )
                assert claimed is not None

            # Process with active heartbeat
            await worker.process_job(job_id)

            async with pg_session_maker() as db:
                finished_job = await JobService.get_job(db, job_id)
                assert finished_job is not None
                assert finished_job.status == JobStatus.COMPLETED.value

    async def test_worker_graceful_shutdown_stops_claiming(
        self,
        pg_session_maker: async_sessionmaker[AsyncSession],
        concurrency_target: Target,
    ) -> None:
        """A worker with shutdown_event set halts claiming and leaves queue untouched."""
        async with pg_session_maker() as db:
            assessment = Assessment(
                title="Shutdown Test",
                target_id=concurrency_target.id,
                target_snapshot={"hostname": concurrency_target.hostname},
                scope_hash=uuid.uuid4().hex,
                status=AssessmentStatus.QUEUED.value,
                discovery_sources=["config_import"],
            )
            db.add(assessment)
            await db.flush()

            job = DiscoveryJob(
                job_type=JobType.CONFIG_IMPORT.value,
                target_id=concurrency_target.id,
                assessment_id=assessment.id,
                input_params={},
                status=JobStatus.QUEUED.value,
            )
            db.add(job)
            await db.commit()
            job_id = job.id

        shutdown_event = asyncio.Event()
        shutdown_event.set()  # Signal immediate shutdown

        worker = AutonomousWorker(
            worker_id="shutdown-worker",
            session_maker=pg_session_maker,
            shutdown_event=shutdown_event,
        )

        await worker.run()

        # Job must remain queued, not claimed
        async with pg_session_maker() as db:
            unchanged_job = await JobService.get_job(db, job_id)
            assert unchanged_job is not None
            assert unchanged_job.status == JobStatus.QUEUED.value
            assert unchanged_job.worker_id is None

    async def test_cancellation_during_each_collector_stage_aborts_writes(
        self,
        pg_session_maker: async_sessionmaker[AsyncSession],
        concurrency_target: Target,
    ) -> None:
        """Cancellation during any collector stage aborts observation/asset writes and preserves immutable snapshot."""
        # Test across all 4 collector sources
        for src in ["network_tls", "static_source", "dependency_manifest", "config_import"]:
            async with pg_session_maker() as db:
                assessment = Assessment(
                    title=f"Cancellation Stage Test - {src}",
                    target_id=concurrency_target.id,
                    target_snapshot={"hostname": concurrency_target.hostname},
                    scope_hash=uuid.uuid4().hex,
                    status=AssessmentStatus.RUNNING.value,
                    discovery_sources=[src],
                )
                db.add(assessment)
                await db.commit()
                assessment_id = assessment.id

            # Pre-cancel assessment
            async with pg_session_maker() as db:
                cancelled = await AssessmentService.cancel_assessment(
                    db, assessment_id, reason="Stage abort test"
                )
                original_snapshot_hash = cancelled.report_snapshot_hash

            # Execute collector for cancelled assessment
            async with pg_session_maker() as db:
                if src == "network_tls":
                    outcome, obs, assets = await AssessmentService._execute_tls_collector(
                        db=db,
                        assessment=cancelled,
                        target=concurrency_target,
                        engine_version="v1.0.0",
                    )
                elif src == "static_source":
                    outcome, obs, assets = await AssessmentService._execute_source_collector(
                        db=db,
                        assessment=cancelled,
                        target=concurrency_target,
                        engine_version="v1.0.0",
                        payload={},
                    )
                elif src == "dependency_manifest":
                    outcome, obs, assets = await AssessmentService._execute_dep_collector(
                        db=db,
                        assessment=cancelled,
                        target=concurrency_target,
                        engine_version="v1.0.0",
                        payload={},
                    )
                else:
                    outcome, obs, assets = await AssessmentService._execute_config_collector(
                        db=db,
                        assessment=cancelled,
                        target=concurrency_target,
                        engine_version="v1.0.0",
                        payload={"config_content": "ssl_protocols TLSv1.3;"},
                    )

            # Assert outcome is cancelled and ZERO observations or assets persisted
            assert outcome.get("status") == "cancelled"
            assert len(obs) == 0
            assert len(assets) == 0

            # Verify terminal snapshot hash remains completely untouched
            async with pg_session_maker() as db:
                refreshed = await AssessmentService.get_assessment(db, assessment_id)
                assert refreshed is not None
                assert refreshed.status == AssessmentStatus.CANCELLED.value
                assert refreshed.report_snapshot_hash == original_snapshot_hash
