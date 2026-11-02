"""Quantum Flow Technologies — CBOM Cryptographic Asset Correlator.

Transforms raw collector observations into durable, deduplicated CryptographicAsset
entities, AssetObservation evidence links, and typed AssetRelationship graph links.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.cbom.keys import (
    build_certificate_key,
    build_config_key,
    build_dependency_key,
    build_endpoint_key,
    build_source_asset_key,
)
from packages.scanner.config.models import ConfigFinding
from packages.scanner.dependencies.models import DependencyItem
from packages.scanner.source.models import SourceFinding
from services.api.app.db.models.asset_observation import AssetObservation
from services.api.app.db.models.asset_relationship import AssetRelationship
from services.api.app.db.models.cryptographic_asset import (
    AssetClassification,
    AssetType,
    CryptographicAsset,
    LifecycleStatus,
)
from services.api.app.db.models.observation import Observation

logger = logging.getLogger("quantumflow.cbom")


class AssetCorrelator:
    """Orchestrates asset resolution, deduplication, and relationship linking."""

    @staticmethod
    async def get_or_create_asset(
        db: AsyncSession,
        asset_key: str,
        asset_type: str,
        display_name: str,
        locator: str | None,
        algorithm_family: str | None,
        algorithm_name: str | None,
        cryptographic_purpose: str,
        parameters: dict[str, Any],
        target_id: uuid.UUID | None = None,
        classification: str = AssetClassification.OBSERVED.value,
        confidence_score: float = 1.0,
        business_criticality: str = "high",
    ) -> CryptographicAsset:
        """Atomically find or instantiate an asset by its canonical asset_key."""
        stmt = select(CryptographicAsset).where(CryptographicAsset.asset_key == asset_key)
        res = await db.execute(stmt)
        asset = res.scalar_one_or_none()

        now = datetime.now(UTC)
        if asset is None:
            asset = CryptographicAsset(
                asset_key=asset_key,
                target_id=target_id,
                asset_type=asset_type,
                display_name=display_name,
                locator=locator,
                algorithm_family=algorithm_family,
                algorithm_name=algorithm_name,
                cryptographic_purpose=cryptographic_purpose,
                parameters=parameters,
                lifecycle_status=LifecycleStatus.ACTIVE.value,
                classification=classification,
                confidence_score=confidence_score,
                business_criticality=business_criticality,
                first_seen_at=now,
                last_seen_at=now,
                correlation_version="v1.0.0",
            )
            db.add(asset)
            await db.flush()
        else:
            asset.last_seen_at = now
            # Update parameters if new details observed
            if parameters:
                merged = dict(asset.parameters or {})
                merged.update(parameters)
                asset.parameters = merged
            await db.flush()

        return asset

    @staticmethod
    async def link_observation(
        db: AsyncSession,
        asset_id: uuid.UUID,
        observation_id: uuid.UUID,
        relationship_type: str = "supports",
        reason: str | None = None,
    ) -> AssetObservation:
        """Create an audit link connecting an observation to an asset if not already present."""
        stmt = select(AssetObservation).where(
            AssetObservation.asset_id == asset_id,
            AssetObservation.observation_id == observation_id,
        )
        res = await db.execute(stmt)
        link = res.scalar_one_or_none()
        if link is None:
            link = AssetObservation(
                asset_id=asset_id,
                observation_id=observation_id,
                relationship_type=relationship_type,
                correlation_reason=reason or "Correlated by CBOM discovery pipeline",
                correlation_version="v1.0.0",
            )
            db.add(link)
            await db.flush()
        return link

    @staticmethod
    async def link_assets(
        db: AsyncSession,
        source_asset_id: uuid.UUID,
        target_asset_id: uuid.UUID,
        relationship_type: str,
        confidence_score: float = 1.0,
        description: str | None = None,
    ) -> AssetRelationship:
        """Create a directed relationship link between two assets in the CBOM graph."""
        stmt = select(AssetRelationship).where(
            AssetRelationship.source_asset_id == source_asset_id,
            AssetRelationship.target_asset_id == target_asset_id,
            AssetRelationship.relationship_type == relationship_type,
        )
        res = await db.execute(stmt)
        rel = res.scalar_one_or_none()
        if rel is None:
            rel = AssetRelationship(
                source_asset_id=source_asset_id,
                target_asset_id=target_asset_id,
                relationship_type=relationship_type,
                confidence_score=confidence_score,
                description=description,
            )
            db.add(rel)
            await db.flush()
        return rel

    @classmethod
    async def ingest_tls_observation(
        cls,
        db: AsyncSession,
        observation: Observation,
    ) -> tuple[CryptographicAsset, CryptographicAsset | None]:
        """Correlate a network TLS probe observation into endpoint and certificate assets."""
        payload = observation.observed_value
        hostname = payload.get("hostname", "unknown.example.com")
        port = payload.get("port", 443)
        protocol = payload.get("negotiated_protocol", "TLSv1.3")
        cipher_suite = payload.get("cipher_suite", "UNKNOWN")

        # 1. Endpoint Config Asset
        endpoint_key = build_endpoint_key(hostname, port)
        endpoint_asset = await cls.get_or_create_asset(
            db=db,
            asset_key=endpoint_key,
            asset_type=AssetType.ENDPOINT_CONFIG.value,
            display_name=f"TLS Endpoint {hostname}:{port}",
            locator=f"{hostname}:{port}",
            algorithm_family="TLS",
            algorithm_name=protocol,
            cryptographic_purpose="transport_security",
            parameters={
                "hostname": hostname,
                "port": port,
                "protocol_version": protocol,
                "cipher_suite": cipher_suite,
                "pinned_ip": payload.get("pinned_ip"),
            },
            target_id=observation.target_id,
            classification=AssetClassification.OBSERVED.value,
            confidence_score=1.0,
        )
        await cls.link_observation(
            db=db,
            asset_id=endpoint_asset.id,
            observation_id=observation.id,
            relationship_type="supports",
            reason=f"Direct TLS handshake with {hostname}:{port}",
        )

        # 2. Presented Certificate Asset (if observed)
        cert_data = payload.get("peer_certificate")
        cert_asset: CryptographicAsset | None = None
        if cert_data and cert_data.get("sha256_fingerprint"):
            fingerprint = cert_data["sha256_fingerprint"]
            cert_key = build_certificate_key(fingerprint)
            pub_key = cert_data.get("public_key", {})
            family = pub_key.get("algorithm_family", "RSA")
            algo_name = pub_key.get(
                "algorithm_name", f"{family}-{pub_key.get('key_size_bits', 2048)}"
            )

            cert_asset = await cls.get_or_create_asset(
                db=db,
                asset_key=cert_key,
                asset_type=AssetType.CERTIFICATE.value,
                display_name=f"Certificate ({cert_data.get('subject_dn', hostname)})",
                locator=f"{hostname}:{port}",
                algorithm_family=family,
                algorithm_name=algo_name,
                cryptographic_purpose="server_authentication",
                parameters=cert_data,
                target_id=observation.target_id,
                classification=AssetClassification.OBSERVED.value,
                confidence_score=1.0,
            )
            await cls.link_observation(
                db=db,
                asset_id=cert_asset.id,
                observation_id=observation.id,
                relationship_type="identifies",
                reason=f"Presented during TLS negotiation by {hostname}",
            )
            # Link Endpoint -> Uses -> Certificate
            await cls.link_assets(
                db=db,
                source_asset_id=endpoint_asset.id,
                target_asset_id=cert_asset.id,
                relationship_type="uses_certificate",
                confidence_score=1.0,
                description=f"Endpoint {hostname}:{port} presents certificate {cert_key}",
            )

        return endpoint_asset, cert_asset

    @classmethod
    async def ingest_source_finding(
        cls,
        db: AsyncSession,
        finding: SourceFinding,
        target_id: uuid.UUID | None,
        observation_id: uuid.UUID,
    ) -> CryptographicAsset:
        """Correlate a source code cryptographic finding into an algorithm_usage asset."""
        asset_key = build_source_asset_key(
            finding.file_path, finding.primitive, finding.line_number
        )
        asset = await cls.get_or_create_asset(
            db=db,
            asset_key=asset_key,
            asset_type=AssetType.ALGORITHM_USAGE.value,
            display_name=f"{finding.algorithm} at {finding.file_path}:{finding.line_number}",
            locator=f"{finding.file_path}#L{finding.line_number}",
            algorithm_family=finding.primitive,
            algorithm_name=finding.algorithm,
            cryptographic_purpose=finding.parameters.get("purpose", "cryptographic_operation"),
            parameters=finding.to_dict(),
            target_id=target_id,
            classification=finding.classification,
            confidence_score=finding.confidence,
        )
        await cls.link_observation(
            db=db,
            asset_id=asset.id,
            observation_id=observation_id,
            relationship_type="identifies",
            reason=f"Static code analysis rule {finding.rule_id} triggered",
        )
        return asset

    @classmethod
    async def ingest_dependency(
        cls,
        db: AsyncSession,
        dep: DependencyItem,
        target_id: uuid.UUID | None,
        observation_id: uuid.UUID,
    ) -> CryptographicAsset:
        """Correlate a software package dependency into a library asset."""
        asset_key = build_dependency_key(dep.ecosystem, dep.name, dep.version)
        asset = await cls.get_or_create_asset(
            db=db,
            asset_key=asset_key,
            asset_type=AssetType.LIBRARY.value,
            display_name=f"Package {dep.name} v{dep.version}",
            locator=dep.manifest_path,
            algorithm_family="CryptographicLibrary" if dep.is_known_crypto else "SoftwarePackage",
            algorithm_name=dep.name,
            cryptographic_purpose="software_dependency",
            parameters=dep.to_dict(),
            target_id=target_id,
            classification=AssetClassification.IMPORTED.value,
            confidence_score=0.95,
        )
        await cls.link_observation(
            db=db,
            asset_id=asset.id,
            observation_id=observation_id,
            relationship_type="identifies",
            reason=f"Manifest entry in {dep.manifest_path}",
        )
        return asset

    @classmethod
    async def ingest_config_finding(
        cls,
        db: AsyncSession,
        cfg: ConfigFinding,
        target_id: uuid.UUID | None,
        observation_id: uuid.UUID,
    ) -> CryptographicAsset:
        """Correlate an imported configuration item into a protocol_config asset."""
        asset_key = build_config_key(cfg.file_path, cfg.directive)
        asset = await cls.get_or_create_asset(
            db=db,
            asset_key=asset_key,
            asset_type=AssetType.PROTOCOL_CONFIG.value,
            display_name=f"{cfg.config_type.upper()} {cfg.directive}",
            locator=f"{cfg.file_path}#L{cfg.line_number or 1}",
            algorithm_family="ConfiguredProtocol",
            algorithm_name=", ".join(cfg.protocols or [cfg.directive]),
            cryptographic_purpose="server_configuration",
            parameters=cfg.to_dict(),
            target_id=target_id,
            classification=AssetClassification.IMPORTED.value,
            confidence_score=0.9,
        )
        await cls.link_observation(
            db=db,
            asset_id=asset.id,
            observation_id=observation_id,
            relationship_type="identifies",
            reason=f"Imported from {cfg.file_path}",
        )
        return asset
