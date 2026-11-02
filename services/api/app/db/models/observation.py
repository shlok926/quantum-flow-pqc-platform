"""Quantum Flow Technologies — Cryptographic Observation Entity Model."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from services.api.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from services.api.app.db.models.scan import Scan
    from services.api.app.db.models.target import Target

JSONType = JSON().with_variant(JSONB(), "postgresql")


class Observation(Base, TimestampMixin):
    """Raw, immutable cryptographic evidence captured during discovery."""

    __tablename__ = "observations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("targets.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    scan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    observation_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="e.g. tls_endpoint, x509_certificate",
    )
    source: Mapped[str] = mapped_column(
        String(64),
        default="network_tls_probe",
        nullable=False,
    )
    observed_value: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        doc="Structured evidence payload preserving observed facts",
    )
    evidence_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Cryptographic SHA-256 digest of canonical serialized evidence payload",
    )
    evidence_reference: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Reference identifier, certificate serial or fingerprint provenance",
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
        doc="Confidence level (1.0 for directly observed facts)",
    )
    collection_status: Mapped[str] = mapped_column(
        String(32),
        default="observed",
        nullable=False,
        doc="observed, partial, failed, or unobserved",
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    collector_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Relationships
    target: Mapped["Target"] = relationship(
        "Target",
        back_populates="observations",
    )
    scan: Mapped["Scan | None"] = relationship(
        "Scan",
        back_populates="observations",
    )
