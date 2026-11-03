# Quantum Flow Engineering Development Backlog

## 1. Backlog Governance & Conventions

- **Product:** Quantum Flow Technologies — Post-Quantum Cryptography (PQC) Discovery & Risk Assessment Platform
- **Document Status:** Initial Master Engineering Backlog (Sprint 0 through Sprint 7)
- **Primary Source:** Implementation Blueprint & Repository Setup v1.0
- **Status Standard:** In accordance with strict engineering integrity rules, **all initial task statuses are set to `NOT STARTED`** until code and verified test suites are committed and merged.
- **Priority Scale:**
  - **P0 (Blocker):** Fundamental architecture, security safety, or data integrity prerequisite. Must be completed before dependent tasks can start.
  - **P1 (High):** Core capability required for the minimum viable discovery and assessment slice.
  - **P2 (Medium):** Important usability, enhancement, or operational capability.
  - **P3 (Low):** Nice-to-have or future enhancement.

---

## 2. Sprint 0 — Repository and Engineering Foundation

| Task ID | Task Title | Priority | Dependencies | Status |
|---|---|---|---|---|
| **QF-001** | Confirm repository structure and baseline monorepo directories | P0 | None | COMPLETED |
| **QF-002** | Add root-level engineering configuration and documentation index | P0 | None | COMPLETED |
| **QF-003** | Configure Python 3.12 and frontend package definitions (`pyproject.toml`, `package.json`) | P0 | QF-001 | COMPLETED |
| **QF-004** | Create Docker Compose for local PostgreSQL 16 and Redis 7 | P0 | QF-001 | COMPLETED |
| **QF-005** | Create FastAPI application skeleton with `/healthz` endpoint | P1 | QF-003 | COMPLETED |
| **QF-006** | Create React / Vite frontend skeleton with basic navigation | P1 | QF-003 | COMPLETED |
| **QF-007** | Setup linting, formatting, and type-checking tooling (Ruff, Mypy) | P0 | QF-003 | COMPLETED |
| **QF-008** | Implement GitHub Actions pull request CI pipeline | P1 | QF-007 | COMPLETED |
| **QF-009** | Draft and submit initial Architecture Decision Record (ADR-0001) | P1 | QF-001 | COMPLETED |

---

## 3. Sprint 1 — Target Management & Bounded TLS Discovery Milestone

### Sprint 1 Core Deliverables

| Task ID | Task Title | Priority | Dependencies | Status |
|---|---|---|---|---|
| **QF-001** | Target registration and management API (Strict FQDN syntax, CRUD, verification challenge, state transitions) | High | QF-004, QF-005 | VERIFIED |
| **QF-002** | SSRF and DNS rebinding safety engine (Multi-stage resolution, denylist, unwrap IPv4-mapped IPv6, IP pinning, SEC-001 timeout/concurrency bounds) | Critical | None | VERIFIED |
| **QF-003** | Bounded TLS handshake collector (Port 443 only, pinned IP, strict SNI, X.509 evidence, no key-exchange fabrication, TEST-001 SNI regression protection) | High | QF-002 | VERIFIED |
| **QF-007** | Observation ingestion and initial CBOM schema (Alembic migration, raw JSONB payload, provenance SHA-256, DATA-001 canonical digest) | High | QF-001, QF-003 | VERIFIED |

### Sprint 1 Backlog Breakdown & Persistence

| Task ID | Task Title | Priority | Dependencies | Status |
|---|---|---|---|---|
| **QF-010** | Configure SQLAlchemy 2.0 and Alembic migration framework | P0 | QF-004, QF-005 | COMPLETED |
| **QF-011** | Implement Tenants, Users, and Projects persistence schema | P0 | QF-010 | NOT STARTED |
| **QF-012** | Implement Targets and Target Safety validation schema | P0 | QF-011 | COMPLETED |
| **QF-013** | Implement Authorisations model and verification logic | P0 | QF-012 | COMPLETED |
| **QF-014** | Implement ScanJobs domain entity and initial schema | P0 | QF-013 | COMPLETED |
| **QF-015** | Build REST API endpoints for Projects, Targets, and Authorisations | P1 | QF-011, QF-012, QF-013 | COMPLETED |
| **QF-016** | Implement tenant context dependency and repository isolation tests | P0 | QF-011, QF-015 | NOT STARTED |
| **QF-022** | Implement target validation filter and SSRF private IP blocker | P0 | QF-012, QF-018 | COMPLETED |
| **QF-023** | Implement two-stage DNS rebinding defense and worker socket binding | P0 | QF-022 | COMPLETED |
| **QF-024** | Implement bounded TLS handshake and socket timeout manager | P1 | QF-023 | COMPLETED |
| **QF-025** | Implement X.509 certificate chain extractor and ASN.1 parser | P1 | QF-024 | COMPLETED |
| **QF-028** | Implement raw observation schema and immutable JSONB storage | P0 | QF-010, QF-025 | COMPLETED |
| **QF-038** | Implement React Projects and Targets management interface | P1 | QF-006, QF-015 | COMPLETED |

