"""Quantum Flow Technologies — Quantum Risk Intelligence API Endpoints.

Provides endpoints to trigger deterministic risk assessments, query QVI scores,
inspect reason factor breakdowns, and download assessment reports.
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.reports.exporter import (
    export_assessment_json,
    export_assessment_markdown,
)
from packages.risk.engine import QuantumRiskEngine
from services.api.app.db.models.cryptographic_asset import CryptographicAsset
from services.api.app.db.models.risk_assessment import RiskAssessment
from services.api.app.db.session import get_db
from services.api.app.schemas.risk import (
    RiskAssessmentListResponse,
    RiskAssessmentResponse,
)

router = APIRouter(tags=["Quantum Risk Intelligence"])


@router.post(
    "/assets/{asset_id}/assessments",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Evaluate Quantum Risk for Asset",
    description="Trigger an explainable quantum risk assessment for an asset following Quantum Risk Methodology v1.0.",
)
async def assess_asset_risk(
    asset_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RiskAssessmentResponse:
    """Assess quantum risk for asset."""
    stmt = select(CryptographicAsset).where(CryptographicAsset.id == asset_id)
    res = await db.execute(stmt)
    asset = res.scalar_one_or_none()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cryptographic asset '{asset_id}' not found",
        )

    assessment, factors, recommendations = QuantumRiskEngine.assess_asset(asset)

    db.add(assessment)
    await db.flush()

    for f in factors:
        f.risk_assessment_id = assessment.id
        db.add(f)

    for r in recommendations:
        r.risk_assessment_id = assessment.id
        db.add(r)

    await db.commit()
    await db.refresh(assessment)

    return RiskAssessmentResponse.model_validate(assessment)


@router.get(
    "/risk-assessments",
    response_model=RiskAssessmentListResponse,
    summary="List Risk Assessments",
    description="List historical quantum risk assessments with category filtering.",
)
async def list_risk_assessments(
    db: Annotated[AsyncSession, Depends(get_db)],
    risk_category: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> RiskAssessmentListResponse:
    """List risk assessments."""
    stmt = select(RiskAssessment)
    count_stmt = select(func.count(RiskAssessment.id))

    if risk_category:
        stmt = stmt.where(RiskAssessment.risk_category == risk_category)
        count_stmt = count_stmt.where(RiskAssessment.risk_category == risk_category)

    stmt = stmt.order_by(RiskAssessment.assessed_at.desc()).limit(limit).offset(offset)

    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    assessments_res = await db.execute(stmt)
    assessments = list(assessments_res.scalars().all())

    return RiskAssessmentListResponse(
        assessments=[RiskAssessmentResponse.model_validate(a) for a in assessments],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/risk-assessments/{assessment_id}",
    response_model=RiskAssessmentResponse,
    summary="Get Risk Assessment Details",
    description="Retrieve complete assessment report with contributing factors and recommendations.",
)
async def get_risk_assessment(
    assessment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RiskAssessmentResponse:
    """Get single assessment."""
    stmt = select(RiskAssessment).where(RiskAssessment.id == assessment_id)
    res = await db.execute(stmt)
    assessment = res.scalar_one_or_none()
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Risk assessment '{assessment_id}' not found",
        )
    return RiskAssessmentResponse.model_validate(assessment)


@router.get(
    "/risk-assessments/{assessment_id}/export/json",
    summary="Export Risk Assessment (JSON)",
    description="Export complete assessment report and recommendations in structured JSON format.",
)
async def export_risk_assessment_json(
    assessment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Export assessment as JSON."""
    stmt = select(RiskAssessment).where(RiskAssessment.id == assessment_id)
    res = await db.execute(stmt)
    assessment = res.scalar_one_or_none()
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Risk assessment '{assessment_id}' not found",
        )
    return export_assessment_json(
        assessment=assessment,
        asset=assessment.asset,
        factors=assessment.factors,
        recommendations=assessment.recommendations,
    )


@router.get(
    "/risk-assessments/{assessment_id}/export/markdown",
    summary="Export Risk Assessment (Markdown)",
    description="Export human-readable executive Markdown assessment report.",
)
async def export_risk_assessment_markdown(
    assessment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Export assessment as Markdown."""
    stmt = select(RiskAssessment).where(RiskAssessment.id == assessment_id)
    res = await db.execute(stmt)
    assessment = res.scalar_one_or_none()
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Risk assessment '{assessment_id}' not found",
        )
    md_content = export_assessment_markdown(
        assessment=assessment,
        asset=assessment.asset,
        factors=assessment.factors,
        recommendations=assessment.recommendations,
    )
    return Response(
        content=md_content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="assessment_{assessment_id}.md"'},
    )
