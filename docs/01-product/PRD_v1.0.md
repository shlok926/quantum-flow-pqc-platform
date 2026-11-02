# QUANTUM FLOW TECHNOLOGIES
# Product Requirements Document (PRD)

**Product:** PQC Discovery & Migration Platform  
**Module:** Enterprise Cryptographic Discovery & Risk Assessment Scanner  
**Document Version:** 1.0 — Initial Draft  
**Status:** Draft — For Product and Technical Review  
**Classification:** Confidential  
**Reference:** Quantum Flow Product Vision & Roadmap — October 2026

---

# 1. Executive Summary

## 1.1 Product Overview

Quantum Flow is building an enterprise-grade Post-Quantum Cryptography (PQC) Discovery & Migration Platform designed to help organisations understand their existing cryptographic infrastructure, identify exposure to future quantum computing threats, prioritise risks and plan migration towards quantum-resistant cryptographic standards.

The first major product capability will be the **Enterprise Cryptographic Discovery & Risk Assessment Scanner**.

The scanner will discover, identify, analyse and inventory cryptographic assets across an organisation's technology environment.

It will collect cryptographic information from:

- Public-facing websites and network endpoints.
- SSL/TLS certificates and certificate chains.
- Application source code repositories.
- Software dependencies and cryptographic libraries.
- Server and infrastructure configurations.
- Cloud and security configuration exports.
- Customer-provided cryptographic inventories.

The collected information will be normalised into a central Cryptographic Bill of Materials (CBOM).

A dedicated Quantum Risk Assessment Engine will evaluate discovered cryptographic assets against quantum-related security threats and generate explainable risk assessments, prioritisation results and recommended remediation actions.

## 1.2 Product Vision

Build a standards-based enterprise platform that enables organisations to:

1. Discover where cryptography is used.
2. Understand which cryptographic assets are vulnerable to future quantum attacks.
3. Build an evidence-backed cryptographic inventory.
4. Assess and prioritise quantum-security risks.
5. Identify migration requirements.
6. Plan controlled migration towards post-quantum cryptography.
7. Verify and maintain their cryptographic security posture.

## 1.3 Core Product Principle

**Discover → Inventory → Prioritise → Plan → Migrate → Assure**

The initial scanner will concentrate on the first three stages and provide inputs to migration planning.

---

# 2. Problem Statement

## 2.1 Current Industry Problem

Modern enterprises depend on cryptographic mechanisms to protect:

- Sensitive business information.
- Customer information.
- Financial transactions.
- Authentication systems.
- Digital certificates.
- Application communications.
- APIs and infrastructure.
- Data storage and transmission.

Many existing systems rely on public-key cryptography such as RSA and elliptic-curve cryptography.

A sufficiently capable fault-tolerant quantum computer could threaten widely deployed public-key cryptographic mechanisms through Shor's algorithm.

Additionally, Grover's algorithm has implications for the security margins of symmetric cryptography and hash-based systems.

Organisations face several challenges:

1. They often lack complete visibility into where cryptography is used.
2. Cryptographic configurations are distributed across multiple systems.
3. Certificates and cryptographic dependencies are difficult to track centrally.
4. Legacy applications may use outdated cryptographic algorithms.
5. Organisations lack a unified, evidence-backed assessment of quantum exposure.
6. PQC migration requires dependency analysis, compatibility testing and coordinated planning.

## 2.2 Problem We Are Solving

Quantum Flow will provide a central platform that discovers cryptographic assets from authorised sources, creates a structured inventory and evaluates their quantum-security exposure.

The platform must answer:

- Where is cryptography being used?
- Which algorithms and protocols are present?
- Which assets depend on RSA or ECC?
- What evidence supports each finding?
- How confident are we in each observation?
- Which assets require the highest migration priority?
- What should the organisation do next?

---

# 3. Product Objectives

## 3.1 Primary Objectives

