"""Quantum Flow Technologies — SQLAlchemy Declarative Base.

All ORM entity models inherit from this base class.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy domain models."""

    # Common type annotations for subclasses in future sprints
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }


class TimestampMixin:
    """Mixin adding UTC creation and modification timestamps to models."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class TenantScopedMixin:
    """Mixin enforcing tenant isolation ownership on domain entities."""

    tenant_id: Mapped[UUID] = mapped_column(
        nullable=False,
        index=True,
    )
