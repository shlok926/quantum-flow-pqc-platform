# QUANTUM FLOW TECHNOLOGIES
# Technical Requirements Document (TRD)

**Product:** PQC Discovery & Migration Platform  
**Module:** Enterprise Cryptographic Discovery & Risk Assessment Scanner  
**Document ID:** QF-TRD-001  
**Version:** 1.0 — Initial Technical Draft  
**Status:** Draft — For Architecture and CISO Review  
**Classification:** Confidential  
**Companion Document:** PRD v1.0 — Enterprise Cryptographic Discovery & Risk Assessment Scanner  
**Product Reference:** Quantum Flow Product Vision & Roadmap, October 2026, Version 1.0

---

## Document Control

| Field | Value |
|---|---|
| Document owner | Product / Engineering |
| Technical reviewers | CISO, Backend, Security, DevOps, QA |
| Approval authority | To be confirmed by Quantum Flow |
| Current status | Draft |
| Review cadence | At architecture milestones and before major releases |

### Revision History

| Version | Date | Description |
|---|---|---|
| 1.0 | 02-Nov-2026 | Initial technical requirements draft |

### How to Read This Document

This TRD translates the PRD into proposed technical requirements and engineering constraints. It is not a record of an already implemented system. Technology selections, interfaces, data structures, limits and security controls in this document are proposals until reviewed and approved by the responsible Quantum Flow stakeholders.

The product vision document provides the strategic direction and broad architecture. Where that document does not specify implementation details, this TRD labels them as proposed design decisions or open decisions rather than presenting them as existing company decisions.

---

# 1. Purpose and Technical Goals

## 1.1 Purpose

This document defines the technical requirements for the Enterprise Cryptographic Discovery & Risk Assessment Scanner, the initial discovery and risk-prioritisation capability of Quantum Flow's broader PQC Discovery & Migration Platform.

It specifies:

- System context and logical architecture.
- Technical components and responsibilities.
- Discovery source interfaces.
- Collector execution and orchestration.
- Cryptographic observation and asset data models.
- Normalisation and CBOM requirements.
- Risk assessment engine requirements.
- API and integration requirements.
- Security, privacy and operational controls.
- Testing, validation and release requirements.
- Technical dependencies, constraints and unresolved decisions.

## 1.2 Technical Goals

The system shall:

1. Discover cryptographic information from multiple authorised source types.
2. Keep each discovery collector modular and independently testable.
3. Preserve evidence and provenance for every finding.
4. Distinguish direct observations from inferred or imported information.
5. Normalise heterogeneous findings into a common cryptographic asset model.
6. Support repeatable, versioned and explainable quantum-risk assessments.
7. Isolate scan failures so one collector failure does not discard successful findings from other collectors.
8. Enforce scope, permissions, resource limits and secure handling of customer data.
9. Support exportable inventory and assessment reports.
10. Provide a foundation for future migration planning and assurance workflows.

## 1.3 Out of Scope for This TRD

This document does not define:

- A production migration execution engine.
- Automatic changes to customer production systems.
- A proprietary cryptographic algorithm.
- A claim of complete discovery across inaccessible systems.
- A claim of NIST certification or regulatory compliance.
- Final commercial pricing, licensing or deployment contracts.

---

# 2. System Context and Design Principles

## 2.1 Product Workflow

The platform follows the product workflow:

**Discover → Inventory → Prioritise → Plan → Migrate → Assure**

The first scanner release primarily implements:

- Discover: collect observations from authorised sources.
- Inventory: normalise and store cryptographic assets as a CBOM.
- Prioritise: evaluate evidence and produce explainable risk findings.

It supplies structured outputs to future planning, migration and assurance capabilities.

## 2.2 Design Principles

### Modular collectors
Each source type shall be implemented as an independent collector with a defined input, output schema, execution contract and test suite.

### Evidence before conclusions
Risk findings must link to the underlying observation and its evidence. The system must not infer runtime cryptographic use solely from a source-code string or dependency name.

### Explicit provenance
Every observation must identify its source, collection method, timestamp, collector version and evidence classification.

### Safe by default
Scans must be restricted to approved targets and authorised data sources. Network access, repository access and file processing must have explicit controls.

### Explainable assessment
Risk rules must be deterministic, versioned, testable and explainable. AI-generated conclusions must not be the sole basis for a risk score.

### Incremental enterprise coverage
The architecture must support additional collectors without requiring a redesign of the inventory or risk engine.

### Honest coverage reporting
The system must report what was scanned, what was not scanned, what failed and what cannot be concluded.

### Standards-based cryptography
Cryptographic algorithms shall be integrated through maintained implementations and supported protocols. The platform will not invent cryptographic primitives.

---

# 3. Proposed System Architecture

## 3.1 Logical Architecture

The proposed system is organised into the following layers:

1. User Interface Layer
2. API and Identity Layer
3. Assessment and Scan Orchestration Layer
4. Discovery Collector Layer
5. Normalisation and Identification Layer
6. Cryptographic Inventory / CBOM Layer
7. Quantum Risk and Recommendation Layer
8. Reporting and Audit Layer
9. Persistence and Infrastructure Layer

