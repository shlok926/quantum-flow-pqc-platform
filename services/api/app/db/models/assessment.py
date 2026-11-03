"""Quantum Flow Technologies — Enterprise Assessment Entity Model.

Manages durable lifecycle states, discovery orchestration, coverage accounting,
and immutable frozen report snapshots for end-to-end PQC risk assessments.
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from services.api.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from services.api.app.db.models.assessment_asset import AssessmentAsset
    from services.api.app.db.models.assessment_observation import AssessmentObservation
    from services.api.app.db.models.discovery_job import DiscoveryJob
    from services.api.app.db.models.risk_assessment import RiskAssessment
    from services.api.app.db.models.target import Target

JSONType = JSON().with_variant(JSONB(), "postgresql")


class AssessmentStatus(enum.StrEnum):
    """Lifecycle states of an enterprise cryptographic assessment."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AssessmentStage(enum.StrEnum):
    """Execution stages of an assessment workflow."""

    PENDING = "PENDING"
    VALIDATING_SCOPE = "VALIDATING_SCOPE"
    DISPATCHING_COLLECTORS = "DISPATCHING_COLLECTORS"
    INGESTING_OBSERVATIONS = "INGESTING_OBSERVATIONS"
    CORRELATING_CBOM = "CORRELATING_CBOM"
    EVALUATING_RISK = "EVALUATING_RISK"
    FINALIZING = "FINALIZING"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Assessment(Base, TimestampMixin):
    """Durable record of an end-to-end enterprise cryptographic discovery and risk assessment."""

    __tablename__ = "assessments"
    __table_args__ = (
        CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="chk_assessment_progress_range",
        ),
        CheckConstraint(
            "status IN ('pending', 'queued', 'running', 'completed', 'partially_completed', 'failed', 'cancelled')",
            name="chk_assessment_status",
        ),
        Index(
            "uq_assessments_active_target_scope",
            "target_id",
            "scope_hash",
            unique=True,
            postgresql_where=text("status IN ('pending', 'queued', 'running')"),
            sqlite_where=text("status IN ('pending', 'queued', 'running')"),
        ),
        Index("ix_assessments_target_id", "target_id"),
        Index("ix_assessments_status", "status"),
        Index("ix_assessments_created_at", text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("targets.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        nullable=False,
        doc="Preserves target identity metadata (hostname, port, environment) even if target is later deleted",
    )
    scope_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="Deterministic hash of target_id and requested discovery sources to prevent duplicate active runs",
    )

    # Lifecycle & stage tracking
    status: Mapped[str] = mapped_column(
        String(50),
        default=AssessmentStatus.PENDING.value,
        nullable=False,
    )
    progress_stage: Mapped[str] = mapped_column(
        String(100),
        default=AssessmentStage.PENDING.value,
        nullable=False,
    )
    progress_percent: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Derived from actual execution state and collector outcomes (0-100)",
    )

    # Scope & collector execution history
    discovery_sources: Mapped[list[str]] = mapped_column(
        JSONType,
        default=list,
        nullable=False,
        doc="Requested sources: tls, source_code, dependencies, config",
    )
    collector_results: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        nullable=False,
        doc="Granular collector execution status, durations, error logs, and attempt records",
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

    # Coverage & Asset summaries
    coverage_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        nullable=False,
        doc="Coverage breakdown by source, classification (OBSERVED/INFERRED), and uninspected areas",
    )
    asset_counts: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        nullable=False,
        doc="Asset count totals broken down by type, classification, and criticality",
    )
    risk_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        nullable=False,
        doc="Overall QVI score, risk category, Shor vs Grover breakdown, and high-priority finding counts",
    )

    # Immutable Frozen Report Snapshot
    report_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
        doc="Frozen report payload computed upon terminal completion to ensure historical reports never mutate",
    )
    report_snapshot_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        doc="Canonical SHA-256 digest of report_snapshot verifying report immutability",
    )

    # Governance & Error logging
    error_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    methodology_version: Mapped[str] = mapped_column(
        String(50),
        default="QFT-RISK-v1.0",
        nullable=False,
    )
    engine_version: Mapped[str] = mapped_column(
        String(50),
        default="v1.0.0",
        nullable=False,
    )

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    target: Mapped["Target | None"] = relationship(
        "Target",
        back_populates="assessments",
    )
    discovery_jobs: Mapped[list["DiscoveryJob"]] = relationship(
        "DiscoveryJob",
        back_populates="assessment",
    )
    assessment_assets: Mapped[list["AssessmentAsset"]] = relationship(
        "AssessmentAsset",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    assessment_observations: Mapped[list["AssessmentObservation"]] = relationship(
        "AssessmentObservation",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    risk_assessments: Mapped[list["RiskAssessment"]] = relationship(
        "RiskAssessment",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )

    def is_terminal(self) -> bool:
        """Check if assessment has reached a terminal execution state."""
        return self.status in (
            AssessmentStatus.COMPLETED.value,
            AssessmentStatus.PARTIALLY_COMPLETED.value,
            AssessmentStatus.FAILED.value,
            AssessmentStatus.CANCELLED.value,
        )

    def is_active(self) -> bool:
        """Check if assessment is actively queued or executing."""
        return self.status in (
            AssessmentStatus.PENDING.value,
            AssessmentStatus.QUEUED.value,
            AssessmentStatus.RUNNING.value,
        )
