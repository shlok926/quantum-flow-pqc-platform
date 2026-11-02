# Quantum Flow Technologies
# Implementation Blueprint & Repository Setup
## Version 1.0 — Draft for Engineering Review

**Document status:** Proposed implementation blueprint  
**Product:** PQC Discovery & Risk Assessment Platform  
**Version:** 1.0  
**Audience:** Engineering, Product, Security, Architecture and QA  
**Purpose:** Translate the approved product and technical design direction into a practical repository, development environment, delivery sequence and implementation plan.

---

## 1. Executive Summary

This document defines a proposed implementation approach for the Quantum Flow Technologies PQC Discovery & Risk Assessment Platform. It converts the existing product requirements and design work into an actionable engineering plan covering:

- Repository layout and module boundaries
- Backend, frontend, worker and database responsibilities
- Local development environment and configuration
- Docker Compose services
- Database migration and seed-data workflow
- API and background-job implementation
- TLS discovery collector integration
- Observation, cryptographic asset and CBOM processing
- Risk assessment engine integration
- Testing, code quality and CI/CD
- Security controls and operational practices
- Sprint-wise implementation and acceptance criteria

The recommended first implementation is a **modular monolith with separately running background workers**. This keeps the initial system understandable and deployable while preserving clear boundaries that can later be extracted into services if scale or operational needs justify it.

The first usable milestone should be a controlled, authorised discovery workflow: a user creates a project and an approved target, submits a scan, a worker performs a bounded TLS inspection, structured observations are persisted, observations are correlated to cryptographic assets, and the platform displays evidence-backed findings and coverage limitations.

The platform must not imply that a public TLS scan discovers every cryptographic asset in an organisation. Internal services, source code, application dependencies, databases, KMS/HSM usage and private network assets require additional authorised collectors or integrations.

> **Implementation status:** This is a design and delivery blueprint. It does not claim that the repository, services, APIs, scanner or scoring engine have already been implemented.

---

## 2. Relationship to Existing Design Documents

This blueprint is intended to be used alongside the following design artefacts:

1. Product Requirements Document (PRD)
2. Technical Requirements Document (TRD)
3. Database Design Document (DDD)
4. API Specification
5. Quantum Risk Assessment Methodology & Core Engine Design
6. CBOM & Cryptographic Asset Correlation Engine Design
7. Company PQC Platform Vision and Roadmap

Where a detailed contract exists in one of those documents, implementation should follow that contract rather than redefining it here. If a conflict is discovered, record it as an architecture decision and obtain the appropriate product/security approval before changing implementation behaviour.

### 2.1 Design principles to preserve

- Discover → Inventory → Prioritise → Plan → Migrate → Assure is the long-term product workflow.
- Build evidence-backed discovery and inventory before migration automation.
- Keep observations, assets, relationships, findings and CBOM snapshots as distinct concepts.
- Preserve provenance: source, timestamp, target, method, confidence, evidence, collector version and execution status.
- Separate observed facts from inferred, imported and unknown information.
- Use explainable, versioned risk rules. Do not present a provisional score as an industry standard.
- Never collect customer private keys or secrets as part of public TLS discovery.
- Require explicit authorisation and enforce safe scan boundaries.
- Do not perform unattended production cryptographic changes.
- Treat coverage limitations as first-class output, not hidden footnotes.

---

## 3. Proposed Architecture

### 3.1 Initial architecture

Use a modular monolith for the API and domain logic, with a separately deployed worker process for asynchronous discovery jobs.

```mermaid
flowchart LR
    U[User / Browser] --> FE[React Frontend]
    FE --> API[FastAPI Application]
    API --> DB[(PostgreSQL)]
    API --> R[(Redis)]
    R --> W[Discovery Worker]
    W --> COL[TLS Collector]
    COL --> EXT[Authorised External TLS Endpoint]
    W --> DB
    API --> DB
    API --> OUT[Reports / Export]
```

### 3.2 Runtime components

| Component | Responsibility | Initial deployment |
|---|---|---|
| Web frontend | User interface, projects, targets, scans, findings, assets and reports | Separate container |
| API | Authentication integration, validation, business workflows and read APIs | FastAPI container |
| Worker | Claims and executes asynchronous scan jobs | Separate worker container |
| PostgreSQL | Durable application and evidence storage | Database container in local development |
| Redis | Queue/broker and short-lived coordination | Redis container in local development |
| TLS collector | Bounded TLS handshake and certificate/configuration observation | Python module invoked by worker |
| Risk engine | Deterministic rule evaluation and explainability | Backend domain module |
| Correlation engine | Observation-to-asset matching and relationship creation | Backend domain module |
| Report/export module | CBOM and assessment exports | Backend module |

Redis must not become the source of truth for scan state. PostgreSQL is authoritative for jobs, executions, observations, findings, assets and audit records. Queue messages should contain identifiers, not sensitive payloads.

### 3.3 Why a modular monolith first

- The POC needs a small operational footprint.
- Domain boundaries can be enforced through packages and interfaces.
- Database transactions are easier to manage.
- Developers can run and debug the full workflow locally.
- A worker process can scale independently without prematurely introducing microservices.
- Future extraction remains possible if a module develops independent scaling, security or release requirements.

Do not split into microservices merely to make the architecture appear enterprise-grade. Extract only when a measured need exists.

---

## 4. Technology Baseline

The following is a proposed baseline consistent with the technical direction in the design documents. Exact versions should be pinned and reviewed at repository creation time.

