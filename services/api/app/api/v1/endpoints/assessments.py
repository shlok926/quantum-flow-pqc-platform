"""Quantum Flow Technologies — Enterprise Assessment REST API Endpoints.

Provides strongly typed, tenant-isolated REST endpoints for creating, querying,
tracking, cancelling, retrying, and retrieving cryptographic assessment reports.
"""

import hashlib
import json
import logging
import os
import urllib.parse
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from packages.reports.exporter import (
    SnapshotIntegrityError,
    export_assessment_csv,
    export_assessment_cyclonedx,
    export_assessment_markdown_report,
    verify_and_load_snapshot,
)
from packages.scanner.safety import (
    derive_global_upload_slot_key,
    derive_tenant_upload_slot_key,
)
from packages.scanner.safety.canonical import compute_canonical_evidence_sha256
from services.api.app.core.config import settings
from services.api.app.core.security import (
    SecurityIdentity,
    get_current_identity,
    verify_tenant_access,
)
from services.api.app.db.models.discovery_job import DiscoveryJob
from services.api.app.db.session import get_db
from services.api.app.schemas.assessment import (
    AssessmentCancelRequest,
    AssessmentCreateRequest,
    AssessmentJobListResponse,
    AssessmentJobSummary,
    AssessmentListResponse,
    AssessmentReportResponse,
    AssessmentResponse,
    StagedUploadResponse,
    UploadTokenMetadata,
)
from services.api.app.services.assessment_service import (
    AssessmentNotFoundError,
    AssessmentService,
    DuplicateActiveAssessmentError,
    InvalidLifecycleTransitionError,
    MaxRetriesExceededError,
    TargetNotEligibleError,
)

logger = logging.getLogger("quantumflow.api.assessments")

router = APIRouter(prefix="/assessments", tags=["Assessments"])

MAX_TENANT_STAGING_BYTES = 100 * 1024 * 1024  # 100MB
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024  # 20MB
IN_FLIGHT_ALLOWANCE_BYTES = 20 * 1024 * 1024  # 20MB
ALLOWED_ARCHIVE_EXTENSIONS = {".zip", ".tar", ".gz", ".tgz"}


def make_content_disposition(filename: str) -> str:
    """Generate RFC 5987 / RFC 6266 compliant Content-Disposition header."""
    encoded_filename = urllib.parse.quote(filename, encoding="utf-8")
    return f"attachment; filename=\"{filename}\"; filename*=UTF-8''{encoded_filename}"


