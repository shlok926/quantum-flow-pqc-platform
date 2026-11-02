"""Quantum Flow Technologies — CycloneDX 1.6 CBOM Serializer.

Converts correlated CryptographicAsset entities into a standards-compliant
CycloneDX 1.6 JSON Cryptographic Bill of Materials (CBOM).
"""

import uuid
from datetime import UTC, datetime
from typing import Any


def serialize_cyclonedx_16(
    assets: list[Any],
    relationships: list[Any] | None = None,
    document_name: str = "Quantum Flow Cryptographic Inventory",
) -> dict[str, Any]:
    """Serialize cryptographic assets and relationships to CycloneDX 1.6 JSON structure."""
    components: list[dict[str, Any]] = []

    for asset in assets:
        asset_type = getattr(asset, "asset_type", "algorithm_usage")
        asset_key = getattr(asset, "asset_key", str(getattr(asset, "id", "")))
        display_name = getattr(asset, "display_name", "Unknown Asset")
        family = getattr(asset, "algorithm_family", "Generic")
        algo_name = getattr(asset, "algorithm_name", family)
        purpose = getattr(asset, "cryptographic_purpose", "unknown")
        params = getattr(asset, "parameters", {}) or {}

        crypto_prop: dict[str, Any] = {}
        component_type = "cryptographic-asset"

        if asset_type == "certificate":
            crypto_prop = {
                "assetType": "certificate",
                "certificateProperties": {
                    "subjectName": params.get("subject_dn", display_name),
                    "issuerName": params.get("issuer_dn", "Unknown CA"),
                    "notValidBefore": params.get("valid_from"),
                    "notValidAfter": params.get("valid_until"),
                    "signatureAlgorithmRef": params.get("signature_algorithm"),
                },
            }
        elif asset_type == "endpoint_config":
            crypto_prop = {
                "assetType": "protocol",
                "protocolProperties": {
                    "type": "tls",
                    "version": params.get("protocol_version", "TLSv1.3"),
                    "cipherSuites": [params.get("cipher_suite")]
                    if params.get("cipher_suite")
                    else [],
                },
            }
        else:
            crypto_prop = {
                "assetType": "algorithm",
                "algorithmProperties": {
                    "primitive": family or "Unknown",
                    "parameterSetIdentifier": algo_name or "Unknown",
                    "cryptoFunctions": [purpose] if purpose else ["unknown"],
                },
            }

        component: dict[str, Any] = {
            "type": component_type,
            "bom-ref": asset_key,
            "name": display_name,
            "description": getattr(asset, "locator", None) or f"{family} cryptographic asset",
            "cryptoProperties": crypto_prop,
            "properties": [
                {
                    "name": "quantumflow:classification",
                    "value": getattr(asset, "classification", "OBSERVED"),
                },
                {
                    "name": "quantumflow:lifecycle_status",
                    "value": getattr(asset, "lifecycle_status", "active"),
                },
                {
                    "name": "quantumflow:confidence",
                    "value": str(getattr(asset, "confidence_score", 1.0)),
                },
            ],
        }
        components.append(component)

    dependencies: list[dict[str, Any]] = []
    if relationships:
        for rel in relationships:
            src_key = getattr(
                getattr(rel, "source_asset", None),
                "asset_key",
                str(getattr(rel, "source_asset_id", "")),
            )
            tgt_key = getattr(
                getattr(rel, "target_asset", None),
                "asset_key",
                str(getattr(rel, "target_asset_id", "")),
            )
            dependencies.append(
                {
                    "ref": src_key,
                    "dependsOn": [tgt_key],
                    "relationship": getattr(rel, "relationship_type", "uses"),
                }
            )

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "tools": {
                "components": [
                    {
                        "type": "application",
                        "name": "Quantum Flow PQC Discovery Platform",
                        "version": "0.1.0",
                        "vendor": "Quantum Flow Technologies",
                    }
                ]
            },
            "component": {
                "type": "application",
                "name": document_name,
            },
        },
        "components": components,
        "dependencies": dependencies,
    }
