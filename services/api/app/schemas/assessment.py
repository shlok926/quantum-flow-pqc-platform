"""Quantum Flow Technologies — Assessment API Pydantic Schemas.

Defines request and response schemas for post-quantum cryptographic assessments,
immutable report snapshots, and child discovery job inspection.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

VALID_SOURCES = {
    "network_tls",
    "static_source",
    "dependency_manifest",
    "config_import",
}

SOURCE_ALIASES = {
    "tls": "network_tls",
    "network_tls": "network_tls",
    "tls_discovery": "network_tls",
    "source": "static_source",
    "static_source": "static_source",
    "source_code": "static_source",
    "source_analysis": "static_source",
    "dependencies": "dependency_manifest",
    "dependency_manifest": "dependency_manifest",
    "dependency_scan": "dependency_manifest",
    "config": "config_import",
    "config_import": "config_import",
}


class AssessmentCreateRequest(BaseModel):
    """Payload for submitting a new post-quantum cryptographic assessment."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable assessment title",
        examples=["Quarterly PQC Assessment - Production Core"],
    )
    target_id: uuid.UUID | None = Field(
        default=None,
        description="Optional registered target domain UUID",
    )
    discovery_sources: list[str] = Field(
        default_factory=lambda: ["network_tls"],
        description="Discovery collectors to execute (network_tls, static_source, dependency_manifest, config_import)",
    )
    input_payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Collector-specific parameters (source_archive_path, config_content, config_type, etc.)",
    )
    upload_token: str | None = Field(
        default=None,
        description="Cryptographic upload token returned from stage-upload endpoint",
    )
    extra_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional scope qualifiers and tenant/environment metadata",
    )

    @field_validator("discovery_sources")
    @classmethod
    def validate_and_normalize_sources(cls, sources: list[str]) -> list[str]:
        """Validate and normalize requested discovery source names."""
        if not sources:
            raise ValueError("At least one discovery source must be specified.")

        normalized: set[str] = set()
        for s in sources:
            clean = s.strip().lower()
            norm = SOURCE_ALIASES.get(clean, clean)
            if norm not in VALID_SOURCES:
                valid_str = ", ".join(sorted(VALID_SOURCES))
                raise ValueError(
                    f"Unsupported discovery source '{s}'. Supported sources are: {valid_str}"
                )
            normalized.add(norm)

        return sorted(normalized)


class AssessmentCancelRequest(BaseModel):
    """Payload for cancelling an active assessment."""

    reason: str = Field(
        default="User cancellation",
        min_length=1,
        max_length=500,
        description="Reason for cancelling the assessment",
        examples=["Maintenance window opened; rescheduling scan"],
    )


class AssessmentResponse(BaseModel):
    """Full representation of a post-quantum cryptographic assessment entity."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    target_id: uuid.UUID | None
    target_snapshot: dict[str, Any]
    scope_hash: str
    status: str
    progress_stage: str
    progress_percent: int
    discovery_sources: list[str]
    collector_results: dict[str, Any]
    coverage_summary: dict[str, Any]
    asset_counts: dict[str, Any]
    risk_summary: dict[str, Any]
    error_summary: str | None
    report_snapshot_hash: str | None
    methodology_version: str
    engine_version: str
    retry_count: int
    max_retries: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AssessmentListResponse(BaseModel):
    """Paginated list of assessment summaries."""

    items: list[AssessmentResponse]
    total: int
    limit: int
    offset: int


class AssessmentReportResponse(BaseModel):
    """Immutable terminal report snapshot with cryptographic verification."""

    assessment_id: uuid.UUID
    status: str
    methodology_version: str
    engine_version: str
    report_snapshot: dict[str, Any]
    report_snapshot_hash: str
    is_hash_verified: bool = Field(
        ...,
        description="True if RFC 8785 canonical hash of report_snapshot matches report_snapshot_hash",
    )
    is_immutable: bool = Field(
        default=True,
        description="Protected by PostgreSQL trigger trg_protect_terminal_assessment_snapshot",
    )
    completed_at: datetime | None


class AssessmentJobSummary(BaseModel):
    """Status and leasing metrics for a child discovery job."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_type: str
    status: str
    progress_percent: int
    worker_id: str | None
    lease_expires_at: datetime | None
    retry_count: int
    error_message: str | None
    result_summary: dict[str, Any] | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class AssessmentJobListResponse(BaseModel):
    """List of child discovery jobs associated with an assessment."""

    assessment_id: uuid.UUID
    total_jobs: int
    jobs: list[AssessmentJobSummary]


class UploadTokenMetadata(BaseModel):
    """Metadata schema persisted in metadata.json alongside staged archives."""

    upload_token: str = Field(..., description="Cryptographic upload token UUID")
    tenant_id: str = Field(..., description="Authoritative tenant identifier")
    filename: str = Field(..., description="Original archive filename")
    byte_size: int = Field(..., ge=0, description="Exact file size in bytes")
    sha256: str = Field(..., description="SHA-256 hex digest of staged archive")
    content_type: str = Field(default="application/zip", description="MIME content type")
    status: str = Field(default="staged", description="Staging status (staged, claimed, active)")
    uploaded_at: str = Field(..., description="ISO 8601 UTC timestamp of upload finalization")
    assessment_id: str | None = Field(default=None, description="Bound assessment UUID if claimed")
    retry_count: int = Field(default=0, ge=0, description="Number of execution retries")


class StagedUploadResponse(BaseModel):
    """API response schema returned by POST /api/v1/assessments/stage-upload."""

    upload_token: str = Field(..., description="Opaque upload token for binding to assessment")
    filename: str = Field(..., description="Sanitized uploaded filename")
    byte_size: int = Field(..., ge=0, description="Size of uploaded file in bytes")
    sha256: str = Field(..., description="Cryptographic SHA-256 digest of uploaded file")
    status: str = Field(default="staged", description="Upload status")
    uploaded_at: datetime = Field(..., description="Timestamp when upload was staged")
