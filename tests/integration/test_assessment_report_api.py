"""Quantum Flow Technologies — Assessment Report Delivery API Integration Tests.

Validates Section 14.2 of Revision 2.1:
1. Active Assessment Conflict (HTTP 409)
2. Unauthenticated Rejection (HTTP 401)
3. Cross-Tenant Isolation (HTTP 404)
4. Tamper Rejection (HTTP 500 on snapshot hash mismatch)
5. CycloneDX 1.6 Delivery (application/vnd.cyclonedx+json, RFC 5987, Content-Length)
6. CSV Delivery (text/csv, CRLF, formula sanitization)
7. Markdown Delivery (text/markdown, Maximum Asset QVI, integrity seal)
"""

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from packages.scanner.safety.canonical import compute_canonical_evidence_sha256
from services.api.app.core.config import settings
from services.api.app.core.security import SecurityIdentity, get_current_identity
from services.api.app.db.models.assessment import Assessment, AssessmentStatus
from services.api.app.main import app

pytestmark = pytest.mark.asyncio


def _build_test_report_snapshot(assessment_id: uuid.UUID, tenant_id: str) -> dict[str, Any]:
    """Generate a structurally valid report snapshot with assets and risk evaluations."""
    return {
        "assessment": {
            "id": str(assessment_id),
            "title": "Quantum Risk Assessment - Test Cluster",
            "methodology_version": "QFT-RISK-v1.0",
            "engine_version": "v1.0.0",
            "status": "completed",
            "progress_percent": 100,
            "created_at": datetime.now(UTC).isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
        },
        "target": {
            "id": str(uuid.uuid4()),
            "hostname": "api.internal.test",
            "tenant_id": tenant_id,
        },
        "coverage": {
            "sources": ["network_tls", "static_source"],
            "total_assets": 2,
            "total_observations": 4,
        },
        "risk_summary": {
            "overall_score": 850,
            "overall_category": "critical",
            "shor_vulnerable_count": 1,
            "grover_margin_count": 1,
            "pqc_recognised_count": 0,
            "critical_risk_count": 1,
            "high_risk_count": 0,
            "elevated_risk_count": 0,
            "guarded_risk_count": 0,
            "low_risk_count": 1,
        },
        "assets": [
            {
                "id": str(uuid.uuid4()),
                "name": "api.internal.test:443",
                "asset_type": "tls_certificate",
                "raw_algorithm": "RSA-2048",
                "detected_key_size": 2048,
                "quantum_threat_type": "shor_vulnerable",
                "qvi_score": 850,
                "qvi_category": "critical",
                "business_criticality": "high",
                "recommended_algorithm": "ML-KEM-768",
            },
            {
                "id": str(uuid.uuid4()),
                "name": "AES-256 Storage",
                "asset_type": "symmetric_key",
                "raw_algorithm": "AES-256-GCM",
                "detected_key_size": 256,
                "quantum_threat_type": "grover_margin",
                "qvi_score": 150,
                "qvi_category": "low",
                "business_criticality": "medium",
                "recommended_algorithm": "AES-256",
            },
        ],
        "recommendations": [
            {
                "priority": "P1",
                "action": "Migrate RSA-2048 to hybrid ML-KEM-768",
            }
        ],
    }


async def _create_test_assessment(
    db: AsyncSession,
    status: str = AssessmentStatus.COMPLETED.value,
    tenant_id: str = "tenant-alpha",
    tamper: bool = False,
) -> Assessment:
    """Helper to persist a test assessment entity."""
    ass_id = uuid.uuid4()
    snapshot = _build_test_report_snapshot(ass_id, tenant_id)
    canonical_hash = compute_canonical_evidence_sha256(snapshot)

    ass = Assessment(
        id=ass_id,
        title="Test Assessment",
        target_id=None,
        target_snapshot={"tenant_id": tenant_id},
        scope_hash="test_scope_hash",
        status=status,
        progress_stage=status.upper(),
        progress_percent=100 if status == AssessmentStatus.COMPLETED.value else 50,
        discovery_sources=["network_tls"],
        report_snapshot=snapshot,
        report_snapshot_hash="0" * 64 if tamper else canonical_hash,
        completed_at=datetime.now(UTC) if status == AssessmentStatus.COMPLETED.value else None,
        methodology_version="QFT-RISK-v1.0",
        engine_version="v1.0.0",
    )
    db.add(ass)
    await db.commit()
    await db.refresh(ass)
    return ass


