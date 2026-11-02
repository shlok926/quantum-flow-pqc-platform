# Architecture Decision Records (ADRs)

## Overview

This directory contains the **Architecture Decision Records (ADRs)** for the Quantum Flow Post-Quantum Cryptography (PQC) Discovery & Risk Assessment Platform. 

An Architecture Decision Record captures an important architectural, structural, or governance decision made for the platform, along with its context, considered options, technical rationale, and downstream consequences.

---

## Why Use ADRs?

1. **Context Preservation:** Software architectures evolve. ADRs document *why* a particular decision was made so future engineers understand the trade-offs rather than having to reverse-engineer past intent.
2. **Review & Governance:** Architecture decisions, particularly those involving cryptography, security boundaries, tenant isolation, and worker orchestration, require review by Technical Leadership, CISO, and Security Architecture.
3. **Traceability:** ADRs connect high-level requirements in the PRD/TRD/SAD to concrete repository structures and implementation patterns.

---

## Decision Lifecycle & Statuses

Each ADR transitions through distinct lifecycle states:

- **Proposed:** The ADR has been drafted and submitted for review. It is undergoing technical and security evaluation.
- **Accepted:** The decision has been approved by the designated authorities (e.g., Technical Lead, CISO, Security Architect) and represents the binding architectural direction.
- **Rejected:** The proposed direction was evaluated and deliberately rejected in favor of another approach or because constraints were not satisfied.
- **Superseded:** A previously accepted ADR has been replaced by a newer decision (e.g., "Superseded by ADR-0005").
- **Deprecated:** The decision is no longer applicable due to architectural evolution or external constraints.

---

## When to Write an ADR

Write an ADR whenever a technical choice involves:
- Architectural patterns (e.g., Monolith vs. Microservices, Orchestration engine).
- Persistence and schema strategy (e.g., PostgreSQL JSONB vs. normalized tables, partition strategy).
- Inter-service messaging and task queues (e.g., Redis, Celery, RabbitMQ, Kafka).
- Security controls, authentication models, tenant boundary enforcement, or cryptographic library selection.
- Collector sandboxing and network egress policies.
- Breaking API versioning or protocol changes.

*Do not write ADRs for routine bug fixes, cosmetic UI modifications, or standard code refactoring.*

---

## How to Create an ADR

1. Copy [`ADR_TEMPLATE.md`](./ADR_TEMPLATE.md) to a new file named `ADR-XXXX-<short-descriptive-title>.md` where `XXXX` is a sequential 4-digit zero-padded number (e.g., `ADR-0001-modular-monolith-architecture.md`).
2. Fill in all sections thoroughly. Do not delete required template fields.
3. Submit the ADR via a pull request using the branch prefix `docs/adr-XXXX-...`.
4. Solicit reviews from the required technical stakeholders and security authorities.
5. Once accepted, update the status to `Accepted`, record the date and reviewers, and merge into the `main` branch.

---

## Index of Architecture Decisions

| ADR ID | Title | Status | Date | Primary Owner / Reviewer |
|---|---|---|---|---|
| *None* | *Initial ADRs pending formal review in Sprint 0* | — | — | — |

> **Note:** Per engineering governance, no historical architecture decisions have been unilaterally recorded as approved without documented sign-off from the technical lead and CISO. Proposed decisions from the Implementation Blueprint and SAD will be submitted as initial ADRs during Sprint 0.

