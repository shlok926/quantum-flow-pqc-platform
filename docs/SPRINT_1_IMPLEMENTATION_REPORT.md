# Quantum Flow Technologies — Sprint 1 Implementation Report

**Product:** Quantum Flow — Enterprise Post-Quantum Cryptography (PQC) Discovery & Risk Assessment Platform  
**Sprint:** Sprint 1 — Target Management & Bounded TLS Discovery  
**Date:** 2026-11-02  
**Status:** COMPLETE & VERIFIED  
**Repository:** `quantum-flow-pqc-platform`

---

## 1. Executive Summary

Sprint 1 delivers the operational discovery foundation of the Quantum Flow platform. Following the successful deployment of the Sprint 0 engineering baseline, Sprint 1 establishes strict target boundary controls, an enterprise-grade SSRF and DNS rebinding mitigation engine, a non-destructive bounded TLS 1.2 / TLS 1.3 handshake collector, and persistent observation ingestion linked to Cryptographic Bill of Materials (CBOM) entities.

All four core functional objectives have been implemented and verified:
1. **QF-001 (High): Target Registration and Management API** — Strict RFC 1034 / RFC 1123 hostname syntax normalisation, mandatory legal authorisation attestation, DNS ownership verification challenges (`quantum-flow-verify=<token>`), state machine enforcement (`pending_verification` -> `verified` -> `disabled`), and full CRUD REST endpoints.
2. **QF-002 (Critical): SSRF and DNS Rebinding Safety Engine** — Deny-by-default egress resolution inspecting *every* resolved A/AAAA record, unmasking IPv4-mapped IPv6 representations, rejecting private (RFC 1918), loopback (RFC 1122 / ::1), link-local (RFC 3927), carrier-grade NAT (RFC 6598), ULA (fc00::/7), AWS/GCP cloud metadata (`169.254.169.254`), and benchmarking networks. Destination IP pinning ensures TCP sockets connect only to the pre-validated IP address, eliminating TOCTOU DNS rebinding attack vectors.
3. **QF-003 (High): Bounded TLS Handshake Collector** — Non-destructive TLS connection restricted strictly to TCP port 443. Connects directly to pinned IPs with strict SNI (`server_hostname`) and certificate verification. Extracts authentic observables: negotiated protocol (`TLSv1.2`, `TLSv1.3`), negotiated cipher suite, ALPN, certificate subject/issuer DNs, serial numbers, validity windows, Subject Alternative Names (SANs), public key algorithms (RSA, ECDSA), key sizes, elliptic curve parameters, and SHA-256 certificate fingerprints. Adheres strictly to the architectural rule: **no fabricated key exchange parameters** (e.g. DHE/ECDHE curve parameters not exposed by standard socket handshakes are never guessed or simulated).
4. **QF-007 (High): Observation Ingestion and Initial CBOM Schema** — Durable PostgreSQL persistence with Alembic migration `194e02e6b034` creating `targets`, `scans`, and `observations` tables. Raw observation payloads are stored as structured JSONB alongside an immutable cryptographic SHA-256 provenance hash, collector version stamping, and timestamping.

---

## 2. Architecture & Safety Design

```
+---------------------------------------------------------------------------------------------------+
|                                 DISCOVERY WORKFLOW ARCHITECTURE                                   |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  [ User / Client ]                                                                                |
|         │                                                                                         |
|         ▼                                                                                         |
|  [ Target Registration API ] ────► [ Hostname Normaliser & RFC 1123 Validator ]                    |
|         │                                    │                                                    |
|         ▼                                    ▼                                                    |
|  [ Target Entity (Pending) ] ◄── Valid lowercase ASCII FQDN (No schemes, ports, or raw IPs)       |
|         │                                                                                         |
|         ▼                                                                                         |
|  [ Verification Challenge ]  ──► Generates token `quantum-flow-verify=<uuid>`                     |
|         │                                                                                         |
|         ▼ (Target Verified)                                                                       |
|  [ Trigger Scan API ] ───────► [ SafeDestinationResolver (SSRF Guard) ]                           |
|                                              │                                                    |
|                                              ├─► Resolves all A/AAAA records via getaddrinfo      |
|                                              ├─► Unwraps IPv4-mapped IPv6 (::ffff:x.x.x.x)        |
|                                              ├─► Evaluates against RFC 1918, RFC 3927, RFC 6598,   |
|                                              │   RFC 1122, fc00::/7, fe80::/10, cloud metadata    |
|                                              ├─► Enforces ALLOW_TEST_TARGETS_ONLY scope           |
|                                              └─► Selects and PINS safe destination IP             |
|                                                              │                                    |
|                                                              ▼ (Safe Pinned IP)                   |
|                                [ BoundedTLSCollector ]                                            |
|                                              │                                                    |
|                                              ├─► Opens direct TCP socket to [Pinned IP]:443       |
|                                              ├─► Wraps socket with SSLContext (SNI=target_host)   |
|                                              ├─► Extracts raw DER certificate & connection facts  |
|                                              └─► Computes SHA-256 provenance hash                 |
|                                                              │                                    |
|                                                              ▼                                    |
|                                [ Database Persistence ]                                           |
|                                              ├─► Scans Table (Status: COMPLETED / FAILED)         |
|                                              └─► Observations Table (Immutable CBOM record)       |
+---------------------------------------------------------------------------------------------------+
```

