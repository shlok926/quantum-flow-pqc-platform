"""Quantum Flow Technologies — Quantum Risk Assessment Scoring Engine.

Implements the deterministic 0–1000 Quantum Vulnerability Index (QVI) calculation,
reason factor generation, and remediation recommendations per Methodology v1.0.
"""

import hashlib
import json
import logging
from typing import Any

from packages.risk.catalogue import lookup_algorithm_threat
from services.api.app.db.models.cryptographic_asset import CryptographicAsset
from services.api.app.db.models.recommendation import (
    Recommendation,
    RecommendationPriority,
    RemediationCategory,
)
from services.api.app.db.models.risk_assessment import (
    RiskAssessment,
    RiskCategory,
    ThreatType,
)
from services.api.app.db.models.risk_factor import RiskFactor

logger = logging.getLogger("quantumflow.risk")

# Methodology v1.0 Dimension Weights
# Per Quantum_Risk_Assessment_Methodology_v1.0.md Section 7.1 and 8.1:
# The methodology defines 8 dimensions:
# - 7 weighted risk dimensions summing to a raw mathematical maximum of 950:
#   D1 (Q): 300 - Cryptographic quantum susceptibility
#   D2 (R): 150 - Cryptographic role and impact
#   D3 (L): 150 - Data confidentiality lifetime / urgency (HNDL)
#   D4 (E): 100 - Exposure and accessibility
#   D5 (B): 100 - Business criticality
#   D6 (M):  75 - Dependency and migration complexity
#   D7 (V):  75 - Vendor/platform readiness gap
#   Sum: 300 + 150 + 150 + 100 + 100 + 75 + 75 = 950 raw points.
# - D8 (Evidence Quality & Completeness): Deliberately UNWEIGHTED per Section 8.1 line 477
#   ("Evidence confidence is deliberately not a weighted risk factor. It is a separate
#   reliability/eligibility measure"). Represented as assessment.evidence_quality.
# Scores are presented on the nominal 0–1000 prioritization scale.
DIMENSION_WEIGHTS: dict[str, int] = {
    "Q": 300,  # Cryptographic quantum susceptibility
    "R": 150,  # Cryptographic role and impact
    "L": 150,  # Data confidentiality lifetime / urgency
    "E": 100,  # Exposure and accessibility
    "B": 100,  # Business criticality
    "M": 75,  # Dependency and migration complexity
    "V": 75,  # Vendor/platform readiness gap
}


def calculate_category(score: int) -> RiskCategory:
    """Map 0–1000 score to methodology category bands."""
    if score >= 800:
        return RiskCategory.CRITICAL
    elif score >= 600:
        return RiskCategory.HIGH
    elif score >= 400:
        return RiskCategory.ELEVATED
    elif score >= 200:
        return RiskCategory.GUARDED
    return RiskCategory.LOW


