"""Quantum Flow Technologies — Observation API Schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ObservationResponse(BaseModel):
    """Response model representing a persistent cryptographic observation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    target_id: UUID
    scan_id: UUID | None
    observation_type: str
    source: str
    observed_value: dict[str, Any]
    evidence_sha256: str
    evidence_reference: str | None
    confidence: float
    collection_status: str
    observed_at: datetime
    collector_version: str
    created_at: datetime


class ObservationListResponse(BaseModel):
    """Collection of observations associated with a target."""

    items: list[ObservationResponse]
    total: int