| ID | Objective |
|---|---|
| OBJ-01 | Discover cryptographic assets across supported enterprise sources. |
| OBJ-02 | Identify cryptographic algorithms, protocols and key parameters. |
| OBJ-03 | Collect and analyse SSL/TLS certificates and certificate chains. |
| OBJ-04 | Detect cryptographic usage in source code and dependencies. |
| OBJ-05 | Import and analyse supported infrastructure configurations. |
| OBJ-06 | Generate a central cryptographic asset inventory (CBOM). |
| OBJ-07 | Assess quantum-related cryptographic exposure. |
| OBJ-08 | Generate explainable risk scores and prioritised findings. |
| OBJ-09 | Recommend appropriate PQC readiness and remediation actions. |
| OBJ-10 | Maintain evidence, scan history and auditability. |

## 3.2 Secondary Objectives

- Support recurring discovery scans.
- Detect changes in cryptographic configurations.
- Identify duplicate and related cryptographic assets.
- Provide exportable reports.
- Support future migration planning and verification.
- Provide an architecture that can support on-premises and customer-controlled deployments.

## 3.3 Non-Goals for Initial Release

The initial release will not claim to:

- Break RSA or ECC using an actual quantum computer.
- Guarantee that an organisation is quantum-safe.
- Discover every cryptographic asset without access to the relevant source.
- Automatically modify production cryptographic configurations.
- Replace PKI, HSM, certificate authority or key-management platforms.
- Provide regulatory certification.
- Perform unrestricted penetration testing.
- Implement proprietary cryptographic algorithms.

---

# 4. Target Users and Stakeholders

## 4.1 Primary Users

**1. Chief Information Security Officer (CISO)**

Needs an organisation-wide understanding of cryptographic exposure, risk prioritisation and migration readiness.

**2. Security Architect**

Needs technical evidence about algorithms, protocols, certificates and infrastructure configurations.

**3. Cryptography / PQC Engineer**

Needs detailed cryptographic observations, algorithm identification and standards-aligned recommendations.

**4. DevSecOps Engineer**

Needs source-code, dependency and configuration discovery capabilities.

**5. IT / Infrastructure Administrator**

Needs visibility into server configurations, certificates and infrastructure dependencies.

**6. Compliance / Audit Team**

Needs evidence, assessment history, reports and traceable recommendations.

## 4.2 Stakeholders

- Product Owner
- Founder / CEO
- CISO
- Software Engineering Team
- Cybersecurity Team
- DevOps Team
- QA and Security Testing Team
- Customer / Design Partner

---

# 5. Product Scope

## 5.1 Enterprise Discovery Scope

The platform will support multiple discovery categories.

### A. Network and TLS Discovery

Purpose: Discover cryptographic information observable through authorised network connections.

Capabilities:

- Domain and hostname input.
- DNS resolution.
- Endpoint and port discovery within approved scope.
- TLS handshake inspection.
- TLS protocol version identification.
- Negotiated cipher-suite identification.
- Observable key-exchange identification.
- Certificate-chain collection.
- Certificate validity and expiration analysis.
- Supported endpoint discovery methods.
- Scan errors and coverage reporting.

### B. Certificate Intelligence

Purpose: Extract and analyse X.509 certificate information.

Capabilities:

- PEM and DER certificate parsing.
- Subject and Subject Alternative Name extraction.
- Issuer identification.
- Serial number extraction.
- Validity-period analysis.
- Public-key algorithm identification.
- Public-key size and parameters.
- Certificate signature algorithm identification.
- Certificate-chain relationship analysis.
- Self-signed and expired certificate detection.
- Certificate fingerprint generation.
- Certificate evidence retention.

### C. Source Code Cryptographic Discovery

Purpose: Identify cryptographic usage within authorised application repositories.

Capabilities:

- Repository scanning.
- Cryptographic API identification.
- Algorithm reference detection.
- Hard-coded cryptographic configuration indicators.
- Cryptographic library usage detection.
- Deprecated algorithm identification.
- Language-specific pattern detection.
- File-level findings.
- Source location and line references.
- Evidence and confidence classification.

Initial language support should be prioritised based on actual implementation capacity and customer requirements.

### D. Dependency and Software Library Discovery

Purpose: Identify cryptographic dependencies and their potential exposure.

Capabilities:

- Dependency manifest analysis.
- Package and library identification.
- Version extraction.
- Known cryptographic library mapping.
- Cryptographic dependency relationship mapping.
- Outdated dependency indicators.
- Software Bill of Materials (SBOM) ingestion where supported.
- Identification of libraries requiring further investigation.

### E. Infrastructure Configuration Discovery

Purpose: Identify cryptographic configurations from supported infrastructure sources.

Potential input sources:

- Web server configuration exports.
- Reverse proxy configuration.
- Load balancer exports.
- Cloud security configuration exports.
- VPN and network security configuration exports.
- Application configuration files.
- PKI and certificate inventory exports.

Initial implementation must explicitly define supported file formats and integration types.

### F. Customer Inventory Import

Purpose: Allow organisations to bring existing cryptographic asset information into the platform.

Capabilities:

- CSV import.
- JSON import.
- Validated schema-based ingestion.
- Data normalisation.
- Duplicate identification.
- Import validation reports.
- Source attribution.

---

# 6. Functional Requirements

## FR-01: Organisation and Assessment Management

The platform shall:

- Support organisation-level assessment records.
- Associate scans with an organisation and project.
- Maintain assessment metadata.
- Support defined scan scopes.
- Record scan owners and timestamps.
- Maintain assessment status.

## FR-02: Scan Scope Management

The platform shall:

- Accept approved domains, repositories and configuration sources.
- Define permitted targets and scan methods.
- Support scope validation.
- Enforce scan timeouts and resource limits.
- Record authorisation and approval metadata.
- Prevent scans outside approved scope.

## FR-03: Discovery Orchestration

The platform shall:

- Create and manage scan jobs.
- Dispatch supported discovery collectors.
- Track individual collector status.
- Handle failures without losing completed results.
- Record execution timestamps.
- Support scan cancellation.
- Support controlled retries.
- Record collector versions.

## FR-04: Cryptographic Identification

The platform shall identify, where evidence permits:

- RSA.
- ECC and ECDSA.
- ECDH and observable elliptic-curve key exchange.
- Diffie-Hellman.
- AES.
- ChaCha20.
- SHA-2 family.
- SHA-3 family.
- HMAC.
- Relevant digital-signature and key-establishment mechanisms.
- Post-quantum cryptographic algorithms.
- Unknown or unsupported cryptographic references.

The platform must distinguish between:

1. Certificate public-key algorithm.
2. Certificate signature algorithm.
3. TLS negotiated key-exchange mechanism.
4. TLS negotiated cipher suite.
5. Application-level cryptographic usage.

These are separate observations and must not be incorrectly treated as equivalent.

## FR-05: Cryptographic Asset Inventory

The platform shall maintain a common asset record containing:

- Asset ID.
- Asset type.
- Organisation.
- Source.
- Target or location.
- Algorithm or protocol.
- Key and signature details.
- Evidence.
- Confidence.
- Business context.
- Dependencies.
- Risk factors.
- Recommendations.
- Audit information.

## FR-06: Risk Assessment

The platform shall:

- Evaluate discovered cryptographic assets.
- Apply versioned and configurable assessment rules.
- Identify quantum-related exposure.
- Distinguish observed facts from inferred risks.
- Generate explainable findings.
- Assign a risk score.
- Assign a risk category.
- Record assessment methodology and version.
- Identify missing information that prevents reliable assessment.

The proposed score range is 0–1000, subject to approval of the scoring methodology and thresholds.

## FR-07: Recommendation Generation

The platform shall:

- Map findings to remediation recommendations.
- Identify relevant NIST PQC standards.
- Recommend further investigation when evidence is incomplete.
- Identify upgrade or configuration-change requirements.
- Highlight vendor-dependent remediation.
- Identify migration dependencies.
- Provide recommended priority and rationale.

## FR-08: Reporting

The platform shall generate:

- Executive summary.
- Technical assessment report.
- Cryptographic asset inventory.
- Risk findings.
- Evidence details.
- Recommendations.
- Scan coverage.
- Scan limitations.
- Assessment timestamp.
- Rule-set version.

Initial output formats: HTML, JSON and PDF.

## FR-09: Audit and History

The platform shall maintain:

- Scan execution history.
- User actions.
- Configuration changes.
- Assessment versions.
- Evidence records.
- Recommendation status.
- Approval records.
- Report generation history.