| Layer | Proposed technology | Notes |
|---|---|---|
| Frontend | React + TypeScript + Vite | Component-based UI |
| Styling | Tailwind CSS | Shared design tokens and components |
| Backend | Python + FastAPI | Versioned REST API |
| Validation | Pydantic | Request/response schemas |
| ORM | SQLAlchemy | Explicit transaction boundaries |
| Migrations | Alembic | Version-controlled schema changes |
| Database | PostgreSQL | Durable relational store |
| Queue | Celery | Asynchronous job execution |
| Broker | Redis | Queue transport and coordination |
| TLS inspection | Python `ssl`, OpenSSL-backed tooling and `cryptography` | Capture only observable public endpoint details |
| Testing | Pytest, HTTPX; frontend test runner | Unit, integration and end-to-end layers |
| API contract | OpenAPI 3.1 | Generated from FastAPI and reviewed |
| Containers | Docker + Docker Compose | Reproducible local setup |
| CI | GitHub Actions | Lint, type checks, tests, build and security checks |

### 4.1 Version policy

- Pin runtime and dependency versions.
- Commit lockfiles.
- Use a supported Python release selected by the engineering team.
- Use a supported Node.js LTS release.
- Pin container image tags; avoid `latest` for reproducible environments.
- Review dependency upgrades through pull requests.
- Record collector and risk-rule versions in persisted execution/assessment records.

---

## 5. Repository Strategy

### 5.1 Recommended repository model

For the initial product, use a **single repository (monorepo)** containing frontend, backend, worker, infrastructure and documentation.

Suggested repository name: `pqc-discovery-platform` (working name; confirm with the team before creating it).

Benefits:
- One pull request can update API contracts and frontend consumers together.
- Shared documentation and local development instructions stay close to code.
- CI can enforce compatibility across modules.
- Initial contributor onboarding is simpler.

### 5.2 Proposed directory structure

```text
pqc-discovery-platform/
├── README.md
├── LICENSE
├── .gitignore
├── .editorconfig
├── .env.example
├── .pre-commit-config.yaml
├── Makefile
├── docker-compose.yml
├── pyproject.toml
├── package.json
│
├── apps/
│   └── web/
│       ├── package.json
│       ├── vite.config.ts
│       ├── tsconfig.json
│       ├── index.html
│       └── src/
│           ├── app/
│           ├── components/
│           ├── features/
│           │   ├── projects/
│           │   ├── targets/
│           │   ├── scans/
│           │   ├── findings/
│           │   ├── assets/
│           │   ├── cbom/
│           │   └── risk/
│           ├── hooks/
│           ├── lib/
│           ├── routes/
│           ├── services/
│           ├── styles/
│           └── types/
│
├── services/
│   └── api/
│       ├── Dockerfile
│       └── app/
│           ├── main.py
│           ├── core/
│           │   ├── config.py
│           │   ├── logging.py
│           │   ├── security.py
│           │   └── errors.py
│           ├── api/
│           │   └── v1/
│           │       ├── router.py
│           │       └── endpoints/
│           ├── domain/
│           │   ├── projects/
│           │   ├── targets/
│           │   ├── authorisations/
│           │   ├── scans/
│           │   ├── observations/
│           │   ├── assets/
│           │   ├── cbom/
│           │   ├── risk/
│           │   ├── recommendations/
│           │   ├── reports/
│           │   └── audit/
│           ├── schemas/
│           ├── repositories/
│           ├── db/
│           │   ├── base.py
│           │   ├── session.py
│           │   └── models/
│           └── integrations/
│
├── services/
│   └── worker/
│       ├── Dockerfile
│       └── app/
│           ├── celery_app.py
│           ├── tasks/
│           ├── orchestration/
│           └── runtime/
│
├── packages/
│   └── scanner/
│       ├── README.md
│       ├── tls/
│       │   ├── client.py
│       │   ├── handshake.py
│       │   ├── certificate_parser.py
│       │   └── models.py
│       ├── safety/
│       │   ├── target_validation.py
│       │   ├── dns_policy.py
│       │   └── network_policy.py
│       └── tests/
│
├── migrations/
│   ├── env.py
│   └── versions/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── security/
│   ├── contract/
│   └── e2e/
│
├── infra/
│   ├── docker/
│   ├── scripts/
│   └── deployment/
│
├── docs/
│   ├── architecture/
│   ├── api/
│   ├── security/
│   ├── operations/
│   ├── decisions/
│   └── runbooks/
│
└── .github/
    ├── workflows/
    │   ├── ci.yml
    │   ├── security.yml
    │   └── release.yml
    ├── ISSUE_TEMPLATE/
    └── pull_request_template.md
```

This is a logical starting structure, not a requirement to create every empty directory on day one. Add packages when the first implementation needs them.

### 5.3 Module ownership and boundaries

| Module | Owns | Must not own |
|---|---|---|
| Projects | Project metadata and tenant ownership | Scanner execution |
| Targets | Target identity, ports and approved scope | Network probing implementation |
| Authorisations | Written approval, scope, validity and evidence reference | Authentication secrets |
| Scans | Scan lifecycle, policy, status and orchestration | Low-level TLS parsing |
| Worker orchestration | Claim, lease, heartbeat, retry and task execution | User-facing business rules |
| Scanner | Network interaction and raw technical observations | Risk score or business priority |
| Observations | Immutable evidence-backed observations | Canonical asset identity alone |
| Correlation | Asset matching and relationship creation | Rewriting raw evidence |
| CBOM | Versioned inventory snapshots and exports | Unverified claims of complete coverage |
| Risk engine | Versioned deterministic assessment and rationale | Hidden AI-only scoring |
| Recommendations | Action guidance mapped to findings and standards | Unapproved production changes |
| Reports | Presentation and export | Changing source evidence |

### 5.4 Dependency direction

Keep dependencies pointing inward toward domain contracts:

- API endpoints call application/domain services.
- Domain services depend on repository interfaces and typed models.
- Repositories implement persistence.
- Worker tasks call application services and scanner interfaces.
- Scanner returns typed observations; it does not write directly to arbitrary database tables.
- Frontend consumes versioned API contracts and does not duplicate risk calculations.

Avoid circular imports and direct cross-module database manipulation.

---

## 6. Local Development Environment

### 6.1 Prerequisites

Install:
- Git
- Docker Desktop or Docker Engine with Compose plugin
- Python runtime selected by the project
- Node.js LTS and npm
- A code editor such as VS Code
- Optional: `make` or an equivalent task runner

