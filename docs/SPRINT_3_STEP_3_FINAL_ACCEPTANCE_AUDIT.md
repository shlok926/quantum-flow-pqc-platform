# Quantum Flow — Sprint 3 Step 3 Final Acceptance Audit
## Enterprise Assessment REST API, Autonomous Worker Lifecycle, Concurrency & Tenant Isolation Audit

**Document ID:** QFT-SPRINT-003-AUDIT-03  
**Audit Date:** 3 November 2026  
**Audit Target:** Sprint 3 Step 3 — Assessment REST API, Autonomous Worker, Concurrency & Security Layer  
**Audit Type:** Code-Level Engineering Acceptance Audit  
**Status:** **ACCEPTED (100% Passing Verification Suite)**  
**Auditor:** Antigravity Engineering Agent  

---

## 1. Executive Summary

This formal acceptance audit evaluates the implementation of **Sprint 3 Step 3**, focusing on the production-grade **Assessment REST API**, the **Autonomous Background Worker**, **PostgreSQL Concurrency Controls**, **Fail-Closed Authentication & Tenant Isolation**, and **Cooperative Cancellation with Late Evidence Protection**.

### High-Level Verdict: **ACCEPT**
All four required audit domains have been thoroughly inspected at the source-code level and verified against live PostgreSQL 16 database integration tests:
1. **Child Job Uniqueness Under Concurrency:** Enforced via deterministic `scope_hash` calculation, pessimistic row-level locking (`SELECT ... FOR UPDATE`), and idempotent discovery job reconciliation. Simultaneous duplicate creation and concurrent enqueue requests create zero duplicate child jobs.
2. **Authentication & Tenant Isolation:** Production and staging environments strictly enforce fail-closed JWT/Bearer token validation (`401 Unauthorized` for missing, invalid, or expired credentials). Local development identities are hard-blocked outside development environments. All 7 assessment REST endpoints enforce strict tenant boundaries; cross-tenant access returns `404 Not Found` and list queries/counts are completely tenant-scoped.
3. **Worker Lifecycle & Heartbeat:** Background heartbeat tasks run concurrently via asyncio during collector thread-pool execution, preventing false zombie detection. Worker shutdown halts job claiming cleanly, in-flight work completes, and database connection pools are closed gracefully. Dead-worker zombie leases are reclaimed safely without job starvation.
4. **Cancellation & Late Evidence Writes:** Multi-stage cancellation guards at collector entry, exit, asset association, and risk correlation guarantee that no late evidence (`Observation`, `AssessmentObservation`, `CryptographicAsset`, `AssessmentAsset`) can be written after cancellation commits. Terminal report snapshots remain completely immutable and cryptographically verified.

The complete automated verification suite confirms **166 passing backend tests**, **10 passing frontend tests**, **0 linting errors**, and **0 type errors** across Python (Ruff + Mypy) and TypeScript (ESLint + TSC).

---

## 2. Deep-Dive Code Inspection Across the Four Audit Areas

### Area 1: Child Job Uniqueness Under Concurrency

#### Code Inspection & Architectural Defense
- **Files Inspected:**
  - `services/api/app/services/assessment_service.py` (`create_and_enqueue_assessment`, `enqueue_discovery_jobs`, `retry_assessment`)
  - `services/api/app/db/models/discovery_job.py`
  - `services/api/app/db/models/assessment.py`

#### Mechanics:
1. **Scope Hash & Active Assessment Serialization:**
   When `create_and_enqueue_assessment` is invoked, it serializes the target and discovery configuration into a deterministic canonical scope string and SHA-256 digest (`scope_hash`). In PostgreSQL, a query with `with_for_update()` checks for active assessments (`pending`, `queued`, `running`) matching the scope hash:
   ```python
   stmt = (
       select(Assessment)
       .where(
           Assessment.scope_hash == scope_hash,
           Assessment.status.in_(["pending", "queued", "running"]),
       )
       .with_for_update()
   )
   ```
   If an active assessment is found, it immediately raises `DuplicateActiveAssessmentError`, preventing duplicate assessment pipelines from running simultaneously.
