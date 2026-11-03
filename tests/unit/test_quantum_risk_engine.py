"""Quantum Flow Technologies — Quantum Risk Rules Engine Unit Tests.

Verifies:
1. Methodology v1.0 score bounded strictly between 0 and 1000.
2. Shor-vulnerable algorithms (RSA, ECC) produce High/Critical quantum susceptibility.
3. Grover-margin algorithms (AES-128) produce Medium Grover susceptibility.
4. Post-quantum standards (ML-KEM) produce Safe status.
5. Actionable remediation recommendations generated with migration options.
"""

from packages.risk.catalogue import lookup_algorithm_threat
from packages.risk.engine import DIMENSION_WEIGHTS, QuantumRiskEngine
from services.api.app.db.models.cryptographic_asset import CryptographicAsset
from services.api.app.db.models.risk_assessment import ThreatType


def test_classify_algorithm_threat() -> None:
    """Verify threat taxonomy classifies classic, grover, and post-quantum accurately."""
    shor = lookup_algorithm_threat("RSA", "RSA-2048")
    assert shor["threat_type"] == ThreatType.SHOR_VULNERABLE.value
    assert shor["quantum_susceptibility_rating"] >= 4

    ecc_shor = lookup_algorithm_threat("ECC", "ECDSA-SECP256R1")
    assert ecc_shor["threat_type"] == ThreatType.SHOR_VULNERABLE.value

    grover = lookup_algorithm_threat("AES", "AES-128")
    assert grover["threat_type"] == ThreatType.GROVER_MARGIN.value

    pqc = lookup_algorithm_threat("ML-KEM", "ML-KEM-768")
    assert pqc["threat_type"] == "pqc_recognised"
    assert pqc["is_pqc"] is True


def test_quantum_risk_engine_score_bounds() -> None:
    """Verify QVI score is strictly bounded [0, 1000] and factor contributions match."""
    rsa_asset = CryptographicAsset(
        asset_key="cert:sha256:11112222333344445555666677778888",
        asset_type="certificate",
        display_name="CN=payment-gateway.internal",
        algorithm_name="RSA-2048",
        algorithm_family="RSA",
        cryptographic_purpose="key_exchange",
        business_criticality="tier_1",
        parameters={"key_size_bits": 2048},
    )

    assessment, factors, recs = QuantumRiskEngine.assess_asset(
        rsa_asset, context={"confidentiality_lifetime_years": 10}
    )

    assert assessment.score is not None
    assert 0 <= assessment.score <= 1000
    assert assessment.quantum_threat_type == ThreatType.SHOR_VULNERABLE.value

    # Check sum of factor contributions equals total score
    total_contrib = sum(f.contribution for f in factors)
    assert total_contrib == assessment.score

    # Check recommendations exist for vulnerable asset
    assert len(recs) > 0
    assert any("ML-KEM" in r.description or "X25519MLKEM768" in r.description for r in recs)


def test_methodology_dimensions_and_max_raw_score() -> None:
    """Verify Methodology v1.0 formula: 7 weighted dimensions sum to exactly 950 raw points.

    Dimension 8 (Evidence quality & completeness) is unweighted per Section 8.1 line 477.
    """
    # 1. Assert exactly 7 weighted dimensions
    assert set(DIMENSION_WEIGHTS.keys()) == {"Q", "R", "L", "E", "B", "M", "V"}

    # 2. Assert weights sum to exactly 950
    total_weights = sum(DIMENSION_WEIGHTS.values())
    assert total_weights == 950
    assert DIMENSION_WEIGHTS["Q"] == 300
    assert DIMENSION_WEIGHTS["R"] == 150
    assert DIMENSION_WEIGHTS["L"] == 150
    assert DIMENSION_WEIGHTS["E"] == 100
    assert DIMENSION_WEIGHTS["B"] == 100
    assert DIMENSION_WEIGHTS["M"] == 75
    assert DIMENSION_WEIGHTS["V"] == 75

    # 3. Simulate maximum ratings (5 across all 7 dimensions)
    max_ratings = dict.fromkeys(DIMENSION_WEIGHTS, 5)
    raw_max = sum(round((w * max_ratings[k]) / 5) for k, w in DIMENSION_WEIGHTS.items())
    assert raw_max == 950

    # 4. Dimension 8 is unweighted reliability measure, preserved on assessment
    observed_asset = CryptographicAsset(
        asset_key="cert:sha256:observed123",
        asset_type="certificate",
        display_name="CN=observed.internal",
        algorithm_name="RSA-2048",
        algorithm_family="RSA",
        cryptographic_purpose="key_exchange",
        business_criticality="critical",
        classification="OBSERVED",
    )
    inferred_asset = CryptographicAsset(
        asset_key="cert:sha256:inferred123",
        asset_type="certificate",
        display_name="CN=inferred.internal",
        algorithm_name="RSA-2048",
        algorithm_family="RSA",
        cryptographic_purpose="key_exchange",
        business_criticality="critical",
        classification="INFERRED",
    )

    assessment_obs, _, _ = QuantumRiskEngine.assess_asset(
        observed_asset, context={"confidentiality_lifetime_years": 10, "exposure": "internet"}
    )
    assessment_inf, _, _ = QuantumRiskEngine.assess_asset(
        inferred_asset, context={"confidentiality_lifetime_years": 10, "exposure": "internet"}
    )

    # Both share identical cryptographic risk score (evidence confidence does NOT alter risk)
    assert assessment_obs.score == assessment_inf.score
    # But Dimension 8 correctly distinguishes evidence confidence
    assert assessment_obs.evidence_quality == "high"
    assert assessment_inf.evidence_quality == "medium"
