"""Quantum Flow Technologies — Discovery Job Pydantic Schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from services.api.app.db.models.discovery_job import JobType


class DiscoveryJobCreate(BaseModel):
    """Payload to submit a new discovery or analysis job."""

    job_type: JobType = Field(..., description="Job classification type")
    target_id: uuid.UUID | None = Field(
        default=None, description="Optional associated target domain"
    )
    input_params: dict[str, Any] = Field(
        default_factory=dict, description="Job parameters and input references"
    )
    timeout_seconds: int = Field(
        default=300, ge=10, le=3600, description="Maximum execution time budget in seconds"
    )


class DiscoveryJobResponse(BaseModel):
    """Durable state representation of a discovery job."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_type: str
    status: str
    target_id: uuid.UUID | None
    input_params: dict[str, Any]
    result_summary: dict[str, Any] | None
    error_message: str | None
    progress_percent: int
    timeout_seconds: int
    retry_count: int
    max_retries: int
    worker_id: str | None
    lease_expires_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DiscoveryJobListResponse(BaseModel):
    """Paginated list of discovery jobs."""

    jobs: list[DiscoveryJobResponse]
    total: int
    limit: int
    offset: int