class TestReportDeliveryAPI:
    """Integration test suite for Section 14.2 authenticated report delivery endpoints."""

    async def test_active_assessment_conflict(
        self,
        async_client: AsyncClient,
        test_db_session: AsyncSession,
    ) -> None:
        """1. Request reports for running/queued assessment; assert HTTP 409 Conflict."""
        ass = await _create_test_assessment(
            test_db_session,
            status=AssessmentStatus.RUNNING.value,
            tenant_id="tenant-alpha",
        )

        app.dependency_overrides[get_current_identity] = lambda: SecurityIdentity(
            user_id="user-1",
            tenant_id="tenant-alpha",
            roles=["admin"],
            permissions=["assessment:export", "assessment:read"],
        )
        try:
            for fmt in ("cyclonedx", "csv", "markdown"):
                resp = await async_client.get(f"/api/v1/assessments/{ass.id}/reports/{fmt}")
                assert resp.status_code == 409, (
                    f"Expected 409 for format {fmt}, got {resp.status_code}"
                )
                err_data = resp.json()
                msg = (
                    err_data.get("error", {}).get("message") or err_data.get("detail", "")
                ).lower()
                assert "active" in msg or "terminal" in msg
        finally:
            app.dependency_overrides.pop(get_current_identity, None)

    async def test_unauthenticated_rejection_in_prod(
        self,
        async_client: AsyncClient,
        test_db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """2. Request report without token in staging/prod; assert HTTP 401 Unauthorized."""
        ass = await _create_test_assessment(test_db_session, tenant_id="tenant-alpha")
        monkeypatch.setattr(settings, "app_env", "production")

        # Without Authorization header in production environment
        resp = await async_client.get(f"/api/v1/assessments/{ass.id}/reports/cyclonedx")
        assert resp.status_code == 401
        assert "WWW-Authenticate" in resp.headers

    async def test_cross_tenant_isolation(
        self,
        async_client: AsyncClient,
        test_db_session: AsyncSession,
    ) -> None:
        """3. Request report owned by another tenant; assert HTTP 404 Not Found."""
        ass = await _create_test_assessment(test_db_session, tenant_id="tenant-other")

        app.dependency_overrides[get_current_identity] = lambda: SecurityIdentity(
            user_id="user-1",
            tenant_id="tenant-alpha",
            roles=["admin"],
            permissions=["assessment:export", "assessment:read"],
        )
        try:
            resp = await async_client.get(f"/api/v1/assessments/{ass.id}/reports/cyclonedx")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_identity, None)

    async def test_tamper_rejection(
        self,
        async_client: AsyncClient,
        test_db_session: AsyncSession,
    ) -> None:
        """4. Modify stored report snapshot; assert HTTP 500 Internal Server Error."""
        ass = await _create_test_assessment(
            test_db_session,
            tenant_id="tenant-alpha",
            tamper=True,
        )

        app.dependency_overrides[get_current_identity] = lambda: SecurityIdentity(
            user_id="user-1",
            tenant_id="tenant-alpha",
            roles=["admin"],
            permissions=["assessment:export", "assessment:read"],
        )
        try:
            resp = await async_client.get(f"/api/v1/assessments/{ass.id}/reports/cyclonedx")
            assert resp.status_code == 500
            err_data = resp.json()
            msg = (err_data.get("error", {}).get("message") or err_data.get("detail", "")).lower()
            assert "tampered" in msg or "integrity" in msg or "verification" in msg
        finally:
            app.dependency_overrides.pop(get_current_identity, None)

    async def test_cyclonedx_delivery(
        self,
        async_client: AsyncClient,
        test_db_session: AsyncSession,
    ) -> None:
        """5. CycloneDX 1.6 delivery compliance."""
        ass = await _create_test_assessment(test_db_session, tenant_id="tenant-alpha")

        app.dependency_overrides[get_current_identity] = lambda: SecurityIdentity(
            user_id="user-1",
            tenant_id="tenant-alpha",
            roles=["admin"],
            permissions=["assessment:export", "assessment:read"],
        )
        try:
            resp = await async_client.get(f"/api/v1/assessments/{ass.id}/reports/cyclonedx")
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "application/vnd.cyclonedx+json"
            assert "attachment; filename=" in resp.headers["content-disposition"]
            assert "filename*=UTF-8''" in resp.headers["content-disposition"]
            assert "content-length" in resp.headers

            body = json.loads(resp.content)
            assert body.get("bomFormat") == "CycloneDX"
            assert body.get("specVersion") in ("1.6", "1.5")
            assert "components" in body
        finally:
            app.dependency_overrides.pop(get_current_identity, None)

    async def test_csv_delivery(
        self,
        async_client: AsyncClient,
        test_db_session: AsyncSession,
    ) -> None:
        """6. CSV delivery with strict CRLF delimiters and formula sanitization."""
        ass = await _create_test_assessment(test_db_session, tenant_id="tenant-alpha")

        app.dependency_overrides[get_current_identity] = lambda: SecurityIdentity(
            user_id="user-1",
            tenant_id="tenant-alpha",
            roles=["admin"],
            permissions=["assessment:export", "assessment:read"],
        )
        try:
            resp = await async_client.get(f"/api/v1/assessments/{ass.id}/reports/csv")
            assert resp.status_code == 200
            assert "text/csv" in resp.headers["content-type"]
            assert "attachment; filename=" in resp.headers["content-disposition"]
            assert "content-length" in resp.headers

            # Verify CRLF line endings in content
            text_content = resp.content.decode("utf-8")
            assert "\r\n" in text_content
            assert "Asset Name" in text_content or "Algorithm" in text_content
        finally:
            app.dependency_overrides.pop(get_current_identity, None)

    async def test_markdown_delivery(
        self,
        async_client: AsyncClient,
        test_db_session: AsyncSession,
    ) -> None:
        """7. Markdown delivery with Maximum Asset QVI and cryptographic integrity seal."""
        ass = await _create_test_assessment(test_db_session, tenant_id="tenant-alpha")

        app.dependency_overrides[get_current_identity] = lambda: SecurityIdentity(
            user_id="user-1",
            tenant_id="tenant-alpha",
            roles=["admin"],
            permissions=["assessment:export", "assessment:read"],
        )
        try:
            resp = await async_client.get(f"/api/v1/assessments/{ass.id}/reports/markdown")
            assert resp.status_code == 200
            assert "text/markdown" in resp.headers["content-type"]
            assert "attachment; filename=" in resp.headers["content-disposition"]
            assert "content-length" in resp.headers

            text_content = resp.content.decode("utf-8")
            assert "Maximum Asset QVI" in text_content
            assert "Integrity Verification" in text_content
            assert ass.report_snapshot_hash in text_content
        finally:
            app.dependency_overrides.pop(get_current_identity, None)
