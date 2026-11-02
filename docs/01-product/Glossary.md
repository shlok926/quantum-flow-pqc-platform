# Quantum Flow Platform — Comprehensive Product & Cryptographic Glossary

**Status:** Draft — Pending Company Review and Approval  
**Document ID:** QFT-PROD-GLOSS-001  
**Version:** 1.0 — Initial Engineering Draft  
**Date:** 02 November 2026  
**Classification:** Internal Product & Engineering Reference  
**Owner:** Product Architecture / Technical Documentation Lead  
**Approval Authority:** `[COMPANY APPROVAL REQUIRED — Product Owner & CISO]`  
**Primary References:** Company Vision & Roadmap (Appendix B), PRD v1.0, TRD v1.0, SAD v1.0, NIST FIPS 203/204/205

---

## 1. Overview & Purpose

This glossary establishes standard definitions for cryptographic concepts, post-quantum cryptography (PQC) standards, product capabilities, data models, and architectural entities used across Quantum Flow Technologies.

Preserving consistent terminology across engineering, product management, security reviews, and customer documentation is essential to avoiding technical ambiguity.

---

## 2. Core Post-Quantum Cryptography (PQC) Concepts

### PQC (Post-Quantum Cryptography)
Cryptographic algorithms—predominantly lattice-based, hash-based, or code-based mathematics—designed to be secure against attacks by both quantum and classical computers, while running efficiently on existing classical hardware.

### CRQC (Cryptographically Relevant Quantum Computer)
A hypothetical, fault-tolerant quantum computer possessing sufficient physical and logical qubits, fidelity, and coherence time to execute Shor’s and Grover’s algorithms against real-world key sizes.

### Shor's Algorithm
A quantum polynomial-time algorithm for integer factorization and discrete logarithms. When executed on a CRQC, Shor’s algorithm fundamentally breaks classical public-key cryptography, including RSA, Diffie-Hellman (DH), and Elliptic-Curve Cryptography (ECDH/ECDSA).

### Grover's Algorithm
A quantum algorithm providing a quadratic speedup for unstructured database search. Grover's algorithm halves the effective symmetric key security margin (e.g., AES-128 is reduced to 64 bits of security, while AES-256 retains 128 bits of post-quantum security).

### Harvest Now, Decrypt Later (HNDL)
An active adversarial intelligence strategy where encrypted communication traffic is intercepted and stored today with the objective of decrypting it in the future once a CRQC becomes operational.

### Quantum Susceptibility
The degree of vulnerability an algorithm, protocol, or key length exhibits when evaluated against quantum attack vectors. Categorized as:
- **Quantum-Vulnerable:** Asymmetric schemes (RSA, ECC, DH) broken by Shor's algorithm.
- **Quantum-Resistant:** Standardized PQC schemes (ML-KEM, ML-DSA, SLH-DSA).
- **Quantum-Degraded:** Symmetric schemes where effective bit strength is halved by Grover's algorithm (e.g., AES-128, SHA-256).

### Cryptographic Agility (Crypto-Agility)
The architectural capability of an application, protocol, or infrastructure component to switch between cryptographic algorithms, key lengths, or protocol configurations through configuration updates or clean software interfaces, without requiring fundamental code rewrites or disruptive architectural redesigns.

---

## 3. NIST Post-Quantum Standards & Primitives

### ML-KEM (Module-Lattice Key-Encapsulation Mechanism — NIST FIPS 203)
The primary post-quantum standard for establishing a shared secret over an insecure channel. Based on the hard mathematical problem of Module Learning with Errors (MLWE). Parameter sets: ML-KEM-512, ML-KEM-768, ML-KEM-1024.

### ML-DSA (Module-Lattice Digital Signature Algorithm — NIST FIPS 204)
The primary post-quantum digital signature standard for general-purpose authentication and document/certificate signing. Derived from CRYSTALS-Dilithium. Parameter sets: ML-DSA-44, ML-DSA-65, ML-DSA-87.

### SLH-DSA (Stateless Hash-Based Digital Signature Algorithm — NIST FIPS 205)
A secondary post-quantum digital signature standard based entirely on cryptographic hash functions (derived from SPHINCS+). Provides security backed by well-understood symmetric hash assumptions, independent of lattice mathematics.

### KEM (Key-Encapsulation Mechanism)
A cryptographic primitive that securely establishes a shared secret between two parties without directly encrypting arbitrary user payload data.

### Hybrid Cryptography (Hybrid Deployment)
A dual-layer cryptographic implementation that combines a classical algorithm (e.g., X25519 or ECDSA) with a post-quantum algorithm (e.g., ML-KEM-768 or ML-DSA-65) in a single protocol exchange. The resulting session remains secure as long as *at least one* of the underlying schemes remains unbroken.

