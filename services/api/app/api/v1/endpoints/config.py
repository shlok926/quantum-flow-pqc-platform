"""Quantum Flow Technologies — Cryptographic Configuration Import Endpoints.

Parses Nginx, Apache, and Kubernetes TLS configurations and correlates findings
into the CBOM inventory.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from packages.cbom.correlator import AssetCorrelator
from packages.scanner.config.importer import ConfigImporter
from packages.scanner.config.models import ConfigFinding
from packages.scanner.safety.canonical import compute_canonical_evidence_sha256
from services.api.app.db.models.observation import Observation
from services.api.app.db.session import get_db
from services.api.app.schemas.source import (
    ConfigImportRequest,
    ConfigImportResponse,
)

router = APIRouter(prefix="/config", tags=["Configuration Import"])


@router.post(
    "/import",
    response_model=ConfigImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import Cryptographic Configuration File",
    description="Import and parse an Nginx, Apache, or Kubernetes TLS configuration for protocol and cipher settings.",
)
async def import_configuration(
    payload: ConfigImportRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConfigImportResponse:
    """Import cryptographic configuration."""
    cfg_type = payload.config_type.lower().strip()
    findings: list[ConfigFinding] = []

    if cfg_type == "nginx":
        findings = ConfigImporter.parse_nginx(payload.content, payload.file_path)
    elif cfg_type in ("apache", "httpd"):
        findings = ConfigImporter.parse_apache(payload.content, payload.file_path)
    elif cfg_type in ("kubernetes", "k8s", "ingress"):
        findings = ConfigImporter.parse_kubernetes_ingress(payload.content, payload.file_path)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported configuration type '{payload.config_type}'. Supported types: nginx, apache, kubernetes",
        )

    assets_created = 0
    for f in findings:
        f_dict = f.to_dict()
        evidence_hash = compute_canonical_evidence_sha256(f_dict)
        obs = Observation(
            target_id=None,
            observation_type="cryptographic_configuration",
            source=f"config_importer_{cfg_type}",
            observed_value=f_dict,
            evidence_sha256=evidence_hash,
            collector_version="v1.0.0",
        )
        db.add(obs)
        await db.flush()

        await AssetCorrelator.ingest_config_finding(
            db=db,
            cfg=f,
            target_id=None,
            observation_id=obs.id,
        )
        assets_created += 1

    await db.commit()

    return ConfigImportResponse(
        config_type=cfg_type,
        file_path=payload.file_path,
        findings_count=len(findings),
        assets_created=assets_created,
        findings=[f.to_dict() for f in findings],
    )
