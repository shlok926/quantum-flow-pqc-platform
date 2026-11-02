"""Quantum Flow Technologies — API v1 Router Aggregator."""

from fastapi import APIRouter

from services.api.app.api.v1.endpoints import health

api_v1_router = APIRouter()

# Include health routes also under /api/v1 for API clients
api_v1_router.include_router(health.router)