### 6.2 Environment variables

Commit `.env.example`, never a populated `.env`.

Example:

```dotenv
APP_ENV=local
APP_NAME=quantum-flow-pqc-platform
API_HOST=0.0.0.0
API_PORT=8000

DATABASE_URL=postgresql+psycopg://pqc_app:local_only_password@postgres:5432/pqc_platform
REDIS_URL=redis://redis:6379/0

JWT_ISSUER=
JWT_AUDIENCE=
OIDC_DISCOVERY_URL=

SCAN_DEFAULT_TIMEOUT_SECONDS=8
SCAN_MAX_TIMEOUT_SECONDS=20
SCAN_MAX_REDIRECTS=0
SCAN_ALLOW_PRIVATE_NETWORKS=false
SCAN_ALLOWED_PORTS=443
SCAN_MAX_CONCURRENCY=5

LOG_LEVEL=INFO
COLLECTOR_VERSION=0.1.0
RISK_RULESET_VERSION=0.1.0
```

The example values are for local development only. Production credentials must be provided through an approved secret-management mechanism. Do not commit tokens, passwords, private keys, customer data or production connection strings.

### 6.3 First-time setup sequence

```bash
git clone <approved-repository-url>
cd pqc-discovery-platform

cp .env.example .env

docker compose up -d postgres redis

# Backend environment and dependencies
python -m venv .venv
# Activate the virtual environment using the command for your OS.
pip install -e ".[dev]"

# Apply database migrations
alembic upgrade head

# Start API in one terminal
uvicorn services.api.app.main:app --reload --host 0.0.0.0 --port 8000

# Start worker in another terminal
celery -A services.worker.app.celery_app worker --loglevel=INFO

# Frontend in another terminal
cd apps/web
npm ci
npm run dev
```

The exact import path and package installation command must be aligned with the final packaging configuration when the repository is scaffolded.

### 6.4 Suggested Makefile commands

```makefile
.PHONY: up down logs migrate test lint format typecheck

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	alembic upgrade head

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy services packages

```

Add frontend-specific commands such as `npm run lint`, `npm run typecheck` and `npm test` in the web package.

---

## 7. Docker Compose Baseline

A local development Compose file should run PostgreSQL, Redis, API, worker and frontend. The following is a starting template; image versions, health checks, Dockerfiles and credentials must be finalised in the repository.

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: pqc_platform
      POSTGRES_USER: pqc_app
      POSTGRES_PASSWORD: local_only_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pqc_app -d pqc_platform"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:7
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

  api:
    build:
      context: .
      dockerfile: services/api/Dockerfile
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    ports:
      - "8000:8000"

  worker:
    build:
      context: .
      dockerfile: services/worker/Dockerfile
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  web:
    build:
      context: apps/web
    ports:
      - "5173:5173"
    depends_on:
      - api

volumes:
  postgres_data:
```

### 7.1 Compose security notes

- The sample passwords are local-only placeholders.
- Do not expose PostgreSQL or Redis publicly in shared or production environments.
- Production services should run as non-root users.
- Use read-only filesystems where practical.
- Drop unnecessary Linux capabilities.
- Apply resource limits and health checks.
- Use separate production secrets and managed data services where appropriate.
- Never mount the Docker socket into the scanner worker.
- Do not give the scanner worker broad host-network access.

---

## 8. Database and Migration Workflow

### 8.1 Migration ownership

Alembic migrations are the only approved mechanism for evolving the relational schema. Do not rely on automatic table creation at API startup.

### 8.2 Migration rules

1. Every schema change is represented by a migration.
2. Migrations are reviewed with the model and API changes.
3. Prefer additive changes before destructive changes.
4. Backfill data in bounded, restartable batches.
5. Use explicit constraints and indexes.
6. Test both fresh database setup and upgrade from the previous release.
7. Destructive migrations require a documented backup and rollback/forward-fix plan.
8. Production migrations run as a controlled release step, not independently in every API replica.

### 8.3 Initial migration groups

Suggested order:

1. Tenant and identity references
2. Projects and project membership
3. Targets and authorisation records
4. Scan policies and scan jobs
5. Scan executions and collector runs
6. Observations and evidence
7. Cryptographic assets and relationships
8. Findings and risk assessments
9. Risk rules and recommendation catalogue
10. CBOM snapshots and export records
11. Audit events and integration metadata

The exact table and column definitions remain governed by the Database Design Document.

### 8.4 Data integrity

- Use UUIDs or the agreed identifier standard consistently.
- Enforce tenant ownership at the application and database layers.
- Use foreign keys for durable relationships.
- Use unique constraints for idempotency keys and canonical asset identity within the correct tenant/project scope.
- Preserve immutable observation evidence.
- Store timestamps in UTC.
- Store collector, schema and ruleset versions with the relevant records.
- Define retention and deletion behaviour before onboarding real customer data.

### 8.5 PostgreSQL Row-Level Security

If PostgreSQL RLS is adopted, implement it as a defence-in-depth control:
- Set tenant context transaction-locally.
- Ensure pooled connections cannot leak tenant context between requests.
- Test queries with multiple tenants.
- Use a restricted application role.
- Ensure administrative/bypass roles are tightly controlled and audited.
- Do not assume RLS removes the need for application-level authorisation checks.

---

## 9. API Implementation Plan

### 9.1 API conventions

- Prefix public endpoints with `/api/v1`.
- Use Pydantic request and response models.
- Keep persistence models separate from public API schemas.
- Return consistent error envelopes.
- Validate tenant/project access on every resource operation.
- Use pagination for potentially large collections.
- Use idempotency for scan creation and other retry-sensitive operations.
- Include correlation/request IDs in logs and responses where appropriate.
- Document status transitions and error codes.

### 9.2 Implementation order

| Order | API area | Initial responsibility |
|---:|---|---|
| 1 | Health/readiness | Liveness, readiness and dependency health |
| 2 | Projects | Create/list/read projects |
| 3 | Targets | Register and validate target metadata |
| 4 | Authorisations | Record scope, owner, approval evidence and validity |
| 5 | Scan validation | Explain whether a target/policy is eligible |
| 6 | Scan submission | Create durable scan job and enqueue identifier |
| 7 | Scan status/progress | Return state, timestamps and coverage |
| 8 | Findings | Return evidence-backed findings |
| 9 | Assets/relationships | Browse cryptographic inventory |
| 10 | Risk assessment | Run/read versioned assessments |
| 11 | CBOM | Create/list/export immutable snapshots |
| 12 | Reports/audit | Evidence trail and export records |

Use the API Specification as the source of truth for endpoint paths, request fields and response semantics.

### 9.3 Scan lifecycle

A suggested lifecycle is:

```mermaid
stateDiagram-v2
    [*] --> queued
    queued --> validating
    validating --> running: authorised and eligible
    validating --> rejected: scope or policy failure
    running --> completed
    running --> partial
    running --> failed
    running --> cancelled
    queued --> cancelled
    completed --> [*]
    partial --> [*]
    failed --> [*]
    rejected --> [*]
    cancelled --> [*]
