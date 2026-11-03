"""Unit tests for CycloneDX 1.6 CBOM schema validation and dependency graph diagnostics.

Verifies:
1. Generated CBOM documents validate against the official CycloneDX 1.6 JSON Schema
   using `JsonValidator` and `jsonschema`.
2. Valid `cryptoProperties` for certificates, protocols, and cryptographic algorithms.
3. Strict distinction between structural schema validity and semantic correctness.
4. Visible diagnostics and comment warnings for unresolved dependency relationships
   while maintaining 100% schema compliance.
"""

import json
import uuid
from typing import Any

import pytest

from packages.reports.exporter import export_assessment_cyclonedx

try:
    from cyclonedx.schema import SchemaVersion  # type: ignore
    from cyclonedx.validation.json import JsonValidator  # type: ignore

    HAVE_CYCLONEDX = True
except ImportError:
    HAVE_CYCLONEDX = False

pytestmark = pytest.mark.skipif(
    not HAVE_CYCLONEDX, reason="cyclonedx-python-lib is required for CBOM schema validation"
)


@pytest.fixture
def validator_1_6() -> Any:
    """Fixture providing CycloneDX 1.6 official JSON schema validator."""
    if not HAVE_CYCLONEDX:
        pytest.skip("cyclonedx-python-lib not installed")
    return JsonValidator(SchemaVersion.V1_6)


@pytest.fixture
def complete_assessment_snapshot() -> dict:
    """Fixture with certificates, protocols, algorithms, and fully resolvable relationships."""
    cert_key = "cert:sha256:1122334455"
    proto_key = "tls:protocol:1.3"
    algo_key = "algo:mlkem:768"

    return {
        "assessment_id": str(uuid.uuid4()),
        "title": "Production TLS and PQC Assessment",
        "status": "completed",
        "target_snapshot": {
            "id": "target-uuid-9999",
            "hostname": "gateway.internal.example.com",
            "environment": "production",
            "business_criticality": "critical",
        },
        "started_at": "2026-11-03T08:00:00Z",
        "completed_at": "2026-11-03T08:05:00Z",
        "methodology_version": "QFT-RISK-v1.0",
        "engine_version": "v1.0.0",
        "risk_summary": {
            "max_asset_qvi": 920,
            "overall_score": 920,
            "risk_category": "critical",
        },
        "assets": [
            {
                "asset_key": cert_key,
                "asset_type": "certificate",
                "display_name": "Edge Wildcard RSA Certificate",
                "algorithm_family": "RSA",
                "algorithm_name": "RSA-2048",
                "cryptographic_purpose": "authentication",
                "locator": "gateway.internal.example.com:443",
                "business_criticality": "critical",
                "classification": "OBSERVED",
                "confidence_score": 1.0,
                "risk_score": 920,
                "risk_category": "critical",
                "quantum_threat_type": "shor_factorisation",
                "parameters": {
                    "subject_dn": "CN=*.internal.example.com",
                    "issuer_dn": "CN=DigiCert Global Root CA",
                    "valid_from": "2026-01-01T00:00:00Z",
                    "valid_until": "2027-01-01T00:00:00Z",
                },
            },
            {
                "asset_key": proto_key,
                "asset_type": "protocol",
                "display_name": "TLS 1.3 Communication Protocol",
                "algorithm_family": "TLS",
                "algorithm_name": "TLS_AES_256_GCM_SHA384",
                "cryptographic_purpose": "secure_channel",
                "locator": "gateway.internal.example.com:443",
                "business_criticality": "critical",
                "classification": "OBSERVED",
                "confidence_score": 1.0,
                "risk_score": 250,
                "risk_category": "low",
                "quantum_threat_type": "grover_search",
                "parameters": {
                    "protocol_version": "1.3",
                    "cipher_suite": "TLS_AES_256_GCM_SHA384",
                },
            },
            {
                "asset_key": algo_key,
                "asset_type": "algorithm",
                "display_name": "NIST ML-KEM-768 Post-Quantum Key Encapsulation",
                "algorithm_family": "ML-KEM",
                "algorithm_name": "ML-KEM-768",
                "cryptographic_purpose": "key_exchange",
                "locator": "packages/crypto/kem.py:15",
                "business_criticality": "high",
                "classification": "OBSERVED",
                "confidence_score": 1.0,
                "risk_score": 100,
                "risk_category": "negligible",
                "quantum_threat_type": "quantum_safe",
                "parameters": {
                    "primitive": "kem",
                    "standard": "FIPS 203",
                },
            },
        ],
        "relationships": [
            {
                "source_asset_key": proto_key,
                "target_asset_key": cert_key,
                "relationship": "authenticates_with",
            },
            {
                "source_asset_key": proto_key,
                "target_asset_key": algo_key,
                "relationship": "negotiates_key_with",
            },
        ],
    }


