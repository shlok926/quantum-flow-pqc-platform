"""Quantum Flow Technologies — Recommendation Entity Model.

Represents an actionable, evidence-backed PQC remediation recommendation
linked to a risk assessment and asset.
"""

import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from services.api.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from services.api.app.db.models.cryptographic_asset import CryptographicAsset
    from services.api.app.db.models.risk_assessment import RiskAssessment

JSONType = JSON().with_variant(JSONB(), "postgresql")


class RemediationCategory(enum.StrEnum):
    """Categorisation of cryptographic remediation actions."""

    ALGORITHM_MIGRATION = "algorithm_migration"
    KEY_SIZE_INCREASE = "key_size_increase"
    HYBRID_UPGRADE = "hybrid_upgrade"
    DEPRECATION = "deprecation"
    FURTHER_DISCOVERY = "further_discovery"


class RecommendationPriority(enum.StrEnum):
    """Urgency level of recommended action."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Recommendation(Base, TimestampMixin):
    """Durable record of an actionable remediation recommendation."""

    __tablename__ = "recommendations"
    __table_args__ = (
        Index("ix_recommendations_assessment_id", "risk_assessment_id"),
        Index("ix_recommendations_asset_id", "asset_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    risk_assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("risk_assessments.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cryptographic_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    remediation_category: Mapped[str] = mapped_column(
        String(50),
        default=RemediationCategory.ALGORITHM_MIGRATION.value,
        nullable=False,
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        default=RecommendationPriority.MEDIUM.value,
        nullable=False,
    )
    evidence_refs: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        nullable=False,
    )
    validation_steps: Mapped[list[str]] = mapped_column(
        JSONType,
        default=list,
        nullable=False,
    )
    known_limitations: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    risk_assessment: Mapped["RiskAssessment"] = relationship(
        "RiskAssessment",
        back_populates="recommendations",
    )
    asset: Mapped["CryptographicAsset"] = relationship(
        "CryptographicAsset",
        lazy="selectin",
    )