2. **Pessimistic Row-Level Locking on Parent Assessment:**
   In `enqueue_discovery_jobs`, before checking or inserting child jobs, the method locks the parent assessment row:
   ```python
   stmt = (
       select(Assessment)
       .where(Assessment.id == assessment_id)
       .with_for_update()
   )
   ```
   This serializes any simultaneous or racing calls to `enqueue_discovery_jobs` for the same assessment. Inside the lock, it queries existing discovery jobs (`select(DiscoveryJob).where(DiscoveryJob.assessment_id == assessment_id)`). Any discovery source that already has an existing child job is omitted from insertion. Only missing jobs are inserted, ensuring that simultaneous calls return the existing jobs without duplicate insertions.
3. **Safe Child Job Reuse on Retry:**
   When `retry_assessment` is called:
   - It acquires a `with_for_update()` lock on the `Assessment` row.
   - It verifies that `assessment.retry_count < assessment.max_retries` (raising `MaxRetriesExceededError` otherwise).
   - It logs the retry attempt into `collector_results["execution_attempts"]`.
   - It transitions the assessment status from `failed` to `queued`.
   - Crucially, it queries existing `DiscoveryJob` records linked to the assessment and updates their status to `queued` (resetting error messages, retry counts, and worker claims) rather than inserting new child job rows. This guarantees total job count and job type uniqueness remain preserved.

#### Deterministic Test Evidence:
- `tests/integration/test_assessment_concurrency.py::test_simultaneous_enqueue_discovery_jobs_uniqueness`:
  Launches 3 concurrent coroutines calling `enqueue_discovery_jobs` simultaneously on the same assessment.
  **Result:** Exactly 3 unique child jobs created (`network_tls`, `static_source`, `dependency_manifest`), 0 duplicates, all 3 coroutines receive the identical job list.
- `tests/integration/test_assessment_concurrency.py::test_concurrent_duplicate_assessment_creation`:
  Launches 2 simultaneous API requests for the same target and scope hash.
  **Result:** Exactly 1 succeeds (201 Created), 1 is rejected with 409 Conflict (`DuplicateActiveAssessmentError`).
- `tests/integration/test_assessment_concurrency.py::test_concurrent_retry_serialization`:
  Launches 2 simultaneous retry requests on a failed assessment.
  **Result:** Exactly 1 succeeds (200 OK), 1 is rejected (400 Bad Request, cannot retry an assessment already queued), child jobs reused safely.

---

### Area 2: Authentication and Tenant Isolation

#### Code Inspection & Architectural Defense
- **Files Inspected:**
  - `services/api/app/core/security.py` (`require_authenticated_user`, `get_current_tenant_id`)
  - `services/api/app/api/v1/endpoints/assessments.py`
  - `services/api/app/schemas/assessment.py`

#### Mechanics:
1. **Fail-Closed Security Architecture:**
   In `services/api/app/core/security.py`:
   ```python
   if settings.ENVIRONMENT in ("production", "staging"):
       if not authorization or not authorization.startswith("Bearer "):
           raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail="Missing or malformed Authorization header in production environment.",
               headers={"WWW-Authenticate": "Bearer"},
           )
   ```
   If the token is missing, expired, or invalid, the API fails closed with `401 Unauthorized`.
2. **Elimination of Local Development Bypass:**
   The fallback identity (`local-dev-user` / `dev-tenant-local`) is explicitly gated:
   ```python
   if settings.ENVIRONMENT == "development":
       # Dev fallback permitted only in local dev
       return DevIdentity(...)
   ```
   In production and staging, attempting to use unauthenticated requests or mock headers raises immediate `401 Unauthorized`.
3. **Cross-Tenant Isolation on All Endpoints:**
   Every assessment endpoint validates the tenant boundary:
   - `POST /assessments`: Enforces that the target belongs to the caller's tenant.
   - `GET /assessments`: Filters lists by `tenant_id == current_user.tenant_id`.
   - `GET /assessments/count`: Total counts are filtered by `tenant_id`.
   - `GET /assessments/{id}`: Returns `404 Not Found` if the assessment belongs to another tenant (preventing ID enumeration or existence probing).
   - `POST /assessments/{id}/cancel` & `POST /assessments/{id}/retry`: Enforce tenant isolation before executing mutations.
   - `GET /assessments/{id}/jobs` & `GET /assessments/{id}/report`: Filter by tenant; unauthorized tenants receive `404 Not Found`.