---

## 4. Platform Discovery & Data Model Terminology

### Cryptographic Discovery
The automated, non-destructive inspection of network endpoints, source repositories, binary artifacts, cloud configurations, or certificates to identify where and how cryptography is utilized.

### Cryptographic Bill of Materials (CBOM)
A machine-readable, structured inventory (e.g., CycloneDX 1.6 format) detailing an organization's cryptographic assets, including algorithms, key sizes, certificate chains, protocols, dependencies, locations, and evidence provenance.

### Raw Observation (Observation)
An immutable, timestamped record emitted by a discovery collector capturing raw, unparsed technical evidence from an endpoint (e.g., a raw TLS ServerHello, an ASN.1 certificate blob, or a cipher suite identifier), bound to an evidence SHA-256 hash.

### Cryptographic Asset (Asset)
A canonical, normalized logical entity representing a cryptographic component within the platform's inventory (e.g., a specific X.509 Certificate, a Public Key, a Hostname Endpoint, or an Algorithm definition).

### Relationship
A typed, directed edge connecting two cryptographic assets in the CBOM graph. Examples:
- `Endpoint --EXPOSES--> Certificate`
- `Certificate --CONTAINS--> PublicKey`
- `Certificate --SIGNED_WITH--> Algorithm`
- `Application --DEPENDS_ON--> CryptoLibrary`

### Evidence Provenance
The cryptographically verifiable chain of origin connecting a CBOM asset or finding back to its source: collector version, execution timestamp, raw socket bytes, target IP, and cryptographic digest.

### Finding
An actionable, evidence-backed evaluation result identifying a specific security risk, quantum vulnerability, configuration flaw, or policy violation associated with an asset.

### Risk Assessment
A deterministic, explainable evaluation of an asset or project's cryptographic posture, producing an objective score, vulnerability categorization, and remediation recommendations under a specific versioned ruleset (`RISK_RULESET_VERSION`).

### Migration Plan
A prioritized, dependency-aware sequence of technical remediation work packages designed to transition vulnerable cryptographic assets to quantum-safe alternatives with minimal operational disruption.

---

## 5. Evidence Status & Confidence Levels

Every cryptographic record in the platform is stamped with an explicit provenance status:

| Status | Definition |
|---|---|
| **Observed** | Directly verified through empirical network handshake, live certificate download, or active socket interaction. Highest reliability. |
| **Imported** | Extracted from third-party configuration files, cloud exports, load balancer dumps, or customer-supplied inventory files. |
| **Inferred** | Derived logically through heuristic analysis, dependency mapping, or default configuration assumptions (e.g., inferring a key exchange algorithm based on cipher suite name). |
| **Unknown** | Information could not be definitively observed or extracted (e.g., an unsupported TLS extension or unparseable ASN.1 structure). Treated defensively in risk scoring. |

### Confidence
A numerical score ($0.0$ to $1.0$) or qualitative rating reflecting the empirical reliability and provenance of an observation or finding. Direct observations hold confidence $1.0$; inferences or partial data hold lower confidence.

### Coverage
The explicitly measured boundary of systems, ports, and layers inspected by a scan job. The platform explicitly reports what was *not* inspected (e.g., internal networks, private repositories), preventing misleading claims of total cryptographic safety.

---

## 6. Network & TLS Terminology

### TLS (Transport Layer Security)
The cryptographic protocol designed to provide end-to-end communications security over a computer network (standardized in RFC 5246 for TLS 1.2 and RFC 8446 for TLS 1.3).

### Certificate (X.509 Certificate)
A digital document conforming to ITU-T X.509 / RFC 5280 that binds a cryptographic public key to an identity (Subject Distinguished Name / Subject Alternative Name) via a digital signature from a Certificate Authority (CA).

### Public Key
The asymmetric cryptographic key published in a certificate used by clients to encrypt shared secrets (in RSA) or verify digital signatures (in RSA/ECDSA/ML-DSA).

### Certificate Signature Algorithm
The algorithm pair (hash function + asymmetric signature scheme) used by an issuing CA to sign an X.509 certificate (e.g., `sha256WithRSAEncryption`, `ecdsa-with-SHA384`).

### Cipher Suite
A standardized named combination of cryptographic algorithms used to establish a secure TLS connection: authentication, key exchange, bulk symmetric encryption, and message authentication code (MAC).

### Key Exchange
The cryptographic mechanism (e.g., ECDH, DHE, or ML-KEM) negotiated during the TLS handshake through which client and server agree on shared session encryption keys.

