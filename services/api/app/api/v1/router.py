"""Quantum Flow Technologies — API v1 Router Aggregator."""

from fastapi import APIRouter

from services.api.app.api.v1.endpoints import (
    assessments,
    assets,
    config,
    health,
    jobs,
    observations,
    risk,
    scans,
    source,
    targets,
)

api_v1_router = APIRouter()

# Register API v1 domain endpoint routers
api_v1_router.include_router(health.router)
api_v1_router.include_router(assessments.router)
api_v1_router.include_router(jobs.router)
api_v1_router.include_router(targets.router)
api_v1_router.include_router(scans.router)
api_v1_router.include_router(observations.router)
api_v1_router.include_router(assets.router)
api_v1_router.include_router(risk.router)
api_v1_router.include_router(source.router)
api_v1_router.include_router(config.router)
