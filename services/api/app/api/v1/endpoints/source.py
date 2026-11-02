"""Quantum Flow Technologies — Source Code Discovery Upload Endpoints.

Safely ingests source archives, performs static AST/pattern analysis and dependency
extraction, and correlates findings into the CBOM inventory.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from packages.cbom.correlator import AssetCorrelator
from packages.scanner.dependencies.scanner import DependencyScanner
from packages.scanner.safety.canonical import compute_canonical_evidence_sha256
from packages.scanner.source.archive import (
    ArchiveSecurityError,
    extract_archive_safely,
)
from packages.scanner.source.scanner import SourceScanner
from services.api.app.db.models.observation import Observation
from services.api.app.db.session import get_db
from services.api.app.schemas.source import SourceUploadResponse

router = APIRouter(prefix="/source", tags=["Source Discovery"])

# Maximum uploaded zip archive size (20 MB)
MAX_UPLOAD_ARCHIVE_BYTES = 20 * 1024 * 1024


@router.post(
    "/upload",
    response_model=SourceUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Source Archive for Cryptographic Discovery",
    description="Upload a ZIP or TAR source code archive for read-only static cryptographic and dependency analysis.",
)
async def upload_source_archive(
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(..., description="ZIP or TAR source archive"),
) -> SourceUploadResponse:
    """Analyze an uploaded source code archive."""
    filename = file.filename or "archive.zip"
    if not (filename.endswith(".zip") or filename.endswith(".tar") or filename.endswith(".tar.gz")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported archive format. Only .zip, .tar, and .tar.gz archives are permitted.",
        )

    # Read archive bytes with size bounding
    content = await file.read(MAX_UPLOAD_ARCHIVE_BYTES + 1)
    if len(content) > MAX_UPLOAD_ARCHIVE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded archive exceeds 20 MB size limit.",
        )

    temp_dir = Path(tempfile.mkdtemp(prefix="qf_src_"))
    try:
        archive_path = temp_dir / filename
        archive_path.write_bytes(content)

        extract_dir = temp_dir / "extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)

        try:
            extract_archive_safely(archive_path, extract_dir)
        except ArchiveSecurityError as sec_err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Archive validation failed: {sec_err}",
            ) from sec_err

        # 1. Run Source Scanner (Python, JS/TS, Java)
        src_scanner = SourceScanner(extract_dir)
        findings, coverage = src_scanner.scan()

        # 2. Run Dependency Scanner
        dep_scanner = DependencyScanner(extract_dir)
        dependencies = dep_scanner.scan()

        # Ingest findings into Observation and CBOM
        for f in findings:
            payload = f.to_dict()
            evidence_hash = compute_canonical_evidence_sha256(payload)
            obs = Observation(
                target_id=None,
                observation_type="source_code_primitive",
                source=f"source_scanner_{f.language}",
                observed_value=payload,
                evidence_sha256=evidence_hash,
                collector_version="v1.0.0",
            )
            db.add(obs)
            await db.flush()
            await AssetCorrelator.ingest_source_finding(
                db=db,
                finding=f,
                target_id=None,
                observation_id=obs.id,
            )

        # Ingest dependencies into Observation and CBOM
        for d in dependencies:
            payload = d.to_dict()
            evidence_hash = compute_canonical_evidence_sha256(payload)
            obs = Observation(
                target_id=None,
                observation_type="software_dependency",
                source=f"dependency_scanner_{d.ecosystem}",
                observed_value=payload,
                evidence_sha256=evidence_hash,
                collector_version="v1.0.0",
            )
            db.add(obs)
            await db.flush()
            await AssetCorrelator.ingest_dependency(
                db=db,
                dep=d,
                target_id=None,
                observation_id=obs.id,
            )

        await db.commit()

        return SourceUploadResponse(
            archive_name=filename,
            files_scanned=coverage.scanned_files_count,
            findings_count=len(findings),
            dependencies_count=len(dependencies),
            coverage=coverage.to_dict(),
            sample_findings=[f.to_dict() for f in findings[:10]],
        )

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
