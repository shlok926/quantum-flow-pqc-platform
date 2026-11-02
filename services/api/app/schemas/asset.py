"""Quantum Flow Technologies — Cryptographic Asset Pydantic Schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CryptographicAssetResponse(BaseModel):
    """Pydantic schema for a correlated CryptographicAsset entity."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    target_id: uuid.UUID | None
    asset_type: str
    asset_key: str
    display_name: str
    locator: str | None
    environment: str | None
    business_criticality: str
    algorithm_family: str | None
    algorithm_name: str | None
    cryptographic_purpose: str
    parameters: dict[str, Any]
    lifecycle_status: str
    classification: str
    confidence_score: float
    first_seen_at: datetime
    last_seen_at: datetime
    correlation_version: str
    created_at: datetime
    updated_at: datetime


class AssetListResponse(BaseModel):
    """Paginated list of cryptographic assets."""

    assets: list[CryptographicAssetResponse]
    total: int
    limit: int
    offset: int


class AssetRelationshipResponse(BaseModel):
    """Relationship between two assets."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_asset_id: uuid.UUID
    target_asset_id: uuid.UUID
    relationship_type: str
    confidence_score: float
    description: str | None
    created_at: datetime
