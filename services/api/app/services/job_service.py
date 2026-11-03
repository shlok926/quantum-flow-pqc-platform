"""Quantum Flow Technologies — Discovery Job Management Service.

Implements durable PostgreSQL-backed job orchestration, atomic worker claiming
with lease timeouts, zombie task recovery, and bounded retries.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.db.models.discovery_job import DiscoveryJob, JobStatus

logger = logging.getLogger("quantumflow.jobs")


class DuplicateJobError(Exception):
    """Raised when an identical job is already queued or running."""


class JobService:
    """Service layer managing the lifecycle of discovery jobs."""

    @staticmethod
    async def create_job(
        db: AsyncSession,
        job_type: str,
        input_params: dict[str, Any],
        target_id: uuid.UUID | None = None,
        assessment_id: uuid.UUID | None = None,
        timeout_seconds: int = 300,
        max_retries: int = 3,
    ) -> DiscoveryJob:
        """Create and queue a new durable discovery job.

        Prevents duplicate active submissions with identical target and parameters.
        """
        # Duplicate active check
        stmt = select(DiscoveryJob).where(
            DiscoveryJob.job_type == job_type,
            DiscoveryJob.status.in_([JobStatus.QUEUED.value, JobStatus.RUNNING.value]),
        )
        if target_id is not None:
            stmt = stmt.where(DiscoveryJob.target_id == target_id)
        if assessment_id is not None:
            stmt = stmt.where(DiscoveryJob.assessment_id == assessment_id)

        result = await db.execute(stmt)
        active_jobs = result.scalars().all()
        for active in active_jobs:
            if active.input_params == input_params:
                logger.info("Found existing duplicate active job: %s", active.id)
                raise DuplicateJobError(
                    f"A discovery job ({active.id}) is already active for this target"
                )

        job = DiscoveryJob(
            job_type=job_type,
            target_id=target_id,
            assessment_id=assessment_id,
            input_params=input_params,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            status=JobStatus.QUEUED.value,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        logger.info("Created and queued discovery job %s (type=%s)", job.id, job_type)
        return job

    @staticmethod
    async def get_job(db: AsyncSession, job_id: uuid.UUID) -> DiscoveryJob | None:
        """Retrieve a discovery job by primary key."""
        stmt = select(DiscoveryJob).where(DiscoveryJob.id == job_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_jobs(
        db: AsyncSession,
        status: str | None = None,
        job_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[DiscoveryJob], int]:
        """List discovery jobs with optional status/type filtering and total count."""
        stmt = select(DiscoveryJob)
        count_stmt = select(func.count(DiscoveryJob.id))

        if status:
            stmt = stmt.where(DiscoveryJob.status == status)
            count_stmt = count_stmt.where(DiscoveryJob.status == status)
        if job_type:
            stmt = stmt.where(DiscoveryJob.job_type == job_type)
            count_stmt = count_stmt.where(DiscoveryJob.job_type == job_type)

        stmt = stmt.order_by(DiscoveryJob.created_at.desc()).limit(limit).offset(offset)

        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one()

        jobs_res = await db.execute(stmt)
        jobs = list(jobs_res.scalars().all())

        return jobs, total

    @staticmethod
    async def claim_next_job(
        db: AsyncSession,
        worker_id: str,
        supported_types: list[str] | None = None,
        lease_seconds: int = 60,
    ) -> DiscoveryJob | None:
        """Atomically claim the next queued discovery job using a leased lock.

        Uses SELECT FOR UPDATE with skip_locked to support multiple concurrent workers
        without race conditions or deadlock collisions.
        """
        now = datetime.now(UTC)
        stmt = (
            select(DiscoveryJob)
            .where(DiscoveryJob.status == JobStatus.QUEUED.value)
            .order_by(DiscoveryJob.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if supported_types:
            stmt = stmt.where(DiscoveryJob.job_type.in_(supported_types))

        res = await db.execute(stmt)
        job = res.scalar_one_or_none()
        if not job:
            return None

        job.status = JobStatus.RUNNING.value
        job.worker_id = worker_id
        job.started_at = now
        job.lease_expires_at = now + timedelta(seconds=lease_seconds)
        job.progress_percent = 5

        await db.commit()
        await db.refresh(job)
        logger.info("Worker %s claimed job %s (type=%s)", worker_id, job.id, job.job_type)
        return job

    @staticmethod
    async def renew_lease(
        db: AsyncSession,
        job_id: uuid.UUID,
        worker_id: str,
        lease_seconds: int = 60,
        progress_percent: int | None = None,
    ) -> bool:
        """Heartbeat lease renewal for an actively executing job."""
        stmt = select(DiscoveryJob).where(
            DiscoveryJob.id == job_id,
            DiscoveryJob.worker_id == worker_id,
            DiscoveryJob.status == JobStatus.RUNNING.value,
        )
        res = await db.execute(stmt)
        job = res.scalar_one_or_none()
        if not job:
            return False

        job.lease_expires_at = datetime.now(UTC) + timedelta(seconds=lease_seconds)
        if progress_percent is not None:
            job.progress_percent = min(max(progress_percent, 0), 100)

        await db.commit()
        return True

    @staticmethod
    async def complete_job(
        db: AsyncSession,
        job_id: uuid.UUID,
        result_summary: dict[str, Any],
    ) -> DiscoveryJob:
        """Mark a job as successfully completed with result metrics."""
        job = await JobService.get_job(db, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = JobStatus.COMPLETED.value
        job.result_summary = result_summary
        job.progress_percent = 100
        job.completed_at = datetime.now(UTC)
        job.lease_expires_at = None

        await db.commit()
        await db.refresh(job)
        logger.info("Job %s completed successfully", job_id)
        return job

    @staticmethod
    async def fail_job(
        db: AsyncSession,
        job_id: uuid.UUID,
        error_message: str,
        can_retry: bool = True,
    ) -> DiscoveryJob:
        """Record job failure; re-queue if under max_retries limit."""
        job = await JobService.get_job(db, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.retry_count += 1
        job.lease_expires_at = None

        if can_retry and job.retry_count <= job.max_retries:
            job.status = JobStatus.QUEUED.value
            job.error_message = f"Attempt {job.retry_count} failed: {error_message}"
            job.worker_id = None
            logger.warning(
                "Job %s failed on attempt %d/%d; re-queued for retry",
                job_id,
                job.retry_count,
                job.max_retries,
            )
        else:
            job.status = JobStatus.FAILED.value
            job.error_message = f"Execution failed: {error_message}"
            job.completed_at = datetime.now(UTC)
            logger.error(
                "Job %s marked permanently FAILED after %d attempts", job_id, job.retry_count
            )

        await db.commit()
        await db.refresh(job)
        return job

    @staticmethod
    async def cancel_job(
        db: AsyncSession,
        job_id: uuid.UUID,
        reason: str = "Cancellation requested by operator",
    ) -> DiscoveryJob:
        """Cancel an active or queued job."""
        job = await JobService.get_job(db, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        if job.status in (JobStatus.COMPLETED.value, JobStatus.FAILED.value):
            return job

        job.status = JobStatus.CANCELLED.value
        job.error_message = reason
        job.completed_at = datetime.now(UTC)
        job.lease_expires_at = None

        await db.commit()
        await db.refresh(job)
        logger.info("Job %s cancelled: %s", job_id, reason)
        return job

    @staticmethod
    async def recover_zombies(
        db: AsyncSession,
    ) -> int:
        """Identify and recover abandoned/crashed worker jobs whose lease has expired."""
        now = datetime.now(UTC)
        stmt = (
            select(DiscoveryJob)
            .where(
                DiscoveryJob.status == JobStatus.RUNNING.value,
                DiscoveryJob.lease_expires_at < now,
            )
            .with_for_update(skip_locked=True)
        )
        res = await db.execute(stmt)
        zombies = res.scalars().all()

        recovered_count = 0
        for job in zombies:
            job.retry_count += 1
            if job.retry_count <= job.max_retries:
                job.status = JobStatus.QUEUED.value
                job.worker_id = None
                job.lease_expires_at = None
                job.error_message = f"Recovered from dead worker on attempt {job.retry_count}"
                logger.warning("Re-queued zombie job %s", job.id)
            else:
                job.status = JobStatus.FAILED.value
                job.completed_at = now
                job.error_message = "Job lease expired and max retries exhausted"
                logger.error("Marked zombie job %s as FAILED", job.id)
            recovered_count += 1

        if recovered_count > 0:
            await db.commit()

        return recovered_count
