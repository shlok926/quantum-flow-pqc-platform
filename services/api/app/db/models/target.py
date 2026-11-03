"""Quantum Flow Technologies — Target Domain Entity Model."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.api.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from services.api.app.db.models.assessment import Assessment
    from services.api.app.db.models.observation import Observation
    from services.api.app.db.models.scan import Scan


class TargetStatus(enum.StrEnum):
    """Operational lifecycle status of an inspected domain target."""

    PENDING_VERIFICATION = "pending_verification"
    VERIFIED = "verified"
    DISABLED = "disabled"


class AuthorisationStatus(enum.StrEnum):
    """Explicit legal authorisation state for scanning a domain target."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    REVOKED = "revoked"


class Target(Base, TimestampMixin):
    """Registered domain target for cryptographic discovery."""

    __tablename__ = "targets"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    hostname: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=TargetStatus.PENDING_VERIFICATION.value,
        nullable=False,
        index=True,
    )
    authorisation_status: Mapped[str] = mapped_column(
        String(50),
        default=AuthorisationStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    authorised_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    authorisation_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    verification_token: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: f"qf-verify={uuid.uuid4()}",
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    disabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    scans: Mapped[list["Scan"]] = relationship(
        "Scan",
        back_populates="target",
        cascade="all, delete-orphan",
        order_by="desc(Scan.created_at)",
    )
    assessments: Mapped[list["Assessment"]] = relationship(
        "Assessment",
        back_populates="target",
    )
    observations: Mapped[list["Observation"]] = relationship(
        "Observation",
        back_populates="target",
        cascade="all, delete-orphan",
        order_by="desc(Observation.created_at)",
    )

    @property
    def is_eligible_for_scan(self) -> bool:
        """A target is strictly eligible for network scan only when both verified and confirmed."""
        return (
            self.status == TargetStatus.VERIFIED.value
            and self.authorisation_status == AuthorisationStatus.CONFIRMED.value
        )
