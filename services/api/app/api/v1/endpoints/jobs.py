"""Quantum Flow Technologies — Discovery Jobs API Endpoints.

Provides endpoints for creating, querying, tracking, and cancelling discovery jobs.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.db.models.discovery_job import JobStatus, JobType
from services.api.app.db.session import get_db
from services.api.app.schemas.discovery_job import (
    DiscoveryJobCreate,
    DiscoveryJobListResponse,
    DiscoveryJobResponse,
)
from services.api.app.services.job_service import DuplicateJobError, JobService

router = APIRouter(prefix="/jobs", tags=["Discovery Jobs"])


@router.post(
    "",
    response_model=DiscoveryJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Discovery Job",
    description="Enqueue a durable asynchronous discovery, parsing, or risk assessment job.",
)
async def submit_discovery_job(
    payload: DiscoveryJobCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DiscoveryJobResponse:
    """Submit a discovery job."""
    try:
        job = await JobService.create_job(
            db=db,
            job_type=payload.job_type.value,
            input_params=payload.input_params,
            target_id=payload.target_id,
            timeout_seconds=payload.timeout_seconds,
        )
    except DuplicateJobError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return DiscoveryJobResponse.model_validate(job)


@router.get(
    "",
    response_model=DiscoveryJobListResponse,
    summary="List Discovery Jobs",
    description="List discovery jobs with optional status/type filtering and pagination.",
)
async def list_discovery_jobs(
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: JobStatus | None = Query(default=None, alias="status"),
    job_type: JobType | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> DiscoveryJobListResponse:
    """List jobs."""
    jobs, total = await JobService.list_jobs(
        db=db,
        status=status_filter.value if status_filter else None,
        job_type=job_type.value if job_type else None,
        limit=limit,
        offset=offset,
    )
    return DiscoveryJobListResponse(
        jobs=[DiscoveryJobResponse.model_validate(j) for j in jobs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{job_id}",
    response_model=DiscoveryJobResponse,
    summary="Get Discovery Job Status",
    description="Retrieve status, progress, and result metrics for a discovery job.",
)
async def get_discovery_job(
    job_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DiscoveryJobResponse:
    """Get job by ID."""
    job = await JobService.get_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery job '{job_id}' not found",
        )
    return DiscoveryJobResponse.model_validate(job)


@router.post(
    "/{job_id}/cancel",
    response_model=DiscoveryJobResponse,
    summary="Cancel Discovery Job",
    description="Cancel an active or queued discovery job.",
)
async def cancel_discovery_job(
    job_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DiscoveryJobResponse:
    """Cancel job."""
    try:
        job = await JobService.cancel_job(db, job_id)
        return DiscoveryJobResponse.model_validate(job)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