```

The final state machine must match the API Specification and database constraints. Avoid inventing additional states in individual modules.

---

## 10. Background Worker and Job Orchestration

### 10.1 Worker responsibilities

The worker should:
1. Receive a scan/job identifier.
2. Load the authoritative job and scope from PostgreSQL.
3. Revalidate authorisation and target policy at execution time.
4. Acquire a lease or execution lock.
5. Record execution start and collector version.
6. Invoke the relevant collector with strict time and network limits.
7. Persist observations and evidence through application services.
8. Trigger correlation and finding/risk processing in the defined order.
9. Record partial/complete/failed outcome and coverage.
10. Release lease and emit structured completion events.

### 10.2 Reliability requirements

- Jobs must be durable in PostgreSQL.
- Queue delivery may be at-least-once; tasks must be idempotent.
- Use bounded retries with exponential backoff and jitter.
- Do not retry permanent policy failures.
- Use execution leases/heartbeats to recover abandoned jobs.
- Make cancellation cooperative and bounded.
- Prevent duplicate concurrent execution for the same scan unless explicitly supported.
- Persist task failure details without exposing secrets.
- Keep queue messages small and non-sensitive.

### 10.3 Suggested task boundaries

```text
submit_scan(scan_id)
    └── execute_scan(scan_id)
          ├── validate_authorisation(scan_id)
          ├── collect_tls_observations(scan_id)
          ├── persist_observations(scan_id)
          ├── correlate_assets(scan_id)
          ├── generate_findings(scan_id)
          ├── assess_risk(scan_id)
          └── finalise_scan(scan_id)
```

These may be one orchestration task initially. Split them into independently queued tasks only when retry, duration or scaling requirements justify it.

---

## 11. TLS Discovery Collector Implementation

### 11.1 First collector scope

The first collector should inspect only explicitly authorised public TLS endpoints and record what can actually be observed during the connection.

Potential observations include:
- Resolved destination addresses and resolution timestamp
- Connection outcome and negotiated protocol version
- Negotiated cipher suite
- Negotiated key-exchange/group information, where reliably available
- Server certificate chain presented
- Leaf certificate validity period
- Certificate signature algorithm
- Certificate public-key algorithm and public-key size/parameters
- Subject Alternative Names
- Certificate fingerprints
- Handshake errors and unsupported/unknown fields

The collector must not conflate:
- Certificate signature algorithm
- Certificate public-key algorithm
- Negotiated cipher suite
- Negotiated key exchange/group
- Application-layer cryptographic use

### 11.2 Observation contract

Each observation should carry a consistent envelope:

```json
{
  "observation_type": "tls.negotiated_cipher_suite",
  "target": {
    "hostname": "approved.example",
    "port": 443,
    "protocol": "https"
  },
  "value": {
    "name": "example-suite"
  },
  "source": "tls_handshake",
  "classification": "observed",
  "confidence": "high",
  "observed_at": "2026-01-01T00:00:00Z",
  "collector_name": "tls_collector",
  "collector_version": "0.1.0",
  "evidence": {
    "method": "negotiated_tls_session"
  }
}
```

This is an illustrative shape, not a final schema. The API Specification and database design determine the actual field names and allowed values.

### 11.3 Safety controls

The scanner is a network-capable component and must be treated as security-sensitive.

- Require explicit authorisation before scanning.
- Validate hostname and port against approved project scope.
- Resolve DNS and validate every resolved address.
- Block loopback, private, link-local, multicast, unspecified and cloud metadata ranges by default.
- Re-check destination addresses at connection time to mitigate DNS rebinding.
- Do not follow redirects unless a separately reviewed policy allows them.
- Enforce connection, handshake and total execution timeouts.
- Enforce per-target and global concurrency limits.
- Restrict ports to the approved allowlist.
- Limit certificate-chain size and parser resource use.
- Never accept arbitrary user-supplied URLs as unrestricted fetch instructions.
- Do not collect private keys, credentials or application payloads.
- Record policy denials and failed attempts for audit.

A public TLS collector must not be presented as a full network vulnerability scanner or complete enterprise cryptographic discovery solution.

---

## 12. Observation, Correlation and CBOM Processing

### 12.1 Processing sequence

```mermaid
flowchart TD
    A[Collector output] --> B[Validate observation schema]
    B --> C[Persist immutable observation]
    C --> D[Normalise algorithm and protocol values]
    D --> E[Resolve canonical asset identity]
    E --> F[Match or create asset]
    F --> G[Create/update relationship]
    G --> H[Update coverage and inventory state]
    H --> I[Build CBOM snapshot when requested]
