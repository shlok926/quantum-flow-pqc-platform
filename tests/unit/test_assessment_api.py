"""Quantum Flow Technologies — Assessment API Unit & Schema Tests.

Validates Pydantic v2 schemas, request validation rules, pagination bounds,
and HTTP status code mappings for the Assessment REST API.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from services.api.app.schemas.assessment import (
    AssessmentCancelRequest,
    AssessmentCreateRequest,
    AssessmentReportResponse,
)
from services.api.app.services.assessment_service import (
    AssessmentNotFoundError,
    DuplicateActiveAssessmentError,
    InvalidLifecycleTransitionError,
    MaxRetriesExceededError,
    TargetNotEligibleError,
)


class TestAssessmentSchemas:
    """Validate Pydantic v2 schema constraints and defaults."""

    def test_assessment_create_request_valid(self) -> None:
        """Valid create payload succeeds with defaults."""
        req = AssessmentCreateRequest(
            title="Production PQC Discovery",
            target_id=uuid.uuid4(),
            discovery_sources=["network_tls", "static_source"],
        )
        assert req.title == "Production PQC Discovery"
        assert req.discovery_sources == ["network_tls", "static_source"]
        assert req.input_payload == {}
        assert req.extra_params == {}

    def test_assessment_create_request_missing_title(self) -> None:
        """Missing title raises validation error."""
        with pytest.raises(ValidationError):
            AssessmentCreateRequest(discovery_sources=["network_tls"])  # type: ignore[call-arg]

    def test_assessment_create_request_empty_title(self) -> None:
        """Empty title raises validation error."""
        with pytest.raises(ValidationError):
            AssessmentCreateRequest(title="")

    def test_assessment_cancel_request_default(self) -> None:
        """Cancel request has sensible default reason."""
        req = AssessmentCancelRequest()
        assert req.reason == "User cancellation"

    def test_assessment_cancel_request_custom(self) -> None:
        """Custom reason accepted within bounds."""
        req = AssessmentCancelRequest(reason="Maintenance window expired")
        assert req.reason == "Maintenance window expired"

    def test_assessment_cancel_request_too_long(self) -> None:
        """Exceeding 500 chars in cancel reason fails validation."""
        with pytest.raises(ValidationError):
            AssessmentCancelRequest(reason="x" * 501)

    def test_assessment_report_response_serialization(self) -> None:
        """Report response validates required fields and types."""
        rep = AssessmentReportResponse(
            assessment_id=uuid.uuid4(),
            status="completed",
            methodology_version="QFT-RISK-v1.0",
            engine_version="v1.0.0",
            report_snapshot={"test": "data"},
            report_snapshot_hash="abc123hash",
            is_hash_verified=True,
            is_immutable=True,
            completed_at=None,
        )
        assert rep.status == "completed"
        assert rep.is_hash_verified is True
        assert rep.is_immutable is True


@pytest.mark.asyncio
class TestAssessmentEndpointRouting:
    """Validate HTTP route status codes, headers, and error mappings."""

    async def test_create_assessment_success(self, async_client: AsyncClient) -> None:
        """POST /assessments returns 201 Created and Location header."""
        test_id = uuid.uuid4()
        now = datetime.now(UTC)
        mock_assessment = MagicMock()
        mock_assessment.id = test_id
        mock_assessment.title = "Test Run"
        mock_assessment.target_id = None
        mock_assessment.target_snapshot = {}
        mock_assessment.scope_hash = "dummyhash"
        mock_assessment.status = "queued"
        mock_assessment.progress_stage = "DISPATCHING_COLLECTORS"
        mock_assessment.progress_percent = 10
        mock_assessment.discovery_sources = ["network_tls"]
        mock_assessment.collector_results = {}
        mock_assessment.coverage_summary = {}
        mock_assessment.asset_counts = {}
        mock_assessment.risk_summary = {}
        mock_assessment.methodology_version = "QFT-RISK-v1.0"
        mock_assessment.engine_version = "v1.0.0"
        mock_assessment.error_summary = None
        mock_assessment.report_snapshot_hash = None
        mock_assessment.started_at = None
        mock_assessment.completed_at = None
        mock_assessment.created_at = now
        mock_assessment.updated_at = now

        with patch(
            "services.api.app.services.assessment_service.AssessmentService.create_and_enqueue_assessment",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = (mock_assessment, [])
            resp = await async_client.post(
                "/api/v1/assessments",
                json={"title": "Test Run", "discovery_sources": ["network_tls"]},
            )

        assert resp.status_code == 201
        assert resp.headers.get("Location") == f"/api/v1/assessments/{test_id}"
        data = resp.json()
        assert data["title"] == "Test Run"
        assert data["status"] == "queued"

    async def test_create_assessment_ineligible_target_400(self, async_client: AsyncClient) -> None:
        """POST /assessments with ineligible target returns 400 Bad Request."""
        target_uuid = str(uuid.uuid4())
        with patch(
            "services.api.app.services.assessment_service.AssessmentService.create_and_enqueue_assessment",
            side_effect=TargetNotEligibleError("Target is not verified"),
        ):
            resp = await async_client.post(
                "/api/v1/assessments",
                json={
                    "title": "Ineligible Test",
                    "target_id": target_uuid,
                    "discovery_sources": ["network_tls"],
                },
            )
        assert resp.status_code == 400
        assert "not verified" in resp.json()["error"]["message"]

    async def test_create_assessment_duplicate_scope_409(self, async_client: AsyncClient) -> None:
        """POST /assessments with duplicate active scope returns 409 Conflict."""
        with patch(
            "services.api.app.services.assessment_service.AssessmentService.create_and_enqueue_assessment",
            side_effect=DuplicateActiveAssessmentError("Active assessment already exists"),
        ):
            resp = await async_client.post(
                "/api/v1/assessments",
                json={"title": "Duplicate Test", "discovery_sources": ["network_tls"]},
            )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["error"]["message"]

    async def test_create_assessment_nonexistent_target_404(
        self, async_client: AsyncClient
    ) -> None:
        """POST /assessments with nonexistent target returns 404 Not Found."""
        target_uuid = str(uuid.uuid4())
        with patch(
            "services.api.app.services.assessment_service.AssessmentService.create_and_enqueue_assessment",
            side_effect=AssessmentNotFoundError("Target not found"),
        ):
            resp = await async_client.post(
                "/api/v1/assessments",
                json={
                    "title": "Missing Target Test",
                    "target_id": target_uuid,
                    "discovery_sources": ["network_tls"],
                },
            )
        assert resp.status_code == 404
        assert "Target not found" in resp.json()["error"]["message"]

    async def test_get_assessment_not_found_404(self, async_client: AsyncClient) -> None:
        """GET /assessments/{id} with missing UUID returns 404."""
        missing_id = uuid.uuid4()
        with patch(
            "services.api.app.services.assessment_service.AssessmentService.get_assessment",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await async_client.get(f"/api/v1/assessments/{missing_id}")
        assert resp.status_code == 404

    async def test_cancel_terminal_assessment_400(self, async_client: AsyncClient) -> None:
        """POST /assessments/{id}/cancel on completed assessment returns 400."""
        test_id = uuid.uuid4()
        mock_a = MagicMock()
        mock_a.target_snapshot = {}

        with (
            patch(
                "services.api.app.services.assessment_service.AssessmentService.get_assessment",
                new_callable=AsyncMock,
                return_value=mock_a,
            ),
            patch(
                "services.api.app.services.assessment_service.AssessmentService.cancel_assessment",
                side_effect=InvalidLifecycleTransitionError("Cannot cancel completed"),
            ),
        ):
            resp = await async_client.post(
                f"/api/v1/assessments/{test_id}/cancel",
                json={"reason": "Operator stop"},
            )
        assert resp.status_code == 400
        assert "Cannot cancel completed" in resp.json()["error"]["message"]

    async def test_retry_max_retries_exceeded_400(self, async_client: AsyncClient) -> None:
        """POST /assessments/{id}/retry when max retries exceeded returns 400."""
        test_id = uuid.uuid4()
        mock_a = MagicMock()
        mock_a.target_snapshot = {}

        with (
            patch(
                "services.api.app.services.assessment_service.AssessmentService.get_assessment",
                new_callable=AsyncMock,
                return_value=mock_a,
            ),
            patch(
                "services.api.app.services.assessment_service.AssessmentService.retry_assessment",
                side_effect=MaxRetriesExceededError("Maximum retries (3) reached"),
            ),
        ):
            resp = await async_client.post(f"/api/v1/assessments/{test_id}/retry")
        assert resp.status_code == 400
        assert "Maximum retries" in resp.json()["error"]["message"]

    async def test_get_report_active_assessment_409(self, async_client: AsyncClient) -> None:
        """GET /assessments/{id}/report while assessment is active returns 409 Conflict."""
        test_id = uuid.uuid4()
        mock_a = MagicMock()
        mock_a.target_snapshot = {}
        mock_a.is_terminal = MagicMock(return_value=False)
        mock_a.report_snapshot = None
        mock_a.report_snapshot_hash = None

        with patch(
            "services.api.app.services.assessment_service.AssessmentService.get_assessment",
            new_callable=AsyncMock,
            return_value=mock_a,
        ):
            resp = await async_client.get(f"/api/v1/assessments/{test_id}/report")
        assert resp.status_code == 409
        assert "Report snapshot is not available until" in resp.json()["error"]["message"]

    async def test_pagination_bounds_validation(self, async_client: AsyncClient) -> None:
        """Query parameters limit/offset are validated within allowed bounds."""
        # limit < 1 fails 422
        resp = await async_client.get("/api/v1/assessments?limit=0")
        assert resp.status_code == 422

        # limit > 100 fails 422
        resp = await async_client.get("/api/v1/assessments?limit=101")
        assert resp.status_code == 422

        # offset < 0 fails 422
        resp = await async_client.get("/api/v1/assessments?offset=-1")
        assert resp.status_code == 422