## 3.2 Component View

```text
                         USER / SECURITY TEAM
                                  |
                                  v
                    REACT + TYPESCRIPT DASHBOARD
                                  |
                                  v
                       FASTAPI API / AUTH LAYER
                                  |
                    +-------------+-------------+
                    |                           |
                    v                           v
             ASSESSMENT SERVICE           SCOPE / POLICY
                    |                           |
                    +-------------+-------------+
                                  |
                                  v
                         SCAN ORCHESTRATOR
                                  |
                         JOB QUEUE / WORKERS
                                  |
          +-----------------------+------------------------+
          |            |           |           |           |
          v            v           v           v           v
       NETWORK      CERTIFICATE  SOURCE     DEPENDENCY  CONFIGURATION
       / TLS         COLLECTOR   COLLECTOR   COLLECTOR   COLLECTOR
          |            |           |           |           |
          +------------+-----------+-----------+-----------+
                                  |
                                  v
                       RAW OBSERVATION STORE
                                  |
                                  v
                    NORMALISATION / IDENTIFICATION
                                  |
                                  v
                      CRYPTOGRAPHIC ASSET MODEL
                                  |
                                  v
                         CBOM / RELATIONSHIPS
                                  |
                                  v
                      QUANTUM RISK RULE ENGINE
                                  |
                                  v
                    RECOMMENDATION / PRIORITISATION
                                  |
                     +------------+------------+
                     |                         |
                     v                         v
                DASHBOARD                 REPORT ENGINE
                     |                         |
                     +------------+------------+
                                  |
                                  v
                     AUDIT / SCAN HISTORY / EXPORT

       POSTGRESQL: metadata, assets, findings, jobs, audit
       OBJECT STORAGE: retained evidence and generated reports (if approved)
       REDIS: job broker / transient coordination (proposed)
```

## 3.3 Component Responsibilities

| Component | Responsibility | Primary output |
|---|---|---|
| Web UI | Assessment creation, scan status, inventory and findings | User actions |
| API layer | Validation, authentication, authorisation and API contracts | Validated requests |
| Assessment service | Organisation and assessment lifecycle | Assessment records |
| Scope/policy service | Target allowlists, approvals and limits | Approved scan scope |
| Scan orchestrator | Job creation, dispatch, retries and cancellation | Scan job state |
| Collectors | Source-specific data collection | Raw observations |
| Normaliser | Common schema mapping and validation | Normalised observations |
| Crypto identifier | Algorithm and protocol classification | Crypto classifications |
| CBOM service | Asset identity, relationships and history | Cryptographic inventory |
| Risk engine | Apply versioned rules to evidence | Risk findings |
| Recommendation engine | Map findings to next actions | Recommendations |
| Report engine | Build executive and technical outputs | HTML/PDF/JSON reports |
| Audit service | Record security-relevant actions | Audit events |

## 3.4 Deployment Architecture

Initial development may use a modular monolith with separately executable background workers. This reduces operational complexity while preserving module boundaries.

Proposed deployment units:

- `frontend`: React web application.
- `api`: FastAPI application.
- `worker`: background scan workers.
- `scheduler`: optional recurring scan scheduler.
- `postgres`: relational database.
- `redis`: job broker and transient coordination.
- `object-storage`: optional evidence/report storage.
- `reverse-proxy`: TLS termination and routing for deployed environments.

The initial local development environment may run these services through Docker Compose.

A distributed microservices deployment is not required for the first POC. Components should have clear interfaces so they can be separated later if scale, isolation or deployment requirements justify it.

---

# 4. Technology Stack Requirements

The following stack is a proposed baseline. Final selections require review for maintainability, licensing, security, operational fit and team capability.

| Layer | Proposed technology | Rationale |
|---|---|---|
| Frontend | React + TypeScript | Component-based dashboard and type safety |
| UI styling | Tailwind CSS | Consistent UI implementation |
| Backend API | Python + FastAPI | Typed API contracts and rapid integration |
| Data validation | Pydantic | Request and observation schema validation |
| Database | PostgreSQL | Relational integrity and queryable inventory |
| ORM / migrations | SQLAlchemy + Alembic | Data access and schema migration |
| Background jobs | Celery | Asynchronous collector execution |
| Broker | Redis | Job dispatch and transient coordination |
| TLS inspection | Python `ssl`, OpenSSL tooling | Protocol and endpoint observations |
| Certificate parsing | `cryptography` | X.509 parsing and key metadata |
| Source scanning | Language-aware parsers and custom rules | Source-level cryptographic indicators |
| Containers | Docker / Docker Compose | Reproducible development and packaging |
| Testing | Pytest, frontend test tooling | Automated validation |
| API contract | OpenAPI | Documented integration contract |
| CI | GitHub Actions | Automated quality gates |
| Reporting | HTML templates and PDF generation | Human-readable assessment output |

### 4.1 Technology Selection Constraints

- Pin dependency versions.
- Record licences and transitive dependencies.
- Track security advisories.
- Avoid unmaintained cryptographic libraries.
- Do not claim algorithm validation or product certification merely because a library implements a standard.
- Record exact tool versions in scan metadata where relevant.

