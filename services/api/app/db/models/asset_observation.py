"""Quantum Flow Technologies — Asset Observation Link Entity Model.

Represents an evidence link connecting a raw observation to a logical
cryptographic asset.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.api.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from services.api.app.db.models.cryptographic_asset import CryptographicAsset
    from services.api.app.db.models.observation import Observation


class AssetObservation(Base, TimestampMixin):
    """Many-to-many linkage between CryptographicAsset and Observation evidence."""

    __tablename__ = "asset_observations"
    __table_args__ = (Index("uq_asset_observation", "asset_id", "observation_id", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cryptographic_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    observation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(
        String(40),
        default="supports",
        nullable=False,
        doc="e.g. supports, identifies, updates",
    )
    correlation_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Human-readable justification for why this observation links to this asset",
    )
    correlation_version: Mapped[str] = mapped_column(
        String(50),
        default="v1.0.0",
        nullable=False,
    )

    # Relationships
    asset: Mapped["CryptographicAsset"] = relationship(
        "CryptographicAsset",
        back_populates="observations",
    )
    observation: Mapped["Observation"] = relationship(
        "Observation",
        lazy="selectin",
    )
