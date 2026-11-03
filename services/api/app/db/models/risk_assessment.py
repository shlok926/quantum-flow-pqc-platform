"""Quantum Flow Technologies — Risk Assessment Entity Model.

Represents an immutable, reproducible quantum risk assessment evaluated
against the Quantum Risk Assessment Methodology v1.0.
"""

import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from services.api.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from services.api.app.db.models.assessment import Assessment
    from services.api.app.db.models.cryptographic_asset import CryptographicAsset
    from services.api.app.db.models.recommendation import Recommendation
    from services.api.app.db.models.risk_factor import RiskFactor

JSONType = JSON().with_variant(JSONB(), "postgresql")


class RiskCategory(enum.StrEnum):
    """Provisional quantum vulnerability risk category."""

    LOW = "low"  # 0–199
    GUARDED = "guarded"  # 200–399
    ELEVATED = "elevated"  # 400–599
    HIGH = "high"  # 600–799
    CRITICAL = "critical"  # 800–1000
    UNKNOWN = "unknown"


class ThreatType(enum.StrEnum):
    """Underlying quantum threat mechanism."""

    SHOR_VULNERABLE = "shor_vulnerable"
    GROVER_MARGIN = "grover_margin"
    PQC_RECOGNISED = "pqc_recognised"
    HYBRID_DEPLOYMENT = "hybrid_deployment"
    UNKNOWN = "unknown"


class RiskAssessment(Base, TimestampMixin):
    """Durable record of an explainable quantum risk assessment."""

    __tablename__ = "risk_assessments"
    __table_args__ = (
        CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 1000)",
            name="chk_risk_score_range",
        ),
        UniqueConstraint("assessment_id", "asset_id", name="uq_risk_assessment_run_asset"),
        UniqueConstraint(
            "id", "assessment_id", "asset_id", name="uq_risk_assessments_id_assessment_asset"
        ),
        UniqueConstraint(
            "id", "assessment_id", "asset_id", name="uq_risk_assessments_id_assessment_asset"
        ),
        Index("ix_risk_assessments_asset_id", "asset_id"),
        Index("ix_risk_assessments_assessment_id", "assessment_id"),
        Index("ix_risk_assessments_risk_category", "risk_category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=True,
        doc="Links this risk assessment evaluation to a specific enterprise assessment run",
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cryptographic_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    assessment_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="provisional",
        nullable=False,
        doc="provisional, approved, superseded, failed",
    )
    score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Quantum Vulnerability Index from 0 to 1000",
    )
    risk_category: Mapped[str] = mapped_column(
        String(30),
        default=RiskCategory.UNKNOWN.value,
        nullable=False,
    )
    quantum_threat_type: Mapped[str] = mapped_column(
        String(40),
        default=ThreatType.UNKNOWN.value,
        nullable=False,
    )
    threat_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Human-readable explanation of primary quantum threat rationale",
    )
    evidence_quality: Mapped[str] = mapped_column(
        String(20),
        default="medium",
        nullable=False,
        doc="high, medium, low, insufficient",
    )
    assessment_input_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="SHA-256 digest of canonical inputs to ensure reproducibility",
    )
    engine_version: Mapped[str] = mapped_column(
        String(50),
        default="v1.0.0",
        nullable=False,
    )
    methodology_version: Mapped[str] = mapped_column(
        String(50),
        default="QFT-RISK-v1.0",
        nullable=False,
    )
    policy_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        nullable=False,
        doc="Scoring weights and dimension policies frozen at assessment time",
    )
    limitations: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        nullable=False,
        doc="Assumptions, missing facts, and coverage boundary disclaimers",
    )
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    assessment: Mapped["Assessment | None"] = relationship(
        "Assessment",
        back_populates="risk_assessments",
    )
    asset: Mapped["CryptographicAsset"] = relationship(
        "CryptographicAsset",
        back_populates="risk_assessments",
    )
    factors: Mapped[list["RiskFactor"]] = relationship(
        "RiskFactor",
        back_populates="risk_assessment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        "Recommendation",
        back_populates="risk_assessment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