@router.post(
    "/stage-upload",
    response_model=StagedUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Stage Archive Upload",
    description="Stage an archive file with two-tier pre-parsing advisory locks and quota enforcement.",
)
async def stage_upload(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[SecurityIdentity, Depends(get_current_identity)],
) -> StagedUploadResponse:
    """Stage an archive file with two-tier pre-parsing locks and quota enforcement."""
    if not identity.has_permission("assessment:create"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    # Check database dialect for advisory locking
    is_postgres = False
    bind = db.bind
    if bind is not None and "postgresql" in getattr(bind.dialect, "name", ""):
        is_postgres = True

    # Step 1 & 2: Two-Tier Pre-Parsing Advisory Locks (Cluster Global + Per-Tenant)
    acquired_global_slot = None
    if is_postgres:
        for slot in range(10):
            key = derive_global_upload_slot_key(slot)
            acquired = await db.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": key})
            if acquired:
                acquired_global_slot = slot
                break
        if acquired_global_slot is None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="System upload capacity reached. Maximum cluster concurrency (10) active.",
            )

    acquired_tenant_slot = None
    if is_postgres:
        for slot in range(3):
            key = derive_tenant_upload_slot_key(identity.tenant_id, slot)
            acquired = await db.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": key})
            if acquired:
                acquired_tenant_slot = slot
                break
        if acquired_tenant_slot is None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Tenant upload concurrency quota exceeded. Maximum 3 concurrent uploads allowed.",
            )

    # Step 3: Quota Accounting & Reservation
    staging_root = Path(settings.staging_dir).resolve()
    tenant_dir = staging_root / identity.tenant_id
    tenant_dir.mkdir(parents=True, exist_ok=True)

    now_utc = datetime.now(UTC)
    now_ts = now_utc.timestamp()

    # Calculate committed and in-flight usage
    committed_bytes = 0
    in_flight_bytes = 0

    if tenant_dir.exists():
        for entry in os.scandir(tenant_dir):
            if not entry.is_dir():
                continue
            meta_path = os.path.join(entry.path, "metadata.json")
            res_path = os.path.join(entry.path, "reservation.json")
            if os.path.isfile(meta_path):
                try:
                    with open(meta_path, encoding="utf-8") as f:
                        meta = json.load(f)
                        if meta.get("status") != "purged":
                            committed_bytes += int(meta.get("byte_size", 0))
                except Exception:
                    pass
            elif os.path.isfile(res_path):
                try:
                    with open(res_path, encoding="utf-8") as f:
                        res = json.load(f)
                        res_at_str = res.get("reserved_at")
                        if res_at_str:
                            res_dt = datetime.fromisoformat(res_at_str)
                            if (now_ts - res_dt.timestamp()) < 300:
                                in_flight_bytes += int(
                                    res.get("byte_size_reserved", IN_FLIGHT_ALLOWANCE_BYTES)
                                )
                except Exception:
                    pass

    if committed_bytes + in_flight_bytes + IN_FLIGHT_ALLOWANCE_BYTES > MAX_TENANT_STAGING_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Staging storage quota exceeded: {MAX_TENANT_STAGING_BYTES // (1024 * 1024)}MB ceiling.",
        )

    upload_token = str(uuid.uuid4())
    upload_dir = tenant_dir / upload_token
    upload_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    reservation_path = upload_dir / "reservation.json"
    reservation_data = {
        "upload_token": upload_token,
        "tenant_id": identity.tenant_id,
        "slot": acquired_tenant_slot if acquired_tenant_slot is not None else 0,
        "status": "in_progress",
        "byte_size_reserved": IN_FLIGHT_ALLOWANCE_BYTES,
        "reserved_at": now_utc.isoformat(),
    }
    with open(reservation_path, "w", encoding="utf-8") as f:
        json.dump(reservation_data, f)

    # Step 4: Explicit Multipart Form Parsing (Invoked strictly after lock & reservation)
    try:
        form = await request.form()
    except Exception as exc:
        if reservation_path.exists():
            reservation_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse multipart form: {exc}",
        ) from exc

    file_item = form.get("file")
    if file_item is None or not hasattr(file_item, "filename") or not file_item.filename:
        if reservation_path.exists():
            reservation_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required form field 'file'",
        )
    file_obj = cast(Any, file_item)

    original_filename = Path(file_obj.filename or "upload.zip").name
    if not any(original_filename.lower().endswith(ext) for ext in ALLOWED_ARCHIVE_EXTENSIONS):
        if reservation_path.exists():
            reservation_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Permitted: {', '.join(sorted(ALLOWED_ARCHIVE_EXTENSIONS))}",
        )

    # Stream file to .part
    part_path = upload_dir / f"{original_filename}.part"
    final_path = upload_dir / original_filename
    sha256_hasher = hashlib.sha256()
    total_bytes = 0

    try:
        with open(part_path, "wb") as out_f:
            while True:
                chunk = await file_obj.read(64 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_ARCHIVE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Uploaded archive exceeds {MAX_ARCHIVE_BYTES // (1024 * 1024)}MB ceiling.",
                    )
                sha256_hasher.update(chunk)
                out_f.write(chunk)
    except Exception:
        if part_path.exists():
            part_path.unlink(missing_ok=True)
        if reservation_path.exists():
            reservation_path.unlink(missing_ok=True)
        raise

    calculated_hash = sha256_hasher.hexdigest()

    # Step 5: Three-Step Atomic Finalization
    os.replace(part_path, final_path)

    metadata = UploadTokenMetadata(
        upload_token=upload_token,
        tenant_id=identity.tenant_id,
        filename=original_filename,
        byte_size=total_bytes,
        sha256=calculated_hash,
        content_type=getattr(file_obj, "content_type", "application/zip") or "application/zip",
        status="staged",
        uploaded_at=now_utc.isoformat(),
        assessment_id=None,
        retry_count=0,
    )

    tmp_meta = upload_dir / "metadata.json.tmp"
    final_meta = upload_dir / "metadata.json"
    with open(tmp_meta, "w", encoding="utf-8") as f:
        f.write(metadata.model_dump_json(indent=2))
    os.replace(tmp_meta, final_meta)

    # Remove reservation file
    if reservation_path.exists():
        reservation_path.unlink(missing_ok=True)

    return StagedUploadResponse(
        upload_token=upload_token,
        filename=original_filename,
        byte_size=total_bytes,
        sha256=calculated_hash,
        status="staged",
        uploaded_at=now_utc,
    )


@router.post(
    "",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create & Enqueue Assessment",
    description=(
        "Atomically create a new enterprise cryptographic assessment and enqueue durable "
        "background discovery jobs in PostgreSQL."
    ),
)
async def create_assessment(
    payload: AssessmentCreateRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[SecurityIdentity, Depends(get_current_identity)],
) -> AssessmentResponse:
    """Create and enqueue an enterprise assessment."""
    if not identity.has_permission("assessment:create"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    try:
        assessment, _ = await AssessmentService.create_and_enqueue_assessment(
            db=db,
            title=payload.title,
            target_id=payload.target_id,
            discovery_sources=payload.discovery_sources,
            input_payload=payload.input_payload,
            extra_params=payload.extra_params,
            tenant_id=identity.tenant_id,
            upload_token=payload.upload_token,
        )
    except AssessmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TargetNotEligibleError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DuplicateActiveAssessmentError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    response.headers["Location"] = f"/api/v1/assessments/{assessment.id}"
    return AssessmentResponse.model_validate(assessment)


@router.get(
    "",
    response_model=AssessmentListResponse,
    summary="List Assessments",
    description="List enterprise assessments with optional target and status filtering, tenant-scoped.",
)
async def list_assessments(
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[SecurityIdentity, Depends(get_current_identity)],
    target_id: uuid.UUID | None = Query(default=None, description="Filter by target UUID"),
    status_filter: str | None = Query(
        default=None, alias="status", description="Filter by assessment status"
    ),
    limit: int = Query(default=50, ge=1, le=100, description="Page limit (1-100)"),
    offset: int = Query(default=0, ge=0, description="Page offset (>=0)"),
) -> AssessmentListResponse:
    """List assessments with tenant isolation and pagination."""
    if not identity.has_permission("assessment:read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    tenant_filter = None if identity.is_admin else identity.tenant_id
    items, total = await AssessmentService.list_assessments(
        db=db,
        target_id=target_id,
        status=status_filter,
        limit=limit,
        offset=offset,
        tenant_id=tenant_filter,
    )
    return AssessmentListResponse(
        items=[AssessmentResponse.model_validate(a) for a in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{assessment_id}",
    response_model=AssessmentResponse,
    summary="Get Assessment Details",
    description="Retrieve live assessment execution status, progress metrics, and summary findings.",
)
async def get_assessment(
    assessment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[SecurityIdentity, Depends(get_current_identity)],
) -> AssessmentResponse:
    """Retrieve an assessment by ID with tenant isolation."""
    if not identity.has_permission("assessment:read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    assessment = await AssessmentService.get_assessment(db, assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment '{assessment_id}' not found",
        )

    verify_tenant_access(identity, assessment.target_snapshot.get("tenant_id"))
    return AssessmentResponse.model_validate(assessment)


@router.post(
    "/{assessment_id}/cancel",
    response_model=AssessmentResponse,
    summary="Cancel Assessment",
    description="Cooperatively cancel an active assessment while preserving all persisted discovery evidence.",
)
async def cancel_assessment(
    assessment_id: uuid.UUID,
    payload: AssessmentCancelRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[SecurityIdentity, Depends(get_current_identity)],
) -> AssessmentResponse:
    """Cooperatively cancel an assessment with tenant isolation."""
    if not identity.has_permission("assessment:cancel"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    assessment = await AssessmentService.get_assessment(db, assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment '{assessment_id}' not found",
        )

    verify_tenant_access(identity, assessment.target_snapshot.get("tenant_id"))

    try:
        cancelled = await AssessmentService.cancel_assessment(
            db=db,
            assessment_id=assessment_id,
            reason=payload.reason,
        )
    except InvalidLifecycleTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return AssessmentResponse.model_validate(cancelled)


@router.post(
    "/{assessment_id}/retry",
    response_model=AssessmentResponse,
    summary="Retry Assessment",
    description="Retry a failed or partially completed assessment with provenance tracking.",
)
async def retry_assessment(
    assessment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[SecurityIdentity, Depends(get_current_identity)],
) -> AssessmentResponse:
    """Retry a failed or partially completed assessment."""
    if not identity.has_permission("assessment:create"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    assessment = await AssessmentService.get_assessment(db, assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment '{assessment_id}' not found",
        )

    verify_tenant_access(identity, assessment.target_snapshot.get("tenant_id"))

    try:
        retried = await AssessmentService.retry_assessment(db, assessment_id)
    except (InvalidLifecycleTransitionError, MaxRetriesExceededError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return AssessmentResponse.model_validate(retried)


@router.get(
    "/{assessment_id}/report",
    response_model=AssessmentReportResponse,
    summary="Get Assessment Report Snapshot",
    description="Retrieve the cryptographically verified, immutable frozen report snapshot.",
)
async def get_assessment_report(
    assessment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[SecurityIdentity, Depends(get_current_identity)],
) -> AssessmentReportResponse:
    """Retrieve terminal assessment report snapshot with cryptographic verification."""
    if not identity.has_permission("assessment:read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    assessment = await AssessmentService.get_assessment(db, assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment '{assessment_id}' not found",
        )

    verify_tenant_access(identity, assessment.target_snapshot.get("tenant_id"))

    if not assessment.is_terminal():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Report snapshot is not available until assessment execution has reached a terminal status.",
        )

    expected_hash = assessment.report_snapshot_hash
    is_verified = False
    if expected_hash and assessment.report_snapshot:
        actual_hash = compute_canonical_evidence_sha256(assessment.report_snapshot)
        is_verified = actual_hash == expected_hash

    return AssessmentReportResponse(
        assessment_id=assessment.id,
        status=assessment.status,
        methodology_version=assessment.methodology_version,
        engine_version=assessment.engine_version,
        report_snapshot=assessment.report_snapshot or {},
        report_snapshot_hash=assessment.report_snapshot_hash or "",
        is_hash_verified=is_verified,
        is_immutable=True,
        completed_at=assessment.completed_at,
    )


@router.get(
    "/{assessment_id}/jobs",
    response_model=AssessmentJobListResponse,
    summary="List Assessment Discovery Jobs",
    description="Inspect background DiscoveryJob worker leases, execution status, and retry counts.",
)
async def list_assessment_jobs(
    assessment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[SecurityIdentity, Depends(get_current_identity)],
) -> AssessmentJobListResponse:
    """List child discovery jobs for an assessment."""
    if not identity.has_permission("assessment:read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    assessment = await AssessmentService.get_assessment(db, assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment '{assessment_id}' not found",
        )

    verify_tenant_access(identity, assessment.target_snapshot.get("tenant_id"))

    stmt = (
        select(DiscoveryJob)
        .where(DiscoveryJob.assessment_id == assessment_id)
        .order_by(DiscoveryJob.created_at.asc())
    )
    jobs = list((await db.scalars(stmt)).all())

    return AssessmentJobListResponse(
        assessment_id=assessment.id,
        total_jobs=len(jobs),
        jobs=[AssessmentJobSummary.model_validate(j) for j in jobs],
    )


@router.get(
    "/{assessment_id}/reports/cyclonedx",
    response_class=Response,
    summary="Download CycloneDX 1.6 CBOM Report",
    description="Deliver verified CycloneDX 1.6 Cryptographic Bill of Materials (CBOM) JSON report.",
)
async def get_cyclonedx_report(
    assessment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[SecurityIdentity, Depends(get_current_identity)],
) -> Response:
    """Download verified CycloneDX 1.6 CBOM report."""
    if not identity.has_permission("assessment:read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    assessment = await AssessmentService.get_assessment(db, assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment '{assessment_id}' not found",
        )

    verify_tenant_access(identity, assessment.target_snapshot.get("tenant_id"))

    if not assessment.is_terminal():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Report is not available until assessment execution has reached a terminal status.",
        )

    try:
        snapshot = verify_and_load_snapshot(assessment)
    except SnapshotIntegrityError as exc:
        logger.critical(
            "SNAPSHOT_INTEGRITY_TAMPER_DETECTED",
            extra={"assessment_id": str(assessment.id), "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Snapshot cryptographic verification failed. Report tampering detected.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load verified snapshot: {exc}",
        ) from exc

    cbom_data = export_assessment_cyclonedx(snapshot)
    content = json.dumps(cbom_data, indent=2)
    content_bytes = content.encode("utf-8")

    filename = f"cbom_{assessment.id}.cyclonedx.json"
    headers = {
        "Content-Type": "application/vnd.cyclonedx+json",
        "Content-Length": str(len(content_bytes)),
        "Content-Disposition": make_content_disposition(filename),
    }
    return Response(
        content=content_bytes,
        status_code=status.HTTP_200_OK,
        headers=headers,
        media_type="application/vnd.cyclonedx+json",
    )


@router.get(
    "/{assessment_id}/reports/csv",
    response_class=Response,
    summary="Download RFC 4180 CSV CBOM Report",
    description="Deliver verified RFC 4180 CRLF CSV report with spreadsheet formula-injection mitigation.",
)
async def get_csv_report(
    assessment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[SecurityIdentity, Depends(get_current_identity)],
) -> Response:
    """Download verified CSV report."""
    if not identity.has_permission("assessment:read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    assessment = await AssessmentService.get_assessment(db, assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment '{assessment_id}' not found",
        )

    verify_tenant_access(identity, assessment.target_snapshot.get("tenant_id"))

    if not assessment.is_terminal():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Report is not available until assessment execution has reached a terminal status.",
        )

    try:
        snapshot = verify_and_load_snapshot(assessment)
    except SnapshotIntegrityError as exc:
        logger.critical(
            "SNAPSHOT_INTEGRITY_TAMPER_DETECTED",
            extra={"assessment_id": str(assessment.id), "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Snapshot cryptographic verification failed. Report tampering detected.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load verified snapshot: {exc}",
        ) from exc

    csv_content = export_assessment_csv(snapshot)
    content_bytes = csv_content.encode("utf-8")

    filename = f"cbom_{assessment.id}.csv"
    headers = {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Length": str(len(content_bytes)),
        "Content-Disposition": make_content_disposition(filename),
    }
    return Response(
        content=content_bytes,
        status_code=status.HTTP_200_OK,
        headers=headers,
        media_type="text/csv",
    )


@router.get(
    "/{assessment_id}/reports/markdown",
    response_class=Response,
    summary="Download Executive Markdown Report",
    description="Deliver verified Executive Markdown report with cryptographic integrity seal.",
)
async def get_markdown_report(
    assessment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[SecurityIdentity, Depends(get_current_identity)],
) -> Response:
    """Download verified Executive Markdown report."""
    if not identity.has_permission("assessment:read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    assessment = await AssessmentService.get_assessment(db, assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment '{assessment_id}' not found",
        )

    verify_tenant_access(identity, assessment.target_snapshot.get("tenant_id"))

    if not assessment.is_terminal():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Report is not available until assessment execution has reached a terminal status.",
        )

    try:
        snapshot = verify_and_load_snapshot(assessment)
    except SnapshotIntegrityError as exc:
        logger.critical(
            "SNAPSHOT_INTEGRITY_TAMPER_DETECTED",
            extra={"assessment_id": str(assessment.id), "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Snapshot cryptographic verification failed. Report tampering detected.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load verified snapshot: {exc}",
        ) from exc

    md_content = export_assessment_markdown_report(snapshot, assessment.report_snapshot_hash)
    content_bytes = md_content.encode("utf-8")

    filename = f"assessment_{assessment.id}_executive_report.md"
    headers = {
        "Content-Type": "text/markdown; charset=utf-8",
        "Content-Length": str(len(content_bytes)),
        "Content-Disposition": make_content_disposition(filename),
    }
    return Response(
        content=content_bytes,
        status_code=status.HTTP_200_OK,
        headers=headers,
        media_type="text/markdown",
    )