---

# 7. Quantum Risk Assessment Requirements

## 7.1 Assessment Philosophy

The risk engine must be evidence-driven, transparent and explainable.

It must not assign risk merely because an algorithm name appears in a file.

Risk assessment must consider:

- Cryptographic algorithm.
- Algorithm role.
- Key size and parameters.
- Protocol usage.
- Exposure and accessibility.
- Data confidentiality lifetime.
- Business criticality.
- Migration complexity.
- Vendor support.
- Evidence confidence.

## 7.2 Quantum Threat Mapping

**Shor's Algorithm**

Assessment focus:

- RSA key establishment and signatures.
- Elliptic-curve cryptography.
- Diffie-Hellman and elliptic-curve Diffie-Hellman.
- Other public-key mechanisms whose security relies on factoring or discrete logarithms.

**Grover's Algorithm**

Assessment focus:

- Symmetric encryption security margins.
- Search-based security assumptions.
- Hash-function security considerations.

The engine must not treat Grover's algorithm as a direct equivalent of Shor's attack on RSA or ECC.

## 7.3 Proposed Risk Factors

| Factor | Assessment |
|---|---|
| Algorithm exposure | Quantum-vulnerable or quantum-resistant properties |
| Key parameters | Algorithm-specific security parameters |
| Data lifetime | How long information needs confidentiality |
| External exposure | Public-facing or internal asset |
| Business criticality | Importance of affected service |
| Dependency complexity | Number and type of dependent components |
| Vendor readiness | Availability of supported remediation |
| Evidence confidence | Reliability of observed information |

## 7.4 Risk Score

Proposed output:

- Numerical score: 0–1000.
- Risk category.
- Finding severity.
- Supporting evidence.
- Risk explanation.
- Recommended action.

**Important:** Exact weights, formula and category thresholds are pending technical approval. The initial implementation must use a documented methodology rather than presenting an arbitrary number as an authoritative industry rating.

The scoring model must be versioned and reproducible.

## 7.5 Risk Finding Example

Example structure:

**Finding:** RSA-based public-key certificate observed.

- Asset: TLS certificate.
- Evidence: Observed X.509 certificate.
- Algorithm: RSA.
- Key size: Extracted from the certificate.
- Quantum relevance: Vulnerable to sufficiently capable quantum attacks using Shor's algorithm.
- Confidence: High for the certificate observation.
- Limitation: Does not independently prove the full application's cryptographic architecture.
- Recommendation: Assess PQC migration compatibility and certificate/PKI dependencies.

---

# 8. Cryptographic Bill of Materials (CBOM)

## 8.1 Purpose

The CBOM will serve as the central inventory of cryptographic assets discovered by all collectors.

## 8.2 Asset Categories

- TLS endpoints.
- X.509 certificates.
- Cryptographic algorithms.
- Public keys.
- Digital signatures.
- Key-exchange mechanisms.
- Application source findings.
- Dependencies.
- Infrastructure configurations.
- Key-management services.
- Imported customer assets.

## 8.3 Evidence Classification

Each record must use one of these classifications:

- **Observed:** Directly identified through a scan or inspection.
- **Inferred:** Identified through indirect evidence or code patterns.
- **Imported:** Supplied through a customer inventory or external configuration.
- **Unknown:** Insufficient information to classify.

## 8.4 Confidence Levels

Proposed levels:

- High.
- Medium.
- Low.
- Unknown.

Confidence must be based on the collection method and evidence quality, not on the risk severity.

---

# 9. Non-Functional Requirements

## NFR-01: Security

- Authentication and role-based access control.
- Secure credential management.
- Encryption of sensitive stored information.
- No collection of private keys or customer secrets.
- Secure API design.
- Input validation.
- Least-privilege access.
- Audit logging.
- Dependency and supply-chain security.

## NFR-02: Performance

- Asynchronous scan execution.
- Configurable connection and execution timeouts.
- Controlled concurrency.
- Resource limits.
- Efficient parsing and normalisation.
- Support for large assessments through background jobs.

Performance targets must be established through benchmarks rather than assumed.

