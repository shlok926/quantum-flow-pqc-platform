# Security Policy & Responsible Vulnerability Disclosure

## 1. Commitment to Security

Quantum Flow Technologies is dedicated to building secure, resilient enterprise software. As a Post-Quantum Cryptography (PQC) discovery and risk assessment platform, our software inspects cryptographic assets and infrastructure. We hold the security of our platform, our contributors, and our customers to the highest standard.

We welcome responsible security research and vulnerability reports from the cybersecurity community.

---

## 2. Reporting Security Vulnerabilities Privately

> [!IMPORTANT]
> **DO NOT report security vulnerabilities via public GitHub issues, discussions, or pull requests.**

If you discover a security vulnerability, flaw, or potential weakness in this repository or its design, report it privately to our security team.

### Primary Reporting Channel
Please report all vulnerabilities via email to our designated security contact:

> **Official Security Contact:**  
> `[COMPANY_CONFIRMATION_REQUIRED: security@quantumflow.example.com / security-team-contact-pending]`  
> *(Note: This email address is a placeholder pending formal corporate confirmation of the dedicated security inbox. Please check with repository administrators for the active encrypted reporting key).*

### Information to Include in Your Report
To help us triage and resolve the issue quickly, include:
- A clear, descriptive summary of the vulnerability.
- Affected components, files, endpoints, or dependencies.
- Step-by-step instructions or a minimal proof-of-concept (PoC) demonstrating the issue.
- Potential impact (e.g., SSRF, tenant data leakage, authentication bypass).
- Any proposed remediation or patches.

> [!CAUTION]
> **Data Privacy Warning:** **NEVER include real customer data, live production credentials, private cryptographic keys, or unauthorized scan outputs in your vulnerability report.** Use synthetic domain names (e.g., `example.com`) and dummy keys.

---

## 3. Coordinated Disclosure Expectations

We ask researchers to adhere to responsible disclosure principles:
1. **Confidentiality:** Do not disclose, publish, or share technical details or exploit code publicly before coordinated disclosure has been reached and a fix has been deployed.
2. **Safe Research:** Do not attempt denial-of-service (DoS) attacks, automated brute-forcing, data destruction, or accessing systems beyond what is necessary to confirm the issue.
3. **Good Faith:** We commit to acknowledging receipt of vulnerability reports within 3 business days, providing ongoing status updates during remediation, and crediting researchers upon resolution (unless anonymity is requested).

---

## 4. Scope & High-Consequence Security Areas

We are particularly interested in responsible reports concerning the following high-consequence architectural boundaries:

| Security Domain | Key Threat Scenarios & Areas of Concern |
|---|---|
| **Scanner Network Egress & SSRF** | Bypasses in IP validation that allow connections to private IPv4 ranges (RFC 1918), loopback, link-local, or cloud metadata endpoints (`169.254.169.254`). |
| **DNS Rebinding** | Time-of-check to time-of-use (TOCTOU) flaws allowing workers to resolve public hostnames to internal network destinations. |
| **Tenant Isolation** | Flaws allowing a user or service in Tenant A to access, modify, or observe targets, assets, or scan reports belonging to Tenant B. |
| **Authentication & Authorisation** | JWT token spoofing, audience/issuer confusion, privilege escalation across RBAC roles, or unauthorized scan execution. |
| **Parser & Ingestion Safety** | Memory corruption, denial of service, or arbitrary code execution through crafted X.509 certificates, ASN.1 structures, or CBOM import files. |
| **Secrets & Credential Exposure** | Accidental logging, caching, or leakage of tokens, customer environment variables, or platform secrets. |

---

## 5. Security Architecture Reference

For details on the platform's proposed defense-in-depth architecture, refer to:
- [`docs/07-security/README.md`](docs/07-security/README.md)
- [`docs/07-security/Threat_Model_Security_Architecture_v1.0.md`](docs/07-security/Threat_Model_Security_Architecture_v1.0.md)

