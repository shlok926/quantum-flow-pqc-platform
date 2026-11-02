# Contributing to Quantum Flow Technologies

Thank you for your interest in contributing to the **Quantum Flow Post-Quantum Cryptography (PQC) Discovery & Risk Assessment Platform**.

As an enterprise cybersecurity product handling cryptographic inventory and risk analysis, we maintain rigorous engineering, security, and documentation standards.

> For the comprehensive, end-to-end engineering lifecycle, review the [Detailed Engineering Contribution Guide](docs/08-development/Contribution_Guide.md) and [Coding Standards](docs/08-development/Coding_Standards.md).

---

## 1. Development Prerequisites

Before submitting contributions, verify your environment meets our baseline standards:
- **Python:** 3.12+
- **Node.js:** 20+ LTS (with `pnpm` or `npm`)
- **Docker & Compose:** Docker Engine 25+ / Compose v2
- **Git:** Configured with LF line endings (`git config --global core.autocrlf input`)

See the [Setup Guide](docs/08-development/Setup_Guide.md) for full onboarding instructions.

---

## 2. Branch Naming Conventions

All work must occur on descriptive, prefixed branches cut from `main`:

- `feature/<short-description>`: New platform features and capabilities (e.g., `feature/tls-cipher-parser`)
- `fix/<short-description>`: Bug fixes and defect remediation (e.g., `fix/jwt-aud-validation`)
- `security/<short-description>`: Security-sensitive hardening and SSRF patches (e.g., `security/dns-rebinding-filter`)
- `docs/<short-description>`: Documentation, ADRs, and specification updates (e.g., `docs/adr-0001-architecture`)
- `chore/<short-description>`: Tooling, dependency, and CI/CD workflow updates (e.g., `chore/bump-ruff-0.4`)

---

## 3. Git Commit Conventions

We strictly follow the **Conventional Commits** specification:

```text
<type>(<scope>): <subject in present imperative tense>

[optional body providing technical rationale]

[optional footer referencing issue, e.g., Closes #24]
```

**Common types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `security`.

---

## 4. Pull Request (PR) Workflow

1. **Issue Reference:** Every PR must address an existing tracked GitHub issue or backlog item (e.g., `Addresses QF-012`).
2. **Focused Diffs:** Keep PRs small and targeted (under 400 lines where practical).
3. **Automated Verification:** All PRs automatically trigger CI checks:
   - Ruff linting and format verification (`ruff check .` and `ruff format --check .`)
   - Static type checking with Mypy (`mypy apps/ packages/`)
   - Full Pytest test suite with code coverage validation (`pytest`)
4. **Code Reviews:** Every PR requires at least one peer approval from a technical lead or senior engineer.

---

## 5. Security-Sensitive Change Review

Any change affecting the following areas is designated **Security-Sensitive**:
- Network egress, DNS resolution, or socket connections (`packages/scanner/safety/`)
- Authentication, session validation, or tenant isolation (`apps/api/auth/`)
- Ingestion parsers (ASN.1, X.509, certificate parsing)
- Threat modeling and security controls (`docs/07-security/`)

**All security-sensitive changes require mandatory review and approval from the CISO or designated Security Architect before merge.**

---

## 6. Database Migration Rules

- Every schema modification must include a corresponding Alembic migration script.
- Both `upgrade()` and `downgrade()` must be tested and fully functional.
- Never modify existing migration scripts that have already been merged into `main`.

---

## 7. Documentation Updates

Any PR that introduces new API endpoints, modifies configuration flags, alters data models, or updates architectural decisions **must include corresponding documentation updates in `docs/` within the same pull request**.