## NFR-03: Reliability

- Failure isolation between collectors.
- Retry handling.
- Scan-state persistence.
- Reproducible findings.
- Error classification.
- Graceful handling of unavailable targets.

## NFR-04: Scalability

The architecture should support:

- Multiple organisations.
- Multiple assessment projects.
- Multiple scan jobs.
- Additional discovery collectors.
- Larger asset inventories.
- Future distributed collector execution.

## NFR-05: Maintainability

- Modular architecture.
- Versioned APIs.
- Versioned assessment rules.
- Automated testing.
- Structured logging.
- Code review.
- Documentation.
- Dependency version tracking.

## NFR-06: Explainability

Every risk finding must provide:

- What was detected.
- Where it was detected.
- How it was detected.
- Supporting evidence.
- Confidence.
- Why it matters.
- Recommended action.

---

# 10. Proposed System Modules

The platform will be organised into the following logical components.

1. Scan Controller
2. Network and TLS Discovery Engine
3. Certificate Intelligence Engine
4. Source Code Discovery Engine
5. Dependency Discovery Engine
6. Infrastructure Configuration Collector
7. Inventory Import Engine
8. Cryptographic Identification Engine
9. Normalisation Engine
10. CBOM and Asset Relationship Engine
11. Quantum Risk Assessment Engine
12. Recommendation Engine
13. Reporting Engine
14. Audit and Assurance Engine

Each engine must have a defined interface, independent tests and documented outputs.

---

# 11. Proposed Technology Direction

These are initial recommendations and require validation in the TRD.

| Layer | Proposed Technology |
|---|---|
| Frontend | React + TypeScript |
| UI | Tailwind CSS |
| Backend | Python + FastAPI |
| Background Jobs | Celery |
| Message Broker | Redis |
| Database | PostgreSQL |
| Certificate Parsing | Python cryptography |
| TLS Inspection | Python SSL / OpenSSL |
| Source Analysis | Language-specific parsers and scanners |
| Containerisation | Docker |
| API Documentation | OpenAPI |
| Testing | Pytest |
| CI/CD | GitHub Actions |
| Reporting | HTML / PDF generation |

The final stack must be reviewed for licensing, maintenance, security and operational suitability.

---

# 12. Security and Authorised Scanning Policy

The scanner must operate only on systems owned by the organisation or explicitly authorised for assessment.

Required safeguards:

1. Explicit target scope.
2. Authorisation metadata.
3. Allowlisted targets.
4. Scan timeouts.
5. Rate and concurrency limits.
6. Safe DNS and network handling.
7. No unrestricted network crawling.
8. No collection of private keys or secrets.
9. No unattended production changes.
10. Audit trails for scan activity.
11. Secure handling of repository credentials.
12. Data retention and deletion policies.

Production migration must require explicit customer approval, validation and rollback planning.

---

# 13. User Workflow

## Step 1: Create Assessment

The user creates an organisation assessment and defines its purpose.

## Step 2: Define Discovery Scope

The user selects supported discovery sources:

- Domain / Network.
- Source Code Repository.
- Dependencies.
- Infrastructure Configuration.
- Customer Inventory.

## Step 3: Validate Authorisation

The platform validates the target scope and required permissions.

## Step 4: Execute Discovery

The scan controller dispatches the relevant collectors.

## Step 5: Normalise Findings

Collected observations are transformed into the common asset schema.

## Step 6: Build CBOM

The inventory engine identifies assets, relationships and duplicates.

## Step 7: Assess Quantum Risk

The risk engine evaluates the available evidence.

## Step 8: Generate Recommendations

The recommendation engine maps findings to remediation actions.

## Step 9: Generate Assessment Report

The platform presents executive and technical findings, evidence and limitations.

## Step 10: Plan Future Migration

Assessment findings become inputs to the migration planning workstream.

---

# 14. Proposed Product Acceptance Criteria

The initial enterprise discovery release will be considered ready for technical demonstration when:

