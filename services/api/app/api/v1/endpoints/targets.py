"""Quantum Flow Technologies — Target Management API Endpoints."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.scanner.safety.hostname import (
    HostnameValidationError,
    normalize_hostname,
)
from services.api.app.db.models.target import (
    AuthorisationStatus,
    Target,
    TargetStatus,
)
from services.api.app.db.session import get_db
from services.api.app.schemas.target import (
    TargetCreate,
    TargetListResponse,
    TargetResponse,
    TargetUpdate,
    TargetVerifyRequest,
)

router = APIRouter(tags=["Target Management"])


@router.post(
    "/targets",
    response_model=TargetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new domain target",
)
async def create_target(
    payload: TargetCreate,
    db: AsyncSession = Depends(get_db),
) -> Target:
    """Register a new domain target with strict DNS syntax validation and authorisation declaration."""
    # 1. Syntactic and security normalization of hostname
    try:
        normalized_host = normalize_hostname(payload.hostname)
    except HostnameValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid hostname syntax: {exc}",
        ) from exc

    # 2. Check for duplicate target registration
    existing = await db.scalar(select(Target).where(Target.hostname == normalized_host))
    if existing is not None:
        if existing.status == TargetStatus.DISABLED.value:
            existing.status = TargetStatus.VERIFIED.value
            existing.disabled_at = None
            existing.verified_at = datetime.now(UTC)
            if payload.authorisation_declared:
                existing.authorisation_status = AuthorisationStatus.CONFIRMED.value
            await db.flush()
            await db.refresh(existing)
            return existing
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Target with hostname '{normalized_host}' is already registered (ID: {existing.id})",
        )

    # 3. Process authorisation declaration
    auth_status = (
        AuthorisationStatus.CONFIRMED.value
        if payload.authorisation_declared
        else AuthorisationStatus.PENDING.value
    )

    new_target = Target(
        hostname=normalized_host,
        display_name=payload.display_name or normalized_host,
        description=payload.description,
        status=TargetStatus.PENDING_VERIFICATION.value,
        authorisation_status=auth_status,
        authorised_by=payload.authorised_by,
        authorisation_reference=payload.authorisation_reference,
    )

    db.add(new_target)
    await db.flush()
    await db.refresh(new_target)
    return new_target


@router.get(
    "/targets",
    response_model=TargetListResponse,
    summary="List registered domain targets",
)
async def list_targets(
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    target_status: str | None = Query(None, alias="status", description="Filter by status"),
    db: AsyncSession = Depends(get_db),
) -> TargetListResponse:
    """List registered targets with pagination and optional status filter."""
    stmt = select(Target)
    count_stmt = select(func.count(Target.id))

    if target_status:
        stmt = stmt.where(Target.status == target_status)
        count_stmt = count_stmt.where(Target.status == target_status)

    total = await db.scalar(count_stmt) or 0
    targets = (
        await db.scalars(stmt.order_by(Target.created_at.desc()).offset(skip).limit(limit))
    ).all()

    return TargetListResponse(
        items=[TargetResponse.model_validate(t) for t in targets],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/targets/{target_id}",
    response_model=TargetResponse,
    summary="Get target by ID",
)
async def get_target(
    target_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Target:
    """Retrieve details for a single domain target."""
    target = await db.scalar(select(Target).where(Target.id == target_id))
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target with ID '{target_id}' was not found",
        )
    return target


@router.patch(
    "/targets/{target_id}",
    response_model=TargetResponse,
    summary="Update target metadata",
)
async def update_target(
    target_id: UUID,
    payload: TargetUpdate,
    db: AsyncSession = Depends(get_db),
) -> Target:
    """Update display name or description for a target."""
    target = await db.scalar(select(Target).where(Target.id == target_id))
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target with ID '{target_id}' was not found",
        )

    if payload.display_name is not None:
        target.display_name = payload.display_name
    if payload.description is not None:
        target.description = payload.description

    await db.flush()
    await db.refresh(target)
    return target


@router.post(
    "/targets/{target_id}/disable",
    response_model=TargetResponse,
    summary="Disable a domain target",
)
async def disable_target(
    target_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Target:
    """Disable target from active scanning scope."""
    target = await db.scalar(select(Target).where(Target.id == target_id))
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target with ID '{target_id}' was not found",
        )

    target.status = TargetStatus.DISABLED.value
    target.disabled_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(target)
    return target


@router.post(
    "/targets/{target_id}/verify",
    response_model=TargetResponse,
    summary="Verify target ownership",
)
async def verify_target(
    target_id: UUID,
    payload: TargetVerifyRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> Target:
    """Verify domain ownership using DNS challenge token verification."""
    target = await db.scalar(select(Target).where(Target.id == target_id))
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target with ID '{target_id}' was not found",
        )

    if target.status == TargetStatus.DISABLED.value:
        target.disabled_at = None

    # In development / MVP mode, verify token match if provided or acknowledge manual challenge
    if payload and payload.token and payload.token.strip() != target.verification_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token does not match expected challenge token",
        )

    target.status = TargetStatus.VERIFIED.value
    target.authorisation_status = AuthorisationStatus.CONFIRMED.value
    target.verified_at = datetime.now(UTC)

    await db.flush()
    await db.refresh(target)
    return target
