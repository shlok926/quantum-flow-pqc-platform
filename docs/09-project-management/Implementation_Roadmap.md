# Quantum Flow Platform Implementation Roadmap

## 1. Document Control & Roadmap Context

- **Product:** Quantum Flow Technologies — Post-Quantum Cryptography (PQC) Discovery & Risk Assessment Platform
- **Document Type:** Engineering Delivery Roadmap (Sprint 0 through Sprint 7)
- **Primary Source:** Implementation Blueprint & Repository Setup v1.0 (Section 21)
- **Status:** Proposed Engineering Sequence (For Technical Lead, Product Owner & CISO Review)
- **Milestone Timeline Policy:** In accordance with engineering governance, this roadmap establishes a logical delivery sequence and milestone structure. **No rigid calendar delivery dates are fabricated**, as velocity depends on engineering team sizing, infrastructure provisioning, and security review cycles.

---

## 2. Strategic Delivery Workflow

The implementation roadmap operationalizes the platform's core product principle:

$$\text{Discover} \longrightarrow \text{Inventory} \longrightarrow \text{Prioritise} \longrightarrow \text{Plan} \longrightarrow \text{Migrate} \longrightarrow \text{Assure}$$

The roadmap begins by constructing the engineering foundation (Sprint 0), delivering the first end-to-end vertical slice (Sprints 1–5), providing analyst-facing UI and exports (Sprint 6), and completing security hardening for a controlled enterprise pilot (Sprint 7).

---

## 3. Sprint-by-Sprint Implementation Roadmap

### Sprint 0 — Repository and Engineering Foundation

- **Objective:** Establish a reproducible, secure, and standardized monorepo foundation ready for collaborative multi-developer engineering.
- **Scope:**
  - Standardized directory layout for control plane, execution plane, and frontend.
  - Python 3.12 virtual environment and frontend tooling definitions.
  - Docker Compose definitions for local PostgreSQL 16 and Redis 7.
  - Initial FastAPI and React skeleton applications with basic health-check endpoints.
  - Code quality tooling (Ruff, Mypy, Pytest) and GitHub Actions CI workflow.
  - Architecture Decision Record (ADR) framework.
- **Deliverables:**
  - Repository structure (`apps/api/`, `apps/worker/`, `apps/web/`, `packages/scanner/`, `infra/docker/`).
  - `infra/docker/docker-compose.yml` defining PostgreSQL and Redis services.
  - Working `/healthz` endpoints in API and Web skeletons.
  - GitHub Actions CI pipeline running lint, type checks, and tests on pull requests.
  - ADR template and initial ADR submissions.
- **Dependencies:** Approved repository access, developer workstation setup.
- **Acceptance Criteria:**
  - A new engineer can clone the repository, run setup scripts, and achieve a working local environment.
  - FastAPI health endpoint responds with HTTP 200 locally.
  - Frontend development server renders the skeleton UI locally.
  - PostgreSQL and Redis containers launch cleanly and pass health checks.
  - CI pipeline successfully triggers and executes on pull requests.

---

### Sprint 1 — Persistence and Core Domain

- **Objective:** Establish durable database persistence and the core business domain models for projects, targets, authorisations, and scan records.
- **Scope:**
  - SQLAlchemy 2.0 declarative models and Alembic migration framework.
  - Core domain models: `Tenants`, `Users`, `Projects`, `Targets`, `Authorisations`, `ScanJobs`.
  - Tenant context propagation and tenant-scoped repository patterns.
  - Target boundary validation logic (rejecting invalid hostnames and ports).
  - Authorisation record validation (written scope, validity window, legal approver).
  - FastAPI CRUD endpoints for projects, targets, and authorisations.
- **Deliverables:**
  - Initial Alembic database migration scripts.
  - Domain models and repositories for core entities.
  - REST API endpoints for `/api/v1/projects`, `/api/v1/targets`, and `/api/v1/authorisations`.
  - Comprehensive unit and database integration test suites.
- **Dependencies:** Sprint 0 engineering foundation and PostgreSQL service.
- **Acceptance Criteria:**
  - All migrations execute cleanly on a fresh database and support complete rollback (`downgrade`).
  - Project, target, and authorisation records persist reliably with full audit fields (`created_at`, `tenant_id`).
  - Target creation rejects out-of-scope, invalid, or malformed hostnames/IPs.
  - Authorisation records are auditable and require documented approval metadata before activation.

---

### Sprint 2 — Scan Orchestration Foundation

