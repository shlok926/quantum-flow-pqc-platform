# Requirements Traceability Matrix (RTM)

**Status:** Draft — Pending Company Review and Approval  
**Document ID:** QFT-PM-RTM-001  
**Version:** 1.0 — Initial Engineering Draft  
**Date:** 02 November 2026  
**Classification:** Internal Technical Management  
**Owner:** Technical Lead / Product Owner  
**Approval Authority:** `[COMPANY APPROVAL REQUIRED — Product Owner & Technical Lead]`  
**Primary Sources:** PRD v1.0, TRD v1.0, SAD v1.0, Database Design v1.0, API Specification v1.0, Threat Model v1.0, Development Backlog

---

## 1. Purpose and Traceability Model

This Requirements Traceability Matrix (RTM) establishes bidirectional traceability across the platform lifecycle:
$$\text{PRD / Business Need} \longleftrightarrow \text{TRD Specification} \longleftrightarrow \text{Architecture Component} \longleftrightarrow \text{Database \& API} \longleftrightarrow \text{Test Suite} \longleftrightarrow \text{Backlog Task}$$

### Identifier Scheme Convention
- **Functional Requirements (`FR-01` to `FR-09`):** Extracted directly from approved PRD v1.0 Section 3.
- **Non-Functional Requirements (`NFR-01` to `NFR-06`):** Extracted directly from approved PRD v1.0 Section 4.
- **Technical Requirements (`TR-01` to `TR-12`):** `[PROPOSED ID SCHEME]` systematically derived from TRD v1.0 sections to provide stable engineering references.
- **Backlog IDs (`QF-001` to `QF-047`):** Direct linkage to [`Development_Backlog.md`](./Development_Backlog.md).
- **Status Standard:** All initial implementation statuses are set to `NOT STARTED`.

---

## 2. Functional Requirements Traceability Matrix

