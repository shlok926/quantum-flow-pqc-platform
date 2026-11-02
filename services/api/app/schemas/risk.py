"""Quantum Flow Technologies — Risk Assessment Pydantic Schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RiskFactorResponse(BaseModel):
    """Pydantic schema for individual dimension evaluation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    factor_code: str
    dimension: str
    title: str
    explanation: str
    rating: int
    weight: int
    contribution: int
    evidence_refs: dict[str, Any]
    input_values: dict[str, Any]


class RecommendationResponse(BaseModel):
    """Pydantic schema for remediation recommendations."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    remediation_category: str
    priority: str
    evidence_refs: dict[str, Any]
    validation_steps: list[str]
    known_limitations: str | None


class RiskAssessmentResponse(BaseModel):
    """Pydantic schema for a complete quantum risk assessment."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_id: uuid.UUID
    assessment_number: int
    status: str
    score: int | None
    risk_category: str
    quantum_threat_type: str
    threat_summary: str
    evidence_quality: str
    assessment_input_hash: str
    engine_version: str
    methodology_version: str
    policy_snapshot: dict[str, Any]
    limitations: dict[str, Any]
    assessed_at: datetime
    factors: list[RiskFactorResponse] = Field(default_factory=list)
    recommendations: list[RecommendationResponse] = Field(default_factory=list)


class RiskAssessmentListResponse(BaseModel):
    """Paginated list of risk assessments."""

    assessments: list[RiskAssessmentResponse]
    total: int
    limit: int
    offset: int
