# Quantum Flow — Sprint 3 Step 1 Post-Implementation Integrity Audit & Remediation Report
## Database Schema, Referential Integrity & Evidence Retention Review

**Document ID:** QFT-SPRINT-003-AUDIT-01  
**Audit Date:** 2026-11-02  
**Remediation Date:** 2026-11-02  
**Audit Scope:** Sprint 3 Step 1 (Database & Models Implementation)  
**Status:** **REMEDIATED — CORRECTIVE ACTIONS IMPLEMENTED & VERIFIED**  
**Auditor:** Antigravity Engineering Agent  

---

## 1. Executive Summary

This post-implementation integrity audit evaluates the database schema, models, and Alembic migrations created for **Sprint 3 Step 1** (`Assessment` lifecycle orchestration, multi-assessment asset associations, referential integrity, and immutable frozen snapshots).

Following the initial audit verdict (`NOT ACCEPTED`), corrective implementation authorization was issued. All identified integrity gaps, missing database-level constraints, cascade deletion risks, trigger-enforced snapshot immutability, and missing test coverage have been **fully resolved and verified against PostgreSQL 16**.

### Key Remediation Achievements:
1. **New Remediation Migration Created:** Migration `5b3e9f2a1c0d` was created revising `4a2d8e1f9b3c`, strictly preserving migration history without altering applied migrations.
2. **Historical Evidence Retention Enforced:** Foreign keys on `assessment_assets.asset_id` and `assessment_observations.observation_id` were updated from `CASCADE` to `ON DELETE RESTRICT`. Global asset or observation deletions cannot destroy historical assessment inventory.
3. **Composite Risk Evaluation Referential Integrity:** Added unique constraint `uq_risk_assessments_id_assessment_asset` and composite foreign key `fk_assessment_assets_risk_composite` on `assessment_assets(risk_assessment_id, assessment_id, asset_id)` referencing `risk_assessments(id, assessment_id, asset_id)` with `ON DELETE SET NULL (risk_assessment_id)`. Mismatched cross-assessment associations are strictly rejected by PostgreSQL.
4. **Database-Level SQL CHECK Constraints:** Added `chk_assessment_progress_range` (`progress_percent BETWEEN 0 AND 100`) and `chk_assessment_status` enforcing permitted lifecycle states.
5. **Database-Level Snapshot Immutability Trigger:** Created PL/pgSQL function and trigger `trg_protect_terminal_assessment_snapshot` on `assessments`. Rejects any update to `report_snapshot` or `report_snapshot_hash` once an assessment enters terminal status (`completed`, `partially_completed`, `failed`, `cancelled`).
6. **Dedicated Test Suites on PostgreSQL 16:** Implemented 13 unit tests in `tests/unit/test_assessment_models.py` and a full populated database upgrade/downgrade integration test in `tests/integration/test_migration_safety.py`. All 112 project tests pass (100% green).

---

## 2. File-by-File Implementation Verification

### 2.1 `services/api/app/db/models/assessment.py`
* **Lifecycle & Stages:** `AssessmentStatus` (`pending`, `queued`, `running`, `completed`, `partially_completed`, `failed`, `cancelled`) and `AssessmentStage`.
* **Resilience:** `target_snapshot: JSONB` captures target identity metadata independently of `target_id`.
* **Duplicate Prevention:** Partial unique index `uq_assessments_active_target_scope` on `(target_id, scope_hash)` for active states (`pending`, `queued`, `running`). Allows parallel active assessments with differing scope hashes.
* **Constraints:** Added `CheckConstraint("progress_percent >= 0 AND progress_percent <= 100", name="chk_assessment_progress_range")` and `CheckConstraint(...)` for status values.
* **Trigger:** Backed by database trigger `trg_protect_terminal_assessment_snapshot`.

### 2.2 `services/api/app/db/models/assessment_asset.py`
* **Composite Primary Key:** `(assessment_id, asset_id)`.
* **Historical Evidence Retention:** `asset_id` foreign key configured with `ondelete="RESTRICT"`.
* **Composite Referential Integrity:** Configured composite foreign key `fk_assessment_assets_risk_composite` referencing `risk_assessments(id, assessment_id, asset_id)` with `ondelete="SET NULL"`.
* **ORM Relationships:** `risk_assessment` mapped with `overlaps="assessment,assessment_assets,asset,assessment_associations"` and `foreign_keys=[risk_assessment_id, assessment_id, asset_id]`. Clean mapper configuration with zero warnings.

### 2.3 `services/api/app/db/models/assessment_observation.py`
* **Composite Primary Key:** `(assessment_id, observation_id)`.
* **Historical Evidence Retention:** `observation_id` foreign key configured with `ondelete="RESTRICT"`.

### 2.4 `services/api/app/db/models/cryptographic_asset.py`
* **Relationship Safety:** Removed `cascade="all, delete-orphan"` from `assessment_associations` and configured `passive_deletes=True`. Prevents ORM from blanking primary key columns or bypassing database `RESTRICT` enforcement.