| Requirement ID | Requirement Description | Source Document | Design Reference (SAD / DDD / API) | Implementation Reference (Planned) | Test Reference | Backlog ID | Status |
|---|---|---|---|---|---|:---:|:---:|
| **FR-01** | **Organisation & Project Management:** Multi-tenant project metadata, tenant isolation, access controls. | PRD v1.0 §3.1 | SAD §4; DDD §4 (`tenants`, `projects`); API §3 (`/projects`) | `apps/api/routers/projects.py` | `tests/unit/test_projects.py`; `tests/security/test_tenant_isolation.py` | `QF-011`, `QF-015` | NOT STARTED |
| **FR-02** | **Scan Scope Management:** Target hostname, IP, port boundary configuration; written authorization verification. | PRD v1.0 §3.2 | SAD §5; DDD §4 (`targets`, `authorisations`); API §4 (`/targets`, `/authorisations`) | `apps/api/routers/targets.py`; `packages/scanner/safety/` | `tests/unit/test_target_validation.py`; `tests/security/test_authorisation_guard.py` | `QF-012`, `QF-013` | NOT STARTED |
| **FR-03** | **Discovery Orchestration:** Asynchronous scan job submission, Celery queue dispatch, execution state machine, heartbeat, timeout, cancellation. | PRD v1.0 §3.3 | TRD §14; SAD §6; DDD §4 (`scan_jobs`); API §5 (`/scan-jobs`) | `apps/worker/celery_app.py`; `apps/api/routers/scan_jobs.py` | `tests/integration/test_worker_orchestration.py`; `tests/unit/test_scan_state.py` | `QF-014`, `QF-017`, `QF-018`, `QF-020` | NOT STARTED |
| **FR-04** | **Cryptographic Identification:** Extract TLS version, cipher suite, key exchange parameters, and complete X.509 certificate chains with ASN.1 parser. | PRD v1.0 §3.4 | TRD §5.1, §5.2; SAD §7; CBOM Design §4; DDD §4 (`raw_observations`) | `packages/scanner/tls/handshake.py`; `packages/scanner/tls/certificate_parser.py` | `tests/unit/test_asn1_parser.py`; `tests/integration/test_synthetic_tls.py` | `QF-024`, `QF-025`, `QF-026` | NOT STARTED |
| **FR-05** | **Cryptographic Asset Inventory (CBOM):** Normalize raw observations into stable cryptographic assets, typed relationships, certificate rotation tracking, and coverage summaries. | PRD v1.0 §3.5 | TRD §6, §7; SAD §8; CBOM Design §5; DDD §4 (`crypto_assets`, `relationships`) | `packages/cbom/correlation.py`; `packages/cbom/cyclonedx.py` | `tests/unit/test_cbom_correlation.py`; `tests/contract/test_cyclonedx_export.py` | `QF-028`, `QF-029`, `QF-030`, `QF-031` | NOT STARTED |
| **FR-06** | **Quantum Risk Assessment:** Deterministic evaluation of discovered assets against Shor's and Grover's algorithms using versioned rulesets (`RISK_RULESET_VERSION`). | PRD v1.0 §3.6 | TRD §8; SAD §9; Risk Methodology §4; DDD §4 (`risk_assessments`, `findings`) | `packages/risk-engine/engine.py`; `packages/risk-engine/rules.py` | `tests/unit/test_risk_determinism.py`; `tests/regression/test_golden_dataset.py` | `QF-033`, `QF-034`, `QF-036`, `QF-037` | NOT STARTED |
| **FR-07** | **Recommendation Generation:** Actionable remediation packages, PQC migration pathways (NIST FIPS 203/204/205), and crypto-agility guidance linked to findings. | PRD v1.0 §3.7 | TRD §9; SAD §10; Risk Methodology §6; DDD §4 (`recommendations`) | `packages/risk-engine/recommendations.py` | `tests/unit/test_recommendations.py` | `QF-035` | NOT STARTED |
| **FR-08** | **Reporting & Export:** Executive summaries, technical audit views, and machine-readable exports (CycloneDX 1.6 JSON, CSV, PDF). | PRD v1.0 §3.8 | TRD §17; SAD §11; API §7 (`/reports`, `/cbom/export`) | `apps/api/routers/reports.py`; `packages/cbom/export.py` | `tests/integration/test_cbom_export.py` | `QF-041`, `QF-042` | NOT STARTED |
| **FR-09** | **Audit & History:** Tamper-evident, append-only logging of user actions, policy transitions, scan events, and SHA-256 evidence digests. | PRD v1.0 §3.9 | TRD §13.4; SAD §12; DDD §4 (`audit_logs`) | `apps/api/middleware/audit.py`; `packages/scanner/models.py` | `tests/security/test_audit_immutability.py` | `QF-046` | NOT STARTED |

---

## 3. Non-Functional & Security Requirements Traceability Matrix

| Requirement ID | Requirement Description | Source Document | Architecture & Security Reference | Implementation Reference (Planned) | Verification / Test Reference | Backlog ID | Status |
|---|---|---|---|---|---|:---:|:---:|
| **NFR-01** | **Security & Egress Control:** Non-bypassable deny-by-default socket filter; block RFC 1918, loopback, link-local, and cloud metadata (`169.254.169.254`). | PRD v1.0 §4.1; TRD §13.1 | Threat Model §4.1; SAD §13 | `packages/scanner/safety/target_validation.py`; `network_policy.py` | `tests/security/test_ssrf_egress.py`; `tests/security/test_dns_rebinding.py` | `QF-022`, `QF-023`, `QF-044` | NOT STARTED |
| **NFR-02** | **Tenant Isolation:** Enforce tenant separation derived from validated JWT claims; PostgreSQL Row-Level Security (RLS). | PRD v1.0 §4.1; TRD §12.3 | Threat Model §4.5; SAD §13 | `apps/api/auth/jwt.py`; `apps/api/dependencies.py` | `tests/security/test_tenant_isolation.py` | `QF-016`, `QF-043`, `QF-045` | NOT STARTED |
| **NFR-03** | **Zero Customer Secrets:** The platform must never collect, inspect, request, or store customer private keys or passwords. | PRD v1.0 §4.1; TRD §13.3 | Threat Model §1.2; Data Governance §1 | `packages/scanner/tls/client.py` | Code Review Gate; Static analysis secret scan | `QF-024` | NOT STARTED |
| **NFR-04** | **Performance & Bounded Timeouts:** Enforce configurable socket timeouts (10s connect, 30s max total); prevent worker hang. | PRD v1.0 §4.2; TRD §18 | TRD §18; SAD §6 | `packages/scanner/tls/handshake.py` | `tests/unit/test_socket_timeouts.py` | `QF-024` | NOT STARTED |
| **NFR-05** | **Reliability & Idempotency:** Worker crash recovery; duplicate scan job delivery must produce zero duplicate DB assets. | PRD v1.0 §4.3; TRD §14.2 | Implementation Blueprint §13 | `apps/worker/tasks/scan.py` | `tests/integration/test_worker_crash_recovery.py` | `QF-019`, `QF-021` | NOT STARTED |
| **NFR-06** | **Deterministic Explainability:** 100% deterministic risk scores and findings across repeated evaluations with identical ruleset versions. | PRD v1.0 §4.6; TRD §8.6 | Risk Methodology §5; TRD §8.6 | `packages/risk-engine/engine.py` | `tests/unit/test_risk_determinism.py` | `QF-034`, `QF-037` | NOT STARTED |

