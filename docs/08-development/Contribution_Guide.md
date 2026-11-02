# Detailed Engineering Contribution Guide

## 1. Introduction

This guide defines the end-to-end engineering lifecycle for contributors to the **Quantum Flow Technologies PQC Discovery & Risk Assessment Platform**. It covers branch management, pull request requirements, automated quality checks, code review expectations, merge strategies, and release discipline.

For a high-level summary of contribution rules, refer to the root [CONTRIBUTING.md](../../CONTRIBUTING.md).

---

## 2. Issue Creation & Management

1. **Every Non-Trivial Change Begins with an Issue:**
   - Feature requests, bug fixes, architecture proposals, and security enhancements must reference a tracked GitHub issue.
   - Use descriptive issue titles: `[Scanner] Implement SNI validation in TLS handshake`.
2. **Issue Categorization:**
   - Label issues appropriately: `bug`, `enhancement`, `security`, `documentation`, `sprint-0`, etc.
   - Assign the issue to the relevant Sprint milestone in accordance with [`Implementation_Roadmap.md`](../09-project-management/Implementation_Roadmap.md).

---

## 3. Branching Strategy & Naming Conventions

All development occurs on short-lived branches created from the primary branch (`main`).

### 3.1 Branch Naming Format

Use standard branch prefixes followed by a forward slash and a concise, kebab-case description:

```text
<prefix>/<short-description>
```

| Prefix | Usage | Example |
|---|---|---|
| `feature/` | New product or technical capabilities | `feature/celery-worker-scaffold` |
| `fix/` | Bug fixes and defects | `fix/asn1-parser-null-byte-handling` |
| `security/` | Security-sensitive fixes, egress safety, auth | `security/ssrf-private-ip-blocklist` |
| `docs/` | Documentation additions or updates | `docs/sprint-0-setup-guide` |
| `chore/` | Tooling, CI/CD, dependency updates | `chore/update-ruff-and-mypy-configs` |

---

## 4. Development Workflow

1. **Pull Latest Changes:**
   ```powershell
   git checkout main
   git pull origin main
   ```
2. **Create a Dedicated Branch:**
   ```powershell
   git checkout -b feature/qf-005-target-validation
   ```
3. **Develop Incrementally:**
   - Commit logically atomic changes with descriptive commit messages conforming to [Coding Standards](./Coding_Standards.md#11-git-commit-message-conventions).
   - Write accompanying unit and integration tests alongside implementation code.
4. **Run Local Verification:**
   Before pushing, run linting, type checks, and tests:
   ```powershell
   ruff check .
   ruff format --check .
   mypy apps/ packages/
   pytest
   ```

---

## 5. Pull Request (PR) Requirements & Structure

### 5.1 PR Title
Format the PR title following Conventional Commits:  
`feat(scanner): add DNS rebinding filter for target endpoints (#42)`

### 5.2 PR Description Template
Ensure your PR description includes:
- **Summary:** Concise statement of what was changed and why.
- **Linked Issue:** E.g., `Closes #42` or `Addresses QF-005`.
- **Type of Change:** (Bug fix, new feature, security hardening, docs).
- **Security Impact Assessment:** Does this touch target validation, tenant isolation, credentials, or network egress?
- **Testing Performed:** List of automated tests added or manual verification steps executed.

### 5.3 PR Hygiene
- Keep PRs small and focused (recommended: under 400 lines of diff where possible).
- Do not mix refactoring with new feature additions.
- Ensure all CI checks pass without warnings or overrides.

---

## 6. Required Quality & CI Gates

Every pull request must satisfy the following automated and manual quality gates:

1. **Automated Linting & Formatting:** `ruff check` and `ruff format --check` must pass with zero violations.
2. **Static Type Checking:** `mypy` must pass with zero type errors.
3. **Automated Test Suite:** All `pytest` unit, integration, and security tests must pass.
4. **Code Coverage:** Core modules (scanner safety, CBOM correlation, risk scoring) must maintain >=80% test coverage.
5. **No Secret Leaks:** Automated secret scanning must verify no credentials, API keys, or private certificates exist in the diff.
6. **Documentation Synchronization:** If API endpoints, data models, or environment variables change, the corresponding documentation in `docs/` must be updated in the same PR.

---

## 7. Code Review & Approval Expectations

- **Required Approvals:** At least one peer review from a senior backend/frontend engineer.
- **Security-Sensitive Changes:** Any change touching:
  - Network egress, DNS resolution, or socket creation (`packages/scanner/safety/`)
  - Authentication, JWT verification, or tenant isolation (`apps/api/auth/`)
  - Threat modeling or security policies (`docs/07-security/`)  
  **MUST receive explicit sign-off from the CISO or designated Security Architect.**
- **Constructive Review Conduct:**
  - Focus feedback on correctness, security boundaries, performance, maintainability, and test coverage.
  - Authors should promptly address review comments or explain technical trade-offs constructively.

---

## 8. Merge Strategy & Branch Maintenance

- **Squash and Merge:** The default merge strategy for feature and fix branches is **Squash and Merge**. This preserves a clean, linear git history on `main` while retaining full granular commit history in the PR conversation.
- **Commit Message on Squash:** The squashed commit message must use the PR title and list key bullet points summarizing the deliverable.
- **Branch Deletion:** Feature branches must be deleted immediately after merging to prevent repository clutter.

---

## 9. Release Discipline & Versioning

- **Semantic Versioning (SemVer):** The platform adheres to `MAJOR.MINOR.PATCH` versioning (e.g., `v1.0.0-alpha`).
- **Release Milestones:** Sprints 0 through 7 produce versioned milestone tags (`v0.1.0-sprint0`, `v0.2.0-sprint1`, etc.).
- **Change Traceability:** Release tags must include release notes generated from merged pull requests, linking every user-facing change to its original issue and security review.

