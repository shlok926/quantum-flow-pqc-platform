import React, { useState } from "react";
import {
  Radar,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Lock,
  Server,
  KeyRound,
} from "lucide-react";
import { useRouter } from "../../router";
import {
  registerTarget,
  listTargets,
  verifyTarget,
  triggerScan,
  getScan,
} from "../../services/api";
import { Target, Scan } from "../../types";

const STAGES = [
  { key: "VALIDATE", label: "Validating domain & SSRF safety rules" },
  { key: "REGISTER", label: "Registering target & authorization status" },
  { key: "VERIFY", label: "Verifying domain destination eligibility" },
  { key: "HANDSHAKE", label: "Executing bounded TLS handshake on port 443" },
  { key: "CERTIFICATE", label: "Extracting X.509 certificate chain & ciphers" },
  { key: "EVALUATE", label: "Evaluating Shor & Grover threat exposure" },
  { key: "COMPLETE", label: "Preparing cryptographic findings report" },
];

export const ScannerPage: React.FC = () => {
  const { navigate } = useRouter();

  // Parse URL query parameter if user arrived from homepage quick scan
  const [domainInput, setDomainInput] = useState<string>(() => {
    if (typeof window !== "undefined") {
      const sp = new URLSearchParams(window.location.search);
      return sp.get("domain") || "";
    }
    return "";
  });

  const [authConfirmed, setAuthConfirmed] = useState<boolean>(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Execution states
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [currentStageIndex, setCurrentStageIndex] = useState<number>(0);
  const [scanError, setScanError] = useState<string | null>(null);

  // Domain Normalization & Syntax Validation (per RFC 1035 / RFC 5737)
  const normalizeAndValidate = (raw: string): { cleanHost: string; error: string | null } => {
    let clean = raw.trim().toLowerCase();
    if (!clean) {
      return { cleanHost: "", error: "Please enter a domain name." };
    }

    // Strip scheme if user pasted full URL
    if (clean.startsWith("https://")) clean = clean.slice(8);
    if (clean.startsWith("http://")) clean = clean.slice(7);

    // Strip paths, query strings, and fragments
    const slashIdx = clean.indexOf("/");
    if (slashIdx !== -1) clean = clean.slice(0, slashIdx);
    const qIdx = clean.indexOf("?");
    if (qIdx !== -1) clean = clean.slice(0, qIdx);
    const hIdx = clean.indexOf("#");
    if (hIdx !== -1) clean = clean.slice(0, hIdx);

    // Check for prohibited ports
    if (clean.includes(":")) {
      return { cleanHost: clean, error: "Port numbers are prohibited. Public scanner inspects standard port 443." };
    }

    // Check for IP literals (SSRF guardrail)
    const ipv4Regex = /^(\d{1,3}\.){3}\d{1,3}$/;
    if (ipv4Regex.test(clean) || clean.includes("::")) {
      return { cleanHost: clean, error: "IP literals are prohibited. Provide a valid domain name (e.g. example.com)." };
    }

    // Strip trailing dot
    if (clean.endsWith(".")) clean = clean.slice(0, -1);

    const labels = clean.split(".");
    if (labels.length < 2) {
      return { cleanHost: clean, error: "Domain must contain at least two labels (e.g. company.com)." };
    }

    for (const label of labels) {
      if (!label) return { cleanHost: clean, error: "Domain contains consecutive dots or empty labels." };
      if (label.length > 63) return { cleanHost: clean, error: "Domain label exceeds 63 characters." };
      if (label.startsWith("-") || label.endsWith("-")) {
        return { cleanHost: clean, error: "Domain labels cannot start or end with a hyphen." };
      }
      if (!/^[a-z0-9-]+$/.test(label)) {
        return { cleanHost: clean, error: `Invalid character in domain label '${label}'.` };
      }
    }

    return { cleanHost: clean, error: null };
  };

  const handleDomainChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setDomainInput(e.target.value);
    if (validationError) {
      const { error } = normalizeAndValidate(e.target.value);
      setValidationError(error);
    }
  };

  const executeRealScan = async (targetHostname: string) => {
    setIsScanning(true);
    setScanError(null);
    setCurrentStageIndex(0);

    try {
      // Stage 1: Validation
      setCurrentStageIndex(0);
      await new Promise((r) => setTimeout(r, 350));

      // Stage 2: Register Target & Authorisation
      setCurrentStageIndex(1);
      let target: Target | null = null;
      try {
        target = await registerTarget({
          hostname: targetHostname,
          environment: "production",
          criticality: "high",
          explicit_authorisation_confirmed: true,
          authorisation_declared: true,
        });
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        // If target already registered (HTTP 409 Conflict), lookup existing target
        if (msg.includes("already registered") || msg.includes("409")) {
          // Extract UUID from message if formatted as "ID: <UUID>"
          const idMatch = msg.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i);
          if (idMatch) {
            target = { id: idMatch[0], hostname: targetHostname, status: "pending_verification" } as Target;
          } else {
            const listRes = await listTargets({ limit: 100 });
            const items = Array.isArray(listRes) ? listRes : listRes.items || [];
            const found = items.find((t) => t.hostname === targetHostname);
            if (found) {
              target = found;
            } else {
              throw new Error(`Target '${targetHostname}' is registered in database. Proceeding with verification.`);
            }
          }
        } else {
          throw err;
        }
      }

      if (!target || !target.id) {
        throw new Error("Unable to establish target registration record.");
      }

      // Stage 3: Verification & Authorisation
      setCurrentStageIndex(2);
      try {
        await verifyTarget(target.id);
      } catch {
        // Continue if already verified
      }

      // Stage 4: Trigger Bounded TLS Handshake
      setCurrentStageIndex(3);
      const scanRes: Scan = await triggerScan(target.id);

      // Stage 5: Certificate Extraction
      setCurrentStageIndex(4);
      let pollAttempts = 0;
      let finalScan: Scan = scanRes;

      while (finalScan.status === "pending" || finalScan.status === "in_progress") {
        pollAttempts++;
        if (pollAttempts > 20) {
          throw new Error("Scan execution timed out after 30 seconds.");
        }
        await new Promise((r) => setTimeout(r, 1200));
        finalScan = await getScan(finalScan.id);
      }

      if (finalScan.status === "failed") {
        throw new Error(finalScan.error_message || "TLS handshake probe failed to establish connection.");
      }

      // Stage 6: Threat Analysis
      setCurrentStageIndex(5);
      await new Promise((r) => setTimeout(r, 450));

      // Stage 7: Finalize & Navigate
      setCurrentStageIndex(6);
      await new Promise((r) => setTimeout(r, 350));

      navigate(`/scan/results/${finalScan.id}`);
    } catch (err: unknown) {
      setScanError(err instanceof Error ? err.message : "Scan execution encountered an error.");
      setIsScanning(false);
    }
  };

  const handleStartScan = (e: React.FormEvent) => {
    e.preventDefault();
    const { cleanHost, error } = normalizeAndValidate(domainInput);
    if (error) {
      setValidationError(error);
      return;
    }
    if (!authConfirmed) {
      setValidationError("Please check the authorization declaration before initiating the scan.");
      return;
    }

    setValidationError(null);
    executeRealScan(cleanHost);
  };

  return (
    <div style={{ maxWidth: "1000px", margin: "0 auto", padding: "4rem 2rem 6rem 2rem" }}>
      {/* Page Header */}
      <div style={{ textAlign: "center", maxWidth: "720px", margin: "0 auto 3rem auto" }}>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "0.4rem",
            padding: "0.25rem 0.75rem",
            borderRadius: "9999px",
            backgroundColor: "var(--olive-light)",
            border: "1px solid var(--olive-border)",
            fontSize: "0.75rem",
            fontWeight: 700,
            color: "var(--olive-primary)",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            marginBottom: "1rem",
          }}
        >
          <Radar size={14} />
          <span>Public Perimeter Assessment</span>
        </div>

        <h1
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: "clamp(2.2rem, 4.5vw, 3.2rem)",
            fontWeight: 700,
            color: "var(--text-primary)",
            letterSpacing: "-0.02em",
            margin: "0 0 1rem 0",
          }}
        >
          Free Quantum Readiness Scanner
        </h1>

        <p style={{ fontSize: "1.05rem", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
          Inspect the public TLS configuration of your domain and understand its observable cryptographic
          exposure against Shor's algorithm and quantum decryption threats.
        </p>
      </div>

      {/* Main Scan Box or Live Progress */}
      {isScanning ? (
        <div
          style={{
            backgroundColor: "#FFFFFF",
            border: "1px solid var(--border-color)",
            borderRadius: "16px",
            padding: "3rem 2.5rem",
            boxShadow: "0 4px 20px rgba(15, 23, 42, 0.05)",
          }}
        >
          <div style={{ textAlign: "center", marginBottom: "2rem" }}>
            <div
              style={{
                width: "48px",
                height: "48px",
                borderRadius: "50%",
                backgroundColor: "var(--olive-light)",
                color: "var(--olive-primary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 1rem auto",
              }}
            >
              <RefreshCw className="qf-spin" size={24} />
            </div>
            <h3 style={{ fontFamily: "var(--font-serif)", fontSize: "1.5rem", color: "var(--text-primary)", margin: "0 0 0.5rem 0" }}>
              Inspecting {domainInput}...
            </h3>
            <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", margin: 0 }}>
              Performing destination-pinned socket probe and X.509 certificate chain analysis.
            </p>
          </div>

          {/* Stepper Progress */}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", maxWidth: "600px", margin: "0 auto" }}>
            {STAGES.map((s, idx) => {
              const isPast = idx < currentStageIndex;
              const isCurrent = idx === currentStageIndex;
              return (
                <div
                  key={s.key}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.75rem",
                    padding: "0.6rem 0.85rem",
                    borderRadius: "6px",
                    backgroundColor: isCurrent ? "var(--olive-light)" : "transparent",
                    color: isPast ? "var(--text-primary)" : isCurrent ? "var(--olive-primary)" : "var(--text-muted)",
                    fontWeight: isCurrent ? 600 : 500,
                    fontSize: "0.85rem",
                    transition: "all 0.2s ease",
                  }}
                >
                  {isPast ? (
                    <CheckCircle2 size={17} style={{ color: "var(--olive-primary)", flexShrink: 0 }} />
                  ) : isCurrent ? (
                    <RefreshCw className="qf-spin" size={17} style={{ color: "var(--olive-primary)", flexShrink: 0 }} />
                  ) : (
                    <div style={{ width: "17px", height: "17px", borderRadius: "50%", border: "2px solid var(--border-color)", flexShrink: 0 }} />
                  )}
                  <span>{s.label}</span>
                </div>
              );
            })}
          </div>

          {scanError && (
            <div style={{ marginTop: "2rem", padding: "1rem", backgroundColor: "#FEF2F2", border: "1px solid #FCA5A5", borderRadius: "8px", color: "var(--rose-primary)", fontSize: "0.85rem", textAlign: "center" }}>
              <AlertTriangle size={18} style={{ display: "inline", marginRight: "0.4rem", verticalAlign: "text-bottom" }} />
              <strong>Scan Error:</strong> {scanError}
              <div style={{ marginTop: "0.75rem" }}>
                <button
                  type="button"
                  onClick={() => setIsScanning(false)}
                  style={{ padding: "0.4rem 0.85rem", borderRadius: "6px", border: "1px solid var(--rose-primary)", backgroundColor: "#FFFFFF", color: "var(--rose-primary)", fontWeight: 600, cursor: "pointer", fontSize: "0.8rem" }}
                >
                  Return & Retry
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div
          style={{
            backgroundColor: "#FFFFFF",
            border: "1px solid var(--border-color)",
            borderRadius: "16px",
            padding: "2.5rem",
            boxShadow: "0 4px 20px rgba(15, 23, 42, 0.04)",
          }}
        >
          <form onSubmit={handleStartScan} style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.9rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.5rem" }}>
                Target Domain *
              </label>
              <div style={{ display: "flex", gap: "0.75rem" }}>
                <input
                  type="text"
                  placeholder="e.g. example.com or api.company.corp"
                  value={domainInput}
                  onChange={handleDomainChange}
                  style={{
                    flex: 1,
                    padding: "0.85rem 1.15rem",
                    borderRadius: "8px",
                    border: validationError ? "1px solid var(--rose-primary)" : "1px solid var(--border-color)",
                    fontSize: "1rem",
                    backgroundColor: "var(--bg-primary)",
                    color: "var(--text-primary)",
                    outline: "none",
                  }}
                />
                <button
                  type="submit"
                  className="qf-btn-primary"
                  style={{
                    padding: "0.85rem 1.75rem",
                    borderRadius: "8px",
                    backgroundColor: "var(--olive-primary)",
                    color: "#FFFFFF",
                    fontSize: "0.95rem",
                    fontWeight: 600,
                    border: "none",
                    cursor: "pointer",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    whiteSpace: "nowrap",
                  }}
                >
                  <Radar size={17} />
                  <span>Scan Domain</span>
                </button>
              </div>
              {validationError && (
                <div style={{ fontSize: "0.8rem", color: "var(--rose-primary)", marginTop: "0.4rem" }}>
                  {validationError}
                </div>
              )}
            </div>

            {/* Quick Suggestions */}
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap", fontSize: "0.8rem", color: "var(--text-muted)" }}>
              <span>Quick Test Targets:</span>
              {["cisco.com", "google.com", "github.com", "whatsapp.com"].map((dom) => (
                <button
                  key={dom}
                  type="button"
                  onClick={() => {
                    setDomainInput(dom);
                    setValidationError(null);
                  }}
                  style={{
                    padding: "0.2rem 0.55rem",
                    borderRadius: "4px",
                    border: "1px solid var(--border-color)",
                    backgroundColor: "var(--bg-tertiary)",
                    color: "var(--text-secondary)",
                    cursor: "pointer",
                    fontSize: "0.775rem",
                  }}
                >
                  {dom}
                </button>
              ))}
            </div>

            {/* Authorization Checkbox */}
            <div style={{ padding: "1rem 1.25rem", backgroundColor: "var(--bg-tertiary)", borderRadius: "8px", border: "1px solid var(--border-light)" }}>
              <label style={{ display: "flex", alignItems: "flex-start", gap: "0.6rem", cursor: "pointer", fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                <input
                  type="checkbox"
                  checked={authConfirmed}
                  onChange={(e) => setAuthConfirmed(e.target.checked)}
                  style={{ marginTop: "3px" }}
                />
                <span>
                  <strong>Explicit Authorisation Declaration:</strong> I confirm that I am authorized to discover public cryptographic parameters for this domain. The scan will perform a non-intrusive, destination-pinned TLS handshake inspection on standard port 443.
                </span>
              </label>
            </div>
          </form>

          {/* Explanation of what the scanner checks */}
          <div style={{ marginTop: "2.5rem", paddingTop: "2rem", borderTop: "1px solid var(--border-light)" }}>
            <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "1rem" }}>
              Parameters Inspected by Free Scanner:
            </h3>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem" }}>
              <div style={{ padding: "0.85rem", backgroundColor: "var(--bg-primary)", borderRadius: "8px", border: "1px solid var(--border-light)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontWeight: 600, fontSize: "0.85rem", color: "var(--text-primary)" }}>
                  <Server size={15} style={{ color: "var(--olive-primary)" }} />
                  <span>TLS Protocol Version</span>
                </div>
                <p style={{ fontSize: "0.775rem", color: "var(--text-muted)", margin: "0.3rem 0 0 0" }}>
                  Verifies TLSv1.3 vs legacy TLSv1.2 negotiation.
                </p>
              </div>

              <div style={{ padding: "0.85rem", backgroundColor: "var(--bg-primary)", borderRadius: "8px", border: "1px solid var(--border-light)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontWeight: 600, fontSize: "0.85rem", color: "var(--text-primary)" }}>
                  <KeyRound size={15} style={{ color: "var(--olive-primary)" }} />
                  <span>Key Exchange Curves</span>
                </div>
                <p style={{ fontSize: "0.775rem", color: "var(--text-muted)", margin: "0.3rem 0 0 0" }}>
                  Evaluates ECDHE curves against ML-KEM-768 hybrid readiness.
                </p>
              </div>

              <div style={{ padding: "0.85rem", backgroundColor: "var(--bg-primary)", borderRadius: "8px", border: "1px solid var(--border-light)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontWeight: 600, fontSize: "0.85rem", color: "var(--text-primary)" }}>
                  <Lock size={15} style={{ color: "var(--olive-primary)" }} />
                  <span>Leaf Public Key & Bit Length</span>
                </div>
                <p style={{ fontSize: "0.775rem", color: "var(--text-muted)", margin: "0.3rem 0 0 0" }}>
                  Detects RSA vs ECC factorization risk under Shor's algorithm.
                </p>
              </div>

              <div style={{ padding: "0.85rem", backgroundColor: "var(--bg-primary)", borderRadius: "8px", border: "1px solid var(--border-light)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontWeight: 600, fontSize: "0.85rem", color: "var(--text-primary)" }}>
                  <ShieldCheck size={15} style={{ color: "var(--olive-primary)" }} />
                  <span>Bulk Cipher Suite</span>
                </div>
                <p style={{ fontSize: "0.775rem", color: "var(--text-muted)", margin: "0.3rem 0 0 0" }}>
                  Inspects AES-256 vs AES-128 Grover security margin.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
