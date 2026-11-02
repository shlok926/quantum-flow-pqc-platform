# ADR-[XXXX]: [Short, Descriptive Title]

## Metadata

| Field | Value |
|---|---|
| **ADR ID** | ADR-[XXXX] (e.g., ADR-0001) |
| **Title** | [Short, descriptive decision title] |
| **Status** | Proposed \| Accepted \| Rejected \| Superseded by ADR-[YYYY] \| Deprecated |
| **Date** | YYYY-MM-DD |
| **Author(s)** | [Name(s), Role(s)] |
| **Reviewers** | [Technical Lead, Backend Lead, CISO, Security Architect] |
| **Approver(s)** | [Designated Technical Authority / CISO] |
| **Related Documents** | [Links to PRD, TRD, SAD, Database Design, API Spec, or other ADRs] |

---

## 1. Context

[Describe the context and background surrounding this decision. What technical, business, or operational circumstances make this decision necessary? Include relevant links to specifications or regulatory standards (e.g., NIST SP 800-208, FIPS 203/204/205, CNSA 2.0).]

---

## 2. Problem Statement

[State the specific problem or dilemma clearly and concisely. What question needs to be answered? What constraint needs to be balanced? What is at stake if no decision or an incorrect decision is made?]

---

## 3. Options Considered

[List all viable technical options evaluated to solve the problem.]

### Option 1: [Option Name]
- **Description:** [Brief description of the approach]
- **Pros:**
  - [Advantage 1]
  - [Advantage 2]
- **Cons:**
  - [Disadvantage 1]
  - [Disadvantage 2]

### Option 2: [Option Name]
- **Description:** [Brief description of the approach]
- **Pros:**
  - [Advantage 1]
  - [Advantage 2]
- **Cons:**
  - [Disadvantage 1]
  - [Disadvantage 2]

### Option 3: [Option Name]
- **Description:** [Brief description of the approach]
- **Pros:**
  - [Advantage 1]
  - [Advantage 2]
- **Cons:**
  - [Disadvantage 1]
  - [Disadvantage 2]

---

## 4. Decision

[State the chosen decision clearly in direct, actionable language. Example: "We will adopt a modular monolith architecture with Celery-based isolated background workers for Sprint 0 through Sprint 3..."]

---

## 5. Rationale

[Explain why this decision was chosen over the alternative options. How does this decision satisfy the requirements, technical principles, and project goals outlined in the TRD and SAD? Detail how trade-offs were weighed.]

---

## 6. Consequences

### Positive Consequences
- [Positive consequence 1, e.g., improved modularity, simplified local development]
- [Positive consequence 2]

### Negative Consequences / Trade-offs
- [Negative consequence 1, e.g., temporary overhead, operational complexity]
- [Mitigation strategy for negative consequence 1]

### Neutral Consequences / Operational Requirements
- [Operational prerequisite, monitoring requirement, or subsequent tooling need]

---

## 7. Security Impact & Threat Model Alignment

[Evaluate the decision against the platform's Threat Model and Security Architecture (Document ID: QFT-PQC-TM-001).]

- **Tenant Isolation:** [Does this decision affect multi-tenant boundary separation?]
- **Attack Surface:** [Does this increase or decrease the network/host attack surface?]
- **SSRF / Egress Risk:** [Does this introduce or mitigate unauthorized network interactions?]
- **Data Protection & Least Privilege:** [How are credentials, evidence, and customer inventories protected?]
- **Auditability:** [Are all relevant actions and state transitions logged in immutable audit trails?]

---

## 8. Alternatives Rejected

[Explicitly document why specific alternatives were not selected, ensuring historical context is preserved.]

- **[Alternative A]:** Rejected because [specific reason, e.g., unmanageable operational complexity at current scale, security boundary compromise, lack of Python 3.12 support].
- **[Alternative B]:** Rejected because [specific reason, e.g., vendor lock-in, unverified cryptographic assurance].

---

## 9. Reviewers & Sign-off

| Role | Name | Status | Sign-off Date |
|---|---|---|---|
| Technical Lead | [Name] | Pending \| Approved \| Rejected | YYYY-MM-DD |
| CISO / Security Architect | [Name] | Pending \| Approved \| Rejected | YYYY-MM-DD |
| Backend Lead | [Name] | Pending \| Approved \| Rejected | YYYY-MM-DD |

