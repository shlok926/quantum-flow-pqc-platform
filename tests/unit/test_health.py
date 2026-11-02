"""Tests for /health/live and /health/ready diagnostic endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_live_endpoint(async_client: AsyncClient) -> None:
    """Verify that /health/live returns HTTP 200 and alive payload."""
    response = await async_client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "version" in data
    assert data["service"] == "quantum-flow-pqc-platform"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_ready_all_healthy(async_client: AsyncClient) -> None:
    """Verify that /health/ready returns HTTP 200 when all dependencies are healthy."""
    with (
        patch(
            "services.api.app.api.v1.endpoints.health.check_database_health",
            new_callable=AsyncMock,
        ) as mock_db,
        patch(
            "services.api.app.api.v1.endpoints.health.check_redis_health",
            new_callable=AsyncMock,
        ) as mock_redis,
    ):
        mock_db.return_value = (True, "connected")
        mock_redis.return_value = (True, "connected")

        response = await async_client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["dependencies"]["database"]["status"] == "connected"
        assert data["dependencies"]["redis"]["status"] == "connected"


@pytest.mark.asyncio
async def test_health_ready_database_degraded(async_client: AsyncClient) -> None:
    """Verify that /health/ready returns HTTP 503 when the database is unreachable."""
    with (
        patch(
            "services.api.app.api.v1.endpoints.health.check_database_health",
            new_callable=AsyncMock,
        ) as mock_db,
        patch(
            "services.api.app.api.v1.endpoints.health.check_redis_health",
            new_callable=AsyncMock,
        ) as mock_redis,
    ):
        mock_db.return_value = (False, "connection refused")
        mock_redis.return_value = (True, "connected")

        response = await async_client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["dependencies"]["database"]["status"] == "disconnected"
        assert "connection refused" in data["dependencies"]["database"]["detail"]
        assert data["dependencies"]["redis"]["status"] == "connected"


@pytest.mark.asyncio
async def test_health_ready_redis_degraded(async_client: AsyncClient) -> None:
    """Verify that /health/ready returns HTTP 503 when Redis is unreachable."""
    with (
        patch(
            "services.api.app.api.v1.endpoints.health.check_database_health",
            new_callable=AsyncMock,
        ) as mock_db,
        patch(
            "services.api.app.api.v1.endpoints.health.check_redis_health",
            new_callable=AsyncMock,
        ) as mock_redis,
    ):
        mock_db.return_value = (True, "connected")
        mock_redis.return_value = (False, "redis timeout")

        response = await async_client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["dependencies"]["database"]["status"] == "connected"
        assert data["dependencies"]["redis"]["status"] == "disconnected"


@pytest.mark.asyncio
async def test_check_database_health_sanitized_failure() -> None:
    """Verify that database connection failures do not leak connection strings or secrets."""
    from services.api.app.db.session import check_database_health

    with patch("services.api.app.db.session.get_async_engine") as mock_engine:
        mock_engine.side_effect = Exception(
            "postgresql+asyncpg://admin:super_secret_password@db.internal:5432/secrets"
        )
        healthy, detail = await check_database_health()
        assert healthy is False
        assert "super_secret_password" not in detail
        assert "db.internal" not in detail
        assert detail == "Database connection unavailable"


@pytest.mark.asyncio
async def test_check_redis_health_sanitized_failure() -> None:
    """Verify that Redis connection failures do not leak connection URLs or credentials."""
    from services.api.app.core.redis import check_redis_health

    with patch("services.api.app.core.redis.from_url") as mock_redis:
        mock_redis.side_effect = Exception(
            "redis://default:sensitive_auth_token@redis.internal:6379/0"
        )
        healthy, detail = await check_redis_health()
        assert healthy is False
        assert "sensitive_auth_token" not in detail
        assert "redis.internal" not in detail
        assert detail == "Redis connection unavailable"


@pytest.mark.asyncio
async def test_check_database_health_sanitized_failure() -> None:
    """Verify that database connection failures do not leak connection strings or secrets."""
    from services.api.app.db.session import check_database_health

    with patch("services.api.app.db.session.get_async_engine") as mock_engine:
        mock_engine.side_effect = Exception(
            "postgresql+asyncpg://admin:super_secret_password@db.internal:5432/secrets"
        )
        healthy, detail = await check_database_health()
        assert healthy is False
        assert "super_secret_password" not in detail
        assert "db.internal" not in detail
        assert detail == "Database connection unavailable"


@pytest.mark.asyncio
async def test_check_redis_health_sanitized_failure() -> None:
    """Verify that Redis connection failures do not leak connection URLs or credentials."""
    from services.api.app.core.redis import check_redis_health

    with patch("services.api.app.core.redis.from_url") as mock_redis:
        mock_redis.side_effect = Exception(
            "redis://default:sensitive_auth_token@redis.internal:6379/0"
        )
        healthy, detail = await check_redis_health()
        assert healthy is False
        assert "sensitive_auth_token" not in detail
        assert "redis.internal" not in detail
        assert detail == "Redis connection unavailable"

