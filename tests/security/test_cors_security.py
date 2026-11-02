"""Tests for CORS security configuration and origin policy enforcement."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cors_preflight_allowed_origin(async_client: AsyncClient) -> None:
    """Verify that authorized origins receive appropriate CORS headers."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    }
    response = await async_client.options("/health/live", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


@pytest.mark.asyncio
async def test_cors_disallows_untrusted_origin(async_client: AsyncClient) -> None:
    """Verify that unauthorized arbitrary origins do not receive allow-origin headers."""
    headers = {
        "Origin": "http://malicious-site.example.com",
        "Access-Control-Request-Method": "GET",
    }
    response = await async_client.options("/health/live", headers=headers)
    # The header should NOT be set for disallowed origins
    assert (
        response.headers.get("access-control-allow-origin") != "http://malicious-site.example.com"
    )
