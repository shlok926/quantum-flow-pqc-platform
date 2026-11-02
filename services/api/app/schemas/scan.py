"""Quantum Flow Technologies — Scan API Schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScanCreate(BaseModel):
    """Payload to trigger a discovery scan on an eligible target."""

    scan_type: str = Field(
        default="tls_handshake",
        description="Type of inspection to execute",
    )


class ScanResponse(BaseModel):
    """Response model representing a scan execution record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    target_id: UUID
    scan_type: str
    status: str
    target_ip: str | None
    error_message: str | None
    collector_version: str
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ScanListResponse(BaseModel):
    """Collection of scans for a target."""

    items: list[ScanResponse]
    total: int
