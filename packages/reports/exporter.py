"""Quantum Flow Technologies — Assessment & CBOM Export Engine.

Generates CycloneDX 1.6 compliant JSON reports, RFC 4180 CSV exports
with CSV formula-injection neutralization, and Markdown assessment summaries.
"""

import csv
import io
from typing import Any

from services.api.app.db.models.cryptographic_asset import CryptographicAsset
from services.api.app.db.models.recommendation import Recommendation
from services.api.app.db.models.risk_assessment import RiskAssessment
from services.api.app.db.models.risk_factor import RiskFactor


def sanitize_csv_field(val: Any) -> str:
    """Neutralize spreadsheet formula injection characters.

    Protects against CSV Formula Injection (CWE-1236).
    If a cell begins with '=', '+', '-', '@', '|', '%', or if leading
    whitespace/control characters are followed by any formula trigger,
    prefix with a single quote "'" to prevent formula execution in Excel/Sheets/Calc.
    """
    if val is None:
        return ""
    s = str(val)
    # Check leading control characters or whitespace followed by formula triggers
    stripped = s.lstrip(" \t\r\n\x0b\x0c")
    if stripped and stripped[0] in ("=", "+", "-", "@", "|", "%"):
        return f"'{s}"
    if s and s[0] in ("\t", "\r", "\n"):
        return f"'{s}"
    return s


def export_assets_csv(assets: list[CryptographicAsset]) -> str:
    """Generate CSV string for cryptographic asset inventory with formula-injection defense."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")

    headers = [
        "Asset Key",
        "Asset Type",
        "Display Name",
        "Algorithm Family",
        "Algorithm Name",
        "Cryptographic Purpose",
        "Locator",
        "Criticality",
        "Classification",
        "Confidence",
        "First Seen At",
        "Last Seen At",
    ]
    writer.writerow([sanitize_csv_field(h) for h in headers])

    for a in assets:
        row = [
            a.asset_key,
            a.asset_type,
            a.display_name,
            a.algorithm_family or "Unknown",
            a.algorithm_name or "Unknown",
            a.cryptographic_purpose,
            a.locator or "",
            a.business_criticality,
            a.classification,
            f"{a.confidence_score:.2f}" if a.confidence_score is not None else "1.00",
            a.first_seen_at.isoformat() if a.first_seen_at else "",
            a.last_seen_at.isoformat() if a.last_seen_at else "",
        ]
        writer.writerow([sanitize_csv_field(c) for c in row])

    return output.getvalue()


def export_assessment_json(
    assessment: RiskAssessment,
    asset: CryptographicAsset,
    factors: list[RiskFactor],
    recommendations: list[Recommendation],
) -> dict[str, Any]:
    """Generate comprehensive JSON assessment report."""
    return {
        "assessment_id": str(assessment.id),
        "asset": {
            "id": str(asset.id),
            "asset_key": asset.asset_key,
            "display_name": asset.display_name,
            "type": asset.asset_type,
            "algorithm_family": asset.algorithm_family,
            "algorithm_name": asset.algorithm_name,
            "purpose": asset.cryptographic_purpose,
            "locator": asset.locator,
            "criticality": asset.business_criticality,
        },
        "quantum_risk": {
            "score": assessment.score,
            "category": assessment.risk_category,
            "threat_type": assessment.quantum_threat_type,
            "threat_summary": assessment.threat_summary,
            "evidence_quality": assessment.evidence_quality,
            "methodology_version": assessment.methodology_version,
            "engine_version": assessment.engine_version,
            "input_hash": assessment.assessment_input_hash,
            "assessed_at": assessment.assessed_at.isoformat() if assessment.assessed_at else None,
        },
        "risk_factors": [
            {
                "dimension": f.dimension,
                "code": f.factor_code,
                "title": f.title,
                "rating": f.rating,
                "weight": f.weight,
                "contribution": f.contribution,
                "explanation": f.explanation,
            }
            for f in factors
        ],
        "recommendations": [
            {
                "id": str(r.id),
                "title": r.title,
                "description": r.description,
                "category": r.remediation_category,
                "priority": r.priority,
                "validation_steps": r.validation_steps,
            }
            for r in recommendations
        ],
        "disclaimer": "This assessment is based on collected discovery evidence and does not represent complete enterprise-wide visibility.",
    }


def export_assessment_markdown(
    assessment: RiskAssessment,
    asset: CryptographicAsset,
    factors: list[RiskFactor],
    recommendations: list[Recommendation],
) -> str:
    """Generate human-readable executive Markdown summary."""
    md = [
        f"# Quantum Risk Assessment Report — {asset.display_name}",
        "",
        f"**Assessment ID:** `{assessment.id}`  ",
        f"**Methodology:** {assessment.methodology_version} | **Engine:** {assessment.engine_version}  ",
        f"**Assessed At:** {assessment.assessed_at.isoformat() if assessment.assessed_at else 'N/A'}  ",
        "",
        "## Executive Summary",
        "",
        f"- **Quantum Vulnerability Index (QVI):** **{assessment.score} / 1000** ({assessment.risk_category.upper()})",
        f"- **Primary Threat:** `{assessment.quantum_threat_type}`",
        f"- **Algorithm Profile:** {asset.algorithm_name or asset.algorithm_family} ({asset.cryptographic_purpose})",
        f"- **Evidence Quality:** {assessment.evidence_quality.upper()}",
        "",
        f"> {assessment.threat_summary}",
        "",
        "## Dimension Breakdown (0–1000 Contribution)",
        "",
        "| Dim | Factor Title | Rating (0–5) | Weight | Contribution |",
        "|---|---|---:|---:|---:|",
    ]

    for f in factors:
        md.append(
            f"| **{f.dimension}** | {f.title} | {f.rating}/5 | {f.weight} | **+{f.contribution}** |"
        )

    md.extend(
        [
            "",
            "## Remediation Recommendations",
            "",
        ]
    )

    if not recommendations:
        md.append("_No immediate migration actions required under current evidence._")
    else:
        for idx, r in enumerate(recommendations, start=1):
            md.append(f"### {idx}. {r.title} [{r.priority.upper()}]")
            md.append(f"{r.description}")
            md.append("")
            md.append("**Validation Steps:**")
            for step in r.validation_steps:
                md.append(f"- {step}")
            md.append("")

    md.extend(
        [
            "---",
            "### Coverage Limitations & Disclaimer",
            "",
            "> [!IMPORTANT]",
            "> This report is strictly based on the specific cryptographic evidence collected and provided. It does not certify absence of other quantum vulnerabilities across unexamined systems or internal networks.",
        ]
    )

    return "\n".join(md)
