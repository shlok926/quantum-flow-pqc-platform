"""Quantum Flow Technologies — CBOM Cryptographic Asset API Endpoints.

Provides asset listing, detail retrieval, relationship exploration,
CycloneDX 1.6 JSON export, and formula-injection-safe CSV exports.
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.cbom.cyclonedx import serialize_cyclonedx_16
from packages.reports.exporter import export_assets_csv
from services.api.app.db.models.asset_relationship import AssetRelationship
from services.api.app.db.models.cryptographic_asset import CryptographicAsset
from services.api.app.db.session import get_db
from services.api.app.schemas.asset import (
    AssetListResponse,
    AssetRelationshipResponse,
    CryptographicAssetResponse,
)

router = APIRouter(tags=["CBOM & Cryptographic Assets"])


@router.get(
    "/assets",
    response_model=AssetListResponse,
    summary="List Cryptographic Assets",
    description="List correlated cryptographic assets with filtering by asset type, algorithm family, and classification.",
)
async def list_assets(
    db: Annotated[AsyncSession, Depends(get_db)],
    asset_type: str | None = Query(default=None),
    algorithm_family: str | None = Query(default=None),
    classification: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AssetListResponse:
    """List assets."""
    stmt = select(CryptographicAsset)
    count_stmt = select(func.count(CryptographicAsset.id))

    if asset_type:
        stmt = stmt.where(CryptographicAsset.asset_type == asset_type)
        count_stmt = count_stmt.where(CryptographicAsset.asset_type == asset_type)
    if algorithm_family:
        stmt = stmt.where(CryptographicAsset.algorithm_family == algorithm_family)
        count_stmt = count_stmt.where(CryptographicAsset.algorithm_family == algorithm_family)
    if classification:
        stmt = stmt.where(CryptographicAsset.classification == classification)
        count_stmt = count_stmt.where(CryptographicAsset.classification == classification)

    stmt = stmt.order_by(CryptographicAsset.last_seen_at.desc()).limit(limit).offset(offset)

    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    assets_res = await db.execute(stmt)
    assets = list(assets_res.scalars().all())

    return AssetListResponse(
        assets=[CryptographicAssetResponse.model_validate(a) for a in assets],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/assets/export/csv",
    summary="Export Cryptographic Assets (CSV)",
    description="Download cryptographic asset inventory in RFC 4180 CSV format with formula-injection neutralization.",
)
async def export_assets_as_csv(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Export assets as safe CSV."""
    stmt = select(CryptographicAsset).order_by(CryptographicAsset.last_seen_at.desc()).limit(1000)
    res = await db.execute(stmt)
    assets = list(res.scalars().all())

    csv_data = export_assets_csv(assets)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="quantumflow_cbom_assets.csv"'},
    )


@router.get(
    "/cbom/export",
    summary="Export Cryptographic Bill of Materials (CycloneDX 1.6 JSON)",
    description="Export full CBOM representation compliant with CycloneDX 1.6 Cryptographic Extension.",
)
async def export_cbom_cyclonedx(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Export CycloneDX 1.6 CBOM."""
    assets_stmt = (
        select(CryptographicAsset).order_by(CryptographicAsset.last_seen_at.desc()).limit(500)
    )
    assets_res = await db.execute(assets_stmt)
    assets = list(assets_res.scalars().all())

    rel_stmt = select(AssetRelationship).limit(500)
    rel_res = await db.execute(rel_stmt)
    relationships = list(rel_res.scalars().all())

    return serialize_cyclonedx_16(assets=assets, relationships=relationships)


@router.get(
    "/assets/{asset_id}",
    response_model=CryptographicAssetResponse,
    summary="Get Cryptographic Asset Details",
    description="Retrieve full details for an individual cryptographic asset.",
)
async def get_asset(
    asset_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CryptographicAssetResponse:
    """Get single asset."""
    stmt = select(CryptographicAsset).where(CryptographicAsset.id == asset_id)
    res = await db.execute(stmt)
    asset = res.scalar_one_or_none()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cryptographic asset '{asset_id}' not found",
        )
    return CryptographicAssetResponse.model_validate(asset)


@router.get(
    "/assets/{asset_id}/relationships",
    response_model=list[AssetRelationshipResponse],
    summary="Get Asset Graph Relationships",
    description="Retrieve outgoing relationships and dependencies for an asset.",
)
async def get_asset_relationships(
    asset_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AssetRelationshipResponse]:
    """Get asset relationships."""
    stmt = select(AssetRelationship).where(AssetRelationship.source_asset_id == asset_id)
    res = await db.execute(stmt)
    relationships = res.scalars().all()
    return [AssetRelationshipResponse.model_validate(r) for r in relationships]
