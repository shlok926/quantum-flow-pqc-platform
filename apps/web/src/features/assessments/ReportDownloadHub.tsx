import React, { useState } from "react";
import {
  Download,
  FileCode,
  FileSpreadsheet,
  FileText,
  ShieldCheck,
  Check,
  Copy,
  AlertCircle,
  Lock,
} from "lucide-react";
import {
  downloadCycloneDxReport,
  downloadCsvReport,
  downloadMarkdownReport,
  triggerBlobDownload,
} from "../../services/api";
import { Button } from "../../components/common/Button";
import { Card } from "../../components/common/Card";
import { Badge } from "../../components/common/Badge";

interface ReportDownloadHubProps {
  assessmentId: string;
  reportSnapshotHash?: string;
  isHashVerified?: boolean;
}

export const ReportDownloadHub: React.FC<ReportDownloadHubProps> = ({
  assessmentId,
  reportSnapshotHash,
  isHashVerified = true,
}) => {
  const [downloadingType, setDownloadingType] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [copiedHash, setCopiedHash] = useState<boolean>(false);

  const handleDownload = async (
    type: "cyclonedx" | "csv" | "markdown",
    fetcher: (id: string) => Promise<Blob>,
    defaultFilename: string
  ) => {
    setDownloadingType(type);
    setErrorMessage(null);
    try {
      const blob = await fetcher(assessmentId);
      triggerBlobDownload(blob, defaultFilename);
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : `Failed to download ${type} report`
      );
    } finally {
      setDownloadingType(null);
    }
  };

  const copyHashToClipboard = () => {
    if (reportSnapshotHash) {
      navigator.clipboard.writeText(reportSnapshotHash);
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2500);
    }
  };

  return (
    <div className="qf-download-hub" style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Integrity & Tamper Proof Header */}
      {reportSnapshotHash && (
        <Card
          style={{
            backgroundColor: "var(--olive-light)",
            border: "1px solid var(--olive-border)",
            padding: "1.25rem 1.5rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <div
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "8px",
                  backgroundColor: "#FFFFFF",
                  border: "1px solid var(--olive-border)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--olive-primary)",
                }}
              >
                <Lock size={18} />
              </div>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <h4 style={{ margin: 0, fontSize: "0.95rem", fontWeight: 600, color: "var(--text-primary)" }}>
                    Cryptographic Report Seal
                  </h4>
                  {isHashVerified ? (
                    <span className="qf-crypto-seal">
                      <ShieldCheck size={14} /> RFC 8785 Canonical Digest Verified
                    </span>
                  ) : (
                    <Badge variant="critical">Digest Unverified</Badge>
                  )}
                </div>
                <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.775rem", color: "var(--text-secondary)" }}>
                  Immutable evidence snapshot hashed using RFC 8785 Canonical JSON & SHA-256. Tampering invalidates all exports.
                </p>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <div
                className="qf-hash-pill"
                title={reportSnapshotHash}
                style={{
                  maxWidth: "280px",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {reportSnapshotHash}
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={copyHashToClipboard}
                icon={copiedHash ? <Check size={13} style={{ color: "var(--olive-primary)" }} /> : <Copy size={13} />}
              >
                {copiedHash ? "Copied" : "Copy"}
              </Button>
            </div>
          </div>
        </Card>
      )}

      {errorMessage && (
        <div className="qf-alert-box qf-alert-security">
          <div className="qf-alert-inner">
            <AlertCircle size={18} style={{ color: "var(--rose-primary)" }} />
            <span>{errorMessage}</span>
          </div>
        </div>
      )}

      {/* Download Action Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
          gap: "1.25rem",
        }}
      >
        {/* CycloneDX 1.6 CBOM */}
        <Card
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            padding: "1.5rem",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
              <div
                style={{
                  width: "40px",
                  height: "40px",
                  borderRadius: "8px",
                  backgroundColor: "rgba(59, 82, 64, 0.08)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--olive-primary)",
                }}
              >
                <FileCode size={22} />
              </div>
              <Badge variant="inferred">JSON 1.6</Badge>
            </div>

            <h3 style={{ fontSize: "1.05rem", fontWeight: 600, color: "var(--text-primary)", margin: "0 0 0.5rem 0" }}>
              CycloneDX 1.6 CBOM
            </h3>
            <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)", lineHeight: 1.45, margin: "0 0 1rem 0" }}>
              Standard Cryptographic Bill of Materials containing discovered algorithms, key lengths, curves,
              cryptographic functions, and dependency provenance per CycloneDX 1.6 Cryptography Extension.
            </p>

            <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", marginBottom: "1.25rem" }}>
              <span className="qf-tag" style={{ fontSize: "0.7rem", padding: "0.15rem 0.45rem", backgroundColor: "var(--bg-tertiary)", borderRadius: "4px" }}>
                NIST SP 800-208
              </span>
              <span className="qf-tag" style={{ fontSize: "0.7rem", padding: "0.15rem 0.45rem", backgroundColor: "var(--bg-tertiary)", borderRadius: "4px" }}>
                FIPS 203 / 204 / 205
              </span>
            </div>
          </div>

          <Button
            variant="primary"
            size="md"
            isLoading={downloadingType === "cyclonedx"}
            onClick={() =>
              handleDownload(
                "cyclonedx",
                downloadCycloneDxReport,
                `cbom_${assessmentId}.cyclonedx.json`
              )
            }
            icon={<Download size={15} />}
          >
            Download CycloneDX JSON
          </Button>
        </Card>

        {/* RFC 4180 CRLF CSV */}
        <Card
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            padding: "1.5rem",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
              <div
                style={{
                  width: "40px",
                  height: "40px",
                  borderRadius: "8px",
                  backgroundColor: "rgba(59, 82, 64, 0.08)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--olive-primary)",
                }}
              >
                <FileSpreadsheet size={22} />
              </div>
              <Badge variant="low">RFC 4180</Badge>
            </div>

            <h3 style={{ fontSize: "1.05rem", fontWeight: 600, color: "var(--text-primary)", margin: "0 0 0.5rem 0" }}>
              RFC 4180 CRLF CSV Export
            </h3>
            <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)", lineHeight: 1.45, margin: "0 0 1rem 0" }}>
              Tabular inventory of all discovered primitives and risk scores. Hardened with comprehensive
              spreadsheet formula-injection mitigation (CWE-1236) and standard CRLF line breaks.
            </p>

            <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", marginBottom: "1.25rem" }}>
              <span className="qf-tag" style={{ fontSize: "0.7rem", padding: "0.15rem 0.45rem", backgroundColor: "var(--bg-tertiary)", borderRadius: "4px" }}>
                CWE-1236 Neutralized
              </span>
              <span className="qf-tag" style={{ fontSize: "0.7rem", padding: "0.15rem 0.45rem", backgroundColor: "var(--bg-tertiary)", borderRadius: "4px" }}>
                Excel / GRC Ready
              </span>
            </div>
          </div>

          <Button
            variant="outline"
            size="md"
            isLoading={downloadingType === "csv"}
            onClick={() =>
              handleDownload(
                "csv",
                downloadCsvReport,
                `cbom_${assessmentId}.csv`
              )
            }
            icon={<Download size={15} />}
          >
            Download CSV Inventory
          </Button>
        </Card>

        {/* Executive Markdown Report */}
        <Card
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            padding: "1.5rem",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
              <div
                style={{
                  width: "40px",
                  height: "40px",
                  borderRadius: "8px",
                  backgroundColor: "rgba(59, 82, 64, 0.08)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--olive-primary)",
                }}
              >
                <FileText size={22} />
              </div>
              <Badge variant="inferred">Markdown</Badge>
            </div>

            <h3 style={{ fontSize: "1.05rem", fontWeight: 600, color: "var(--text-primary)", margin: "0 0 0.5rem 0" }}>
              Executive Markdown Report
            </h3>
            <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)", lineHeight: 1.45, margin: "0 0 1rem 0" }}>
              Human-readable executive audit document. Includes Maximum Asset QVI analysis, category breakdown,
              Shor/Grover threat matrices, and NIST PQC migration timeline roadmap.
            </p>

            <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", marginBottom: "1.25rem" }}>
              <span className="qf-tag" style={{ fontSize: "0.7rem", padding: "0.15rem 0.45rem", backgroundColor: "var(--bg-tertiary)", borderRadius: "4px" }}>
                Executive Briefing
              </span>
              <span className="qf-tag" style={{ fontSize: "0.7rem", padding: "0.15rem 0.45rem", backgroundColor: "var(--bg-tertiary)", borderRadius: "4px" }}>
                Audit Provenance
              </span>
            </div>
          </div>

          <Button
            variant="outline"
            size="md"
            isLoading={downloadingType === "markdown"}
            onClick={() =>
              handleDownload(
                "markdown",
                downloadMarkdownReport,
                `report_${assessmentId}.md`
              )
            }
            icon={<Download size={15} />}
          >
            Download Markdown Report
          </Button>
        </Card>
      </div>
    </div>
  );
};

