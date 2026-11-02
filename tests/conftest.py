"""Quantum Flow Technologies — Global Test Fixtures and Configuration."""

from collections.abc import AsyncGenerator
from typing import Any, cast

import pytest
from httpx import ASGITransport, AsyncClient

from services.api.app.main import app


@pytest.fixture
def anyio_backend() -> str:
    """Designate anyio backend for async tests."""
    return "asyncio"


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an asynchronous HTTP client bound to the FastAPI application."""
    transport = ASGITransport(app=cast(Any, app))
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
