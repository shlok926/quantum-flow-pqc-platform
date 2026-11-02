"""Quantum Flow Technologies — FastAPI Main Application Entry Point.

Sprint 0 Engineering Foundation: Control plane API service with health probes,
versioned routing, environment CORS, and structured error handling.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from services.api.app.api.v1.endpoints.health import router as health_router
from services.api.app.api.v1.router import api_v1_router
from services.api.app.core.config import settings
from services.api.app.core.redis import close_redis_client
from services.api.app.db.session import close_async_engine

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("quantumflow.api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifecycle events manager for the FastAPI application.

    Note: In accordance with architectural rules, database tables are NOT created
    automatically at startup; schema evolution is strictly managed via Alembic migrations.
    """
    logger.info(
        "Starting %s (%s) in '%s' environment",
        settings.app_name,
        settings.app_version,
        settings.app_env,
    )
    yield
    logger.info("Shutting down %s", settings.app_name)
    await close_async_engine()
    await close_redis_client()


app = FastAPI(
    title="Quantum Flow Technologies — PQC Discovery & Risk Assessment API",
    description=(
        "Enterprise platform for continuous cryptographic discovery, "
        "Cryptographic Bill of Materials (CBOM) inventory, and deterministic quantum risk analysis."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ------------------------------------------------------------------------------
# CORS Middleware Configuration (Derived from Environment, Never Wildcard in Prod)
# ------------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------------------
# Standardized Error Handlers (Consistent Error Envelope Foundation)
# ------------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Format Pydantic request validation errors into a standard error envelope."""
    logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "The request payload failed schema validation.",
                "details": exc.errors(),
            },
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Format standard HTTP exceptions into a standard error envelope."""
    detail: Any = exc.detail
    message = detail if isinstance(detail, str) else "An HTTP error occurred."
    details = None if isinstance(detail, str) else detail

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": message,
                "details": details,
            },
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled internal errors and return sanitized 500 responses."""
    logger.exception("Unhandled server exception on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal server error occurred.",
                "details": None,
            },
        },
    )


# ------------------------------------------------------------------------------
# Top-Level Health Probes (Required by Container Orchestrators & Monitoring)
# ------------------------------------------------------------------------------
app.include_router(health_router)

# ------------------------------------------------------------------------------
# Versioned API Routes (/api/v1)
# ------------------------------------------------------------------------------
app.include_router(api_v1_router, prefix=settings.api_v1_prefix)