```

### 12.2 Required distinctions

- **Observation:** A time-bound piece of evidence from a collector or integration.
- **Asset:** A canonical inventory entity with lifecycle and identity.
- **Relationship:** A typed link between assets.
- **Finding:** A rule-derived issue or condition supported by observations.
- **Assessment:** A versioned evaluation of risk.
- **CBOM snapshot:** A point-in-time, exportable representation of inventory and relationships.

Do not overwrite an observation when an asset changes. New observations should preserve history and allow the platform to identify certificate rotation, configuration changes and newly discovered endpoints.

### 12.3 Correlation behaviour

- Endpoint identity should use hostname, port and protocol, not IP address alone.
- Certificate identity should use a fingerprint of the exact DER certificate.
- Public-key identity should be based on the SubjectPublicKeyInfo fingerprint and remain distinct from certificate identity.
- Certificate rotation should create a new certificate asset while preserving prior history.
- Source-code or dependency evidence must not be treated as proof of runtime use.
- Ambiguous matches should be marked for review rather than silently merged.
- Every relationship should retain provenance and confidence.

### 12.4 CBOM snapshot

Each snapshot should include:
- Snapshot identifier and creation time
- Tenant/project scope
- Included assets and relationships
- Observation/evidence references
- Collector and normalisation versions
- Coverage summary
- Unknown, unsupported and not-scanned areas
- Schema version
- Export format/version
- Integrity manifest or hash, if adopted

A CBOM export must not imply complete coverage when only public TLS endpoints have been inspected.

---

## 13. Risk Engine Integration

### 13.1 Execution order

The risk engine should run after observations are validated and correlated to assets. It should consume normalised facts and versioned rules rather than raw network responses.

### 13.2 Core requirements

- Deterministic evaluation for the same input and ruleset version.
- Explicit rule identifiers and versions.
- Evidence references for each triggered rule.
- Explainable contribution to any aggregate score.
- Clear handling of unknown or missing inputs.
- Separate confidence from risk severity.
- No silent conversion of missing data to zero risk.
- Ability to withhold a score where critical evidence is insufficient.
- Store the ruleset version and assessment timestamp.
- Preserve prior assessments for comparison.

### 13.3 Provisional score governance

The proposed 0–1000 framework and category thresholds remain provisional until calibrated and approved by the CISO/product owner. It is not an industry-standard score. The implementation must make the methodology version visible and must not market it as an externally certified rating.

### 13.4 AI usage boundary

AI may assist with summarising evidence or drafting recommendations in a later phase, but the authoritative risk score must remain reproducible and rule-based unless a separately governed model is approved. AI-generated text must not create unsupported claims or alter evidence.

---

## 14. Frontend Implementation Plan

### 14.1 Initial navigation

Suggested first navigation:

- Dashboard
- Projects
- Targets
- Scans
- Findings
- Cryptographic Assets
- CBOM
- Risk Assessments
- Reports
- Settings / Audit (permission-controlled)

### 14.2 First user journeys

1. Create or open a project.
2. Register a target.
3. Record or verify authorisation and scan scope.
4. Validate target eligibility.
5. Submit a scan.
6. View scan progress and status.
7. Review discovered endpoint/certificate observations.
8. Review findings with evidence and confidence.
9. View cryptographic assets and relationships.
10. Generate a CBOM snapshot and inspect coverage limitations.

### 14.3 UI principles

- Show observed, inferred, imported and unknown distinctly.
- Display timestamps and collector version where useful.
- Make evidence accessible from findings.
- Show scan coverage and skipped/unsupported/not-scanned states.
- Explain why a risk score is unavailable.
- Do not use a green status to imply that an unscanned area is safe.
- Avoid presenting provisional score categories as certified ratings.
- Use accessible colour contrast, keyboard navigation and clear loading/error states.

### 14.4 Frontend quality

- TypeScript strict mode.
- Shared API client and generated/maintained API types.
- Centralised error handling.
- Route-level access control backed by API authorisation.
- Unit tests for critical UI logic.
- Component tests for scan status, findings and evidence views.
- End-to-end tests for the core authorised scan journey.

---

## 15. Authentication, Authorisation and Tenant Isolation

### 15.1 Identity integration

Use the organisation-approved identity provider and OIDC/OAuth2 approach. Do not implement custom password storage unless explicitly approved and security-reviewed.

### 15.2 Authorisation model

At minimum, define roles such as:
- Organisation administrator
- Project owner
- Security analyst
- Read-only auditor

Final role names and permissions require product/security approval.

### 15.3 Enforcement

- Authenticate every protected API request.
- Authorise every project-scoped resource access.
- Enforce tenant scope in repository queries and database controls.
- Validate worker identity for internal endpoints.
- Separate internal worker APIs from public user APIs.
- Protect state-changing actions with appropriate CSRF/token strategy based on the auth architecture.
- Audit privileged actions, authorisation changes, scan submission/cancellation and risk exceptions.

Do not rely on frontend route hiding as a security control.

---

## 16. Logging, Observability and Audit

### 16.1 Structured logging fields

Where applicable, log:
- Timestamp
- Log level
- Service and environment
- Request/correlation ID
- Tenant/project identifiers (non-sensitive)
- Scan/job/execution identifiers
- Collector and ruleset versions
- Event name and duration
- Error category

Never log access tokens, passwords, private keys, full secrets or unnecessary customer data.

### 16.2 Initial metrics

- API request count, latency and error rate
- Queue depth and oldest queued job age
- Scan duration and outcome counts
- Collector timeout/failure rates
- Observation counts by type
- Correlation match/ambiguous/unmatched counts
- Risk assessment duration and failure rate
- Database connection pool saturation
- Worker heartbeat and lease-expiry counts

### 16.3 Audit trail

Audit events should be append-oriented and capture actor, action, target resource, timestamp, outcome and relevant change metadata. Do not use ordinary application logs as a substitute for durable audit records.

---

## 17. Testing Strategy

### 17.1 Test layers

| Layer | What to test | Examples |
|---|---|---|
| Unit | Pure domain logic | Algorithm classification, canonical IDs, risk rules |
| Component | Module behaviour | Correlation service, scan policy validator |
| Integration | Real dependencies | PostgreSQL transactions, Redis queue, worker |
| Contract | API schemas | Request validation, response compatibility |
| Security | Abuse and boundary cases | SSRF, DNS rebinding, tenant isolation |
| End-to-end | User journey | Authorised target to findings and CBOM |
| Regression | Previously fixed defects | Certificate parsing and retry behaviour |

### 17.2 Essential test scenarios

- Invalid hostname, malformed port and unsupported protocol.
- Target outside approved scope.
- Expired or revoked authorisation.
- DNS resolving to private or metadata address.
- DNS answer changing between validation and connection.
- TLS handshake timeout and connection refusal.
- Missing or malformed certificate chain.
- Unknown algorithm or unsupported TLS extension.
- Certificate rotation across two scans.
- Same certificate observed on multiple endpoints.
- Duplicate task delivery.
- Worker crash and lease recovery.
- Cancellation during a running scan.
- Partial scan with one endpoint failing.
- Tenant A attempting to read Tenant B resources.
- Risk assessment with incomplete critical evidence.
- CBOM export accurately reporting coverage gaps.

### 17.3 Test data

Use synthetic certificates, local test TLS servers and controlled fixtures. Never use customer production secrets or private keys in test fixtures. Any test key material must be generated solely for testing and clearly marked as non-production.

---

## 18. Code Quality and Engineering Conventions

### 18.1 Python

Suggested tools:
- Ruff for linting and formatting
- Mypy or Pyright for static typing
- Pytest for tests
- Coverage reporting
- Pre-commit hooks

Conventions:
- Type public functions and domain boundaries.
- Keep functions focused.
- Use explicit domain exceptions.
- Avoid broad exception swallowing.
- Use dependency injection for external systems.
- Keep network code separate from domain rules.
- Use structured logging.
- Avoid hard-coded configuration and secrets.

### 18.2 TypeScript

Suggested tools:
- ESLint
- Prettier
- TypeScript strict mode
- Frontend unit/component test framework

Conventions:
- Avoid `any` unless justified and isolated.
- Keep API types aligned with OpenAPI.
- Keep domain/business logic out of presentation components.
- Use reusable components for evidence and status display.
- Handle loading, empty, partial and error states explicitly.

### 18.3 Git workflow

Suggested branch naming:
- `feature/<short-description>`
- `fix/<short-description>`
- `security/<short-description>`
- `docs/<short-description>`
- `chore/<short-description>`

Pull requests should include:
- Purpose and scope
- Linked issue
- Design/API/database impact
- Security impact
- Tests run and results
- Screenshots for UI changes
- Migration and rollback notes where applicable
- Known limitations

Require at least one reviewer. Security-sensitive scanner, tenant-isolation and authentication changes should receive designated security review.

---

## 19. CI/CD Pipeline

### 19.1 Pull request checks

Every pull request should run:

1. Formatting and lint checks
2. Python static type checks
3. Backend unit tests
4. Frontend lint/type checks/tests
5. API schema generation/validation
6. Migration consistency checks
7. Container build
8. Dependency vulnerability scan
9. Secret scanning
10. Software composition analysis
11. Relevant security tests

### 19.2 Main branch checks

On merge:
- Re-run required checks.
- Build versioned container images.
- Generate build metadata/SBOM as appropriate.
- Publish to an approved registry.
- Deploy only to the approved development/staging environment through controlled workflow.

### 19.3 Production release

Production release should require:
- Approved change/release record
- Reviewed migration plan
- Backup/restore readiness
- Security and QA sign-off
- Environment-specific configuration
- Rollback or forward-fix plan
- Post-deployment smoke tests
- Audit record of release version

Do not place production credentials in repository variables unless the organisation's approved secret-management model explicitly permits it.

---

## 20. Security and Privacy Checklist

### 20.1 Before first external scan

- [ ] Written authorisation recorded.
- [ ] Target ownership and scope verified.
- [ ] DNS and IP policy implemented.
- [ ] Private, loopback, link-local and metadata ranges blocked by default.
- [ ] DNS rebinding protections tested.
- [ ] Port allowlist enforced.
- [ ] Connection and execution timeouts enforced.
- [ ] Concurrency and rate limits enforced.
- [ ] Redirect policy defined.
- [ ] No private-key or secret collection.
- [ ] Scan actions and policy denials audited.
- [ ] Worker egress is restricted.
- [ ] Error messages do not disclose sensitive internals.

### 20.2 Before onboarding a customer

- [ ] Tenant isolation tested.
- [ ] Authentication and RBAC reviewed.
- [ ] Data retention/deletion policy approved.
- [ ] Backup and recovery tested.
- [ ] Encryption in transit and at rest addressed.
- [ ] Audit access and retention addressed.
- [ ] Dependency and container scanning enabled.
- [ ] Incident response and operational ownership defined.
- [ ] Customer-facing limitations and coverage semantics reviewed.

---

## 21. Sprint-wise Implementation Plan

The schedule below is a proposed engineering sequence. Actual duration depends on team size, access to infrastructure, review cycles and product decisions. Do not treat it as a committed delivery date until the team estimates it.

### Sprint 0 — Repository and engineering foundation

**Goal:** Make the project reproducible and ready for collaborative development.

Tasks:
- Confirm repository name, access and ownership.
- Create monorepo structure.
- Add README, contribution guide and environment example.
- Configure Python and frontend package managers.
- Add Docker Compose for PostgreSQL and Redis.
- Add API and frontend skeletons.
- Add lint, formatting and test commands.
- Add GitHub Actions PR workflow.
- Add architecture decision record template.

Acceptance:
- A new developer can clone the repo and follow setup instructions.
- API health endpoint responds locally.
- Frontend loads locally.
- PostgreSQL and Redis pass health checks.
- CI runs on a pull request.

### Sprint 1 — Persistence and core domain

**Goal:** Establish durable project, target, authorisation and scan records.

Tasks:
- Configure SQLAlchemy and Alembic.
- Implement initial schema.
- Implement project and target domain services.
- Implement authorisation records and validation.
- Add tenant/project access checks.
- Add API endpoints for project and target management.
- Add integration tests.

Acceptance:
- Project and target records persist.
- Out-of-scope targets are rejected.
- Authorisation metadata is auditable.
- Migrations work on a clean database.

### Sprint 2 — Scan orchestration foundation

**Goal:** Create reliable asynchronous scan jobs without yet expanding scanner scope.

Tasks:
- Configure Celery and Redis.
- Implement scan validation and submission endpoints.
- Implement durable job state and execution records.
- Add worker identity and lease/heartbeat logic.
- Add retry, cancellation and failure handling.
- Add scan progress/status endpoint.
- Test duplicate delivery and worker restart.

Acceptance:
- An authorised scan request creates one durable job.
- Worker can claim and complete a controlled test job.
- Duplicate delivery does not duplicate persisted effects.
- Failures and cancellation are represented correctly.

### Sprint 3 — TLS collector POC

**Goal:** Collect a small, reliable set of TLS observations from explicitly authorised endpoints.

Tasks:
- Implement target and DNS safety validation.
- Implement bounded TLS connection/handshake.
- Parse server certificate chain.
- Capture protocol, cipher suite and available key-exchange metadata.
- Extract certificate signature/public-key metadata separately.
- Add collector version and provenance envelope.
- Add synthetic TLS test fixtures and security tests.

Acceptance:
- Collector returns structured observations for supported test endpoints.
- Unsupported or unavailable data is explicitly marked.
- Unsafe destinations are blocked.
- Timeouts and resource limits are enforced.
- No secrets/private keys are collected.

### Sprint 4 — Observation persistence and CBOM correlation

**Goal:** Convert raw collector output into a traceable inventory.

Tasks:
- Implement observation validation and immutable persistence.
- Implement canonical endpoint and certificate identity.
- Implement public-key identity separately.
- Implement asset match/create and typed relationships.
- Implement certificate rotation handling.
- Implement coverage summaries.
- Add correlation and idempotency tests.

Acceptance:
- Repeated scans link observations to existing assets where identity matches.
- Certificate rotation creates a new certificate asset.
- Ambiguous matches remain reviewable.
- Every asset/relationship is traceable to evidence.

### Sprint 5 — Findings and risk assessment

**Goal:** Produce explainable findings and a versioned provisional assessment.

Tasks:
- Implement initial algorithm classification catalogue.
- Implement versioned risk rules.
- Implement evidence-to-finding linkage.
- Implement confidence and missing-data handling.
- Implement risk assessment persistence and API.
- Add rationale and recommendation references.
- Review provisional score and thresholds with CISO/product owner.

Acceptance:
- Same inputs and ruleset version produce deterministic output.
- Findings link to supporting evidence.
- Missing critical evidence does not silently become zero risk.
- Score methodology and provisional status are visible.
- CISO/product approval is recorded before customer-facing use of the score.

### Sprint 6 — Frontend workflow and CBOM export

**Goal:** Make the discovery workflow usable by an analyst.

Tasks:
- Implement project and target screens.
- Implement authorisation and scan submission flow.
- Implement scan progress/status.
- Implement findings and evidence detail.
- Implement asset inventory and relationship views.
- Implement CBOM snapshot and export.
- Display coverage and limitations prominently.

Acceptance:
- Analyst can complete the authorised scan journey through the UI.
- Partial/failed/unsupported states are clear.
- CBOM export includes scope, version and coverage limitations.
- UI does not claim unobserved areas are safe.

### Sprint 7 — Hardening and pilot readiness

**Goal:** Prepare a controlled pilot, not unrestricted production deployment.

Tasks:
- Complete tenant-isolation and SSRF security testing.
- Review authentication, RBAC and audit.
- Add operational dashboards and alerts.
- Test backup and restore.
- Review data retention and privacy.
- Conduct dependency/container security review.
- Prepare pilot runbook and known-limitations document.
- Obtain security/product sign-off.

Acceptance:
- Critical security findings are resolved or formally accepted.
- Pilot scope and authorisation are documented.
- Operational owners and escalation paths are known.
- Recovery and rollback procedures are tested.
- Pilot limitations are communicated honestly.

---

## 22. Definition of Done

A feature is not complete merely because it works on a developer machine.

A feature is done when:
- Acceptance criteria are met.
- Code is reviewed and merged.
- Tests cover normal, error and relevant abuse paths.
- Lint and type checks pass.
- API and database contracts are updated.
- Migrations are tested where applicable.
- Logs and audit events are appropriate.
- Security and privacy implications are reviewed.
- Documentation and runbooks are updated.
- Known limitations are documented.
- No unsupported product claims are introduced.

For scanner changes, include target-safety and network-boundary tests. For risk-engine changes, include determinism, explainability and ruleset-version tests. For CBOM changes, include provenance and coverage tests.

---

## 23. Architecture Decision Records to Create

Create short ADRs for decisions that affect future compatibility or security:

1. Monorepo versus multiple repositories.
2. Modular monolith and worker deployment model.
3. Authentication provider and OIDC integration.
4. Tenant isolation strategy and PostgreSQL RLS decision.
5. Queue/job durability and lease strategy.
6. TLS inspection library/tooling and supported metadata.
7. Canonical identity rules for endpoint, certificate and public key.
8. Observation immutability and retention.
9. Risk scoring methodology approval and versioning.
10. CBOM schema and export format/version.
11. Production deployment and secrets management.
12. Data residency, retention and deletion requirements.

Each ADR should state context, options, decision, consequences, security impact, owner and date.

---

## 24. Open Decisions Before Implementation

The engineering team should resolve or explicitly defer the following:

| Decision | Why it matters | Suggested owner |
|---|---|---|
| Final repository name and ownership | Access, CI and code governance | Engineering lead |
| Identity provider | Authentication and user lifecycle | CTO / Security |
| Tenant and project model | Data isolation and permissions | Architecture |
| Deployment target | Networking, secrets and operations | DevOps / CTO |
| Approved scan scope | Legal and operational safety | CISO / Customer owner |
| TLS metadata library/tooling | Accuracy and supported observations | Scanner engineer |
| Supported ports and protocols | Product scope and safety | Product / Security |
| Risk score weights and thresholds | Customer-facing risk interpretation | CISO / Product |
| CBOM export schema | Interoperability and versioning | Architecture |
| Data retention and residency | Privacy and compliance | Security / Legal |
| Pilot customer and test targets | Validation and acceptance | Product / Sales |
| Alerting and incident ownership | Operational readiness | Engineering / Security |

Do not silently choose answers to these questions in code when they materially affect customer security, product claims or data handling.

---

## 25. Immediate Engineering Backlog

The following is a practical initial backlog. Convert each item into a repository issue with owner, estimate and acceptance criteria.

| ID | Work item | Priority | Dependency |
|---|---|---|---|
| QF-001 | Create repository and branch protection | P0 | None |
| QF-002 | Add architecture and contribution documentation | P0 | QF-001 |
| QF-003 | Add Python backend skeleton and health endpoint | P0 | QF-001 |
| QF-004 | Add React frontend skeleton | P0 | QF-001 |
| QF-005 | Add PostgreSQL and Redis Compose services | P0 | QF-001 |
| QF-006 | Configure SQLAlchemy and Alembic | P0 | QF-003, QF-005 |
| QF-007 | Add CI lint/type/test/build workflow | P0 | QF-003, QF-004 |
| QF-008 | Implement project and target models/APIs | P1 | QF-006 |
| QF-009 | Implement authorisation and scan policy model | P1 | QF-008 |
| QF-010 | Implement durable scan job orchestration | P1 | QF-006, QF-005 |
| QF-011 | Implement safe TLS collector prototype | P1 | QF-009 |
| QF-012 | Implement observation persistence | P1 | QF-011 |
| QF-013 | Implement asset correlation | P1 | QF-012 |
| QF-014 | Implement findings and risk rules | P1 | QF-013 |
| QF-015 | Implement CBOM snapshot/export | P2 | QF-013 |
| QF-016 | Implement analyst frontend workflow | P2 | QF-008 through QF-015 |
| QF-017 | Complete pilot security and operations review | P0 before pilot | Core workflow |

---

## 26. Release Gates

### Gate A — Developer Preview
- Repository and local setup work.
- API and frontend skeletons are functional.
- CI is active.
- No external scanning required.

### Gate B — Internal Discovery POC
- Approved test targets only.
- TLS observations are evidence-backed.
- Worker reliability and safety tests pass.
- Findings and inventory are traceable.
- No claim of full enterprise discovery.

### Gate C — Analyst MVP
- Projects, targets, authorisations, scans, findings and assets are usable.
- CBOM snapshot/export works.
- Coverage and unknowns are visible.
- Risk methodology is approved for the intended use or clearly labelled provisional.

### Gate D — Controlled Pilot Readiness
- Tenant isolation and security review completed.
- Operational monitoring, backup and incident procedures exist.
- Customer authorisation and pilot scope are documented.
- Limitations and data handling are communicated.

Passing one gate does not automatically approve the next. Each gate requires explicit review and sign-off.

---

## 27. Final Recommendation

Start with **Sprint 0**, not with the full scanner or risk engine. Establish the repository, local environment, package boundaries, migrations and CI first. Then implement the smallest vertical slice:

**Project → Authorised Target → Scan Job → TLS Observation → Persisted Evidence → Asset Correlation → Finding → Risk Explanation → CBOM Snapshot.**

This vertical slice validates the product architecture end-to-end while keeping the initial scope controlled. Build only the collector capabilities that can be reliably observed and tested. Expand into source-code, dependency, internal-network, cloud, KMS/HSM and application collectors as separate authorised workstreams.

The platform's credibility will come from accurate evidence, safe collection, traceable inventory, explainable prioritisation and honest coverage—not from the number of dashboards or algorithms advertised.

---

## Appendix A — Suggested Initial README Outline

1. Product overview and current scope
2. Architecture diagram
3. Repository structure
4. Prerequisites
5. Local setup
6. Environment variables
7. Start/stop commands
8. Run migrations
9. Run tests and quality checks
10. API documentation location
11. Scanner safety policy
12. Contribution and pull-request process
13. Security reporting process
14. Known limitations and roadmap

## Appendix B — Suggested Pull Request Template

```markdown
## Summary
What does this change do?

