# Data Governance & Retention Policy

**Status:** Draft — Pending Company Review and Approval  
**Document ID:** QFT-SEC-DGOV-001  
**Version:** 1.0 — Initial Engineering Draft  
**Date:** 02 November 2026  
**Classification:** Internal Security Governance  
**Owner:** CISO / Security Architecture / Data Protection Lead  
**Approval Authority:** `[COMPANY APPROVAL REQUIRED — CISO & Legal Counsel]`  
**Related Documents:** Threat Model v1.0, Database Design v1.0, SAD v1.0

---

## 1. Purpose and Scope

This policy governs the classification, handling, storage, retention, export, and destruction of data collected and processed by the **Quantum Flow Post-Quantum Cryptography (PQC) Discovery & Risk Assessment Platform**.

As an enterprise cybersecurity product, the platform inspects customer network endpoints and builds cryptographic inventories. Maintaining rigorous data hygiene, data minimization, and strict tenant boundaries is essential to maintaining customer trust and regulatory integrity.

> [!CAUTION]
> **Core Cryptographic Principle — No Private Key Collection:**  
> **The platform NEVER collects, requests, ingests, processes, or stores customer private keys, passwords, authentication secrets, or customer application payloads.** Discovery collectors are strictly bounded to publicly inspectable TLS handshake parameters and X.509 certificate metadata. Any collector implementation attempting to acquire private keys must be immediately rejected in architecture review.

---

## 2. Data Classification Matrix

All data stored or processed by the platform is categorized into four distinct classification tiers:

| Tier | Classification Level | Description & Examples | Storage & Encryption Standard |
|---|---|---|---|
| **Tier 1** | **Customer Confidential** | Tenant identity, project names, target hostnames, written scan authorizations, legal approvers, custom network configurations. | PostgreSQL encrypted volume; Row-Level Security (RLS); strict tenant isolation. |
| **Tier 2** | **Technical Evidence & Inventory** | Raw TLS observation envelopes, X.509 certificate chains, public keys, cipher suites, protocol versions, CBOM asset graphs, and risk findings. | PostgreSQL JSONB / Object Storage; immutable evidence digests (SHA-256); AES-256-GCM at rest. |
| **Tier 3** | **Security & Audit Records** | Append-only audit logs, user login events, scan submission timestamps, actor IDs, policy transition history. | Tamper-evident, append-only PostgreSQL tables; immutable log storage. |
| **Tier 4** | **Platform Public Reference** | Public NIST PQC standards (FIPS 203/204/205), algorithm classification catalogs, OID registries, public vulnerability definitions. | Read-only static catalogs; public repository. |

---

## 3. Data Minimisation Principles

1. **Strictly Bounded Collection:** Discovery collectors must capture only the technical metadata necessary to assess cryptographic algorithms, key lengths, and certificate lifetimes (e.g., ServerHello, Certificate chain, KeyExchange parameters).
2. **Payload Exclusion:** Network collectors must never inspect or store HTTP request/response bodies, URL query strings, application cookies, or POST data.
3. **Log Sanitization:** Application logs must automatically redact Authorization headers, JWT tokens, session cookies, and database credentials.

---

## 4. Tenant Isolation & Data Ownership

- **Customer Ownership:** Customers retain complete ownership of all target definitions, authorization records, cryptographic inventories (CBOM), and risk assessment reports.
- **Server-Derived Tenant Context:** Every database query, queue message, and API endpoint must derive `tenant_id` exclusively from cryptographically validated JWT session claims—never from client-supplied request payloads.
- **Multi-Tenant Logical Separation:** All tenant-owned records in PostgreSQL must carry a mandatory `tenant_id` foreign key. Cross-tenant data leakage is treated as a Critical (P0) security defect.

---

## 5. Proposed Retention & Lifecycle Schedule `[PROVISIONAL — PENDING LEGAL REVIEW]`

The following retention periods represent proposed engineering defaults and are subject to formal legal, compliance, and customer contract approval:

| Data Category | Proposed Active Retention | Proposed Archive / Backup Retention | Deletion Mechanism |
|---|---|---|---|
| **Raw Scan Observations** | 90 days after scan completion | 365 days (encrypted archive) | Automated partition pruning |
| **CBOM Asset Inventories** | Retained while Project/Asset is active | 365 days after asset retirement | Soft-delete with historical tombstone |
| **Risk Assessments & Findings** | Retained for historical trend comparison | 3 years (audit compliance) | Archived to cold storage |
| **Audit Logs** | 1 year active searchability | 7 years (compliance archive) | Immutable append-only write-once |
| **User & Tenant Metadata** | Duration of active subscription | 30 days post-termination | Cryptographic erasure upon contract exit |

*Note: Statutory retention requirements vary across jurisdictions (e.g., India DPDP Act, EU GDPR, US federal mandates). These proposed schedules must be reviewed by legal counsel before customer contracting.*

---

## 6. Data Deletion & "Right to be Forgotten"

1. **Target Removal:** When an authorized target is deleted by a customer, its target records are marked as decommissioned. Historical scan evidence remains archived for audit compliance unless tenant-wide purge is requested.
2. **Tenant Offboarding & Purge:** Upon verified termination of a customer agreement:
   - All tenant-scoped records across PostgreSQL (`projects`, `targets`, `scan_jobs`, `crypto_assets`, `findings`) are permanently deleted via cascading tenant removal.
   - Associated Redis cached objects are evicted immediately.
   - Backup snapshots age out and are overwritten in accordance with the 30-day backup rotation schedule.

---

## 7. Data Export & Portability

Customers have the right to export their complete cryptographic inventory and risk data at any time without vendor lock-in:
- **CBOM Export Formats:** Standard CycloneDX 1.6 Cryptographic BOM (JSON) and generic normalized JSON.
- **Report Formats:** Summary PDF reports and detailed CSV asset exports.
- **API Access:** Programmatic export via authenticated REST endpoints (`GET /api/v1/cbom/export`).

---

## 8. Cryptographic Controls for Data at Rest & in Transit

- **Data in Transit:**
  - TLS 1.3 enforced for all external ingress to FastAPI endpoints; TLS 1.2+ minimum with secure cipher suites for internal service traffic.
  - Plaintext HTTP is strictly prohibited.
- **Data at Rest:**
  - All database volumes, worker temporary directories, and backup archives must be encrypted with AES-256-GCM.
  - Encryption keys must be rotated annually and managed independently of application compute nodes.

---

## 9. Access Control & Operational Governance

- **Least Privilege Access:** Access to production customer data is restricted to authorized operations personnel via temporary, audited break-glass credentials.
- **Role-Based Access Control (RBAC):** Platform access within each tenant is governed by granular RBAC roles (`TenantAdmin`, `SecurityLead`, `SecurityAnalyst`, `Auditor`).
- **Audit Trails:** Every access, scan initiation, export, and deletion action generates a tamper-evident audit log record.

