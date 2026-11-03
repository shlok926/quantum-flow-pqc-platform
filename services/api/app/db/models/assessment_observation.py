"""Quantum Flow Technologies — Assessment to Observation Association Model.

Preserves immutable observation provenance for specific assessment runs.
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.api.app.db.base import Base

if TYPE_CHECKING:
    from services.api.app.db.models.assessment import Assessment
    from services.api.app.db.models.observation import Observation


class AssessmentObservation(Base):
    """Associates an assessment run with raw cryptographic observations captured during its execution."""

    __tablename__ = "assessment_observations"
    __table_args__ = (
        Index("ix_assessment_obs_assessment_id", "assessment_id"),
        Index("ix_assessment_obs_observation_id", "observation_id"),
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    observation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    assessment: Mapped["Assessment"] = relationship(
        "Assessment",
        back_populates="assessment_observations",
    )
    observation: Mapped["Observation"] = relationship(
        "Observation",
    )