### 4.2 Proposed Repository Structure

```text
quantum-flow-pqc-discovery/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   ├── services/
│   │   └── types/
│   └── tests/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   ├── core/
│   │   ├── auth/
│   │   ├── assessments/
│   │   ├── scan_orchestration/
│   │   ├── collectors/
│   │   │   ├── network_tls/
│   │   │   ├── certificates/
│   │   │   ├── source_code/
│   │   │   ├── dependencies/
│   │   │   ├── configurations/
│   │   │   └── imports/
│   │   ├── normalisation/
│   │   ├── crypto_identification/
│   │   ├── inventory/
│   │   ├── cbom/
│   │   ├── risk_engine/
│   │   ├── recommendations/
│   │   ├── reporting/
│   │   ├── audit/
│   │   ├── database/
│   │   └── workers/
│   └── tests/
│       ├── unit/
│       ├── integration/
│       ├── fixtures/
│       └── ground_truth/
│
├── docs/
├── infrastructure/
│   ├── docker/
│   └── deployment/
├── scripts/
├── .github/
│   └── workflows/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
└── LICENSE
```

This is a proposed logical structure. It may be adjusted after the architecture and implementation plan are approved.

---

# 5. Discovery Source Technical Requirements

## 5.1 Network and TLS Collector

### Purpose
Observe cryptographic information exposed by an approved network endpoint.

### Inputs
- Assessment ID.
- Approved hostname or IP.
- Approved port or port list.
- Connection timeout.
- TLS inspection policy.
- Optional SNI hostname.
- Scan correlation ID.

### Collection requirements
The collector should capture, where supported and observable:

- DNS resolution result.
- Resolved address.
- Target hostname and port.
- Connection result and timestamp.
- Negotiated TLS protocol version.
- Negotiated cipher suite.
- Observable key-exchange group or mechanism.
- Peer certificate chain.
- Certificate fingerprints.
- Handshake and parsing errors.
- Collector version.

### Important technical distinctions
The following are separate data points and must not be conflated:

1. Certificate subject public-key algorithm.
2. Certificate signature algorithm.
3. TLS negotiated cipher suite.
4. TLS key-exchange group or mechanism.
5. Application-level cryptographic algorithms.

A certificate containing an RSA public key does not, by itself, prove that the current TLS session used RSA key exchange. A TLS 1.3 cipher-suite name also does not encode the key-exchange group.

### Safety requirements
- Only approved targets may be scanned.
- Enforce connection timeouts and bounded concurrency.
- Do not perform unrestricted port sweeps.
- Validate hostname and SNI handling.
- Prevent DNS rebinding and address-scope bypasses.
- Re-check resolved addresses against the approved target policy before connecting.
- Block loopback, link-local, private and metadata-service ranges unless explicitly authorised for a customer-controlled internal assessment.
- Record all connection attempts and failures.

### Output
A set of network observations and certificate references using the common observation schema.

## 5.2 Certificate Intelligence Collector

### Purpose
Parse and analyse certificates obtained from network observations or authorised certificate files.

### Supported inputs
- PEM certificate.
- DER certificate.
- Certificate chain in supported PEM bundle format.
- Certificate objects returned by the TLS collector.

### Required fields
- Subject.
- Issuer.
- Subject Alternative Names.
- Serial number.
- Not-before and not-after timestamps.
- Public-key algorithm.
- Public-key size or curve parameters, where applicable.
- Certificate signature algorithm.
- Fingerprint.
- Basic constraints and relevant key usage extensions, where available.
- Chain position and issuer relationship.
- Parse and validation status.

### Validation rules
- Separate parse success from trust-chain validation.
- Separate certificate expiry from quantum exposure.
- Record unknown or unsupported algorithms rather than guessing.
- Preserve source and timestamp.
- Avoid storing private key material.

## 5.3 Source Code Discovery Collector

### Purpose
Identify cryptographic indicators in authorised source repositories.

### Initial supported languages
To be confirmed. Proposed candidates include Python, Java, JavaScript/TypeScript, C and C++.

### Discovery methods
- Language-aware parsing where practical.
- API and symbol matching.
- Import and package reference detection.
- Configuration pattern detection.
- Algorithm identifier detection.
- Dependency manifest correlation.

### Finding requirements
Each source finding should include:
- Repository identifier.
- Commit or revision identifier.
- File path.
- Line range where available.
- Language.
- Matched API, symbol or pattern.
- Classification.
- Evidence excerpt with sensitive data minimised.
- Confidence and rationale.
- Scanner/rule version.

### Limitations
A source-code match is an indicator, not proof of runtime use. Dead code, test fixtures, comments, wrappers, dynamic loading and custom implementations may affect accuracy. The system must label static findings as inferred unless runtime or configuration evidence supports a stronger conclusion.

### Security requirements
- Use least-privilege repository credentials.
- Do not log access tokens.
- Avoid executing untrusted repository code.
- Apply archive/file size limits.
- Prevent path traversal and unsafe archive extraction.
- Exclude secrets from retained evidence where possible.

