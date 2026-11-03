"""create_assessments_and_association_tables

Revision ID: 4a2d8e1f9b3c
Revises: 288ce714065a
Create Date: 2026-11-02 14:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "4a2d8e1f9b3c"
down_revision: str | None = "288ce714065a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create assessments table
    op.create_table(
        "assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column(
            "target_snapshot",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("scope_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column(
            "progress_stage", sa.String(length=100), nullable=False, server_default="PENDING"
        ),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "discovery_sources",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "collector_results",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column(
            "coverage_summary",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "asset_counts",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "risk_summary",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "report_snapshot",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("report_snapshot_hash", sa.String(length=64), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column(
            "methodology_version",
            sa.String(length=50),
            nullable=False,
            server_default="QFT-RISK-v1.0",
        ),
        sa.Column("engine_version", sa.String(length=50), nullable=False, server_default="v1.0.0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assessments_target_id", "assessments", ["target_id"])
    op.create_index("ix_assessments_status", "assessments", ["status"])
    op.create_index("ix_assessments_created_at", "assessments", ["created_at"])
    op.create_index(
        "uq_assessments_active_target_scope",
        "assessments",
        ["target_id", "scope_hash"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'queued', 'running')"),
        sqlite_where=sa.text("status IN ('pending', 'queued', 'running')"),
    )

    # 2. Add assessment_id to discovery_jobs
    op.add_column("discovery_jobs", sa.Column("assessment_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_discovery_jobs_assessment_id",
        "discovery_jobs",
        "assessments",
        ["assessment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_discovery_jobs_assessment_id", "discovery_jobs", ["assessment_id"])

    # 3. Add assessment_id and unique constraint to risk_assessments
    op.add_column("risk_assessments", sa.Column("assessment_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_risk_assessments_assessment_id",
        "risk_assessments",
        "assessments",
        ["assessment_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_risk_assessments_assessment_id", "risk_assessments", ["assessment_id"])
    op.create_unique_constraint(
        "uq_risk_assessment_run_asset", "risk_assessments", ["assessment_id", "asset_id"]
    )

    # 4. Create assessment_assets association table
    op.create_table(
        "assessment_assets",
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column(
            "classification", sa.String(length=30), nullable=False, server_default="OBSERVED"
        ),
        sa.Column(
            "asset_snapshot",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("risk_assessment_id", sa.Uuid(), nullable=True),
        sa.Column("first_seen_in_assessment", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["cryptographic_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["risk_assessment_id"], ["risk_assessments.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("assessment_id", "asset_id"),
    )
    op.create_index("ix_assessment_assets_assessment_id", "assessment_assets", ["assessment_id"])
    op.create_index("ix_assessment_assets_asset_id", "assessment_assets", ["asset_id"])
    op.create_index("ix_assessment_assets_risk_id", "assessment_assets", ["risk_assessment_id"])

    # 5. Create assessment_observations association table
    op.create_table(
        "assessment_observations",
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("observation_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["observation_id"], ["observations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("assessment_id", "observation_id"),
    )
    op.create_index("ix_assessment_obs_assessment_id", "assessment_observations", ["assessment_id"])
    op.create_index(
        "ix_assessment_obs_observation_id", "assessment_observations", ["observation_id"]
    )


def downgrade() -> None:
    # 1. Drop association tables
    op.drop_table("assessment_observations")
    op.drop_table("assessment_assets")

    # 2. Revert risk_assessments changes
    op.drop_constraint("uq_risk_assessment_run_asset", "risk_assessments", type_="unique")
    op.drop_index("ix_risk_assessments_assessment_id", table_name="risk_assessments")
    op.drop_constraint("fk_risk_assessments_assessment_id", "risk_assessments", type_="foreignkey")
    op.drop_column("risk_assessments", "assessment_id")

    # 3. Revert discovery_jobs changes
    op.drop_index("ix_discovery_jobs_assessment_id", table_name="discovery_jobs")
    op.drop_constraint("fk_discovery_jobs_assessment_id", "discovery_jobs", type_="foreignkey")
    op.drop_column("discovery_jobs", "assessment_id")

    # 4. Drop assessments table
    op.drop_table("assessments")