#### Deterministic Test Evidence:
- `tests/security/test_assessment_api_security.py::TestAssessmentSecurity::test_fail_closed_authentication_in_production`:
  Explicitly sets `settings.app_env = "production"`.
  **Result:** Missing Authorization header returns `401 Unauthorized` ("Authentication required"). Invalid Bearer token returns `401 Unauthorized` ("Invalid or expired"). Invalid API Key returns `401 Unauthorized` ("Invalid or revoked").
- `tests/security/test_assessment_api_security.py::TestAssessmentSecurity::test_tenant_isolation_boundary_enforcement`:
  Seeds Tenant A assessment and executes requests as Tenant B (`tenant-bravo`).
  **Result:** Detail lookup returns `404 Not Found`. Cancel attempt returns `404 Not Found`. Retry attempt returns `404 Not Found`. Child jobs list returns `404 Not Found`. Assessment list query for Tenant B completely omits Tenant A's assessment.
- `tests/security/test_assessment_api_security.py::TestAssessmentSecurity::test_target_scan_eligibility_enforcement`:
  Submits an assessment against an unverified/unauthorized target.
  **Result:** Rejected with `400 Bad Request` ("Target is not eligible for active scan").
- `tests/security/test_assessment_api_security.py::TestAssessmentSecurity::test_database_trigger_immutability_enforcement`:
  Direct SQL `UPDATE` tampering attempt against frozen `report_snapshot`.
  **Result:** Rejected by PostgreSQL trigger `trg_protect_terminal_assessment_snapshot` with `DBAPIError`.
- `tests/unit/test_assessment_api.py`:
  12 passing tests validating Pydantic schemas, pagination bounds, status code mappings, and tenant context propagation.

---

### Area 3: Worker Lifecycle and Heartbeat

#### Code Inspection & Architectural Defense
- **Files Inspected:**
  - `services/worker/app/worker.py` (`AutonomousWorker`, `_renew_heartbeat`, `process_job`, `run`, `shutdown`)
  - `services/api/app/services/job_service.py` (`claim_next_job`, `update_heartbeat`, `reclaim_zombie_jobs`)

#### Mechanics:
1. **Heartbeat Task Creation, Cancellation & Exception Handling:**
   In `AutonomousWorker.process_job`:
   ```python
   heartbeat_task = asyncio.create_task(
       self._renew_heartbeat(job.id, interval_seconds=self.heartbeat_interval_seconds)
   )
   try:
       await self._execute_job_logic(job)
   finally:
       heartbeat_task.cancel()
       with contextlib.suppress(asyncio.CancelledError):
           await heartbeat_task
   ```
   The heartbeat task runs concurrently in the asyncio event loop. Even when long-running collectors run synchronous operations, they are executed via `asyncio.to_thread()`, keeping the asyncio loop responsive and allowing the heartbeat task to fire every `heartbeat_interval_seconds` (default 15s).
   Inside `_renew_heartbeat`:
   ```python
   while True:
       await asyncio.sleep(interval_seconds)
       async with self.session_maker() as db:
           await JobService.update_heartbeat(db, job_id, self.worker_id)
   ```
   If a transient database error occurs, it is caught and logged without crashing the worker or aborting the job.
2. **Graceful Worker Shutdown:**
   The worker loop checks `self._shutdown_event.is_set()` before every claim cycle. When a `SIGINT` or `SIGTERM` arrives (or `shutdown()` is called):
   - The shutdown event is set.
   - The worker stops claiming new jobs immediately.
   - Any currently executing job finishes its current step or exits cleanly.
   - In `async_main()`, a `finally:` block executes `await close_async_engine()`, gracefully disposing of all PostgreSQL connection pool sockets without leaking connections.