## 5.4 Dependency Discovery Collector

### Purpose
Identify cryptographic libraries and related dependencies.

### Inputs
Supported package manifests and lockfiles, to be selected and documented per release.

### Required output
- Package ecosystem.
- Package name.
- Version.
- Direct or transitive relationship, where determinable.
- Manifest source.
- Cryptographic library classification.
- Advisory or support metadata, if an approved source is integrated.
- Confidence and evidence.

### Important limitation
The presence of a cryptographic library does not prove that a particular algorithm is invoked at runtime. Dependency evidence must remain distinct from observed algorithm usage.

## 5.5 Infrastructure Configuration Collector

### Purpose
Parse supported configuration exports from servers, proxies, load balancers, cloud platforms and other infrastructure.

### Requirements
- Explicitly documented supported formats.
- Safe parsing without executing configuration content.
- Version-aware parsers where necessary.
- Source file and location evidence.
- Algorithm/protocol extraction.
- Parse errors and unsupported-field reporting.
- Sensitive value redaction.

Initial formats and vendors are open decisions and must be prioritised with the CISO/product owner.

## 5.6 Customer Inventory Importer

### Purpose
Ingest customer-supplied inventories through controlled schemas.

### Requirements
- CSV and JSON support as initial candidates.
- Schema validation.
- Import preview and error report.
- Source attribution.
- Duplicate detection.
- Idempotent re-import behaviour where possible.
- Clear distinction between imported and directly observed data.

---

# 6. Common Observation and Asset Data Model

## 6.1 Observation vs Asset

The system must distinguish an **observation** from an **asset**.

- An observation is a time-bound piece of evidence collected by a particular method.
- An asset is the normalised entity that may be supported by one or more observations.

For example, repeated TLS scans may produce several observations of the same endpoint certificate over time. These observations can be linked to a stable asset identity while retaining historical evidence.

## 6.2 Common Observation Schema

Proposed fields:

| Field | Type | Description |
|---|---|---|
| observation_id | UUID | Unique observation identifier |
| assessment_id | UUID | Parent assessment |
| scan_run_id | UUID | Scan execution identifier |
| source_type | Enum | Network, certificate, source, dependency, config, import |
| target | String / JSON | Target or source reference |
| observed_at | Timestamp | Collection time |
| collector_name | String | Collector identity |
| collector_version | String | Collector version |
| method | String | Collection method |
| classification | Enum | Observed, inferred, imported, unknown |
| confidence | Enum / numeric | Confidence level and optional calibrated value |
| raw_evidence_ref | String | Protected evidence reference |
| normalised_payload | JSON | Validated structured observation |
| status | Enum | Success, partial, failed, unsupported |
| error_code | String | Stable error classification |
| error_detail | String | Sanitised diagnostic detail |

## 6.3 Cryptographic Asset Schema

Proposed logical fields:

| Field | Type | Description |
|---|---|---|
| asset_id | UUID | Stable asset identifier |
| organisation_id | UUID | Tenant / organisation |
| asset_type | Enum | Endpoint, certificate, key reference, source finding, dependency, configuration |
| canonical_identifier | String | Stable identity key |
| display_name | String | Human-readable name |
| location | JSON | Host, repository, file or infrastructure location |
| algorithm_family | String | RSA, ECC, AES, SHA-2 etc. |
| algorithm_name | String | Specific algorithm where known |
| algorithm_role | Enum | Key establishment, signature, encryption, hash, MAC, unknown |
| parameters | JSON | Key size, curve, mode or parameters |
| protocol | String | TLS or other protocol |
| first_seen_at | Timestamp | First observation |
| last_seen_at | Timestamp | Most recent observation |
| lifecycle_status | Enum | Active, stale, retired, unknown |
| evidence_status | Enum | Observed, inferred, imported, unknown |
| created_at | Timestamp | Record creation |
| updated_at | Timestamp | Last update |

## 6.4 Relationships

The inventory should support relationships such as:

- Endpoint presents certificate.
- Certificate issued by issuer.
- Application depends on library.
- Source file references algorithm.
- Service uses endpoint.
- Configuration enables protocol.
- Asset depends on vendor component.

The initial implementation may use relational link tables. A graph database is not required unless demonstrated by query or scale requirements.

## 6.5 Data Normalisation

Normalisation must:
- Map equivalent algorithm identifiers to canonical names.
- Preserve original observed identifiers.
- Preserve source-specific raw evidence references.
- Avoid discarding unknown values.
- Record normaliser version.
- Be deterministic and testable.

---

# 7. CBOM Technical Requirements

## 7.1 Purpose

The CBOM is the consolidated inventory view of cryptographic assets and their relationships.

## 7.2 Required Capabilities

- Stable asset identifiers.
- Multiple observations per asset.
- Asset relationship mapping.
- Source and evidence provenance.
- Duplicate detection.
- Historical change tracking.
- Filter and search.
- JSON export.
- CSV export where suitable.
- Report linkage.

## 7.3 Duplicate Resolution

