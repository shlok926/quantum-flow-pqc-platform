"""Integration tests for Target Management REST API endpoints."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_target_success(async_client: AsyncClient) -> None:
    """Verify successful target registration with authorisation declaration."""
    payload = {
        "hostname": "example.com",
        "display_name": "Example Corp Primary",
        "description": "Production edge ingress",
        "authorisation_declared": True,
        "authorised_by": "sec-ops@example.com",
        "authorisation_reference": "SEC-TICKET-1042",
    }
    response = await async_client.post("/api/v1/targets", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["hostname"] == "example.com"
    assert data["display_name"] == "Example Corp Primary"
    assert data["status"] == "pending_verification"
    assert data["authorisation_status"] == "confirmed"
    assert data["authorised_by"] == "sec-ops@example.com"
    assert "qf-verify=" in data["verification_token"]
    assert data["is_eligible_for_scan"] is False


@pytest.mark.asyncio
async def test_register_target_normalizes_hostname(async_client: AsyncClient) -> None:
    """Verify that hostnames are normalized (lowercase, whitespace stripped)."""
    payload = {
        "hostname": "  SUB.Example.ORG.  ",
        "authorisation_declared": True,
    }
    response = await async_client.post("/api/v1/targets", json=payload)
    assert response.status_code == 201
    assert response.json()["hostname"] == "sub.example.org"


@pytest.mark.asyncio
async def test_register_target_invalid_syntax_rejected(async_client: AsyncClient) -> None:
    """Verify rejection of URL schemes, IP literals, and invalid domains."""
    # URL scheme
    res = await async_client.post(
        "/api/v1/targets",
        json={"hostname": "https://example.com", "authorisation_declared": True},
    )
    assert res.status_code == 422

    # IP literal
    res = await async_client.post(
        "/api/v1/targets",
        json={"hostname": "192.0.2.1", "authorisation_declared": True},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_duplicate_target_rejected(async_client: AsyncClient) -> None:
    """Verify that registering an existing domain hostname returns 409 Conflict."""
    payload = {"hostname": "duplicate.org", "authorisation_declared": True}
    res1 = await async_client.post("/api/v1/targets", json=payload)
    assert res1.status_code == 201

    res2 = await async_client.post("/api/v1/targets", json=payload)
    assert res2.status_code == 409
    assert "already registered" in res2.json()["error"]["message"]


@pytest.mark.asyncio
async def test_list_and_get_targets(async_client: AsyncClient) -> None:
    """Verify listing targets with pagination and retrieving by ID."""
    await async_client.post(
        "/api/v1/targets",
        json={"hostname": "target1.net", "authorisation_declared": True},
    )
    res_reg = await async_client.post(
        "/api/v1/targets",
        json={"hostname": "target2.net", "authorisation_declared": True},
    )
    target_id = res_reg.json()["id"]

    # List
    list_res = await async_client.get("/api/v1/targets?limit=10")
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2

    # Get by ID
    get_res = await async_client.get(f"/api/v1/targets/{target_id}")
    assert get_res.status_code == 200
    assert get_res.json()["hostname"] == "target2.net"


@pytest.mark.asyncio
async def test_get_unknown_target_returns_404(async_client: AsyncClient) -> None:
    """Verify that requesting a non-existent UUID returns 404."""
    unknown_id = uuid.uuid4()
    res = await async_client.get(f"/api/v1/targets/{unknown_id}")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_update_target_metadata(async_client: AsyncClient) -> None:
    """Verify updating display name and description."""
    reg = await async_client.post(
        "/api/v1/targets",
        json={"hostname": "update-test.com", "authorisation_declared": True},
    )
    tid = reg.json()["id"]

    patch_res = await async_client.patch(
        f"/api/v1/targets/{tid}",
        json={"display_name": "Updated Name", "description": "New description"},
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["display_name"] == "Updated Name"
    assert data["description"] == "New description"


@pytest.mark.asyncio
async def test_verify_target_flow(async_client: AsyncClient) -> None:
    """Verify the domain ownership verification challenge transition."""
    reg = await async_client.post(
        "/api/v1/targets",
        json={"hostname": "verify-me.com", "authorisation_declared": True},
    )
    tid = reg.json()["id"]
    token = reg.json()["verification_token"]

    # Attempt verification with wrong token
    bad_res = await async_client.post(
        f"/api/v1/targets/{tid}/verify",
        json={"verification_method": "token", "token": "wrong-token"},
    )
    assert bad_res.status_code == 400

    # Verification with correct token
    good_res = await async_client.post(
        f"/api/v1/targets/{tid}/verify",
        json={"verification_method": "token", "token": token},
    )
    assert good_res.status_code == 200
    verified_data = good_res.json()
    assert verified_data["status"] == "verified"
    assert verified_data["verified_at"] is not None
    assert verified_data["is_eligible_for_scan"] is True


@pytest.mark.asyncio
async def test_disable_target_flow(async_client: AsyncClient) -> None:
    """Verify that a target can be disabled and is then ineligible for scanning."""
    reg = await async_client.post(
        "/api/v1/targets",
        json={"hostname": "disable-me.org", "authorisation_declared": True},
    )
    tid = reg.json()["id"]

    dis_res = await async_client.post(f"/api/v1/targets/{tid}/disable")
    assert dis_res.status_code == 200
    data = dis_res.json()
    assert data["status"] == "disabled"
    assert data["is_eligible_for_scan"] is False