- **Objective:** Construct a reliable, resilient, asynchronous job orchestration engine to dispatch and manage scan tasks without data loss.
- **Scope:**
  - Celery worker integration with Redis broker and PostgreSQL result backend.
  - Scan job state machine (`SUBMITTED` → `QUEUED` → `RUNNING` → `COMPLETED` / `FAILED` / `CANCELLED`).
  - Worker claim, lease renewal, heartbeat tracking, and zombie-task recovery.
  - Scan initiation, progress reporting, and cancellation endpoints.
  - Idempotency guards against duplicate job delivery and concurrent task collisions.
- **Deliverables:**
  - Celery application module (`apps/worker/celery_app.py`) and task definitions.
  - Scan state transition logic with strict validation guards.
  - API endpoints for `/api/v1/scan-jobs` (create, list, get status, cancel).
  - Integration tests simulating worker disconnections and duplicate messages.
- **Dependencies:** Sprint 1 domain models (specifically `ScanJobs` and `Authorisations`) and Redis.
- **Acceptance Criteria:**
  - Submitting an authorised scan request creates exactly one durable job in Redis and PostgreSQL.
  - An isolated worker claims, processes, and marks a test job as completed.
  - Duplicate message delivery produces zero duplicate database records or phantom jobs.
  - Scan cancellations immediately terminate worker execution and record the cancellation reason.

---

### Sprint 3 — TLS Collector Proof-of-Concept (POC)

- **Objective:** Safely collect a bounded, highly reliable set of TLS configurations and X.509 certificate metadata from explicitly authorised network endpoints.
- **Scope:**
  - Pre-connection network safety engine (SSRF defense, blocking private IPv4/IPv6, loopback, and link-local addresses).
  - DNS rebinding mitigation (two-stage DNS check with worker-pinned IP connection and SNI).
  - Bounded TLS socket handshake (configurable connection and read timeouts).
  - X.509 certificate chain extraction and ASN.1 metadata parsing (leaf and intermediates).
  - Protocol version, negotiated cipher suite, and key-exchange parameter recording.
  - Provenance envelope attachment (collector version, timestamp, resolved IP).
  - Synthetic TLS test server fixtures (RSA 2048/4096, ECC P-256/P-384, expired certs).
- **Deliverables:**
  - Standalone scanner package (`packages/scanner/`).
  - Target safety and network validation filters.
  - Low-level TLS handshake and certificate parser modules.
  - Synthetic TLS test suite and security abuse test cases.
- **Dependencies:** Sprint 2 scan orchestration and Celery worker infrastructure.
- **Acceptance Criteria:**
  - Collector successfully extracts structured TLS and certificate observations from live and synthetic endpoints.
  - Private, loopback, link-local, and cloud metadata destinations are blocked before socket creation.
  - Timeouts and connection bounds are strictly enforced without worker hang.
  - Unsupported cipher suites or partial handshakes are recorded with explicit error metadata.
  - **Zero private keys or sensitive credentials are ever collected or stored.**

---

### Sprint 4 — Observation Persistence & CBOM Correlation

- **Objective:** Transform raw, immutable collector observation envelopes into a correlated, normalized Cryptographic Bill of Materials (CBOM).
- **Scope:**
  - Observation validation and immutable raw evidence persistence (JSONB/PostgreSQL).
  - Cryptographic asset identity resolution (distinguishing endpoints, certificates, algorithms, and public keys).
  - Correlation engine matching observations to existing cryptographic assets or creating new ones.
  - Relationship mapping (e.g., `Endpoint --USES--> Certificate --SIGNED_WITH--> Algorithm`).
  - Certificate rotation detection and historical versioning.
  - Coverage summaries and uninspected area warnings.
- **Deliverables:**
  - Correlation package (`packages/cbom/`).
  - Relational schema and tables for `CryptoAssets`, `CryptoAssetRelationships`, and `RawObservations`.
  - Idempotent asset correlation pipeline.
  - Automated tests validating duplicate-observation handling and certificate rotation.
- **Dependencies:** Sprint 3 TLS collector observations and Sprint 1 database infrastructure.
- **Acceptance Criteria:**
  - Raw observations are persisted immutably with SHA-256 evidence digests.
  - Repeated scans of the same endpoint correlate to existing assets without creating duplicates.
  - Renewed or rotated certificates spawn a new certificate asset while maintaining historical link to the endpoint.
  - Every asset and relationship in the CBOM is traceable to source observation evidence.

---

