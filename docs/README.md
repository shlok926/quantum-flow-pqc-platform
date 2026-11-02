# Quantum Flow Platform — Master Documentation Index

**Document ID:** QFT-DOC-INDEX-001  
**Version:** 1.0  
**Status:** Maintained Repository Index  
**Date:** 02 November 2026  
**Classification:** Internal Technical Documentation  

---

## Overview

Welcome to the centralized documentation library for the **Quantum Flow Technologies Post-Quantum Cryptography (PQC) Discovery & Risk Assessment Platform**.

This index provides a complete, structured directory of all strategic, architectural, technical, operational, and governance documents across the repository.

---

## 1. Company Vision & Strategic Roadmap

| Document Title | Relative File Path | Purpose | Current Status |
|---|---|---|---|
| **Product Vision & Roadmap (PDF)** | [`00-company-vision/PQC_Platform_Vision_and_Roadmap.pdf`](./00-company-vision/PQC_Platform_Vision_and_Roadmap.pdf) | Executive vision, strategic horizons, India DST & NQM policy alignment, and four-month roadmap by Founder & CEO. | **Approved / Baseline (v1.0)** |
| **Vision Directory Guide** | [`00-company-vision/README.md`](./00-company-vision/README.md) | Summary of executive artifact, SHA-256 verification hash, and core product principles. | Maintained Guide |

---

## 2. Product Requirements

| Document Title | Relative File Path | Purpose | Current Status |
|---|---|---|---|
| **Product Requirements Document (PRD)** | [`01-product/PRD_v1.0.md`](./01-product/PRD_v1.0.md) | Product scope, user personas, functional requirements (FR-01 to FR-09), non-functional requirements (NFR-01 to NFR-06). | Draft — Initial Review |
| **Product & Cryptographic Glossary** | [`01-product/Glossary.md`](./01-product/Glossary.md) | Standardized definitions of PQC, NIST standards, Shor's/Grover's algorithms, CBOM entities, and evidence confidence levels. | Draft — Pending Review |

---

## 3. Architecture & System Engineering

| Document Title | Relative File Path | Purpose | Current Status |
|---|---|---|---|
| **Technical Requirements Document (TRD)** | [`02-technical-architecture/TRD_v1.0.md`](./02-technical-architecture/TRD_v1.0.md) | Detailed technical specifications, component responsibilities, collector designs, limits, and engineering constraints. | Draft — Architecture Review |
| **System Architecture Document (SAD)** | [`02-technical-architecture/SAD_v1.0.md`](./02-technical-architecture/SAD_v1.0.md) | Control plane vs. execution plane topology, trust boundaries, network flows, and multi-tenant isolation model. | Draft — Architecture Review |
| **Implementation Blueprint** | [`02-technical-architecture/Implementation_Blueprint_v1.0.md`](./02-technical-architecture/Implementation_Blueprint_v1.0.md) | Monorepo layout, sprint-by-sprint delivery plan (Sprint 0–7), package boundaries, and local tooling plan. | Proposed Implementation Blueprint |
| **Architecture Decisions Guide** | [`02-technical-architecture/Architecture_Decisions/README.md`](./02-technical-architecture/Architecture_Decisions/README.md) | Governance and lifecycle process for authoring, evaluating, and adopting Architecture Decision Records (ADRs). | Maintained Guide |
| **ADR Template** | [`02-technical-architecture/Architecture_Decisions/ADR_TEMPLATE.md`](./02-technical-architecture/Architecture_Decisions/ADR_TEMPLATE.md) | Standardized markdown template for submitting technical and architectural decisions. | Standard Template |

---

## 4. Database & Persistence Design

| Document Title | Relative File Path | Purpose | Current Status |
|---|---|---|---|
| **Database Design Document (DDD)** | [`03-database/Database_Design_v1.0.md`](./03-database/Database_Design_v1.0.md) | Relational schema definitions (Tenants, Projects, Targets, ScanJobs, CryptoAssets, RawObservations, AuditLogs) and indexing. | Draft — Technical Review |

---

## 5. API Specifications

| Document Title | Relative File Path | Purpose | Current Status |
|---|---|---|---|
| **REST API Specification** | [`04-api/API_Specification_v1.0.md`](./04-api/API_Specification_v1.0.md) | Complete OpenAPI/REST endpoint contracts, request/response JSON schemas, error handling (RFC 7807), and auth headers. | Draft — Technical Review |

---

## 6. Quantum Risk Assessment Engine

| Document Title | Relative File Path | Purpose | Current Status |
|---|---|---|---|
| **Risk Assessment Methodology** | [`05-risk-engine/Quantum_Risk_Assessment_Methodology_v1.0.md`](./05-risk-engine/Quantum_Risk_Assessment_Methodology_v1.0.md) | Mathematical formulas, Shor/Grover vulnerability weighting, confidentiality lifetime scoring, and ruleset versioning. | Draft — Architecture Review |

---

## 7. CBOM & Cryptographic Asset Correlation Engine