class QuantumRiskEngine:
    """Evaluates cryptographic assets against Quantum Risk Assessment Methodology v1.0."""

    @classmethod
    def assess_asset(
        cls,
        asset: CryptographicAsset,
        context: dict[str, Any] | None = None,
    ) -> tuple[RiskAssessment, list[RiskFactor], list[Recommendation]]:
        """Perform a deterministic quantum risk assessment for an asset."""
        ctx = context or {}
        threat_info = lookup_algorithm_threat(asset.algorithm_family, asset.algorithm_name)

        # ----------------------------------------------------------------------
        # Rate Dimensions (0 to 5)
        # ----------------------------------------------------------------------
        # D1: Quantum susceptibility (Q)
        rating_q = threat_info.get("quantum_susceptibility_rating", 3)

        # D2: Cryptographic role and impact (R)
        purpose = (asset.cryptographic_purpose or "").lower()
        if any(p in purpose for p in ("key_establishment", "key_exchange", "root_ca")):
            rating_r = 5
        elif any(p in purpose for p in ("server_authentication", "signature", "encryption")):
            rating_r = 4
        elif any(p in purpose for p in ("integrity", "hashing", "mac")):
            rating_r = 3
        else:
            rating_r = 2

        # D3: Data confidentiality lifetime / urgency (L) (Harvest Now Decrypt Later)
        lifetime_years = ctx.get("confidentiality_lifetime_years", 5)
        if lifetime_years >= 10:
            rating_l = 5
        elif lifetime_years >= 7:
            rating_l = 4
        elif lifetime_years >= 3:
            rating_l = 3
        else:
            rating_l = 2

        # D4: Exposure and accessibility (E)
        exposure = ctx.get("exposure", "internet").lower()
        if "internet" in exposure or "public" in exposure:
            rating_e = 5
        elif "partner" in exposure:
            rating_e = 3
        elif "internal" in exposure:
            rating_e = 2
        else:
            rating_e = 1

        # D5: Business criticality (B)
        crit = (asset.business_criticality or "high").lower()
        if crit == "critical":
            rating_b = 5
        elif crit == "high":
            rating_b = 4
        elif crit == "medium":
            rating_b = 3
        else:
            rating_b = 1

        # D6: Dependency and migration complexity (M)
        dep_count = len(getattr(asset, "outgoing_relationships", []) or [])
        if dep_count >= 5:
            rating_m = 4
        elif dep_count >= 2:
            rating_m = 3
        else:
            rating_m = 2

        # D7: Vendor / platform readiness gap (V)
        if threat_info.get("is_pqc", False):
            rating_v = 0
        elif rating_q >= 4:
            rating_v = 3
        else:
            rating_v = 2

        ratings = {
            "Q": rating_q,
            "R": rating_r,
            "L": rating_l,
            "E": rating_e,
            "B": rating_b,
            "M": rating_m,
            "V": rating_v,
        }

        # Calculate contributions
        contributions: dict[str, int] = {}
        for dim, rating in ratings.items():
            weight = DIMENSION_WEIGHTS[dim]
            contributions[dim] = round((weight * rating) / 5)

        total_score = sum(contributions.values())
        risk_cat = calculate_category(total_score)

        # Canonical input hash
        input_dict = {
            "asset_key": asset.asset_key,
            "algorithm": asset.algorithm_name,
            "ratings": ratings,
            "context": ctx,
        }
        input_bytes = json.dumps(input_dict, sort_keys=True).encode("utf-8")
        input_hash = hashlib.sha256(input_bytes).hexdigest()

        # Build RiskAssessment
        assessment = RiskAssessment(
            asset_id=asset.id,
            assessment_number=1,
            status="provisional",
            score=total_score,
            risk_category=risk_cat.value,
            quantum_threat_type=threat_info.get("threat_type", ThreatType.UNKNOWN.value),
            threat_summary=threat_info.get("summary", "Quantum threat evaluation completed."),
            evidence_quality="high" if asset.classification == "OBSERVED" else "medium",
            assessment_input_hash=input_hash,
            engine_version="v1.0.0",
            methodology_version="QFT-RISK-v1.0",
            policy_snapshot=DIMENSION_WEIGHTS,
            limitations={
                "disclaimer": "Provisional evaluation based on collected evidence; not complete enterprise inventory.",
                "scope": asset.locator or asset.display_name,
            },
        )

        # Build RiskFactors
        factor_defs = [
            (
                "Q",
                "DIM_Q_QUANTUM_SUSCEPTIBILITY",
                "Cryptographic Quantum Susceptibility",
                threat_info["summary"],
            ),
            (
                "R",
                "DIM_R_CRYPTOGRAPHIC_ROLE",
                "Cryptographic Role & Security Impact",
                f"Role is '{asset.cryptographic_purpose}'",
            ),
            (
                "L",
                "DIM_L_CONFIDENTIALITY_LIFETIME",
                "Data Confidentiality Lifetime (HNDL)",
                f"Protected data sensitivity horizon: {lifetime_years} years",
            ),
            (
                "E",
                "DIM_E_NETWORK_EXPOSURE",
                "Exposure and Network Accessibility",
                f"Asset network exposure level: {exposure}",
            ),
            (
                "B",
                "DIM_B_BUSINESS_CRITICALITY",
                "Business Criticality",
                f"Operational asset criticality: {asset.business_criticality}",
            ),
            (
                "M",
                "DIM_M_MIGRATION_COMPLEXITY",
                "Remediation & Migration Complexity",
                f"Estimated dependent components: {dep_count}",
            ),
            (
                "V",
                "DIM_V_VENDOR_READINESS_GAP",
                "Vendor & Protocol Readiness Gap",
                "Evaluation of available PQC migration path",
            ),
        ]

        factors: list[RiskFactor] = []
        for dim, code, title, expl in factor_defs:
            factor = RiskFactor(
                factor_code=code,
                dimension=dim,
                title=title,
                explanation=expl,
                rating=ratings[dim],
                weight=DIMENSION_WEIGHTS[dim],
                contribution=contributions[dim],
                evidence_refs={"asset_key": asset.asset_key, "algorithm": asset.algorithm_name},
                input_values={"rating": ratings[dim]},
            )
            factors.append(factor)

        # Build Recommendations
        recommendations: list[Recommendation] = []
        if threat_info.get("threat_type") == ThreatType.SHOR_VULNERABLE.value:
            recommendations.append(
                Recommendation(
                    asset_id=asset.id,
                    title=f"Plan PQC Migration for {asset.algorithm_name}",
                    description=f"Transition from classical {asset.algorithm_family} to NIST FIPS 203 (ML-KEM) or FIPS 204 (ML-DSA).",
                    remediation_category=RemediationCategory.ALGORITHM_MIGRATION.value,
                    priority=RecommendationPriority.CRITICAL.value
                    if total_score >= 600
                    else RecommendationPriority.HIGH.value,
                    evidence_refs={"algorithm": asset.algorithm_name, "score": total_score},
                    validation_steps=[
                        "Identify all dependent clients and TLS endpoints.",
                        "Verify server and client support for hybrid X25519MLKEM768.",
                        "Pilot PQC key encapsulation in staging environment.",
                    ],
                    known_limitations="Requires client software and TLS stack compatibility for post-quantum key exchange.",
                )
            )
        elif threat_info.get("threat_type") == ThreatType.GROVER_MARGIN.value and "128" in (
            asset.algorithm_name or ""
        ):
            recommendations.append(
                Recommendation(
                    asset_id=asset.id,
                    title=f"Upgrade {asset.algorithm_name} to 256-bit Key Length",
                    description="Grover's algorithm halves symmetric security bits; upgrade AES-128 to AES-256 for a 128-bit quantum margin.",
                    remediation_category=RemediationCategory.KEY_SIZE_INCREASE.value,
                    priority=RecommendationPriority.MEDIUM.value,
                    evidence_refs={"algorithm": asset.algorithm_name},
                    validation_steps=["Verify cipher suite configuration supports AES-256-GCM."],
                )
            )

        return assessment, factors, recommendations
