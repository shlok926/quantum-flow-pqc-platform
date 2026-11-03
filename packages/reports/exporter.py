"""Quantum Flow Technologies — Assessment & CBOM Export Engine.

Generates CycloneDX 1.6 compliant JSON reports, RFC 4180 CRLF CSV exports
with comprehensive spreadsheet formula-injection mitigation, and Executive
Markdown assessment reports derived from cryptographically verified terminal snapshots.
"""

import csv
import hmac
import io
import uuid
from datetime import UTC, datetime
from typing import Any

from packages.scanner.safety.canonical import compute_canonical_evidence_sha256
from services.api.app.db.models.cryptographic_asset import CryptographicAsset
from services.api.app.db.models.recommendation import Recommendation
from services.api.app.db.models.risk_assessment import RiskAssessment
from services.api.app.db.models.risk_factor import RiskFactor


class SnapshotIntegrityError(Exception):
    """Raised when an assessment terminal report snapshot fails cryptographic integrity verification."""

    pass


# Characters to strip when checking for leading formula triggers:
# ASCII whitespace, control characters (0x00-0x1f, 0x7f), Unicode whitespace (NBSP, ZWSP, ideographic), and BOM.
_CSV_STRIP_CHARS = "".join(chr(i) for i in range(32)) + "\x7f\u00a0\u200b\u3000\ufeff "


def sanitize_csv_field(val: Any) -> str:
    """Neutralize spreadsheet formula injection characters (CWE-1236).

    If a cell begins with '=', '+', '-', '@', '|', '%', or if leading
    whitespace, control characters, or Unicode spaces are followed by
    any formula trigger, prefix with a single quote "'" to neutralize formula execution.
    Input values are not mutated in place.
    """
    if val is None:
        return ""
    s = str(val)
    stripped = s.lstrip(_CSV_STRIP_CHARS)
    if stripped and stripped[0] in ("=", "+", "-", "@", "|", "%"):
        return f"'{s}"
    if s and (ord(s[0]) < 32 or s[0] in ("\x7f", "\u00a0", "\u200b", "\u3000", "\ufeff")):
        return f"'{s}"
    return s


def verify_and_load_snapshot(assessment: Any) -> dict[str, Any]:
    """Verify cryptographic integrity of an assessment's terminal report snapshot.

    Recomputes the RFC 8785 canonical JSON SHA-256 digest of the snapshot
    and compares it in constant time against the immutable stored hash.

    Returns:
        dict[str, Any]: The verified snapshot dictionary.

    Raises:
        ValueError: If snapshot or stored hash is missing.
        SnapshotIntegrityError: If the recomputed digest does not match the stored hash.
    """
    if isinstance(assessment, dict):
        snapshot = assessment.get("report_snapshot") or assessment
        stored_hash = assessment.get("report_snapshot_hash")
    else:
        snapshot = getattr(assessment, "report_snapshot", None)
        stored_hash = getattr(assessment, "report_snapshot_hash", None)

    if snapshot is None:
        raise ValueError("Terminal assessment report snapshot is missing")
    if not stored_hash or len(stored_hash.strip()) != 64:
        raise ValueError("Report snapshot hash is missing or malformed")

    computed_hash = compute_canonical_evidence_sha256(snapshot)
    if not hmac.compare_digest(computed_hash.lower(), stored_hash.strip().lower()):
        raise SnapshotIntegrityError(
            "Terminal assessment report snapshot failed cryptographic integrity verification. "
            f"Computed: {computed_hash}, Stored: {stored_hash}. Report export aborted."
        )

    return dict(snapshot)