---

## 4. Sprint 2 — Cryptographic Discovery & Risk Intelligence Milestone

### Sprint 2 Core Deliverables

| Task ID | Task Title | Priority | Dependencies | Status |
|---|---|---|---|---|
| **QF-DISC-01** | Discovery Job Execution Engine (PostgreSQL durable state, SKIP LOCKED concurrency, worker leases, zombie recovery, duplicate prevention) | High | QF-010, QF-014 | VERIFIED |
| **QF-SRC-01** | Source Code Cryptographic Discovery (Python AST analysis; JS/TS and Java regex pattern matching; Zip Slip, Bomb, and Private Key defense with 50MB ceiling) | High | QF-DISC-01 | VERIFIED |
| **QF-DEP-01** | Dependency Manifest Scanner (Declared dependencies from requirements.txt, package.json, pom.xml; lockfile-resolved records from poetry.lock, package-lock.json; crypto library classification; 5MB manifest size limit) | High | QF-SRC-01 | VERIFIED |
| **QF-CFG-01** | Configuration Import Engine (Nginx ssl_protocols/ciphers, Apache SSL, Kubernetes Ingress TLS parsing; private keys never stored) | High | None | VERIFIED |
| **QF-CBOM-01** | CBOM Asset Correlation Engine (Deterministic asset keys, CryptographicAsset, AssetObservation, AssetRelationship graph, CycloneDX 1.6) | Critical | QF-007, QF-SRC-01 | VERIFIED |
| **QF-RISK-01** | Quantum Risk Rules Engine (Methodology v1.0, 8 dimensions [7 weighted Q/R/L/E/B/M/V summing to 950 raw points, unweighted D8 evidence quality, 0–1000 prioritization scale], Shor vs Grover, traceable recommendations) | Critical | QF-CBOM-01 | VERIFIED |
| **QF-REP-01** | Assessment Reports & Exports (CycloneDX 1.6 JSON, injection-safe CSV with formula prefix neutralization, executive Markdown summary) | High | QF-CBOM-01, QF-RISK-01 | VERIFIED |
| **QF-UI-02** | Frontend Discovery & Risk Intelligence (Source upload, Config import, CBOM Asset Explorer, Quantum Risk Dashboard, CycloneDX/CSV exports) | High | QF-CBOM-01, QF-RISK-01 | VERIFIED |

### Sprint 2 Backlog Breakdown & Persistence

| Task ID | Task Title | Priority | Dependencies | Status |
|---|---|---|---|---|
| **QF-018** | Implement Scan Job state machine and durable transitions | P0 | QF-014 | COMPLETED |
| **QF-019** | Implement worker lease, heartbeat, and zombie task reclamation | P1 | QF-018 | COMPLETED |
| **QF-020** | Build Scan Job submission, status, and cancellation API endpoints | P1 | QF-018 | COMPLETED |
| **QF-021** | Implement duplicate delivery idempotency guards and worker tests | P0 | QF-019, QF-020 | COMPLETED |
| **QF-029** | Implement cryptographic asset identity resolution engine | P1 | QF-028 | COMPLETED |
| **QF-030** | Implement CBOM asset correlation engine and relationship graph | P1 | QF-029 | COMPLETED |
| **QF-033** | Implement cryptographic algorithm classification catalogue | P0 | QF-030 | COMPLETED |
| **QF-034** | Implement quantum risk scoring ruleset engine (Shor / Grover) | P0 | QF-033 | COMPLETED |
| **QF-035** | Implement rule-based finding and recommendation generator | P1 | QF-034 | COMPLETED |
| **QF-036** | Implement risk assessment persistence and versioned API | P1 | QF-035 | COMPLETED |
| **QF-037** | Build risk scoring determinism and regression test suite | P0 | QF-034, QF-036 | COMPLETED |
| **QF-040** | Implement Cryptographic Asset Inventory and CBOM table views | P1 | QF-030, QF-038 | COMPLETED |
| **QF-041** | Implement Risk Findings detail and evidence inspector UI | P1 | QF-036, QF-040 | COMPLETED |
| **QF-042** | Implement CycloneDX 1.6 and JSON CBOM export service | P2 | QF-030, QF-040 | COMPLETED |

