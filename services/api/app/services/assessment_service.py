"""Quantum Flow Technologies — Enterprise Assessment Orchestration Service.

Coordinates end-to-end multi-collector discovery, durable job execution,
observation ingestion, CBOM correlation, quantum risk evaluation,
and immutable frozen reporting under a unified Assessment lifecycle.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.cbom.correlator import AssetCorrelator
from packages.risk.engine import QuantumRiskEngine, calculate_category
from packages.scanner.config.importer import ConfigImporter
from packages.scanner.config.models import ConfigFinding
from packages.scanner.dependencies.scanner import DependencyScanner
from packages.scanner.safety.canonical import (
    compute_canonical_evidence_sha256,
    compute_canonical_scope_hash,
)
from packages.scanner.safety.containment import (
    derive_token_lock_key,
    safe_delete_workspace,
    write_cleanup_failure_record,
)
from packages.scanner.safety.resolver import SafeDestinationResolver
from packages.scanner.source.archive import extract_archive_safely
from packages.scanner.source.scanner import SourceScanner
from packages.scanner.tls.collector import BoundedTLSCollector
from services.api.app.core.config import settings
from services.api.app.db.models.assessment import (
    Assessment,
    AssessmentStage,
    AssessmentStatus,
)
from services.api.app.db.models.assessment_asset import AssessmentAsset
from services.api.app.db.models.assessment_observation import AssessmentObservation
from services.api.app.db.models.cryptographic_asset import CryptographicAsset
from services.api.app.db.models.discovery_job import DiscoveryJob, JobStatus, JobType
from services.api.app.db.models.observation import Observation
from services.api.app.db.models.risk_assessment import RiskAssessment, ThreatType
from services.api.app.db.models.target import Target
from services.api.app.services.job_service import JobService

logger = logging.getLogger("quantumflow.assessment")

# Normalized discovery source names
VALID_DISCOVERY_SOURCES = {
    "network_tls",
    "static_source",
    "dependency_manifest",
    "config_import",
}

SOURCE_ALIASES = {
    "tls": "network_tls",
    "network_tls": "network_tls",
    "tls_discovery": "network_tls",
    "source": "static_source",
    "static_source": "static_source",
    "source_code": "static_source",
    "source_analysis": "static_source",
    "dependencies": "dependency_manifest",
    "dependency_manifest": "dependency_manifest",
    "dependency_scan": "dependency_manifest",
    "config": "config_import",
    "config_import": "config_import",
}

# Mapping between discovery sources and durable background DiscoveryJob types
SOURCE_TO_JOB_TYPE: dict[str, str] = {
    "network_tls": JobType.TLS_DISCOVERY.value,
    "static_source": JobType.SOURCE_ANALYSIS.value,
    "dependency_manifest": JobType.DEPENDENCY_SCAN.value,
    "config_import": JobType.CONFIG_IMPORT.value,
}

JOB_TYPE_TO_SOURCE: dict[str, str] = {v: k for k, v in SOURCE_TO_JOB_TYPE.items()}


class AssessmentError(Exception):
    """Base exception for assessment orchestration errors."""


class AssessmentNotFoundError(AssessmentError):
    """Raised when the specified assessment cannot be found."""


class DuplicateActiveAssessmentError(AssessmentError):
    """Raised when an active assessment already exists for the target and scope."""


class InvalidLifecycleTransitionError(AssessmentError):
    """Raised when attempting an illegal lifecycle status transition."""


class MaxRetriesExceededError(AssessmentError):
    """Raised when retrying an assessment that has exceeded its maximum retry limit."""


class TargetNotEligibleError(AssessmentError):
    """Raised when target is not eligible for active discovery."""


class AssessmentCancelledError(AssessmentError):
    """Raised when an operation is attempted on a cancelled assessment."""


def normalize_discovery_sources(sources: list[str] | None) -> list[str]:
    """Normalize and deduplicate requested discovery source names."""
    if not sources:
        return ["network_tls"]
    normalized = set()
    for s in sources:
        clean = s.strip().lower()
        norm = SOURCE_ALIASES.get(clean, clean)
        if norm in VALID_DISCOVERY_SOURCES:
            normalized.add(norm)
    return sorted(normalized) if normalized else ["network_tls"]


def compute_coverage_summary(
    requested_sources: list[str],
    collector_results: dict[str, Any],
    assessment_assets: list[Any],
    observations: list[Any],
) -> dict[str, Any]:
    """Compute multi-dimensional coverage summary across sources and classifications."""
    sources_summary: dict[str, Any] = {}
    for src in requested_sources:
        res = collector_results.get(src, {})
        sources_summary[src] = {
            "status": res.get("status", "pending"),
            "duration_ms": res.get("duration_ms", 0),
            "observations_count": sum(
                1
                for obs in observations
                if getattr(obs, "source", "") == src
                or getattr(obs, "observation_type", "").startswith(src)
            ),
            "error": res.get("error"),
        }

    classifications = {"OBSERVED": 0, "INFERRED": 0, "IMPORTED": 0, "UNKNOWN": 0}
    for a in assessment_assets:
        c = getattr(a, "classification", "OBSERVED") or "OBSERVED"
        classifications[c] = classifications.get(c, 0) + 1

    evidence_quality = {
        "high": sum(1 for obs in observations if getattr(obs, "confidence", 1.0) >= 0.9),
        "medium": sum(1 for obs in observations if 0.5 <= getattr(obs, "confidence", 1.0) < 0.9),
        "low": sum(1 for obs in observations if getattr(obs, "confidence", 1.0) < 0.5),
    }

    return {
        "sources": sources_summary,
        "classifications": classifications,
        "evidence_quality": evidence_quality,
        "total_observations": len(observations),
        "total_assets": len(assessment_assets),
    }


def compute_asset_counts(assets: list[Any]) -> dict[str, Any]:
    """Compute asset counts broken down by type and criticality."""
    by_type: dict[str, int] = {}
    by_criticality: dict[str, int] = {}
    for a in assets:
        t = getattr(a, "asset_type", "unknown")
        crit = getattr(a, "business_criticality", "medium")
        by_type[t] = by_type.get(t, 0) + 1
        by_criticality[crit] = by_criticality.get(crit, 0) + 1

    return {
        "total": len(assets),
        "by_type": by_type,
        "by_criticality": by_criticality,
    }


def compute_risk_summary(risk_evaluations: Sequence[RiskAssessment]) -> dict[str, Any]:
    """Aggregate asset-level risk evaluations into an assessment risk summary."""
    if not risk_evaluations:
        return {
            "overall_score": 0,
            "overall_category": "low",
            "shor_vulnerable_count": 0,
            "grover_margin_count": 0,
            "pqc_recognised_count": 0,
            "critical_risk_count": 0,
            "high_risk_count": 0,
            "elevated_risk_count": 0,
            "guarded_risk_count": 0,
            "low_risk_count": 0,
        }

    scores = [r.score for r in risk_evaluations if r.score is not None]
    overall_score = max(scores) if scores else 0
    overall_category = calculate_category(overall_score).value

    shor_count = sum(
        1
        for r in risk_evaluations
        if getattr(r, "quantum_threat_type", "") == ThreatType.SHOR_VULNERABLE.value
    )
    grover_count = sum(
        1
        for r in risk_evaluations
        if getattr(r, "quantum_threat_type", "") == ThreatType.GROVER_MARGIN.value
    )
    pqc_count = sum(
        1
        for r in risk_evaluations
        if getattr(r, "quantum_threat_type", "") == ThreatType.PQC_RECOGNISED.value
    )

    return {
        "overall_score": overall_score,
        "overall_category": overall_category,
        "shor_vulnerable_count": shor_count,
        "grover_margin_count": grover_count,
        "pqc_recognised_count": pqc_count,
        "critical_risk_count": sum(1 for s in scores if s >= 800),
        "high_risk_count": sum(1 for s in scores if 600 <= s < 800),
        "elevated_risk_count": sum(1 for s in scores if 400 <= s < 600),
        "guarded_risk_count": sum(1 for s in scores if 200 <= s < 400),
        "low_risk_count": sum(1 for s in scores if s < 200),
    }


def build_report_snapshot(
    assessment: Assessment,
    target_snapshot: dict[str, Any],
    coverage_summary: dict[str, Any],
    asset_counts: dict[str, Any],
    risk_summary: dict[str, Any],
    assessment_assets: list[AssessmentAsset],
    risk_evaluations: list[RiskAssessment],
    recommendations: list[Any] | None = None,
) -> dict[str, Any]:
    """Compile the immutable terminal report snapshot dictionary."""
    risk_by_asset_id: dict[uuid.UUID, RiskAssessment] = {r.asset_id: r for r in risk_evaluations}

    serialized_assets: list[dict[str, Any]] = []
    recommendations_list: list[dict[str, Any]] = []

    for aa in assessment_assets:
        r_eval = risk_by_asset_id.get(aa.asset_id)
        snap = dict(aa.asset_snapshot or {})
        snap["first_seen_in_assessment"] = aa.first_seen_in_assessment
        snap["classification"] = aa.classification
        snap["risk_score"] = r_eval.score if r_eval else None
        snap["risk_category"] = r_eval.risk_category if r_eval else "unknown"
        snap["quantum_threat_type"] = (
            r_eval.quantum_threat_type if r_eval else ThreatType.UNKNOWN.value
        )
        serialized_assets.append(snap)

    if recommendations:
        for rec in recommendations:
            recommendations_list.append(
                {
                    "priority": getattr(rec, "priority", "medium"),
                    "category": getattr(rec, "remediation_category", "algorithm_migration"),
                    "title": getattr(rec, "title", "PQC Remediation"),
                    "description": getattr(rec, "description", ""),
                }
            )

    completed_iso = assessment.completed_at.isoformat() if assessment.completed_at else None

    return {
        "assessment_id": str(assessment.id),
        "title": assessment.title,
        "status": assessment.status,
        "target_snapshot": target_snapshot,
        "started_at": (assessment.started_at.isoformat() if assessment.started_at else None),
        "completed_at": completed_iso,
        "methodology_version": assessment.methodology_version,
        "engine_version": assessment.engine_version,
        "coverage_summary": coverage_summary,
        "asset_counts": asset_counts,
        "risk_summary": risk_summary,
        "assets": serialized_assets,
        "recommendations": recommendations_list,
    }


class AssessmentService:
    """Orchestrates enterprise cryptographic discovery, durable execution, and reporting."""

    @staticmethod
    async def is_cancelled(db: AsyncSession, assessment_id: uuid.UUID) -> bool:
        """Check whether the assessment has entered CANCELLED status."""
        status = await db.scalar(select(Assessment.status).where(Assessment.id == assessment_id))
        return status == AssessmentStatus.CANCELLED.value

    @staticmethod
    async def create_assessment(
        db: AsyncSession,
        title: str,
        target_id: uuid.UUID | None = None,
        discovery_sources: list[str] | None = None,
        extra_params: dict[str, Any] | None = None,
    ) -> Assessment:
        """Create and queue a new enterprise cryptographic assessment."""
        clean_sources = normalize_discovery_sources(discovery_sources)
        target_snapshot: dict[str, Any] = {}

        if target_id is not None:
            target = await db.scalar(select(Target).where(Target.id == target_id))
            if target is None:
                raise AssessmentNotFoundError(f"Target with ID '{target_id}' was not found")

            target_snapshot = {
                "id": str(target.id),
                "hostname": target.hostname,
                "display_name": target.display_name,
                "status": target.status,
                "authorisation_status": target.authorisation_status,
            }

        scope_hash = compute_canonical_scope_hash(
            target_id=str(target_id) if target_id else None,
            discovery_sources=clean_sources,
            extra_params=extra_params,
        )

        # Check for active duplicate assessment with identical scope
        active_stmt = select(Assessment).where(
            Assessment.target_id == target_id,
            Assessment.scope_hash == scope_hash,
            Assessment.status.in_(
                [
                    AssessmentStatus.PENDING.value,
                    AssessmentStatus.QUEUED.value,
                    AssessmentStatus.RUNNING.value,
                ]
            ),
        )
        existing_active = await db.scalar(active_stmt)
        if existing_active is not None:
            raise DuplicateActiveAssessmentError(
                f"An active assessment '{existing_active.id}' is already executing for target '{target_id}' with matching scope"
            )

        assessment = Assessment(
            title=title,
            target_id=target_id,
            target_snapshot=target_snapshot,
            scope_hash=scope_hash,
            status=AssessmentStatus.PENDING.value,
            progress_stage=AssessmentStage.PENDING.value,
            progress_percent=0,
            discovery_sources=clean_sources,
            collector_results={},
            coverage_summary={},
            asset_counts={},
            risk_summary={},
            methodology_version="QFT-RISK-v1.0",
            engine_version="v1.0.0",
        )
        db.add(assessment)
        await db.commit()
        await db.refresh(assessment)
        logger.info(
            "Created assessment %s for target %s (sources=%s)",
            assessment.id,
            target_id,
            clean_sources,
        )
        return assessment

    @classmethod
    async def create_and_enqueue_assessment(
        cls,
        db: AsyncSession,
        title: str,
        target_id: uuid.UUID | None = None,
        discovery_sources: list[str] | None = None,
        input_payload: dict[str, Any] | None = None,
        extra_params: dict[str, Any] | None = None,
        engine_version: str = "v1.0.0",
        tenant_id: str | None = None,
        upload_token: str | None = None,
    ) -> tuple[Assessment, list[DiscoveryJob]]:
        """Atomically create an assessment and enqueue its durable child DiscoveryJobs in a single transaction."""
        payload = dict(input_payload or {})
        params = dict(extra_params or {})
        if tenant_id and "tenant_id" not in params:
            params["tenant_id"] = tenant_id

        # ----------------------------------------------------------------------
        # Upload Token Claiming, PostgreSQL Transaction Advisory Lock & Validation
        # ----------------------------------------------------------------------
        if upload_token:
            params["upload_token"] = upload_token
            # 1. 64-bit PostgreSQL transaction advisory lock
            lock_key = derive_token_lock_key(upload_token)
            bind = db.bind or getattr(db, "sync_session", db).bind
            dialect_name = bind.dialect.name if bind else ""
            if "postgres" in dialect_name:
                locked = await db.scalar(
                    text("SELECT pg_try_advisory_xact_lock(:lock_key)"),
                    {"lock_key": lock_key},
                )
                if not locked:
                    raise DuplicateActiveAssessmentError(
                        f"Upload token '{upload_token}' claim is currently in-flight in another transaction"
                    )

            # 2. Check canonical tenant and duplicate claim in PostgreSQL
            token_check_stmt = select(Assessment).where(
                Assessment.target_snapshot["upload_token"].as_string() == upload_token
            )
            existing_token_claims = (await db.scalars(token_check_stmt)).all()
            for claimant in existing_token_claims:
                c_tenant = claimant.target_snapshot.get("tenant_id")
                if c_tenant != tenant_id:
                    raise DuplicateActiveAssessmentError(
                        f"Cross-tenant integrity violation: token '{upload_token}' bound to different tenant '{c_tenant}'"
                    )
                raise DuplicateActiveAssessmentError(
                    f"Token '{upload_token}' has already been claimed by assessment '{claimant.id}'"
                )

            # 3. Check disk staging directory
            staging_root = Path(settings.staging_dir)
            effective_tenant = tenant_id or "default"
            token_dir = staging_root / effective_tenant / upload_token
            meta_path = token_dir / "metadata.json"

            if not meta_path.exists():
                # Cross-tenant disk inspection
                if staging_root.exists():
                    for t_dir in staging_root.iterdir():
                        if (
                            t_dir.is_dir()
                            and t_dir.name != effective_tenant
                            and (t_dir / upload_token).exists()
                        ):
                            raise DuplicateActiveAssessmentError(
                                f"Cross-tenant integrity violation: token '{upload_token}' belongs to tenant '{t_dir.name}'"
                            )
                raise AssessmentNotFoundError(
                    f"Staged upload token '{upload_token}' not found or staging metadata missing"
                )

            try:
                with open(meta_path, encoding="utf-8") as f:
                    meta_data = json.load(f)
            except Exception as exc:
                raise AssessmentNotFoundError(
                    f"Staged upload metadata corrupt or unreadable: {exc}"
                ) from exc

            if meta_data.get("tenant_id") and meta_data.get("tenant_id") != tenant_id:
                raise DuplicateActiveAssessmentError(
                    f"Cross-tenant integrity violation: metadata tenant '{meta_data.get('tenant_id')}' != '{tenant_id}'"
                )

            filename = meta_data.get("filename", "")
            staged_file_path = str(token_dir / filename)
            payload["source_archive_path"] = staged_file_path
            params["source_archive_path"] = staged_file_path

        clean_sources = normalize_discovery_sources(discovery_sources)
        target_snapshot: dict[str, Any] = {}
        target: Target | None = None

        if target_id is not None:
            target = await db.scalar(select(Target).where(Target.id == target_id))
            if target is None:
                raise AssessmentNotFoundError(f"Target with ID '{target_id}' was not found")

            # Scan eligibility enforcement for network discovery
            if "network_tls" in clean_sources and not target.is_eligible_for_scan:
                raise TargetNotEligibleError(
                    f"Target '{target.hostname}' is not eligible for active scan "
                    f"(status='{target.status}', authorisation='{target.authorisation_status}')"
                )

            target_snapshot = {
                "id": str(target.id),
                "hostname": target.hostname,
                "display_name": target.display_name,
                "status": target.status,
                "authorisation_status": target.authorisation_status,
            }
        if tenant_id:
            target_snapshot["tenant_id"] = tenant_id
        if upload_token:
            target_snapshot["upload_token"] = upload_token

        scope_hash = compute_canonical_scope_hash(
            target_id=str(target_id) if target_id else None,
            discovery_sources=clean_sources,
            extra_params=params,
        )

        # Check for active duplicate assessment with identical scope
        active_stmt = select(Assessment).where(
            Assessment.target_id == target_id,
            Assessment.scope_hash == scope_hash,
            Assessment.status.in_(
                [
                    AssessmentStatus.PENDING.value,
                    AssessmentStatus.QUEUED.value,
                    AssessmentStatus.RUNNING.value,
                ]
            ),
        )
        existing_active = await db.scalar(active_stmt)
        if existing_active is not None:
            raise DuplicateActiveAssessmentError(
                f"An active assessment '{existing_active.id}' is already executing "
                f"for target '{target_id}' with matching scope"
            )

        assessment = Assessment(
            title=title,
            target_id=target_id,
            target_snapshot=target_snapshot,
            scope_hash=scope_hash,
            status=AssessmentStatus.QUEUED.value,
            progress_stage=AssessmentStage.DISPATCHING_COLLECTORS.value,
            progress_percent=10,
            discovery_sources=clean_sources,
            collector_results={"extra_params": params},
            coverage_summary={},
            asset_counts={},
            risk_summary={},
            methodology_version="QFT-RISK-v1.0",
            engine_version=engine_version,
        )
        db.add(assessment)
        await db.flush()

        # Lazy metadata reconciliation: write assessment_id to staged metadata.json
        if upload_token:
            effective_tenant = tenant_id or "default"
            token_dir = Path(settings.staging_dir) / effective_tenant / upload_token
            meta_path = token_dir / "metadata.json"
            if meta_path.exists():
                try:
                    with open(meta_path, encoding="utf-8") as f:
                        meta_data = json.load(f)
                    meta_data["assessment_id"] = str(assessment.id)
                    tmp_m = token_dir / f"metadata.json.{uuid.uuid4().hex[:8]}.tmp"
                    with open(tmp_m, "w", encoding="utf-8") as f:
                        json.dump(meta_data, f, indent=2)
                    os.replace(tmp_m, meta_path)
                except Exception as exc:
                    logger.warning(
                        "Lazy metadata reconciliation note for token %s: %s", upload_token, exc
                    )

        # Enqueue durable discovery jobs for each requested source
        created_jobs: list[DiscoveryJob] = []
        for src in clean_sources:
            job_type = SOURCE_TO_JOB_TYPE.get(src)
            if not job_type:
                continue

            collector_params = dict(payload)
            if job_type == JobType.TLS_DISCOVERY.value and target:
                collector_params["hostname"] = target.hostname
                collector_params["port"] = 443

            job = DiscoveryJob(
                job_type=job_type,
                target_id=assessment.target_id,
                assessment_id=assessment.id,
                input_params=collector_params,
                status=JobStatus.QUEUED.value,
                progress_percent=0,
                timeout_seconds=300,
                max_retries=3,
            )
            db.add(job)
            created_jobs.append(job)

        await db.commit()
        await db.refresh(assessment)
        for j in created_jobs:
            await db.refresh(j)

        logger.info(
            "Atomically created assessment %s and enqueued %d discovery jobs",
            assessment.id,
            len(created_jobs),
        )
        return assessment, created_jobs

    @staticmethod
    async def get_assessment(
        db: AsyncSession,
        assessment_id: uuid.UUID,
    ) -> Assessment | None:
        """Retrieve an assessment by ID with eager relationships loaded."""
        stmt = (
            select(Assessment)
            .where(Assessment.id == assessment_id)
            .options(
                selectinload(Assessment.assessment_assets),
                selectinload(Assessment.assessment_observations),
                selectinload(Assessment.risk_assessments),
            )
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def list_assessments(
        db: AsyncSession,
        target_id: uuid.UUID | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
        tenant_id: str | None = None,
    ) -> tuple[list[Assessment], int]:
        """List assessments with pagination and optional target/status/tenant filters."""
        stmt = select(Assessment)
        count_stmt = select(func.count(Assessment.id))

        if target_id is not None:
            stmt = stmt.where(Assessment.target_id == target_id)
            count_stmt = count_stmt.where(Assessment.target_id == target_id)
        if status:
            stmt = stmt.where(Assessment.status == status)
            count_stmt = count_stmt.where(Assessment.status == status)
        if tenant_id:
            tenant_filter = Assessment.target_snapshot["tenant_id"].as_string() == tenant_id
            stmt = stmt.where(tenant_filter)
            count_stmt = count_stmt.where(tenant_filter)

        stmt = stmt.order_by(Assessment.created_at.desc()).limit(limit).offset(offset)

        total_res = await db.scalar(count_stmt)
        total = total_res or 0
        items_res = await db.scalars(stmt)
        return list(items_res.all()), total

    @staticmethod
    async def cancel_assessment(
        db: AsyncSession,
        assessment_id: uuid.UUID,
        reason: str = "User cancellation",
    ) -> Assessment:
        """Cooperatively cancel an active assessment while preserving all persisted evidence."""
        # Row-level lock on assessment to serialize concurrent cancellation requests
        lock_stmt = (
            select(Assessment)
            .where(Assessment.id == assessment_id)
            .options(
                selectinload(Assessment.assessment_assets),
                selectinload(Assessment.assessment_observations),
                selectinload(Assessment.risk_assessments),
            )
            .with_for_update()
        )
        assessment = await db.scalar(lock_stmt)
        if assessment is None:
            raise AssessmentNotFoundError(f"Assessment '{assessment_id}' was not found")

        if assessment.is_terminal():
            raise InvalidLifecycleTransitionError(
                f"Cannot cancel assessment '{assessment_id}' in terminal status '{assessment.status}'"
            )

        now = datetime.now(UTC)
        assessment.status = AssessmentStatus.CANCELLED.value
        assessment.progress_stage = AssessmentStage.CANCELLED.value
        assessment.completed_at = now
        assessment.error_summary = reason

        # Cooperative cancellation: Cancel any active or queued child DiscoveryJobs
        active_jobs_stmt = select(DiscoveryJob).where(
            DiscoveryJob.assessment_id == assessment.id,
            DiscoveryJob.status.in_([JobStatus.QUEUED.value, JobStatus.RUNNING.value]),
        )
        active_jobs = (await db.scalars(active_jobs_stmt)).all()
        for j in active_jobs:
            await JobService.cancel_job(db, j.id, reason=f"Assessment cancelled: {reason}")

        # Build snapshot of partially collected evidence
        coverage = compute_coverage_summary(
            requested_sources=assessment.discovery_sources,
            collector_results=assessment.collector_results,
            assessment_assets=assessment.assessment_assets,
            observations=assessment.assessment_observations,
        )
        counts = compute_asset_counts(
            [aa.asset_snapshot for aa in assessment.assessment_assets if aa.asset_snapshot]
        )
        risk = compute_risk_summary(assessment.risk_assessments)

        snapshot = build_report_snapshot(
            assessment=assessment,
            target_snapshot=assessment.target_snapshot,
            coverage_summary=coverage,
            asset_counts=counts,
            risk_summary=risk,
            assessment_assets=assessment.assessment_assets,
            risk_evaluations=assessment.risk_assessments,
        )
        assessment.report_snapshot = snapshot
        assessment.report_snapshot_hash = compute_canonical_evidence_sha256(snapshot)

        await db.commit()
        await db.refresh(assessment)
        logger.info(
            "Cancelled assessment %s; preserved partial evidence and cancelled child jobs",
            assessment.id,
        )
        return assessment

    @staticmethod
    async def retry_assessment(
        db: AsyncSession,
        assessment_id: uuid.UUID,
    ) -> Assessment:
        """Retry a failed or partially completed assessment with provenance tracking."""
        # Row-level lock on assessment to serialize concurrent retry requests
        lock_stmt = (
            select(Assessment)
            .where(Assessment.id == assessment_id)
            .options(
                selectinload(Assessment.assessment_assets),
                selectinload(Assessment.assessment_observations),
                selectinload(Assessment.risk_assessments),
            )
            .with_for_update()
        )
        assessment = await db.scalar(lock_stmt)
        if assessment is None:
            raise AssessmentNotFoundError(f"Assessment '{assessment_id}' was not found")

        if assessment.status not in (
            AssessmentStatus.FAILED.value,
            AssessmentStatus.PARTIALLY_COMPLETED.value,
        ):
            raise InvalidLifecycleTransitionError(
                f"Only failed or partially completed assessments can be retried. Current: '{assessment.status}'"
            )

        if assessment.retry_count >= assessment.max_retries:
            raise MaxRetriesExceededError(
                f"Assessment '{assessment_id}' has reached its maximum retries ({assessment.max_retries})"
            )

        # Record attempt history
        current_results = dict(assessment.collector_results or {})
        attempts = current_results.get("execution_attempts", [])
        attempts.append(
            {
                "attempt_number": assessment.retry_count + 1,
                "attempted_at": datetime.now(UTC).isoformat(),
                "status_before_retry": assessment.status,
                "error_summary": assessment.error_summary,
            }
        )
        current_results["execution_attempts"] = attempts

        assessment.retry_count += 1
        assessment.status = AssessmentStatus.QUEUED.value
        assessment.progress_stage = AssessmentStage.PENDING.value
        assessment.progress_percent = 0
        assessment.collector_results = current_results
        assessment.error_summary = None
        # Preserve snapshot attributes during retry transition to satisfy DB immutability trigger
        assessment.completed_at = None

        # Re-queue or reset any failed child discovery jobs
        jobs_stmt = select(DiscoveryJob).where(
            DiscoveryJob.assessment_id == assessment.id,
            DiscoveryJob.status.in_([JobStatus.FAILED.value, JobStatus.CANCELLED.value]),
        )
        existing_jobs = (await db.scalars(jobs_stmt)).all()
        for j in existing_jobs:
            j.status = JobStatus.QUEUED.value
            j.worker_id = None
            j.lease_expires_at = None
            j.error_message = None
            j.progress_percent = 0

        await db.commit()
        await db.refresh(assessment)
        logger.info(
            "Queued retry for assessment %s (retry_count=%s)",
            assessment.id,
            assessment.retry_count,
        )
        return assessment

    # ==========================================================================
    # Concurrency-Safe First-Seen Provenance Strategy (Phase 3)
    # ==========================================================================
    @classmethod
    async def _associate_asset_to_assessment(
        cls,
        db: AsyncSession,
        assessment: Assessment,
        asset: CryptographicAsset,
    ) -> tuple[AssessmentAsset, bool]:
        """Atomically correlate an asset to an assessment with concurrency-safe first-seen tracking.

        Definition of first_seen_in_assessment:
        An asset is considered `first_seen_in_assessment = True` for Assessment A if and only if
        Assessment A is the chronologically earliest assessment in the platform to associate with this asset.

        Concurrency & Provenance Strategy:
        Uses PostgreSQL row-level locking (SELECT ... FOR UPDATE) on `cryptographic_assets` to serialize
        concurrent assessments discovering the exact same asset, preventing duplicate first-seen claims.
        Queries historical `assessment_assets` associations to verify if any prior assessment exists.
        """
        # 1. Acquire row-level lock on the target cryptographic asset
        lock_stmt = (
            select(CryptographicAsset.id).where(CryptographicAsset.id == asset.id).with_for_update()
        )
        await db.execute(lock_stmt)

        # Cancellation guard to prevent late asset associations after cancellation
        if await cls.is_cancelled(db, assessment.id):
            logger.info("Assessment %s is cancelled; halting asset association", assessment.id)
            raise AssessmentCancelledError(f"Assessment '{assessment.id}' is cancelled")

        # 2. Check if an AssessmentAsset record already exists for this (assessment_id, asset_id)
        existing_stmt = select(AssessmentAsset).where(
            AssessmentAsset.assessment_id == assessment.id,
            AssessmentAsset.asset_id == asset.id,
        )
        existing_aa = await db.scalar(existing_stmt)
        if existing_aa is not None:
            return existing_aa, False

        # 3. Query prior assessment associations for this asset
        # An assessment is considered prior if its created_at timestamp is earlier than this assessment,
        # or in tie-breaking if its ID is lexicographically smaller.
        prior_stmt = (
            select(AssessmentAsset.assessment_id)
            .join(Assessment, AssessmentAsset.assessment_id == Assessment.id)
            .where(
                AssessmentAsset.asset_id == asset.id,
                AssessmentAsset.assessment_id != assessment.id,
                (Assessment.created_at < assessment.created_at)
                | (
                    (Assessment.created_at == assessment.created_at)
                    & (Assessment.id < assessment.id)
                ),
            )
            .limit(1)
        )
        prior_association = await db.scalar(prior_stmt)
        first_seen = prior_association is None

        # 4. Build frozen snapshot of asset attributes
        snapshot = {
            "id": str(asset.id),
            "asset_key": asset.asset_key,
            "display_name": asset.display_name,
            "asset_type": asset.asset_type,
            "algorithm_family": asset.algorithm_family,
            "algorithm_name": asset.algorithm_name,
            "cryptographic_purpose": asset.cryptographic_purpose,
            "parameters": asset.parameters or {},
            "business_criticality": asset.business_criticality,
            "confidence_score": asset.confidence_score,
        }

        aa = AssessmentAsset(
            assessment_id=assessment.id,
            asset_id=asset.id,
            classification=asset.classification or "OBSERVED",
            asset_snapshot=snapshot,
            first_seen_in_assessment=first_seen,
        )
        db.add(aa)
        await db.flush()
        return aa, True

    # ==========================================================================
    # Collector Execution Modules
    # ==========================================================================
    @classmethod
    async def _execute_tls_collector(
        cls,
        db: AsyncSession,
        assessment: Assessment,
        target: Target | None,
        engine_version: str,
    ) -> tuple[dict[str, Any], list[Observation], list[CryptographicAsset]]:
        """Execute bounded TLS network inspection and ingest CBOM observations."""
        if await cls.is_cancelled(db, assessment.id):
            logger.info("Assessment %s is cancelled; halting TLS collector", assessment.id)
            return (
                {
                    "status": "cancelled",
                    "reason": "Late execution aborted due to assessment cancellation",
                },
                [],
                [],
            )

        if not target or not target.is_eligible_for_scan:
            return (
                {
                    "status": "failed",
                    "error": (
                        f"Target '{target.hostname if target else 'None'}' is not verified or authorized"
                    ),
                },
                [],
                [],
            )

        t0 = time.perf_counter()
        resolver = SafeDestinationResolver(
            allow_test_targets_only=False,
            allow_loopback_for_tests=True,
        )
        collector = BoundedTLSCollector(
            resolver=resolver,
            collector_version=engine_version,
            allow_unverified_certificates=True,
        )
        # Run TLS collection in worker thread pool so event loop remains responsive
        tls_result = await asyncio.to_thread(collector.inspect_target, target.hostname)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        # Cancellation check before writing any observations or assets
        if await cls.is_cancelled(db, assessment.id):
            logger.info(
                "Assessment %s was cancelled during TLS collection; discarding late evidence",
                assessment.id,
            )
            return (
                {
                    "status": "cancelled",
                    "reason": "Late execution aborted due to assessment cancellation",
                },
                [],
                [],
            )

        if not tls_result.success or not tls_result.endpoint_evidence:
            return (
                {
                    "status": "failed",
                    "duration_ms": elapsed_ms,
                    "error": tls_result.error_message or "TLS inspection failed",
                },
                [],
                [],
            )

        cert = tls_result.certificate_evidence
        obs_payload = {
            "hostname": target.hostname,
            "port": 443,
            "pinned_ip": tls_result.pinned_ip,
            "negotiated_protocol": tls_result.endpoint_evidence.negotiated_protocol,
            "cipher_suite": tls_result.endpoint_evidence.negotiated_cipher_name,
            "cipher_bits": tls_result.endpoint_evidence.negotiated_cipher_bits,
            "peer_certificate": (
                {
                    "subject_dn": cert.subject_dn if cert else None,
                    "issuer_dn": cert.issuer_dn if cert else None,
                    "serial_hex": cert.serial_number_hex if cert else None,
                    "valid_from": cert.valid_from.isoformat() if cert else None,
                    "valid_until": cert.valid_to.isoformat() if cert else None,
                    "sha256_fingerprint": cert.sha256_fingerprint if cert else None,
                    "public_key": {
                        "algorithm_family": cert.public_key_algorithm if cert else "RSA",
                        "key_size_bits": cert.public_key_size_bits if cert else 2048,
                    },
                    "signature_algorithm": cert.signature_algorithm if cert else "sha256",
                }
                if cert
                else None
            ),
        }
        obs_hash = compute_canonical_evidence_sha256(obs_payload)
        obs = Observation(
            target_id=target.id,
            observation_type="tls_endpoint",
            source="network_tls",
            observed_value=obs_payload,
            evidence_sha256=obs_hash,
            confidence=1.0,
            collector_version=engine_version,
        )
        db.add(obs)
        await db.flush()

        db.add(AssessmentObservation(assessment_id=assessment.id, observation_id=obs.id))
        ep_asset, cert_asset = await AssetCorrelator.ingest_tls_observation(db, obs)

        assets: list[CryptographicAsset] = [ep_asset]
        if cert_asset:
            assets.append(cert_asset)

        outcome = {
            "status": "success",
            "duration_ms": elapsed_ms,
            "evidence_sha256": obs_hash,
            "protocol": tls_result.endpoint_evidence.negotiated_protocol,
        }
        return outcome, [obs], assets

    @classmethod
    async def _execute_source_collector(
        cls,
        db: AsyncSession,
        assessment: Assessment,
        target: Target | None,
        engine_version: str,
        payload: dict[str, Any],
        job_id: uuid.UUID | None = None,
    ) -> tuple[dict[str, Any], list[Observation], list[CryptographicAsset]]:
        """Execute static source code cryptographic scanner."""
        if await cls.is_cancelled(db, assessment.id):
            logger.info("Assessment %s is cancelled; halting source collector", assessment.id)
            return (
                {
                    "status": "cancelled",
                    "reason": "Late execution aborted due to assessment cancellation",
                },
                [],
                [],
            )

        t0 = time.perf_counter()
        source_dir = payload.get("source_dir")
        archive_path = payload.get("source_archive_path")
        workspace_dir: Path | None = None

        if archive_path and Path(archive_path).exists():
            try:
                scratch_root = Path(settings.scratch_dir)
                os.makedirs(scratch_root, mode=0o700, exist_ok=True)
                workspace_dir = (
                    scratch_root / f"job_{job_id or assessment.id}_{uuid.uuid4().hex[:12]}"
                )
                os.makedirs(workspace_dir, mode=0o700, exist_ok=False)
                await asyncio.to_thread(extract_archive_safely, Path(archive_path), workspace_dir)
                source_dir = str(workspace_dir)
            except Exception as exc:
                if workspace_dir and workspace_dir.exists():
                    safe_delete_workspace(workspace_dir)
                return (
                    {
                        "status": "failed",
                        "error": f"Archive extraction failed: {exc}",
                    },
                    [],
                    [],
                )

        if not source_dir or not Path(source_dir).exists():
            return (
                {
                    "status": "skipped",
                    "reason": "No source archive or repository directory provided in payload",
                },
                [],
                [],
            )

        try:
            scanner = SourceScanner(Path(source_dir))
            findings, src_coverage = await asyncio.to_thread(scanner.scan)
            elapsed_ms = int((time.perf_counter() - t0) * 1000)

            # Cancellation check before writing any observations or assets
            if await cls.is_cancelled(db, assessment.id):
                logger.info(
                    "Assessment %s was cancelled during source scanning; discarding late evidence",
                    assessment.id,
                )
                return (
                    {
                        "status": "cancelled",
                        "reason": "Late execution aborted due to assessment cancellation",
                    },
                    [],
                    [],
                )

            obs_list: list[Observation] = []
            asset_list: list[CryptographicAsset] = []

            for finding in findings:
                f_payload = {
                    "file_path": finding.file_path,
                    "line_number": finding.line_number,
                    "primitive": finding.primitive,
                    "algorithm": finding.algorithm,
                    "library": finding.library,
                    "parameters": finding.parameters,
                }
                f_hash = compute_canonical_evidence_sha256(f_payload)
                f_obs = Observation(
                    target_id=target.id if target else None,
                    observation_type="source_code",
                    source="static_source",
                    observed_value=f_payload,
                    evidence_sha256=f_hash,
                    confidence=finding.confidence,
                    collector_version=engine_version,
                )
                db.add(f_obs)
                await db.flush()

                db.add(AssessmentObservation(assessment_id=assessment.id, observation_id=f_obs.id))
                obs_list.append(f_obs)

                src_asset = await AssetCorrelator.ingest_source_finding(
                    db=db,
                    finding=finding,
                    target_id=target.id if target else None,
                    observation_id=f_obs.id,
                )
                asset_list.append(src_asset)

            outcome = {
                "status": "success",
                "duration_ms": elapsed_ms,
                "findings_count": len(findings),
                "files_examined": src_coverage.total_files_examined,
            }
            return outcome, obs_list, asset_list
        finally:
            if workspace_dir and workspace_dir.exists():
                success = safe_delete_workspace(workspace_dir)
                if not success:
                    write_cleanup_failure_record(
                        workspace_dir=workspace_dir,
                        job_id=job_id or assessment.id,
                        staging_dir=settings.staging_dir,
                        tenant_id=assessment.target_snapshot.get("tenant_id")
                        if assessment.target_snapshot
                        else None,
                        assessment_id=str(assessment.id),
                        error="Safe workspace deletion failed in source collector finally block",
                        db=db,
                    )

    @classmethod
    async def _execute_dep_collector(
        cls,
        db: AsyncSession,
        assessment: Assessment,
        target: Target | None,
        engine_version: str,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], list[Observation], list[CryptographicAsset]]:
        """Execute dependency manifest cryptographic scanner."""
        if await cls.is_cancelled(db, assessment.id):
            logger.info("Assessment %s is cancelled; halting dependency collector", assessment.id)
            return (
                {
                    "status": "cancelled",
                    "reason": "Late execution aborted due to assessment cancellation",
                },
                [],
                [],
            )

        t0 = time.perf_counter()
        dep_dir = payload.get("dependency_dir") or payload.get("source_dir")
        if not dep_dir or not Path(dep_dir).exists():
            return (
                {
                    "status": "skipped",
                    "reason": "No dependency directory or manifest path provided",
                },
                [],
                [],
            )

        dep_scanner = DependencyScanner(Path(dep_dir))
        dep_items = await asyncio.to_thread(dep_scanner.scan)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        # Cancellation check before writing any observations or assets
        if await cls.is_cancelled(db, assessment.id):
            logger.info(
                "Assessment %s was cancelled during dependency scan; discarding late evidence",
                assessment.id,
            )
            return (
                {
                    "status": "cancelled",
                    "reason": "Late execution aborted due to assessment cancellation",
                },
                [],
                [],
            )

        obs_list: list[Observation] = []
        asset_list: list[CryptographicAsset] = []

        for item in dep_items:
            d_payload = {
                "name": item.name,
                "version": item.version,
                "ecosystem": item.ecosystem,
                "manifest_path": item.manifest_path,
                "is_direct": item.is_direct,
                "is_known_crypto": item.is_known_crypto,
            }
            d_hash = compute_canonical_evidence_sha256(d_payload)
            d_obs = Observation(
                target_id=target.id if target else None,
                observation_type="dependency_manifest",
                source="dependency_manifest",
                observed_value=d_payload,
                evidence_sha256=d_hash,
                confidence=0.9 if not item.is_direct else 0.75,
                collector_version=engine_version,
            )
            db.add(d_obs)
            await db.flush()

            db.add(AssessmentObservation(assessment_id=assessment.id, observation_id=d_obs.id))
            obs_list.append(d_obs)

            dep_asset = await AssetCorrelator.ingest_dependency(
                db=db,
                dep=item,
                target_id=target.id if target else None,
                observation_id=d_obs.id,
            )
            asset_list.append(dep_asset)

        outcome = {
            "status": "success",
            "duration_ms": elapsed_ms,
            "dependencies_count": len(dep_items),
        }
        return outcome, obs_list, asset_list

    @classmethod
    async def _execute_config_collector(
        cls,
        db: AsyncSession,
        assessment: Assessment,
        target: Target | None,
        engine_version: str,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], list[Observation], list[CryptographicAsset]]:
        """Execute web server and ingress configuration parser."""
        if await cls.is_cancelled(db, assessment.id):
            logger.info("Assessment %s is cancelled; halting config collector", assessment.id)
            return (
                {
                    "status": "cancelled",
                    "reason": "Late execution aborted due to assessment cancellation",
                },
                [],
                [],
            )

        t0 = time.perf_counter()
        config_content = payload.get("config_content")
        config_type = payload.get("config_type", "nginx")

        if not config_content:
            return (
                {
                    "status": "skipped",
                    "reason": "No configuration content supplied in payload",
                },
                [],
                [],
            )

        cfg_findings: list[ConfigFinding] = []
        if config_type == "nginx":
            cfg_findings = await asyncio.to_thread(ConfigImporter.parse_nginx, config_content)
        elif config_type == "apache":
            cfg_findings = await asyncio.to_thread(ConfigImporter.parse_apache, config_content)
        elif config_type == "ingress":
            cfg_findings = await asyncio.to_thread(
                ConfigImporter.parse_kubernetes_ingress, config_content
            )

        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        # Cancellation check before writing any observations or assets
        if await cls.is_cancelled(db, assessment.id):
            logger.info(
                "Assessment %s was cancelled during config parsing; discarding late evidence",
                assessment.id,
            )
            return (
                {
                    "status": "cancelled",
                    "reason": "Late execution aborted due to assessment cancellation",
                },
                [],
                [],
            )
        obs_list: list[Observation] = []
        asset_list: list[CryptographicAsset] = []

        for cfg_find in cfg_findings:
            c_payload = {
                "directive": cfg_find.directive,
                "file_path": cfg_find.file_path,
                "line_number": cfg_find.line_number,
                "raw_value": cfg_find.raw_value,
                "protocols": cfg_find.protocols,
                "ciphers": cfg_find.ciphers,
            }
            c_hash = compute_canonical_evidence_sha256(c_payload)
            c_obs = Observation(
                target_id=target.id if target else None,
                observation_type="configuration",
                source="config_import",
                observed_value=c_payload,
                evidence_sha256=c_hash,
                confidence=0.9,
                collector_version=engine_version,
            )
            db.add(c_obs)
            await db.flush()

            db.add(AssessmentObservation(assessment_id=assessment.id, observation_id=c_obs.id))
            obs_list.append(c_obs)

            cfg_asset = await AssetCorrelator.ingest_config_finding(
                db=db,
                cfg=cfg_find,
                target_id=target.id if target else None,
                observation_id=c_obs.id,
            )
            asset_list.append(cfg_asset)

        outcome = {
            "status": "success",
            "duration_ms": elapsed_ms,
            "findings_count": len(cfg_findings),
        }
        return outcome, obs_list, asset_list

    # ==========================================================================
    # Durable Worker Architecture (Phase 1)
    # ==========================================================================
    @classmethod
    async def enqueue_discovery_jobs(
        cls,
        db: AsyncSession,
        assessment_id: uuid.UUID,
        input_payload: dict[str, Any] | None = None,
    ) -> list[DiscoveryJob]:
        """Create and queue durable DiscoveryJob records for each requested source."""
        payload = input_payload or {}
        # Row-level lock on assessment to serialize concurrent job enqueues
        lock_stmt = select(Assessment).where(Assessment.id == assessment_id).with_for_update()
        assessment = await db.scalar(lock_stmt)
        if assessment is None:
            raise AssessmentNotFoundError(f"Assessment '{assessment_id}' was not found")

        if await cls.is_cancelled(db, assessment.id):
            logger.info("Assessment %s is cancelled; skipping job enqueue", assessment.id)
            return []

        now = datetime.now(UTC)
        assessment.status = AssessmentStatus.RUNNING.value
        assessment.progress_stage = AssessmentStage.DISPATCHING_COLLECTORS.value
        assessment.progress_percent = 20
        assessment.started_at = assessment.started_at or now

        target: Target | None = None
        if assessment.target_id:
            target = await db.scalar(select(Target).where(Target.id == assessment.target_id))

        created_jobs: list[DiscoveryJob] = []
        for src in assessment.discovery_sources:
            job_type = SOURCE_TO_JOB_TYPE.get(src)
            if not job_type:
                continue

            # Check if active or completed job already exists for this assessment
            stmt = select(DiscoveryJob).where(
                DiscoveryJob.assessment_id == assessment.id,
                DiscoveryJob.job_type == job_type,
            )
            existing = await db.scalar(stmt)
            if existing is not None:
                created_jobs.append(existing)
                continue

            collector_params = dict(payload)
            if job_type == JobType.TLS_DISCOVERY.value and target:
                collector_params["hostname"] = target.hostname
                collector_params["port"] = 443

            job = DiscoveryJob(
                job_type=job_type,
                target_id=assessment.target_id,
                assessment_id=assessment.id,
                input_params=collector_params,
                status=JobStatus.QUEUED.value,
                progress_percent=0,
                timeout_seconds=300,
                max_retries=3,
            )
            db.add(job)
            created_jobs.append(job)

        await db.commit()
        for j in created_jobs:
            await db.refresh(j)

        logger.info(
            "Enqueued %d discovery jobs for assessment %s", len(created_jobs), assessment.id
        )
        return created_jobs

    @classmethod
    async def execute_discovery_job(
        cls,
        db: AsyncSession,
        job_id: uuid.UUID,
        worker_id: str | None = None,
    ) -> DiscoveryJob:
        """Execute a single durable DiscoveryJob, ingesting evidence and advancing assessment."""
        job = await JobService.get_job(db, job_id)
        if job is None:
            raise ValueError(f"DiscoveryJob '{job_id}' not found")

        if not job.assessment_id:
            raise ValueError(f"DiscoveryJob '{job_id}' is not linked to an assessment")

        assessment = await cls.get_assessment(db, job.assessment_id)
        if assessment is None:
            raise AssessmentNotFoundError(f"Assessment '{job.assessment_id}' not found")

        # Cooperative cancellation check
        if await cls.is_cancelled(db, assessment.id):
            logger.info(
                "Parent assessment %s is cancelled; cancelling job %s", assessment.id, job.id
            )
            return await JobService.cancel_job(db, job.id, "Parent assessment cancelled")

        target: Target | None = None
        if assessment.target_id:
            target = await db.scalar(select(Target).where(Target.id == assessment.target_id))

        worker_name = worker_id or "inline_worker"
        job.status = JobStatus.RUNNING.value
        job.worker_id = worker_name
        job.started_at = datetime.now(UTC)
        job.lease_expires_at = datetime.now(UTC) + timedelta(seconds=60)
        await db.commit()

        try:
            outcome: dict[str, Any] = {}
            if job.job_type == JobType.TLS_DISCOVERY.value:
                outcome, _, _ = await cls._execute_tls_collector(
                    db=db,
                    assessment=assessment,
                    target=target,
                    engine_version=assessment.engine_version,
                )
            elif job.job_type == JobType.SOURCE_ANALYSIS.value:
                outcome, _, _ = await cls._execute_source_collector(
                    db=db,
                    assessment=assessment,
                    target=target,
                    engine_version=assessment.engine_version,
                    payload=job.input_params,
                    job_id=job.id,
                )
            elif job.job_type == JobType.DEPENDENCY_SCAN.value:
                outcome, _, _ = await cls._execute_dep_collector(
                    db=db,
                    assessment=assessment,
                    target=target,
                    engine_version=assessment.engine_version,
                    payload=job.input_params,
                )
            elif job.job_type == JobType.CONFIG_IMPORT.value:
                outcome, _, _ = await cls._execute_config_collector(
                    db=db,
                    assessment=assessment,
                    target=target,
                    engine_version=assessment.engine_version,
                    payload=job.input_params,
                )
            else:
                outcome = {"status": "failed", "error": f"Unknown job type '{job.job_type}'"}

            # Re-check cancellation before advancing terminal job status
            if await cls.is_cancelled(db, assessment.id):
                logger.info(
                    "Assessment %s was cancelled while job %s was executing; cancelling job",
                    assessment.id,
                    job.id,
                )
                return await JobService.cancel_job(db, job.id, "Parent assessment cancelled")

            if outcome.get("status") in ("success", "skipped"):
                await JobService.complete_job(db, job.id, result_summary=outcome)
            else:
                err_msg = outcome.get("error", "Collector execution failed")
                await JobService.fail_job(db, job.id, error_message=err_msg, can_retry=False)

        except Exception as exc:
            logger.exception("Error during execution of job %s: %s", job.id, exc)
            await JobService.fail_job(db, job.id, error_message=str(exc), can_retry=False)

        await db.refresh(job)

        # Attempt to synchronize and advance assessment
        await cls.sync_assessment_from_jobs(db, assessment.id)
        return job

    @classmethod
    async def sync_assessment_from_jobs(
        cls,
        db: AsyncSession,
        assessment_id: uuid.UUID,
    ) -> Assessment:
        """Check all child DiscoveryJobs and advance assessment to CBOM correlation and risk scoring."""
        # Row-level lock on assessment to serialize concurrent job completion sync
        lock_stmt = select(Assessment).where(Assessment.id == assessment_id).with_for_update()
        assessment = await db.scalar(lock_stmt)
        if assessment is None:
            raise AssessmentNotFoundError(f"Assessment '{assessment_id}' was not found")

        if assessment.is_terminal():
            return assessment

        if await cls.is_cancelled(db, assessment.id):
            return assessment

        # Retrieve all child jobs
        stmt = select(DiscoveryJob).where(DiscoveryJob.assessment_id == assessment.id)
        jobs = list((await db.scalars(stmt)).all())

        if not jobs:
            return assessment

        terminal_statuses = (
            JobStatus.COMPLETED.value,
            JobStatus.FAILED.value,
            JobStatus.CANCELLED.value,
        )
        completed_count = sum(1 for j in jobs if j.status in terminal_statuses)

        if completed_count < len(jobs):
            # Still jobs pending or running
            progress = 20 + int((completed_count / len(jobs)) * 30)
            assessment.progress_percent = progress
            await db.commit()
            return assessment

        # All child discovery jobs have completed!
        collector_outcomes: dict[str, Any] = dict(assessment.collector_results or {})
        for j in jobs:
            src = JOB_TYPE_TO_SOURCE.get(j.job_type, j.job_type)
            if j.status == JobStatus.COMPLETED.value:
                collector_outcomes[src] = j.result_summary or {"status": "success"}
            elif j.status == JobStatus.FAILED.value:
                collector_outcomes[src] = {
                    "status": "failed",
                    "error": j.error_message or "Execution failed",
                }
            elif j.status == JobStatus.CANCELLED.value:
                collector_outcomes[src] = {
                    "status": "cancelled",
                    "error": j.error_message or "Job cancelled",
                }

        assessment.collector_results = collector_outcomes
        await db.commit()

        # Query all observations linked to this assessment
        obs_stmt = (
            select(Observation)
            .join(
                AssessmentObservation,
                AssessmentObservation.observation_id == Observation.id,
            )
            .where(AssessmentObservation.assessment_id == assessment.id)
        )
        observations = list((await db.scalars(obs_stmt)).all())

        # Query all cryptographic assets associated with observations for this assessment
        from services.api.app.db.models.asset_observation import AssetObservation

        assets_stmt = (
            select(CryptographicAsset)
            .join(
                AssetObservation,
                AssetObservation.asset_id == CryptographicAsset.id,
            )
            .where(AssetObservation.observation_id.in_([obs.id for obs in observations]))
            .distinct()
        )
        discovered_assets: list[CryptographicAsset] = []
        if observations:
            discovered_assets = list((await db.scalars(assets_stmt)).all())

        # Advance through Stages 3, 4, 5
        return await cls._correlate_and_evaluate(
            db=db,
            assessment=assessment,
            discovered_assets=discovered_assets,
            collector_outcomes=collector_outcomes,
            observations=observations,
        )

    # ==========================================================================
    # CBOM Correlation, Risk Evaluation & Immutable Finalization
    # ==========================================================================
    @classmethod
    async def _correlate_and_evaluate(
        cls,
        db: AsyncSession,
        assessment: Assessment,
        discovered_assets: list[CryptographicAsset],
        collector_outcomes: dict[str, Any],
        observations: list[Observation],
    ) -> Assessment:
        """Advance assessment through Stage 3 (CBOM), Stage 4 (Risk), and Stage 5 (Finalization)."""
        # Cancellation checkpoint before Stage 3
        if await cls.is_cancelled(db, assessment.id):
            logger.info("Assessment %s was cancelled; halting before Stage 3", assessment.id)
            await db.refresh(assessment)
            return assessment

        # ----------------------------------------------------------------------
        # Stage 3: Correlating CBOM Assets & Concurrency-Safe First-Seen Tracking
        # ----------------------------------------------------------------------
        assessment.progress_stage = AssessmentStage.CORRELATING_CBOM.value
        assessment.progress_percent = 55
        assessment.collector_results = collector_outcomes
        await db.commit()

        unique_assets: dict[uuid.UUID, CryptographicAsset] = {a.id: a for a in discovered_assets}

        created_assessment_assets: list[AssessmentAsset] = []
        try:
            for asset in unique_assets.values():
                aa, _ = await cls._associate_asset_to_assessment(
                    db=db,
                    assessment=assessment,
                    asset=asset,
                )
                created_assessment_assets.append(aa)
            await db.flush()
        except AssessmentCancelledError:
            await db.rollback()
            await db.refresh(assessment)
            return assessment

        # Cancellation checkpoint before Stage 4
        if await cls.is_cancelled(db, assessment.id):
            logger.info("Assessment %s was cancelled; halting before Stage 4", assessment.id)
            await db.refresh(assessment)
            return assessment

        # ----------------------------------------------------------------------
        # Stage 4: Evaluating Quantum Risk
        # ----------------------------------------------------------------------
        assessment.progress_stage = AssessmentStage.EVALUATING_RISK.value
        assessment.progress_percent = 80
        await db.commit()

        risk_evaluations: list[RiskAssessment] = []
        all_recs: list[Any] = []
        for asset in unique_assets.values():
            if await cls.is_cancelled(db, assessment.id):
                logger.info(
                    "Assessment %s was cancelled during risk evaluation; halting", assessment.id
                )
                await db.rollback()
                await db.refresh(assessment)
                return assessment

            r_stmt = select(RiskAssessment).where(
                RiskAssessment.assessment_id == assessment.id,
                RiskAssessment.asset_id == asset.id,
            )
            existing_risk = await db.scalar(r_stmt)

            if existing_risk is None:
                r_assessment, factors, recs = QuantumRiskEngine.assess_asset(
                    asset,
                    context={"confidentiality_lifetime_years": 10, "exposure": "internet"},
                )
                r_assessment.id = uuid.uuid4()
                r_assessment.assessment_id = assessment.id
                r_assessment.asset_id = asset.id

                db.add(r_assessment)
                await db.flush()

                for factor in factors:
                    factor.risk_assessment_id = r_assessment.id
                    db.add(factor)

                for rec in recs:
                    rec.risk_assessment_id = r_assessment.id
                    db.add(rec)
                    all_recs.append(rec)

                await db.flush()
                risk_evaluations.append(r_assessment)

                for aa in created_assessment_assets:
                    if aa.asset_id == asset.id:
                        aa.risk_assessment_id = r_assessment.id
                        break
            else:
                risk_evaluations.append(existing_risk)

        await db.flush()

        # Cancellation checkpoint before Stage 5
        if await cls.is_cancelled(db, assessment.id):
            logger.info("Assessment %s was cancelled; halting before Stage 5", assessment.id)
            await db.refresh(assessment)
            return assessment

        # ----------------------------------------------------------------------
        # Stage 5: Finalizing & Immutable Snapshot Generation
        # ----------------------------------------------------------------------
        assessment.progress_stage = AssessmentStage.FINALIZING.value
        assessment.progress_percent = 95
        await db.commit()

        coverage_summary = compute_coverage_summary(
            requested_sources=assessment.discovery_sources,
            collector_results=collector_outcomes,
            assessment_assets=created_assessment_assets,
            observations=observations,
        )
        counts = compute_asset_counts(list(unique_assets.values()))
        risk = compute_risk_summary(risk_evaluations)

        # Determine terminal status
        active_statuses = [
            out.get("status")
            for src, out in collector_outcomes.items()
            if src in assessment.discovery_sources
        ]

        if not active_statuses or all(s == "failed" for s in active_statuses):
            final_status = AssessmentStatus.FAILED.value
            assessment.error_summary = "All requested discovery collectors failed."
        elif any(s == "failed" for s in active_statuses):
            final_status = AssessmentStatus.PARTIALLY_COMPLETED.value
            failed_collectors = [
                src for src, out in collector_outcomes.items() if out.get("status") == "failed"
            ]
            assessment.error_summary = (
                f"Partial assessment completed. Failed collectors: {', '.join(failed_collectors)}"
            )
        else:
            final_status = AssessmentStatus.COMPLETED.value
            assessment.error_summary = None

        assessment.status = final_status
        assessment.progress_stage = final_status.upper()
        assessment.progress_percent = 100
        assessment.completed_at = datetime.now(UTC)
        assessment.collector_results = collector_outcomes
        assessment.coverage_summary = coverage_summary
        assessment.asset_counts = counts
        assessment.risk_summary = risk

        snapshot = build_report_snapshot(
            assessment=assessment,
            target_snapshot=assessment.target_snapshot,
            coverage_summary=coverage_summary,
            asset_counts=counts,
            risk_summary=risk,
            assessment_assets=created_assessment_assets,
            risk_evaluations=risk_evaluations,
            recommendations=all_recs,
        )
        assessment.report_snapshot = snapshot
        assessment.report_snapshot_hash = compute_canonical_evidence_sha256(snapshot)

        await db.commit()
        await db.refresh(assessment)

        # Terminal Cleanup Hook for Staged Upload Archive
        if assessment.status == AssessmentStatus.COMPLETED.value:
            upload_token = (assessment.target_snapshot or {}).get("upload_token")
            tenant_id = (assessment.target_snapshot or {}).get("tenant_id") or "default"
            if upload_token and settings.staging_dir:
                token_dir = Path(settings.staging_dir) / tenant_id / upload_token
                if token_dir.exists():
                    safe_delete_workspace(token_dir)
                    logger.info("Terminal cleanup hook: safely removed staged upload %s", token_dir)

        logger.info(
            "Assessment %s finalized with status '%s' (assets=%s, qvi_score=%s)",
            assessment.id,
            assessment.status,
            counts["total"],
            risk["overall_score"],
        )
        return assessment

    # ==========================================================================
    # Unified Execution Pipeline Entry Point (Phase 1 & Phase 2)
    # ==========================================================================
    @classmethod
    async def execute_assessment(
        cls,
        db: AsyncSession,
        assessment_id: uuid.UUID,
        input_payload: dict[str, Any] | None = None,
        execution_mode: str = "sync",
        worker_id: str | None = None,
    ) -> Assessment:
        """Execute the end-to-end multi-collector assessment workflow pipeline.

        Supported Modes:
        - "sync": Runs discovery collectors sequentially, creates durable DiscoveryJob records,
                  and finalizes assessment within the current invocation (preserves CLI demo workflow).
        - "durable": Enqueues durable DiscoveryJobs into PostgreSQL; if worker_id is provided,
                     claims and processes them to completion.
        """
        payload = input_payload or {}
        # Row-level lock on assessment to serialize concurrent execution requests
        lock_stmt = select(Assessment).where(Assessment.id == assessment_id).with_for_update()
        assessment = await db.scalar(lock_stmt)
        if assessment is None:
            raise AssessmentNotFoundError(f"Assessment '{assessment_id}' was not found")

        # Cooperative cancellation check
        if await cls.is_cancelled(db, assessment.id):
            logger.info("Assessment %s is cancelled; aborting execute_assessment", assessment.id)
            return assessment

        if execution_mode == "durable":
            jobs = await cls.enqueue_discovery_jobs(db, assessment.id, payload)
            if worker_id:
                # Process queued jobs via worker
                for j in jobs:
                    if await cls.is_cancelled(db, assessment.id):
                        break
                    await cls.execute_discovery_job(db, j.id, worker_id=worker_id)
                refreshed = await cls.get_assessment(db, assessment.id)
                return refreshed or assessment
            return assessment

        # ----------------------------------------------------------------------
        # Synchronous Execution with Durable Job Records (CLI / In-Process Mode)
        # ----------------------------------------------------------------------
        now = datetime.now(UTC)
        assessment.status = AssessmentStatus.RUNNING.value
        assessment.progress_stage = AssessmentStage.VALIDATING_SCOPE.value
        assessment.progress_percent = 10
        assessment.started_at = assessment.started_at or now
        await db.commit()

        target: Target | None = None
        if assessment.target_id:
            target = await db.scalar(select(Target).where(Target.id == assessment.target_id))

        collector_outcomes: dict[str, Any] = dict(assessment.collector_results or {})
        all_observations: list[Observation] = []
        all_assets: list[CryptographicAsset] = []

        # Cancellation check before Stage 2
        if await cls.is_cancelled(db, assessment.id):
            await db.refresh(assessment)
            return assessment

        assessment.progress_stage = AssessmentStage.DISPATCHING_COLLECTORS.value
        assessment.progress_percent = 25
        await db.commit()

        # Enqueue durable discovery jobs for audit & durable record retention
        durable_jobs = await cls.enqueue_discovery_jobs(db, assessment.id, payload)
        job_by_type = {j.job_type: j for j in durable_jobs}

        # 2a. Network TLS Collector
        if "network_tls" in assessment.discovery_sources:
            if await cls.is_cancelled(db, assessment.id):
                await db.refresh(assessment)
                return assessment

            tls_job = job_by_type.get(JobType.TLS_DISCOVERY.value)
            outcome, obs, assets = await cls._execute_tls_collector(
                db=db,
                assessment=assessment,
                target=target,
                engine_version=assessment.engine_version,
            )
            collector_outcomes["network_tls"] = outcome
            all_observations.extend(obs)
            all_assets.extend(assets)
            if tls_job:
                if outcome.get("status") == "success":
                    await JobService.complete_job(db, tls_job.id, result_summary=outcome)
                else:
                    await JobService.fail_job(
                        db, tls_job.id, outcome.get("error", "TLS scan failed"), can_retry=False
                    )

        # 2b. Static Source Scanner
        if "static_source" in assessment.discovery_sources:
            if await cls.is_cancelled(db, assessment.id):
                await db.refresh(assessment)
                return assessment

            src_job = job_by_type.get(JobType.SOURCE_ANALYSIS.value)
            outcome, obs, assets = await cls._execute_source_collector(
                db=db,
                assessment=assessment,
                target=target,
                engine_version=assessment.engine_version,
                payload=payload,
            )
            collector_outcomes["static_source"] = outcome
            all_observations.extend(obs)
            all_assets.extend(assets)
            if src_job:
                if outcome.get("status") in ("success", "skipped"):
                    await JobService.complete_job(db, src_job.id, result_summary=outcome)
                else:
                    await JobService.fail_job(
                        db, src_job.id, outcome.get("error", "Source scan failed"), can_retry=False
                    )

        # 2c. Dependency Manifest Scanner
        if "dependency_manifest" in assessment.discovery_sources:
            if await cls.is_cancelled(db, assessment.id):
                await db.refresh(assessment)
                return assessment

            dep_job = job_by_type.get(JobType.DEPENDENCY_SCAN.value)
            outcome, obs, assets = await cls._execute_dep_collector(
                db=db,
                assessment=assessment,
                target=target,
                engine_version=assessment.engine_version,
                payload=payload,
            )
            collector_outcomes["dependency_manifest"] = outcome
            all_observations.extend(obs)
            all_assets.extend(assets)
            if dep_job:
                if outcome.get("status") in ("success", "skipped"):
                    await JobService.complete_job(db, dep_job.id, result_summary=outcome)
                else:
                    await JobService.fail_job(
                        db, dep_job.id, outcome.get("error", "Dep scan failed"), can_retry=False
                    )

        # 2d. Configuration Importer
        if "config_import" in assessment.discovery_sources:
            if await cls.is_cancelled(db, assessment.id):
                await db.refresh(assessment)
                return assessment

            cfg_job = job_by_type.get(JobType.CONFIG_IMPORT.value)
            outcome, obs, assets = await cls._execute_config_collector(
                db=db,
                assessment=assessment,
                target=target,
                engine_version=assessment.engine_version,
                payload=payload,
            )
            collector_outcomes["config_import"] = outcome
            all_observations.extend(obs)
            all_assets.extend(assets)
            if cfg_job:
                if outcome.get("status") in ("success", "skipped"):
                    await JobService.complete_job(db, cfg_job.id, result_summary=outcome)
                else:
                    await JobService.fail_job(
                        db, cfg_job.id, outcome.get("error", "Config scan failed"), can_retry=False
                    )

        # Advance Stages 3, 4, 5
        return await cls._correlate_and_evaluate(
            db=db,
            assessment=assessment,
            discovered_assets=all_assets,
            collector_outcomes=collector_outcomes,
            observations=all_observations,
        )
