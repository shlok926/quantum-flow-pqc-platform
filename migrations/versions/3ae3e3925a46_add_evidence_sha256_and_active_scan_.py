"""add_evidence_sha256_and_active_scan_unique_index

Revision ID: 3ae3e3925a46
Revises: 194e02e6b034
Create Date: 2026-11-02 10:25:19.312169+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3ae3e3925a46"
down_revision: str | None = "194e02e6b034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add evidence_sha256 column to observations table
    op.add_column(
        "observations",
        sa.Column(
            "evidence_sha256",
            sa.String(length=64),
            nullable=False,
            server_default="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        ),
    )
    op.alter_column("observations", "evidence_sha256", server_default=None)
    op.create_index(
        op.f("ix_observations_evidence_sha256"), "observations", ["evidence_sha256"], unique=False
    )

    # 2. Add partial unique index on scans to prevent concurrent duplicate active scans per target
    op.create_index(
        "uq_scans_active_target",
        "scans",
        ["target_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'in_progress')"),
        sqlite_where=sa.text("status IN ('pending', 'in_progress')"),
    )


def downgrade() -> None:
    # 1. Drop partial unique index on scans
    op.drop_index("uq_scans_active_target", table_name="scans")

    # 2. Drop index and column on observations
    op.drop_index(op.f("ix_observations_evidence_sha256"), table_name="observations")
    op.drop_column("observations", "evidence_sha256")
