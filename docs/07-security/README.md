# 07 — Security Architecture & Engineering Controls

## Overview

This directory contains the security architecture, threat model, safe-scanning controls, and security engineering guidelines for the **Quantum Flow Post-Quantum Cryptography (PQC) Discovery & Risk Assessment Platform**.

As an enterprise platform that discovers cryptographic assets from external endpoints and customer-provided environments, the platform operates in a high-consequence trust environment. It must inspect untrusted external systems and user-provided inputs without introducing vulnerabilities, leaking customer information, or acting as an unauthorized network proxy.

> [!WARNING]
> **Implementation Status Notice:** The security specifications and controls documented in this directory represent **approved architectural requirements and proposed engineering designs**. They do **not** constitute evidence that all controls are already fully implemented, certified, or penetration-tested in code. Every control must be implemented in its corresponding sprint and verified via automated test suites and independent review.

---

## Canonical Threat Model & Security Specification

The core technical security document for this platform is preserved in this directory:

- [**Threat Model & Security Architecture Document v1.0**](./Threat_Model_Security_Architecture_v1.0.md)  
  *Document ID: QFT-PQC-TM-001 | Version: 1.0 — Initial Technical Draft*

All contributors and engineers working on network collectors, parsers, orchestration, and storage MUST review this document.

---

## Planned Security Documentation Areas & Control Domains

The security engineering program is divided into ten core control domains:

### 1. Threat Modeling & Attack Surface Analysis
- **Scope:** Complete STRIDE and attack-tree analysis across control plane, execution plane, and storage layers.
- **Key Boundary:** Strict isolation between the Control Plane (FastAPI, PostgreSQL, Redis) and the Execution Plane (isolated Celery workers running in sandboxed, non-root containers).
- **Core Doc:** [`Threat_Model_Security_Architecture_v1.0.md`](./Threat_Model_Security_Architecture_v1.0.md).

### 2. Scanner Safety & SSRF Prevention
- **Scope:** Server-Side Request Forgery (SSRF) defense mechanisms.
- **Requirements:**
  - Strict destination address validation before initiating any socket connection.
  - Deny-by-default egress policy blocking private IPv4 ranges (RFC 1918: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopback (`127.0.0.0/8`), link-local (`169.254.0.0/16`), cloud metadata endpoints (`169.254.169.254`), and IPv6 equivalents.
  - Restricting target network connections strictly to approved ports (default 443, 8443).
  - Explicit written authorization verification prior to scan initiation.

### 3. DNS Rebinding Protection
- **Scope:** Mitigating TOCTOU (Time-of-Check to Time-of-Use) attacks where domain names resolve to public IPs during validation but switch to private/internal IPs during connection.
- **Requirements:**
  - Two-stage DNS resolution and validation.
  - Worker-pinned IP connections: resolve hostname, validate IP against blocklist, and connect directly to the validated IP while passing the original hostname as TLS Server Name Indication (SNI).
  - Enforce bounded connection timeouts and disallow untracked HTTP redirects across network boundaries.

### 4. Authentication, Session Management & Authorisation
- **Scope:** Enterprise identity integration and role-based access control (RBAC).
- **Requirements:**
  - OIDC / OAuth 2.0 integration for enterprise Single Sign-On (SSO).
  - Cryptographically verified JWT bearer tokens with strict audience (`aud`), issuer (`iss`), and expiration (`exp`) validation.
  - Granular RBAC roles: `TenantAdmin`, `SecurityLead`, `SecurityAnalyst`, `Auditor`, `ScannerService`.
  - Service-to-service authentication between control plane and workers using short-lived tokens or mutual TLS.

### 5. Multi-Tenant Isolation
- **Scope:** Cryptographic and logical boundary enforcement between distinct customer tenants.
- **Requirements:**
  - Server-derived tenant context from authenticated JWT claims—never trust tenant IDs supplied in request payloads or query parameters.
  - Tenant-scoped database queries (`tenant_id` filtering on all CRUD operations and PostgreSQL Row-Level Security policies).
  - Strict isolation of object-storage evidence buckets and message queues per tenant or with signed tenant prefixes.

### 6. Data Protection & Cryptographic Storage
- **Scope:** Protection of customer evidence, cryptographic inventories, and assessment records at rest and in transit.
- **Requirements:**
  - TLS 1.3 enforced for all external API endpoints; TLS 1.2+ minimum with secure cipher suites for internal service traffic.
  - Encryption at rest (AES-256-GCM) for sensitive database fields, evidence artifacts, and backups.
  - Data minimisation principle: **The platform NEVER collects, requests, stores, or handles customer private keys, passwords, or unrelated secrets.**

### 7. Secrets Management
- **Scope:** Secure lifecycle management of platform credentials, API tokens, and database passwords.
- **Requirements:**
  - Zero hardcoded secrets in source code, configuration files, or container images.
  - Dynamic injection of secrets via environment variables or secret vaults (e.g., HashiCorp Vault, AWS Secrets Manager).
  - Sanitisation of logs to redact Authorization headers, tokens, and sensitive query strings.

### 8. Audit Logging & Non-Repudiation
- **Scope:** Immutable traceability for compliance, forensics, and operational integrity.
- **Requirements:**
  - Structured, machine-readable JSON audit logs recording actor identity, timestamp, tenant ID, action performed, target IP/domain, and outcome.
  - Append-only audit table architecture in PostgreSQL.
  - Cryptographic hashing (SHA-256) of raw scan observation envelopes to guarantee evidence provenance.

### 9. Dependency & Supply-Chain Security
- **Scope:** Mitigating risks from third-party open-source libraries, container bases, and build tools.
- **Requirements:**
  - Automated software composition analysis (SCA) via tools such as Dependabot, `pip-audit`, and Trivy.
  - Pinned dependency versions with hash checking (`uv.lock` / `poetry.lock` / `pnpm-lock.yaml`).
  - Minimal, hardened container base images (e.g., distroless or Alpine Linux) running as non-root users.

### 10. Vulnerability Disclosure & Incident Response
- **Scope:** Structured policy for receiving, evaluating, and addressing externally reported vulnerabilities.
- **Reference:** See root [`SECURITY.md`](../../SECURITY.md) for the responsible disclosure policy and reporting protocols.

---

## Security Documentation Roadmap

As implementation progresses through Sprints 0 through 7, dedicated engineering specifications for each domain above will be authored and linked from this index:

| Document | Topic | Target Sprint | Status |
|---|---|---|---|
| `Threat_Model_Security_Architecture_v1.0.md` | Core Threat Model & STRIDE Analysis | Sprint 0 | **Preserved / Under Review** |
| `SSRF_and_DNS_Rebinding_Specification.md` | Network Safety Controls & Socket Interceptor | Sprint 3 | Planned |
| `Tenant_Isolation_Specification.md` | PostgreSQL RLS & Context Propagation | Sprint 1 | Planned |
| `Secrets_and_Key_Management_Guide.md` | Vault Integration & Credential Hygiene | Sprint 2 | Planned |
| `Audit_Logging_Specification.md` | Immutable Logging Schema & Provenance | Sprint 4 | Planned |

