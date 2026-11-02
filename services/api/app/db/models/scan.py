"""Quantum Flow Technologies — Scan Execution Entity Model."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.api.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from services.api.app.db.models.observation import Observation
    from services.api.app.db.models.target import Target


class ScanStatus(enum.StrEnum):
    """Execution status of an individual scan inspection."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Scan(Base, TimestampMixin):
    """Durable record of a bounded TLS discovery inspection."""

    __tablename__ = "scans"
    __table_args__ = (
        Index(
            "uq_scans_active_target",
            "target_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'in_progress')"),
            sqlite_where=text("status IN ('pending', 'in_progress')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("targets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scan_type: Mapped[str] = mapped_column(
        String(50),
        default="tls_handshake",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=ScanStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    target_ip: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        doc="Validated and pinned destination IP address used for connection",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Sanitized failure description",
    )
    collector_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    target: Mapped["Target"] = relationship(
        "Target",
        back_populates="scans",
    )
    observations: Mapped[list["Observation"]] = relationship(
        "Observation",
        back_populates="scan",
        cascade="all, delete-orphan",
        order_by="desc(Observation.created_at)",
    )
