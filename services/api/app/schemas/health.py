"""Quantum Flow Technologies — Health & Diagnostic Schemas."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthLiveResponse(BaseModel):
    """Payload returned by liveness probe confirming process is responsive."""

    status: str = Field(default="alive", description="Process liveness state")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp of the probe",
    )
    version: str = Field(description="Application version")
    service: str = Field(default="quantum-flow-api", description="Service name")


class DependencyStatus(BaseModel):
    """Detailed health status for a single backing dependency."""

    status: str = Field(description="Health state (e.g., connected, disconnected, error)")
    detail: str | None = Field(default=None, description="Diagnostic detail or failure message")


class HealthReadyResponse(BaseModel):
    """Payload returned by readiness probe checking backing dependencies."""

    status: str = Field(description="System readiness state ('ready' or 'not_ready')")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp of the probe",
    )
    version: str = Field(description="Application version")
    dependencies: dict[str, DependencyStatus] = Field(
        description="Status map of critical backing dependencies"
    )


class ErrorDetail(BaseModel):
    """Standardized error payload conforming to RFC 7807 problem details pattern."""

    code: str = Field(description="Stable machine-readable error code")
    message: str = Field(description="Human-readable explanation of the error")
    details: Any = Field(default=None, description="Optional granular field errors or context")


class ErrorResponse(BaseModel):
    """Standard top-level envelope for API errors."""

    success: bool = Field(default=False, description="Always false for error responses")
    error: ErrorDetail = Field(description="Structured error details")
