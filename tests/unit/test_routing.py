"""Tests for API routing, metadata endpoints, and error handling foundations."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_openapi_schema_endpoint(async_client: AsyncClient) -> None:
    """Verify that the OpenAPI JSON specification is generated and accessible."""
    response = await async_client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert "Quantum Flow" in data["info"]["title"]
    assert "/health/live" in data["paths"]
    assert "/health/ready" in data["paths"]


@pytest.mark.asyncio
async def test_api_v1_health_routes(async_client: AsyncClient) -> None:
    """Verify that versioned API health endpoints under /api/v1 are registered."""
    response = await async_client.get("/api/v1/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


@pytest.mark.asyncio
async def test_not_found_error_envelope(async_client: AsyncClient) -> None:
    """Verify that non-existent routes return a structured 404 response."""
    response = await async_client.get("/api/v1/non-existent-resource")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "HTTP_404"