## Linked issue
Closes #

## Scope
- [ ] Backend
- [ ] Frontend
- [ ] Worker / scanner
- [ ] Database / migration
- [ ] Documentation
- [ ] CI / infrastructure

## Design impact
Describe API, schema, module-boundary or architecture changes.

## Security and privacy impact
Describe authorisation, tenant isolation, network access, secrets and data-handling implications.

## Validation
- [ ] Unit tests
- [ ] Integration tests
- [ ] Security tests (if applicable)
- [ ] Frontend checks (if applicable)
- [ ] Migration tested (if applicable)
- [ ] Manual verification

## Evidence
Add logs, screenshots or test output where useful.

## Risks and limitations
List known gaps and follow-up work.
```

## Appendix C — Non-Negotiable Engineering Rules

1. No scan without explicit authorisation and validated scope.
2. No unrestricted URL fetching from user input.
3. No private-key or secret collection by the discovery collector.
4. No direct worker writes that bypass domain validation and audit requirements.
5. No mutable rewriting of historical observations.
6. No merging assets solely because names look similar.
7. No treating unknown cryptographic details as safe.
8. No presenting provisional risk scores as standards-based or certified.
9. No claiming public TLS discovery equals complete enterprise cryptographic inventory.
10. No production migration or cryptographic change without an approved change process.
