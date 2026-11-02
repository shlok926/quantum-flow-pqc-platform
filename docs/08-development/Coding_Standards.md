# Quantum Flow Engineering Coding Standards

## 1. Introduction & Core Philosophy

This document defines the official engineering standards, design conventions, and quality gates for the **Quantum Flow Technologies PQC Discovery & Risk Assessment Platform**.

As an enterprise cryptographic security product, Quantum Flow demands high code clarity, absolute determinism, strict type safety, defensive error handling, and robust security controls. Code must be written not just to function, but to be auditable, maintainable, and verifiable.

---

## 2. Python Standards & Conventions

- **Target Version:** Python 3.12+
- **Style Guide:** Strict PEP 8 enforcement via **Ruff** (line length limit: **100 characters**).
- **Type Annotations:** **100% strict type hints required** on all public functions, methods, and class attributes. Unannotated functions will fail Mypy in CI.
- **Imports:** Group imports in three distinct blocks separated by single blank lines:
  1. Standard library imports
  2. Third-party dependencies
  3. First-party application/package imports
- **Formatting:** Code formatted exclusively using `ruff format`. No manual style arguments in PRs.

```python
# Good Example:
from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field

from packages.scanner.models import ScanObservation


def process_observations(
    scan_id: UUID,
    observations: Sequence[ScanObservation],
    recorded_at: datetime | None = None,
) -> int:
    """Process and correlate scan observations for a specific scan job."""
    timestamp = recorded_at or datetime.now(timezone.utc)
    ...
```

---

## 3. FastAPI & API Design Conventions

- **Framework:** FastAPI with asynchronous endpoint handlers (`async def`) for I/O-bound operations (database queries, network requests) and synchronous handlers for CPU-bound tasks.
- **RESTful Resource Naming:**
  - Resource collections must be plural nouns in kebab-case (e.g., `/api/v1/scan-jobs`, `/api/v1/cryptographic-assets`).
  - Hierarchical sub-resources: `/api/v1/projects/{project_id}/targets`.
  - Action endpoints must use POST with descriptive nouns or verbs: `/api/v1/scan-jobs/{scan_id}/cancel`.
- **Versioning:** All public endpoints must reside under a versioned path prefix: `/api/v1/...`.
- **Dependency Injection:** Use FastAPI's `Depends` for authentication, database session management, and tenant validation. Never instantiate global database sessions.
- **Response Envelopes:** Standardized JSON envelopes for API responses:
  ```json
  {
    "success": true,
    "data": { ... },
    "error": null,
    "meta": {
      "request_id": "req-123e4567-e89b-12d3-a456-426614174000",
      "timestamp": "2026-11-02T12:00:00Z"
    }
  }
  ```

---

## 4. Pydantic Conventions (Pydantic v2)

- Use `pydantic.BaseModel` with strict typing.
- Separate schemas by responsibility:
  - `*CreateRequest` (payload for creation)
  - `*UpdateRequest` (payload for partial updates)
  - `*Response` (payload returned by API)
  - `*InDB` (internal representation with persistence IDs)
- Model Configuration:
  ```python
  from pydantic import BaseModel, ConfigDict

  class AssetResponse(BaseModel):
      model_config = ConfigDict(from_attributes=True, extra="forbid")
      
      id: UUID
      algorithm_name: str
      key_size_bits: int | None = None
  ```
- Always provide clear field descriptions using `Field(description="...")`.

---

## 5. SQLAlchemy 2.0 & Alembic Conventions

- **Syntax:** Strict SQLAlchemy 2.0 declarative style using `Mapped[...]` and `mapped_column(...)`.
- **Primary Keys:** Standardize on UUIDv7 or UUIDv4 stored as native PostgreSQL `UUID`.
- **Timestamps:** Every table must include `created_at` and `updated_at` timestamps with UTC timezone (`DateTime(timezone=True)`).
- **Tenant Scoping:** All tenant-owned tables must explicitly include a non-nullable `tenant_id` foreign key.
- **Alembic Migrations:**
  - Every migration script must have a clear, descriptive message (e.g., `alembic revision -m "create_scan_jobs_table"`).
  - Both `upgrade()` and `downgrade()` methods must be fully implemented and tested.
  - Never alter existing historical migration files once merged to `main`. Always create a new revision.

---

## 6. TypeScript & React Standards

- **Target Version:** TypeScript 5.4+, React 18+
- **Tooling:** Vite, ESLint (`@typescript-eslint`), Prettier, Tailwind CSS.
- **Type Safety:**
  - `any` is strictly prohibited. Use `unknown` with type narrowing if type is ambiguous.
  - Export shared types and interfaces from `types/` or generate them from OpenAPI specifications.
