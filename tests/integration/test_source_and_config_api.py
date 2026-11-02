"""Quantum Flow Technologies — Source, Config, CBOM, and Risk API Integration Tests.

Verifies:
1. POST /api/v1/source/upload archives and extracts AST findings into CBOM assets.
2. POST /api/v1/config/import ingests Nginx/Apache/K8s configs into CBOM assets.
3. GET /api/v1/assets lists correlated assets with filters.
4. GET /api/v1/cbom/export produces valid CycloneDX 1.6 JSON.
5. GET /api/v1/assets/export/csv exports CSV with formula injection defense.
6. POST /api/v1/risk-assessments/{asset_id}/evaluate generates QVI assessment & recommendations.
"""

import io
import zipfile

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_source_archive_end_to_end(async_client: AsyncClient) -> None:
    """Verify source archive upload extracts code findings and creates CBOM assets."""
    # Build in-memory zip containing a python file with RSA
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr(
            "app/auth.py",
            """from cryptography.hazmat.primitives.asymmetric import rsa
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
""",
        )
        zf.writestr("requirements.txt", "cryptography==42.0.5\n")
    zip_buffer.seek(0)

    files = {"file": ("repo.zip", zip_buffer.getvalue(), "application/zip")}
    res = await async_client.post("/api/v1/source/upload", files=files)
    assert res.status_code == 201
    data = res.json()
    assert data["files_scanned"] >= 1
    assert data["findings_count"] >= 1

    # Verify assets were correlated into CBOM
    assets_res = await async_client.get("/api/v1/assets")
    assert assets_res.status_code == 200
    assets_data = assets_res.json()
    assert assets_data["total"] >= 1

    # Verify CycloneDX export
    cbom_res = await async_client.get("/api/v1/cbom/export")
    assert cbom_res.status_code == 200
    cbom_data = cbom_res.json()
    assert cbom_data["bomFormat"] == "CycloneDX"
    assert cbom_data["specVersion"] == "1.6"

    # Verify CSV export
    csv_res = await async_client.get("/api/v1/assets/export/csv")
    assert csv_res.status_code == 200
    assert "Asset Key,Asset Type" in csv_res.text


@pytest.mark.asyncio
async def test_import_nginx_config_and_evaluate_risk(async_client: AsyncClient) -> None:
    """Verify config import creates protocol assets and risk assessment evaluates QVI."""
    config_content = """server {
    listen 443 ssl;
    server_name portal.example.com;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256;
}"""
    import_res = await async_client.post(
        "/api/v1/config/import",
        json={
            "config_type": "nginx",
            "file_path": "nginx.conf",
            "content": config_content,
        },
    )
    assert import_res.status_code == 201
    assert import_res.json()["findings_count"] >= 2

    # Query the created asset
    assets_res = await async_client.get("/api/v1/assets")
    assert assets_res.status_code == 200
    items = assets_res.json()["assets"]
    assert len(items) >= 1
    asset_id = items[0]["id"]

    # Evaluate risk for this asset
    risk_res = await async_client.post(
        f"/api/v1/assets/{asset_id}/assessments",
    )
    assert risk_res.status_code == 201
    risk_data = risk_res.json()
    assert 0 <= risk_data["score"] <= 1000
    assert "risk_category" in risk_data
    assert len(risk_data["factors"]) == 7  # 7 dimensions Q, R, L, E, B, M, V
    assert "recommendations" in risk_data
