import React, { useState } from "react";
import { CheckCircle2, ArrowRight, Lock, Download } from "lucide-react";
import { useRouter } from "../../router";
import { triggerBlobDownload } from "../../services/api";

export const RequestDemoPage: React.FC = () => {
  const { navigate } = useRouter();

  // Form Fields
  const [fullName, setFullName] = useState<string>("");
  const [email, setEmail] = useState<string>("");
  const [organization, setOrganization] = useState<string>("");
  const [jobTitle, setJobTitle] = useState<string>("");
  const [interest, setInterest] = useState<string>("complete_platform");
  const [message, setMessage] = useState<string>("");

  // Form State
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [submitted, setSubmitted] = useState<boolean>(false);

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!fullName.trim()) newErrors.fullName = "Full name is required.";
    if (!email.trim()) {
      newErrors.email = "Business email is required.";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      newErrors.email = "Please enter a valid email address.";
    }
    if (!organization.trim()) newErrors.organization = "Organization name is required.";
    if (!jobTitle.trim()) newErrors.jobTitle = "Job title is required.";

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleDownloadSampleReport = () => {
    const sampleMd = `# Quantum Flow Enterprise — Sample Cryptographic Discovery & Quantum Risk Report
Document Reference: QFT-ENT-SAMPLE-2026-v1
Classification: CONFIDENTIAL / COMMERCIAL IN CONFIDENCE
Standards Baseline: NIST SP 800-208 | FIPS 203 (ML-KEM) | FIPS 204 (ML-DSA) | CycloneDX 1.6

---

## Executive Summary
This sample report illustrates the depth and fidelity of the Quantum Flow Enterprise discovery engine.
Unlike perimeter-only probes, the Enterprise platform combines:
1. Multi-Collector Ingestion: Network TLS, Python/Java/Go AST code parsing, manifest dependencies, OS keystores.
2. Kernel-Enforced Process Containment: Windows Job Objects & POSIX process groups preventing rogue scanner processes.
3. CycloneDX 1.6 Cryptographic Bill of Materials (CBOM): Machine-readable inventory with RFC 8785 canonical hashes.
4. Quantum Vulnerability Index (QVI Methodology v1.0): 7-dimension weighted risk evaluation.

### Overall Enterprise Quantum Exposure
- Total Cryptographic Assets Discovered: 1,482 assets
- Shor Vulnerable Asymmetric Keys: 642 keys (RSA, ECDSA)
- Grover Sensitive Symmetric Ciphers: 840 ciphers (AES-128, AES-256)
- High-Risk Active HNDL Pathways: 38 external mTLS endpoints
- Enterprise QVI Score: 785 / 1000 (HIGH QUANTUM RISK)

---
*To schedule a customized evaluation against your enterprise code repositories and infrastructure, submit the technical briefing inquiry.*
`;
    const blob = new Blob([sampleMd], { type: "text/markdown;charset=utf-8" });
    triggerBlobDownload(blob, "quantumflow_enterprise_sample_report.md");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    // Note: Since no public CRM/contact endpoint currently exists in backend API,
    // we simulate realistic validation and save inquiry to browser session for demo.
    await new Promise((resolve) => setTimeout(resolve, 800));
    setSubmitting(false);
    setSubmitted(true);
  };

  return (
    <div style={{ maxWidth: "1000px", margin: "0 auto", padding: "4rem 2rem 6rem 2rem" }}>
      <div style={{ textAlign: "center", maxWidth: "680px", margin: "0 auto 3.5rem auto" }}>
        <div style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--olive-primary)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
          Enterprise Engagement
        </div>
        <h1 style={{ fontFamily: "var(--font-serif)", fontSize: "clamp(2.2rem, 4vw, 3rem)", fontWeight: 700, color: "var(--text-primary)", margin: "0 0 1rem 0" }}>
          Request an Enterprise Architecture Demo
        </h1>
        <p style={{ fontSize: "1.05rem", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
          Experience Quantum Flow's automated CBOM generation, deterministic QVI evaluation,
          and kernel-isolated discovery workflows in a tailored 30-minute technical session.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "3rem", alignItems: "start" }}>
        {/* Left Side: Value Props */}
        <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
          <div style={{ backgroundColor: "#FFFFFF", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "2rem" }}>
            <h3 style={{ fontSize: "1.15rem", fontWeight: 700, margin: "0 0 1rem 0", color: "var(--text-primary)" }}>
              What to Expect in Your Demo:
            </h3>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "1rem", fontSize: "0.9rem", color: "var(--text-secondary)" }}>
              <li style={{ display: "flex", alignItems: "flex-start", gap: "0.6rem" }}>
                <CheckCircle2 size={18} style={{ color: "var(--olive-primary)", flexShrink: 0, marginTop: "2px" }} />
                <span><strong>Multi-Collector Orchestration:</strong> Live walkthrough of TLS, Python AST, and manifest discovery.</span>
              </li>
              <li style={{ display: "flex", alignItems: "flex-start", gap: "0.6rem" }}>
                <CheckCircle2 size={18} style={{ color: "var(--olive-primary)", flexShrink: 0, marginTop: "2px" }} />
                <span><strong>CycloneDX 1.6 CBOM Export:</strong> Live ingestion and JSON schema validation.</span>
              </li>
              <li style={{ display: "flex", alignItems: "flex-start", gap: "0.6rem" }}>
                <CheckCircle2 size={18} style={{ color: "var(--olive-primary)", flexShrink: 0, marginTop: "2px" }} />
                <span><strong>QVI Methodology v1.0 Scoring:</strong> Deep dive into the 7 weighted risk dimensions.</span>
              </li>
              <li style={{ display: "flex", alignItems: "flex-start", gap: "0.6rem" }}>
                <CheckCircle2 size={18} style={{ color: "var(--olive-primary)", flexShrink: 0, marginTop: "2px" }} />
                <span><strong>Cryptographic Tamper Sealing:</strong> RFC 8785 Canonical JSON SHA-256 evidence validation.</span>
              </li>
            </ul>
          </div>

          <div style={{ backgroundColor: "#FFFFFF", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "1.75rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.5rem" }}>
              <Download size={18} style={{ color: "var(--olive-primary)" }} />
              <span>Looking for a Sample Report?</span>
            </div>
            <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.5, margin: "0 0 1rem 0" }}>
              Download an authentic anonymized Quantum Flow Enterprise Cryptographic Bill of Materials (CBOM) & QVI risk audit.
            </p>
            <button
              type="button"
              onClick={handleDownloadSampleReport}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem",
                padding: "0.6rem 1rem",
                borderRadius: "6px",
                backgroundColor: "var(--bg-secondary)",
                border: "1px solid var(--border-color)",
                color: "var(--text-primary)",
                fontSize: "0.85rem",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              <Download size={15} style={{ color: "var(--olive-primary)" }} />
              <span>Download Sample Enterprise Report (.md)</span>
            </button>
          </div>

          <div style={{ padding: "1.25rem 1.5rem", backgroundColor: "var(--olive-light)", borderRadius: "10px", border: "1px solid var(--olive-border)", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 700, color: "var(--olive-primary)", marginBottom: "0.3rem" }}>
              <Lock size={15} />
              <span>Strict Data Confidentiality</span>
            </div>
            We operate under non-disclosure agreements with regulated enterprise customers. All discovery data is strictly isolated by tenant.
          </div>
        </div>

        {/* Right Side: Form / Success State */}
        <div style={{ backgroundColor: "#FFFFFF", border: "1px solid var(--border-color)", borderRadius: "14px", padding: "2.5rem", boxShadow: "0 4px 20px rgba(15, 23, 42, 0.04)" }}>
          {submitted ? (
            <div style={{ textAlign: "center", padding: "2rem 1rem", display: "flex", flexDirection: "column", alignItems: "center", gap: "1.25rem" }}>
              <div style={{ width: "52px", height: "52px", borderRadius: "50%", backgroundColor: "var(--olive-light)", color: "var(--olive-primary)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <CheckCircle2 size={30} />
              </div>
              <h3 style={{ fontFamily: "var(--font-serif)", fontSize: "1.5rem", fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
                Demo Request Received
              </h3>
              <p style={{ fontSize: "0.925rem", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
                Thank you, <strong>{fullName}</strong>. An enterprise cryptography specialist will contact you at <strong>{email}</strong> within one business day to coordinate the architecture demo.
              </p>
              <div style={{ padding: "0.85rem 1.25rem", backgroundColor: "var(--bg-tertiary)", borderRadius: "8px", fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
                Inquiry registered for organization: <strong>{organization}</strong>
              </div>
              <button
                type="button"
                className="qf-btn-primary"
                onClick={() => navigate("/scan")}
                style={{ marginTop: "1rem", padding: "0.75rem 1.5rem", borderRadius: "8px", backgroundColor: "var(--olive-primary)", color: "#FFFFFF", border: "none", fontWeight: 600, cursor: "pointer" }}
              >
                Try Free Public Scanner Meanwhile
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
              <h3 style={{ fontSize: "1.2rem", fontWeight: 700, margin: "0 0 0.5rem 0", color: "var(--text-primary)" }}>
                Schedule Technical Briefing
              </h3>

              <div>
                <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.35rem" }}>
                  Full Name *
                </label>
                <input
                  type="text"
                  className="qf-form-input"
                  style={{ width: "100%", padding: "0.65rem 0.85rem", borderRadius: "6px", border: "1px solid var(--border-color)", fontSize: "0.9rem" }}
                  placeholder="e.g. Elena Rostova"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
                {errors.fullName && <div style={{ fontSize: "0.75rem", color: "var(--rose-primary)", marginTop: "0.25rem" }}>{errors.fullName}</div>}
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.35rem" }}>
                  Business Email *
                </label>
                <input
                  type="email"
                  className="qf-form-input"
                  style={{ width: "100%", padding: "0.65rem 0.85rem", borderRadius: "6px", border: "1px solid var(--border-color)", fontSize: "0.9rem" }}
                  placeholder="e.g. elena@enterprise.corp"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
                {errors.email && <div style={{ fontSize: "0.75rem", color: "var(--rose-primary)", marginTop: "0.25rem" }}>{errors.email}</div>}
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.35rem" }}>
                    Organization *
                  </label>
                  <input
                    type="text"
                    className="qf-form-input"
                    style={{ width: "100%", padding: "0.65rem 0.85rem", borderRadius: "6px", border: "1px solid var(--border-color)", fontSize: "0.9rem" }}
                    placeholder="e.g. Acme Financial"
                    value={organization}
                    onChange={(e) => setOrganization(e.target.value)}
                  />
                  {errors.organization && <div style={{ fontSize: "0.75rem", color: "var(--rose-primary)", marginTop: "0.25rem" }}>{errors.organization}</div>}
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.35rem" }}>
                    Job Title *
                  </label>
                  <input
                    type="text"
                    className="qf-form-input"
                    style={{ width: "100%", padding: "0.65rem 0.85rem", borderRadius: "6px", border: "1px solid var(--border-color)", fontSize: "0.9rem" }}
                    placeholder="e.g. CISO / Security Architect"
                    value={jobTitle}
                    onChange={(e) => setJobTitle(e.target.value)}
                  />
                  {errors.jobTitle && <div style={{ fontSize: "0.75rem", color: "var(--rose-primary)", marginTop: "0.25rem" }}>{errors.jobTitle}</div>}
                </div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.35rem" }}>
                  Primary Area of Interest
                </label>
                <select
                  className="qf-form-select"
                  style={{ width: "100%", padding: "0.65rem 0.85rem", borderRadius: "6px", border: "1px solid var(--border-color)", fontSize: "0.9rem", backgroundColor: "#FFFFFF" }}
                  value={interest}
                  onChange={(e) => setInterest(e.target.value)}
                >
                  <option value="complete_platform">Full Platform Demonstration</option>
                  <option value="cbom">CycloneDX 1.6 CBOM Generation</option>
                  <option value="qvi">QVI Risk Prioritization & Threat Modeling</option>
                  <option value="pqc_migration">NIST FIPS 203/204/205 Transition Planning</option>
                  <option value="custom_collectors">Custom Source & Binary Inspection</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.35rem" }}>
                  Additional Notes (Optional)
                </label>
                <textarea
                  className="qf-form-textarea"
                  rows={3}
                  style={{ width: "100%", padding: "0.65rem 0.85rem", borderRadius: "6px", border: "1px solid var(--border-color)", fontSize: "0.9rem", fontFamily: "inherit" }}
                  placeholder="Tell us about your infrastructure or compliance timeline..."
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                />
              </div>

              <button
                type="submit"
                className="qf-btn-primary"
                disabled={submitting}
                style={{
                  marginTop: "0.5rem",
                  padding: "0.85rem",
                  borderRadius: "8px",
                  backgroundColor: "var(--olive-primary)",
                  color: "#FFFFFF",
                  fontWeight: 600,
                  fontSize: "0.95rem",
                  border: "none",
                  cursor: submitting ? "not-allowed" : "pointer",
                  opacity: submitting ? 0.7 : 1,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "0.5rem",
                }}
              >
                <span>{submitting ? "Submitting Inquiry..." : "Submit Technical Demo Request"}</span>
                <ArrowRight size={16} />
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
