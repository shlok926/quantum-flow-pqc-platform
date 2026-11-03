"""Quantum Flow Technologies — Cryptographic Asset Entity Model.

Represents a logical cryptographic asset or usage instance identified
through correlation of discovery observations.
"""

import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from services.api.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from services.api.app.db.models.assessment_asset import AssessmentAsset
    from services.api.app.db.models.asset_observation import AssetObservation
    from services.api.app.db.models.asset_relationship import AssetRelationship
    from services.api.app.db.models.risk_assessment import RiskAssessment
    from services.api.app.db.models.target import Target

JSONType = JSON().with_variant(JSONB(), "postgresql")


class AssetType(enum.StrEnum):
    """Categorization of cryptographic assets in the inventory."""

    CERTIFICATE = "certificate"
    ENDPOINT_CONFIG = "endpoint_config"
    ALGORITHM_USAGE = "algorithm_usage"
    LIBRARY = "library"
    PROTOCOL_CONFIG = "protocol_config"
    KEY_REFERENCE = "key_reference"


class AssetClassification(enum.StrEnum):
    """Evidence strength and discovery classification."""

    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    IMPORTED = "IMPORTED"
    UNKNOWN = "UNKNOWN"


class LifecycleStatus(enum.StrEnum):
    """Asset lifecycle state."""

    ACTIVE = "active"
    CHANGED = "changed"
    STALE = "stale"
    RETIRED = "retired"
    UNKNOWN = "unknown"


class CryptographicAsset(Base, TimestampMixin):
    """Durable record of a correlated cryptographic asset or usage instance."""

    __tablename__ = "cryptographic_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("targets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    asset_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        index=True,
    )
    asset_key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Deterministic stable key for idempotent asset correlation",
    )
    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    locator: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Physical or logical location: e.g. host:port, relative file path, dependency name",
    )
    environment: Mapped[str | None] = mapped_column(
        String(30),
        default="production",
        nullable=True,
    )
    business_criticality: Mapped[str] = mapped_column(
        String(20),
        default="high",
        nullable=False,
    )
    algorithm_family: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
        index=True,
        doc="e.g. RSA, ECC, AES, SHA-2, ML-KEM",
    )
    algorithm_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
        index=True,
        doc="e.g. RSA-2048, ECDSA-secp256r1, AES-256-GCM",
    )
    cryptographic_purpose: Mapped[str] = mapped_column(
        String(40),
        default="unknown",
        nullable=False,
        doc="e.g. key_establishment, signature, encryption, integrity, hashing",
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        nullable=False,
        doc="Structured algorithm parameters: key size, curve name, mode, etc.",
    )
    lifecycle_status: Mapped[str] = mapped_column(
        String(20),
        default=LifecycleStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )
    classification: Mapped[str] = mapped_column(
        String(20),
        default=AssetClassification.OBSERVED.value,
        nullable=False,
    )
    confidence_score: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    correlation_version: Mapped[str] = mapped_column(
        String(50),
        default="v1.0.0",
        nullable=False,
    )

    # Relationships
    target: Mapped["Target | None"] = relationship(
        "Target",
        lazy="selectin",
    )
    observations: Mapped[list["AssetObservation"]] = relationship(
        "AssetObservation",
        back_populates="asset",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    outgoing_relationships: Mapped[list["AssetRelationship"]] = relationship(
        "AssetRelationship",
        foreign_keys="[AssetRelationship.source_asset_id]",
        back_populates="source_asset",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    risk_assessments: Mapped[list["RiskAssessment"]] = relationship(
        "RiskAssessment",
        back_populates="asset",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    assessment_associations: Mapped[list["AssessmentAsset"]] = relationship(
        "AssessmentAsset",
        back_populates="asset",
        passive_deletes=True,
    )