### 2.5 `services/api/app/db/models/risk_assessment.py`
* **Integrity:** `UniqueConstraint("id", "assessment_id", "asset_id", name="uq_risk_assessments_id_assessment_asset")` added alongside `uq_risk_assessment_run_asset`. Standalone risk assessments (`assessment_id IS NULL`) remain fully supported.

### 2.6 `packages/scanner/safety/canonical.py`
* **Canonical Scope Hashing:** Added `compute_canonical_scope_hash(target_id, discovery_sources, port, repo_locator, repo_ref, config_type, extra_params)` using RFC 8785-aligned canonical JSON serialization and SHA-256.

### 2.7 Alembic Migrations
* `4a2d8e1f9b3c_create_assessments_and_association_.py`: Base Step 1 tables and columns (unchanged).
* `5b3e9f2a1c0d_correct_assessment_integrity_and_triggers.py`: Applied and verified remediation migration. Implements `RESTRICT` FKs, composite risk FK, CHECK constraints, and immutability trigger with symmetric upgrade/downgrade paths.

---

## 3. Database Integrity Matrix (10 Critical Areas) — Post-Remediation

| # | Integrity Area | Implementation Location | Database Mechanism | Application Mechanism | Post-Remediation Status |
|---|---|---|---|---|---|
| **1** | **Composite Risk Assessment Consistency** | `models/assessment_asset.py`<br/>`models/risk_assessment.py`<br/>Migration `5b3e9f2a1c0d` | `fk_assessment_assets_risk_composite` referencing `(id, assessment_id, asset_id)` | ORM composite foreign keys with overlap suppression | **PASS** |
| **2** | **Historical Evidence Deletion Protection** | `models/assessment_asset.py`<br/>`models/assessment_observation.py`<br/>Migration `5b3e9f2a1c0d` | `ON DELETE RESTRICT` on `asset_id` and `observation_id` | `passive_deletes=True` on `CryptographicAsset` | **PASS** |
| **3** | **Terminal Snapshot Immutability** | Migration `5b3e9f2a1c0d`<br/>`assessments` trigger | PL/pgSQL `trg_protect_terminal_assessment_snapshot` | `is_terminal()` guards | **PASS** |
| **4** | **Canonical SHA-256 Digest** | `packages/scanner/safety/canonical.py` | SHA-256 hash columns | RFC 8785 deterministic serialization | **PASS** |
| **5** | **Atomic Snapshot Persistence** | `models/assessment.py` | Single row transactional UPDATE | Atomic service persistence | **PASS** |
| **6** | **Concurrent First-Seen Tracking** | `models/assessment_asset.py` | `first_seen_in_assessment: Boolean` | `SELECT FOR UPDATE` correlation lock | **PASS** |
| **7** | **Scope Hash Coverage** | `packages/scanner/safety/canonical.py`<br/>`models/assessment.py` | `uq_assessments_active_target_scope` partial unique index | Granular canonical digest (sources, port, repo, config) | **PASS** |
| **8** | **Retry Provenance Tracking** | `models/assessment.py` | `collector_results: JSONB`, `retry_count: Integer` | Append-only attempt log schema | **PASS** |
| **9** | **Target Deletion Preservation** | `models/assessment.py` | `ForeignKey(ondelete="SET NULL")` + `target_snapshot` | Retains full target metadata on target deletion | **PASS** |
| **10** | **Status & Progress Constraints** | `models/assessment.py`<br/>Migration `5b3e9f2a1c0d` | `chk_assessment_progress_range`<br/>`chk_assessment_status` | Python `AssessmentStatus` enum validation | **PASS** |

---

## 4. Corrective Finding Resolutions

### [AUDIT-HIGH-01] Relational Cascade Deletion Destroys Historical Assessment Associations — **RESOLVED**
* **Root Cause:** Foreign keys used `ON DELETE CASCADE`.
* **Resolution:** Migration `5b3e9f2a1c0d` dropped cascade constraints and created `fk_assessment_assets_asset_id_restrict` and `fk_assessment_observations_observation_id_restrict` with `ON DELETE RESTRICT`. `CryptographicAsset.assessment_associations` updated with `passive_deletes=True`.
* **Verification:** `test_asset_deletion_restricted_when_in_assessment` and `test_observation_deletion_restricted_when_in_assessment` verify that deleting referenced assets or observations is rejected with `IntegrityError` (code 23503).

### [AUDIT-HIGH-02] Composite Foreign Key Missing on `assessment_assets` — **RESOLVED**
* **Root Cause:** `assessment_assets.risk_assessment_id` pointed to `risk_assessments.id` via a scalar foreign key, permitting cross-assessment mismatches.
* **Resolution:** Migration `5b3e9f2a1c0d` added `UniqueConstraint("id", "assessment_id", "asset_id")` on `risk_assessments` and composite foreign key `fk_assessment_assets_risk_composite` on `assessment_assets(risk_assessment_id, assessment_id, asset_id)` with `ON DELETE SET NULL (risk_assessment_id)`.
* **Verification:** `test_cross_assessment_risk_association_rejected_by_composite_fk` confirms that linking a risk evaluation from Assessment A1 to an asset in Assessment A2 is rejected with `IntegrityError`.

