"""Quantum Flow Technologies — Observation Query Endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.db.models.observation import Observation
from services.api.app.db.models.target import Target
from services.api.app.db.session import get_db
from services.api.app.schemas.observation import (
    ObservationListResponse,
    ObservationResponse,
)

router = APIRouter(tags=["Observations"])


@router.get(
    "/targets/{target_id}/observations",
    response_model=ObservationListResponse,
    summary="Get observations for a target",
)
async def list_target_observations(
    target_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ObservationListResponse:
    """Retrieve all persistent cryptographic observations associated with a target."""
    target = await db.scalar(select(Target).where(Target.id == target_id))
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target with ID '{target_id}' was not found",
        )

    observations = (
        await db.scalars(
            select(Observation)
            .where(Observation.target_id == target_id)
            .order_by(Observation.observed_at.desc())
        )
    ).all()

    return ObservationListResponse(
        items=[ObservationResponse.model_validate(o) for o in observations],
        total=len(observations),
    )


@router.get(
    "/observations/{observation_id}",
    response_model=ObservationResponse,
    summary="Get single observation by ID",
)
async def get_observation(
    observation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Observation:
    """Retrieve a single cryptographic observation."""
    obs = await db.scalar(select(Observation).where(Observation.id == observation_id))
    if obs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation with ID '{observation_id}' was not found",
        )
    return obs
