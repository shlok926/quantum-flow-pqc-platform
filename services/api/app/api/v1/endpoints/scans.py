"""Quantum Flow Technologies — Scan Discovery & Execution Endpoints."""

import asyncio
import dataclasses
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from packages.scanner.safety.canonical import compute_canonical_evidence_sha256
from packages.scanner.safety.resolver import SafeDestinationResolver
from packages.scanner.tls.collector import BoundedTLSCollector
from services.api.app.core.config import settings
from services.api.app.db.models.observation import Observation
from services.api.app.db.models.scan import Scan, ScanStatus
from services.api.app.db.models.target import Target
from services.api.app.db.session import get_db
from services.api.app.schemas.scan import (
    ScanCreate,
    ScanListResponse,
    ScanResponse,
)

router = APIRouter(tags=["Scan Execution"])


@router.post(
    "/targets/{target_id}/scans",
    response_model=ScanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate a bounded TLS discovery inspection",
)
async def create_scan(
    target_id: UUID,
    payload: ScanCreate,
    db: AsyncSession = Depends(get_db),
) -> Scan:
    """Initiate and execute a safe, destination-pinned TLS handshake inspection on port 443."""
    target = await db.scalar(select(Target).where(Target.id == target_id))
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target with ID '{target_id}' was not found",
        )

    # 1. Enforce strict eligibility gate: Verified status AND Confirmed authorisation required
    if not target.is_eligible_for_scan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Target '{target.hostname}' is not eligible for scanning. "
                f"Status: '{target.status}', Authorisation: '{target.authorisation_status}'. "
                "Scanning requires both status='verified' and authorisation_status='confirmed'."
            ),
        )

    # 2. Prevent duplicate concurrent active scans on the same target
    active_scan = await db.scalar(
        select(Scan).where(
            Scan.target_id == target.id,
            Scan.status.in_([ScanStatus.PENDING.value, ScanStatus.IN_PROGRESS.value]),
        )
    )
    if active_scan is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"An active scan '{active_scan.id}' is already in progress for target '{target.hostname}'"
            ),
        )

    started_at = datetime.now(UTC)
    collector_version = settings.collector_version

    # 3. Record durable Scan execution record (database partial unique index enforces race protection)
    scan = Scan(
        target_id=target.id,
        scan_type=payload.scan_type,
        status=ScanStatus.IN_PROGRESS.value,
        collector_version=collector_version,
        started_at=started_at,
    )
    db.add(scan)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An active scan is already in progress for target '{target.hostname}'",
        ) from exc

    # 4. Configure Safe Destination Resolver and Bounded TLS Collector
    resolver = SafeDestinationResolver(
        allow_test_targets_only=settings.allow_test_targets_only,
        allow_loopback_for_tests=(settings.app_env in {"local", "test"}),
    )
    collector = BoundedTLSCollector(
        resolver=resolver,
        collector_version=collector_version,
    )

    # 5. Perform bounded TLS inspection offloaded from async event loop thread
    try:
        result = await asyncio.to_thread(collector.inspect_target, target.hostname)
    except Exception as exc:
        scan.status = ScanStatus.FAILED.value
        scan.error_message = f"Unexpected collector execution error: {exc}"
        scan.completed_at = datetime.now(UTC)
        await db.flush()
        await db.refresh(scan)
        return scan

    completed_at = datetime.now(UTC)
    scan.completed_at = completed_at
    scan.target_ip = result.pinned_ip

    if result.success and result.endpoint_evidence and result.certificate_evidence:
        scan.status = ScanStatus.COMPLETED.value

        # Persist structured TLS transport observation with canonical SHA-256 hash
        endpoint_dict = dataclasses.asdict(result.endpoint_evidence)
        endpoint_dict["scan_timestamp"] = result.endpoint_evidence.scan_timestamp.isoformat()
        endpoint_sha256 = compute_canonical_evidence_sha256(endpoint_dict)

        obs_endpoint = Observation(
            target_id=target.id,
            scan_id=scan.id,
            observation_type="tls_endpoint",
            source="network_tls_probe",
            observed_value=endpoint_dict,
            evidence_sha256=endpoint_sha256,
            confidence=1.0,
            collection_status="observed",
            observed_at=completed_at,
            collector_version=collector_version,
        )
        db.add(obs_endpoint)

        # Persist structured X.509 leaf certificate observation with canonical SHA-256 hash
        cert_dict = dataclasses.asdict(result.certificate_evidence)
        cert_dict["valid_from"] = result.certificate_evidence.valid_from.isoformat()
        cert_dict["valid_to"] = result.certificate_evidence.valid_to.isoformat()
        cert_sha256 = compute_canonical_evidence_sha256(cert_dict)

        obs_cert = Observation(
            target_id=target.id,
            scan_id=scan.id,
            observation_type="x509_certificate",
            source="network_tls_probe",
            observed_value=cert_dict,
            evidence_reference=result.certificate_evidence.sha256_fingerprint,
            evidence_sha256=cert_sha256,
            confidence=1.0,
            collection_status="observed",
            observed_at=completed_at,
            collector_version=collector_version,
        )
        db.add(obs_cert)

    else:
        scan.status = ScanStatus.FAILED.value
        scan.error_message = result.error_message or "TLS inspection failed"

    await db.flush()
    await db.refresh(scan)
    return scan


@router.get(
    "/targets/{target_id}/scans",
    response_model=ScanListResponse,
    summary="List scans for a target",
)
async def list_target_scans(
    target_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ScanListResponse:
    """List historical scan executions for a target."""
    target = await db.scalar(select(Target).where(Target.id == target_id))
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target with ID '{target_id}' was not found",
        )

    scans = (
        await db.scalars(
            select(Scan).where(Scan.target_id == target_id).order_by(Scan.created_at.desc())
        )
    ).all()

    return ScanListResponse(
        items=[ScanResponse.model_validate(s) for s in scans],
        total=len(scans),
    )


@router.get(
    "/scans/{scan_id}",
    response_model=ScanResponse,
    summary="Get scan by ID",
)
async def get_scan(
    scan_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Scan:
    """Retrieve details for a single scan execution."""
    scan = await db.scalar(select(Scan).where(Scan.id == scan_id))
    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID '{scan_id}' was not found",
        )
    return scan
