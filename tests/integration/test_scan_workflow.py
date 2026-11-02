"""Integration tests for discovery scan execution and observation persistence."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from packages.scanner.tls.collector import (
    CertificateEvidence,
    TLSCollectionResult,
    TLSEndpointEvidence,
)


@pytest.mark.asyncio
async def test_scan_ineligible_target_rejected(async_client: AsyncClient) -> None:
    """Verify that an unverified target is strictly rejected from scan initiation."""
    reg = await async_client.post(
        "/api/v1/targets",
        json={"hostname": "ineligible.com", "authorisation_declared": True},
    )
    tid = reg.json()["id"]

    # Target is in 'pending_verification' status
    scan_res = await async_client.post(f"/api/v1/targets/{tid}/scans", json={})
    assert scan_res.status_code == 400
    assert "not eligible for scanning" in scan_res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_successful_scan_persists_observations(async_client: AsyncClient) -> None:
    """Verify end-to-end scan execution, scan record update, and observation persistence."""
    # 1. Register target
    reg = await async_client.post(
        "/api/v1/targets",
        json={"hostname": "eligible-scan.com", "authorisation_declared": True},
    )
    tid = reg.json()["id"]
    token = reg.json()["verification_token"]

    # 2. Verify target
    ver_res = await async_client.post(
        f"/api/v1/targets/{tid}/verify",
        json={"verification_method": "token", "token": token},
    )
    assert ver_res.status_code == 200
    assert ver_res.json()["is_eligible_for_scan"] is True

    # 3. Mock BoundedTLSCollector returning real evidence
    mock_endpoint = TLSEndpointEvidence(
        target_hostname="eligible-scan.com",
        target_ip="93.184.216.34",
        port=443,
        scan_timestamp=datetime.now(UTC),
        collector_version="1.0.0",
        connection_status="connected",
        negotiated_protocol="TLSv1.3",
        negotiated_cipher_name="TLS_AES_256_GCM_SHA384",
        negotiated_cipher_bits=256,
        negotiated_alpn="h2",
        key_exchange_group=None,
        key_exchange_status="unobserved",
    )
    mock_cert = CertificateEvidence(
        subject_dn="CN=eligible-scan.com",
        issuer_dn="CN=DigiCert Global Root G2",
        serial_number_hex="1A2B3C4D5E6F",
        valid_from=datetime.now(UTC),
        valid_to=datetime.now(UTC),
        is_currently_valid=True,
        san_dns_names=["eligible-scan.com", "www.eligible-scan.com"],
        sha256_fingerprint="A" * 64,
        public_key_algorithm="RSA",
        public_key_size_bits=2048,
        elliptic_curve_name=None,
        signature_algorithm="sha256WithRSAEncryption",
    )
    mock_result = TLSCollectionResult(
        success=True,
        target_hostname="eligible-scan.com",
        pinned_ip="93.184.216.34",
        endpoint_evidence=mock_endpoint,
        certificate_evidence=mock_cert,
    )

    with patch(
        "services.api.app.api.v1.endpoints.scans.BoundedTLSCollector.inspect_target",
        return_value=mock_result,
    ):
        # 4. Trigger Scan
        scan_res = await async_client.post(
            f"/api/v1/targets/{tid}/scans",
            json={"scan_type": "tls_handshake"},
        )
        assert scan_res.status_code == 201
        scan_data = scan_res.json()
        assert scan_data["status"] == "completed"
        assert scan_data["target_ip"] == "93.184.216.34"
        scan_id = scan_data["id"]

        # 5. Verify scan is in scan history
        scans_list_res = await async_client.get(f"/api/v1/targets/{tid}/scans")
        assert scans_list_res.status_code == 200
        assert len(scans_list_res.json()["items"]) == 1

        # 6. Verify single scan endpoint
        get_scan_res = await async_client.get(f"/api/v1/scans/{scan_id}")
        assert get_scan_res.status_code == 200
        assert get_scan_res.json()["status"] == "completed"

        # 7. Verify persistent observations
        obs_res = await async_client.get(f"/api/v1/targets/{tid}/observations")
        assert obs_res.status_code == 200
        obs_list = obs_res.json()["items"]
        assert len(obs_list) == 2

        obs_types = {o["observation_type"] for o in obs_list}
        assert "tls_endpoint" in obs_types
        assert "x509_certificate" in obs_types

        endpoint_obs = next(o for o in obs_list if o["observation_type"] == "tls_endpoint")
        assert endpoint_obs["observed_value"]["negotiated_protocol"] == "TLSv1.3"
        assert endpoint_obs["observed_value"]["negotiated_cipher_name"] == "TLS_AES_256_GCM_SHA384"
        assert endpoint_obs["observed_value"]["key_exchange_status"] == "unobserved"
        assert len(endpoint_obs["evidence_sha256"]) == 64

        cert_obs = next(o for o in obs_list if o["observation_type"] == "x509_certificate")
        assert cert_obs["observed_value"]["public_key_algorithm"] == "RSA"
        assert cert_obs["observed_value"]["public_key_size_bits"] == 2048
        assert cert_obs["evidence_reference"] == "A" * 64
        assert len(cert_obs["evidence_sha256"]) == 64


@pytest.mark.asyncio
async def test_failed_scan_records_failure_state(async_client: AsyncClient) -> None:
    """Verify that a scan failure (e.g. handshake error or timeout) records status='failed'."""
    reg = await async_client.post(
        "/api/v1/targets",
        json={"hostname": "failing-target.com", "authorisation_declared": True},
    )
    tid = reg.json()["id"]
    token = reg.json()["verification_token"]

    await async_client.post(
        f"/api/v1/targets/{tid}/verify",
        json={"verification_method": "token", "token": token},
    )

    mock_fail_result = TLSCollectionResult(
        success=False,
        target_hostname="failing-target.com",
        pinned_ip="192.0.2.1",
        endpoint_evidence=None,
        certificate_evidence=None,
        error_code="TLS_HANDSHAKE_FAILED",
        error_message="TLS connection reset by peer during handshake",
    )

    with patch(
        "services.api.app.api.v1.endpoints.scans.BoundedTLSCollector.inspect_target",
        return_value=mock_fail_result,
    ):
        scan_res = await async_client.post(f"/api/v1/targets/{tid}/scans", json={})
        assert scan_res.status_code == 201
        data = scan_res.json()
        assert data["status"] == "failed"
        assert "reset by peer" in data["error_message"]


@pytest.mark.asyncio
async def test_duplicate_active_scan_rejected(async_client: AsyncClient) -> None:
    """Verify that initiating a scan while an active scan is already in progress returns 409 Conflict."""
    reg = await async_client.post(
        "/api/v1/targets",
        json={"hostname": "active-scan-target.com", "authorisation_declared": True},
    )
    tid = reg.json()["id"]
    token = reg.json()["verification_token"]

    await async_client.post(
        f"/api/v1/targets/{tid}/verify",
        json={"verification_method": "token", "token": token},
    )

    # Simulate an active scan running via a slow inspect_target
    import asyncio

    def slow_inspect(hostname: str) -> TLSCollectionResult:
        # Wait until test signals
        import time

        time.sleep(0.3)
        return TLSCollectionResult(
            success=False,
            target_hostname=hostname,
            pinned_ip=None,
            endpoint_evidence=None,
            certificate_evidence=None,
            error_code="TEST_SLOW_COMPLETE",
        )

    with patch(
        "services.api.app.api.v1.endpoints.scans.BoundedTLSCollector.inspect_target",
        side_effect=slow_inspect,
    ):
        # Fire first scan (runs in background thread for 0.3s)
        task1 = asyncio.create_task(
            async_client.post(f"/api/v1/targets/{tid}/scans", json={"scan_type": "tls_handshake"})
        )
        # Yield to event loop to allow task1 to register scan and transition to in_progress
        await asyncio.sleep(0.05)

        # Fire second scan while task1 is in_progress
        res2 = await async_client.post(
            f"/api/v1/targets/{tid}/scans", json={"scan_type": "tls_handshake"}
        )
        assert res2.status_code == 409
        assert "already in progress" in res2.json()["error"]["message"]

        res1 = await task1
        assert res1.status_code == 201


@pytest.mark.asyncio
async def test_scan_collector_exception_cleanup(async_client: AsyncClient) -> None:
    """Verify that if inspect_target raises an unhandled exception, scan status transitions to 'failed'."""
    reg = await async_client.post(
        "/api/v1/targets",
        json={"hostname": "crash-scan-target.com", "authorisation_declared": True},
    )
    tid = reg.json()["id"]
    token = reg.json()["verification_token"]

    await async_client.post(
        f"/api/v1/targets/{tid}/verify",
        json={"verification_method": "token", "token": token},
    )

    with patch(
        "services.api.app.api.v1.endpoints.scans.BoundedTLSCollector.inspect_target",
        side_effect=RuntimeError("Simulated OS network subsystem failure"),
    ):
        scan_res = await async_client.post(f"/api/v1/targets/{tid}/scans", json={})
        assert scan_res.status_code == 201
        data = scan_res.json()
        assert data["status"] == "failed"
        assert "Simulated OS network subsystem failure" in data["error_message"]
        assert data["completed_at"] is not None
