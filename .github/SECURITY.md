# Security Policy

## Supported Versions

The following table details which release lines of Quantum Flow PQC Platform currently receive security updates and vulnerability patches:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

We prioritize platform security and cryptographic integrity. If you believe you have discovered a security vulnerability in Quantum Flow PQC Platform, please follow these steps:

1. **Private Vulnerability Reporting**: Use GitHub's built-in [Private Vulnerability Reporting](https://github.com/shlok926/quantum-flow-pqc-platform/security/advisories/new) feature directly in the Security tab of this repository.
2. **Do Not Open Public Issues**: To protect production deployments and ongoing cryptographic migrations, please do not file public GitHub issues or public pull requests for undisclosed vulnerabilities.
3. **Information to Include**:
   - Description of the vulnerability and its potential impact.
   - Minimal reproduction steps, proof-of-concept script, or sample payload.
   - Affected components (API endpoints, CBOM parser, cryptographic risk engine, worker queue, or web frontend).
   - Any proposed mitigations or remediation steps.

## Response SLA

- **Initial Triage**: Within 24-48 hours.
- **Vulnerability Assessment & Fix**: Dependent on severity, critical cryptographic/secrets issues are prioritized for emergency patch release.
- **Public Disclosure**: Coordinated disclosure once an update or mitigation is published.

