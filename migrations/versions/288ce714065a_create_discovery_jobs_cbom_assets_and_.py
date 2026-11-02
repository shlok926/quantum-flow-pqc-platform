"""create_discovery_jobs_cbom_assets_and_risk_tables

Revision ID: 288ce714065a
Revises: 3ae3e3925a46
Create Date: 2026-11-02 11:41:24.395649+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "288ce714065a"
down_revision: str | None = "3ae3e3925a46"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 0. make observations.target_id nullable for non-network observations
    op.alter_column("observations", "target_id", existing_type=sa.Uuid(), nullable=True)

    # 1. discovery_jobs
    op.create_table(
        "discovery_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column(
            "input_params",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "result_summary",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("worker_id", sa.String(length=100), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_discovery_jobs_job_type", "discovery_jobs", ["job_type"])
    op.create_index("ix_discovery_jobs_status", "discovery_jobs", ["status"])
    op.create_index("ix_discovery_jobs_target_id", "discovery_jobs", ["target_id"])
    op.create_index("ix_discovery_jobs_worker_id", "discovery_jobs", ["worker_id"])
    op.create_index("ix_discovery_jobs_lease_expires_at", "discovery_jobs", ["lease_expires_at"])

    # 2. cryptographic_assets
    op.create_table(
        "cryptographic_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("asset_type", sa.String(length=40), nullable=False),
        sa.Column("asset_key", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("locator", sa.Text(), nullable=True),
        sa.Column("environment", sa.String(length=30), nullable=True),
        sa.Column("business_criticality", sa.String(length=20), nullable=False),
        sa.Column("algorithm_family", sa.String(length=80), nullable=True),
        sa.Column("algorithm_name", sa.String(length=120), nullable=True),
        sa.Column("cryptographic_purpose", sa.String(length=40), nullable=False),
        sa.Column(
            "parameters",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("lifecycle_status", sa.String(length=20), nullable=False),
        sa.Column("classification", sa.String(length=20), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_key"),
    )
    op.create_index("ix_cryptographic_assets_target_id", "cryptographic_assets", ["target_id"])
    op.create_index("ix_cryptographic_assets_asset_type", "cryptographic_assets", ["asset_type"])
    op.create_index("ix_cryptographic_assets_asset_key", "cryptographic_assets", ["asset_key"])
    op.create_index(
        "ix_cryptographic_assets_algorithm_family", "cryptographic_assets", ["algorithm_family"]
    )
    op.create_index(
        "ix_cryptographic_assets_algorithm_name", "cryptographic_assets", ["algorithm_name"]
    )
    op.create_index(
        "ix_cryptographic_assets_lifecycle_status", "cryptographic_assets", ["lifecycle_status"]
    )

    # 3. asset_observations
    op.create_table(
        "asset_observations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("observation_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(length=40), nullable=False),
        sa.Column("correlation_reason", sa.Text(), nullable=True),
        sa.Column("correlation_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["cryptographic_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["observation_id"], ["observations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_asset_observation", "asset_observations", ["asset_id", "observation_id"], unique=True
    )
    op.create_index("ix_asset_observations_asset_id", "asset_observations", ["asset_id"])
    op.create_index(
        "ix_asset_observations_observation_id", "asset_observations", ["observation_id"]
    )

    # 4. asset_relationships
    op.create_table(
        "asset_relationships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_asset_id", sa.Uuid(), nullable=False),
        sa.Column("target_asset_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(length=50), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_asset_id"], ["cryptographic_assets.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_asset_id"], ["cryptographic_assets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_asset_rel_pair",
        "asset_relationships",
        ["source_asset_id", "target_asset_id", "relationship_type"],
        unique=True,
    )
    op.create_index("ix_asset_relationships_source_id", "asset_relationships", ["source_asset_id"])
    op.create_index("ix_asset_relationships_target_id", "asset_relationships", ["target_asset_id"])

    # 5. risk_assessments
    op.create_table(
        "risk_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("risk_category", sa.String(length=30), nullable=False),
        sa.Column("quantum_threat_type", sa.String(length=40), nullable=False),
        sa.Column("threat_summary", sa.Text(), nullable=False),
        sa.Column("evidence_quality", sa.String(length=20), nullable=False),
        sa.Column("assessment_input_hash", sa.String(length=64), nullable=False),
        sa.Column("engine_version", sa.String(length=50), nullable=False),
        sa.Column("methodology_version", sa.String(length=50), nullable=False),
        sa.Column(
            "policy_snapshot",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "limitations",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 1000)", name="chk_risk_score_range"
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["cryptographic_assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_assessments_asset_id", "risk_assessments", ["asset_id"])
    op.create_index("ix_risk_assessments_risk_category", "risk_assessments", ["risk_category"])

    # 6. risk_factors
    op.create_table(
        "risk_factors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("risk_assessment_id", sa.Uuid(), nullable=False),
        sa.Column("factor_code", sa.String(length=100), nullable=False),
        sa.Column("dimension", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("contribution", sa.Integer(), nullable=False),
        sa.Column(
            "evidence_refs",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "input_values",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["risk_assessment_id"], ["risk_assessments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_factors_assessment_id", "risk_factors", ["risk_assessment_id"])

    # 7. recommendations
    op.create_table(
        "recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("risk_assessment_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("remediation_category", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column(
            "evidence_refs",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "validation_steps",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("known_limitations", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["cryptographic_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["risk_assessment_id"], ["risk_assessments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recommendations_assessment_id", "recommendations", ["risk_assessment_id"])
    op.create_index("ix_recommendations_asset_id", "recommendations", ["asset_id"])


def downgrade() -> None:
    op.drop_table("recommendations")
    op.drop_table("risk_factors")
    op.drop_table("risk_assessments")
    op.drop_table("asset_relationships")
    op.drop_table("asset_observations")
    op.drop_table("cryptographic_assets")
    op.drop_table("discovery_jobs")
    op.alter_column("observations", "target_id", existing_type=sa.Uuid(), nullable=False)