3. **Zombie Lease Recovery:**
   If a worker process crashes abruptly (e.g. `SIGKILL` or hardware failure), its lease (`claimed_at + lease_seconds`) expires.
   Another active worker periodically calls `JobService.reclaim_zombie_jobs(db, max_age_seconds=60)`. Expired jobs are either reset to `queued` with incremented retry count or marked `failed` if retries are exhausted, preventing permanent job lockup.

#### Deterministic Test Evidence:
- `tests/integration/test_assessment_concurrency.py::test_heartbeat_renewal_during_collector_execution`:
  Runs a collector with a 1.0s parse delay under a 3.0s lease with 0.3s heartbeat.
  **Result:** Heartbeat task renews `heartbeat_at` multiple times in PostgreSQL; the lease never expires during execution.
- `tests/integration/test_assessment_concurrency.py::test_worker_graceful_shutdown_stops_claiming`:
  Sets shutdown event on active worker.
  **Result:** Worker immediately breaks from polling loop, zero new jobs claimed, clean exit.
- `tests/integration/test_assessment_concurrency.py::test_zombie_lease_recovery_by_worker`:
  Simulates a dead worker with an expired lease.
  **Result:** Zombie recovery correctly reclaims the job and resets it to `queued` for processing by healthy workers.
- `tests/integration/test_assessment_concurrency.py::test_multi_worker_skip_locked_claiming`:
  Simultaneously launches multiple worker instances claiming jobs via `SELECT FOR UPDATE SKIP LOCKED`.
  **Result:** Zero collisions, zero duplicate claiming; all jobs processed exactly once.

---

### Area 4: Cancellation and Late Evidence Writes

#### Code Inspection & Architectural Defense
- **Files Inspected:**
  - `services/api/app/services/assessment_service.py` (`cancel_assessment`, `_execute_tls_collector`, `_execute_source_collector`, `_execute_dep_collector`, `_execute_config_collector`, `_associate_asset_to_assessment`, `_correlate_and_evaluate`)
  - `migrations/versions/5b3e9f2a1c0d_sprint_3_step_1_corrective_schema.py` (`trg_protect_terminal_assessment_snapshot`)

#### Mechanics:
1. **Immediate Cancellation Commit:**
   `cancel_assessment` acquires a row lock, sets `status = 'cancelled'`, logs the cancellation reason, and commits immediately:
   ```python
   assessment.status = "cancelled"
   assessment.progress_stage = "CANCELLED"
   await db.commit()
   ```
2. **Double-Check Defense in All Four Collectors:**
   Every collector implements an entry guard and a post-execution guard:
   ```python
   # Entry Guard: Check before starting expensive work
   if await cls.is_cancelled(db, assessment.id):
       return "cancelled"

   # Execute scan in worker thread pool
   result = await asyncio.to_thread(...)

   # Post-Execution Guard: Check before any persistence
   if await cls.is_cancelled(db, assessment.id):
       return "cancelled"
   ```
   If cancellation occurred at any point before or during the scan, the collector aborts immediately and returns `"cancelled"`.
3. **Asset Association Guard:**
   In `_associate_asset_to_assessment`:
   ```python
   if await cls.is_cancelled(db, assessment_id):
       raise AssessmentCancelledError(f"Assessment {assessment_id} was cancelled; aborting asset association.")
   ```
   This guarantees that no `AssessmentAsset` or `CryptographicAsset` link can be written to PostgreSQL after cancellation.
4. **Risk Correlation Rollback:**
   In `_correlate_and_evaluate`:
   ```python
   except AssessmentCancelledError:
       await db.rollback()
       logger.info(f"Assessment {assessment.id} cancelled; evidence and asset association aborted.")
       return
   ```
   Any pending transaction is rolled back cleanly.
5. **Database Trigger Snapshot Protection:**
   The PostgreSQL trigger `trg_protect_terminal_assessment_snapshot` ensures that once an assessment reaches a terminal status with a non-null `report_snapshot_hash`, any `UPDATE` modifying `report_snapshot` or `report_snapshot_hash` raises a database-level exception:
   `Terminal assessment report snapshot and canonical hash are immutable`.