### [AUDIT-MED-01] Missing Database-Level Immutability Protection for Terminal Snapshots — **RESOLVED**
* **Root Cause:** Snapshot immutability relied solely on application code.
* **Resolution:** Migration `5b3e9f2a1c0d` installed trigger `trg_protect_terminal_assessment_snapshot`. When `OLD.status IN ('completed', 'partially_completed', 'failed', 'cancelled')` and `OLD.report_snapshot_hash IS NOT NULL`, any modification to `report_snapshot` or `report_snapshot_hash` raises a PL/pgSQL exception. Initial setting on transition to terminal status is permitted.
* **Verification:** `test_terminal_snapshot_modification_rejected_by_trigger` confirms direct SQL updates to frozen snapshots and hashes are blocked, while `test_updating_non_snapshot_fields_on_terminal_assessment_permitted` verifies non-snapshot operational fields remain updateable.

### [AUDIT-MED-02] Missing SQL CHECK Constraints for Status and Progress — **RESOLVED**
* **Root Cause:** No database-level validation of status strings or progress range.
* **Resolution:** Migration `5b3e9f2a1c0d` added check constraints `chk_assessment_progress_range` and `chk_assessment_status`.
* **Verification:** `test_invalid_status_rejected_by_check_constraint`, `test_negative_progress_percent_rejected`, and `test_excessive_progress_percent_rejected` verify constraint enforcement.

### [AUDIT-MED-03] Coarse Scope Hash Definition — **RESOLVED**
* **Root Cause:** Scope hash was not formally defined with granular parameters.
* **Resolution:** Implemented `compute_canonical_scope_hash` incorporating target ID, sorted discovery sources, target port, repository locator, repository ref, configuration type, and custom parameters.
* **Verification:** `test_canonical_scope_hash_properties` and `test_parallel_active_assessments_with_different_scopes_allowed` verify deterministic behavior and parallel execution support.

### [AUDIT-LOW-01] Zero Automated Tests for Sprint 3 Step 1 Entities — **RESOLVED**
* **Resolution:** Implemented `tests/unit/test_assessment_models.py` (13 tests) and `tests/integration/test_migration_safety.py` (1 integration test covering populated legacy downgrade/upgrade).
* **Verification:** All 14 new tests execute against PostgreSQL 16 container and pass.

---

## 5. Verification Test Suite Summary

* **Unit Tests (`tests/unit/test_assessment_models.py`):** 13 passed in 2.60s.
  * Valid assessment creation and state transitions.
  * Invalid status rejected by database constraint.
  * Negative progress percent rejected by database constraint.
  * Excessive progress percent rejected by database constraint.
  * Cross-assessment risk association rejected by composite FK.
  * Asset deletion restricted when in assessment (RESTRICT).
  * Observation deletion restricted when in assessment (RESTRICT).
  * Target deletion leaves assessment intact with target_id=NULL and target_snapshot preserved.
  * Duplicate active assessment rejected by partial unique index.
  * Parallel active assessments with different scopes allowed.
  * Terminal snapshot modification rejected by trigger.
  * Updating non-snapshot fields on terminal assessment permitted.
  * Canonical scope hash deterministic properties.
* **Integration Tests (`tests/integration/test_migration_safety.py`):** 1 passed in 9.17s.
  * Pre-populates Sprint 1 target, scan, observations.
  * Pre-populates Sprint 2 CBOM assets and standalone risk assessment (`assessment_id=NULL`).
  * Executes downgrade to `4a2d8e1f9b3c` on populated data and verifies data retention.
  * Executes re-upgrade to `5b3e9f2a1c0d` (head) and verifies data retention and relationship integrity.
  * Verifies new Sprint 3 assessment associations link to legacy entities cleanly.
* **Full Python Test Suite:** 112 passed in 14.85s (100% green).
* **Code Quality:** `ruff check` (clean), `ruff format` (clean), `mypy` (clean across 111 source files).
* **Frontend Quality:** `typecheck:web` (0 errors), `lint:web` (0 warnings), `test:web` (10 passed), `build:web` (production bundle built cleanly).

---

## 6. Final Recommendation

**Verdict:** **STEP 1 REMEDIATION ACCEPTED AND COMPLETE**  
**Readiness:** The database schema, referential integrity rules, cascade protections, PostgreSQL trigger, and regression test suites are fully hardened, verified, and ready.  
**Next Step:** Submit report for explicit user review and approval before proceeding to Sprint 3 Step 2 (`AssessmentOrchestrator`).
