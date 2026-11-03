# Quantum Flow — Sprint 3 Step 4, Phase 2 Implementation Plan (Revision 2.1)
## Secure Staged File Uploads, Lifecycle Management & Enterprise Report Delivery

**Document ID:** QFT-SPRINT-003-STEP-4-PHASE-2-PLAN-REV2.1  
**Version:** 2.1 (Final Technical Clarification Revision)  
**Date:** 3 November 2026  
**Status:** Submitted for Final Technical Review & Authorization (Planning Only — No Implementation Until Authorized)  
**Target Milestone:** Sprint 3 Step 4 — Phase 2: Staged Uploads, Storage Architecture & Report Delivery  
**Prerequisites:** Sprint 3 Step 4 Phase 1 (Reporting Engine Exporters) Formally Accepted  

---

## 1. Executive Summary & Purpose

Phase 1 established the core reporting engine (`packages/reports/exporter.py`), delivering schema-validated CycloneDX 1.6 CBOM generation, RFC 4180 CRLF CSV export with spreadsheet formula-injection mitigation, Executive Markdown generation, and RFC 8785 canonical JSON SHA-256 snapshot verification.

**Sprint 3 Step 4, Phase 2 bridges the gap between the core discovery engine, persistent storage, background workers, and external consumers:**
1. **Two-Tier Pre-Parsing Advisory Locks (Cluster Global + Per-Tenant):** In the upload endpoint, tenant identity is resolved from HTTP headers and a two-tier PostgreSQL transaction advisory lock is acquired **before triggering multipart form parsing (`request.form()`)**: Tier 1 acquires one of 10 shared cluster-wide global slots (`qf:global_upload_slot:0..9`), and Tier 2 acquires one of 3 per-tenant slots (`qf:upload_slot:{tenant_id}:0..2`). Both locks remain held across file streaming in a single transaction, enforcing cluster-wide concurrency limits across multiple API containers without database migrations or process-local semaphores.
2. **Short-Lived Atomic Storage Quota Reservation & Active-Slot Guard:** Decouples upload slot concurrency from storage quota checks. A dedicated short-lived transaction mutex (`qf:quota_mutex:{tenant_id}`) checks and atomically reserves staging quotas (including active in-flight uploads and reserved byte allowances via `reservation.json`) in $<5\text{ms}$ without serializing concurrent file transfers. GC preserves in-flight reservations while the corresponding upload-slot advisory lock remains active, protecting slow or high-latency uploads. Atomic file replacement guarantees crash resilience during finalization.
3. **Deployment-Level Request-Body & Temporary Storage Protection:** Combines reverse-proxy ceilings (25MB), custom ASGI middleware enforcing `Content-Length` rejection before parsing and chunked body capping, container `/tmp` `tmpfs` bounding, and destination staging to prevent memory or disk exhaustion.
4. **Canonical Tenant Ownership & Advisory-Lock Binding:** Establishes the authoritative tenant identity from `Assessment.target_snapshot["tenant_id"]`. Transaction-scoped PostgreSQL advisory locks serialize token claims and prevent concurrency races between assessment creation and garbage collection.
5. **Crash Recovery & Reconciliation:** Decouples durable database commits from ephemeral filesystem updates (`metadata.json`). Background workers reconcile metadata lazily upon claiming discovery jobs.
6. **5-State Database Ownership Classification Garbage Collection:** An hourly worker daemon cleans expired unreferenced uploads, preserves active and retryable archives, heals metadata, and preserves archives with ambiguous, missing, or multiple tenant records.
7. **Descriptor-Relative Filesystem TOCTOU & Confinement Deletion:** Implements true no-follow directory descriptor (`dir_fd`) operations with `O_DIRECTORY | O_NOFOLLOW` on POSIX systems, and an explicit, hardened fallback on Windows preventing path traversal, symlink hijacking, and TOCTOU races.
8. **Verified 64-Bit Advisory Locking, Strict Process Containment & Conclusive Whole-Group Quarantine Tracking:** Enforces exclusively created, randomly named scratch directories (`0700` permissions) under an absolute, non-symlink trusted root. The worker acquires a deterministic 64-bit advisory lock on a dedicated pinned connection and verifies ownership via `pg_locks` OID casts (`CAST(:classid AS oid)`, `CAST(:objid AS oid)`, `objsubid=1`). Scratch operations execute under strict OS containment: on Windows, processes are launched in a suspended state (`CREATE_SUSPENDED`), assigned to a Job Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` (with all breakaway flags disabled), and resumed only after assignment succeeds; on POSIX, processes run in dedicated sessions with anti-escape controls and cgroups/namespaces. Descendant termination evaluates all group members using kernel-safe `/proc/*/stat` parsing (splitting strictly after the final closing parenthesis `)` to avoid field shifting from spaces/parentheses in process names) and treats any unread, permission-restricted, or indeterminate entry as a fail-closed trigger that halts cleanup. Multi-factor quarantine descriptors (`.quarantine.json` tracking boot ID, PGID, and process creation times) prevent PID-recycling errors, permanently barring GC deletion until all descendant access is positively and conclusively confirmed dead.
9. **Authenticated Complete HTTP Report Delivery:** Formally documents the in-memory materialization lifecycle of the Phase 1 exporters, delivering verified reports using complete HTTP responses with explicit `Content-Length`, RFC 5987 `Content-Disposition`, and fail-closed cryptographic integrity verification (strictly distinguished from incremental streaming).

> [!IMPORTANT]
> **Strict Engineering Boundaries:**
> - **Zero Database Migrations:** No database tables or schema migrations will be created. All storage and token deduplication map to existing JSONB fields (`target_snapshot->>'upload_token'`, `input_params->>'upload_token'`) and standard PostgreSQL advisory locks (`pg_try_advisory_xact_lock`).
> - **Zero Mathematical Changes:** QVI Methodology v1.0 and CBOM asset identity algorithms remain strictly invariant.
> - **Single-Host Shared Volume Boundary:** Docker named volume storage (`staging_data`) is tailored for single-host deployments. Distributed object storage (S3/GCS) is documented as an architectural evolution path deferred beyond Sprint 3.
> - **Zero Commits & Zero Pushes:** Implementation code will only be executed after formal authorization.

---

## 2. Scope & Non-Goals

### 2.1 In Scope for Phase 2
- Configuration parameters `staging_dir` and `scratch_dir` in `services/api/app/core/config.py`.
- Shared Docker named volume `staging_data` mounted at `/var/lib/quantumflow/staging` in `docker-compose.yml`.
- Pydantic schemas `StagedUploadResponse` and `UploadTokenMetadata` in `services/api/app/schemas/assessment.py`.
- Pure ASGI request-body size limiting middleware (`RequestBodyLimitMiddleware`) in `services/api/app/main.py`.
- Endpoint `POST /api/v1/assessments/stage-upload` accepting raw `Request`, acquiring slot advisory lock before `request.form()`, reserving storage quota atomically, streaming to `.part`, and writing metadata.
- Transaction advisory-lock claim (`pg_try_advisory_xact_lock`) and cross-tenant token collision detection in `AssessmentService.create_and_enqueue_assessment`.
- Lazy metadata reconciliation and read-only archive consumption in `AssessmentService._execute_source_collector` and `_execute_dep_collector`.
- Secure isolated scratch workspace creation (`0700` permissions), descriptor-relative extraction writes, error-logging cleanup (`.cleanup_failed`), and active-lease-aware orphan reclamation in `packages/scanner/source/archive.py`.
- Retry-safe archive preservation and terminal cleanup hook upon assessment completion or retry exhaustion.
- Background worker hourly 5-state database-authoritative Garbage Collection daemon with descriptor-relative (`dir_fd`) POSIX cleanup, safe Windows fallback, and lease-verified scratch reclamation in `services/worker/app/worker.py`.
- Complete HTTP report download endpoints `GET /api/v1/assessments/{id}/reports/cyclonedx`, `csv`, and `markdown` in `services/api/app/api/v1/endpoints/assessments.py`.
- Integration test suites `tests/integration/test_staged_upload.py` and `tests/integration/test_assessment_report_api.py`.

### 2.2 Explicit Non-Goals
- Modifying React frontend components or templates (`apps/web`).
- Implementing application-level HTTP `Idempotency-Key` headers (deferred post-Sprint 3).
- Multi-host distributed object storage drivers (S3, MinIO, GCS).
- Incremental/chunked generator streaming for reports (in-memory materialization satisfies all Sprint 3 bounds).
- Modifying PostgreSQL database tables or generating Alembic migrations.
- Altering QVI Methodology v1.0 scoring formulas or asset-key generation algorithms.

---

## 3. Architecture & Data Flow

```mermaid
flowchart TD
    subgraph Client["API Client / Web UI"]
        C_UP["POST /stage-upload<br/>(Upload ZIP/Manifest)"]
        C_CR["POST /assessments<br/>(title, target_id, upload_token)"]
        C_REP["GET /assessments/{id}/reports/{format}<br/>(Complete HTTP Response Download)"]
    end

    subgraph API["FastAPI Control Plane (services/api)"]
        EP_MW["ASGI Body Limit Middleware<br/>- Checks Content-Length <= 25MB<br/>- Caps chunked transfer stream"]
        EP_STG["stage_upload(request: Request)<br/>1. Resolve tenant from auth header<br/>2. Open DB session; acquire slot lock (0..2)<br/>3. Short-lived quota reservation<br/>4. Call request.form() after lock acquired<br/>5. Stream to .part & write metadata.json<br/>6. Commit tx / auto-release slot lock"]
        EP_ASS["create_assessment()<br/>- In-tx token advisory lock<br/>- Canonical tenant check<br/>- Commit DB transaction<br/>- Post-commit metadata sync"]
        EP_REP["download_report()<br/>- Snapshot hash verify<br/>- In-memory materialization<br/>- Complete HTTP Response"]
    end

    subgraph SharedFS["Shared Staging Volume (/var/lib/quantumflow/staging)"]
        DIR_STG["{STAGING_DIR}/{tenant_id}/{upload_token}/<br/>- source_archive.zip (or manifest)<br/>- reservation.json (in-flight)<br/>- metadata.json (bound/staged)"]
    end

    subgraph DB["PostgreSQL 16 Authoritative Storage"]
        T_ASS[("assessments<br/>target_snapshot->>'upload_token'<br/>target_snapshot->>'tenant_id'")]
        T_JOB[("discovery_jobs<br/>input_params->>'upload_token'")]
        LOCKS["PostgreSQL Transaction Advisory Locks<br/>pg_try_advisory_xact_lock(:key)"]
    end

    subgraph Worker["AutonomousWorker Process (services/worker)"]
        W_CLAIM["Claim DiscoveryJob (SKIP LOCKED)"]
        W_SCRATCH["Create Isolated Scratch (0700)<br/>Job-specific random path"]
        W_READ["Read Staged Archive (Read-Only)<br/>Extract validating bytes written<br/>Descriptor-relative writes"]
        W_HEAL["Lazy Metadata Reconciliation<br/>(Heal metadata.json if null)"]
        W_CLEAN["Terminal Cleanup<br/>(Upon Success or Retry Exhaustion)"]
        W_GC["Hourly Garbage Collector Daemon<br/>- 5-State DB classification<br/>- dir_fd / O_NOFOLLOW deletion<br/>- Active-lease-aware scratch GC"]
    end

    C_UP --> EP_MW
    EP_MW --> EP_STG
    EP_STG -->|1. Acquire Slot Lock (0..2)| LOCKS
    EP_STG -->|2. Short-Lived Quota Mutex| LOCKS
    EP_STG -->|3. Write reservation.json| DIR_STG
    EP_STG -->|4. Parse form & Stream .part| DIR_STG
    C_CR --> EP_ASS
    EP_ASS -->|Token Lock| LOCKS
    EP_ASS -->|Verify & Bind Token| T_ASS
    EP_ASS -->|Enqueue Jobs| T_JOB
    EP_ASS -.->|Sync Bound Status| DIR_STG

    W_CLAIM --> T_JOB
    W_CLAIM --> W_SCRATCH
    W_SCRATCH --> W_READ
    DIR_STG -->|Read-Only Stream| W_READ
    W_READ --> W_HEAL
    W_HEAL -.->|Heal if uncommitted| DIR_STG
    W_CLEAN -->|Descriptor-relative delete| DIR_STG

    W_GC -->|Acquire Lock| LOCKS
    W_GC -->|5-State Classification| T_ASS
    W_GC -->|Purge Expired/Terminal| DIR_STG
    W_GC -->|Lease-Verified Scratch Purge| W_SCRATCH

    C_REP --> EP_REP
    EP_REP --> T_ASS
```

---

## 4. Shared Storage Design & Deployment Boundaries

### 4.1 Single-Host Docker Named Volume (`staging_data`)
The API and Worker run as distinct operating system processes and execute in isolated container namespaces in production.
- **Docker Compose Mount:** Both `api` and `worker` services mount the persistent named volume `staging_data` to `/var/lib/quantumflow/staging`.
- **Environment Configuration:** Both containers define `STAGING_DIR=/var/lib/quantumflow/staging`.
- **Local Development Host Alignment:** When executing locally without containers, `settings.staging_dir` defaults to `Path("./staging_data")`. Both environments enforce identical subpath resolution and isolation semantics.
- **Persistent Failure Record Hosting:** In addition to tenant staging directories, the persistent volume `staging_data` explicitly hosts the worker cleanup failure tracking registry under `{STAGING_DIR}/.cleanup_failures/`. Because `staging_data` is an independent Docker named volume decoupled from container lifecycles, all failure records, attempt counts, and escalation markers survive container restarts, container recreation (`docker compose up -d --force-recreate worker`), and worker image redeployments.

### 4.2 Multi-Host Deployment Boundary Qualification
- **Sprint 3 Scope (Single-Host Invariant):** Docker named volumes share underlying host disk storage. This completely satisfies local development, single-node Docker Compose, and single-host enterprise VM deployments.
- **Distributed Systems Limitation:** In multi-node Kubernetes clusters or distributed VMs across multiple availability zones, a local Docker named volume cannot bridge independent container hosts.
- **Future Architectural Evolution:** Multi-host scaling requires:
  1. Distributed network-attached storage (NFS, AWS EFS, Azure Files) mounted at `STAGING_DIR`.
  2. S3-compatible object storage (AWS S3, MinIO, GCS) with pre-signed upload URLs and worker chunked streaming.
- **Explicit Sprint Boundary:** Object storage adapters are deferred post-Sprint 3. Single-host shared volume storage satisfies all Sprint 3 requirements.

---

## 5. Multipart Parsing Order & Upload Slot Advisory Locking

### 5.1 Pre-Parsing Advisory Lock Acquisition Protocol
In standard FastAPI endpoints, declaring a parameter `file: UploadFile = File(...)` causes FastAPI's routing dependency graph to parse the multipart request body and spool the upload file to temporary disk *before* entering the endpoint function. If advisory locking were performed inside such an endpoint function, Starlette would have already buffered the file on disk, rendering pre-upload concurrency control ineffective.

To guarantee that the upload slot is acquired **before** multipart parsing and spooling begins:

1. **Endpoint Signature:** The endpoint is declared with a raw `request: Request` parameter:
   ```python
   @router.post("/stage-upload", response_model=StagedUploadResponse, status_code=201)
   async def stage_upload(
       request: Request,
       identity: Annotated[SecurityIdentity, Depends(get_current_identity)],
       db_session_factory: Annotated[async_sessionmaker, Depends(get_sessionmaker)],
   ) -> StagedUploadResponse:
   ```
2. **Step 1: Authenticate & Resolve Tenant (Headers Only):**
   `get_current_identity` inspects only the HTTP `Authorization: Bearer <token>` header without reading or buffering the request body.
3. **Step 2: Acquire Two-Tier Advisory Locks (Cluster Global + Per-Tenant) Before Parsing:**
   Before touching `request.form()`, the endpoint begins a database transaction and executes two-tier advisory locking:
   - **Tier 1: Cluster-Wide Global Upload Slot Acquisition (`qf:global_upload_slot:0..9`):**
     To protect the shared database connection pool and filesystem I/O across *all* running API processes and containers, the endpoint attempts to acquire one of 10 cluster-wide global slots:
     ```python
     def derive_global_upload_slot_key(slot: int) -> int:
         """Derive deterministic signed 64-bit integer key for cluster global upload slot (0..9)."""
         raw = f"qf:global_upload_slot:{slot}".encode("utf-8")
         digest = hashlib.sha256(raw).digest()
         return int.from_bytes(digest[:8], byteorder="big", signed=True)
     ```
     The endpoint evaluates:
     ```sql
     SELECT pg_try_advisory_xact_lock(:global_slot_key);
     ```
     across slots `0..9`. If all 10 slots return `False`, the entire cluster has saturated its global upload concurrency ceiling. The endpoint rolls back and returns `HTTP 429 Too Many Requests` (with `Retry-After: 5`).
   - **Tier 2: Per-Tenant Concurrency Slot Acquisition (0..2):**
     Within the *same* database transaction, the endpoint attempts to acquire slot `0`, `1`, or `2` for `identity.tenant_id`:
     ```sql
     SELECT pg_try_advisory_xact_lock(:tenant_slot_key);
     ```
     If slots 0, 1, and 2 all return `False`, the tenant has saturated their 3 active upload slots. The endpoint rolls back (releasing the Tier 1 global slot immediately) and returns `HTTP 429 Too Many Requests`.
   - **Crucial Guarantee:** **Zero multipart body bytes have been read, parsed, or spooled by Starlette.** Both cluster-wide and tenant-level limits are enforced before any payload data is processed.
4. **Step 3: Trigger Explicit Multipart Parsing:**
   Only *after* both the global slot lock and tenant slot lock are secured in the open transaction, the endpoint invokes:
   ```python
   form = await request.form()
   upload_file: UploadFile = form.get("file")
   ```
5. **Step 4: Stream and Stage File:**
   Stream from `upload_file.file` to `{STAGING_DIR}/{tenant_id}/{upload_token}/{filename}.part` in bounded 64KB chunks.
6. **Step 5: Atomic Rename & Commit:**
   Atomically rename `.part` to final filename, write `metadata.json`, and commit the database transaction, which atomically releases **both** the global upload slot lock and the tenant slot lock across the cluster.

### 5.2 Slot Lock Lifetime, Cluster Concurrency & Crash Safety
- **Lock Scope:** Transaction-scoped (`xact`).
- **Cluster-Wide Coordination (Zero In-Memory Semaphores):**
  Because API instances run in multiple processes and containers, in-memory `asyncio.Semaphore` cannot enforce a cluster-wide ceiling. The Tier 1 advisory lock mechanism enforces a shared, cluster-wide maximum of 10 concurrent uploads across all API processes and hosts purely via PostgreSQL, with **zero database migrations**.
- **Per-Tenant Invariant:** A cluster-wide maximum of 3 concurrent uploads per tenant is preserved across all API instances.
- **Open Transaction Invariant:** The database transaction remains open for the entire duration of file streaming, hashing, and atomic `.part` rename.
- **Exit Path Guarantees:**
  - **Success:** Transaction commits, atomically releasing both global and tenant advisory locks.
  - **Client Disconnect / Timeout:** Transaction automatically rolls back, releasing both locks.
  - **Validation Failure / HTTP 413:** Transaction rolls back, releasing both locks.
  - **Worker / API Crash:** If the API process terminates abruptly (`kill -9`, power loss, container restart), PostgreSQL detects TCP connection termination and **automatically releases all transaction advisory locks immediately**.
- **Connection Pool Protection:**
  Because the global advisory lock restricts simultaneous open upload transactions to at most 10 across the entire cluster, the database connection pool cannot be starved by upload streaming. File streaming is further wrapped in `asyncio.timeout(60)` to abort stalled uploads.

### 5.3 Deterministic 64-Bit Lock-Key Derivation & Collision Analysis
Each tenant has 3 discrete 64-bit advisory lock keys corresponding to slots `0`, `1`, and `2`:
```python
def derive_tenant_slot_key(tenant_id: str, slot: int) -> int:
    """Derive deterministic signed 64-bit integer key for tenant upload slot (0..2)."""
    raw = f"qf:upload_slot:{tenant_id}:{slot}".encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=True)
```
- **Collision Probability:** For $n = 10{,}000$ independently hashed tenant keys in a signed 64-bit space ($2^{64}$), the birthday-bound collision probability is approximately:
  $$P \approx \frac{n(n - 1)}{2 \times 2^{64}} = \frac{10^4 \times 9999}{2 \times 1.84467 \times 10^{19}} \approx 2.71 \times 10^{-12}$$
  (approximately 1 in 370 billion). If an astronomical collision were ever to occur between two distinct tenant IDs, it would result in a safe, conservative concurrency block (temporary HTTP 429) rather than any security bypass or data corruption.

---

## 6. Separation of Upload Slot Locking from Storage Quota Reservation

Holding a quota mutex for the entire duration of file transfer would serialize uploads for a tenant and undermine the intended 3-slot concurrency. Furthermore, counting only completed directories with `metadata.json` misses in-progress uploads and reserved byte allowances.

The design strictly decouples **long-lived slot locking** from **short-lived storage quota reservation**, and subordinates quota garbage collection to active upload-slot locks:

```
[Incoming Upload Request]
        │
        ▼
[Acquire Upload Slot Lock (0..2)]  ──► Held throughout entire upload stream (concurrency = max 3)
        │
        ▼
[Open Short-Lived Quota Mutex Tx]  ──► Held for <5ms in a separate isolated transaction
        │
        ├─► Inspect completed metadata.json + active in-flight reservation.json
        ├─► Sum staged file bytes + reserved byte allowances (20MB archive / 5MB manifest)
        ├─► If count >= 5 or total reserved bytes >= 100MB: Rollback & Return HTTP 429
        ├─► Exclusively create {token}/ directory & write reservation.json (in_progress, slot, reserved_bytes)
        │
[Commit Quota Mutex Tx]            ──► Mutex released immediately (<5ms); other slots can proceed
        │
        ▼
[Stream File to .part]             ──► Concurrent streaming across up to 3 slots
        │
        ▼
[Atomic Finalization]              ──► Write metadata.json.tmp -> Atomic os.replace() -> unlink reservation.json
        │
        ▼
[Commit Slot Lock Tx]              ──► Releases upload slot lock
```

### 6.1 Short-Lived Atomic Reservation Protocol & In-Flight Accounting
1. **Isolated Transaction:** In a dedicated transaction separate from the file streaming session, acquire the tenant's quota mutex:
   ```sql
   SELECT pg_try_advisory_xact_lock(:quota_mutex_key);
   ```
2. **Comprehensive In-Flight Quota Accounting:**
   Inside the staging directory `{STAGING_DIR}/{tenant_id}/`:
   - **Count Completed Uploads:** Directories containing `metadata.json` with `"status": "staged"`.
   - **Count Active In-Flight Reservations:** Directories containing `reservation.json` where `"status": "in_progress"` and `now_utc - reserved_at < 300s` (or whose upload-slot lock is actively held).
   - **Calculate Total Committed and Reserved Storage:**
     $$\text{Total Used Bytes} = \sum_{\text{completed}} \text{actual_file_bytes} + \sum_{\text{in_progress}} \text{byte_size_reserved}$$
     where `byte_size_reserved` is $20\text{MB}$ (`20971520` bytes) for archives and $5\text{MB}$ (`5242880` bytes) for standalone manifests.
   - **Quota Decision:** If $(\text{Total Upload Count} + 1) > 5$ OR $(\text{Total Used Bytes} + \text{New Reserved Bytes}) > 100\text{MB}$:
     Roll back the transaction and return `HTTP 429 Too Many Requests`.
3. **Write Initial Reservation File:**
   - Exclusively create `{STAGING_DIR}/{tenant_id}/{upload_token}` with `os.makedirs(..., exist_ok=False)`.
   - Atomically write `reservation.json` including the active slot index:
     ```json
     {
       "upload_token": "upl_0123456789abcdef0123456789abcdef",
       "tenant_id": "tenant-corp",
       "slot": 0,
       "status": "in_progress",
       "byte_size_reserved": 20971520,
       "reserved_at": "2026-11-03T11:00:00Z"
     }
     ```
4. **Immediate Mutex Commit:**
   Commit the quota transaction immediately ($<5\text{ms}$). The quota mutex is released, allowing concurrent uploads on other slots to reserve space without serialization.

### 6.2 Atomic Finalization & Crash Recovery
To guarantee directory state recoverability after API container crashes or ungraceful terminations:
1. **Three-Step Atomic Replacement Sequence:**
   - When file streaming completes and SHA-256 verification succeeds:
     1. Write temporary metadata: `{STAGING_DIR}/{tenant_id}/{upload_token}/metadata.json.tmp`. Flush buffers and force disk sync (`os.fsync`).
     2. Atomically rename temporary file to final metadata: `os.replace("metadata.json.tmp", "metadata.json")`. (Atomic on POSIX and Windows).
     3. Remove the initial reservation file: `os.unlink("reservation.json")`.
2. **Crash Scenarios & State Recovery:**
   - **Crash Between Step 2 and Step 3 (Both `metadata.json` and `reservation.json` exist):**
     `metadata.json` is treated as authoritative and complete. Subsequent GC and worker processes recognize the upload as staged and delete the residual `reservation.json` without invalidating the archive.
   - **Crash During File Streaming (Only `reservation.json` and partial `.part` exist):**
     Governed by the GC Upload-Slot Guard Protocol below.
   - **Crash Before Final Metadata Rename (Only `metadata.json.tmp` exists):**
     Treated as an unfinalized upload governed by the GC Upload-Slot Guard Protocol.

### 6.3 GC Upload-Slot Guard Protocol (Never Purge Active Uploads Solely by Age)
A client on a high-latency connection or a large archive transfer might upload slowly, legitimately taking longer than 300 seconds. **GC must never purge an in-progress reservation or delete a staging directory based solely on timestamp age.**

The GC daemon applies the **Upload-Slot Guard Protocol**:
1. When GC inspects an unfinalized directory containing `reservation.json` without `metadata.json`:
   - It reads `tenant_id` and `slot` (`0..2`) from `reservation.json`.
   - It derives the 64-bit slot lock key:
     `slot_key = derive_tenant_slot_key(tenant_id, slot)`
   - In a transaction, GC probes the lock:
     ```sql
     SELECT pg_try_advisory_xact_lock(:slot_key);
     ```
2. **Evaluation of Lock State:**
   - **Case A: Lock Acquisition Returns `False` (Slot Lock Actively Held):**
     An API worker process is currently holding the slot lock and streaming data across the HTTP connection.
     **GC MUST PRESERVE THE RESERVATION AND STAGING DIRECTORY**, even if `now_utc - reserved_at > 300s`. The upload is active.
   - **Case B: Lock Acquisition Returns `True` (Slot Lock Not Held):**
     No API process holds the lock.
     - GC rolls back the probe transaction immediately (releasing the probe lock).
     - If `now_utc - reserved_at > 300s`, the upload transaction has terminated ungracefully (client disconnect, API container crash, or network timeout).
     - GC safely unlinks `.part`, deletes `reservation.json`, and removes `{STAGING_DIR}/{tenant_id}/{upload_token}`.

---

## 7. Request-Body and Temporary Storage Protection

```
[Incoming Request]
        │
        ▼
[Layer 1: Reverse Proxy (Nginx / Ingress)] ──► Drops Content-Length > 25MB (client_max_body_size)
        │
        ▼
[Layer 2: Pure ASGI Size Limiting Middleware] ──► Checks Content-Length; wraps receive() to cap chunked transfer;
        │                                         aborts with HTTP 413 if cumulative bytes exceed 25MB
        ▼
[Layer 3: Starlette Multipart Spooling]     ──► Up to 1MB in RAM; overflow spooled to /tmp (mode 0600)
        │
        ▼
[Layer 4: Application Endpoint]             ──► Copies 64KB chunks to .part; enforces 20MB/5MB ceiling
        │
        ▼
[Layer 5: Cleanup & Disconnect]             ──► Spool auto-deleted; endpoint unlinks .part; GC cleans orphaned >15m
```

### 7.1 Multi-Layer Request Protection Specifications

| Layer | Enforcement Mechanism | Limit | Technical Execution Point & Guarantees |
|---|---|:---:|---|
| **Layer 1: Reverse Proxy (Nginx / Ingress)** | `client_max_body_size 25M;` | **25 MB** | Edge drops request before proxying to container. `client_body_timeout 60s;` drops stalled uploads. |
| **Layer 2: Pure ASGI Middleware (`RequestBodyLimitMiddleware`)** | Python ASGI middleware in `services/api/app/main.py` | **25 MB** | 1. If `Content-Length > 25MB`: sends HTTP 413 immediately without calling downstream handler.<br/>2. If chunked transfer: wraps ASGI `receive()` and counts bytes; if cumulative bytes exceed 25MB, raises HTTP 413. **Caps total body delivered downstream.** |
| **Layer 3: Starlette Multipart Spooling** | `SpooledTemporaryFile(max_size=1MB)` | **1 MB in RAM** | Oversized payloads spill to container `/tmp`. Container `/tmp` mounted with `tmpfs: /tmp:size=256M,mode=1777` to prevent container root disk exhaustion. |
| **Layer 4: Application Staging Endpoint** | Chunk-by-chunk copy from `UploadFile.file` | **20MB (ZIP) / 5MB (Manifest)** | Reads 64KB chunks; enforces domain limits; writes to `.part`. Wrapped in `asyncio.timeout(60)`. |
| **Layer 5: Cleanup & Disconnect Handling** | `try ... finally` + Starlette context | **Immediate / 15m** | Starlette unlinks spool upon request end. Endpoint unlinks `.part`. Worker GC purges orphaned `.part` files older than 15 minutes. |

> [!NOTE]
> **Accurate Middleware Guarantee:** For requests with an explicit `Content-Length`, the middleware rejects before any multipart parsing occurs. For chunked requests without `Content-Length`, earlier chunks may be parsed by Starlette before the cumulative 25MB ceiling is reached. The middleware guarantees that total body delivered downstream is strictly capped at 25MB.

---

## 8. Canonical Tenant Ownership & Tenant Boundary Verification

### 8.1 Authoritative System of Record Audit
A thorough inspection of the repository codebase confirms:
1. **Model Audit (`services/api/app/db/models/assessment.py`):** The `Assessment` entity does **not** have an independent top-level column named `tenant_id`.
2. **Canonical Tenant Storage:** Tenant ownership is canonically and durably stored inside the JSONB document:
   `Assessment.target_snapshot["tenant_id"]`.
3. **Existing Scoping Implementation:**
   - Assessment creation (`assessment_service.py:420`): explicitly persists `target_snapshot["tenant_id"] = tenant_id`.
   - Assessment listing (`assessment_service.py:541`): executes `Assessment.target_snapshot["tenant_id"].as_string() == tenant_id`.
   - Access verification (`security.py:142`): `verify_tenant_access(identity, assessment.target_snapshot.get("tenant_id"))`.
4. **System-Wide Ownership Guarantee:**
   The API upload staging, assessment creation, background worker claiming, report delivery, and hourly garbage collection must all reference this exact canonical identity:
   $$\text{Canonical Tenant ID} \equiv \text{Assessment.target_snapshot["tenant_id"]}$$

### 8.2 Deterministic Ownership Behavior Matrix

| Scenario | Database State | Directory Path State | API Action | Worker / GC Action |
|---|---|---|---|---|
| **Exact Tenant Match** | Exactly 1 record where `record.tenant_id == expected_tenant_id` | `{STAGING_DIR}/{expected_tenant_id}/{token}` | Bound and active; returns 200/201 | If active/retryable: preserve and reconcile `metadata.json`. If terminal finalized: safely purge. |
| **Missing Tenant ID** | 1 record where `target_snapshot` has no `tenant_id` or is `null` | `{STAGING_DIR}/{expected_tenant_id}/{token}` | Rejected with HTTP 409 Conflict | Treated as **ambiguous ownership defect (State 3)**. GC never infers ownership; preserves directory; logs `AMBIGUOUS_TOKEN_OWNERSHIP`. |
| **Cross-Tenant Collision** | 1 record where `record.tenant_id != expected_tenant_id` | `{STAGING_DIR}/{expected_tenant_id}/{token}` | Rejected with HTTP 409 Conflict | Treated as **cross-tenant integrity violation (State 3/5)**. Preserves directory; logs `CRITICAL_CROSS_TENANT_INTEGRITY_VIOLATION`. |
| **Duplicate Records (Same Tenant)** | $>1$ records matching `expected_tenant_id` | `{STAGING_DIR}/{expected_tenant_id}/{token}` | Rejected with HTTP 409 Conflict | Treated as **database integrity violation (State 4)**. Preserves directory; logs `CRITICAL_INTEGRITY_VIOLATION`. |
| **Duplicate Records (Cross-Tenant)** | $>1$ records across different tenant identities | `{STAGING_DIR}/{expected_tenant_id}/{token}` | Rejected with HTTP 409 Conflict | Treated as **cross-tenant integrity violation (State 5)**. Preserves directory; logs `CRITICAL_CROSS_TENANT_INTEGRITY_VIOLATION`. |
| **Unreferenced Upload** | 0 records referencing token in PostgreSQL | `{STAGING_DIR}/{expected_tenant_id}/{token}` | N/A (unbound staging) | If `now_utc >= expires_at` (>4h) and metadata valid: safely purge. If metadata corrupt/missing: **preserve directory** and log `UNVERIFIABLE_STAGING_ENTRY`. |

---

## 9. PostgreSQL Transaction Advisory Locking for Assessments

To eliminate race conditions between `create_and_enqueue_assessment` and the background garbage collection daemon:

### 9.1 Advisory Lock Key Derivation
The 64-bit signed integer key is deterministically derived from the upload token:
```python
def derive_token_lock_key(upload_token: str) -> int:
    digest = hashlib.sha256(f"upload_token:{upload_token}".encode()).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=True)
```

### 9.2 Exclusive In-Transaction Acquisition
Inside `async with db.begin()` transaction:
```sql
SELECT pg_try_advisory_xact_lock(:lock_key);
```
- **Lock Scope:** Transaction-level (`xact`). PostgreSQL automatically releases the advisory lock upon transaction commit or rollback.
- **Non-Blocking:** If another transaction holds the lock, API returns `HTTP 409 Conflict` ("Upload token claim in-flight"); GC aborts and defers.

---

## 10. Descriptor-Relative Filesystem TOCTOU & Confinement Deletion

Pathname-based `os.lstat()` followed by `os.unlink()` or `os.rmdir()` is inherently susceptible to Time-of-Check-to-Time-of-Use (TOCTOU) races where an attacker swaps a directory segment with a symlink between the check and the deletion call.

The cleanup design implements **descriptor-relative filesystem operations (`dir_fd`)** on POSIX platforms, with an explicit, hardened fallback on Windows.

### 10.1 POSIX Descriptor-Relative Deletion Protocol (`dir_fd` + `O_NOFOLLOW`)
On POSIX platforms (Linux / Docker production containers) where `os.supports_dir_fd` is supported:

1. **Root Directory Anchor:**
   Open the verified canonical staging root with `O_DIRECTORY | O_CLOEXEC`:
   ```python
   root_fd = os.open(canonical_staging_root, os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0))
   ```
2. **Hop-by-Hop No-Follow Traversal:**
   Open each verified path segment (`tenant_id`, then `upload_token`) relative to its parent file descriptor using `os.O_NOFOLLOW`:
   ```python
   tenant_fd = os.open(tenant_id, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=root_fd)
   token_fd = os.open(upload_token, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=tenant_fd)
   ```
   If any component is a symbolic link, `os.open` raises `OSError` (`ELOOP` / `SYMLINK_LOOP`). GC catches this immediately, preserves the directory, and logs `SECURITY_VIOLATION_SYMLINK_IN_PATH`.
3. **Descriptor-Relative Recursive Removal:**
   - Iterate directory entries using `os.scandir(token_fd)`.
   - Inspect each entry using `entry.stat(follow_symlinks=False)`.
   - If entry is a symlink: unlink using `os.unlink(entry.name, dir_fd=token_fd)` without following.
   - If entry is a regular file: unlink using `os.unlink(entry.name, dir_fd=token_fd)`.
   - If entry is a directory: open child with `os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=token_fd)` and recurse descriptor-relatively. After clearing, remove directory using `os.rmdir(entry.name, dir_fd=token_fd)`.
4. **Empty Parent Pruning:**
   - Remove empty token directory using `os.rmdir(upload_token, dir_fd=tenant_fd)`.
   - If `tenant_fd` has no remaining entries, prune using `os.rmdir(tenant_id, dir_fd=root_fd)`.
5. **Descriptor Leak Prevention:** All opened directory descriptors are wrapped in `try ... finally` ensuring `os.close(fd)` is executed under all conditions.

### 10.2 Windows Platform Hardened Fallback Protocol
On Windows environments (where `os.supports_dir_fd` is empty and `O_NOFOLLOW` is not defined in standard CRT):
1. **Explicit Identification:** Document that `os.supports_dir_fd` is empty on Windows (`supports_dir_fd: []`).
2. **Reparse Point & Symlink Sniffing:**
   Inspect each entry using `entry.stat(follow_symlinks=False)`:
   - Check `entry.is_symlink()`.
   - Check Windows file attributes: `st.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT != 0`.
   - Check for directory junctions and volume mounts.
3. **No-Follow Deletion:**
   - If an entry is a symbolic link or directory junction: remove the junction/symlink node itself using `os.unlink(entry.path)` (or `os.rmdir` for directory junctions on Windows). **Never follow into the junction target.**
   - If a regular file: remove using `os.unlink(entry.path)`.
   - If a genuine physical directory: recurse safely with identical confinement checks.
4. **Strict Confinement Check Before Every Deletion:**
   Assert `os.path.commonpath([canonical_staging_root, os.path.abspath(target_path)]) == str(canonical_staging_root)` immediately prior to every delete invocation.
5. **Windows File Lock Handling:**
   If an antivirus process or background indexer temporarily locks a file (`PermissionError` / WinError 32 `The process cannot access the file because it is being used by another process`), catch the exception, log `DELETION_DEFERRED`, leave remaining files intact, and defer cleanup to the next cycle without crashing.

---

## 11. Secure Scratch Workspace Isolation, Active-Lease GC & Cleanup Recovery

The extraction engine in [`packages/scanner/source/archive.py`](file:///d:/Desktop/quantum-flow-pqc-platform/packages/scanner/source/archive.py) enforces defense-in-depth resource ceilings, active-lease-aware garbage collection, and explicit cleanup failure recovery:

### 11.1 Dedicated Secure Scratch Workspace Design
When a worker claims an archive discovery job, it creates an isolated, exclusive scratch workspace:
1. **Trusted Scratch Parent Root:**
   - Configured via `settings.scratch_dir` with an absolute path (`/var/lib/quantumflow/scratch` or `./scratch`).
   - Verified at worker startup:
     - `st = os.lstat(scratch_root)`
     - `assert not os.path.islink(scratch_root)`
     - `assert stat.S_ISDIR(st.st_mode)`
     - `assert (st.st_mode & 0o777) == 0o700` (mode `0700` strictly owned by worker user).
2. **Job-Specific Unique Path:**
   - Path generation combines `job_id` and 12 random hex characters:
     `workspace = scratch_root / f"job_{job_id}_{uuid.uuid4().hex[:12]}"`
   - Created exclusively with `os.makedirs(workspace, mode=0o700, exist_ok=False)` **strictly after acquiring the per-job advisory lock**.
   - Path collisions between concurrent worker processes or jobs are cryptographically and statistically negligible ($p < 2^{-122}$).
   - Permissions `0700` (`rwx------`) guarantee other processes or tenants cannot read or write to the scratch directory.
3. **Descriptor-Relative Extraction Writes & Confinement:**
   - On POSIX: Destination subdirectories are opened with `os.open(..., O_DIRECTORY | O_NOFOLLOW, dir_fd=...)`. Files are created with `os.open(..., O_WRONLY | O_CREAT | O_EXCL | getattr(os, "O_NOFOLLOW", 0), dir_fd=...)`. Any member attempting a symlink escape triggers an immediate `OSError`.
   - On all platforms: Every extracted path is asserted: `assert destination.resolve().is_relative_to(workspace)`.

### 11.2 Atomic Worker–GC Scratch Coordination Protocol & Lease Correlation
A legitimate, extensive source scan may execute longer than 30 minutes. **Age alone must never establish that a scratch workspace is abandoned, and a database lease check alone does not prevent race conditions between a running worker and the GC cleaner.**

To ensure strict mutual exclusion across all worker and GC processes, both components participate in a **shared PostgreSQL per-job advisory locking protocol**:

#### 1. Deterministic Per-Job 64-Bit Lock-Key & `pg_locks` Mapping Derivation
Both worker execution and GC cleanup derive the identical signed 64-bit integer key from `job_id`:
```python
def derive_job_scratch_lock_key(job_id: str | UUID) -> int:
    """Derive deterministic signed 64-bit integer advisory lock key for job scratch coordination."""
    raw = f"qf:job_scratch:{job_id}".encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=True)
```

In PostgreSQL's internal lock manager (`src/backend/storage/lmgr/lock.c`), a single 64-bit advisory lock key is mapped into `pg_locks` across three distinct columns:
- `classid` (`oid`, unsigned 32-bit integer): Upper 32 bits of the 64-bit integer.
- `objid` (`oid`, unsigned 32-bit integer): Lower 32 bits of the 64-bit integer.
- `objsubid` (`smallint`, int2): Set to `1` (indicating a single 64-bit `bigint` key; value `2` is reserved for two-parameter `(int4, int4)` advisory locks).

The Python helper computes and validates this exact mapping:
```python
def split_advisory_lock_key(key_int64: int) -> tuple[int, int, int]:
    """Decompose signed 64-bit int into validated PostgreSQL pg_locks (classid, objid, objsubid)."""
    u64 = key_int64 & 0xFFFF_FFFF_FFFF_FFFF
    classid = (u64 >> 32) & 0xFFFF_FFFF
    objid = u64 & 0xFFFF_FFFF
    objsubid = 1
    # Strict range validation before database binding
    if not (0 <= classid <= 4294967295) or not (0 <= objid <= 4294967295):
        raise ValueError(f"Advisory lock key components out of 32-bit unsigned range: classid={classid}, objid={objid}")
    return classid, objid, objsubid
```

#### 2. Worker Lock Acquisition & Dedicated Connection Session Ownership
To guarantee that the advisory lock cannot be silently lost or uncoupled from heartbeat renewals:
1. **Dedicated Connection Pinning:** When a worker claims a job from `discovery_jobs`, it checks out a dedicated database connection (`asyncpg` / raw connection) from the connection engine.
   - **Strict Pinning Invariant:** This dedicated connection is **pinned exclusively to this job and is NEVER returned to the connection pool** while the job is executing or the scratch workspace exists.
   - **Session-Level Lock Acquisition:** The worker acquires the session advisory lock exclusively on this dedicated connection:
     ```sql
     SELECT pg_try_advisory_lock(:job_scratch_lock_key);
     ```
   - If lock acquisition returns `False` (another worker holds it), the worker aborts execution immediately without touching the filesystem.
2. **Lifetime Guarantee:** The worker retains this dedicated connection throughout the entire duration of archive extraction, source analysis, and post-analysis cleanup.
3. **Dedicated Lock-Validity & Heartbeat Query (Explicit OID Casts):**
   The worker executes all heartbeat renewals and lock-ownership verifications **strictly on this same dedicated connection**:
   ```sql
   WITH lock_check AS (
       SELECT EXISTS (
           SELECT 1 FROM pg_locks
           WHERE locktype = 'advisory'
             AND classid = CAST(:classid AS oid)
             AND objid = CAST(:objid AS oid)
             AND objsubid = 1
             AND pid = pg_backend_pid()
             AND mode = 'ExclusiveLock'
             AND granted = true
       ) AS has_lock
   ),
   lease_update AS (
       UPDATE discovery_jobs
       SET lease_expires_at = clock_timestamp() + interval '60 seconds'
       WHERE id = :job_id
         AND worker_id = :worker_id
         AND status = 'running'
         AND (SELECT has_lock FROM lock_check) = true
       RETURNING id
   )
   SELECT
       (SELECT has_lock FROM lock_check) AS lock_held,
       EXISTS (SELECT 1 FROM lease_update) AS lease_renewed;
   ```
   - **Explicit OID Casting:** In PostgreSQL, `classid` and `objid` in `pg_locks` are typed as `oid`. Explicitly specifying `CAST(:classid AS oid)` and `CAST(:objid AS oid)` guarantees type matching across asyncpg and SQLAlchemy parameter binding without ambiguous type coercions.
   - **No Accidental Acquisition Count Inflation:** In PostgreSQL, calling `pg_try_advisory_lock()` repeatedly on an already-held session lock increments an internal per-session lock counter, which requires an equal number of `pg_advisory_unlock()` calls to release. By querying `pg_locks` as a passive catalog read, the lock counter **remains exactly 1**.
   - **Mechanisms Verified:**
     1. `locktype = 'advisory'` confirms the lock type.
     2. `classid` and `objid` match the high and low 32-bit components of the 64-bit key as OIDs.
     3. `objsubid = 1` matches single-key bigint advisory locks.
     4. `pid = pg_backend_pid()` verifies that *this exact dedicated database session* holds the lock.
     5. `mode = 'ExclusiveLock'` and `granted = true` confirm active exclusive grant.
     6. The lease is renewed if and only if `lock_held` is `true`.
     7. If `lock_held` is `false`, `lease_renewed` is `false`, or if any query timeout or socket exception occurs: the worker immediately triggers fail-closed cessation.
   - **Prohibition on Assumption:** The worker **must never assume that successful lease renewal on a different pooled connection proves ownership of the advisory lock**. Only verification on the dedicated session constitutes proof of ownership.
4. **Release Invariants:** The worker executes `SELECT pg_advisory_unlock(:job_scratch_lock_key)` on this dedicated connection strictly in a `finally:` block **after** scratch workspace deletion finishes, and only then returns the connection to the pool. If the connection drops or the process terminates, PostgreSQL releases the lock automatically on TCP disconnect.

#### 3. GC Deletion Verification Protocol (Cleaner Side)
Before attempting to delete any scratch workspace `job_{job_id}_{hex}`, the GC daemon executes the following mandatory verification pipeline:
1. **Database Job Existence Check:**
   GC extracts `job_id` from the directory name and queries:
   ```sql
   SELECT id, status, worker_id, lease_expires_at FROM discovery_jobs WHERE id = :job_id;
   ```
   - **Missing Database Record Safeguard:** If no row is returned for `job_id`:
     **GC MUST NOT DELETE THE WORKSPACE.** It emits a high-priority structured integrity alert:
     `CRITICAL_ORPHAN_SCRATCH_DIR: Scratch workspace {workspace} references non-existent job_id {job_id}. Preserving workspace for operator security audit.`
     The workspace is marked and preserved. A missing database record must never be assumed safe to delete.
2. **Active Lease Check:**
   If `job.status == "running"` AND `now_utc < job.lease_expires_at`:
   **GC PRESERVES THE WORKSPACE IMMEDIATELY.** (Worker is actively heartbeating).
3. **Atomic Mutual Exclusion Advisory Lock Check:**
   Even if the job status is terminal (`completed`, `failed`, `cancelled`) OR its lease has expired without heartbeat (`now_utc >= lease_expires_at + 120s`), GC **MUST** attempt to acquire the job's advisory lock before touching the filesystem:
   ```sql
   SELECT pg_try_advisory_xact_lock(:job_scratch_lock_key);
   ```
   - **If Lock Acquisition Returns `False`:**
     An active worker process is currently using or cleaning up this workspace!
     **GC IMMEDIATELY ABORTS AND DEFERS DELETION.**
     This eliminates the race condition where a worker resumes or renews its lease between the lease check and directory deletion.
   - **If Lock Acquisition Returns `True`:**
     Zero workers hold the workspace lock. GC proceeds with safe, descriptor-relative deletion.

#### 4. Worker Crash & Zombie Recovery Sequence
1. Worker crashes abruptly mid-scan -> PostgreSQL automatically releases `qf:job_scratch:{job_id}` upon TCP connection close.
2. Worker heartbeat ceases -> `lease_expires_at` lapses.
3. System zombie recovery daemon (`JobService.recover_zombies`) transitions the stalled job to `failed` or re-queues it.
4. On the next GC cycle, GC acquires the transaction lock `pg_try_advisory_xact_lock(:job_scratch_lock_key)` (which succeeds because the worker is dead), verifies the terminal/zombie state, and safely cleans up the abandoned scratch workspace.

#### 5. Concrete Process-Launch Architecture, Descendant Verification & Multi-Factor Quarantine
In asynchronous Python, running synchronous CPU-bound or I/O-bound filesystem tasks via `asyncio.to_thread()` is inherently unsafe under cancellation: cancelling an asyncio task raises `asyncio.CancelledError` in the coroutine, but **the underlying Python thread cannot be forcibly terminated**. It continues executing in the background until completion, continuing to read and write to the scratch workspace.

To provide an absolute, verifiable guarantee that zero filesystem reads or writes continue after lock loss, the system selects **one concrete process-launch architecture: `subprocess.Popen` / `asyncio.create_subprocess_exec` executing an isolated scanner module entrypoint** (`python -m packages.scanner.runner --job-id <id> --workspace <path>`):

```
[Worker Process (Asyncio Main)]
        │
        ├── Dedicated Connection (Pinned) ──► pg_try_advisory_lock() + pg_locks Heartbeat
        │
        └── Launches Isolated Process Tree ──► subprocess.Popen()
                  │
                  ├─► POSIX: start_new_session=True (New PGID == PID)
                  │   Termination: os.killpg(pid, SIGKILL)
                  │   Verification: poll os.killpg(pid, 0) == ProcessLookupError (all descendants dead)
                  │
                  └─► Windows: Windows Job Object (JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)
                      Termination: TerminateJobObject(hJob, 1) + CloseHandle()
                      Verification: QueryInformationJobObject() -> NumberOfProcessIdsInList == 0
```

##### 1. POSIX Process-Group Launch, Kernel-Safe `/proc` Parsing & Conclusive Verification
1. **Dedicated Session Establishment:** On POSIX, the child scanner process is spawned with:
   ```python
   proc = subprocess.Popen(
       cmd,
       start_new_session=True,  # Calls os.setsid() in child immediately after fork
       cwd=workspace,
   )
   ```
   Calling `start_new_session=True` makes the child the leader of a brand new session and process group where `PGID == PID`. Any subprocesses spawned by the scanner (e.g. decompression utilities, CLI parsers) automatically inherit this PGID.
2. **Anti-Escape Restriction & OS-Level Boundaries:**
   - Scanner tools and child processes are **strictly prohibited from deliberately escaping the managed session or process group** (e.g. via `setsid()`, `setpgid()`, or double-fork daemonization).
   - For defense-in-depth against arbitrary scripts: in production Linux containers, worker processes execute jobs within dedicated **PID Namespaces (`CLONE_NEWPID`)** or **cgroups v2** (`/sys/fs/cgroup/quantumflow/job_{id}` with `cgroup.kill`). When `cgroup.kill` is written with `1`, the Linux kernel atomically freezes and kills every process inside the cgroup, completely eliminating any possibility of escape via session detachment.
3. **Process-Group Termination:** When connection loss or heartbeat failure occurs:
   - Delivers `SIGKILL` to the entire process group:
     `os.killpg(proc.pid, signal.SIGKILL)`
4. **Kernel-Safe `/proc/[pid]/stat` Parsing (Immune to Whitespace & Brackets in Process Names):**
   According to the Linux kernel format (`fs/proc/array.c`), `/proc/[pid]/stat` begins with:
   `pid (comm) state ppid pgrp session ...`
   Because the executable name `comm` is enclosed in parentheses and can contain arbitrary whitespace, nested parentheses, and brackets (e.g. `(scanner (worker) v2)`), a naive `.split()` causes unpredictable field shifting.
   To parse with 100% kernel compliance:
   - Locate the boundary by finding the **last closing parenthesis `)`** via `rfind(')')`.
   - Everything before the final `)` is `pid` and `comm`.
   - The tokenized remainder after the final `)` begins strictly at field 3 (`state`):
     - `remainder[0]` = field 3 (`state`, `%c`)
     - `remainder[1]` = field 4 (`ppid`, `%d`)
     - `remainder[2]` = field 5 (`pgrp`, `%d`)
     - `remainder[19]` = field 22 (`starttime`, `%llu`)
   This guarantees that `pgrp` and `starttime` are indexed reliably regardless of spaces or brackets in process names.
5. **Fail-Closed Conclusive Scan Policy (Never Treat Incomplete Scan as Verified):**
   When scanning `/proc`, individual process reads can fail:
   - `FileNotFoundError` / `ProcessLookupError` (`ENOENT` / `ESRCH`): A process exited between directory enumeration and reading. This is a normal kernel lifecycle race and is safely tolerated.
   - `PermissionError` (`EACCES` / `EPERM`) or `OSError` (`EIO`): The process exists, but cannot be read or verified. Because the worker cannot inspect its `pgrp`, the identity of that active process is unknown.
   - Malformed / truncated format: Missing closing parenthesis or fewer than 20 fields after `)`.
   **Strict Safety Rule:** If ANY process entry cannot be verified due to permission restrictions, I/O errors, or malformed stat output, or if `/proc` itself cannot be fully enumerated:
   - The scan is flagged as **indeterminate** (`is_scan_conclusive = False`).
   - The worker or GC **must NOT assume the process group is empty**.
   - **Cleanup is immediately HALTED**, workspace deletion is aborted, and an operational alert is logged.
   ```python
   class ProcStatParseError(Exception):
       '''Raised when /proc/[pid]/stat is malformed, truncated, or unreadable.'''
       pass

   def parse_proc_stat(pid: int) -> tuple[int, int]:
       '''
       Parses /proc/[pid]/stat safely according to Linux kernel specification.
       Returns (pgrp, starttime).
       '''
       stat_path = f"/proc/{pid}/stat"
       try:
           with open(stat_path, "r", encoding="utf-8", errors="replace") as f:
               content = f.read()
       except (FileNotFoundError, ProcessLookupError):
           # Process exited concurrently between scandir and read: normal kernel race
           raise FileNotFoundError(f"Process {pid} terminated concurrently")
       except OSError as exc:
           # PermissionError (EACCES/EPERM), EIO, etc.: cannot verify identity!
           raise ProcStatParseError(f"Cannot read {stat_path}: {exc}") from exc

       # Isolate comm by finding the final closing parenthesis
       rparen = content.rfind(")")
       if rparen == -1:
           raise ProcStatParseError(f"Malformed {stat_path}: missing closing parenthesis")

       remainder = content[rparen + 1:].strip().split()
       if len(remainder) < 20:  # Must have at least up to field 22 (index 19 in remainder)
           raise ProcStatParseError(f"Truncated {stat_path}: found {len(remainder)} fields after ')'")

       try:
           pgrp = int(remainder[2])        # Field 5 (1-based): pgrp
           starttime = int(remainder[19])  # Field 22 (1-based): starttime
           return pgrp, starttime
       except ValueError as exc:
           raise ProcStatParseError(f"Invalid integer field in {stat_path}: {exc}") from exc

   def scan_active_pgid_descendants(target_pgid: int) -> tuple[list[int], bool]:
       '''
       Scans /proc for processes belonging to target_pgid.
       Returns (matching_pids, is_scan_conclusive).
       
       If ANY process entry (other than clean ENOENT) cannot be read or verified,
       is_scan_conclusive is set to False, halting cleanup.
       '''
       matching_pids = []
       is_scan_conclusive = True

       try:
           proc_entries = list(os.scandir("/proc"))
       except OSError as exc:
           # /proc cannot be enumerated (e.g. unmounted, permission error)
           return [], False

       for entry in proc_entries:
           if not (entry.is_dir() and entry.name.isdigit()):
               continue
           pid = int(entry.name)
           try:
               pgrp, _ = parse_proc_stat(pid)
               if pgrp == target_pgid:
                   matching_pids.append(pid)
           except FileNotFoundError:
               # Clean concurrent process exit: safe to continue
               continue
           except ProcStatParseError as exc:
               # Process exists but cannot be verified! We cannot prove it is not in pgid!
               is_scan_conclusive = False
               logger.warning("PROC_SCAN_INDETERMINATE_ENTRY", pid=pid, error=str(exc))

       return matching_pids, is_scan_conclusive
   ```
6. **Comprehensive Descendant Verification Loop:**
   ```python
   deadline = time.monotonic() + 10.0
   all_descendants_dead = False
   while time.monotonic() < deadline:
       try:
           os.killpg(original_pgid, 0)
           time.sleep(0.2)
       except ProcessLookupError:
           # Kernel killpg reports no processes in PGID.
           # Now verify against /proc whole-system scan.
           lingering, is_conclusive = scan_active_pgid_descendants(original_pgid)
           
           if not is_conclusive:
               # Incomplete scan: do not assume process group is empty!
               logger.error(
                   "PROC_SCAN_INCOMPLETE_CLEANUP_HALTED",
                   pgid=original_pgid,
                   reason="One or more /proc entries could not be read or verified"
               )
               all_descendants_dead = False
               break

           if not lingering:
               # Both killpg and conclusive /proc scan confirm ZERO descendants!
               all_descendants_dead = True
               break

           time.sleep(0.2)

   proc.poll()
   if not all_descendants_dead:
       # Cleanup HALTED! Do NOT delete workspace!
       # Workspace enters durable quarantine.
   ```
7. **Handling Uninterruptible Child ("D" State):**
   If processes with `pgrp == original_pgid` remain after 10 seconds (e.g. process stuck in uninterruptible sleep `D` state waiting on blocked driver or NFS/disk I/O) or if the scan is indeterminate, the workspace enters the durable quarantine state below.

##### 2. Windows Job Object Containment & Suspended Launch Architecture
Ordinary `subprocess.Popen()` followed by post-launch Job Object assignment is vulnerable to a race condition where the child process executes instructions or spawns descendants before assignment occurs. Furthermore, enabling breakaway permissions allows child processes to escape Job Object containment.

To guarantee 100% race-free containment on Windows:

1. **Strict Job Object Configuration (Zero Breakaway Permissions):**
   - Create unique Job Object: `hJob = win32job.CreateJobObject(None, f"qf_job_{job_id}_{uuid.uuid4().hex[:8]}")`.
   - **Removal of Breakaway Flags:** `JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK` and `JOB_OBJECT_LIMIT_BREAKAWAY_OK` are **strictly removed and forbidden**.
   - Configure limits strictly with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`:
     ```python
     info = win32job.QueryInformationJobObject(hJob, win32job.JobObjectExtendedLimitInformation)
     info["BasicLimitInformation"]["LimitFlags"] = win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
     win32job.SetInformationJobObject(hJob, win32job.JobObjectExtendedLimitInformation, info)
     ```
   - Under this configuration, the Windows kernel strictly forbids any child process from breaking away. Any attempt to spawn a process with `CREATE_BREAKAWAY_FROM_JOB` is rejected by the Windows kernel with `ERROR_ACCESS_DENIED`.
2. **Suspended Process Creation & Pre-Execution Assignment:**
   - The scanner process is launched in a **suspended state** using Win32 `CreateProcessW` (via `win32process.CreateProcess` or `ctypes`):
     ```python
     hProcess, hThread, dwProcessId, dwThreadId = win32process.CreateProcess(
         None, cmd_line, None, None, True,
         win32con.CREATE_SUSPENDED | win32con.CREATE_NO_WINDOW,
         None, str(workspace), startup_info
     )
     ```
   - **Assign While Suspended:**
     ```python
     try:
         win32job.AssignProcessToJobObject(hJob, hProcess)
     except Exception as exc:
         # Fail closed immediately: terminate suspended process before any instruction executes
         win32process.TerminateProcess(hProcess, 1)
         win32api.CloseHandle(hThread)
         win32api.CloseHandle(hProcess)
         raise ProcessContainmentError(f"Failed to assign scanner process to Job Object: {exc}")
     ```
   - **Resume Thread ONLY After Successful Assignment:**
     ```python
     win32process.ResumeThread(hThread)
     win32api.CloseHandle(hThread)
     ```
   - **Crucial Guarantee:** The scanner process **cannot execute a single instruction outside the Job Object**. All descendants spawned by the scanner are unconditionally and transitively contained in the Job Object.
3. **Job Object Termination:**
   - Terminate all assigned processes simultaneously: `win32job.TerminateJobObject(hJob, 1)` followed by closing the handle `win32api.CloseHandle(hJob)`.
4. **Complete Descendant Verification (Process Count == 0):**
   - Active verification queries the Job Object process list until the count reaches zero:
     ```python
     deadline = time.monotonic() + 10.0
     all_descendants_dead = False
     while time.monotonic() < deadline:
         pids = win32job.QueryInformationJobObject(hJob, win32job.JobObjectBasicProcessIdList)
         if len(pids) == 0:
             all_descendants_dead = True
             break
         time.sleep(0.2)
     ```
5. **Handling Uninterruptible Windows Processes:**
   If processes remain in the Job Object list after 10 seconds (e.g. pending uncancelable driver IRP packet), the workspace enters the durable quarantine state below.

##### 3. Multi-Factor Quarantine Identity (Preventing PID-Recycling Errors)
A raw PID is reusable by the operating system and cannot prove identity if the original leader process exited while descendants remain, or if the PID was recycled by an unrelated newly spawned process.

If descendant termination cannot be verified within the 10-second deadline, the worker captures **multi-factor process identity** and writes a durable quarantine descriptor to `{STAGING_DIR}/.cleanup_failures/{workspace_basename}.quarantine.json`:
```json
{
  "workspace_path": "/var/lib/quantumflow/scratch/job_9b1deb4d_a1b2c3d4e5f6",
  "workspace_basename": "job_9b1deb4d_a1b2c3d4e5f6",
  "job_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "status": "quarantined_child_alive",
  "quarantined_at": "2026-11-03T12:00:00Z",
  "process_identity": {
    "leader_pid": 12345,
    "leader_create_time": 1793617200.123456,
    "posix_boot_id": "4b6f1234-5678-9abc-def0-123456789abc",
    "posix_pgid": 12345,
    "posix_session_id": 12345,
    "windows_job_object_name": "Global\qf_job_9b1deb4d_a1b2c3d4",
    "windows_creation_filetime": 133456789012345678
  },
  "reason": "Process group 12345 failed to confirm termination of all descendants within 10s deadline after SIGKILL/TerminateJobObject"
}
```

##### 4. GC Whole-Group Verification Protocol Before Quarantined Workspace Deletion
When GC inspects `.quarantine.json` records on its hourly cycle:
- **POSIX Verification Pipeline (Whole-Group & Boot ID):**
  1. Read `/proc/sys/kernel/random/boot_id`:
     - If `current_boot_id != record['process_identity']['posix_boot_id']`:
       The host rebooted! All processes from the prior boot are physically dead. Safe to delete.
  2. If `boot_id` matches: scan all running processes via `scan_active_pgid_descendants(record['process_identity']['posix_pgid'])`:
     - If `is_scan_conclusive is False`:
       One or more `/proc` entries could not be read or verified (e.g. `PermissionError`, `EIO`, or malformed stat format).
       **INCOMPLETE /PROC SCAN: GC MUST NOT ASSUME PROCESS GROUP IS EMPTY.**
       **GC STRICTLY HALTS CLEANUP, PRESERVES THE WORKSPACE, AND RAISES AN OPERATIONAL ALERT.**
     - If `len(matching_pids) > 0`:
       Check process start times (field 22 `starttime`). If start time is consistent with having been created during the job execution window:
       An original descendant process is STILL ALIVE in kernel uninterruptible state!
       **GC PRESERVES THE WORKSPACE AND DEFERS.**
     - If and only if `len(matching_pids) == 0`, `is_scan_conclusive is True`, and `os.killpg(original_pgid, 0)` raises `ProcessLookupError`:
       All processes in the original process group are conclusively verified dead. Safe to delete.
- **Windows Verification Pipeline (Job Object & Boot Time):**
  1. Check system boot time (`psutil.boot_time()`). If the host rebooted after `quarantined_at`, all processes from the prior boot are dead. Safe to delete.
  2. If system did not reboot: query Job Object via `QueryInformationJobObject(hJob, JobObjectBasicProcessIdList)`.
     - If `len(pids) > 0`: original processes or descendants are STILL ALIVE in the Job Object. **GC preserves workspace and defers**.
     - If `len(pids) == 0`: all processes assigned to the Job Object are dead. Safe to delete.
  3. If Job Object handle is lost: query process via `OpenProcess`. If `GetProcessTimes()` reports `CreationTime != record['process_identity']['windows_creation_filetime']`:
     Leader PID was recycled and Job Object closed. Safe to delete.
- **Conclusive Establishment Rule:** If `/proc` cannot be read, if any process stat entry cannot be read or parsed (e.g. `PermissionError`, `EIO`, or malformed format), or if process-group membership cannot be conclusively verified:
  **GC MUST PRESERVE THE WORKSPACE and require manual operator intervention.** Deletion is strictly forbidden if safety cannot be conclusively proven. An incomplete `/proc` scan is never accepted as a successful verification.

##### 5. The Five-Point Universal Safety Invariant
> [!IMPORTANT]
> **A workspace is eligible for deletion only after:**
> 1. The worker has stopped accessing it.
> 2. All child and descendant processes have stopped accessing it.
> 3. Process termination has been positively verified.
> 4. GC has acquired the appropriate advisory lock (`qf:job_scratch:{job_id}`).
> 5. No quarantine or unresolved cleanup-failure condition remains.

##### 6. Lifecycle Behavior Across All Five Failure Scenarios:
- **Scenario 1: Database connection loss during archive extraction:**
  Process group / Job Object is killed immediately. Worker polls descendant termination. Once confirmed dead, worker logs `WORKER_LOCK_LOST`, does NOT delete workspace, and yields partial directory to GC. If child remains alive after 10s, directory is quarantined.
- **Scenario 2: Database connection loss during source parsing:**
  Process group executing AST parsing is killed and verified dead (`descendants_dead == True`). Workspace preserved intact and yielded to GC.
- **Scenario 3: Database connection loss during CBOM ingestion:**
  Archive extraction and AST scanning have already finished cleanly and child processes have exited. CBOM ingestion executes SQL queries into PostgreSQL. If connection drops during ingestion, SQL transaction rolls back and raises `ConnectionError`. No writes to scratch workspace occur. Workspace is preserved for GC zombie cleanup.
- **Scenario 4: Heartbeat timeout while a collector is running:**
  Heartbeat query times out after 15 seconds without receiving a response from PostgreSQL on the dedicated connection. Worker immediately treats this as lock loss, terminates process group / Job Object, verifies descendant exit, and yields workspace to GC.
- **Scenario 5: Worker shutdown (SIGTERM/SIGINT) while a collector is running:**
  Worker shutdown signal handler catches `SIGTERM`. Signals process group with `SIGTERM` / `terminate()`, grants 5-second grace period for clean exit, escalates to process-group `SIGKILL` / Job Object termination, and actively verifies descendant termination. Workspace preserved safely for GC reclamation.

---

### 11.3 Durable External Cleanup Failure Recovery & Escalation (Container-Persistent Storage)
If a filesystem permission issue, file lock (e.g. Windows `WinError 32`), or underlying storage glitch prevents workspace deletion, relying on an in-directory marker (`.cleanup_failed`) is fragile because the same filesystem issue may prevent writing inside that directory. Furthermore, storing failure records in `{SCRATCH_DIR}` is insufficient because local container scratch storage is ephemeral and destroyed upon container replacement (`docker compose up -d --force-recreate worker`).

Revision 2.1 enforces **deployment-durable cleanup tracking hosted on the persistent Docker named volume `staging_data` with an in-database fallback**:

#### 1. Exact Storage Location on Persistent Named Volume (`staging_data`)
All cleanup failure records are stored strictly **outside** the target workspace directory and placed on the persistent shared storage volume:
- **Dedicated Storage Root:** `{STAGING_DIR}/.cleanup_failures/` (e.g., `/var/lib/quantumflow/staging/.cleanup_failures/`).
- **Persistent Volume Backing:**
  In `docker-compose.yml`, both `api` and `worker` services mount the persistent named volume `staging_data` to `/var/lib/quantumflow/staging`.
  Because Docker named volumes are managed independently of container lifecycles, files written to `{STAGING_DIR}/.cleanup_failures/` **survive worker container restarts, stops, container recreations, image updates, and container replacement**.
- **Initialization & Directory Verification:**
  At worker startup:
  - `os.makedirs(staging_dir / ".cleanup_failures", mode=0o700, exist_ok=True)`
  - `st = os.lstat(staging_dir / ".cleanup_failures")`
  - `assert not os.path.islink(staging_dir / ".cleanup_failures")`
  - `assert stat.S_ISDIR(st.st_mode)`
  - `assert (st.st_mode & 0o777) == 0o700` (mode `0700` strictly owned by worker user `quantumflow`).

#### 2. File Permissions & Tenant Isolation
- **Permissions:** Directory mode `0700` (`rwx------`) and file mode `0600` (`rw-------`) ensure that only the worker process user can read or write failure records.
- **Path Sanitization:** Filenames are strictly formatted as `{workspace_basename}.json`. The cleaner strictly validates `re.match(r"^job_[0-9a-fA-F-]{36}_[0-9a-fA-F]{12}$", workspace_basename)` before any filesystem operation, eliminating directory traversal risks.
- **Tenant Isolation:** The `.cleanup_failures/` directory resides at the root of `STAGING_DIR`, outside tenant upload trees (`{STAGING_DIR}/{tenant_id}/`). The leading dot (`.`) ensures that directory enumerations and tenant-scoped API routes never list, access, or expose cleanup failure descriptors over HTTP.

#### 3. Four-Step Atomic Failure-Record Creation & Crash Durability
When `shutil.rmtree(workspace)` raises `OSError` in the worker `finally:` block:
1. The error is explicitly logged (never suppressed):
   `SCRATCH_CLEANUP_FAILURE: Failed to remove workspace {workspace}: {exc}`.
2. The worker performs a **4-step crash-durable atomic file write**:
   - **Step 1 (Uniquely Created Temporary File):** Creates `{STAGING_DIR}/.cleanup_failures/{workspace_basename}.{uuid4().hex}.tmp`. Using a unique UUID per write eliminates collisions across concurrent processes or retries.
   - **Step 2 (Data & File Inode Flush):** Writes JSON content, flushes user-space buffers (`f.flush()`), and executes physical disk synchronization: `os.fsync(f.fileno())`.
   - **Step 3 (Atomic Replacement):** Atomically renames temporary file to target: `os.replace(tmp_path, target_path)`. (Atomic on POSIX and Windows).
   - **Step 4 (Parent-Directory Metadata Synchronization):**
     - **POSIX / Linux Platforms:** Opens the parent directory and explicitly syncs directory metadata to physical storage:
       ```python
       try:
           dir_fd = os.open(str(parent_dir), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
           try:
               os.fsync(dir_fd)
           finally:
               os.close(dir_fd)
       except OSError:
           pass
       ```
     - **Windows Platform Directory Flushing & Durability Limitations:** On Windows, invoking `os.fsync` or Win32 `FlushFileBuffers` on a directory file handle is unsupported by the standard Python runtime and raises `OSError` / WinError 6 (Invalid Handle). While native Win32 `CreateFileW` with `FILE_FLAG_BACKUP_SEMANTICS` can open directory handles, standard Python runtime does not expose verified synchronous directory platter commit. Furthermore, NTFS metadata journaling ($LogFile) guarantees file system internal structural consistency upon reboot, but does NOT guarantee immediate physical platter flush of the directory index ($INDEX_ROOT/$INDEX_ALLOCATION) upon sudden power loss. Consequently, on Windows there is a weaker durability window where sudden host power loss immediately after `os.replace` could lose the updated directory entry or leave an orphaned `.tmp` file.
   - **Startup Reconciliation Protocol (Compensating for Crash Durability Limitations):**
     To ensure zero state loss across sudden power failures or unclean container terminations on any platform:
     1. At worker startup, the GC daemon scans `{STAGING_DIR}/.cleanup_failures/` and unlinks any orphaned `*.tmp` files older than 10 minutes.
     2. It inspects all entries in `{SCRATCH_DIR}`, cross-referencing each with PostgreSQL `discovery_jobs`.
     3. It reads `discovery_jobs.result_summary['cleanup_failure']` across all jobs; if a database record exists but the corresponding volume file was lost due to an unclean reboot, the record file is reconstructed on disk.
     4. It inspects `.quarantine.json` records; if the host has rebooted, the recorded child PIDs are confirmed dead, allowing quarantined workspaces to safely transition to cleanup.
   - Record contents:
     ```json
     {
       "workspace_path": "/var/lib/quantumflow/scratch/job_9b1deb4d_a1b2c3d4e5f6",
       "workspace_basename": "job_9b1deb4d_a1b2c3d4e5f6",
       "job_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
       "tenant_id": "tenant-corp",
       "assessment_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
       "first_failed_at": "2026-11-03T11:30:00Z",
       "last_failed_at": "2026-11-03T11:45:00Z",
       "attempts": 1,
       "status": "pending_retry",
       "last_error": "PermissionError: [WinError 32] The process cannot access the file because it is being used by another process"
     }
     ```
3. On subsequent hourly sweeps, the cleaner reads the descriptor, increments `attempts`, updates `last_failed_at`, and rewrites the record using the exact same 4-step protocol.

#### 4. Behaviour If Failure-Record Persistence Itself Fails (Selective In-Database Fallback)
If the persistent staging volume itself experiences an I/O error, read-only remount, or disk-full condition preventing writing the failure descriptor:
1. **Primary Critical Log:** The worker logs an immediate high-priority alert to `sys.stderr`:
   `CRITICAL_CLEANUP_PERSISTENCE_FAILURE: Could not write cleanup failure record for workspace {workspace} to {target_path}: {exc}`.
2. **Selective In-Database Fallback (Zero Migrations):** The worker executes an atomic database update targeting the existing `result_summary` JSONB column of `discovery_jobs` using a SQLAlchemy-compatible cast:
   ```sql
   UPDATE discovery_jobs
   SET result_summary = jsonb_set(
       COALESCE(result_summary, '{}'::jsonb),
       '{cleanup_failure}',
       CAST(:failure_payload AS jsonb),
       true
   )
   WHERE id = :job_id;
   ```
   - **Key Preservation Guarantee:** Using `jsonb_set(..., '{cleanup_failure}', CAST(:failure_payload AS jsonb), true)` strictly updates **only the `cleanup_failure` key** within `result_summary`. All other existing keys (e.g. `cbom_asset_count`, `tls_observations`, `qvi_score`) are **strictly preserved intact**.
   - **Affected-Row Count Check:**
     The worker inspects `cursor.rowcount`:
     - If `rowcount == 1`: Update succeeded and failure is durably recorded in PostgreSQL.
     - If `rowcount == 0`: The `job_id` record does not exist in `discovery_jobs`! The worker logs:
       `CRITICAL_FALLBACK_RECORD_MISSING: Cannot persist cleanup failure to database; job {job_id} does not exist. Workspace {workspace} marked as orphaned quarantine.`
       The workspace is preserved on disk for operator inspection.
3. **Emergency Failure Handling:**
   If the database fallback itself fails (e.g. PostgreSQL disconnect or operational error):
   The worker emits an emergency structured log to `sys.stderr`:
   `EMERGENCY_CLEANUP_FALLBACK_FAILED: Both persistent volume write and database fallback failed for workspace {workspace}: {exc}`.
   The workspace is preserved strictly untouched on disk. Deletion is forbidden.

#### 5. Active-Worker Verification Before Retry
Before the GC daemon attempts to retry deleting an entry from `.cleanup_failures/`:
1. It queries `discovery_jobs` to verify that `job_id` is terminal (`completed`, `failed`, `cancelled`) or a lease-expired zombie.
2. It attempts to acquire `pg_try_advisory_xact_lock(derive_job_scratch_lock_key(job_id))`.
3. If the lock is held by an active worker, retry is deferred immediately.
4. **Authoritative State Rule:** A cleanup failure descriptor **never overrides the database's authoritative active-job ownership state**. If the database indicates the job is actively leased or running, the workspace is preserved.

#### 6. Escalation Threshold & Operator Recovery Procedure
- **Retry Ceiling:** GC increments `attempts` on each hourly retry cycle.
- **Escalation Trigger:** If `attempts >= 5`:
  - The record's status is updated to `"escalated_manual_intervention_required"`.
  - Automatic deletion retries are halted to avoid continuous I/O thrashing and log spam.
  - A high-priority structured alert is emitted:
    `CRITICAL_SCRATCH_DIR_LEAK: Workspace {workspace} has failed 5 consecutive cleanup attempts (Last error: {last_error}). Retries halted. Preserving for operator inspection.`
  - The workspace remains preserved on disk for forensic examination.
- **Operator Recovery & Manual Inspection Procedure:**
  Operators inspect and resolve escalated workspaces using:
  ```bash
  # 1. List all persistent cleanup failures and escalation states across containers
  python -m services.worker.app.worker --list-cleanup-failures

  # 2. Inspect raw descriptors on the persistent volume
  cat /var/lib/quantumflow/staging/.cleanup_failures/*.json

  # 3. Retry cleanup once underlying file locks or permissions are resolved
  python -m services.worker.app.worker --retry-cleanup-failures

  # 4. Force-purge an abandoned workspace and unlink its persistent failure descriptor
  python -m services.worker.app.worker --force-purge-failure job_9b1deb4d_a1b2c3d4e5f6
  ```

### 11.4 Resource Ceilings & Actual Bytes Written Validation
| Parameter | Limit | Enforcement Mechanism | Failure Consequence |
|---|:---:|---|---|
| **Compressed Upload Ceiling** | **20 MB** (`MAX_ARCHIVE_BYTES`) | Chunk-by-chunk streaming in `POST /stage-upload` | Abort stream; delete `.part`; `HTTP 413` |
| **Standalone Manifest Ceiling** | **5 MB** (`MAX_MANIFEST_BYTES`) | Chunk-by-chunk streaming in `POST /stage-upload` | Abort stream; delete `.part`; `HTTP 413` |
| **Uncompressed Expanded Ceiling** | **200 MB** (`MAX_UNCOMPRESSED_BYTES`) | Tracked actual bytes written chunk-by-chunk | Abort extraction; wipe scratch; `ArchiveSecurityError` |
| **Maximum Extracted File Count** | **500 files** (`MAX_FILE_COUNT`) | Counter incremented on every created file | Abort extraction; wipe scratch; `ArchiveSecurityError` |
| **Single File Size Ceiling** | **10 MB** (`MAX_SINGLE_FILE_BYTES`) | Tracked bytes written per individual file | Abort extraction; wipe scratch; `ArchiveSecurityError` |
| **Nested Archive Ceiling** | **0 nested archives** | Rejected during member inspection | Member skipped or rejected; `ArchiveSecurityError` |

- **Actual Bytes Written Validation:** During decompression, the extractor tracks actual bytes written to disk chunk-by-chunk, ignoring potentially spoofed header size fields (`ZipInfo.file_size` / `TarInfo.size`). If total uncompressed bytes exceed 200MB or a single file exceeds 10MB, extraction aborts immediately and wipes the scratch directory.
- **Member Path Traversal & Special File Rejection:** Rejects Zip Slip, absolute paths, Windows drive paths (`^[a-zA-Z]:`), symlinks, hardlinks, TAR special devices/FIFOs, and colliding normalized names.
- **Secret Sniffing:** Sniffs first 4KB for PEM private key headers; excludes `.env`, `credentials.json`, `service_account.json`, and SSH keys.

---

## 12. Authenticated Complete HTTP Report Delivery Semantics

An audit of [`packages/reports/exporter.py`](file:///d:/Desktop/quantum-flow-pqc-platform/packages/reports/exporter.py) confirms the exact execution model of the Phase 1 reporting engine:

### 12.1 Materialization Audit Finding
```python
def export_assessment_cyclonedx(snapshot: dict[str, Any]) -> dict[str, Any]: ...
def export_assessment_csv(snapshot: dict[str, Any]) -> str: ...
def export_assessment_markdown_report(snapshot: dict[str, Any], stored_hash: str | None = None) -> str: ...
```
- **Finding:** The Phase 1 exporters do **not** use generator-based chunked streaming; they materialize the report document entirely in memory as a dictionary or string.
- **Architectural Rationale:**
  1. The entire terminal snapshot is already loaded in memory from PostgreSQL (`report_snapshot` in `Assessment`, typically 15KB to 2MB).
  2. Cryptographic verification `verify_and_load_snapshot` requires the full snapshot in memory to compute the canonical RFC 8785 SHA-256 digest before export begins.
  3. CycloneDX 1.6 requires cross-component dependency graph resolution that cannot be streamed without full component availability.

### 12.2 Complete HTTP Response Delivery Lifecycle
Rather than using a misleading chunked `StreamingResponse` without `Content-Length` (which masks disconnects and streaming errors), the API serves reports via FastAPI's standard `Response` (or `JSONResponse`):

1. **Verification Gate:** Retrieve `Assessment` by ID; verify caller tenant. Verify status is terminal (`completed`, `partially_completed`, `failed`, `cancelled`). Recompute RFC 8785 SHA-256 over `report_snapshot`; assert constant-time match with `report_snapshot_hash`. If mismatched, abort with `HTTP 500 Internal Server Error`.
2. **In-Memory Materialization:** Execute exporter function (`export_assessment_cyclonedx`, `export_assessment_csv`, or `export_assessment_markdown_report`).
3. **HTTP Response Packaging:**
   - **CycloneDX 1.6 JSON:**
     `media_type="application/vnd.cyclonedx+json"`
     `headers={"Content-Disposition": f'attachment; filename="cbom-{assessment_id}.json"'}`
   - **RFC 4180 CRLF CSV:**
     `media_type="text/csv; charset=utf-8"`
     `headers={"Content-Disposition": f'attachment; filename="cbom-{assessment_id}.csv"'}`
   - **Executive Markdown:**
     `media_type="text/markdown; charset=utf-8"`
     `headers={"Content-Disposition": f'attachment; filename="report-{assessment_id}.md"'}`
4. **Memory Footprint Bounds:**
   - 500 assets: CSV $\approx$ 100 KB, CycloneDX $\approx$ 250 KB, Markdown $\approx$ 25 KB.
   - 5,000 assets (extreme enterprise run): $\approx$ 2.5 MB in memory.
   - This in-memory model is deterministic, fast, provides exact `Content-Length`, and eliminates stream buffering defects.

---

## 13. File-by-File Change Inventory

| File Path | Action | Description of Planned Changes |
|---|:---:|---|
| `services/api/app/core/config.py` | Modify | Add `staging_dir: str = Field(default="./staging_data")` and `scratch_dir: str = Field(default="./scratch")` to `Settings`. |
| `services/api/app/main.py` | Modify | Add `RequestBodyLimitMiddleware` enforcing 25MB request-body limit prior to multipart parsing. |
| `services/api/app/schemas/assessment.py` | Modify | Add `StagedUploadResponse` and `UploadTokenMetadata`. Add optional `upload_token` field to `AssessmentCreateRequest`. |
| `services/api/app/api/v1/endpoints/assessments.py` | Modify | Implement `POST /stage-upload` accepting raw `Request`, acquiring slot advisory lock before `request.form()`, reserving storage quota atomically, streaming to `.part`, and report download routes `GET /reports/*` using complete verified HTTP responses. |
| `services/api/app/services/assessment_service.py` | Modify | Add transaction advisory lock token claiming, cross-tenant collision detection, worker lazy metadata reconciliation, isolated scratch creation (`0700`), read-only archive extraction, and terminal cleanup hook. |
| `packages/scanner/source/archive.py` | Modify | Harden extraction: validate actual decompressed bytes written on disk, enforce `0700` scratch workspace, descriptor-relative writes on POSIX, explicit error logging on cleanup (`.cleanup_failed`), and reject Zip Slip, drive paths, symlinks, and special files. |
| `services/worker/app/worker.py` | Modify | Implement hourly 5-state database-authoritative Garbage Collection daemon with descriptor-relative (`dir_fd`) POSIX cleanup, safe Windows fallback, active-lease-aware scratch GC, and `.cleanup_failed` orphan retry. |
| `docker-compose.yml` | Modify | Declare `staging_data` volume and mount at `/var/lib/quantumflow/staging` in `api` and `worker` services. |
| `tests/integration/test_staged_upload.py` | **Create** | Integration tests covering staging lifecycle, slot lock acquired before `request.form()`, slot lock held across stream, atomic storage quota reservation, worker extraction, scratch isolation, retry preservation, active-job scratch preservation (>30m), terminal cleanup, 5-state GC, and TOCTOU defense. |
| `tests/integration/test_assessment_report_api.py` | **Create** | Integration tests covering complete HTTP report delivery, media types, disposition headers, active 409 conflict, 401 auth, and 500 hash tampering rejection. |

---

## 14. Comprehensive Testing Strategy

### 14.1 Staged Upload Integration Suite (`test_staged_upload.py`)
1. **Pre-Parsing Slot Lock Acquisition:** Prove slot lock is acquired before Starlette multipart parsing starts; assert that an unauthenticated or slot-saturated request rejects before body chunks are parsed.
2. **Cluster-Wide Global Concurrency & Advisory Lock Slots:**
    - Tier 1 (Global Slots 0..9): Verify acquisition of shared global upload slots across multiple simulated API processes; assert 11th concurrent upload cluster-wide is rejected with HTTP 429.
    - Tier 2 (Per-Tenant Slots 0..2): Verify acquisition of per-tenant slots within the same transaction; assert 4th concurrent upload for a single tenant is rejected with HTTP 429.
    - Cluster-Wide Rollback: Verify that client disconnect or upload failure releases both the global slot lock and tenant slot lock automatically without database migrations.
3. **Atomic Storage Quota Reservation & In-Flight Accounting:** Verify concurrent uploads under the same tenant update `reservation.json` and count accurately; verify that reserved bytes ($20\text{MB}$) count against the 100MB quota.
4. **Slot-Lock Guard for In-Progress Reservations:** Simulate active upload holding slot lock for $>300$ seconds; assert GC detects active slot advisory lock and preserves reservation and `.part` file.
5. **Atomic Metadata Replacement & Finalization Crash Recovery:** Simulate crash where both `metadata.json` and `reservation.json` exist; assert `metadata.json` takes precedence and redundant reservation is cleaned without data loss.
6. **Valid Staged Upload:** Upload 1MB valid ZIP; verify `.part` rename, `metadata.json`, and 201 response.
7. **Ceiling Enforcement:** Upload 21MB archive; assert streaming aborts with HTTP 413.
8. **ASGI Body Limit Middleware:** Send 26MB request; assert middleware rejects with HTTP 413 before multipart parser spools file to disk.
9. **Chunked Request Capping:** Send chunked stream exceeding 25MB; assert stream is capped and terminated with HTTP 413.
10. **Client Disconnect During Upload:** Simulate client aborting connection mid-upload; assert slot lock is auto-released and partial `.part` is unlinked.
11. **Actual Bytes Written Validation:** Decompress archive with spoofed header; assert extraction aborts when actual written bytes exceed ceiling.
12. **Scratch Workspace Isolation:** Assert scratch workspace is created exclusively with `0700` permissions.
13. **Worker–GC Advisory Lock Mutual Exclusion:** Worker holds `qf:job_scratch:{job_id}`; assert GC `pg_try_advisory_xact_lock` returns `False` and defers deletion.
14. **64-Bit Advisory Lock Real Driver Verification Suite:**
    - Test A (Owning Session Detection): Execute actual verification query against live PostgreSQL using application's `asyncpg` driver; verify owning session detects its lock matching `classid = CAST(:classid AS oid)`, `objid = CAST(:objid AS oid)`, `objsubid=1`, `pid=pg_backend_pid()`, `mode='ExclusiveLock'`, and `granted=true`.
    - Test B (Non-Owning Session Exclusion): Verify different session checking `pg_locks` for its own PID returns false.
    - Test C (Disconnection Cleanup): Verify disconnected session automatically releases lock and drops from `pg_locks`.
    - Test D (Different Key Independence): Verify lock on a different key does not produce false positives.
    - Test E (Parameter Range Validation): Verify binding `classid` or `objid` outside `[0, 4294967295]` raises `ValueError` before execution.
15. **Windows Suspended-Process Job Object Containment:** On Windows, verify process launch with `CREATE_SUSPENDED`, verify assignment to Job Object with breakaway disabled before thread resumption, assert that killing Job Object terminates all descendants, and verify `NumberOfProcessIdsInList == 0`.
16. **POSIX Whole-Group Descendant & Anti-Escape Verification:** On POSIX, launch process group with `start_new_session=True`; simulate leader process exiting while descendant remains in PGID; assert parent polling `/proc/*/stat` detects lingering descendant with `pgrp == original_pgid` and prevents workspace deletion.
17. **Multi-Factor Quarantine, Boot ID & Leader-Exit Resilience:** Simulate unkillable descendant process; assert worker creates `.quarantine.json` with multi-factor identity (leader PID, create time, boot ID, PGID, Job Object name). Simulate PID recycling (new process with same PID but different creation time); assert GC evaluates `/proc` for whole PGID and boot ID, safely reclaiming only when the entire group is confirmed dead.
18. **Kernel-Safe `/proc/[pid]/stat` Parsing with Complex Comm Names:** Simulate `/proc/[pid]/stat` content where executable name (`comm`) contains whitespace, nested parentheses, and brackets (e.g. `1234 (scanner (worker) v2) R 1000 1234 1234 ...` or `5678 (python ) bad) S 1000 1234 1234 ...`); verify that `parse_proc_stat` isolates fields using `rfind(')')`, extracting `pgrp` (field 5) from `remainder[2]` and `starttime` (field 22) from `remainder[19]` without field shifting.
19. **Indeterminate `/proc` Scan Rejection & Cleanup Halt:** Simulate a `/proc` scan where a process entry raises `PermissionError` or is truncated/malformed; assert that `scan_active_pgid_descendants` returns `is_scan_conclusive = False`, worker and GC refuse to conclude that the process group is empty, halt workspace deletion, treat the workspace as locked/quarantined, and preserve all files intact.
20. **Concurrent Process Exit Tolerance (`ENOENT` Safe Handling):** Simulate a process terminating concurrently between `/proc` directory enumeration and file read (raising `FileNotFoundError` / `ENOENT`); assert that the exception is safely ignored as a standard kernel race, `is_scan_conclusive` remains `True`, and genuine group membership is accurately reported.
21. **Worker Deletion Prohibition on Lock Loss:** Simulate worker losing lock ownership; assert worker does NOT invoke `shutil.rmtree` and yields workspace intact to GC zombie recovery.
22. **Active Job Scratch Preservation:** Simulate active job running for 40 minutes (with active worker lease and advisory lock); assert scratch GC does **not** delete the active workspace.
23. **Missing Job Record Integrity Guard:** Simulate scratch workspace with unknown `job_id`; assert GC preserves workspace and logs `CRITICAL_ORPHAN_SCRATCH_DIR` without deleting.
24. **Four-Step Atomic Cleanup-Record Creation:** Verify cleanup failure writes use unique temporary files (`.tmp`), `os.fsync`, atomic `os.replace`, and parent directory sync on POSIX.
25. **Startup Reconciliation Suite:** Simulate unclean shutdown with lingering `.tmp` files and orphaned scratch dirs; assert worker startup reconciles database records, cleans stale `.tmp`, and reclaims dead quarantine PIDs.
26. **Container-Persistent Cleanup Failure Recovery:** Simulate file lock during scratch cleanup; assert failure descriptor written in `{STAGING_DIR}/.cleanup_failures/` on persistent named volume `staging_data`, verify attempt counts survive simulated worker container replacement, and assert escalation alert after 5 failed attempts.
27. **Selective In-Database Cleanup Failure Fallback & Rowcount Check:** Simulate write failure on staging volume; assert worker executes `CAST(:failure_payload AS jsonb)`, verify all other `result_summary` fields remain untouched, and assert `rowcount == 0` triggers `CRITICAL_FALLBACK_RECORD_MISSING` preserving workspace.
28. **Zip Slip & Path Traversal Rejection:** Attempt to extract archive containing `../etc/passwd` or `C:\malicious`; assert `ArchiveSecurityError`.
29. **Symlink and Hardlink Rejection:** Attempt to extract archive with symlinks/hardlinks; assert links rejected.
30. **Colliding Path Rejection:** Attempt to extract archive with colliding case-insensitive paths; assert rejection.
31. **Transaction Advisory Lock Serializes Claim:** Concurrent creation attempts on same token; assert first succeeds, second returns HTTP 409.
32. **Cross-Tenant Collision Protection:** Attempt to bind token under different tenant; assert HTTP 409 Conflict.
33. **Worker Lazy Metadata Reconciliation:** Commit assessment with `assessment_id: null` in metadata; assert worker reconciles upon job claim.
34. **Retry Preservation:** Job fails with `retry_count < max_retries`; assert archive preserved in staging.
35. **Terminal Cleanup Hook:** Assessment reaches `completed`; assert staging directory safely removed.
36. **5-State GC Classification:**
    - State 1: Expired unbound upload (>4h) purged; active upload (<4h) preserved; corrupt metadata preserved.
    - State 2: Active assessment archive preserved; terminal finalized archive purged.
    - State 3: Mismatched/null tenant preserved and alert logged.
    - State 4: Multiple matching records preserved and alert logged.
    - State 5: Cross-tenant records preserved and alert logged.
37. **Descriptor-Relative Symlink Validation:** Create symlinked path component; assert GC detects link, aborts deletion, and preserves directory.

### 14.2 Report Delivery API Suite (`test_assessment_report_api.py`)
1. **Active Assessment Conflict:** Request reports for `queued`/`running` assessment; assert `HTTP 409 Conflict`.
2. **Unauthenticated Rejection:** Request report without token in staging/prod; assert `HTTP 401 Unauthorized`.
3. **Cross-Tenant Isolation:** Request report owned by another tenant; assert `HTTP 404 Not Found`.
4. **Tamper Rejection:** Modify stored report snapshot; assert `HTTP 500 Internal Server Error` with snapshot verification failure.
5. **CycloneDX 1.6 Delivery:** Assert `Content-Type: application/vnd.cyclonedx+json`, RFC 5987 filename, valid JSON, Content-Length present, and schema compliance.
6. **CSV Delivery:** Assert `Content-Type: text/csv`, RFC 5987 filename, strict CRLF delimiters, Content-Length present, and formula sanitization.
7. **Markdown Delivery:** Assert `Content-Type: text/markdown`, RFC 5987 filename, Maximum Asset QVI header, Content-Length present, and integrity seal.

---

## 15. Acceptance Criteria Checklist

- [ ] `POST /api/v1/assessments/stage-upload` acquires two-tier advisory locks (global slots 0..9 and tenant slots 0..2) **before triggering `request.form()`** and holds locks throughout streaming.
- [ ] Cluster-wide upload concurrency is enforced across all API containers via PostgreSQL advisory locks without database migrations or process-local semaphores.
- [ ] Storage quota reservation is decoupled into a short-lived transaction ($<5\text{ms}$), tracking active `reservation.json` files and reserved bytes ($20\text{MB}$) without serializing file transfers.
- [ ] GC Upload-Slot Guard preserves in-progress reservations >300s old while their upload-slot advisory lock remains active.
- [ ] Three-step atomic metadata persistence (`metadata.json.tmp` -> `metadata.json` -> `unlink reservation.json`) prevents crash inconsistency.
- [ ] ASGI middleware enforces a 25MB ceiling on `Content-Length` and caps chunked streams before downstream exhaustion.
- [ ] Staged uploads use atomic `.part` rename and atomic metadata persistence.
- [ ] Assessment creation acquires a 64-bit PostgreSQL transaction advisory lock derived from `hash(upload_token)`.
- [ ] Canonical tenant ownership is verified against `Assessment.target_snapshot["tenant_id"]`.
- [ ] Cross-tenant or missing tenant token references reject with HTTP 409 Conflict.
- [ ] Worker acquires 64-bit advisory lock on a dedicated pinned connection and verifies ownership in `pg_locks` with explicit OID casts (`CAST(:classid AS oid)`, `CAST(:objid AS oid)`, `objsubid=1`) without lock-count inflation.
- [ ] Windows processes launch in a suspended state (`CREATE_SUSPENDED`), assign to a Job Object with `KILL_ON_JOB_CLOSE` (breakaway flags strictly disabled), and resume only after successful assignment.
- [ ] POSIX processes launch in a dedicated session with anti-escape controls; termination verifies that all descendants in `/proc/*/stat` (parsed strictly after final `)` to prevent field shifting from whitespace/brackets in process names) have exited, and incomplete/unverified `/proc` scans fail closed and halt cleanup.
- [ ] An incomplete or indeterminate `/proc` scan (due to `PermissionError`, `EIO`, or malformed stat entries) is treated as unverified, immediately halting cleanup and preserving the workspace.
- [ ] Quarantined workspaces persist multi-factor identity (boot ID, PGID, create times) in `.quarantine.json`, guarding against leader exit and PID recycling, and permanently barring GC deletion until process death is confirmed.
- [ ] Worker strictly prohibits workspace deletion upon losing lock ownership, safely yielding directory to GC recovery.
- [ ] Scratch workspace GC coordinates with PostgreSQL job leases and never purges workspaces belonging to active jobs, even if running $>30$ minutes.
- [ ] Scratch workspaces with missing database records are preserved and logged as `CRITICAL_ORPHAN_SCRATCH_DIR` rather than blindly deleted.
- [ ] Scratch cleanup failures are durably tracked on the persistent named volume `staging_data` in `{STAGING_DIR}/.cleanup_failures/` using 4-step atomic write and startup reconciliation.
- [ ] Fallback persistence uses `CAST(:failure_payload AS jsonb)`, checks `rowcount`, and preserves all other keys with zero database migrations.
- [ ] Archive extraction validates actual decompressed bytes written on disk, rejecting Zip Slip, drive paths, symlinks, and special files.
- [ ] Workers lazily reconcile `metadata.json` if API crashes after database commit.
- [ ] Staged archives are preserved while assessments are active or retryable.
- [ ] Staged archives are safely cleaned up once assessments reach terminal completion or exhausted retries.
- [ ] Background worker GC executes hourly 5-state classification and never deletes ambiguous or multiple records.
- [ ] GC enforces descriptor-relative (`dir_fd`) operations with `O_NOFOLLOW` on POSIX, and hardened safe fallback on Windows.
- [ ] `GET /api/v1/assessments/{id}/reports/cyclonedx` delivers complete verified CycloneDX 1.6 CBOM JSON response.
- [ ] `GET /api/v1/assessments/{id}/reports/csv` delivers complete verified RFC 4180 CRLF CSV response with formula mitigation.
- [ ] `GET /api/v1/assessments/{id}/reports/markdown` delivers complete verified Executive Markdown response.
- [ ] Report delivery enforces terminal status (409 on active) and verifies snapshot SHA-256 (500 on tamper).
- [ ] Zero database migrations created; zero QVI mathematical changes introduced.
- [ ] All integration and security tests pass cleanly.

---

## 16. Rollback and Failure-Handling Considerations

- **PostgreSQL Advisory Lock Auto-Release:** If an API worker or database transaction crashes mid-operation, PostgreSQL automatically releases all transaction-scoped advisory locks upon connection termination. No persistent locks are orphaned.
- **Filesystem Cleanup Failures:** If an OS `PermissionError` occurs during directory deletion (e.g. temporary Windows file lock), GC catches `OSError`, logs `DELETION_DEFERRED`, and retries on the next hourly cycle without interrupting the worker daemon.
- **Rollback Safety:** Because Phase 2 introduces zero database migrations and zero schema changes, rolling back requires only reverting application code files without touching PostgreSQL tables.