def _map_primitive(family: str, purpose: str) -> str:
    """Map algorithm family and purpose to CycloneDX 1.6 primitive enum."""
    fam = (family or "").lower().strip()
    purp = (purpose or "").lower().strip()

    if any(k in fam for k in ("rsa", "pke", "elgamal")):
        if any(k in purp for k in ("sign", "auth", "signature")):
            return "signature"
        return "pke"
    if any(
        k in fam
        for k in (
            "ecdsa",
            "ed25519",
            "ed448",
            "dsa",
            "sphincs",
            "slh-dsa",
            "ml-dsa",
            "dilithium",
        )
    ):
        return "signature"
    if any(k in fam for k in ("ecdh", "dh", "x25519", "x448")):
        return "key-agree"
    if any(k in fam for k in ("kem", "kyber", "ml-kem", "frodo")):
        return "kem"
    if any(k in fam for k in ("aes-gcm", "chacha20-poly1305", "ae")):
        return "ae"
    if any(k in fam for k in ("aes", "des", "3des", "blowfish", "camellia", "aria")):
        return "block-cipher"
    if any(k in fam for k in ("rc4", "chacha", "salsa")):
        return "stream-cipher"
    if any(
        k in fam
        for k in (
            "sha2",
            "sha3",
            "sha-256",
            "sha-384",
            "sha-512",
            "sha-1",
            "sha1",
            "sha256",
            "md5",
            "blake2",
        )
    ):
        return "hash"
    if any(k in fam for k in ("hmac", "cmac", "gmac", "poly1305")):
        return "mac"
    if any(k in fam for k in ("pbkdf2", "scrypt", "argon2", "hkdf")):
        return "kdf"
    if any(k in fam for k in ("drbg", "prng")):
        return "drbg"
    if any(k in fam for k in ("shake", "xof")):
        return "xof"

    if "sign" in purp:
        return "signature"
    if "hash" in purp:
        return "hash"
    if "encrypt" in purp:
        return "block-cipher"
    if "key_agree" in purp or "key-exchange" in purp:
        return "key-agree"
    if "kem" in purp:
        return "kem"
    if "mac" in purp:
        return "mac"

    return "other"


def _map_crypto_functions(purpose: str, primitive: str) -> list[str]:
    """Map purpose and primitive to CycloneDX 1.6 cryptoFunctions enum list."""
    purp = (purpose or "").lower()
    funcs = set()
    if any(k in purp for k in ("encrypt", "confidentiality")):
        funcs.add("encrypt")
        funcs.add("decrypt")
    if any(k in purp for k in ("sign", "auth", "signature")):
        funcs.add("sign")
        funcs.add("verify")
    if any(k in purp for k in ("hash", "digest", "integrity")):
        funcs.add("digest")
    if any(k in purp for k in ("mac", "tag")):
        funcs.add("tag")
    if any(k in purp for k in ("key_derive", "kdf")):
        funcs.add("keyderive")
    if any(k in purp for k in ("key_exchange", "key_agreement", "kem")):
        funcs.add("encapsulate")
        funcs.add("decapsulate")
    if not funcs:
        if primitive in ("pke", "block-cipher", "stream-cipher", "ae"):
            funcs.update(["encrypt", "decrypt"])
        elif primitive == "signature":
            funcs.update(["sign", "verify"])
        elif primitive == "hash":
            funcs.add("digest")
        elif primitive == "mac":
            funcs.add("tag")
        elif primitive == "kem":
            funcs.update(["encapsulate", "decapsulate"])
        else:
            funcs.add("other")
    return sorted(funcs)