### Sprint 5 — Findings and Quantum Risk Assessment

- **Objective:** Evaluate cryptographic assets against post-quantum risk criteria to generate deterministic, explainable risk findings and provisional migration priorities.
- **Scope:**
  - Cryptographic algorithm classification catalogue (NIST PQC standards, CNSA 2.0, legacy public-key algorithms).
  - Quantum risk scoring engine (evaluating Shor's algorithm vulnerability on RSA/ECC and Grover's impact on symmetric key sizes).
  - Rule-based finding generation linking specific asset attributes to risk descriptions.
  - Confidence scoring and explicit handling of missing or incomplete data.
  - Deterministic risk score calculation with ruleset versioning.
  - Actionable remediation and PQC migration recommendation generation.
- **Deliverables:**
  - Quantum risk engine package (`packages/risk-engine/`).
  - Versioned risk ruleset catalog (`RISK_RULESET_VERSION`).
  - Risk findings schema and persistence (`RiskAssessments`, `Findings`, `Recommendations`).
  - API endpoints for `/api/v1/risk-assessments` and `/api/v1/findings`.
  - Comprehensive determinism and regression test suite.
- **Dependencies:** Sprint 4 correlated CBOM assets.
- **Acceptance Criteria:**
  - Identical asset inputs and ruleset versions yield 100% deterministic numeric scores and findings.
  - Every finding links directly to the specific cryptographic asset and supporting observation evidence.
  - Missing or unobserved parameters do not silently downgrade risk scores; missing data flags are prominently raised.
  - Provisional status is clearly marked until formal CISO / Product Owner review and approval.

---

### Sprint 6 — Frontend Workflow and CBOM Export

- **Objective:** Deliver an intuitive, accessible web dashboard enabling security analysts to manage projects, launch scans, inspect findings, and export standard CBOM artifacts.
- **Scope:**
  - Project and target management interface.
  - Written authorisation review and scan submission workflow.
  - Real-time scan progress tracking and status indicators.
  - Cryptographic asset inventory table with filtering by algorithm, key size, and quantum status.
  - Explainable finding detail view with evidence provenance inspection.
  - Standardized CBOM export functionality (CycloneDX 1.6 / JSON / CSV).
  - Explicit visual banners highlighting scan limitations and unobserved architectural scopes.
- **Deliverables:**
  - React application views (`apps/web/src/pages/Projects`, `Targets`, `Scans`, `Inventory`, `Risk`).
  - CBOM export generation service.
  - End-to-end user journey tests (Playwright or Cypress).
- **Dependencies:** Sprint 1–5 backend APIs and data models.
- **Acceptance Criteria:**
  - An analyst can complete the full discovery workflow through the web interface without manual API calls.
  - Partial scan failures and unsupported protocols are displayed clearly.
  - CBOM export outputs fully compliant CycloneDX JSON containing cryptographic component metadata.
  - UI never claims or implies that unscanned systems or private networks are quantum-safe.

---

### Sprint 7 — Security Hardening & Pilot Readiness

- **Objective:** Harden the platform, conduct rigorous verification, and establish operational controls to prepare for a controlled, customer-authorised pilot deployment.
- **Scope:**
  - Dedicated multi-tenant isolation and penetration testing.
  - Advanced SSRF and DNS rebinding fuzzing.
  - OIDC / OAuth2 SSO integration and JWT token validation hardening.
  - Role-Based Access Control (RBAC) enforcement across all endpoints.
  - Security audit logging verification (tamper-evident audit tables).
  - Container vulnerability scanning (Trivy) and dependency audit (`pip-audit`, `pnpm audit`).
  - Operational health metrics (Prometheus/Grafana) and error alerts (Sentry).
  - Pilot deployment runbook, backup/recovery procedures, and documented known limitations.
- **Deliverables:**
  - Security test suite and third-party penetration testing report remediation.
  - Production-ready Docker Compose / Helm deployment manifests with non-root security contexts.
  - Pilot Operations Runbook (`docs/operations/Pilot_Runbook.md`).
  - Formal CISO and Product Leadership sign-off artifact.
- **Dependencies:** Sprint 6 completed system.
- **Acceptance Criteria:**
  - All critical and high-severity security findings are remediated or formally accepted with documented CISO waiver.
  - Tenant isolation is verified under concurrent multi-tenant load tests.
  - Backup and point-in-time recovery procedures are verified in staging.
  - Pilot scope, customer authorisation agreements, and known platform limitations are formally documented.

