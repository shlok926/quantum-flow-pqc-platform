"""Quantum Flow Technologies — Discovery Job Entity Model.

Manages durable state transitions, leasing, retry limits, and progress
for asynchronous discovery and analysis jobs.
"""

import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from services.api.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from services.api.app.db.models.assessment import Assessment

JSONType = JSON().with_variant(JSONB(), "postgresql")


class JobStatus(enum.StrEnum):
    """Lifecycle states of an asynchronous discovery job."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(enum.StrEnum):
    """Supported discovery and analysis job types."""

    TLS_DISCOVERY = "tls_discovery"
    SOURCE_ANALYSIS = "source_analysis"
    DEPENDENCY_SCAN = "dependency_scan"
    CONFIG_IMPORT = "config_import"
    RISK_ASSESSMENT = "risk_assessment"


class DiscoveryJob(Base, TimestampMixin):
    """Durable record of an asynchronous discovery, parsing, or assessment job."""

    __tablename__ = "discovery_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    job_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=JobStatus.QUEUED.value,
        nullable=False,
        index=True,
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True,
        index=True,
    )
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assessments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    input_params: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        nullable=False,
    )
    result_summary: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    progress_percent: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        default=300,
        nullable=False,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
    )
    worker_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    assessment: Mapped["Assessment | None"] = relationship(
        "Assessment",
        back_populates="discovery_jobs",
    )

    def is_active(self) -> bool:
        """Check if job is in an active non-terminal state."""
        return self.status in (JobStatus.QUEUED.value, JobStatus.RUNNING.value)

    def is_expired(self) -> bool:
        """Check if a running job's lease has expired without renewal."""
        if self.status != JobStatus.RUNNING.value or self.lease_expires_at is None:
            return False
        return datetime.now(UTC) > self.lease_expires_at
