"""Quantum Flow Technologies — Assessment to Cryptographic Asset Association Model.

Preserves the historical participation of assets across assessments along with
frozen asset metadata snapshots and risk evaluation links.
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, ForeignKeyConstraint, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from services.api.app.db.base import Base

if TYPE_CHECKING:
    from services.api.app.db.models.assessment import Assessment
    from services.api.app.db.models.cryptographic_asset import CryptographicAsset
    from services.api.app.db.models.risk_assessment import RiskAssessment

JSONType = JSON().with_variant(JSONB(), "postgresql")


class AssessmentAsset(Base):
    """Associates an assessment run with a cryptographic asset, freezing metadata at assessment time."""

    __tablename__ = "assessment_assets"
    __table_args__ = (
        ForeignKeyConstraint(
            ["risk_assessment_id", "assessment_id", "asset_id"],
            ["risk_assessments.id", "risk_assessments.assessment_id", "risk_assessments.asset_id"],
            ondelete="SET NULL",
            name="fk_assessment_assets_risk_composite",
        ),
        Index("ix_assessment_assets_assessment_id", "assessment_id"),
        Index("ix_assessment_assets_asset_id", "asset_id"),
        Index("ix_assessment_assets_risk_id", "risk_assessment_id"),
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cryptographic_assets.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    classification: Mapped[str] = mapped_column(
        String(30),
        default="OBSERVED",
        nullable=False,
        doc="OBSERVED, INFERRED, IMPORTED, UNKNOWN",
    )
    asset_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        nullable=False,
        doc="Frozen copy of asset attributes (display_name, algorithm, purpose, parameters) at assessment time",
    )
    risk_assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True,
        doc="Links to the specific immutable RiskAssessment evaluated for this assessment run",
    )
    first_seen_in_assessment: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="True if the cryptographic asset was first created/discovered during this assessment",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    assessment: Mapped["Assessment"] = relationship(
        "Assessment",
        back_populates="assessment_assets",
        foreign_keys=[assessment_id],
    )
    asset: Mapped["CryptographicAsset"] = relationship(
        "CryptographicAsset",
        back_populates="assessment_associations",
        foreign_keys=[asset_id],
    )
    risk_assessment: Mapped["RiskAssessment | None"] = relationship(
        "RiskAssessment",
        foreign_keys=[risk_assessment_id, assessment_id, asset_id],
        overlaps="assessment,assessment_assets,asset,assessment_associations",
    )