Duplicate detection must use asset-type-specific identity rules. For example:
- Certificate: fingerprint and issuer/serial context.
- TLS endpoint: hostname, port and relevant endpoint identity.
- Source finding: repository revision, file, location and rule identity.
- Dependency: ecosystem, package and version.

The system must not merge assets solely because their algorithm names match.

---

# 8. Quantum Risk Assessment Engine

## 8.1 Engine Responsibilities

The risk engine shall:
- Consume normalised assets and supporting observations.
- Evaluate algorithm role and security assumptions.
- Apply versioned rules.
- Consider contextual risk factors when available.
- Produce deterministic findings.
- Explain each conclusion.
- Identify missing evidence.
- Store the methodology version used.

## 8.2 Threat Mapping Requirements

### Shor-related assessment
Identify public-key mechanisms whose security relies on integer factorisation or discrete logarithms, including relevant RSA, finite-field Diffie-Hellman and elliptic-curve mechanisms.

### Grover-related assessment
Evaluate symmetric and hash-based security margins with appropriate algorithm-specific interpretation. Do not apply a simplistic universal “key length divided by two” rule without accounting for the construction, security target and applicable guidance.

### PQC algorithm recognition
Recognise relevant standardised PQC algorithms, including:
- ML-KEM — FIPS 203.
- ML-DSA — FIPS 204.
- SLH-DSA — FIPS 205.

Recognition does not imply that a deployment is correctly configured, interoperable, validated or certified.

## 8.3 Risk Dimensions

Proposed dimensions:

1. Cryptographic quantum exposure.
2. Algorithm role and usage.
3. Key parameters and security level.
4. Data confidentiality lifetime.
5. Asset exposure and accessibility.
6. Business criticality.
7. Dependency and migration complexity.
8. Vendor and platform support.
9. Evidence quality and confidence.

## 8.4 Scoring Requirements

The product PRD proposes a score from 0 to 1000. The exact formula and category thresholds are not yet approved.

Before implementation, the risk methodology must define:
- Score direction and meaning.
- Factor definitions.
- Weighting or rule precedence.
- Missing-data treatment.
- Confidence treatment.
- Asset-level versus organisation-level aggregation.
- Category thresholds.
- Rule versioning.
- Test cases and expected outcomes.
- Explanation format.

The score must not imply an official NIST or government rating unless a specific authority publishes and approves that methodology.

## 8.5 Risk Finding Schema

Each finding should contain:
- finding_id.
- asset_id.
- rule_id.
- rule_version.
- title.
- description.
- severity/category.
- score contribution, if applicable.
- evidence references.
- confidence.
- affected algorithm and role.
- quantum threat rationale.
- assumptions and limitations.
- recommended action.
- created_at.

## 8.6 Explainability

A user must be able to answer:
- What was found?
- Where was it found?
- Which evidence supports it?
- Was it directly observed or inferred?
- Why does it matter for quantum security?
- What information is missing?
- What should be done next?

---

# 9. Recommendation Engine

## 9.1 Responsibilities

The recommendation engine maps risk findings to guidance and next steps.

## 9.2 Recommendation Categories

- Investigate further.
- Upgrade software or library.
- Update cryptographic configuration.
- Engage vendor.
- Review certificate and PKI dependencies.
- Evaluate supported PQC capability.
- Plan hybrid migration where supported.
- Retest and verify.
- Record accepted risk or exception.

## 9.3 Recommendation Requirements

Each recommendation must include:
- Linked finding.
- Action description.
- Rationale.
- Priority.
- Prerequisites.
- Dependencies.
- Validation steps.
- Source or standards reference where applicable.
- Applicability limitations.

Recommendations must not assume that every TLS stack, certificate authority, client or vendor currently supports every PQC option.

---

# 10. API Requirements

## 10.1 API Principles

- REST-style versioned API.
- JSON request and response bodies.
- OpenAPI documentation.
- Authentication and authorisation on protected endpoints.
- Consistent error envelope.
- Request validation.
- Pagination for list endpoints.
- Correlation IDs.
- Idempotency for suitable job-creation operations.
- No secrets in URLs or logs.