### Safety Features Implemented:
1. **Strict Port Bounding:** Only TCP port 443 is permitted for TLS inspection. Arbitrary port scanning is impossible.
2. **IP Pinning to Defeat DNS Rebinding:** The TCP connection is established directly to `selected_ip` returned by the safety resolver, while the TLS SNI header carries the target hostname. Re-resolving hostnames during connection is prevented.
3. **Multi-Stage Resolution Inspection:** If a domain resolves to multiple IP addresses, every resolved IP must pass all safety checks. If even a single address falls into a prohibited subnet, the entire resolution is rejected.
4. **ALLOW_TEST_TARGETS_ONLY Guard:** When enabled (default in test and development), scans are strictly confined to RFC 5737 (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`) and RFC 3849 (`2001:db8::/32`) test ranges, preventing inadvertent scanning of arbitrary internet endpoints.

---

## 3. Database Schema & Migration Status

Alembic revision `194e02e6b034_create_targets_scans_and_observations_.py` was generated and executed against the PostgreSQL database.

```sql
-- Target Domains
CREATE TABLE targets (
    id UUID PRIMARY KEY,
    hostname VARCHAR(253) NOT NULL UNIQUE,
    environment VARCHAR(32) NOT NULL DEFAULT 'production',
    criticality VARCHAR(32) NOT NULL DEFAULT 'high',
    status VARCHAR(32) NOT NULL DEFAULT 'pending_verification',
    authorisation_status VARCHAR(32) NOT NULL DEFAULT 'pending',
    verification_token VARCHAR(64) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    verified_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX ix_targets_hostname ON targets (hostname);
CREATE INDEX ix_targets_status ON targets (status);

-- Scan Executions
CREATE TABLE scans (
    id UUID PRIMARY KEY,
    target_id UUID NOT NULL REFERENCES targets(id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    target_ip VARCHAR(64),
    port INTEGER NOT NULL DEFAULT 443,
    collector_version VARCHAR(32) NOT NULL,
    error_code VARCHAR(64),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX ix_scans_target_id ON scans (target_id);
CREATE INDEX ix_scans_status ON scans (status);

-- CBOM Observations
CREATE TABLE observations (
    id UUID PRIMARY KEY,
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES targets(id) ON DELETE CASCADE,
    observation_type VARCHAR(64) NOT NULL DEFAULT 'network_tls_endpoint',
    evidence_payload JSONB NOT NULL,
    evidence_sha256 VARCHAR(64) NOT NULL,
    collector_version VARCHAR(32) NOT NULL,
    observed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX ix_observations_target_id ON observations (target_id);
CREATE INDEX ix_observations_scan_id ON observations (scan_id);
CREATE INDEX ix_observations_type ON observations (observation_type);
```

---

## 4. API Specification & Endpoints Implemented

| Method | Endpoint | Description | Status Code |
|---|---|---|---|
| `POST` | `/api/v1/targets` | Register a new domain target with explicit authorisation | 201 Created |
| `GET` | `/api/v1/targets` | List registered targets with status/environment filtering & pagination | 200 OK |
| `GET` | `/api/v1/targets/{id}` | Retrieve target details by UUID | 200 OK |
| `PATCH` | `/api/v1/targets/{id}` | Update target environment, criticality, or description | 200 OK |
| `POST` | `/api/v1/targets/{id}/disable` | Disable target, revoking scan permissions | 200 OK |
| `POST` | `/api/v1/targets/{id}/verify` | Verify domain control challenge token | 200 OK |
| `POST` | `/api/v1/targets/{id}/scans` | Trigger bounded TLS discovery scan on target | 201 Created |
| `GET` | `/api/v1/targets/{id}/scans` | List historical discovery scans for a target | 200 OK |
| `GET` | `/api/v1/scans/{id}` | Retrieve individual scan execution status & errors | 200 OK |
| `GET` | `/api/v1/targets/{id}/observations` | List raw cryptographic observations ingested for target | 200 OK |
| `GET` | `/api/v1/observations/{id}` | Retrieve specific observation evidence record | 200 OK |

---

## 5. Collector Observable Evidence vs. Deferred Capabilities

### Implemented Observables (QF-003):
- **Transport Connection:** Target hostname, pinned IP, destination port (443), negotiated TLS protocol (`TLSv1.2` or `TLSv1.3`), negotiated cipher suite name, ALPN protocol (`h2`, `http/1.1`), peer certificate chain length.
- **X.509 Certificate Cryptography:** Subject Distinguished Name (DN), Issuer Distinguished Name (DN), Serial number (hexadecimal), validity start/end timestamps, boolean validity state, Subject Alternative Names (SAN DNS names), SHA-256 certificate fingerprint.
- **Key Parameters:** Asymmetric algorithm family (`RSA`, `EC`, `Ed25519`, `Ed448`), public key modulus size (bits), elliptic curve name (e.g. `secp256r1`, `secp384r1`).
- **Data Provenance:** Immutable SHA-256 digest calculated across the canonical JSON representation of the evidence payload.

### Intentionally Deferred Capabilities:
- **Ephemeral Key Exchange Parameter Reconstruction:** Standard client TLS socket interfaces do not reliably expose the ephemeral key share (e.g. `X25519` vs `secp256r1`) without non-standard SSL logging or raw packet capture. Per platform design integrity rules, **key exchange parameters are never fabricated or guessed**. Ephemeral key exchange inspection is formally scheduled for dedicated packet-level or SSLKEYLOG-based collectors in future sprints.
- **Non-TLS Discovery:** SSH, IPsec, VPN, and internal code repositories are deferred to Sprints 3+.

---

## 6. Frontend Implementation Summary

The frontend application (`apps/web`) has been expanded with a cybersecurity-grade Target Management and Discovery view:

1. **Target Registration Modal:**
   - Real-time client-side domain validation matching backend RFC 1034/1123 rules (instant visual feedback rejecting schemes, paths, raw IP literals, single-label hostnames).
   - Environment and criticality selectors.
   - Mandatory explicit authorization certification checkbox.
2. **Target Inventory Table:**
   - Filterable by lifecycle status (`pending_verification`, `verified`, `disabled`) and environment.
   - Dynamic action buttons: "Scan" (enabled exclusively for verified targets), "Verify" (launches challenge modal), "Evidence" (opens CBOM drawer), and "Disable".
3. **Verification Challenge Modal:**
   - Displays required DNS TXT host `_pqc-challenge.<domain>` and verification value `quantum-flow-verify=<token>` with one-click clipboard copy.
4. **Cryptographic TLS Evidence Inspector Drawer:**
   - Visualizes negotiated transport facts (pinned IP, TLS version, cipher suite, ALPN).
   - Visualizes certificate details (algorithm, key length, curve name, validity window, SANs).
   - Renders certificate SHA-256 fingerprint and CBOM observation evidence hash.
5. **SSRF Guard Alert Banner:**
   - Prominently displays safety interception details if a scan destination is blocked by the security resolver.

---

## 7. Quality Gates & Test Execution Summary

All quality gates have been executed and passed with 100% compliance:

| Tool / Test Suite | Scope | Target | Result | Status |
|---|---|---|---|---|
| **Pytest** | Backend | Unit, integration, security, and remediation tests | **65 / 65 passed** (0 failures, 4.18s) | PASSED |
| **Ruff Check** | Backend | Code style, import order, best practices | **All checks passed** (0 errors) | PASSED |
| **Ruff Format** | Backend | Code formatting compliance | **66 files formatted** (0 discrepancies) | PASSED |
| **Mypy** | Backend | Static type checking (strict mode) | **Success in 58 source files** | PASSED |
| **TypeScript (`tsc`)** | Frontend | Static type checking (`noEmit`) | **0 errors** | PASSED |
| **ESLint** | Frontend | Linting with 0-warning ceiling | **0 errors, 0 warnings** | PASSED |
| **Vitest** | Frontend | Component and UI integration tests | **10 / 10 passed** (3 test suites) | PASSED |
| **Vite Build** | Frontend | Production bundle compilation | **Built successfully** (dist bundle: 191 kB) | PASSED |

---

## 8. Security Audit Findings & Remediation Summary

Following an independent architectural and security audit of the Sprint 1 milestone, four specific findings were addressed, verified, and hardened:

### 1. SEC-001 (High): Enforceable DNS Resolution Timeout & Concurrency Limiting
- **Finding:** Python's standard `socket.getaddrinfo()` is a blocking resolver call subject to operating system and upstream DNS timeouts (which can exceed 30 seconds), bypassing application-level timeout bounds.
- **Remediation:** 
  - Implemented `packages/scanner/safety/resolver.py` with a dedicated, named worker pool (`ThreadPoolExecutor(thread_name_prefix="qf_dns_resolver")`).
  - Implemented strict lookup bounding with `future.result(timeout=self.dns_timeout_seconds)`. On expiration, the future is cancelled, resolution is safely rejected, and late results are discarded.
  - Implemented a concurrency limiter (`threading.Semaphore(max_resolver_threads * 2)`) to reject incoming resolutions immediately under thread exhaustion, preventing thread-pool saturation or resource starvation.
  - Added unit test coverage verifying rapid timeout enforcement and concurrency rejection.

### 2. ARCH-001 (Medium): Asynchronous Event Loop Safety & Active Scan Deduplication
- **Finding:** The discovery API executed synchronous network collector calls directly inside the async FastAPI request handler, blocking the event loop. Furthermore, concurrent active scans against the same target were not constrained.
- **Remediation:**
  - Offloaded blocking network I/O to worker threads via `await asyncio.to_thread(collector.inspect_target, target.hostname)`.
  - Added pre-scan application validation rejecting scans with HTTP 409 Conflict if an active scan (`pending` or `in_progress`) already exists for the target.
  - Enforced race condition protection at the PostgreSQL database level using partial unique index `uq_scans_active_target` (`scans (target_id) WHERE status IN ('pending', 'in_progress')`) applied in Alembic revision `3ae3e3925a46`.
  - Wrapped collector execution in full exception trapping: if an unhandled error occurs, the scan is automatically updated to `failed` with sanitized diagnostics, eliminating orphaned `in_progress` scans.

### 3. DATA-001 (Medium): Canonical Evidence Payload Cryptographic Digest (RFC 8785)
- **Finding:** The JSONB observation payload lacked an explicit, independently verifiable SHA-256 cryptographic digest calculated over a canonical serialization, risking undetectable payload mutation.
- **Remediation:**
  - Created `packages/scanner/safety/canonical.py` implementing RFC 8785 JSON canonicalization (lexicographically sorted keys, compact separators `(',', ':')`, strict UTF-8 encoding).
  - Implemented `compute_canonical_evidence_sha256(payload)` computing lowercase SHA-256 digests over the canonical byte stream.
  - Implemented `verify_evidence_integrity(payload, stored_sha256)` using constant-time string comparison (`hmac.compare_digest`) to prevent timing side channels.
  - Added `evidence_sha256` column to `observations` table schema and Alembic revision `3ae3e3925a46`, indexing the hash for integrity auditing.
  - *Integrity Note:* Storing the SHA-256 digest alongside the JSONB record in the database guarantees application-level payload consistency and detects unauthorized modifications. It is acknowledged that full tamper-proof non-repudiation against an internal database administrator requires external append-only ledgers or digital signatures (planned for later compliance milestones).

### 4. TEST-001 (Low): Explicit TLS SNI and Pinned IP Regression Assertion
- **Finding:** While TLS collector implementation passed `server_hostname` to `wrap_socket()`, unit test suites lacked an explicit assertion guaranteeing that the original target hostname is passed for SNI and hostname verification while the socket connects strictly to the pinned IP.
- **Remediation:**
  - Added `test_tls_sni_and_pinned_ip_enforcement()` in `tests/unit/test_tls_collector.py` asserting `server_hostname == "secure.example.com"`, `mock_connect.assert_called_once_with(("93.184.216.34", 443))`, `check_hostname is True`, and `verify_mode == ssl.CERT_REQUIRED`.

---

## 9. Ready State for Sprint 2

With Sprint 1 verified and complete, the platform is positioned for **Sprint 2: Quantum Vulnerability Index (QVI) & Algorithmic Risk Engine**:
- Raw observation schemas are durably stored in PostgreSQL.
- Genuine cryptographic evidence (RSA key lengths, ECDSA curves, TLS versions) is available for deterministic risk evaluation.
- The next milestone will implement the quantum risk ruleset (Shor's algorithm impact on RSA/ECC, Grover's impact on symmetric ciphers, and Mosca's Theorem timeline projections).