1. A user can create an authorised assessment.
2. Supported discovery sources can be configured.
3. TLS endpoints and certificate chains can be inspected.
4. Certificate details can be extracted correctly.
5. Supported source-code patterns can be identified.
6. Supported dependencies can be inventoried.
7. Supported infrastructure configurations can be imported.
8. Findings can be normalised into a common asset model.
9. The CBOM can be generated.
10. Quantum risk rules produce reproducible and explainable results.
11. Risk findings include evidence and confidence.
12. Recommendations are linked to specific findings.
13. Reports include scope and coverage limitations.
14. Failed collectors do not invalidate successful independent collectors.
15. Tests are validated against known-ground-truth assets.

A dashboard alone does not constitute a completed discovery scanner.

---

# 15. Development Roadmap

The following roadmap is aligned with the four-month direction in the Quantum Flow Vision & Roadmap document. Dates and milestones are targets, subject to technical review and capacity.

| Period | Target Deliverables |
|---|---|
| Days 1–10 | Scope, architecture, threat model, repository, backlog and standards register |
| Days 11–30 | TLS/certificate collector, schema, inventory and basic report |
| Days 31–45 | Source/dependency discovery, configuration imports, risk rules and exports |
| Days 46–60 | Scanner MVP, installation guide and repeatable demonstration |
| Days 61–75 | CBOM/dependency view and migration planner |
| Days 76–90 | Controlled PQC/hybrid test and rollback evidence |
| Days 91–120 | Pilot package, independent review and customer feedback |

Full enterprise discovery coverage will be delivered incrementally. Each collector must have its own coverage statement and acceptance tests.

---

# 16. Risks and Dependencies

| Risk | Proposed Mitigation |
|---|---|
| Limited visibility into private infrastructure | Support authenticated, customer-controlled collectors and configuration imports |
| Incomplete cryptographic evidence | Track confidence and unknown values |
| False-positive source findings | Use language-aware analysis and validation |
| False risk classifications | Use reviewed, versioned assessment rules |
| Inconsistent collector outputs | Enforce common schemas |
| Vendor compatibility limitations | Maintain a supported-configuration matrix |
| Sensitive data exposure | Data minimisation and secure handling |
| Scope expansion | Prioritised backlog and milestone acceptance gates |
| Performance limitations | Asynchronous execution and resource controls |

---

# 17. Standards and Reference Foundation

The product should use maintained official standards and guidance as its baseline.

Initial references:

- NIST FIPS 203 — ML-KEM.
- NIST FIPS 204 — ML-DSA.
- NIST FIPS 205 — SLH-DSA.
- NIST Post-Quantum Cryptography Project.
- NIST SP 800-57 Part 1.
- Department of Science and Technology — Quantum Safe Ecosystem in India.

The standards register must record publication versions, errata status and review dates.

Using a NIST-standardised algorithm does not automatically make a product NIST-certified.

---

# 18. Open Decisions Requiring Technical Approval

The following decisions must be resolved before implementation:

1. Exact risk-scoring formula and category thresholds.
2. Initial supported source-code languages.
3. Initial infrastructure configuration formats.
4. Network scanning scope and supported ports.
5. Authentication and tenant-isolation model.
6. On-premises versus cloud deployment priorities.
7. CBOM schema and interoperability requirements.
8. Evidence retention and data deletion policy.
9. Initial scale and performance targets.
10. Approved PQC recommendation profiles.
11. Collector execution model and job orchestration.
12. Product acceptance criteria for each discovery source.

---

# 19. Definition of Done

A feature is complete only when:

- Requirements are documented.
- Implementation is reviewed.
- Automated tests pass.
- Security implications are considered.
- Evidence and limitations are documented.
- API and schema contracts are updated.
- The feature is demonstrated.
- Known issues are recorded.

---

# 20. Final Product Direction

Quantum Flow's Enterprise Cryptographic Discovery & Risk Assessment Scanner will form the foundation of its broader PQC Discovery & Migration Platform.

Its primary differentiator will not be the invention of cryptographic algorithms. It will be the ability to discover cryptographic assets across heterogeneous enterprise environments, connect them through an evidence-backed inventory, prioritise their quantum exposure and guide organisations towards controlled, standards-aligned migration.

**Core Product Promise:**

Discover your cryptography. Understand your quantum exposure. Prioritise your risks. Prepare for a quantum-safe future.