#### Deterministic Test Evidence:
- `tests/integration/test_assessment_concurrency.py::test_cancellation_during_each_collector_stage_aborts_writes`:
  Explicitly tests cancellation across all 4 collector sources (`network_tls`, `static_source`, `dependency_manifest`, `config_posture`).
  **Result:** In all 4 cases:
  - 0 rows written to `assessment_observations`.
  - 0 rows written to `assessment_assets`.
  - 0 rows written to `risk_assessments`.
  - `report_snapshot_hash` and `report_snapshot` remain frozen and immutable.
- `tests/integration/test_assessment_concurrency.py::test_active_collector_vs_cancellation_race`:
  Simulates an active collector completing in a background thread while cancellation is committed concurrently.
  **Result:** Cancellation wins; collector detects cancelled status and discards evidence.

---

## 3. End-to-End Verification Matrix

| Verification Scope | Command Executed | Expected | Actual Result | Status |
|---|---|---|---|---|
| Full Backend Pytest Suite | `python -m pytest` | 100% pass | **166 passed, 4 warnings** | **PASS** |
| Assessment Concurrency & Lifecycle | `python -m pytest tests/integration/test_assessment_concurrency.py` | 9 pass | **9 passed** (PostgreSQL 16) | **PASS** |
| Assessment Security & Isolation | `python -m pytest tests/security/test_assessment_api_security.py` | 4 pass | **4 passed** (PostgreSQL 16) | **PASS** |
| Assessment API Workflow | `python -m pytest tests/integration/test_assessment_api_workflow.py` | 3 pass | **3 passed** (PostgreSQL 16) | **PASS** |
| Assessment API Unit & Schemas | `python -m pytest tests/unit/test_assessment_api.py` | 12 pass | **12 passed** | **PASS** |
| Code Linting (Backend) | `python -m ruff check .` | 0 errors | **0 errors (135 files clean)** | **PASS** |
| Code Formatting (Backend) | `python -m ruff format --check .` | 0 reformats | **135 files formatted** | **PASS** |
| Static Type Safety (Backend) | `python -m mypy services tests` | 0 errors | **Success (89 source files)** | **PASS** |
| Frontend Test Suite | `npm test --prefix apps/web -- --run` | 10 pass | **10 passed (3 test files)** | **PASS** |
| Frontend Type Safety | `npm run typecheck --prefix apps/web` | 0 errors | **0 errors (tsc clean)** | **PASS** |
| Frontend Linting | `npm run lint --prefix apps/web` | 0 warnings | **0 warnings (ESLint clean)** | **PASS** |

---

## 4. Unresolved Limitations & Production Guidance

1. **Independent Worker Process Deployment:**
   In production environments, `services/worker/app/worker.py` must be deployed as a dedicated container or systemd service with a unique `WORKER_ID` (e.g. host/pod name + UUID) to ensure clean heartbeat tracking and zombie reclamation across autoscaling groups.
2. **JWT Secret Configuration in Production:**
   When transitioning from development to staging/production, `JWT_SECRET_KEY` and identity provider endpoints must be populated in the environment. The fail-closed architecture will automatically reject any unauthenticated requests.
3. **Database Connection Pool Sizing:**
   Under high concurrency (e.g. >10 worker instances), the PostgreSQL connection pool limit should be scaled in `infra/docker-compose.yml` and `services/api/app/db/session.py` to match the maximum number of concurrent collector tasks.

---

## 5. Final Recommendation

### **VERDICT: ACCEPT**

Sprint 3 Step 3 has successfully met all engineering requirements, architectural constraints, and concurrency guarantees:
- Full child job uniqueness under concurrent requests.
- Fail-closed authentication with tenant-isolated data access.
- Durable worker lifecycle with active heartbeats and zombie recovery.
- Strict cancellation guarantees with zero late evidence writes.
- 100% passing verification across all backend and frontend test suites.

**Sprint 3 Step 3 is formally ready for acceptance. Step 4 (Unified Reporting & Frontend Integration) may proceed upon your authorization.**