def export_assessment_cyclonedx(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Generate CycloneDX 1.6 compliant CBOM JSON dictionary from an assessment snapshot.

    Includes cryptoProperties, Quantum Flow extension properties, and visible dependency
    graph diagnostics for unresolved relationships without producing invalid schema documents.
    """
    raw_assessment_id = snapshot.get("assessment_id") or ""
    try:
        doc_uuid = str(uuid.UUID(str(raw_assessment_id)))
    except (ValueError, TypeError):
        doc_uuid = str(uuid.uuid4())

    target_snapshot = snapshot.get("target_snapshot") or {}
    target_hostname = target_snapshot.get("hostname", "Unknown Target")
    title = snapshot.get("title", f"CBOM for {target_hostname}")
    risk_summary = snapshot.get("risk_summary") or {}
    max_qvi = str(
        risk_summary.get("max_asset_qvi")
        or risk_summary.get("overall_score")
        or snapshot.get("qvi_score")
        or 0
    )

    metadata_properties = [
        {"name": "qft:assessment_id", "value": str(raw_assessment_id)},
        {"name": "qft:target_id", "value": str(target_snapshot.get("id") or "")},
        {"name": "qft:scope_hash", "value": str(snapshot.get("scope_hash") or "")},
        {
            "name": "qft:methodology_version",
            "value": str(snapshot.get("methodology_version") or "QFT-RISK-v1.0"),
        },
        {"name": "qft:max_asset_qvi", "value": max_qvi},
    ]

    components: list[dict[str, Any]] = []
    assets = snapshot.get("assets") or []

    for a in assets:
        asset_type = a.get("asset_type", "algorithm_usage")
        asset_key = a.get("asset_key") or str(uuid.uuid4())
        display_name = a.get("display_name") or a.get("algorithm_name") or "Unknown Asset"
        family = a.get("algorithm_family") or "Generic"
        algo_name = a.get("algorithm_name") or family
        purpose = a.get("cryptographic_purpose") or "unknown"
        locator = a.get("locator") or f"{family} cryptographic asset"
        params = a.get("parameters") or {}

        crypto_props: dict[str, Any]
        if asset_type == "certificate":
            cert_props: dict[str, Any] = {
                "subjectName": str(
                    params.get("subject_dn") or params.get("subject_cn") or display_name
                ),
                "issuerName": str(
                    params.get("issuer_dn") or params.get("issuer_cn") or "Unknown CA"
                ),
                "certificateFormat": "X.509",
            }
            if params.get("valid_from"):
                cert_props["notValidBefore"] = str(params["valid_from"])
            if params.get("valid_until"):
                cert_props["notValidAfter"] = str(params["valid_until"])

            crypto_props = {
                "assetType": "certificate",
                "certificateProperties": cert_props,
            }
        elif asset_type in ("protocol", "endpoint_config"):
            cipher_suites = []
            if params.get("cipher_suite"):
                cipher_suites.append({"name": str(params["cipher_suite"])})
            elif a.get("algorithm_name"):
                cipher_suites.append({"name": str(a["algorithm_name"])})

            crypto_props = {
                "assetType": "protocol",
                "protocolProperties": {
                    "type": "tls",
                    "version": str(params.get("protocol_version") or "1.3"),
                    "cipherSuites": cipher_suites,
                },
            }
        else:
            primitive = _map_primitive(family, purpose)
            crypto_funcs = _map_crypto_functions(purpose, primitive)
            crypto_props = {
                "assetType": "algorithm",
                "algorithmProperties": {
                    "primitive": primitive,
                    "parameterSetIdentifier": str(algo_name),
                    "cryptoFunctions": crypto_funcs,
                },
            }

        component_properties = [
            {"name": "qft:qvi_score", "value": str(a.get("risk_score") or 0)},
            {
                "name": "qft:risk_category",
                "value": str(a.get("risk_category") or "unknown").upper(),
            },
            {
                "name": "qft:quantum_threat",
                "value": str(a.get("quantum_threat_type") or "unknown"),
            },
            {
                "name": "qft:evidence_quality",
                "value": str(a.get("evidence_quality") or "medium"),
            },
            {
                "name": "qft:classification",
                "value": str(a.get("classification") or "OBSERVED"),
            },
            {
                "name": "qft:methodology_version",
                "value": str(snapshot.get("methodology_version") or "QFT-RISK-v1.0"),
            },
            {"name": "qft:asset_key", "value": str(asset_key)},
            {"name": "qft:locator", "value": str(locator)},
            {"name": "qft:cryptographic_purpose", "value": str(purpose)},
        ]

        component: dict[str, Any] = {
            "type": "cryptographic-asset",
            "bom-ref": str(asset_key),
            "name": str(display_name),
            "description": str(locator),
            "cryptoProperties": crypto_props,
            "properties": component_properties,
        }
        components.append(component)

    component_refs = {c["bom-ref"] for c in components}
    dependencies: list[dict[str, Any]] = []
    unresolved_count = 0
    relationships = snapshot.get("relationships") or []

    for rel in relationships:
        src = str(rel.get("source_asset_key") or rel.get("source_key") or rel.get("source") or "")
        tgt = str(rel.get("target_asset_key") or rel.get("target_key") or rel.get("target") or "")
        if src in component_refs and tgt in component_refs:
            dependencies.append({"ref": src, "dependsOn": [tgt]})
        else:
            unresolved_count += 1
            metadata_properties.append(
                {
                    "name": "qft:export_diagnostics:unresolved_dependency",
                    "value": f"source:{src}->target:{tgt} (missing component bom-ref)",
                }
            )

    if unresolved_count > 0:
        metadata_properties.append(
            {
                "name": "qft:dependency_graph_status",
                "value": "INCOMPLETE_RELATIONSHIPS_RECORDED",
            }
        )
        metadata_properties.append(
            {
                "name": "qft:warning:incomplete_dependency_graph",
                "value": f"WARNING: {unresolved_count} cryptographic relationships could not be resolved in the component inventory",
            }
        )
        metadata_properties.append(
            {
                "name": "qft:comment",
                "value": (
                    f"WARNING: CBOM dependency graph contains {unresolved_count} unresolved relationships. "
                    "See qft:export_diagnostics in metadata.properties."
                ),
            }
        )

    metadata: dict[str, Any] = {
        "timestamp": str(
            snapshot.get("completed_at")
            or snapshot.get("started_at")
            or datetime.now(UTC).isoformat()
        ),
        "tools": {
            "components": [
                {
                    "type": "application",
                    "name": "Quantum Flow PQC Scanner",
                    "version": "1.0.0",
                }
            ]
        },
        "component": {
            "type": "application",
            "name": str(target_hostname),
            "description": str(title),
        },
        "properties": metadata_properties,
    }

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{doc_uuid}",
        "version": 1,
        "metadata": metadata,
        "components": components,
        "dependencies": dependencies,
    }


def export_assessment_csv(snapshot: dict[str, Any]) -> str:
    """Generate RFC 4180 CRLF compliant CSV asset inventory with formula-injection defense.

    Output records are delimited strictly with CRLF (\\r\\n). All columns are sanitized
    without mutating the input snapshot data.
    """
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")

    headers = [
        "Assessment ID",
        "Target Hostname",
        "Asset Key",
        "Asset Type",
        "Display Name",
        "Algorithm Family",
        "Algorithm Name",
        "Cryptographic Purpose",
        "Locator",
        "Business Criticality",
        "Classification",
        "Confidence Score",
        "QVI Risk Score",
        "Risk Category",
        "Quantum Threat Type",
        "Remediation Priority",
    ]
    writer.writerow([sanitize_csv_field(h) for h in headers])

    assessment_id = str(snapshot.get("assessment_id") or "")
    target_hostname = str((snapshot.get("target_snapshot") or {}).get("hostname", ""))
    assets = snapshot.get("assets") or []

    for a in assets:
        risk_score_val = a.get("risk_score")
        risk_score_str = str(risk_score_val) if risk_score_val is not None else "N/A"

        confidence_val = a.get("confidence_score")
        confidence_str = f"{float(confidence_val):.2f}" if confidence_val is not None else "1.00"

        row = [
            assessment_id,
            target_hostname,
            str(a.get("asset_key") or ""),
            str(a.get("asset_type") or "algorithm_usage"),
            str(a.get("display_name") or a.get("algorithm_name") or "Unknown Asset"),
            str(a.get("algorithm_family") or "Unknown"),
            str(a.get("algorithm_name") or a.get("algorithm_family") or "Unknown"),
            str(a.get("cryptographic_purpose") or "unknown"),
            str(a.get("locator") or ""),
            str(a.get("business_criticality") or "medium"),
            str(a.get("classification") or "OBSERVED"),
            confidence_str,
            risk_score_str,
            str(a.get("risk_category") or "unknown").upper(),
            str(a.get("quantum_threat_type") or "unknown"),
            str(a.get("remediation_priority") or "medium").upper(),
        ]
        writer.writerow([sanitize_csv_field(c) for c in row])

    return output.getvalue()


def export_assessment_markdown_report(
    snapshot: dict[str, Any], stored_hash: str | None = None
) -> str:
    """Generate human-readable executive Markdown summary report.

    Details Maximum Asset QVI, category distribution, network evidence, Shor/Grover
    threat profiles, NIST remediation roadmaps, and explicit distinctions between
    Python AST analysis and JavaScript/TypeScript/Java heuristic analysis.
    """
    raw_assessment_id = snapshot.get("assessment_id") or "N/A"
    title = snapshot.get("title") or "Post-Quantum Cryptographic Assessment Report"
    status = str(snapshot.get("status") or "completed").upper()
    target_snapshot = snapshot.get("target_snapshot") or {}
    hostname = target_snapshot.get("hostname", "Unknown Target")
    environment = target_snapshot.get("environment", "production")
    criticality = target_snapshot.get("business_criticality", "high")
    completed_at = snapshot.get("completed_at") or snapshot.get("started_at") or "N/A"
    methodology = snapshot.get("methodology_version") or "QFT-RISK-v1.0"
    engine_ver = snapshot.get("engine_version") or "v1.0.0"

    risk_summary = snapshot.get("risk_summary") or {}
    max_qvi = (
        risk_summary.get("max_asset_qvi")
        or risk_summary.get("overall_score")
        or snapshot.get("qvi_score")
        or 0
    )
    overall_cat = (
        risk_summary.get("risk_category") or snapshot.get("risk_category") or "MEDIUM"
    ).upper()

    assets = snapshot.get("assets") or []
    asset_count = len(assets)

    scores = [a.get("risk_score") for a in assets if a.get("risk_score") is not None]
    mean_qvi = sum(scores) / len(scores) if scores else 0.0

    critical_count = sum(1 for a in assets if str(a.get("risk_category", "")).upper() == "CRITICAL")
    high_count = sum(1 for a in assets if str(a.get("risk_category", "")).upper() == "HIGH")
    medium_count = sum(1 for a in assets if str(a.get("risk_category", "")).upper() == "MEDIUM")
    low_count = sum(1 for a in assets if str(a.get("risk_category", "")).upper() == "LOW")
    negligible_count = sum(
        1 for a in assets if str(a.get("risk_category", "")).upper() in ("NEGLIGIBLE", "GUARDED")
    )

    digest_hash = stored_hash or snapshot.get("report_snapshot_hash") or "N/A"

    lines: list[str] = [
        "# Quantum Flow — Post-Quantum Cryptographic Assessment Report",
        "",
        f"**Assessment Title:** {title}  ",
        f"**Assessment ID:** `{raw_assessment_id}`  ",
        f"**Target Hostname:** `{hostname}` ({environment} / {criticality})  ",
        f"**Assessment Status:** `{status}`  ",
        f"**Timestamp (UTC):** {completed_at}  ",
        f"**Methodology:** {methodology} | **Engine Version:** {engine_ver}  ",
        "",
        "> [!NOTE]",
        f"> **Integrity Verification:** Canonical Snapshot Digest SHA-256: `{digest_hash}` (Verified)  ",
        "> *Note: SHA-256 canonical snapshot digest match confirmed. This indicates cryptographic evidence integrity against modification, not an asymmetric digital signature by a third-party certificate authority.*",
        "",
        "## 1. Executive Summary",
        "",
        f"- **Maximum Asset QVI:** **{max_qvi} / 1000** ({overall_cat})",
        f"- **Mean Asset QVI:** **{mean_qvi:.1f} / 1000** across {asset_count} cryptographic assets",
        f"- **Post-Quantum Posture:** {'High quantum exposure detected. Migration planning recommended.' if int(max_qvi) >= 400 else 'Manageable risk profile under current methodology.'}",
        "",
        "### Asset Risk Distribution",
        "",
        "| Risk Category | Asset Count | Proportion |",
        "|---|---:|---:|",
        f"| **CRITICAL** (800–1000) | {critical_count} | {(critical_count / asset_count * 100) if asset_count else 0:.1f}% |",
        f"| **HIGH** (600–799) | {high_count} | {(high_count / asset_count * 100) if asset_count else 0:.1f}% |",
        f"| **MEDIUM** (400–599) | {medium_count} | {(medium_count / asset_count * 100) if asset_count else 0:.1f}% |",
        f"| **LOW** (200–399) | {low_count} | {(low_count / asset_count * 100) if asset_count else 0:.1f}% |",
        f"| **NEGLIGIBLE** (0–199) | {negligible_count} | {(negligible_count / asset_count * 100) if asset_count else 0:.1f}% |",
        "",
        "---",
        "",
        "## 2. Observation Scope & Discovery Mechanisms",
        "",
        f"- **Target Domain:** `{hostname}` (SSRF Protection: Pinned Destination IP active)",
        "- **Discovery Collectors & Analysis Mechanisms:**",
        "  - **Network TLS Discovery:** Bounded socket handshake & X.509 certificate chain extraction.",
        "  - **Python Source Discovery:** Native Python AST parsing (`ast.parse` and `ast.NodeVisitor`) for syntactic cryptographic call inspection.",
        "  - **JavaScript / TypeScript Discovery:** Lexical and regex heuristic pattern matching (not AST parsing).",
        "  - **Java Discovery:** Lexical and token stream pattern matching (not AST parsing).",
        "  - **Dependency Manifest Scanning:** Structured package dependency manifest parsing (`requirements.txt`, `package.json`, `poetry.lock`, `pom.xml`).",
        "",
        "---",
        "",
        "## 3. Cryptographic Asset Inventory & Primitives Summary",
        "",
        "| Asset Key | Type | Display Name | Algorithm / Primitives | Purpose | Risk QVI | Category |",
        "|---|---|---|---|---|---:|:---:|",
    ]

    for a in assets:
        key = str(a.get("asset_key", ""))
        atype = str(a.get("asset_type", "algorithm"))
        name = str(a.get("display_name") or a.get("algorithm_name") or "Unknown")
        algo = str(a.get("algorithm_name") or a.get("algorithm_family") or "Unknown")
        purp = str(a.get("cryptographic_purpose") or "unknown")
        qvi = str(a.get("risk_score") if a.get("risk_score") is not None else "N/A")
        cat = str(a.get("risk_category") or "unknown").upper()
        lines.append(f"| `{key}` | {atype} | {name} | {algo} | {purp} | **{qvi}** | {cat} |")

    relationships = snapshot.get("relationships") or []
    component_refs = {str(a.get("asset_key")) for a in assets}
    unresolved_rels = [
        r
        for r in relationships
        if str(r.get("source_asset_key") or r.get("source") or "") not in component_refs
        or str(r.get("target_asset_key") or r.get("target") or "") not in component_refs
    ]

    if unresolved_rels:
        lines.extend(
            [
                "",
                "> [!WARNING]",
                f"> **Dependency Graph Incomplete:** {len(unresolved_rels)} cryptographic relationships could not be linked to inventoried components. See export diagnostics for details.",
            ]
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 4. Quantum Threat Analysis (Methodology v1.0)",
            "",
            "- **Shor's Algorithm Vulnerability:**",
            "  Asymmetric algorithms (RSA, ECDSA, ECDH) are exposed to polynomial-time factorisation and discrete logarithm attacks on Cryptographically Relevant Quantum Computers (CRQCs). Assets relying on these primitives have critical vulnerability windows.",
            "- **Grover's Algorithm Speedup:**",
            "  Symmetric ciphers and hash functions experience a theoretical quadratic speedup on unstructured search. A 128-bit symmetric key provides an effective ~64-bit security margin against an idealized quantum adversary; 256-bit symmetric keys provide ~128 bits of security margin.",
            "",
            "---",
            "",
            "## 5. Prioritised Remediation Roadmap (NIST Standards)",
            "",
            "Recommendations aligned with NIST Post-Quantum Cryptography standards:",
            "- **FIPS 203 (ML-KEM):** Transition key encapsulation mechanisms from RSA/ECDH to ML-KEM-768 or ML-KEM-1024.",
            "- **FIPS 204 (ML-DSA):** Upgrade public-key signatures to ML-DSA-65 or ML-DSA-87.",
            "- **FIPS 205 (SLH-DSA):** Deploy stateless hash-based signatures for firmware and long-term root-of-trust authentication.",
            "",
        ]
    )

    recs = snapshot.get("recommendations") or []
    if not recs:
        lines.append("_No specific remediation steps required for currently observed assets._")
    else:
        for idx, r in enumerate(recs, start=1):
            prio = str(r.get("priority", "medium")).upper()
            rtitle = r.get("title", "Remediation Action")
            desc = r.get("description", "")
            lines.append(f"### {idx}. [{prio}] {rtitle}")
            lines.append(f"{desc}")
            lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## 6. Coverage Limitations & Governance Disclaimer",
            "",
            "> [!IMPORTANT]",
            "> **Absence of discovery evidence from unexamined sources does NOT constitute proof of post-quantum safety.**",
            "> This assessment is strictly bounded by the evidence gathered during execution. Unexamined microservices, internal network segments, or omitted source repositories may harbor unmitigated cryptographic vulnerabilities.",
        ]
    )

    return "\n".join(lines)


# ==============================================================================
# Preserved Sprint 2 Asset & Risk Exporters (Backward Compatibility)
# ==============================================================================


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
    """Generate comprehensive JSON assessment report for a single asset."""
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
    """Generate human-readable executive Markdown summary for a single asset."""
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
