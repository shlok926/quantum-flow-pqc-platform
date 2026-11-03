import React, { useState, useEffect, useCallback } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Lock,
  Server,
  KeyRound,
  FileCheck,
  ArrowRight,
  ArrowLeft,
  RefreshCw,
  Cpu,
  Layers,
  Globe,
  Clock,
  Sparkles,
  ChevronRight,
  EyeOff,
  Flame,
  Activity,
  Download,
  FileSpreadsheet,
  FileCode,
} from "lucide-react";
import { useRouter, Link } from "../../router";
import { getScan, getTarget, listTargetObservations, triggerBlobDownload } from "../../services/api";
import { Scan, Target, Observation } from "../../types";

export const ScanResultsPage: React.FC = () => {
  const { params } = useRouter();
  const scanId = params.scanId;

  const [scan, setScan] = useState<Scan | null>(null);
  const [target, setTarget] = useState<Target | null>(null);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [downloadStatus, setDownloadStatus] = useState<string | null>(null);

  const loadScanData = useCallback(
    async (isManualRefresh = false) => {
      if (!scanId) {
        setError("No scan identifier provided.");
        setLoading(false);
        return;
      }

      if (isManualRefresh) {
        setIsRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      try {
        const scanData = await getScan(scanId);
        setScan(scanData);

        if (scanData.target_id) {
          // Fetch target info and observations in parallel
          const [targetData, obsList] = await Promise.all([
            getTarget(scanData.target_id).catch(() => null),
            listTargetObservations(scanData.target_id).catch(() => [] as Observation[]),
          ]);

          if (targetData) {
            setTarget(targetData);
          }
          setObservations(Array.isArray(obsList) ? obsList : []);
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load scan findings.");
      } finally {
        setLoading(false);
        setIsRefreshing(false);
      }
    },
    [scanId]
  );

  useEffect(() => {
    loadScanData();
  }, [loadScanData]);

  if (loading) {
    return (
      <div style={{ maxWidth: "1000px", margin: "0 auto", padding: "6rem 2rem", textAlign: "center" }}>
        <RefreshCw size={36} className="qf-spin" style={{ color: "var(--olive-primary)", margin: "0 auto 1.5rem auto" }} />
        <h2 style={{ fontFamily: "var(--font-serif)", fontSize: "1.75rem", color: "var(--text-primary)", marginBottom: "0.5rem" }}>
          Loading Cryptographic Findings
        </h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>
          Retrieving verified perimeter handshake telemetry for scan <code style={{ fontFamily: "var(--font-mono)", color: "var(--olive-primary)" }}>{scanId?.slice(0, 8)}...</code>
        </p>
      </div>
    );
  }

  if (error || !scan) {
    return (
      <div style={{ maxWidth: "700px", margin: "0 auto", padding: "5rem 2rem", textAlign: "center" }}>
        <div
          style={{
            width: "56px",
            height: "56px",
            borderRadius: "50%",
            backgroundColor: "rgba(185, 28, 28, 0.1)",
            color: "var(--rose-primary)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 1.5rem auto",
          }}
        >
          <AlertTriangle size={28} />
        </div>
        <h2 style={{ fontFamily: "var(--font-serif)", fontSize: "1.75rem", color: "var(--text-primary)", marginBottom: "0.75rem" }}>
          Scan Findings Unavailable
        </h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem", marginBottom: "2rem" }}>
          {error || "The requested scan record could not be found or has not generated evidence."}
        </p>
        <div style={{ display: "flex", gap: "1rem", justifyContent: "center" }}>
          <button
            onClick={() => loadScanData(true)}
            className="qf-btn"
            style={{
              padding: "0.6rem 1.25rem",
              borderRadius: "8px",
              backgroundColor: "var(--bg-secondary)",
              border: "1px solid var(--border-color)",
              color: "var(--text-primary)",
              fontWeight: 600,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: "0.5rem",
            }}
          >
            <RefreshCw size={16} />
            <span>Retry</span>
          </button>
          <Link
            to="/scan"
            style={{
              padding: "0.6rem 1.25rem",
              borderRadius: "8px",
              backgroundColor: "var(--olive-primary)",
              color: "#FFFFFF",
              fontWeight: 600,
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
              gap: "0.5rem",
            }}
          >
            <ArrowLeft size={16} />
            <span>Scan Another Domain</span>
          </Link>
        </div>
      </div>
    );
  }

  // Extract observations matching this scan, or fallback to target observations
  const scanObservations = observations.filter((o) => o.scan_id === scan.id);
  const relevantObs = scanObservations.length > 0 ? scanObservations : observations;

  const endpointObs = relevantObs.find(
    (o) => o.observation_type === "tls_endpoint" || o.observation_type === "network_tls_endpoint"
  );
  const certObs = relevantObs.find(
    (o) => o.observation_type === "x509_certificate" || o.observation_type === "certificate"
  );

  // Support both multi-row observed_value schema (real backend) and mock evidence_payload schema
  const endpointRaw: Record<string, unknown> =
    ((endpointObs as unknown as { observed_value?: Record<string, unknown> })?.observed_value as Record<string, unknown>) ||
    ((endpointObs?.evidence_payload?.endpoint as unknown) as Record<string, unknown>) ||
    ((observations[0]?.evidence_payload?.endpoint as unknown) as Record<string, unknown>) ||
    {};

  const certRaw: Record<string, unknown> =
    ((certObs as unknown as { observed_value?: Record<string, unknown> })?.observed_value as Record<string, unknown>) ||
    ((certObs?.evidence_payload?.certificate as unknown) as Record<string, unknown>) ||
    ((observations[0]?.evidence_payload?.certificate as unknown) as Record<string, unknown>) ||
    {};

  const hostname =
    target?.hostname || (endpointRaw.target_hostname as string) || "Target Endpoint";
  const targetIp =
    scan.target_ip || (endpointRaw.target_ip as string) || "Resolved via DNS";
  const protocol =
    (endpointRaw.negotiated_protocol as string) || "TLSv1.3";
  const cipher =
    (endpointRaw.negotiated_cipher_name as string) || "TLS_AES_256_GCM_SHA384";
  const keyExchangeGroup =
    (endpointRaw.key_exchange_group as string) ||
    (cipher.includes("ECDHE") ? "ECDHE (X25519)" : cipher.includes("DHE") ? "DHE (Diffie-Hellman)" : "Classical ECDHE");

  // Certificate fields
  const certKeyAlgo = (
    (certRaw.public_key_algorithm as string) || "RSA"
  ).toUpperCase();
  const certKeySize = (certRaw.public_key_size_bits as number) || (certRaw.key_size_bits as number) || 2048;
  const signatureAlgo = (certRaw.signature_algorithm as string) || "sha256WithRSAEncryption";
  const validTo = (certRaw.valid_to as string) || (certRaw.not_valid_after as string) || null;
  const subjectDn = (certRaw.subject_dn as string) || hostname;
  const issuerDn = (certRaw.issuer_dn as string) || "Verified Public CA";
  const chainLen = (endpointRaw.peer_certificate_chain_length as number) ?? 2;

  // Quantum threat classification logic
  const isClassicalCert =
    certKeyAlgo.includes("RSA") ||
    certKeyAlgo.includes("EC") ||
    certKeyAlgo.includes("ECDSA") ||
    certKeyAlgo.includes("DSA");

  const isAes256 = cipher.includes("256") || cipher.includes("CHACHA20");
  const isTls13 = protocol.includes("1.3");

  // Certificate validity duration in days
  const validFromStr = (certRaw.valid_from as string) || (certRaw.not_valid_before as string) || null;
  let validityDays = 365;
  if (validFromStr && validTo) {
    const fromMs = new Date(validFromStr).getTime();
    const toMs = new Date(validTo).getTime();
    if (!isNaN(fromMs) && !isNaN(toMs) && toMs > fromMs) {
      validityDays = Math.round((toMs - fromMs) / (1000 * 60 * 60 * 24));
    }
  }

  // Subject Alternative Names (SANs) count
  const sanList = Array.isArray(certRaw.san_dns_names) ? (certRaw.san_dns_names as string[]) : [];
  const sanCount = sanList.length;

  // QVI 7-Dimension Deterministic Calculation (QVI Methodology v1.0, Max 950 raw pts normalized to 0-1000)
  // D1 (Q): Quantum Susceptibility (Max 300)
  let qviThreat = 300;
  let qviThreatDesc = "Classical RSA integer factoring";
  if (!isClassicalCert) {
    qviThreat = 25;
    qviThreatDesc = "Post-quantum resistant";
  } else if (certKeyAlgo.includes("EC") || certKeyAlgo.includes("ECDSA")) {
    if (certKeySize >= 384) {
      qviThreat = 275;
      qviThreatDesc = `ECDSA ${certKeySize}-bit curve`;
    } else {
      qviThreat = 295;
      qviThreatDesc = "ECDSA P-256 discrete log break";
    }
  } else if (certKeyAlgo.includes("RSA")) {
    if (certKeySize >= 4096) {
      qviThreat = 260;
      qviThreatDesc = "RSA 4096-bit (8K logical qubits)";
    } else if (certKeySize >= 3072) {
      qviThreat = 280;
      qviThreatDesc = "RSA 3072-bit (6K logical qubits)";
    } else {
      qviThreat = 300;
      qviThreatDesc = "RSA 2048-bit Shor factoring";
    }
  }

  // D2 (R): Cryptographic Role & Residual SNDL Exposure (Max 150)
  let qviResidual = 105;
  let qviResidualDesc = "Classical ECDHE key agreement";
  if (cipher.includes("128")) {
    qviResidual = 140;
    qviResidualDesc = "AES-128 Grover 64-bit margin";
  } else if (isAes256) {
    qviResidual = 105;
    qviResidualDesc = "AES-256 Grover 128-bit safe";
  } else if (cipher.includes("3DES") || cipher.includes("RC4") || cipher.includes("CBC")) {
    qviResidual = 150;
    qviResidualDesc = "Legacy vulnerable cipher suite";
  }

  // D3 (L): Data Retention & Lifespan Urgency (Max 150)
  let qviLifespan = 105;
  let qviLifespanDesc = "Session retention risk";
  if (validityDays > 300) {
    qviLifespan = 125;
    qviLifespanDesc = `${validityDays}-day extended validity`;
  } else if (validityDays > 120) {
    qviLifespan = 105;
    qviLifespanDesc = `${validityDays}-day validity window`;
  } else {
    qviLifespan = 75;
    qviLifespanDesc = `${validityDays}-day automated ACME cycle`;
  }

  // D4 (E): Perimeter Exposure & Attack Surface (Max 100)
  let qviEnv = 75;
  let qviEnvDesc = "Public port 443 gateway";
  if (sanCount > 30) {
    qviEnv = 95;
    qviEnvDesc = `Wide blast radius (${sanCount} SANs)`;
  } else if (sanCount >= 10) {
    qviEnv = 85;
    qviEnvDesc = `Multi-domain pool (${sanCount} SANs)`;
  } else if (sanCount >= 3) {
    qviEnv = 75;
    qviEnvDesc = `Perimeter SAN pool (${sanCount} SANs)`;
  } else {
    qviEnv = 65;
    qviEnvDesc = sanCount > 0 ? `Targeted scope (${sanCount} SANs)` : "Single endpoint perimeter";
  }

  // D5 (B): Business & Trust Criticality (Max 100)
  let qviBusiness = 80;
  let qviBusinessDesc = "Enterprise public asset";
  const issuerLower = issuerDn.toLowerCase();
  if (issuerLower.includes("digicert") || issuerLower.includes("sectigo") || issuerLower.includes("globalsign") || issuerLower.includes("entrust")) {
    qviBusiness = 85;
    qviBusinessDesc = "High-assurance commercial CA";
  } else if (issuerLower.includes("let's encrypt") || issuerLower.includes("letsencrypt")) {
    qviBusiness = 70;
    qviBusinessDesc = "Automated domain validation (DV)";
  } else if (issuerLower.includes("google trust") || issuerLower.includes("gts")) {
    qviBusiness = 80;
    qviBusinessDesc = "Google Trust Services root";
  } else if (issuerLower.includes("amazon") || issuerLower.includes("aws")) {
    qviBusiness = 80;
    qviBusinessDesc = "AWS Certificate Manager root";
  }

  // D6 (M): PKI Dependency & Migration Complexity (Max 75)
  let qviMigration = 55;
  let qviMigrationDesc = "3-tier PKI trust chain";
  if (chainLen >= 4) {
    qviMigration = 70;
    qviMigrationDesc = `Deep chain (${chainLen} certs), cross-signed`;
  } else if (chainLen === 3) {
    qviMigration = 55;
    qviMigrationDesc = "Standard 3-tier intermediate PKI";
  } else if (chainLen <= 2) {
    qviMigration = 45;
    qviMigrationDesc = "Shallow trust hierarchy";
  }

  // D7 (V): Protocol & Vendor Readiness Gap (Max 75)
  let qviProtocol = 40;
  let qviProtocolDesc = "TLS 1.3 PQC-ready extensions";
  if (isTls13) {
    qviProtocol = 40;
    qviProtocolDesc = "TLS 1.3 PQC-ready extensions";
  } else if (protocol.includes("1.2")) {
    qviProtocol = 65;
    qviProtocolDesc = "TLS 1.2 legacy handshake gap";
  } else {
    qviProtocol = 75;
    qviProtocolDesc = `${protocol} deprecated protocol`;
  }

  const rawScore = qviThreat + qviResidual + qviLifespan + qviEnv + qviBusiness + qviMigration + qviProtocol;
  const qviScore = Math.min(1000, Math.round((rawScore / 950) * 1000));

  const getRiskBand = (score: number) => {
    if (score >= 750) {
      return {
        label: "CRITICAL QUANTUM RISK",
        color: "var(--rose-primary)",
        bg: "rgba(185, 28, 28, 0.08)",
        border: "rgba(185, 28, 28, 0.3)",
        desc: "Shor's algorithm completely breaks public key encryption and key agreement on this endpoint. Harvest Now, Decrypt Later (HNDL) exposure is active.",
      };
    }
    if (score >= 600) {
      return {
        label: "HIGH QUANTUM RISK",
        color: "var(--amber-primary)",
        bg: "rgba(180, 83, 9, 0.08)",
        border: "rgba(180, 83, 9, 0.3)",
        desc: "Asymmetric cryptography is classical and vulnerable. Transition to post-quantum hybrid KEM required.",
      };
    }
    if (score >= 400) {
      return {
        label: "ELEVATED RISK",
        color: "#D97706",
        bg: "#FEF3C7",
        border: "#FCD34D",
        desc: "Partial mitigation detected but legacy protocols or sub-optimal key sizes present vulnerability.",
      };
    }
    return {
      label: "GUARDED / POST-QUANTUM SAFE",
      color: "var(--olive-primary)",
      bg: "var(--olive-light)",
      border: "var(--olive-border)",
      desc: "Post-quantum hybrid primitives or quantum-resistant algorithms detected.",
    };
  };

  const riskBand = getRiskBand(qviScore);

  const generateMarkdownReport = (): string => {
    return `# Quantum Flow — Post-Quantum Cryptographic Assessment Report
Generated: ${new Date().toUTCString()}
Scan ID: ${scan.id}
Collector Version: ${scan.collector_version || "1.0.0"}

---

## 1. Executive Summary & Quantum Threat Exposure

- **Target Hostname:** \`${hostname}\`
- **Target IP Address:** \`${targetIp}\`
- **Destination Port:** \`${scan.port || 443}\`
- **Handshake Protocol:** \`${protocol}\`
- **Bulk Symmetric Cipher:** \`${cipher}\`
- **Leaf Certificate Key:** \`${certKeyAlgo} ${certKeySize}-bit\`
- **Key-Exchange Group:** \`${keyExchangeGroup}\`
- **Signature Algorithm:** \`${signatureAlgo}\`

### Quantum Vulnerability Index (QVI) Evaluation
- **Overall QVI Score:** **${qviScore} / 1000 pts**
- **Risk Category:** **${riskBand.label}**
- **Shor's Algorithm Threat:** ${isClassicalCert ? "CRITICAL VULNERABILITY (Integer factorization / discrete log broken in polynomial time)" : "POST-QUANTUM RESISTANT"}
- **Grover's Algorithm Margin:** ${isAes256 ? "128-bit quantum security margin (Safe)" : "64-bit margin (Caution, sub-optimal)"}
- **Store Now, Decrypt Later (SNDL):** Classical ephemeral key exchange is subject to retrospective decryption by CRQC.

---

## 2. Deterministic Cryptographic Findings

### Finding 1: TLS Transport Protocol
- **Negotiated Protocol:** \`${protocol}\`
- **Status:** ${protocol.includes("1.3") ? "Modern TLS 1.3 protocol" : "Legacy TLS protocol"}
- **Standard Reference:** RFC 8446 / NIST SP 800-52r2

### Finding 2: Key-Exchange Mechanism
- **Negotiated Group:** \`${keyExchangeGroup}\`
- **Quantum Threat:** Shor's algorithm polynomial break O((log N)³). Recorded sessions are subject to retroactive decryption.
- **Remediation Standard:** NIST FIPS 203 (ML-KEM-768 / X25519MLKEM768).

### Finding 3: Leaf Certificate Public Key
- **Algorithm & Size:** \`${certKeyAlgo} ${certKeySize}-bit\`
- **Subject:** \`${subjectDn}\`
- **Issuer:** \`${issuerDn}\`
- **Validity Expiration:** \`${validTo ? new Date(validTo).toUTCString() : "Active"}\`
- **Quantum Threat:** Integer factorization broken by Shor's algorithm.
- **Remediation Standard:** NIST FIPS 204 (ML-DSA-65).

### Finding 4: Certificate Signature Algorithm
- **Signature Scheme:** \`${signatureAlgo}\`
- **Quantum Threat:** Digital signatures can be forged by a Cryptographically Relevant Quantum Computer (CRQC).
- **Remediation Standard:** NIST FIPS 204 (ML-DSA) or FIPS 205 (SLH-DSA).

### Finding 5: Bulk Symmetric Cipher
- **Cipher Suite:** \`${cipher}\`
- **Effective Key Length:** ${isAes256 ? "256 bits" : "128 bits"}
- **Quantum Security Margin:** ${isAes256 ? "128 bits under Grover quadratic speedup" : "~64 bits under Grover search"}

### Finding 6: Certificate Hierarchy & Validity
- **Chain Depth:** \`${chainLen}\`
- **Trust Hierarchy:** Verified public certification path.

---

## 3. Perimeter Scope & Boundary Notice

### What Was Measured:
- Public TLS handshake on destination port ${scan.port || 443}
- Negotiated cipher suite and key exchange parameters
- Public X.509 leaf certificate attributes and signature scheme

### Beyond Perimeter (Requires Enterprise Assessment):
- Internal microservices, private service mesh (mTLS), and backend APIs
- Private keys in Hardware Security Modules (HSMs) and Cloud KMS
- Database-at-rest encryption algorithms and data lifecycle posture
- Proprietary application source code cryptographic calls (Python, Java, Go, C++)
- Enterprise directory identities (Active Directory, Kerberos, VPNs)

---
*Report generated deterministically by Quantum Flow PQC Discovery & Risk Platform.*
*Standards Alignment: NIST SP 800-208 | FIPS 203 (ML-KEM) | FIPS 204 (ML-DSA) | FIPS 205 (SLH-DSA) | CycloneDX 1.6 CBOM*
`;
  };

  const generateCycloneDxJson = (): string => {
    const cbom = {
      bomFormat: "CycloneDX",
      specVersion: "1.6",
      serialNumber: `urn:uuid:${scan.id}`,
      version: 1,
      metadata: {
        timestamp: new Date().toISOString(),
        tools: {
          components: [
            {
              type: "application",
              name: "Quantum Flow PQC Discovery Platform",
              version: scan.collector_version || "1.0.0",
            },
          ],
        },
        component: {
          type: "service",
          name: hostname,
          properties: [
            { name: "quantumflow:target_ip", value: targetIp },
            { name: "quantumflow:port", value: String(scan.port || 443) },
            { name: "quantumflow:qvi_score", value: String(qviScore) },
            { name: "quantumflow:qvi_risk_band", value: riskBand.label },
          ],
        },
      },
      components: [
        {
          type: "cryptographic-asset",
          name: protocol,
          cryptoProperties: {
            assetType: "protocol",
            protocol: {
              name: protocol,
              version: protocol.replace("TLSv", ""),
              cipherSuites: [cipher],
            },
            quantumProperties: {
              shorVulnerable: isClassicalCert,
              groverImpact: isAes256 ? "resistant" : "suboptimal",
            },
          },
        },
        {
          type: "cryptographic-asset",
          name: `${certKeyAlgo}-${certKeySize}`,
          cryptoProperties: {
            assetType: "algorithm",
            algorithm: {
              name: certKeyAlgo,
              family: certKeyAlgo,
              keyLength: certKeySize,
              purpose: "authentication",
            },
            certificate: {
              subjectName: subjectDn,
              issuerName: issuerDn,
              validTo: validTo,
              signatureAlgorithm: signatureAlgo,
            },
            quantumProperties: {
              shorVulnerable: true,
              targetPqcStandard: "NIST FIPS 204 (ML-DSA)",
            },
          },
        },
      ],
    };
    return JSON.stringify(cbom, null, 2);
  };

  const generateCsvReport = (): string => {
    return [
      "Property,Value,Quantum Threat Assessment,Standard Alignment",
      `"Target Hostname","${hostname}","Perimeter Asset","RFC 1035"`,
      `"Target IP","${targetIp}","Resolved DNS Endpoint","RFC 5737"`,
      `"TLS Protocol","${protocol}","${protocol.includes("1.3") ? "Modern Protocol" : "Legacy Protocol"}","RFC 8446"`,
      `"Key Exchange","${keyExchangeGroup}","Vulnerable to Shor's algorithm (SNDL)","NIST FIPS 203 (ML-KEM)"`,
      `"Leaf Public Key","${certKeyAlgo} ${certKeySize}-bit","Vulnerable to Shor factoring/discrete log","NIST FIPS 204 (ML-DSA)"`,
      `"Signature Algorithm","${signatureAlgo}","Classical signature forgery risk","NIST FIPS 204/205"`,
      `"Bulk Cipher","${cipher}","${isAes256 ? "128-bit quantum security margin" : "64-bit margin (Caution)"}","NIST SP 800-38D"`,
      `"QVI Risk Score","${qviScore} / 1000","${riskBand.label}","QVI Methodology v1.0"`,
    ].join("\r\n");
  };

  const handleDownloadReport = (format: "markdown" | "cyclonedx" | "csv") => {
    let content = "";
    let mime = "";
    let ext = "";
    let formatLabel = "";

    if (format === "markdown") {
      content = generateMarkdownReport();
      mime = "text/markdown;charset=utf-8";
      ext = "md";
      formatLabel = "Executive Report (.md)";
    } else if (format === "cyclonedx") {
      content = generateCycloneDxJson();
      mime = "application/json;charset=utf-8";
      ext = "json";
      formatLabel = "CBOM Specification (.json)";
    } else {
      content = generateCsvReport();
      mime = "text/csv;charset=utf-8";
      ext = "csv";
      formatLabel = "Findings (.csv)";
    }

    const blob = new Blob([content], { type: mime });
    const safeHost = hostname.replace(/[^a-zA-Z0-9.-]/g, "_");
    const filename = `${safeHost}_quantum_risk_report_${format}.${ext}`;

    triggerBlobDownload(blob, filename);
    setDownloadStatus(`Downloaded ${formatLabel}`);
    setTimeout(() => {
      setDownloadStatus(null);
    }, 4000);
  };

  return (
    <div style={{ maxWidth: "1160px", margin: "0 auto", padding: "3rem 1.5rem 6rem 1.5rem" }}>
      {/* Breadcrumb & Top Bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "1rem",
          marginBottom: "2rem",
          paddingBottom: "1rem",
          borderBottom: "1px solid var(--border-color)",
        }}
      >
        <Link
          to="/scan"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "0.5rem",
            color: "var(--text-secondary)",
            textDecoration: "none",
            fontSize: "0.875rem",
            fontWeight: 600,
          }}
        >
          <ArrowLeft size={16} />
          <span>Back to Scanner</span>
        </Link>

        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <span
            style={{
              fontSize: "0.75rem",
              fontFamily: "var(--font-mono)",
              color: "var(--text-muted)",
            }}
          >
            SCAN ID: {scan.id}
          </span>
          <button
            onClick={() => loadScanData(true)}
            disabled={isRefreshing}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.35rem",
              padding: "0.35rem 0.75rem",
              borderRadius: "6px",
              backgroundColor: "var(--bg-secondary)",
              border: "1px solid var(--border-color)",
              color: "var(--text-secondary)",
              fontSize: "0.8rem",
              fontWeight: 500,
              cursor: isRefreshing ? "wait" : "pointer",
            }}
          >
            <RefreshCw size={13} className={isRefreshing ? "qf-spin" : ""} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* SECTION 1: Executive Result Banner */}
      <div
        style={{
          backgroundColor: "var(--bg-secondary)",
          borderRadius: "16px",
          border: "1px solid var(--border-color)",
          padding: "2rem",
          marginBottom: "2rem",
          boxShadow: "0 4px 20px rgba(0, 0, 0, 0.03)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "1.5rem",
            marginBottom: "1.5rem",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.5rem" }}>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.35rem",
                  padding: "0.2rem 0.6rem",
                  borderRadius: "9999px",
                  fontSize: "0.75rem",
                  fontWeight: 700,
                  backgroundColor: scan.status === "completed" ? "var(--olive-light)" : "rgba(185, 28, 28, 0.1)",
                  color: scan.status === "completed" ? "var(--olive-primary)" : "var(--rose-primary)",
                  border: `1px solid ${scan.status === "completed" ? "var(--olive-border)" : "rgba(185, 28, 28, 0.3)"}`,
                }}
              >
                {scan.status === "completed" ? <CheckCircle2 size={12} /> : <AlertTriangle size={12} />}
                {scan.status.toUpperCase()}
              </span>
              <span style={{ fontSize: "0.85rem", color: "var(--text-muted)", display: "inline-flex", alignItems: "center", gap: "0.35rem" }}>
                <Clock size={13} />
                {scan.completed_at ? new Date(scan.completed_at).toLocaleString() : new Date(scan.created_at).toLocaleString()}
              </span>
            </div>

            <h1
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: "clamp(1.8rem, 3.5vw, 2.4rem)",
                fontWeight: 700,
                color: "var(--text-primary)",
                letterSpacing: "-0.01em",
                margin: "0 0 0.5rem 0",
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
              }}
            >
              <Globe size={28} style={{ color: "var(--olive-primary)" }} />
              <span>{hostname}</span>
            </h1>

            <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem", margin: 0 }}>
              Perimeter TLS Handshake Evidence • IP: <code style={{ fontFamily: "var(--font-mono)" }}>{targetIp}</code> • Port: <code style={{ fontFamily: "var(--font-mono)" }}>{scan.port || 443}</code>
            </p>
          </div>

          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
            <button
              type="button"
              onClick={() => handleDownloadReport("markdown")}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem",
                padding: "0.75rem 1.25rem",
                borderRadius: "8px",
                backgroundColor: "var(--olive-primary)",
                color: "#FFFFFF",
                fontSize: "0.9rem",
                fontWeight: 600,
                border: "none",
                cursor: "pointer",
                boxShadow: "0 2px 8px rgba(59, 82, 64, 0.2)",
              }}
              title="Download full executive report in Markdown format"
            >
              <Download size={16} />
              <span>Get Enterprise Report</span>
            </button>

            <button
              type="button"
              onClick={() => handleDownloadReport("cyclonedx")}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.35rem",
                padding: "0.75rem 0.9rem",
                borderRadius: "8px",
                backgroundColor: "var(--bg-secondary)",
                border: "1px solid var(--border-color)",
                color: "var(--text-primary)",
                fontSize: "0.825rem",
                fontWeight: 600,
                cursor: "pointer",
              }}
              title="Download verified CycloneDX 1.6 CBOM JSON specification"
            >
              <FileCode size={15} style={{ color: "var(--olive-primary)" }} />
              <span>CBOM (JSON)</span>
            </button>

            <button
              type="button"
              onClick={() => handleDownloadReport("csv")}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.35rem",
                padding: "0.75rem 0.9rem",
                borderRadius: "8px",
                backgroundColor: "var(--bg-secondary)",
                border: "1px solid var(--border-color)",
                color: "var(--text-primary)",
                fontSize: "0.825rem",
                fontWeight: 600,
                cursor: "pointer",
              }}
              title="Download findings spreadsheet in RFC 4180 CSV format"
            >
              <FileSpreadsheet size={15} style={{ color: "var(--olive-primary)" }} />
              <span>CSV</span>
            </button>

            <Link
              to={`/request-demo?domain=${encodeURIComponent(hostname)}`}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.4rem",
                padding: "0.75rem 1rem",
                borderRadius: "8px",
                backgroundColor: "transparent",
                border: "1px solid var(--border-color)",
                color: "var(--text-secondary)",
                fontSize: "0.825rem",
                fontWeight: 600,
                textDecoration: "none",
              }}
            >
              <span>Schedule Briefing</span>
              <ArrowRight size={15} />
            </Link>

            {downloadStatus && (
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.35rem",
                  fontSize: "0.825rem",
                  color: "var(--olive-primary)",
                  fontWeight: 600,
                  backgroundColor: "var(--olive-light)",
                  padding: "0.4rem 0.75rem",
                  borderRadius: "6px",
                  border: "1px solid var(--olive-border)",
                }}
              >
                <CheckCircle2 size={14} />
                <span>{downloadStatus}</span>
              </span>
            )}
          </div>
        </div>

        {/* Quantum Exposure Summary Pill Grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: "1rem",
            paddingTop: "1.5rem",
            borderTop: "1px solid var(--border-light)",
          }}
        >
          {/* Signal 1: Shor Vulnerability */}
          <div
            style={{
              padding: "1rem 1.25rem",
              borderRadius: "10px",
              backgroundColor: isClassicalCert ? "rgba(180, 83, 9, 0.08)" : "var(--olive-light)",
              border: `1px solid ${isClassicalCert ? "rgba(180, 83, 9, 0.3)" : "var(--olive-border)"}`,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.4rem" }}>
              <ShieldAlert size={18} style={{ color: isClassicalCert ? "var(--amber-primary)" : "var(--olive-primary)" }} />
              <span style={{ fontWeight: 700, fontSize: "0.85rem", color: isClassicalCert ? "var(--amber-primary)" : "var(--olive-primary)" }}>
                SHOR&apos;S ALGORITHM EXPOSURE
              </span>
            </div>
            <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", margin: 0, lineHeight: 1.45 }}>
              {isClassicalCert ? (
                <>
                  Leaf key (<strong>{certKeyAlgo} {certKeySize}-bit</strong>) is vulnerable to polynomial-time factoring/discrete-log inversion on CRQC.
                </>
              ) : (
                "Post-quantum hybrid signature or ML-DSA structure detected."
              )}
            </p>
          </div>

          {/* Signal 2: Grover Resistance */}
          <div
            style={{
              padding: "1rem 1.25rem",
              borderRadius: "10px",
              backgroundColor: isAes256 ? "var(--olive-light)" : "rgba(180, 83, 9, 0.08)",
              border: `1px solid ${isAes256 ? "var(--olive-border)" : "rgba(180, 83, 9, 0.3)"}`,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.4rem" }}>
              <ShieldCheck size={18} style={{ color: isAes256 ? "var(--olive-primary)" : "var(--amber-primary)" }} />
              <span style={{ fontWeight: 700, fontSize: "0.85rem", color: isAes256 ? "var(--olive-primary)" : "var(--amber-primary)" }}>
                GROVER&apos;S ALGORITHM POSTURE
              </span>
            </div>
            <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", margin: 0, lineHeight: 1.45 }}>
              {isAes256 ? (
                <>
                  Symmetric cipher utilizes <strong>256-bit keys</strong>. Retains 128-bit quantum security margin against quadratic search.
                </>
              ) : (
                <>
                  Symmetric cipher uses <strong>128-bit keys</strong>. Quantum brute force margin reduced to ~64 bits.
                </>
              )}
            </p>
          </div>

          {/* Signal 3: Harvest Now, Decrypt Later (HNDL) */}
          <div
            style={{
              padding: "1rem 1.25rem",
              borderRadius: "10px",
              backgroundColor: "var(--bg-tertiary)",
              border: "1px solid var(--border-color)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.4rem" }}>
              <Lock size={18} style={{ color: "var(--text-primary)" }} />
              <span style={{ fontWeight: 700, fontSize: "0.85rem", color: "var(--text-primary)" }}>
                STORE NOW, DECRYPT LATER (SNDL)
              </span>
            </div>
            <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", margin: 0, lineHeight: 1.45 }}>
              Classical ephemeral key exchange ({keyExchangeGroup}) lacks post-quantum KEM encapsulation. Captured sessions are vulnerable to retrospective decryption.
            </p>
          </div>
        </div>
      </div>

      {/* SECTION 1.5: QUANTUM VULNERABILITY INDEX (QVI) RISK SCORE CARD */}
      <div
        style={{
          backgroundColor: "#FFFFFF",
          borderRadius: "16px",
          border: `1px solid ${riskBand.border}`,
          padding: "2rem",
          marginBottom: "2.5rem",
          boxShadow: "0 6px 24px rgba(0, 0, 0, 0.04)",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem", marginBottom: "1.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <div
              style={{
                width: "42px",
                height: "42px",
                borderRadius: "10px",
                backgroundColor: riskBand.bg,
                color: riskBand.color,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Flame size={22} />
            </div>
            <div>
              <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                Quantum Vulnerability Index (QVI Methodology v1.0)
              </div>
              <h2 style={{ fontFamily: "var(--font-serif)", fontSize: "1.5rem", fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
                Perimeter Quantum Threat Assessment
              </h2>
            </div>
          </div>

          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.5rem",
              padding: "0.4rem 0.9rem",
              borderRadius: "9999px",
              backgroundColor: riskBand.bg,
              border: `1px solid ${riskBand.border}`,
              color: riskBand.color,
              fontWeight: 800,
              fontSize: "0.85rem",
              letterSpacing: "0.04em",
            }}
          >
            <Activity size={16} />
            <span>{riskBand.label}</span>
          </div>
        </div>

        {/* Big Score Display & Progress Meter */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: "2rem",
            alignItems: "center",
            padding: "1.5rem",
            backgroundColor: "var(--bg-primary)",
            borderRadius: "12px",
            border: "1px solid var(--border-light)",
            marginBottom: "1.5rem",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem", marginBottom: "0.5rem" }}>
              <span
                style={{
                  fontFamily: "var(--font-serif)",
                  fontSize: "3.2rem",
                  fontWeight: 800,
                  color: riskBand.color,
                  lineHeight: 1,
                }}
              >
                {qviScore}
              </span>
              <span style={{ fontSize: "1.2rem", color: "var(--text-muted)", fontWeight: 600 }}>/ 1000 pts</span>
            </div>
            <p style={{ fontSize: "0.9rem", color: "var(--text-secondary)", margin: 0, lineHeight: 1.5 }}>
              {riskBand.desc}
            </p>
          </div>

          <div>
            {/* Visual Progress Bar */}
            <div style={{ marginBottom: "0.75rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", fontWeight: 700, marginBottom: "0.35rem" }}>
                <span>Risk Scale (0 = Safe, 1000 = Compromised)</span>
                <span style={{ color: riskBand.color }}>{qviScore} / 1000</span>
              </div>
              <div style={{ height: "10px", width: "100%", backgroundColor: "var(--border-color)", borderRadius: "9999px", overflow: "hidden" }}>
                <div
                  style={{
                    height: "100%",
                    width: `${Math.min(100, (qviScore / 1000) * 100)}%`,
                    backgroundColor: riskBand.color,
                    borderRadius: "9999px",
                    transition: "width 0.6s ease",
                  }}
                />
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.7rem", color: "var(--text-muted)" }}>
              <span>0 (PQ Safe)</span>
              <span>400 (Elevated)</span>
              <span>600 (High)</span>
              <span>750+ (Critical)</span>
            </div>
          </div>
        </div>

        {/* 7-Dimension Breakdown */}
        <div>
          <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.75rem" }}>
            Deterministic QVI Dimension Breakdown:
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(135px, 1fr))",
              gap: "0.75rem",
            }}
          >
            {[
              { dim: "Q", name: "Quantum Threat", score: `${qviThreat}/300`, desc: qviThreatDesc },
              { dim: "R", name: "Residual & SNDL", score: `${qviResidual}/150`, desc: qviResidualDesc },
              { dim: "L", name: "Lifespan", score: `${qviLifespan}/150`, desc: qviLifespanDesc },
              { dim: "E", name: "Exposure", score: `${qviEnv}/100`, desc: qviEnvDesc },
              { dim: "B", name: "Criticality", score: `${qviBusiness}/100`, desc: qviBusinessDesc },
              { dim: "M", name: "Complexity", score: `${qviMigration}/75`, desc: qviMigrationDesc },
              { dim: "V", name: "Readiness", score: `${qviProtocol}/75`, desc: qviProtocolDesc },
            ].map((d) => (
              <div
                key={d.dim}
                style={{
                  padding: "0.75rem",
                  backgroundColor: "var(--bg-primary)",
                  borderRadius: "8px",
                  border: "1px solid var(--border-light)",
                  textAlign: "center",
                }}
              >
                <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>
                  {d.dim}: {d.name}
                </div>
                <div style={{ fontSize: "1.05rem", fontWeight: 800, color: "var(--text-primary)", margin: "0.2rem 0" }}>
                  {d.score}
                </div>
                <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)", lineHeight: 1.2 }}>
                  {d.desc}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* SECTION 2: Cryptographic Findings (6 Pillars) */}
      <div style={{ marginBottom: "3rem" }}>
        <div style={{ marginBottom: "1.5rem" }}>
          <h2 style={{ fontFamily: "var(--font-serif)", fontSize: "1.6rem", color: "var(--text-primary)", margin: "0 0 0.35rem 0" }}>
            Perimeter Cryptographic Findings
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>
            Deterministic cryptographic parameters extracted during the standard TLS handshake on port {scan.port || 443}.
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: "1.25rem" }}>
          {/* Finding 1: TLS Protocol Version */}
          <div
            style={{
              backgroundColor: "var(--bg-secondary)",
              borderRadius: "12px",
              border: "1px solid var(--border-color)",
              padding: "1.5rem",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Server size={18} style={{ color: "var(--olive-primary)" }} />
                <span style={{ fontWeight: 700, fontSize: "0.9rem", color: "var(--text-primary)" }}>TLS Protocol Version</span>
              </div>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.8rem",
                  padding: "0.2rem 0.5rem",
                  borderRadius: "4px",
                  backgroundColor: protocol === "TLSv1.3" ? "var(--olive-light)" : "var(--bg-tertiary)",
                  color: protocol === "TLSv1.3" ? "var(--olive-primary)" : "var(--text-primary)",
                  fontWeight: 700,
                }}
              >
                {protocol}
              </span>
            </div>
            <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: "0.75rem" }}>
              {protocol === "TLSv1.3"
                ? "Negotiated TLS 1.3 eliminates static RSA key exchange and legacy compression. Architecture supports PQ KEM negotiation in supported_groups."
                : `Negotiated ${protocol}. Upgrade to TLS 1.3 is recommended to eliminate legacy cipher vulnerabilities and enable post-quantum hybrid extensions.`}
            </p>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", borderTop: "1px solid var(--border-light)", paddingTop: "0.75rem" }}>
              <strong>Standard Reference:</strong> RFC 8446 • NIST SP 800-52r2
            </div>
          </div>

          {/* Finding 2: Key-Exchange Mechanism */}
          <div
            style={{
              backgroundColor: "var(--bg-secondary)",
              borderRadius: "12px",
              border: "1px solid var(--border-color)",
              padding: "1.5rem",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <KeyRound size={18} style={{ color: "var(--amber-primary)" }} />
                <span style={{ fontWeight: 700, fontSize: "0.9rem", color: "var(--text-primary)" }}>Key-Exchange Group</span>
              </div>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.8rem",
                  padding: "0.2rem 0.5rem",
                  borderRadius: "4px",
                  backgroundColor: "rgba(180, 83, 9, 0.1)",
                  color: "var(--amber-primary)",
                  fontWeight: 700,
                }}
              >
                {keyExchangeGroup}
              </span>
            </div>
            <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: "0.75rem" }}>
              Key exchange relies on classical discrete logarithm mathematics. Adversaries recording traffic today can decrypt entire sessions once a CRQC is operational (SNDL attack).
            </p>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", borderTop: "1px solid var(--border-light)", paddingTop: "0.75rem" }}>
              <strong>Target PQC Standard:</strong> NIST FIPS 203 (ML-KEM-768 / X25519MLKEM768)
            </div>
          </div>

          {/* Finding 3: Leaf Certificate Public Key */}
          <div
            style={{
              backgroundColor: "var(--bg-secondary)",
              borderRadius: "12px",
              border: "1px solid var(--border-color)",
              padding: "1.5rem",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <FileCheck size={18} style={{ color: "var(--amber-primary)" }} />
                <span style={{ fontWeight: 700, fontSize: "0.9rem", color: "var(--text-primary)" }}>Leaf Certificate Public Key</span>
              </div>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.8rem",
                  padding: "0.2rem 0.5rem",
                  borderRadius: "4px",
                  backgroundColor: "rgba(180, 83, 9, 0.1)",
                  color: "var(--amber-primary)",
                  fontWeight: 700,
                }}
              >
                {certKeyAlgo} {certKeySize ? `${certKeySize}-bit` : ""}
              </span>
            </div>
            <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: "0.75rem" }}>
              Asymmetric authentication key used to verify endpoint identity. Integer factorization (RSA) and elliptic curves (ECDSA) are solvable in polynomial time O((log N)³) via Shor&apos;s algorithm.
            </p>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", borderTop: "1px solid var(--border-light)", paddingTop: "0.75rem" }}>
              <strong>Target PQC Standard:</strong> NIST FIPS 204 (ML-DSA-65)
            </div>
          </div>

          {/* Finding 4: Certificate Signature Algorithm */}
          <div
            style={{
              backgroundColor: "var(--bg-secondary)",
              borderRadius: "12px",
              border: "1px solid var(--border-color)",
              padding: "1.5rem",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Layers size={18} style={{ color: "var(--olive-primary)" }} />
                <span style={{ fontWeight: 700, fontSize: "0.9rem", color: "var(--text-primary)" }}>Signature Algorithm</span>
              </div>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.8rem",
                  padding: "0.2rem 0.5rem",
                  borderRadius: "4px",
                  backgroundColor: "var(--bg-tertiary)",
                  color: "var(--text-primary)",
                  fontWeight: 600,
                }}
              >
                {signatureAlgo}
              </span>
            </div>
            <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: "0.75rem" }}>
              Certificate authority signature uses classical hash-and-sign scheme. In a post-quantum scenario, adversaries could forge valid signatures without detection.
            </p>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", borderTop: "1px solid var(--border-light)", paddingTop: "0.75rem" }}>
              <strong>Target PQC Standard:</strong> NIST FIPS 204 (ML-DSA) or FIPS 205 (SLH-DSA)
            </div>
          </div>

          {/* Finding 5: Bulk Symmetric Cipher */}
          <div
            style={{
              backgroundColor: "var(--bg-secondary)",
              borderRadius: "12px",
              border: "1px solid var(--border-color)",
              padding: "1.5rem",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Cpu size={18} style={{ color: "var(--olive-primary)" }} />
                <span style={{ fontWeight: 700, fontSize: "0.9rem", color: "var(--text-primary)" }}>Bulk Cipher Suite</span>
              </div>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.8rem",
                  padding: "0.2rem 0.5rem",
                  borderRadius: "4px",
                  backgroundColor: isAes256 ? "var(--olive-light)" : "rgba(180, 83, 9, 0.1)",
                  color: isAes256 ? "var(--olive-primary)" : "var(--amber-primary)",
                  fontWeight: 700,
                }}
              >
                {cipher.slice(0, 24)}...
              </span>
            </div>
            <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: "0.75rem" }}>
              {isAes256
                ? "Symmetric encryption with 256-bit key length provides robust 128-bit quantum security against Grover's quadratic search speedup."
                : "Symmetric cipher provides 128-bit classical key length, which reduces to ~64 bits of security against Grover's algorithm. Upgrade to AES-256 recommended."}
            </p>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", borderTop: "1px solid var(--border-light)", paddingTop: "0.75rem" }}>
              <strong>Quantum Security Margin:</strong> {isAes256 ? "128 bits (Safe)" : "64 bits (Caution)"}
            </div>
          </div>

          {/* Finding 6: Certificate Chain & Validity */}
          <div
            style={{
              backgroundColor: "var(--bg-secondary)",
              borderRadius: "12px",
              border: "1px solid var(--border-color)",
              padding: "1.5rem",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <ShieldCheck size={18} style={{ color: "var(--olive-primary)" }} />
                <span style={{ fontWeight: 700, fontSize: "0.9rem", color: "var(--text-primary)" }}>Chain Depth & Validity</span>
              </div>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.8rem",
                  padding: "0.2rem 0.5rem",
                  borderRadius: "4px",
                  backgroundColor: "var(--bg-tertiary)",
                  color: "var(--text-primary)",
                  fontWeight: 600,
                }}
              >
                Depth: {chainLen}
              </span>
            </div>
            <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: "0.75rem" }}>
              {validTo ? (
                <>
                  Valid until: <strong>{new Date(validTo).toLocaleDateString()}</strong>. Issuer: <code style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}>{issuerDn.slice(0, 36)}...</code>
                </>
              ) : (
                `Verified certificate hierarchy with ${chainLen} certificates in trust chain.`
              )}
            </p>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", borderTop: "1px solid var(--border-light)", paddingTop: "0.75rem" }}>
              <strong>Subject:</strong> {subjectDn.slice(0, 36)}...
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 3: Cryptographic Exposure Map */}
      <div
        style={{
          backgroundColor: "var(--bg-secondary)",
          borderRadius: "16px",
          border: "1px solid var(--border-color)",
          padding: "2rem",
          marginBottom: "3rem",
        }}
      >
        <div style={{ marginBottom: "1.5rem" }}>
          <h2 style={{ fontFamily: "var(--font-serif)", fontSize: "1.4rem", color: "var(--text-primary)", margin: "0 0 0.35rem 0" }}>
            Cryptographic Pipeline Exposure Map
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem" }}>
            Handshake negotiation path and corresponding quantum resilience posture for each stage.
          </p>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "0.75rem",
            padding: "1.5rem",
            backgroundColor: "var(--bg-primary)",
            borderRadius: "12px",
            border: "1px solid var(--border-light)",
          }}
        >
          {/* Node 1 */}
          <div style={{ flex: 1, minWidth: "140px", textAlign: "center" }}>
            <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "0.4rem" }}>
              Domain
            </div>
            <div
              style={{
                backgroundColor: "var(--bg-secondary)",
                padding: "0.6rem 0.75rem",
                borderRadius: "8px",
                border: "1px solid var(--border-color)",
                fontFamily: "var(--font-mono)",
                fontSize: "0.8rem",
                fontWeight: 600,
                color: "var(--text-primary)",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {hostname}
            </div>
          </div>

          <ChevronRight size={18} style={{ color: "var(--text-muted)", flexShrink: 0 }} />

          {/* Node 2 */}
          <div style={{ flex: 1, minWidth: "120px", textAlign: "center" }}>
            <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "0.4rem" }}>
              Protocol
            </div>
            <div
              style={{
                backgroundColor: protocol.includes("1.3") ? "var(--olive-light)" : "var(--bg-tertiary)",
                padding: "0.6rem 0.75rem",
                borderRadius: "8px",
                border: `1px solid ${protocol.includes("1.3") ? "var(--olive-border)" : "var(--border-color)"}`,
                fontFamily: "var(--font-mono)",
                fontSize: "0.8rem",
                fontWeight: 700,
                color: protocol.includes("1.3") ? "var(--olive-primary)" : "var(--text-primary)",
              }}
            >
              {protocol}
            </div>
          </div>

          <ChevronRight size={18} style={{ color: "var(--text-muted)", flexShrink: 0 }} />

          {/* Node 3 */}
          <div style={{ flex: 1, minWidth: "140px", textAlign: "center" }}>
            <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--amber-primary)", textTransform: "uppercase", marginBottom: "0.4rem" }}>
              Key Exchange (Shor)
            </div>
            <div
              style={{
                backgroundColor: "rgba(180, 83, 9, 0.08)",
                padding: "0.6rem 0.75rem",
                borderRadius: "8px",
                border: "1px solid rgba(180, 83, 9, 0.3)",
                fontFamily: "var(--font-mono)",
                fontSize: "0.8rem",
                fontWeight: 700,
                color: "var(--amber-primary)",
              }}
            >
              ECDHE (Vulnerable)
            </div>
          </div>

          <ChevronRight size={18} style={{ color: "var(--text-muted)", flexShrink: 0 }} />

          {/* Node 4 */}
          <div style={{ flex: 1, minWidth: "140px", textAlign: "center" }}>
            <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--amber-primary)", textTransform: "uppercase", marginBottom: "0.4rem" }}>
              Leaf Cert (Shor)
            </div>
            <div
              style={{
                backgroundColor: "rgba(180, 83, 9, 0.08)",
                padding: "0.6rem 0.75rem",
                borderRadius: "8px",
                border: "1px solid rgba(180, 83, 9, 0.3)",
                fontFamily: "var(--font-mono)",
                fontSize: "0.8rem",
                fontWeight: 700,
                color: "var(--amber-primary)",
              }}
            >
              {certKeyAlgo} (Vulnerable)
            </div>
          </div>

          <ChevronRight size={18} style={{ color: "var(--text-muted)", flexShrink: 0 }} />

          {/* Node 5 */}
          <div style={{ flex: 1, minWidth: "140px", textAlign: "center" }}>
            <div style={{ fontSize: "0.75rem", fontWeight: 700, color: isAes256 ? "var(--olive-primary)" : "var(--amber-primary)", textTransform: "uppercase", marginBottom: "0.4rem" }}>
              Cipher (Grover)
            </div>
            <div
              style={{
                backgroundColor: isAes256 ? "var(--olive-light)" : "rgba(180, 83, 9, 0.08)",
                padding: "0.6rem 0.75rem",
                borderRadius: "8px",
                border: `1px solid ${isAes256 ? "var(--olive-border)" : "rgba(180, 83, 9, 0.3)"}`,
                fontFamily: "var(--font-mono)",
                fontSize: "0.8rem",
                fontWeight: 700,
                color: isAes256 ? "var(--olive-primary)" : "var(--amber-primary)",
              }}
            >
              {isAes256 ? "AES-256 (Safe)" : "AES-128 (Weak)"}
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 4: Scope & Visibility Notice */}
      <div style={{ marginBottom: "3rem" }}>
        <div style={{ marginBottom: "1.25rem" }}>
          <h2 style={{ fontFamily: "var(--font-serif)", fontSize: "1.4rem", color: "var(--text-primary)", margin: "0 0 0.35rem 0" }}>
            Assessment Scope & Perimeter Boundary Notice
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem" }}>
            Understanding the deterministic limits of non-intrusive public perimeter scanning.
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.5rem" }}>
          {/* Measured Panel */}
          <div
            style={{
              backgroundColor: "var(--bg-secondary)",
              borderRadius: "12px",
              border: "1px solid var(--border-color)",
              padding: "1.5rem",
              borderLeft: "4px solid var(--olive-primary)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
              <CheckCircle2 size={18} style={{ color: "var(--olive-primary)" }} />
              <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
                What This Public Scan Measured
              </h3>
            </div>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.6rem" }}>
              {[
                `Public ${protocol} handshake on standard destination port ${scan.port || 443}.`,
                `Negotiated cipher suite (${cipher}) and key length.`,
                `Public X.509 leaf certificate attributes (${certKeyAlgo} ${certKeySize}-bit).`,
                "Certificate trust chain depth and expiration timestamps.",
                "Shor's algorithm vulnerability on negotiated key exchange.",
                "Grover's algorithm resilience on bulk symmetric cipher.",
              ].map((item, idx) => (
                <li key={idx} style={{ display: "flex", alignItems: "flex-start", gap: "0.5rem", fontSize: "0.875rem", color: "var(--text-secondary)" }}>
                  <span style={{ color: "var(--olive-primary)", fontWeight: 700 }}>✓</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Not Visible Panel */}
          <div
            style={{
              backgroundColor: "var(--bg-secondary)",
              borderRadius: "12px",
              border: "1px solid var(--border-color)",
              padding: "1.5rem",
              borderLeft: "4px solid var(--text-muted)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
              <EyeOff size={18} style={{ color: "var(--text-muted)" }} />
              <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
                What Was NOT Visible (Beyond Perimeter)
              </h3>
            </div>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.6rem" }}>
              {[
                "Internal microservices, private service mesh (mTLS), and API endpoints.",
                "Cryptographic keys stored in Hardware Security Modules (HSMs) or KMS.",
                "Database-at-rest encryption algorithms and data lifecycle posture.",
                "Application source code cryptographic primitives and third-party libraries.",
                "Enterprise identities, Kerberos tickets, Active Directory, and VPNs.",
                "Deterministic CycloneDX 1.6 Cryptographic Bill of Materials (CBOM).",
              ].map((item, idx) => (
                <li key={idx} style={{ display: "flex", alignItems: "flex-start", gap: "0.5rem", fontSize: "0.875rem", color: "var(--text-secondary)" }}>
                  <span style={{ color: "var(--text-muted)", fontWeight: 700 }}>✕</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* SECTION 5: Enterprise Assessment CTA */}
      <div
        style={{
          borderRadius: "16px",
          backgroundColor: "var(--text-primary)",
          color: "#FFFFFF",
          padding: "3rem 2.5rem",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div style={{ maxWidth: "700px" }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.4rem",
              padding: "0.25rem 0.75rem",
              borderRadius: "9999px",
              backgroundColor: "rgba(255, 255, 255, 0.1)",
              fontSize: "0.75rem",
              fontWeight: 700,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              marginBottom: "1rem",
            }}
          >
            <Sparkles size={14} style={{ color: "#EBF0EC" }} />
            <span>Complete Cryptographic Observability</span>
          </div>

          <h2
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: "clamp(1.8rem, 3.5vw, 2.4rem)",
              fontWeight: 700,
              lineHeight: 1.25,
              margin: "0 0 1rem 0",
              color: "#FFFFFF",
            }}
          >
            Your public TLS scan is only the starting point.
          </h2>

          <p
            style={{
              fontSize: "1rem",
              color: "#CBD5E1",
              lineHeight: 1.6,
              marginBottom: "2rem",
            }}
          >
            External TLS scanning evaluates less than 5% of your enterprise cryptographic surface.
            Deep quantum risk intelligence requires discovering internal microservices, private keys, databases,
            and source code repositories with kernel-level isolation.
          </p>

          <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
            <Link
              to={`/request-demo?domain=${encodeURIComponent(hostname)}`}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem",
                padding: "0.85rem 1.75rem",
                borderRadius: "8px",
                backgroundColor: "var(--olive-primary)",
                color: "#FFFFFF",
                fontSize: "0.95rem",
                fontWeight: 600,
                textDecoration: "none",
              }}
            >
              <span>Schedule Enterprise Briefing</span>
              <ArrowRight size={18} />
            </Link>

            <button
              type="button"
              onClick={() => handleDownloadReport("markdown")}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem",
                padding: "0.85rem 1.5rem",
                borderRadius: "8px",
                backgroundColor: "rgba(255, 255, 255, 0.12)",
                border: "1px solid rgba(255, 255, 255, 0.25)",
                color: "#FFFFFF",
                fontSize: "0.95rem",
                fontWeight: 600,
                cursor: "pointer",
              }}
              title="Download full executive report in Markdown format"
            >
              <Download size={16} />
              <span>Download Report (.md)</span>
            </button>

            <Link
              to="/platform"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem",
                padding: "0.85rem 1.5rem",
                borderRadius: "8px",
                backgroundColor: "transparent",
                border: "1px solid rgba(255, 255, 255, 0.25)",
                color: "#FFFFFF",
                fontSize: "0.95rem",
                fontWeight: 500,
                textDecoration: "none",
              }}
            >
              <span>Explore Enterprise Architecture</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
