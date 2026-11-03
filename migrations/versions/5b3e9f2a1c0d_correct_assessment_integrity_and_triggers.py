"""correct_assessment_integrity_and_triggers

Revision ID: 5b3e9f2a1c0d
Revises: 4a2d8e1f9b3c
Create Date: 2026-11-02 14:35:00.000000+00:00
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5b3e9f2a1c0d"
down_revision: str | None = "4a2d8e1f9b3c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Historical Evidence Retention: change asset_id in assessment_assets from CASCADE to RESTRICT
    op.drop_constraint("assessment_assets_asset_id_fkey", "assessment_assets", type_="foreignkey")
    op.create_foreign_key(
        "fk_assessment_assets_asset_id_restrict",
        "assessment_assets",
        "cryptographic_assets",
        ["asset_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # 2. Historical Evidence Retention: change observation_id in assessment_observations from CASCADE to RESTRICT
    op.drop_constraint(
        "assessment_observations_observation_id_fkey",
        "assessment_observations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_assessment_observations_observation_id_restrict",
        "assessment_observations",
        "observations",
        ["observation_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # 3. Composite Risk Evaluation Referential Integrity
    # Add unique constraint on (id, assessment_id, asset_id) in risk_assessments
    op.create_unique_constraint(
        "uq_risk_assessments_id_assessment_asset",
        "risk_assessments",
        ["id", "assessment_id", "asset_id"],
    )

    # Drop old scalar FK on assessment_assets
    op.drop_constraint(
        "assessment_assets_risk_assessment_id_fkey",
        "assessment_assets",
        type_="foreignkey",
    )

    # Add composite foreign key linking (risk_assessment_id, assessment_id, asset_id) to risk_assessments
    if is_postgres:
        op.execute("""
            ALTER TABLE assessment_assets
            ADD CONSTRAINT fk_assessment_assets_risk_composite
            FOREIGN KEY (risk_assessment_id, assessment_id, asset_id)
            REFERENCES risk_assessments(id, assessment_id, asset_id)
            ON DELETE SET NULL (risk_assessment_id);
        """)
    else:
        with op.batch_alter_table("assessment_assets") as batch_op:
            batch_op.create_foreign_key(
                "fk_assessment_assets_risk_composite",
                "risk_assessments",
                ["risk_assessment_id", "assessment_id", "asset_id"],
                ["id", "assessment_id", "asset_id"],
                ondelete="SET NULL",
            )

    # 4. Status & Progress Range CHECK Constraints
    op.create_check_constraint(
        "chk_assessment_progress_range",
        "assessments",
        "progress_percent >= 0 AND progress_percent <= 100",
    )
    op.create_check_constraint(
        "chk_assessment_status",
        "assessments",
        "status IN ('pending', 'queued', 'running', 'completed', 'partially_completed', 'failed', 'cancelled')",
    )

    # 5. Terminal Snapshot Immutability PostgreSQL Trigger
    if is_postgres:
        op.execute("""
        CREATE OR REPLACE FUNCTION trg_fn_protect_terminal_assessment_snapshot()
        RETURNS TRIGGER AS $$
        BEGIN
            -- If the row was already terminal AND had a frozen snapshot hash, reject mutations to snapshot or hash
            IF OLD.status IN ('completed', 'partially_completed', 'failed', 'cancelled')
               AND OLD.report_snapshot_hash IS NOT NULL THEN
                IF (NEW.report_snapshot IS DISTINCT FROM OLD.report_snapshot) OR
                   (NEW.report_snapshot_hash IS DISTINCT FROM OLD.report_snapshot_hash) THEN
                    RAISE EXCEPTION 'Terminal assessment report snapshot and canonical hash are immutable (assessment_id: %)', OLD.id;
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS trg_protect_terminal_assessment_snapshot ON assessments;
        CREATE TRIGGER trg_protect_terminal_assessment_snapshot
        BEFORE UPDATE ON assessments
        FOR EACH ROW
        EXECUTE FUNCTION trg_fn_protect_terminal_assessment_snapshot();
        """)


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Drop snapshot immutability trigger & function
    if is_postgres:
        op.execute(
            "DROP TRIGGER IF EXISTS trg_protect_terminal_assessment_snapshot ON assessments;"
        )
        op.execute("DROP FUNCTION IF EXISTS trg_fn_protect_terminal_assessment_snapshot();")

    # 2. Drop CHECK constraints on assessments
    op.drop_constraint("chk_assessment_status", "assessments", type_="check")
    op.drop_constraint("chk_assessment_progress_range", "assessments", type_="check")

    # 3. Revert composite FK on assessment_assets
    if is_postgres:
        op.execute(
            "ALTER TABLE assessment_assets DROP CONSTRAINT IF EXISTS fk_assessment_assets_risk_composite;"
        )
    else:
        with op.batch_alter_table("assessment_assets") as batch_op:
            batch_op.drop_constraint("fk_assessment_assets_risk_composite", type_="foreignkey")

    op.create_foreign_key(
        "assessment_assets_risk_assessment_id_fkey",
        "assessment_assets",
        "risk_assessments",
        ["risk_assessment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint(
        "uq_risk_assessments_id_assessment_asset",
        "risk_assessments",
        type_="unique",
    )

    # 4. Revert observation_id in assessment_observations back to CASCADE
    op.drop_constraint(
        "fk_assessment_observations_observation_id_restrict",
        "assessment_observations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "assessment_observations_observation_id_fkey",
        "assessment_observations",
        "observations",
        ["observation_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 5. Revert asset_id in assessment_assets back to CASCADE
    op.drop_constraint(
        "fk_assessment_assets_asset_id_restrict",
        "assessment_assets",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "assessment_assets_asset_id_fkey",
        "assessment_assets",
        "cryptographic_assets",
        ["asset_id"],
        ["id"],
        ondelete="CASCADE",
    )