---

## 4. Proposed Technical Requirements Reference `[PROPOSED ID SCHEME]`

| Proposed ID | Technical Requirement Scope | TRD Source | Target Architecture Component | Backlog Mapping | Status |
|---|---|---|---|:---:|:---:|
| `TR-01` | Modular Monolith layout with isolated Celery background workers | TRD §3.1, §4.2 | Monorepo root (`apps/`, `packages/`, `infra/`) | `QF-001`, `QF-002` | NOT STARTED |
| `TR-02` | Python 3.12+ backend and FastAPI async REST API engine | TRD §4.1 | `apps/api/` | `QF-003`, `QF-005` | NOT STARTED |
| `TR-03` | React 18 / TypeScript 5.4+ frontend with Vite build system | TRD §4.1 | `apps/web/` | `QF-003`, `QF-006` | NOT STARTED |
| `TR-04` | PostgreSQL 16 persistence with async SQLAlchemy 2.0 and Alembic | TRD §11.1 | `migrations/`, `apps/api/models/` | `QF-004`, `QF-010` | NOT STARTED |
| `TR-05` | Redis 7 broker for Celery task queuing and distributed caching | TRD §4.1, §14 | `infra/docker/`, `apps/worker/` | `QF-004`, `QF-017` | NOT STARTED |
| `TR-06` | Two-stage DNS resolution with worker-pinned IP connection and SNI | TRD §5.1, §13.1 | `packages/scanner/safety/dns_policy.py` | `QF-023` | NOT STARTED |
| `TR-07` | Raw observation envelope with SHA-256 digest and immutable JSONB | TRD §6.2, §11.4 | `packages/scanner/models.py` | `QF-028` | NOT STARTED |
| `TR-08` | Cryptographic asset graph with deduplication and rotation tracking | TRD §6.3, §7.3 | `packages/cbom/` | `QF-029`, `QF-031` | NOT STARTED |
| `TR-09` | Versioned algorithm classification catalog (NIST PQC / CNSA 2.0) | TRD §8.2 | `packages/risk-engine/catalog.py` | `QF-033` | NOT STARTED |
| `TR-10` | CycloneDX 1.6 Cryptographic BOM export schema compliance | TRD §7.2, §17.3 | `packages/cbom/cyclonedx.py` | `QF-042` | NOT STARTED |
| `TR-11` | OIDC / OAuth2 authentication with JWT claim tenant derivation | TRD §12.1 | `apps/api/auth/` | `QF-045` | NOT STARTED |
| `TR-12` | Code quality gates: Ruff format/lint, Mypy strict, Pytest CI | TRD §20.1 | `.github/workflows/ci.yml` | `QF-007`, `QF-008` | NOT STARTED |

---

## 5. Traceability Governance & Maintenance

- Any PR introducing a new functional feature or modifying an API contract must update this matrix in the same PR.
- The Technical Lead and QA Lead review this matrix prior to the completion of each sprint.

