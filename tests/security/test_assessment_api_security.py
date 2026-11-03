"""Quantum Flow Technologies — Assessment Security, Authentication & Tenant Boundary Tests.

Validates fail-closed authentication in production/staging environments,
multi-tenant boundary enforcement, RFC 5737 target eligibility guards,
and terminal report snapshot database trigger immutability.
"""

import os
import socket
import uuid
from collections.abc import AsyncGenerator
from typing import Any, cast
from urllib.parse import urlparse

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from services.api.app.core.config import settings
from services.api.app.db.models.assessment import Assessment, AssessmentStatus
from services.api.app.db.models.target import AuthorisationStatus, Target, TargetStatus
from services.api.app.db.session import get_db
from services.api.app.main import app

PG_ASYNC_URL = os.getenv(
    "DATABASE_URL_ASYNC",
    "postgresql+asyncpg://quantumflow:quantumflow_secret_dev@localhost:5434/quantumflow_db",
)


def _is_db_reachable(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 5432
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except Exception:
        return False


@pytest.fixture(scope="module", autouse=True)
def require_postgres() -> None:
    if not _is_db_reachable(PG_ASYNC_URL):
        pytest.skip("PostgreSQL async test database is not available on port 5434")


@pytest_asyncio.fixture
async def pg_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create async engine connected to PostgreSQL 16 database."""
    engine = create_async_engine(
        PG_ASYNC_URL,
        pool_pre_ping=True,
        echo=False,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def pg_session_maker(pg_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create session maker bound to PostgreSQL 16."""
    return async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def pg_client(
    pg_session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncClient, None]:
    """Provide AsyncClient wired to PostgreSQL 16."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with pg_session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=cast(Any, app))
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def security_target(
    pg_session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[Target, None]:
    """Seed target domain for security testing."""
    target_id = uuid.uuid4()
    hostname = f"security-{uuid.uuid4().hex[:8]}.quantumflow.internal"

    async with pg_session_maker() as session:
        target = Target(
            id=target_id,
            hostname=hostname,
            display_name="Security Audit Target",
            status=TargetStatus.VERIFIED.value,
            authorisation_status=AuthorisationStatus.CONFIRMED.value,
            verification_token=f"qf-verify={uuid.uuid4()}",
        )
        session.add(target)
        await session.commit()

    yield target

    async with pg_session_maker() as session:
        # Cascade cleanup
        await session.execute(
            text(
                "DELETE FROM assessment_observations WHERE assessment_id IN (SELECT id FROM assessments WHERE target_id = :id)"
            ),
            {"id": target_id},
        )
        await session.execute(
            text(
                "DELETE FROM assessment_assets WHERE assessment_id IN (SELECT id FROM assessments WHERE target_id = :id)"
            ),
            {"id": target_id},
        )
        await session.execute(
            text(
                "DELETE FROM risk_assessments WHERE assessment_id IN (SELECT id FROM assessments WHERE target_id = :id)"
            ),
            {"id": target_id},
        )
        await session.execute(
            text("DELETE FROM discovery_jobs WHERE target_id = :id"),
            {"id": target_id},
        )
        await session.execute(
            text("DELETE FROM assessments WHERE target_id = :id"),
            {"id": target_id},
        )
        await session.execute(
            text("DELETE FROM observations WHERE target_id = :id"),
            {"id": target_id},
        )
        await session.execute(
            text("DELETE FROM targets WHERE id = :id"),
            {"id": target_id},
        )
        await session.commit()


@pytest.mark.asyncio
class TestAssessmentSecurity:
    """Validate security defenses, authentication fail-closed, tenant boundaries, and immutability."""

    async def test_fail_closed_authentication_in_production(
        self,
        pg_client: AsyncClient,
    ) -> None:
        """Production environment strictly rejects unauthenticated or invalid credential requests."""
        orig_env = settings.app_env
        try:
            settings.app_env = "production"

            # 1. Missing Authorization header returns 401
            resp_no_auth = await pg_client.post(
                "/api/v1/assessments",
                json={"title": "Prod Attack Run", "discovery_sources": ["network_tls"]},
            )
            assert resp_no_auth.status_code == 401
            assert "Authentication required" in resp_no_auth.json()["error"]["message"]

            # 2. Invalid Bearer Token returns 401
            resp_bad_jwt = await pg_client.get(
                "/api/v1/assessments",
                headers={"Authorization": "Bearer invalid_forged_token_xyz"},
            )
            assert resp_bad_jwt.status_code == 401
            assert "Invalid or expired" in resp_bad_jwt.json()["error"]["message"]

            # 3. Invalid API Key returns 401
            resp_bad_key = await pg_client.get(
                "/api/v1/assessments",
                headers={"X-API-Key": "untrusted_live_key"},
            )
            assert resp_bad_key.status_code == 401
            assert "Invalid or revoked" in resp_bad_key.json()["error"]["message"]
        finally:
            settings.app_env = orig_env

    async def test_tenant_isolation_boundary_enforcement(
        self,
        pg_client: AsyncClient,
        security_target: Target,
    ) -> None:
        """Tenant A assessment cannot be accessed, listed, or mutated by Tenant B (fails 404)."""
        # Create assessment for Tenant A
        tenant_a_headers = {
            "Authorization": "Bearer qf_token_tenant-alpha_analyst-1",
            "X-Tenant-Id": "tenant-alpha",
        }
        create_resp = await pg_client.post(
            "/api/v1/assessments",
            headers=tenant_a_headers,
            json={
                "title": "Tenant Alpha Restricted Assessment",
                "target_id": str(security_target.id),
                "discovery_sources": ["network_tls"],
                "extra_params": {"tenant": "tenant-alpha"},
            },
        )
        assert create_resp.status_code == 201
        assessment_id = create_resp.json()["id"]

        # Tenant B attempts to read or mutate Tenant A's assessment
        tenant_b_headers = {
            "Authorization": "Bearer qf_token_tenant-bravo_analyst-2",
            "X-Tenant-Id": "tenant-bravo",
        }

        # 1. Detail lookup returns 404
        get_b = await pg_client.get(
            f"/api/v1/assessments/{assessment_id}", headers=tenant_b_headers
        )
        assert get_b.status_code == 404

        # 2. Cancel attempt returns 404
        cancel_b = await pg_client.post(
            f"/api/v1/assessments/{assessment_id}/cancel",
            headers=tenant_b_headers,
            json={"reason": "Malicious cancel"},
        )
        assert cancel_b.status_code == 404

        # 3. Retry attempt returns 404
        retry_b = await pg_client.post(
            f"/api/v1/assessments/{assessment_id}/retry",
            headers=tenant_b_headers,
        )
        assert retry_b.status_code == 404

        # 4. Jobs list returns 404
        jobs_b = await pg_client.get(
            f"/api/v1/assessments/{assessment_id}/jobs",
            headers=tenant_b_headers,
        )
        assert jobs_b.status_code == 404

        # 5. List query for Tenant B does NOT include Tenant A's assessment
        list_b = await pg_client.get("/api/v1/assessments", headers=tenant_b_headers)
        assert list_b.status_code == 200
        items_b = list_b.json()["items"]
        assert not any(item["id"] == assessment_id for item in items_b)

    async def test_target_scan_eligibility_enforcement(
        self,
        pg_client: AsyncClient,
        pg_session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        """Target with unconfirmed authorization status is rejected for network TLS discovery."""
        unauth_target_id = uuid.uuid4()
        async with pg_session_maker() as session:
            target = Target(
                id=unauth_target_id,
                hostname=f"unauth-{uuid.uuid4().hex[:8]}.internal",
                status=TargetStatus.PENDING_VERIFICATION.value,
                authorisation_status=AuthorisationStatus.PENDING.value,
                verification_token=f"qf-verify={uuid.uuid4()}",
            )
            session.add(target)
            await session.commit()

        try:
            resp = await pg_client.post(
                "/api/v1/assessments",
                json={
                    "title": "Unauthorized Scan Attempt",
                    "target_id": str(unauth_target_id),
                    "discovery_sources": ["network_tls"],
                },
            )
            assert resp.status_code == 400
            assert "not eligible for active scan" in resp.json()["error"]["message"]
        finally:
            async with pg_session_maker() as session:
                await session.execute(
                    text("DELETE FROM targets WHERE id = :id"), {"id": unauth_target_id}
                )
                await session.commit()

    async def test_database_trigger_immutability_enforcement(
        self,
        pg_session_maker: async_sessionmaker[AsyncSession],
        security_target: Target,
    ) -> None:
        """PostgreSQL trigger trg_protect_terminal_assessment_snapshot rejects SQL tampering."""
        assessment_id = uuid.uuid4()
        async with pg_session_maker() as session:
            assessment = Assessment(
                id=assessment_id,
                title="Trigger Defense Target Assessment",
                target_id=security_target.id,
                target_snapshot={"hostname": security_target.hostname},
                scope_hash="hash-immutable-trigger-test",
                status=AssessmentStatus.COMPLETED.value,
                progress_stage="COMPLETED",
                progress_percent=100,
                discovery_sources=["network_tls"],
                report_snapshot={"qvi": 950, "status": "COMPLETED"},
                report_snapshot_hash="5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",
            )
            session.add(assessment)
            await session.commit()

        # Attempt to tamper with the terminal report snapshot via direct SQL
        async with pg_session_maker() as session:
            with pytest.raises(DBAPIError) as exc_info:
                await session.execute(
                    text("UPDATE assessments SET report_snapshot = :forged WHERE id = :id"),
                    {
                        "forged": '{"qvi": 0, "status": "TAMPERED"}',
                        "id": assessment_id,
                    },
                )
                await session.commit()

            assert "Terminal assessment report snapshot and canonical hash are immutable" in str(
                exc_info.value
            )