def test_cyclonedx_1_6_official_schema_validation(
    validator_1_6: JsonValidator, complete_assessment_snapshot: dict
) -> None:
    """Verify that export_assessment_cyclonedx produces a 100% valid CycloneDX 1.6 JSON document."""
    cbom = export_assessment_cyclonedx(complete_assessment_snapshot)
    json_str = json.dumps(cbom)

    validation_error = validator_1_6.validate_str(json_str)
    assert validation_error is None, f"CycloneDX 1.6 schema validation failed: {validation_error}"

    # Verify root schema structure
    assert cbom["bomFormat"] == "CycloneDX"
    assert cbom["specVersion"] == "1.6"
    assert cbom["serialNumber"].startswith("urn:uuid:")
    assert cbom["version"] == 1
    assert "components" in cbom
    assert len(cbom["components"]) == 3
    assert len(cbom["dependencies"]) == 2


def test_cyclonedx_crypto_properties_mapping(complete_assessment_snapshot: dict) -> None:
    """Verify semantic mapping of certificate, protocol, and algorithm cryptoProperties."""
    cbom = export_assessment_cyclonedx(complete_assessment_snapshot)
    by_key = {c["bom-ref"]: c for c in cbom["components"]}

    # 1. Certificate Properties
    cert_comp = by_key["cert:sha256:1122334455"]
    assert cert_comp["type"] == "cryptographic-asset"
    cert_crypto = cert_comp["cryptoProperties"]
    assert cert_crypto["assetType"] == "certificate"
    cert_props = cert_crypto["certificateProperties"]
    assert cert_props["subjectName"] == "CN=*.internal.example.com"
    assert cert_props["issuerName"] == "CN=DigiCert Global Root CA"
    assert cert_props["notValidBefore"] == "2026-01-01T00:00:00Z"
    assert cert_props["certificateFormat"] == "X.509"

    # 2. Protocol Properties
    proto_comp = by_key["tls:protocol:1.3"]
    proto_crypto = proto_comp["cryptoProperties"]
    assert proto_crypto["assetType"] == "protocol"
    proto_props = proto_crypto["protocolProperties"]
    assert proto_props["type"] == "tls"
    assert proto_props["version"] == "1.3"
    assert proto_props["cipherSuites"] == [{"name": "TLS_AES_256_GCM_SHA384"}]

    # 3. Algorithm Properties (Post-Quantum KEM)
    algo_comp = by_key["algo:mlkem:768"]
    algo_crypto = algo_comp["cryptoProperties"]
    assert algo_crypto["assetType"] == "algorithm"
    algo_props = algo_crypto["algorithmProperties"]
    assert algo_props["primitive"] == "kem"
    assert algo_props["parameterSetIdentifier"] == "ML-KEM-768"
    assert "encapsulate" in algo_props["cryptoFunctions"]


def test_cyclonedx_visible_diagnostics_for_unresolved_dependencies(
    validator_1_6: JsonValidator, complete_assessment_snapshot: dict
) -> None:
    """Verify unresolved dependency relationships produce visible diagnostics and remain schema-valid."""
    snapshot_with_missing_dep = dict(complete_assessment_snapshot)
    # Add relationships pointing to non-existent assets
    snapshot_with_missing_dep["relationships"] = [
        {
            "source_asset_key": "tls:protocol:1.3",
            "target_asset_key": "cert:sha256:1122334455",  # Exists
        },
        {
            "source_asset_key": "tls:protocol:1.3",
            "target_asset_key": "cert:sha256:non_existent_target",  # Unresolved target
        },
        {
            "source_asset_key": "algo:phantom:unknown",  # Unresolved source
            "target_asset_key": "algo:mlkem:768",
        },
    ]

    cbom = export_assessment_cyclonedx(snapshot_with_missing_dep)
    json_str = json.dumps(cbom)

    # 1. Structural Validity: Must still be 100% valid against official CycloneDX 1.6 schema
    validation_error = validator_1_6.validate_str(json_str)
    assert validation_error is None, (
        f"Schema validation failed on incomplete graph: {validation_error}"
    )

    # 2. Semantic Integrity: Only valid relationships emitted in dependencies list
    assert len(cbom["dependencies"]) == 1
    assert cbom["dependencies"][0]["ref"] == "tls:protocol:1.3"
    assert cbom["dependencies"][0]["dependsOn"] == ["cert:sha256:1122334455"]

    # 3. Visible Diagnostics: Recorded in metadata properties and comment
    meta_props = {p["name"]: p["value"] for p in cbom["metadata"]["properties"]}
    assert meta_props.get("qft:dependency_graph_status") == "INCOMPLETE_RELATIONSHIPS_RECORDED"
    assert "2 cryptographic relationships could not be resolved" in meta_props.get(
        "qft:warning:incomplete_dependency_graph", ""
    )

    # Find the diagnostic entries
    diag_entries = [
        p["value"]
        for p in cbom["metadata"]["properties"]
        if p["name"] == "qft:export_diagnostics:unresolved_dependency"
    ]
    assert len(diag_entries) == 2
    assert any("non_existent_target" in d for d in diag_entries)
    assert any("algo:phantom:unknown" in d for d in diag_entries)

    # Visible comment warning in properties
    assert "WARNING: CBOM dependency graph contains 2 unresolved relationships." in meta_props.get(
        "qft:comment", ""
    )