## 10.2 Proposed Endpoint Catalogue

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/assessments` | Create assessment |
| GET | `/api/v1/assessments` | List assessments |
| GET | `/api/v1/assessments/{id}` | Assessment details |
| POST | `/api/v1/assessments/{id}/scopes` | Add approved scope |
| POST | `/api/v1/assessments/{id}/scans` | Start scan |
| GET | `/api/v1/scans/{id}` | Scan status |
| POST | `/api/v1/scans/{id}/cancel` | Cancel scan |
| GET | `/api/v1/scans/{id}/observations` | List observations |
| GET | `/api/v1/assets` | Search CBOM assets |
| GET | `/api/v1/assets/{id}` | Asset details |
| GET | `/api/v1/findings` | List risk findings |
| GET | `/api/v1/findings/{id}` | Finding details |
| GET | `/api/v1/reports/{id}` | Report metadata |
| POST | `/api/v1/imports` | Submit inventory import |

These are proposed routes and must be refined during API design.

## 10.3 Scan Request Example

```json
{
  "assessment_id": "UUID",
  "collector_types": ["network_tls", "certificate"],
  "targets": [
    {
      "hostname": "example.com",
      "ports": [443]
    }
  ],
  "policy_id": "approved-policy-id"
}
```

The server must validate the assessment, user permissions, target authorisation and policy before creating a job.

## 10.4 Scan Status Example

```json
{
  "scan_id": "UUID",
  "status": "running",
  "collectors": [
    {
      "name": "network_tls",
      "status": "completed"
    },
    {
      "name": "certificate",
      "status": "running"
    }
  ],
  "created_at": "ISO-8601 timestamp",
  "updated_at": "ISO-8601 timestamp"
}
```

## 10.5 Error Contract

Proposed common error shape:

```json
{
  "error": {
    "code": "TARGET_NOT_IN_SCOPE",
    "message": "The requested target is not included in the approved assessment scope.",
    "correlation_id": "UUID"
  }
}
```

Do not expose stack traces, credentials, internal network details or sensitive file contents in client-facing errors.

---

# 11. Database and Persistence Requirements

## 11.1 Proposed Database

PostgreSQL is the proposed primary relational database.

## 11.2 Logical Entities

- organisations
- users
- roles
- assessments
- assessment_scopes
- scan_runs
- scan_jobs
- collector_runs
- observations
- cryptographic_assets
- asset_observations
- asset_relationships
- findings
- risk_rule_sets
- risk_rules
- recommendations
- reports
- audit_events
- imports

## 11.3 Persistence Rules

- Use UUIDs for primary identifiers where appropriate.
- Enforce organisation-level ownership and access checks.
- Use foreign keys for relational integrity.
- Add indexes based on measured query patterns.
- Use migrations for schema changes.
- Store timestamps in UTC.
- Retain original source identifiers.
- Avoid storing secrets or private keys.
- Separate metadata from large evidence blobs when appropriate.
- Define retention and deletion policies before customer pilots.

## 11.4 Evidence Storage

Small structured observations may be stored in PostgreSQL. Larger raw evidence and generated reports may use protected object storage if approved.

Every evidence object must have:
- Stable reference.
- Organisation and assessment association.
- Content type.
- Size.
- Hash/checksum where suitable.
- Creation timestamp.
- Access policy.
- Retention status.

---

# 12. Authentication, Authorisation and Tenant Isolation

## 12.1 Authentication

The authentication provider and method are open decisions. The architecture should support secure authentication and future enterprise identity integration.

## 12.2 Authorisation

Proposed roles:
- Organisation Admin.
- Security Analyst.
- Engineer.
- Auditor / Read-only.
- Platform Administrator.

Role definitions and permissions must be reviewed before implementation.

## 12.3 Tenant Isolation

Every organisation-owned record must be scoped to an organisation. API queries must enforce tenant boundaries server-side. Client-supplied organisation identifiers must never be trusted as the sole access-control mechanism.

Tenant isolation tests are mandatory before multi-tenant deployment.

---

# 13. Security and Privacy Requirements

## 13.1 Network Safety

The network collector must defend against:
- Server-side request forgery (SSRF).
- DNS rebinding.
- Redirect-based scope escape.
- Access to loopback and link-local addresses.
- Cloud metadata endpoint access.
- Unbounded connection attempts.
- Excessive concurrency and resource consumption.

Every redirect and resolved address must be checked against the approved policy. Internal/private address scanning is disabled by default and requires explicit customer-controlled approval.

## 13.2 Repository Safety

- Never execute scanned source code.
- Use read-only, least-privilege credentials.
- Redact tokens and secrets.
- Enforce file count, size and archive expansion limits.
- Prevent path traversal.
- Record repository revision.
- Delete temporary working copies according to retention policy.

## 13.3 Data Protection

- Minimise collected data.
- Encrypt data in transit.
- Protect stored evidence and reports.
- Restrict access by organisation and role.
- Redact secrets from logs.
- Define data retention and deletion.
- Avoid collection of customer private keys.

## 13.4 Audit

Record:
- User identity.
- Organisation.
- Action.
- Target/resource.
- Timestamp.
- Result.
- Correlation ID.
- Relevant approval or policy reference.

Audit logs should be append-oriented and access-controlled.

## 13.5 Production Changes

The scanner is read-only. It must not change production cryptographic configurations. Future migration functionality must require explicit customer approval, a controlled maintenance process, validation and rollback evidence.

---

# 14. Background Jobs and Orchestration

## 14.1 Job Lifecycle

Proposed states:

- queued
- validating
- running
- partially_completed
- completed
- failed
- cancelling
- cancelled

Collector runs should have their own independent status.

## 14.2 Orchestration Requirements

- Create a scan job only after scope and permissions pass validation.
- Dispatch collectors based on selected source types.
- Apply bounded retries to transient failures.
- Do not retry permanent validation or authorisation failures.
- Support cancellation.
- Persist job state.
- Prevent duplicate execution where idempotency is required.
- Record start/end times and execution metadata.
- Isolate collector errors.
- Provide progress information without claiming false precision.

## 14.3 Resource Controls

- Per-assessment concurrency limits.
- Per-target rate limits.
- Connection and read timeouts.
- Maximum file and archive sizes.
- Maximum repository scan duration.
- Worker resource limits.
- Queue limits and back-pressure.

Numeric limits must be established through load testing and operational review.

---

# 15. Observability and Operations

## 15.1 Logging

Use structured logs with:
- Timestamp.
- Severity.
- Service/component.
- Correlation ID.
- Scan/job ID.
- Organisation ID where safe.
- Error code.
- Sanitised diagnostic context.

Do not log access tokens, private keys, passwords or unredacted secrets.

## 15.2 Metrics

Proposed operational metrics:
- Scan jobs by status.
- Collector success/failure rate.
- Scan duration.
- Queue wait time.
- Timeout rate.
- Findings produced by source type.
- Parser failure rate.
- Worker resource utilisation.
- API latency and error rate.

Metrics must avoid exposing customer-sensitive data.

## 15.3 Health Checks

Provide:
- API liveness.
- API readiness.
- Database connectivity.
- Broker connectivity.
- Worker health.
- Storage availability where applicable.

---

# 16. Testing and Validation Requirements

## 16.1 Unit Testing

Test:
- Certificate parsing.
- Algorithm identification.
- Normalisation.
- Asset identity.
- Duplicate detection.
- Risk rules.
- Recommendation mapping.
- Schema validation.
- Scope policy validation.

## 16.2 Integration Testing

Test:
- API to database.
- API to job broker.
- Orchestrator to workers.
- Collectors to normaliser.
- Normaliser to CBOM.
- CBOM to risk engine.
- Risk engine to report generation.

## 16.3 Ground-Truth Test Lab

Create controlled test assets with known configurations, including:
- TLS endpoints with different protocol versions.
- RSA certificates with varied key sizes.
- ECC certificates using supported curves.
- Different certificate signature algorithms.
- Expired and self-signed certificates.
- Different cipher suites and key-exchange groups.
- Known source-code examples.
- Known dependency manifests.
- Supported and unsupported configuration files.

Expected results must be recorded before running the scanner. Compare observed output against this ground truth.

## 16.4 Security Testing

- SSRF and scope-bypass tests.
- DNS rebinding tests.
- Path traversal tests.
- Malformed certificate tests.
- Malicious archive tests.
- Authentication and authorisation tests.
- Tenant-isolation tests.
- Rate-limit and resource-exhaustion tests.
- Secret-redaction tests.

## 16.5 Quality Gates

A release candidate must have:
- Passing automated tests.
- Reviewed dependencies.
- Documented supported-source matrix.
- Known limitations.
- Reproducible sample assessment.
- No unresolved critical security issue.
- Reviewed risk-rule version.
- Demonstrable evidence trail.

---

# 17. Reporting Requirements

## 17.1 Executive Report

Include:
- Assessment scope.
- Assessment date.
- Overall summary.
- Key risk themes.
- Priority findings.
- Recommended next actions.
- Coverage and limitations.

## 17.2 Technical Report

Include:
- Target and source details.
- Observed cryptographic assets.
- Certificate and protocol information.
- Source/dependency findings.
- Risk rules and versions.
- Evidence and confidence.
- Recommendations.
- Errors and unsupported sources.
- Scan coverage.

## 17.3 Machine-Readable Export

Provide structured JSON export for integration and downstream migration planning. CSV may be offered for tabular inventory data.

---

# 18. Performance and Scalability

The system must support asynchronous scans and bounded concurrency.

The team must define performance targets for:
- API response latency.
- Maximum scan duration by source type.
- Concurrent scan jobs.
- Assets per assessment.
- Repository size and file count.
- Evidence storage volume.
- Report generation time.

These values are not specified in the product vision document and must be established through prototype measurements, expected customer scale and infrastructure constraints.

Do not publish unbenchmarked throughput or scale claims.

---

# 19. Deployment and Environment Requirements

## 19.1 Environments

Proposed environments:
- Local development.
- Automated test.
- Staging / demonstration.
- Production or customer-controlled deployment.

## 19.2 Configuration

- Use environment-based configuration.
- Provide `.env.example` without secrets.
- Store secrets in an approved secret manager for deployed environments.
- Separate development and production credentials.
- Pin container image versions.
- Apply database migrations explicitly.
- Restrict administrative endpoints.

## 19.3 Deployment Modes

The product vision anticipates on-premises and customer-controlled deployment, with multi-tenant SaaS only after isolation and access control are proven.

The initial deployment mode remains an open product/architecture decision. The architecture should avoid hard dependencies that prevent a future customer-controlled deployment.

---

# 20. CI/CD and Engineering Standards

## 20.1 Pull Request Checks

Proposed checks:
- Formatting.
- Linting.
- Type checking.
- Unit tests.
- Integration tests where practical.
- Build verification.
- Dependency vulnerability checks.
- Secret scanning.
- Container/image scanning where applicable.

## 20.2 Engineering Practices

- Feature branches.
- Pull request review.
- Protected main branch.
- No committed secrets.
- Reproducible development setup.
- Versioned migrations.
- API contract review.
- Dependency and licence tracking.
- Release notes.
- Documented rollback for deployments.

---

# 21. Technical Acceptance Criteria

The technical foundation and initial scanner implementation must demonstrate:

1. A validated assessment and authorised scope can be created.
2. Scan jobs are persisted and orchestrated asynchronously.
3. A TLS collector can inspect an approved endpoint.
4. Certificate parsing extracts the required X.509 fields.
5. TLS protocol, cipher suite and key-exchange observations are kept distinct.
6. Source, dependency and configuration collectors use documented input/output contracts.
7. Findings are normalised into a common observation schema.
8. Assets can be linked to multiple observations.
9. CBOM records retain evidence and provenance.
10. Risk rules are versioned, deterministic and testable.
11. Risk findings explain their evidence and limitations.
12. Recommendations link to findings.
13. Reports disclose scope, coverage and failures.
14. Scope restrictions and tenant isolation are tested.
15. Collector failures do not erase successful independent results.
16. The system can reproduce a known-ground-truth demonstration.

---

# 22. Dependencies and External Interfaces

Potential dependencies include:
- DNS resolution.
- Network connectivity to approved endpoints.
- TLS and certificate libraries.
- Source repository providers.
- Package ecosystem manifests and registries.
- Customer configuration exports.
- PostgreSQL.
- Redis or an approved job broker.
- Object storage, if selected.
- NIST standards and maintained guidance.

External service availability must not be assumed. Each integration must define authentication, permissions, rate limits, failure behaviour and data handling.

---

# 23. Open Technical Decisions

The following decisions require review before implementation is considered architecture-approved.

| ID | Decision | Proposed direction | Owner |
|---|---|---|---|
| TD-01 | Deployment model | Start locally/containerised; preserve on-prem path | Product / DevOps |
| TD-02 | Initial source languages | Prioritise Python, Java, JS/TS, C/C++ based on demand | CISO / Engineering |
| TD-03 | Network scope | Explicit hostname/port allowlist; no unrestricted sweep | CISO |
| TD-04 | Internal scanning | Disabled by default; explicit customer-controlled enablement | Security |
| TD-05 | Job system | Celery + Redis proposal | Backend |
| TD-06 | Evidence storage | PostgreSQL metadata; protected object storage for larger evidence if needed | Backend / Security |
| TD-07 | Authentication | Select provider and RBAC model | Product / Security |
| TD-08 | Tenant isolation | Enforced server-side; test before SaaS | Backend / Security |
| TD-09 | CBOM format | Define internal schema and evaluate interoperability needs | Architecture |
| TD-10 | Risk methodology | CISO-approved versioned rules and scoring | CISO |
| TD-11 | Configuration formats | Select first supported vendors/formats | Product / Security |
| TD-12 | Performance targets | Establish from benchmarks and pilot expectations | Engineering / DevOps |

---

# 24. Relationship to the Product Roadmap

The Quantum Flow product vision describes:
- First two weeks: scope, owners, threat model and architecture.
- By week four: discovery prototype for TLS endpoints, certificates and structured findings.
- By week eight: scanner MVP with coverage matrix and test results.
- By month three: inventory/CBOM and migration plan.
- By month four: controlled PQC/hybrid migration demonstration and pilot readiness targets.

This TRD supports that direction. It does not claim those milestones have already been achieved. Delivery dates and scope must be confirmed by the team.

---

# 25. References

## Internal product reference
- Quantum Flow Technologies, *PQC Discovery & Migration Platform — Product Vision & Roadmap*, October 2026, Version 1.0.

## Standards identified in the product reference
- NIST FIPS 203 — ML-KEM.
- NIST FIPS 204 — ML-DSA.
- NIST FIPS 205 — SLH-DSA.
- NIST Post-Quantum Cryptography Project.
- NIST SP 800-57 Part 1.
- Department of Science and Technology, *Implementation of Quantum Safe Ecosystem in India*.

The standards register must verify current versions, errata and applicability before implementation or customer-facing claims.

---

# 26. Approval Checklist

Before treating this TRD as approved:

- [ ] PRD scope reviewed and approved.
- [ ] Initial discovery sources prioritised.
- [ ] Architecture reviewed by CISO / technical lead.
- [ ] Deployment model selected.
- [ ] Technology stack approved.
- [ ] Common observation and asset schema reviewed.
- [ ] CBOM approach agreed.
- [ ] Risk methodology owner and approval process assigned.
- [ ] Network scanning safety policy approved.
- [ ] Repository and CI/CD approach approved.
- [ ] Security and privacy requirements reviewed.
- [ ] Performance targets and pilot assumptions agreed.

---

# 27. Final Technical Direction

The Enterprise Cryptographic Discovery & Risk Assessment Scanner shall be built as a modular, evidence-driven system.

Its technical foundation will consist of independent discovery collectors, a common observation model, cryptographic identification and normalisation, a central CBOM, a versioned quantum-risk engine and an explainable recommendation/reporting layer.

The architecture must be extensible to additional enterprise sources while preserving strict scope controls, tenant isolation, data minimisation and transparent coverage limitations.

**Technical principle: Every finding must be traceable to evidence, every assessment must be reproducible, and every limitation must be visible.**
