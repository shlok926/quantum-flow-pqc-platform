"""Quantum Flow Technologies — CBOM Correlation & CycloneDX Serialization Unit Tests.

Verifies:
1. Deterministic asset key generation across sources.
2. CycloneDX 1.6 JSON export structure with cryptoProperties.
"""

from packages.cbom.cyclonedx import serialize_cyclonedx_16
from packages.cbom.keys import (
    build_certificate_key,
    build_config_key,
    build_dependency_key,
    build_endpoint_key,
    build_source_asset_key,
)
from services.api.app.db.models.cryptographic_asset import (
    AssetClassification,
    CryptographicAsset,
)


def test_asset_keys_are_deterministic() -> None:
    """Verify identical inputs yield exact identical deterministic asset keys."""
    k1 = build_certificate_key("A" * 64)
    k2 = build_certificate_key("a" * 64)
    assert k1 == k2
    assert k1.startswith("cert:sha256:")

    tls_k = build_endpoint_key("api.example.com", 443)
    assert tls_k == "tls:api.example.com:443"

    src_k = build_source_asset_key("src/auth.py", "RSA", 45)
    assert src_k == "code:src/auth.py:rsa:45"

    dep_k = build_dependency_key("pypi", "cryptography", "42.0.5")
    assert dep_k == "dep:pypi:cryptography:42.0.5"

    cfg_k = build_config_key("nginx.conf", "ssl_protocols")
    assert cfg_k == "cfg:nginx.conf:ssl_protocols"


def test_cyclonedx_16_serialization() -> None:
    """Verify CycloneDX 1.6 JSON output format with cryptographic extensions."""
    asset = CryptographicAsset(
        asset_key="cert:sha256:abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234",
        asset_type="certificate",
        display_name="CN=secure.example.com",
        algorithm_name="RSA-2048",
        algorithm_family="RSA",
        classification=AssetClassification.OBSERVED.value,
        parameters={"subject_dn": "CN=secure.example.com"},
    )

    cbom = serialize_cyclonedx_16(assets=[asset], relationships=[])

    assert cbom["bomFormat"] == "CycloneDX"
    assert cbom["specVersion"] == "1.6"
    assert len(cbom["components"]) == 1

    comp = cbom["components"][0]
    assert comp["type"] == "cryptographic-asset"
    assert comp["name"] == "CN=secure.example.com"
    assert "cryptoProperties" in comp
    assert comp["cryptoProperties"]["assetType"] == "certificate"
    assert (
        comp["cryptoProperties"]["certificateProperties"]["subjectName"] == "CN=secure.example.com"
    )