- **Component Architecture:**
  - Functional components with typed props using `React.FC<Props>` or direct parameter typing:
    ```tsx
    interface TargetCardProps {
      targetId: string;
      hostname: string;
      port: number;
      isAuthorized: boolean;
      onScanRequested: (targetId: string) => void;
    }

    export const TargetCard = ({ targetId, hostname, port, isAuthorized, onScanRequested }: TargetCardProps) => { ... };
    ```
  - Keep components modular. Separate data-fetching hooks (`useScanResults`) from presentation components.
  - Prominently display scan coverage limits and partial observation warnings. Never state that an uninspected network area is safe.

---

## 7. Error Handling & Exception Discipline

- **Never Swallow Exceptions:** Never use bare `except:` or `except Exception: pass`. Catch specific exceptions and re-raise or wrap with contextual metadata.
- **Domain Exceptions:** Define explicit domain exception hierarchies inheriting from a base `QuantumFlowException`:
  ```python
  class QuantumFlowException(Exception):
      """Base exception for platform domain errors."""

  class ScopeViolationError(QuantumFlowException):
      """Raised when a target IP falls outside authorized scan boundaries."""
  ```
- **HTTP Error Translation:** Catch domain exceptions in global FastAPI exception handlers and map them to consistent RFC 7807 Problem Details or standardized JSON error envelopes.
- **Worker Resilience:** In Celery tasks, handle network failures with exponential backoff and maximum retry limits. Unrecoverable validation errors must fail immediately and mark the scan job as failed.

---

## 8. Logging & Observability

- **Structured Logging:** Use structured JSON logging in production (via `structlog` or `logging` with JSON formatters).
- **Context Propagation:** Ensure every log record includes:
  - `tenant_id`
  - `scan_id` / `job_id` (if applicable)
  - `request_id` / `correlation_id`
- **Log Levels:**
  - `DEBUG`: Verbose diagnostics (handshake negotiation details, parser steps).
  - `INFO`: Normal operational events (scan job created, worker claimed task, scan completed).
  - `WARNING`: Recoverable anomalies (target handshake timed out, certificate expired, unsupported extension).
  - `ERROR`: System failures requiring investigation (database connection failed, unhandled exception in worker).
  - `CRITICAL`: System-wide outages or catastrophic integrity violations.
- **Data Minimisation & Sanitisation:**
  - **CRITICAL:** NEVER log credentials, authorization tokens, private keys, or raw customer file contents. Redact Authorization headers automatically.

---

## 9. Security Engineering & Safe Scanning Rules

Every engineer must adhere to the following non-negotiable security principles:

1. **Deny-by-Default Egress:** Scanner workers must validate target hostnames and IPs against private/internal IP address ranges (RFC 1918, RFC 3927, loopback, link-local, AWS metadata `169.254.169.254`) before establishing any socket connection.
2. **DNS Rebinding Prevention:** Target IPs must be validated upon DNS resolution and socket connections must bind directly to the validated IP, using SNI for virtual hosting.
3. **Written Authorization Verification:** No scan job may transition to `RUNNING` without a verified, active authorization record.
4. **Tenant Context from Token:** Always derive `tenant_id` from the cryptographically verified JWT payload. Never accept `tenant_id` from client request bodies or query parameters.
5. **No Private Key Ingestion:** The platform does not collect, import, or store private keys. Any collector attempting to extract private keys must be rejected in code review.

---

## 10. Testing Requirements & Coverage Gates

All code submissions must be backed by automated tests:

- **Unit Tests:** Fast, isolated tests targeting pure functions, parsing logic, risk score algorithms, and Pydantic models. Zero network or database dependencies.
- **Integration Tests:** Test FastAPI endpoints and database repositories using test containers or local test PostgreSQL databases.
- **Contract Tests:** Verify API schema stability against OpenAPI specifications.
- **Security Tests:** Unit tests verifying that out-of-scope IPs (e.g., `127.0.0.1`, `10.0.0.1`, `169.254.169.254`) are systematically blocked by target validation routines.
- **Determinism Tests:** Verify that risk scoring produces identical numeric scores and findings given identical inputs across multiple runs.
- **Coverage Goal:** Minimum **80% line coverage** on core domain logic, scanner safety filters, and risk calculation modules.

---

## 11. Git Commit Message Conventions

We enforce the **Conventional Commits** specification:

```text
<type>(<scope>): <short description in present imperative tense>

[optional body providing technical context and motivation]

[optional footer referencing issues, e.g., Fixes #123, Refs #456]
```

### Allowed Types:
- `feat`: A new user-facing or technical feature
- `fix`: A bug fix
- `docs`: Documentation-only changes
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `test`: Adding or correcting tests
- `chore`: Tooling, configuration, or dependency updates
- `security`: Specific security enhancements, vulnerability patches, or safety filters

### Examples:
- `feat(scanner): implement bounded TLS 1.3 socket handshake`
- `fix(cbom): prevent duplicate cryptographic asset generation on certificate rotation`
- `docs(adr): add ADR-0001 for modular monolith architecture`
- `security(egress): enforce RFC 1918 private IP blocking in target validator`