---

## 5. Sprint 3 — End-to-End Enterprise Assessment & Repeatable Demonstration

### Sprint 3 Core Deliverables

| Task ID | Task Title | Priority | Dependencies | Status |
|---|---|---|---|---|
| **QF-S3-01** | Assessment Database Models & Referential Integrity (Assessments, AssessmentAsset, AssessmentObservation, RESTRICT FKs, Composite Risk FK, Status/Progress CHECKs, Immutability Trigger) | Critical | QF-CBOM-01, QF-RISK-01 | VERIFIED (STEP 1 REMEDIATED) |
| **QF-S3-02** | Assessment Orchestration Engine (`AssessmentOrchestrator`, lifecycle transitions, collector parallel dispatch, partial failure handling, cooperative cancellation, atomic progress) | Critical | QF-S3-01 | NOT STARTED (AWAITING AUTH) |
| **QF-S3-03** | Assessment REST API Endpoints (`POST /api/v1/assessments`, `GET /api/v1/assessments`, `GET /{id}`, `POST /{id}/cancel`, `POST /{id}/retry`, `GET /{id}/coverage`) | High | QF-S3-02 | NOT STARTED |
| **QF-S3-04** | Repeatable Demonstration Environment (Synthetic multi-source target fixture, pre-seeded observations, reproducible QVI evaluation) | High | QF-S3-03 | NOT STARTED |
| **QF-S3-05** | Frontend Guided Assessment Workflow (Multi-source assessment creation wizard, live progress polling, findings summary view) | High | QF-S3-03 | NOT STARTED |
| **QF-S3-06** | Immutable Assessment Reports & Multi-Format Exporters (JSON snapshot, CycloneDX 1.6 CBOM, formula-neutralized CSV, Executive PDF/Markdown) | High | QF-S3-02, QF-S3-03 | NOT STARTED |

---

## 9. Sprint 7 — Security Hardening & Pilot Readiness

| Task ID | Task Title | Priority | Dependencies | Status |
|---|---|---|---|---|
| **QF-043** | Conduct multi-tenant isolation and PostgreSQL RLS security audit | P0 | QF-016, QF-036 | NOT STARTED |
| **QF-044** | Conduct SSRF, DNS rebinding, and network fuzzing penetration tests | P0 | QF-022, QF-023 | NOT STARTED |
| **QF-045** | Implement OIDC / OAuth2 SSO integration and JWT RBAC enforcement | P1 | QF-015, QF-043 | NOT STARTED |
| **QF-046** | Implement append-only security audit log and provenance verification | P1 | QF-028, QF-043 | NOT STARTED |
| **QF-047** | Implement operational health metrics, alerts, and pilot runbook | P1 | QF-039, QF-044 | NOT STARTED |

---

## 10. Detailed Task Specifications (Sample: Sprint 0 & 1 Foundation)

### QF-001: Confirm repository structure and baseline monorepo directories
- **Description:** Establish the approved monorepo folder layout as outlined in TRD v1.0 and Implementation Blueprint v1.0.
- **Acceptance Criteria:**
  - Folders `apps/api/`, `apps/worker/`, `apps/web/`, `packages/scanner/`, `infra/docker/` are created with placeholder `.gitkeep` or initial README files.
  - No broken or orphan directories exist.
- **Priority:** P0 | **Status:** NOT STARTED

### QF-004: Create Docker Compose for local PostgreSQL 16 and Redis 7
- **Description:** Provide a production-aligned Docker Compose file for spinning up local dependencies required by FastAPI and Celery.
- **Acceptance Criteria:**
  - `docker compose -f infra/docker/docker-compose.yml up` starts PostgreSQL 16 on port 5432 and Redis 7 on port 6379.
  - Named volumes are configured for local persistence across restarts.
  - Health checks are defined for both services.
- **Priority:** P0 | **Status:** NOT STARTED

### QF-022: Implement target validation filter and SSRF private IP blocker
- **Description:** Implement a strict pre-connection network validator in `packages/scanner/safety/` to enforce deny-by-default egress.
- **Acceptance Criteria:**
  - Blocks all IPv4 private address ranges (RFC 1918), loopback, link-local, and AWS metadata (`169.254.169.254`).
  - Blocks equivalent IPv6 private/multicast ranges.
  - Unit tests verify rejection of forbidden targets.
- **Priority:** P0 | **Status:** NOT STARTED