| Document Title | Relative File Path | Purpose | Current Status |
|---|---|---|---|
| **CBOM & Correlation Engine Design** | [`06-cbom/CBOM_Asset_Correlation_Engine_v1.0.md`](./06-cbom/CBOM_Asset_Correlation_Engine_v1.0.md) | Raw observation normalization, graph relationship modeling, certificate rotation handling, and CycloneDX 1.6 export. | Draft — Architecture Review |

---

## 8. Security & Compliance

| Document Title | Relative File Path | Purpose | Current Status |
|---|---|---|---|
| **Security Architecture & Controls** | [`07-security/README.md`](./07-security/README.md) | Index of the 10 security control domains (SSRF prevention, DNS rebinding, worker sandboxing, data protection). | Maintained Guide |
| **Threat Model & Security Architecture** | [`07-security/Threat_Model_Security_Architecture_v1.0.md`](./07-security/Threat_Model_Security_Architecture_v1.0.md) | Comprehensive STRIDE threat analysis, trust boundaries, attack surface evaluation, and non-bypassable egress controls. | Draft — CISO Review |
| **Data Governance & Retention Policy** | [`07-security/Data_Governance_and_Retention.md`](./07-security/Data_Governance_and_Retention.md) | Data classification, minimization, prohibition of private key ingestion, tenant isolation, and proposed retention schedules. | Draft — Pending Approval |
| **Incident Response Plan (IRP)** | [`07-security/Incident_Response_Plan.md`](./07-security/Incident_Response_Plan.md) | Severity matrix (P0–P3), detection, containment playbooks (SSRF, tenant leak, worker compromise), and recovery procedures. | Draft — Pending Approval |

---

## 9. Development & Engineering Operations

| Document Title | Relative File Path | Purpose | Current Status |
|---|---|---|---|
| **Developer Setup Guide** | [`08-development/Setup_Guide.md`](./08-development/Setup_Guide.md) | Developer onboarding guide distinguishing working immediate commands from target architecture workflows. | Maintained Guide |
| **Coding Standards** | [`08-development/Coding_Standards.md`](./08-development/Coding_Standards.md) | Code quality, strict type hints, FastAPI, Pydantic v2, SQLAlchemy 2.0, React 18, error handling, and logging standards. | Maintained Standard |
| **Contribution Guide** | [`08-development/Contribution_Guide.md`](./08-development/Contribution_Guide.md) | Detailed pull request lifecycle, required checks, branch naming, and code review conduct. | Maintained Guide |
| **Comprehensive Testing Strategy** | [`08-development/Testing_Strategy.md`](./08-development/Testing_Strategy.md) | Test pyramid, synthetic TLS test environments, security abuse test suites (SSRF/DNS rebinding), and provisional coverage gates. | Draft — Pending Approval |
| **Deployment & Operations Runbook** | [`08-development/Deployment_Operations_Runbook.md`](./08-development/Deployment_Operations_Runbook.md) | Proposed deployment topology, container builds, health probes, monitoring, database migration procedures, and rollbacks. | Draft — Pending Approval |
| **Release Management Guide** | [`08-development/Release_Management_Guide.md`](./08-development/Release_Management_Guide.md) | Semantic versioning rules, release branching, CI release gates, database migration review, and changelog governance. | Draft — Pending Approval |

---

## 10. Project Management & Traceability

| Document Title | Relative File Path | Purpose | Current Status |
|---|---|---|---|
| **Implementation Roadmap** | [`09-project-management/Implementation_Roadmap.md`](./09-project-management/Implementation_Roadmap.md) | Sprint-by-sprint delivery sequence spanning Sprint 0 through Sprint 7 with deliverables and acceptance criteria. | Proposed Roadmap |
| **Development Backlog** | [`09-project-management/Development_Backlog.md`](./09-project-management/Development_Backlog.md) | 47 granular engineering tasks (QF-001 to QF-047) initialized to NOT STARTED. | Active Master Backlog |
| **Requirements Traceability Matrix** | [`09-project-management/Requirements_Traceability_Matrix.md`](./09-project-management/Requirements_Traceability_Matrix.md) | End-to-end matrix mapping PRD requirements (FR-01 to FR-09) to TRD, SAD, database, API, tests, and backlog tasks. | Draft — Traceability Baseline |

---

## 11. Technical Governance & Audit

| Document Title | Relative File Path | Purpose | Current Status |
|---|---|---|---|
| **Documentation Governance Guide** | [`Documentation_Governance.md`](./Documentation_Governance.md) | Document ownership, lifecycle states (`DRAFT`, `IN_REVIEW`, `APPROVED`, etc.), naming standards, and approval rules. | Draft — Pending Approval |
| **Repository Setup & Audit Report** | [`REPOSITORY_SETUP_AUDIT.md`](./REPOSITORY_SETUP_AUDIT.md) | Master audit of repository state, SHA-256 verification of preserved documents, and Sprint 0 readiness assessment. | Maintained Audit |

