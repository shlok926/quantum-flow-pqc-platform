"""Quantum Flow Technologies — Discovery Job API and State Engine Integration Tests.

Verifies:
1. Job creation through API endpoint.
2. Duplicate active job prevention for identical targets/params.
3. Job status retrieval and cancellation.
4. Concurrency lease timeout and zombie job recovery in JobService.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.db.models.discovery_job import DiscoveryJob, JobStatus, JobType
from services.api.app.services.job_service import JobService


@pytest.mark.asyncio
async def test_create_and_get_discovery_job(async_client: AsyncClient) -> None:
    """Verify discovery job submission and retrieval."""
    res = await async_client.post(
        "/api/v1/jobs",
        json={
            "job_type": "source_analysis",
            "input_params": {"repo_url": "test-repo"},
            "timeout_seconds": 120,
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "queued"
    assert data["job_type"] == "source_analysis"
    job_id = data["id"]

    # Retrieve job by ID
    get_res = await async_client.get(f"/api/v1/jobs/{job_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == job_id


@pytest.mark.asyncio
async def test_duplicate_pending_job_rejected(async_client: AsyncClient) -> None:
    """Verify duplicate active job for the exact same target is rejected."""
    target_id = str(uuid.uuid4())

    res1 = await async_client.post(
        "/api/v1/jobs",
        json={
            "job_type": "tls_discovery",
            "target_id": target_id,
        },
    )
    assert res1.status_code == 201

    # Second job with identical target_id and job_type must be rejected with 409
    res2 = await async_client.post(
        "/api/v1/jobs",
        json={
            "job_type": "tls_discovery",
            "target_id": target_id,
        },
    )
    assert res2.status_code == 409
    assert "already active" in res2.json()["error"]["message"]


@pytest.mark.asyncio
async def test_cancel_discovery_job(async_client: AsyncClient) -> None:
    """Verify pending jobs can be cancelled safely."""
    res = await async_client.post(
        "/api/v1/jobs",
        json={
            "job_type": "config_import",
            "input_params": {"file": "nginx.conf"},
        },
    )
    assert res.status_code == 201
    job_id = res.json()["id"]

    cancel_res = await async_client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_job_service_zombie_recovery(test_db_session: AsyncSession) -> None:
    """Verify orphaned/zombie running jobs past heartbeat expiration are recovered."""
    # Insert a stale running job with expired lease
    stale_job = DiscoveryJob(
        job_type=JobType.SOURCE_ANALYSIS.value,
        status=JobStatus.RUNNING.value,
        worker_id="crashed-worker-99",
        retry_count=0,
        max_retries=3,
        lease_expires_at=datetime.now(UTC) - timedelta(seconds=10),
    )
    test_db_session.add(stale_job)
    await test_db_session.commit()
    await test_db_session.refresh(stale_job)

    # Run zombie recovery
    recovered_count = await JobService.recover_zombies(test_db_session)
    assert recovered_count >= 1

    await test_db_session.refresh(stale_job)
    assert stale_job.status == JobStatus.QUEUED.value
    assert stale_job.retry_count == 1
