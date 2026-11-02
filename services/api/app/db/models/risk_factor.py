"""Quantum Flow Technologies — Risk Factor Entity Model.

Represents an individual dimension evaluation or explanation contributing
to a quantum risk assessment score.
"""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from services.api.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from services.api.app.db.models.risk_assessment import RiskAssessment

JSONType = JSON().with_variant(JSONB(), "postgresql")


class RiskFactor(Base, TimestampMixin):
    """Specific factor contributing to a quantum risk assessment."""

    __tablename__ = "risk_factors"
    __table_args__ = (Index("ix_risk_factors_assessment_id", "risk_assessment_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    risk_assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("risk_assessments.id", ondelete="CASCADE"),
        nullable=False,
    )
    factor_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Machine-readable factor identifier (e.g. DIM_Q_SHOR_EXPOSURE)",
    )
    dimension: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Evaluation dimension: Q, R, L, E, B, M, V",
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Detailed rationale explaining the score contribution",
    )
    rating: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Normalised rating from 0 to 5",
    )
    weight: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Dimension weight (totaling 1000)",
    )
    contribution: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Calculated point contribution: round(weight * rating / 5)",
    )
    evidence_refs: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        nullable=False,
        doc="References to supporting observations or asset properties",
    )
    input_values: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        nullable=False,
        doc="Non-secret input facts considered during evaluation",
    )

    # Relationships
    risk_assessment: Mapped["RiskAssessment"] = relationship(
        "RiskAssessment",
        back_populates="factors",
    )
