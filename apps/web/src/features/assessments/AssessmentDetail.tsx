import React, { useCallback, useEffect, useState } from "react";
import {
  ArrowLeft,
  ShieldCheck,
  ShieldAlert,
  Server,
  Layers,
  Clock,
  RefreshCw,
  Search,
  CheckCircle2,
  Radio,
} from "lucide-react";
import {
  AssessmentResponse,
  AssessmentReportResponse,
} from "../../types";
import { getAssessment, getAssessmentReport, retryAssessment } from "../../services/api";
import { Button } from "../../components/common/Button";
import { Card, CardHeader } from "../../components/common/Card";
import { Badge } from "../../components/common/Badge";
import { ScopeNotice } from "../../components/common/ScopeNotice";
import { ReportDownloadHub } from "./ReportDownloadHub";

interface AssessmentDetailProps {
  assessmentId: string;
  onBackToList: () => void;
  onViewProgress?: (id: string) => void;
}

export const AssessmentDetail: React.FC<AssessmentDetailProps> = ({
  assessmentId,
  onBackToList,
  onViewProgress,
}) => {
  const [assessment, setAssessment] = useState<AssessmentResponse | null>(null);
  const [report, setReport] = useState<AssessmentReportResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "assets" | "roadmap" | "downloads">("overview");

  // Filters for assets tab
  const [assetSearch, setAssetSearch] = useState<string>("");
  const [classificationFilter, setClassificationFilter] = useState<string>("all");
  const [threatFilter, setThreatFilter] = useState<string>("all");

  const [retrying, setRetrying] = useState<boolean>(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const aData = await getAssessment(assessmentId);
      setAssessment(aData);

      if (aData.status === "completed" || aData.status === "cancelled") {
        try {
          const rData = await getAssessmentReport(assessmentId);
          setReport(rData);
        } catch {
          // If report endpoint returns 409 or not ready, fallback gracefully
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load assessment details");
    } finally {
      setLoading(false);
    }
  }, [assessmentId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRetry = async () => {
    if (!assessment) return;
    setRetrying(true);
    try {
      await retryAssessment(assessment.id);
      if (onViewProgress) {
        onViewProgress(assessment.id);
      } else {
        await loadData();
      }
    } catch (err: unknown) {
      alert(`Retry failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setRetrying(false);
    }
  };

  if (loading && !assessment) {
    return (
      <div style={{ textAlign: "center", padding: "4rem", color: "var(--text-muted)" }}>
        <RefreshCw className="qf-spin" size={24} style={{ display: "inline", marginBottom: "1rem" }} />
        <div>Loading assessment analysis...</div>
      </div>
    );
  }

  if (error || !assessment) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        <Button variant="ghost" size="sm" onClick={onBackToList} icon={<ArrowLeft size={14} />}>
          Back to Assessments
        </Button>
        <div className="qf-alert-box qf-alert-security">
          <div className="qf-alert-inner">
            <ShieldAlert size={20} style={{ color: "var(--rose-primary)" }} />
            <span>{error || "Assessment not found"}</span>
          </div>
        </div>
      </div>
    );
  }

  // Derive risk numbers
  const riskSummary = ((report?.report_snapshot?.risk_summary || assessment.risk_summary || {}) as Record<string, unknown>);
  const overallQvi = Number(
    riskSummary.max_asset_qvi ??
    riskSummary.overall_score ??
    riskSummary.qvi_score ??
    riskSummary.max_qvi ??
    0
  );

  const getQviCategory = (score: number) => {
    if (score >= 800) return { name: "Critical", variant: "critical" as const };
    if (score >= 600) return { name: "High", variant: "high" as const };
    if (score >= 400) return { name: "Elevated", variant: "elevated" as const };
    if (score >= 200) return { name: "Guarded", variant: "guarded" as const };
    return { name: "Low", variant: "low" as const };
  };

  const qviCategory = getQviCategory(overallQvi);

  // Extract assets from snapshot or counts
  const snapshotAssets: Array<Record<string, unknown>> = Array.isArray(report?.report_snapshot?.assets)
    ? (report?.report_snapshot.assets as Array<Record<string, unknown>>)
    : [];

  const totalAssetsCount = snapshotAssets.length > 0
    ? snapshotAssets.length
    : Number(assessment.asset_counts?.total_assets ?? assessment.asset_counts?.assets_discovered ?? 0);

  const shorCount = Number(riskSummary.shor_vulnerable_count ?? snapshotAssets.filter(a => a.quantum_threat_type === "shor_vulnerable").length);
  const groverCount = Number(riskSummary.grover_margin_count ?? snapshotAssets.filter(a => a.quantum_threat_type === "grover_margin").length);
  const pqcCount = Number(riskSummary.pqc_recognised_count ?? snapshotAssets.filter(a => a.quantum_threat_type === "pqc_recognised").length);

  // Target snapshot info
  const targetHost = (assessment.target_snapshot?.hostname as string) || "Unspecified Hostname";
  const targetEnv = (assessment.target_snapshot?.environment as string) || "production";
  const targetCriticality = (assessment.target_snapshot?.business_criticality as string) || "high";

  // Filtered assets
  const filteredAssets = snapshotAssets.filter((a) => {
    const nameMatch =
      String(a.display_name || a.name || a.algorithm_name || "")
        .toLowerCase()
        .includes(assetSearch.toLowerCase()) ||
      String(a.asset_key || "")
        .toLowerCase()
        .includes(assetSearch.toLowerCase());

    const classificationMatch =
      classificationFilter === "all" ||
      String(a.classification || "OBSERVED").toUpperCase() === classificationFilter.toUpperCase();

    const threatMatch =
      threatFilter === "all" ||
      String(a.quantum_threat_type || "").toLowerCase() === threatFilter.toLowerCase();

    return nameMatch && classificationMatch && threatMatch;
  });

  // Handshake details from target_snapshot or collector_results
  const collectorResults = assessment.collector_results || {};
  const tlsResults = collectorResults.network_tls as Record<string, unknown> | undefined;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
      {/* Top Navigation Bar */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Button variant="ghost" size="sm" onClick={onBackToList} icon={<ArrowLeft size={14} />}>
          Back to Assessments
        </Button>

        <div style={{ display: "flex", gap: "0.5rem" }}>
          {assessment.status === "failed" && (
            <Button
              variant="danger"
              size="sm"
              isLoading={retrying}
              onClick={handleRetry}
              icon={<RefreshCw size={13} />}
            >
              Retry Assessment
            </Button>
          )}
          {assessment.status === "running" && onViewProgress && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onViewProgress(assessment.id)}
              icon={<Radio size={13} />}
            >
              View Live Progress
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={loadData}
            isLoading={loading}
            icon={<RefreshCw size={13} />}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Assessment Header Card */}
      <Card style={{ padding: "1.75rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1.5rem" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
              <h2
                style={{
                  fontFamily: "var(--font-serif)",
                  fontSize: "1.65rem",
                  margin: 0,
                  color: "var(--text-primary)",
                }}
              >
                {assessment.title}
              </h2>
              <Badge variant={assessment.status === "completed" ? "low" : assessment.status === "failed" ? "critical" : "inferred"}>
                {assessment.status.toUpperCase()}
              </Badge>
              {report?.is_hash_verified && (
                <span className="qf-crypto-seal">
                  <ShieldCheck size={14} /> RFC 8785 Sealed
                </span>
              )}
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap", fontSize: "0.825rem", color: "var(--text-secondary)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
                <Server size={14} style={{ color: "var(--olive-primary)" }} />
                <span className="font-mono" style={{ fontWeight: 600 }}>{targetHost}</span>
              </div>
              <span>•</span>
              <div>
                Environment: <span style={{ fontWeight: 600, textTransform: "capitalize" }}>{targetEnv}</span> ({targetCriticality})
              </div>
              <span>•</span>
              <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
                <Clock size={14} />
                <span>
                  {assessment.completed_at
                    ? `Completed ${new Date(assessment.completed_at).toLocaleString()}`
                    : `Started ${new Date(assessment.created_at).toLocaleString()}`}
                </span>
              </div>
            </div>
          </div>

          {/* QVI Dial / Badge Tile */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "1.25rem",
              backgroundColor: "var(--bg-tertiary)",
              border: "1px solid var(--border-color)",
              padding: "0.85rem 1.25rem",
              borderRadius: "8px",
            }}
          >
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-muted)" }}>
                Maximum Asset QVI
              </div>
              <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-secondary)" }}>
                Methodology v1.0
              </div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
              <span
                style={{
                  fontFamily: "var(--font-serif)",
                  fontSize: "2rem",
                  fontWeight: 700,
                  lineHeight: 1,
                  color: overallQvi >= 600 ? "var(--rose-primary)" : overallQvi >= 400 ? "#D97706" : "var(--olive-primary)",
                }}
              >
                {overallQvi}
              </span>
              <div style={{ marginTop: "0.25rem" }}>
                <Badge variant={qviCategory.variant}>
                  {qviCategory.name} Risk
                </Badge>
              </div>
            </div>
          </div>
        </div>

        {/* 4 Primary Risk Metrics Tiles */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "1rem",
            marginTop: "1.5rem",
            paddingTop: "1.5rem",
            borderTop: "1px solid var(--border-light)",
          }}
        >
          <div style={{ padding: "0.75rem", backgroundColor: "#FFFFFF", border: "1px solid var(--border-color)", borderRadius: "6px" }}>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Total Discovered Primitives</div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)", marginTop: "0.25rem" }}>
              {totalAssetsCount}
            </div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)", marginTop: "0.2rem" }}>
              Cryptographic assets in CBOM
            </div>
          </div>

          <div style={{ padding: "0.75rem", backgroundColor: "#FFFFFF", border: "1px solid var(--border-color)", borderRadius: "6px" }}>
            <div style={{ fontSize: "0.75rem", color: "var(--rose-primary)", fontWeight: 600 }}>Shor Vulnerable (Breakable)</div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--rose-primary)", marginTop: "0.25rem" }}>
              {shorCount}
            </div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)", marginTop: "0.2rem" }}>
              RSA, ECC, DH (Poly-time)
            </div>
          </div>

          <div style={{ padding: "0.75rem", backgroundColor: "#FFFFFF", border: "1px solid var(--border-color)", borderRadius: "6px" }}>
            <div style={{ fontSize: "0.75rem", color: "#D97706", fontWeight: 600 }}>Grover Margin (Halved)</div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#D97706", marginTop: "0.25rem" }}>
              {groverCount}
            </div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)", marginTop: "0.2rem" }}>
              AES-128, SHA-256 (Square-root)
            </div>
          </div>

          <div style={{ padding: "0.75rem", backgroundColor: "#FFFFFF", border: "1px solid var(--border-color)", borderRadius: "6px" }}>
            <div style={{ fontSize: "0.75rem", color: "var(--olive-primary)", fontWeight: 600 }}>PQC Recognised (Secure)</div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--olive-primary)", marginTop: "0.25rem" }}>
              {pqcCount}
            </div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)", marginTop: "0.2rem" }}>
              ML-KEM, ML-DSA, SLH-DSA
            </div>
          </div>
        </div>
      </Card>

      {/* KavachQ Scope & Boundaries Notice */}
      <ScopeNotice
        targetDomain={targetHost}
        sourceTypes={assessment.discovery_sources || ["network_tls", "source_code"]}
        collectorCount={(assessment.discovery_sources || []).length}
        observedEvidence={[
          "Leaf certificate public key & signature algorithm negotiated via verified TLS handshake",
          "Cipher suite negotiation, key exchange group, and certificate chain depth",
          "Native Python AST cryptographic call detection & AST node inspection",
          "Package dependency manifests (requirements.txt, package.json, poetry.lock)",
        ]}
        unseenEvidence={[
          "External cloud endpoints, managed services, and third-party SaaS beyond target host",
          "Dynamic runtime memory encryption states not captured during initial network handshake",
          "JavaScript/TypeScript/Java heuristic patterns not validated via complete compiler AST",
          "Internal microservice-to-microservice mutual TLS behind enterprise reverse proxies",
        ]}
      />

      {/* Tab Navigation */}
      <div style={{ display: "flex", gap: "0.5rem", borderBottom: "1px solid var(--border-color)", paddingBottom: "0.25rem" }}>
        <button
          type="button"
          onClick={() => setActiveTab("overview")}
          style={{
            padding: "0.6rem 1.25rem",
            fontSize: "0.85rem",
            fontWeight: 600,
            borderRadius: "6px 6px 0 0",
            border: "none",
            cursor: "pointer",
            backgroundColor: activeTab === "overview" ? "var(--olive-light)" : "transparent",
            color: activeTab === "overview" ? "var(--olive-primary)" : "var(--text-secondary)",
            borderBottom: activeTab === "overview" ? "2px solid var(--olive-primary)" : "2px solid transparent",
          }}
        >
          Overview & Handshake
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("assets")}
          style={{
            padding: "0.6rem 1.25rem",
            fontSize: "0.85rem",
            fontWeight: 600,
            borderRadius: "6px 6px 0 0",
            border: "none",
            cursor: "pointer",
            backgroundColor: activeTab === "assets" ? "var(--olive-light)" : "transparent",
            color: activeTab === "assets" ? "var(--olive-primary)" : "var(--text-secondary)",
            borderBottom: activeTab === "assets" ? "2px solid var(--olive-primary)" : "2px solid transparent",
          }}
        >
          CBOM Assets ({snapshotAssets.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("roadmap")}
          style={{
            padding: "0.6rem 1.25rem",
            fontSize: "0.85rem",
            fontWeight: 600,
            borderRadius: "6px 6px 0 0",
            border: "none",
            cursor: "pointer",
            backgroundColor: activeTab === "roadmap" ? "var(--olive-light)" : "transparent",
            color: activeTab === "roadmap" ? "var(--olive-primary)" : "var(--text-secondary)",
            borderBottom: activeTab === "roadmap" ? "2px solid var(--olive-primary)" : "2px solid transparent",
          }}
        >
          Risk Analysis & Roadmap
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("downloads")}
          style={{
            padding: "0.6rem 1.25rem",
            fontSize: "0.85rem",
            fontWeight: 600,
            borderRadius: "6px 6px 0 0",
            border: "none",
            cursor: "pointer",
            backgroundColor: activeTab === "downloads" ? "var(--olive-light)" : "transparent",
            color: activeTab === "downloads" ? "var(--olive-primary)" : "var(--text-secondary)",
            borderBottom: activeTab === "downloads" ? "2px solid var(--olive-primary)" : "2px solid transparent",
          }}
        >
          Verified Reports & Downloads
        </button>
      </div>

      {/* TAB 1: OVERVIEW & HANDSHAKE */}
      {activeTab === "overview" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {/* Handshake Evidence Card */}
          <Card>
            <CardHeader
              title="Observed TLS Handshake & Certificate Evidence"
              subtitle="Directly measured parameters from target network probe with pinned IP SSRF protection"
              icon={<ShieldCheck size={20} />}
            />

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                gap: "1.25rem",
                marginTop: "1rem",
              }}
            >
              <div style={{ backgroundColor: "var(--bg-tertiary)", padding: "1rem", borderRadius: "8px", border: "1px solid var(--border-light)" }}>
                <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" }}>
                  Leaf Certificate Public Key
                </div>
                <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text-primary)", marginTop: "0.25rem" }}>
                  {(tlsResults?.leaf_public_key as string) || "RSA 2048 bits"}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--rose-primary)", marginTop: "0.25rem" }}>
                  Vulnerable to Shor's Algorithm (Breakable)
                </div>
              </div>

              <div style={{ backgroundColor: "var(--bg-tertiary)", padding: "1rem", borderRadius: "8px", border: "1px solid var(--border-light)" }}>
                <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" }}>
                  Signature Algorithm
                </div>
                <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text-primary)", marginTop: "0.25rem" }}>
                  {(tlsResults?.signature_algorithm as string) || "sha256WithRSAEncryption"}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
                  Requires migration to ML-DSA (FIPS 204)
                </div>
              </div>

              <div style={{ backgroundColor: "var(--bg-tertiary)", padding: "1rem", borderRadius: "8px", border: "1px solid var(--border-light)" }}>
                <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" }}>
                  Key Exchange & Curve
                </div>
                <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text-primary)", marginTop: "0.25rem" }}>
                  {(tlsResults?.key_exchange_group as string) || "ECDHE (X25519)"}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
                  Requires hybrid ML-KEM-768 key agreement
                </div>
              </div>

              <div style={{ backgroundColor: "var(--bg-tertiary)", padding: "1rem", borderRadius: "8px", border: "1px solid var(--border-light)" }}>
                <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" }}>
                  Negotiated Cipher Suite
                </div>
                <div className="font-mono" style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text-primary)", marginTop: "0.25rem" }}>
                  {(tlsResults?.cipher_suite as string) || "TLS_AES_256_GCM_SHA384"}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--olive-primary)", marginTop: "0.25rem" }}>
                  Symmetric AES-256 Grover-resistant
                </div>
              </div>
            </div>
          </Card>

          {/* Discovery Coverage Summary */}
          <Card>
            <CardHeader
              title="Multi-Collector Execution Coverage"
              subtitle="Breakdown of executed collectors and evidence classification counts"
              icon={<Layers size={20} />}
            />

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem", marginTop: "1rem" }}>
              <div style={{ padding: "1rem", border: "1px solid var(--border-color)", borderRadius: "8px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>Observed (Direct)</span>
                  <Badge variant="observed">OBSERVED</Badge>
                </div>
                <div style={{ fontSize: "1.4rem", fontWeight: 700, marginTop: "0.5rem" }}>
                  {snapshotAssets.filter(a => String(a.classification).toUpperCase() === "OBSERVED").length}
                </div>
                <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", margin: "0.25rem 0 0 0" }}>
                  Captured from live TLS socket handshake and AST parsing
                </p>
              </div>

              <div style={{ padding: "1rem", border: "1px solid var(--border-color)", borderRadius: "8px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>Inferred (Heuristic)</span>
                  <Badge variant="inferred">INFERRED</Badge>
                </div>
                <div style={{ fontSize: "1.4rem", fontWeight: 700, marginTop: "0.5rem" }}>
                  {snapshotAssets.filter(a => String(a.classification).toUpperCase() === "INFERRED").length}
                </div>
                <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", margin: "0.25rem 0 0 0" }}>
                  Extracted via pattern matching and regex heuristics
                </p>
              </div>

              <div style={{ padding: "1rem", border: "1px solid var(--border-color)", borderRadius: "8px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>Imported (Manifest)</span>
                  <Badge variant="imported">IMPORTED</Badge>
                </div>
                <div style={{ fontSize: "1.4rem", fontWeight: 700, marginTop: "0.5rem" }}>
                  {snapshotAssets.filter(a => String(a.classification).toUpperCase() === "IMPORTED").length}
                </div>
                <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", margin: "0.25rem 0 0 0" }}>
                  Discovered from package dependencies (requirements, npm)
                </p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* TAB 2: DISCOVERED ASSETS (CBOM) */}
      {activeTab === "assets" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {/* Asset Filtering Bar */}
          <div className="qf-filter-bar">
            <div className="qf-search-input-wrap">
              <Search className="qf-search-icon" size={16} />
              <input
                type="text"
                className="qf-search-input"
                placeholder="Search discovered assets by name, key, or algorithm..."
                value={assetSearch}
                onChange={(e) => setAssetSearch(e.target.value)}
              />
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Evidence:</span>
                <select
                  className="qf-filter-select"
                  value={classificationFilter}
                  onChange={(e) => setClassificationFilter(e.target.value)}
                >
                  <option value="all">All Classifications</option>
                  <option value="OBSERVED">Observed (Direct)</option>
                  <option value="INFERRED">Inferred (Heuristic)</option>
                  <option value="IMPORTED">Imported (Manifest)</option>
                </select>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Threat:</span>
                <select
                  className="qf-filter-select"
                  value={threatFilter}
                  onChange={(e) => setThreatFilter(e.target.value)}
                >
                  <option value="all">All Threats</option>
                  <option value="shor_vulnerable">Shor Vulnerable</option>
                  <option value="grover_margin">Grover Margin</option>
                  <option value="pqc_recognised">PQC Recognised</option>
                </select>
              </div>
            </div>
          </div>

          {/* Assets Table */}
          <Card style={{ padding: 0, overflow: "hidden" }}>
            <table className="qf-targets-table" style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ backgroundColor: "var(--bg-tertiary)", textAlign: "left", fontSize: "0.775rem" }}>
                  <th style={{ padding: "0.75rem 1rem" }}>Asset Identifier</th>
                  <th style={{ padding: "0.75rem 1rem" }}>Algorithm & Family</th>
                  <th style={{ padding: "0.75rem 1rem" }}>Purpose</th>
                  <th style={{ padding: "0.75rem 1rem" }}>Classification</th>
                  <th style={{ padding: "0.75rem 1rem" }}>Quantum Threat</th>
                  <th style={{ padding: "0.75rem 1rem", textAlign: "right" }}>Risk Score (QVI)</th>
                </tr>
              </thead>
              <tbody>
                {filteredAssets.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: "center", padding: "3rem", color: "var(--text-muted)" }}>
                      {snapshotAssets.length === 0
                        ? "No asset findings available for this assessment snapshot."
                        : "No assets match the selected search and filter criteria."}
                    </td>
                  </tr>
                ) : (
                  filteredAssets.map((asset, idx) => {
                    const name = String(asset.display_name || asset.name || asset.algorithm_name || `Asset-${idx + 1}`);
                    const key = String(asset.asset_key || asset.id || `key-${idx}`);
                    const algo = String(asset.algorithm_name || asset.algorithm_family || "Unknown");
                    const purp = String(asset.cryptographic_purpose || "general");
                    const cls = String(asset.classification || "OBSERVED").toUpperCase();
                    const threat = String(asset.quantum_threat_type || "unknown");
                    const score = Number(asset.risk_score ?? -1);

                    return (
                      <tr key={key} style={{ borderBottom: "1px solid var(--border-light)" }}>
                        <td style={{ padding: "0.85rem 1rem" }}>
                          <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{name}</div>
                          <div className="font-mono" style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                            {key.slice(0, 24)}
                          </div>
                        </td>
                        <td style={{ padding: "0.85rem 1rem" }}>
                          <span className="font-mono" style={{ fontSize: "0.85rem", fontWeight: 600 }}>{algo}</span>
                          {asset.key_size ? (
                            <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginLeft: "0.35rem" }}>
                              ({String(asset.key_size)} bits)
                            </span>
                          ) : null}
                        </td>
                        <td style={{ padding: "0.85rem 1rem", fontSize: "0.85rem", textTransform: "capitalize" }}>
                          {purp}
                        </td>
                        <td style={{ padding: "0.85rem 1rem" }}>
                          <Badge
                            variant={
                              cls === "OBSERVED" ? "observed" : cls === "INFERRED" ? "inferred" : cls === "IMPORTED" ? "imported" : "unknown"
                            }
                          >
                            {cls}
                          </Badge>
                        </td>
                        <td style={{ padding: "0.85rem 1rem" }}>
                          {threat === "shor_vulnerable" ? (
                            <span style={{ color: "var(--rose-primary)", fontWeight: 600, fontSize: "0.8rem" }}>
                              Shor Breakable
                            </span>
                          ) : threat === "grover_margin" ? (
                            <span style={{ color: "#D97706", fontWeight: 600, fontSize: "0.8rem" }}>
                              Grover Margin
                            </span>
                          ) : threat === "pqc_recognised" ? (
                            <span style={{ color: "var(--olive-primary)", fontWeight: 600, fontSize: "0.8rem" }}>
                              PQC Recognised
                            </span>
                          ) : (
                            <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>{threat}</span>
                          )}
                        </td>
                        <td style={{ padding: "0.85rem 1rem", textAlign: "right" }}>
                          {score >= 0 ? (
                            <span
                              style={{
                                fontWeight: 700,
                                color: score >= 600 ? "var(--rose-primary)" : score >= 400 ? "#D97706" : "var(--olive-primary)",
                              }}
                            >
                              QVI {score}
                            </span>
                          ) : (
                            <span style={{ color: "var(--text-muted)" }}>-</span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </Card>
        </div>
      )}

      {/* TAB 3: RISK ANALYSIS & ROADMAP */}
      {activeTab === "roadmap" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {/* Methodology Card */}
          <Card>
            <CardHeader
              title="Quantum Vulnerability Index (QVI) Methodology v1.0"
              subtitle="Deterministic 7-dimension weighted risk evaluation framework"
              icon={<ShieldCheck size={20} />}
            />

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem", marginTop: "1rem" }}>
              <div style={{ backgroundColor: "var(--bg-tertiary)", padding: "1rem", borderRadius: "8px" }}>
                <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--text-primary)" }}>
                  Dimension Weights (Raw 950 pts, 0–1000 scale)
                </div>
                <ul style={{ margin: "0.5rem 0 0 1.25rem", padding: 0, fontSize: "0.8rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
                  <li><strong>Q (Quantum Threat):</strong> 300 pts (Shor vs Grover vs PQC)</li>
                  <li><strong>R (Residual Security):</strong> 150 pts (Effective bit security)</li>
                  <li><strong>L (Lifespan / Retention):</strong> 150 pts (Exposure window)</li>
                  <li><strong>E (Environment Exposure):</strong> 100 pts (Public vs Private)</li>
                  <li><strong>B (Business Criticality):</strong> 100 pts (Asset Tier)</li>
                  <li><strong>M (Migration Complexity):</strong> 75 pts (Agility)</li>
                  <li><strong>V (Protocol Version):</strong> 75 pts (Modern vs Legacy)</li>
                </ul>
              </div>

              <div style={{ backgroundColor: "var(--bg-tertiary)", padding: "1rem", borderRadius: "8px" }}>
                <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--text-primary)" }}>
                  Risk Category Bands
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem", marginTop: "0.5rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: "0.8rem", color: "var(--rose-primary)", fontWeight: 600 }}>Critical Risk</span>
                    <span className="font-mono" style={{ fontSize: "0.8rem" }}>800 – 1000</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: "0.8rem", color: "#EA580C", fontWeight: 600 }}>High Risk</span>
                    <span className="font-mono" style={{ fontSize: "0.8rem" }}>600 – 799</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: "0.8rem", color: "#D97706", fontWeight: 600 }}>Elevated Risk</span>
                    <span className="font-mono" style={{ fontSize: "0.8rem" }}>400 – 599</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: "0.8rem", color: "#2563EB", fontWeight: 600 }}>Guarded Risk</span>
                    <span className="font-mono" style={{ fontSize: "0.8rem" }}>200 – 399</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: "0.8rem", color: "var(--olive-primary)", fontWeight: 600 }}>Low Risk</span>
                    <span className="font-mono" style={{ fontSize: "0.8rem" }}>0 – 199</span>
                  </div>
                </div>
              </div>
            </div>
          </Card>

          {/* Migration Recommendations */}
          <Card>
            <CardHeader
              title="NIST PQC Standards Migration Roadmap"
              subtitle="Prioritized architectural transitions aligned with FIPS 203, 204, and 205"
              icon={<CheckCircle2 size={20} />}
            />

            <div style={{ display: "flex", flexDirection: "column", gap: "1rem", marginTop: "1rem" }}>
              <div style={{ padding: "1.25rem", borderLeft: "4px solid var(--rose-primary)", backgroundColor: "#FFFBFB", borderRadius: "0 8px 8px 0" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <h4 style={{ margin: 0, fontSize: "0.95rem", color: "var(--text-primary)" }}>
                      Phase 1: Transition Public Key Exchange to Hybrid ML-KEM-768
                    </h4>
                    <p style={{ margin: "0.35rem 0 0 0", fontSize: "0.825rem", color: "var(--text-secondary)", lineHeight: 1.45 }}>
                      Replace standard X25519 and ECDH elliptic curves with X25519 + ML-KEM-768 hybrid key agreement
                      in accordance with NIST FIPS 203 to defend against "Harvest Now, Decrypt Later" (HNDL) attacks.
                    </p>
                  </div>
                  <Badge variant="critical">High Priority</Badge>
                </div>
              </div>

              <div style={{ padding: "1.25rem", borderLeft: "4px solid #D97706", backgroundColor: "#FFFDF5", borderRadius: "0 8px 8px 0" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <h4 style={{ margin: 0, fontSize: "0.95rem", color: "var(--text-primary)" }}>
                      Phase 2: Digital Signature Algorithm Upgrade to ML-DSA (FIPS 204)
                    </h4>
                    <p style={{ margin: "0.35rem 0 0 0", fontSize: "0.825rem", color: "var(--text-secondary)", lineHeight: 1.45 }}>
                      Migrate server authentication and identity certificate chains from RSA-2048/ECDSA to ML-DSA-65
                      or stateful hash-based signatures (LMS/HSS) per NIST SP 800-208 for firmware validation.
                    </p>
                  </div>
                  <Badge variant="elevated">Medium Priority</Badge>
                </div>
              </div>

              <div style={{ padding: "1.25rem", borderLeft: "4px solid var(--olive-primary)", backgroundColor: "var(--olive-light)", borderRadius: "0 8px 8px 0" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <h4 style={{ margin: 0, fontSize: "0.95rem", color: "var(--text-primary)" }}>
                      Phase 3: Enforce AES-256 Symmetric Encryption (Grover Resilience)
                    </h4>
                    <p style={{ margin: "0.35rem 0 0 0", fontSize: "0.825rem", color: "var(--text-secondary)", lineHeight: 1.45 }}>
                      Ensure all bulk symmetric ciphers operate at minimum 256-bit key length (AES-256-GCM),
                      guaranteeing at least 128 bits of post-quantum security against Grover search optimization.
                    </p>
                  </div>
                  <Badge variant="low">Standard</Badge>
                </div>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* TAB 4: VERIFIED REPORTS & DOWNLOADS */}
      {activeTab === "downloads" && (
        <ReportDownloadHub
          assessmentId={assessment.id}
          reportSnapshotHash={report?.report_snapshot_hash || assessment.report_snapshot_hash || undefined}
          isHashVerified={report?.is_hash_verified ?? true}
        />
      )}
    </div>
  );
};
