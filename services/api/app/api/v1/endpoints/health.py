"""Quantum Flow Technologies — Health Check Endpoints.

Implements /health/live (liveness) and /health/ready (readiness).
"""

from fastapi import APIRouter, Response, status

from services.api.app.core.config import settings
from services.api.app.core.redis import check_redis_health
from services.api.app.db.session import check_database_health
from services.api.app.schemas.health import (
    DependencyStatus,
    HealthLiveResponse,
    HealthReadyResponse,
)

router = APIRouter(tags=["Health & Diagnostics"])


@router.get(
    "/health/live",
    response_model=HealthLiveResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Liveness Probe",
    description="Returns 200 OK if the FastAPI process is running and accepting HTTP requests.",
)
async def get_live_health() -> HealthLiveResponse:
    """Check process liveness."""
    return HealthLiveResponse(
        status="alive",
        version=settings.app_version,
        service=settings.app_name,
    )


@router.get(
    "/health/ready",
    response_model=HealthReadyResponse,
    responses={
        status.HTTP_200_OK: {"description": "All required backing dependencies are healthy."},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "One or more critical dependencies are unreachable or degraded."
        },
    },
    summary="Service Readiness Probe",
    description=(
        "Verifies connectivity to PostgreSQL and Redis. "
        "Returns 200 OK when ready; 503 Service Unavailable if any required dependency fails."
    ),
)
async def get_ready_health(response: Response) -> HealthReadyResponse:
    """Check readiness of dependencies."""
    db_healthy, db_detail = await check_database_health()
    redis_healthy, redis_detail = await check_redis_health()

    dependencies = {
        "database": DependencyStatus(
            status="connected" if db_healthy else "disconnected",
            detail=db_detail,
        ),
        "redis": DependencyStatus(
            status="connected" if redis_healthy else "disconnected",
            detail=redis_detail,
        ),
    }

    all_healthy = db_healthy and redis_healthy
    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthReadyResponse(
        status="ready" if all_healthy else "not_ready",
        version=settings.app_version,
        dependencies=dependencies,
    )
