"""Quantum Flow Technologies — Asset Relationship Entity Model.

Models typed, directed relationships between cryptographic assets in the CBOM graph.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.api.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from services.api.app.db.models.cryptographic_asset import CryptographicAsset


class AssetRelationship(Base, TimestampMixin):
    """Directed relationship between two CryptographicAsset entities."""

    __tablename__ = "asset_relationships"
    __table_args__ = (
        Index(
            "uq_asset_rel_pair",
            "source_asset_id",
            "target_asset_id",
            "relationship_type",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    source_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cryptographic_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cryptographic_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="e.g. uses_certificate, depends_on_library, configures_endpoint, implements_primitive",
    )
    confidence_score: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    source_asset: Mapped["CryptographicAsset"] = relationship(
        "CryptographicAsset",
        foreign_keys=[source_asset_id],
        back_populates="outgoing_relationships",
    )
    target_asset: Mapped["CryptographicAsset"] = relationship(
        "CryptographicAsset",
        foreign_keys=[target_asset_id],
        lazy="selectin",
    )
