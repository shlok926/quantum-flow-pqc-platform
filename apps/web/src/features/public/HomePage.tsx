import React, { useState } from "react";
import {
  Radar,
  ArrowRight,
  ShieldCheck,
  Layers,
  Flame,
  GitBranch,
  Lock,
  CheckCircle2,
} from "lucide-react";
import { useRouter } from "../../router";

export const HomePage: React.FC = () => {
  const { navigate } = useRouter();
  const [quickDomain, setQuickDomain] = useState<string>("");

  const handleQuickScan = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = quickDomain.trim();
    if (trimmed) {
      navigate(`/scan?domain=${encodeURIComponent(trimmed)}`);
    } else {
      navigate("/scan");
    }
  };

  return (
    <div className="qf-public-home" style={{ display: "flex", flexDirection: "column", gap: "6rem", paddingBottom: "4rem" }}>
      {/* =========================================================================
          SECTION 2: HERO SECTION
          ========================================================================= */}
      <section
        style={{
          padding: "5rem 2rem 2rem 2rem",
          maxWidth: "1280px",
          margin: "0 auto",
          width: "100%",
        }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
            gap: "3.5rem",
            alignItems: "center",
          }}
        >
          {/* Left Column: Editorial Headline & Copy */}
          <div style={{ maxWidth: "620px" }}>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem",
                padding: "0.3rem 0.75rem",
                borderRadius: "9999px",
                backgroundColor: "var(--olive-light)",
                border: "1px solid var(--olive-border)",
                fontSize: "0.775rem",
                fontWeight: 700,
                color: "var(--olive-primary)",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                marginBottom: "1.5rem",
              }}
            >
              <ShieldCheck size={14} />
              <span>NIST FIPS 203 / 204 / 205 Standards Alignment</span>
            </div>

            <h1
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: "clamp(2.4rem, 4.5vw, 3.5rem)",
                fontWeight: 700,
                color: "var(--text-primary)",
                lineHeight: 1.15,
                letterSpacing: "-0.02em",
                margin: "0 0 1.5rem 0",
              }}
            >
              Discover Your Cryptographic Exposure. Prepare for the Quantum Era.
            </h1>

            <p
              style={{
                fontSize: "1.125rem",
                color: "var(--text-secondary)",
                lineHeight: 1.6,
                margin: "0 0 2rem 0",
              }}
            >
              Quantum Flow helps enterprises discover cryptographic assets across networks, code,
              and infrastructure, assess quantum-vulnerable infrastructure, prioritise risk with deterministic
              QVI scoring, and execute their transition to post-quantum cryptography.
            </p>

            <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "center" }}>
              <button
                type="button"
                className="qf-btn-primary"
                onClick={() => navigate("/scan")}
                style={{
                  padding: "0.85rem 1.75rem",
                  fontSize: "1rem",
                  fontWeight: 600,
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  borderRadius: "8px",
                  border: "none",
                  backgroundColor: "var(--olive-primary)",
                  color: "#FFFFFF",
                  cursor: "pointer",
                  boxShadow: "0 2px 4px rgba(59, 82, 64, 0.15)",
                }}
              >
                <Radar size={18} />
                <span>Run Free Scan</span>
              </button>

              <button
                type="button"
                className="qf-btn-outline"
                onClick={() => navigate("/request-demo")}
                style={{
                  padding: "0.85rem 1.5rem",
                  fontSize: "1rem",
                  fontWeight: 600,
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  borderRadius: "8px",
                  border: "1px solid var(--border-color)",
                  backgroundColor: "#FFFFFF",
                  color: "var(--text-primary)",
                  cursor: "pointer",
                }}
              >
                <span>Request a Demo</span>
                <ArrowRight size={16} />
              </button>
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "1.5rem",
                marginTop: "2.5rem",
                paddingTop: "1.5rem",
                borderTop: "1px solid var(--border-light)",
                fontSize: "0.8rem",
                color: "var(--text-muted)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                <CheckCircle2 size={15} style={{ color: "var(--olive-primary)" }} />
                <span>Zero Installation</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                <CheckCircle2 size={15} style={{ color: "var(--olive-primary)" }} />
                <span>RFC 5737 Bounded Probes</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                <CheckCircle2 size={15} style={{ color: "var(--olive-primary)" }} />
                <span>RFC 8785 Sealed Evidence</span>
              </div>
            </div>
          </div>

          {/* Right Column: Architectural Visual Card (Original Cryptographic Exposure Graphic) */}
          <div
            style={{
              backgroundColor: "#FFFFFF",
              border: "1px solid var(--border-color)",
              borderRadius: "14px",
              padding: "1.75rem",
              boxShadow: "0 10px 30px rgba(15, 23, 42, 0.05)",
              display: "flex",
              flexDirection: "column",
              gap: "1.25rem",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border-light)", paddingBottom: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <div style={{ width: "10px", height: "10px", borderRadius: "50%", backgroundColor: "var(--olive-primary)" }}></div>
                <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)" }}>
                  Observable Cryptographic Posture Map
                </span>
              </div>
              <span className="font-mono" style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                RFC 8785 Sealed
              </span>
            </div>

            {/* Simulated Live Exposure Nodes */}
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <div style={{ padding: "0.85rem 1rem", backgroundColor: "var(--bg-tertiary)", borderRadius: "8px", borderLeft: "4px solid var(--rose-primary)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "0.8rem", fontWeight: 600 }}>Leaf Public Key: RSA-2048</span>
                  <span style={{ fontSize: "0.7rem", fontWeight: 700, color: "var(--rose-primary)", backgroundColor: "#FEE2E2", padding: "0.15rem 0.5rem", borderRadius: "4px" }}>
                    SHOR VULNERABLE
                  </span>
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.3rem" }}>
                  Target handshake relies on factoring assumption. Requires transition to ML-DSA.
                </div>
              </div>

              <div style={{ padding: "0.85rem 1rem", backgroundColor: "var(--bg-tertiary)", borderRadius: "8px", borderLeft: "4px solid #D97706" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "0.8rem", fontWeight: 600 }}>Key Exchange: X25519 (ECDH)</span>
                  <span style={{ fontSize: "0.7rem", fontWeight: 700, color: "#D97706", backgroundColor: "#FEF3C7", padding: "0.15rem 0.5rem", borderRadius: "4px" }}>
                    HNDL EXPOSURE
                  </span>
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.3rem" }}>
                  Harvest-Now-Decrypt-Later risk. Migration target: X25519 + ML-KEM-768 hybrid.
                </div>
              </div>

              <div style={{ padding: "0.85rem 1rem", backgroundColor: "var(--bg-tertiary)", borderRadius: "8px", borderLeft: "4px solid var(--olive-primary)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "0.8rem", fontWeight: 600 }}>Bulk Cipher: AES-256-GCM</span>
                  <span style={{ fontSize: "0.7rem", fontWeight: 700, color: "var(--olive-primary)", backgroundColor: "var(--olive-light)", padding: "0.15rem 0.5rem", borderRadius: "4px" }}>
                    GROVER RESISTANT
                  </span>
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.3rem" }}>
                  128-bit post-quantum security margin maintained under quadratic speedup.
                </div>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: "0.75rem", borderTop: "1px solid var(--border-light)", fontSize: "0.8rem" }}>
              <span style={{ color: "var(--text-secondary)" }}>Deterministic QVI Score:</span>
              <span style={{ fontWeight: 700, color: "var(--rose-primary)" }}>785 / 1000 (HIGH RISK)</span>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          SECTION 3: PLATFORM CAPABILITIES
          ========================================================================= */}
      <section
        style={{
          maxWidth: "1280px",
          margin: "0 auto",
          padding: "0 2rem",
          width: "100%",
        }}
      >
        <div style={{ textAlign: "center", maxWidth: "700px", margin: "0 auto 3.5rem auto" }}>
          <h2
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: "2.25rem",
              fontWeight: 700,
              color: "var(--text-primary)",
              margin: "0 0 1rem 0",
            }}
          >
            Comprehensive Cryptographic Governance
          </h2>
          <p style={{ fontSize: "1rem", color: "var(--text-secondary)", lineHeight: 1.55 }}>
            Purpose-built architectural capabilities designed to lead regulated organizations
            from unknown cryptographic exposure to certified quantum resilience.
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: "1.75rem",
          }}
        >
          {/* Capability 1 */}
          <div
            style={{
              backgroundColor: "#FFFFFF",
              border: "1px solid var(--border-color)",
              borderRadius: "12px",
              padding: "2rem",
              display: "flex",
              flexDirection: "column",
              gap: "1rem",
            }}
          >
            <div
              style={{
                width: "44px",
                height: "44px",
                borderRadius: "8px",
                backgroundColor: "var(--olive-light)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--olive-primary)",
              }}
            >
              <Radar size={22} />
            </div>
            <h3 style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
              1. Cryptographic Discovery
            </h3>
            <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.55, margin: 0 }}>
              Discover cryptographic assets across authorized infrastructure. Automated multi-collector
              telemetry across public TLS endpoints, native Python AST code, and package dependency manifests.
            </p>
          </div>

          {/* Capability 2 */}
          <div
            style={{
              backgroundColor: "#FFFFFF",
              border: "1px solid var(--border-color)",
              borderRadius: "12px",
              padding: "2rem",
              display: "flex",
              flexDirection: "column",
              gap: "1rem",
            }}
          >
            <div
              style={{
                width: "44px",
                height: "44px",
                borderRadius: "8px",
                backgroundColor: "var(--olive-light)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--olive-primary)",
              }}
            >
              <Layers size={22} />
            </div>
            <h3 style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
              2. Cryptographic Inventory
            </h3>
            <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.55, margin: 0 }}>
              Centralized Cryptographic Bill of Materials (CBOM) per CycloneDX 1.6 Cryptography Standard.
              Correlate algorithms, key lengths, curves, and software components with immutable provenance.
            </p>
          </div>

          {/* Capability 3 */}
          <div
            style={{
              backgroundColor: "#FFFFFF",
              border: "1px solid var(--border-color)",
              borderRadius: "12px",
              padding: "2rem",
              display: "flex",
              flexDirection: "column",
              gap: "1rem",
            }}
          >
            <div
              style={{
                width: "44px",
                height: "44px",
                borderRadius: "8px",
                backgroundColor: "var(--olive-light)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--olive-primary)",
              }}
            >
              <Flame size={22} />
            </div>
            <h3 style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
              3. Quantum Risk Intelligence
            </h3>
            <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.55, margin: 0 }}>
              Deterministic 7-dimension Quantum Vulnerability Index (QVI Methodology v1.0).
              Differentiate Shor period-finding exposure from Grover square-root key halving with zero black-box scoring.
            </p>
          </div>

          {/* Capability 4 */}
          <div
            style={{
              backgroundColor: "#FFFFFF",
              border: "1px solid var(--border-color)",
              borderRadius: "12px",
              padding: "2rem",
              display: "flex",
              flexDirection: "column",
              gap: "1rem",
            }}
          >
            <div
              style={{
                width: "44px",
                height: "44px",
                borderRadius: "8px",
                backgroundColor: "var(--olive-light)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--olive-primary)",
              }}
            >
              <GitBranch size={22} />
            </div>
            <h3 style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
              4. Migration Planning
            </h3>
            <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.55, margin: 0 }}>
              Actionable transition paths aligned with NIST FIPS 203 (ML-KEM), FIPS 204 (ML-DSA),
              and FIPS 205 (SLH-DSA). Prioritize remediations based on exposure windows and business criticality.
            </p>
          </div>
        </div>
      </section>

      {/* =========================================================================
          SECTION 4: HOW QUANTUM FLOW WORKS (4-STAGE WORKFLOW)
          ========================================================================= */}
      <section
        style={{
          backgroundColor: "#F4F1EA",
          borderTop: "1px solid var(--border-color)",
          borderBottom: "1px solid var(--border-color)",
          padding: "5rem 2rem",
        }}
      >
        <div style={{ maxWidth: "1280px", margin: "0 auto" }}>
          <div style={{ textAlign: "center", maxWidth: "680px", margin: "0 auto 3.5rem auto" }}>
            <h2
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: "2.25rem",
                fontWeight: 700,
                color: "var(--text-primary)",
                margin: "0 0 1rem 0",
              }}
            >
              The 4-Stage Post-Quantum Lifecycle
            </h2>
            <p style={{ fontSize: "1rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
              A deterministic framework guiding cryptographic modernization across complex enterprise systems.
            </p>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
              gap: "2rem",
              position: "relative",
            }}
          >
            {/* Stage 1 */}
            <div style={{ backgroundColor: "#FFFFFF", padding: "1.75rem", borderRadius: "10px", border: "1px solid var(--border-color)" }}>
              <div style={{ fontSize: "0.8rem", fontWeight: 800, color: "var(--olive-primary)", letterSpacing: "0.08em", marginBottom: "0.5rem" }}>
                STAGE 01
              </div>
              <h3 style={{ fontSize: "1.25rem", fontWeight: 700, margin: "0 0 0.75rem 0", color: "var(--text-primary)" }}>
                DISCOVER
              </h3>
              <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.55, margin: 0 }}>
                Extract public TLS parameters, parse native AST source code, and inspect software package manifests
                under strict RFC 5737 safety boundaries.
              </p>
            </div>

            {/* Stage 2 */}
            <div style={{ backgroundColor: "#FFFFFF", padding: "1.75rem", borderRadius: "10px", border: "1px solid var(--border-color)" }}>
              <div style={{ fontSize: "0.8rem", fontWeight: 800, color: "var(--olive-primary)", letterSpacing: "0.08em", marginBottom: "0.5rem" }}>
                STAGE 02
              </div>
              <h3 style={{ fontSize: "1.25rem", fontWeight: 700, margin: "0 0 0.75rem 0", color: "var(--text-primary)" }}>
                INVENTORY
              </h3>
              <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.55, margin: 0 }}>
                Correlate findings into an automated Cryptographic Bill of Materials (CBOM), classifying evidence
                as OBSERVED, INFERRED, or IMPORTED.
              </p>
            </div>

            {/* Stage 3 */}
            <div style={{ backgroundColor: "#FFFFFF", padding: "1.75rem", borderRadius: "10px", border: "1px solid var(--border-color)" }}>
              <div style={{ fontSize: "0.8rem", fontWeight: 800, color: "var(--olive-primary)", letterSpacing: "0.08em", marginBottom: "0.5rem" }}>
                STAGE 03
              </div>
              <h3 style={{ fontSize: "1.25rem", fontWeight: 700, margin: "0 0 0.75rem 0", color: "var(--text-primary)" }}>
                PRIORITISE
              </h3>
              <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.55, margin: 0 }}>
                Evaluate quantum vulnerability with 7 weighted dimensions (Q, R, L, E, B, M, V) to calculate
                deterministic 0–1000 QVI risk indices.
              </p>
            </div>

            {/* Stage 4 */}
            <div style={{ backgroundColor: "#FFFFFF", padding: "1.75rem", borderRadius: "10px", border: "1px solid var(--border-color)" }}>
              <div style={{ fontSize: "0.8rem", fontWeight: 800, color: "var(--olive-primary)", letterSpacing: "0.08em", marginBottom: "0.5rem" }}>
                STAGE 04
              </div>
              <h3 style={{ fontSize: "1.25rem", fontWeight: 700, margin: "0 0 0.75rem 0", color: "var(--text-primary)" }}>
                PLAN & ACT
              </h3>
              <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.55, margin: 0 }}>
                Deploy NIST PQC remediation roadmaps, export RFC 8785 sealed verification reports,
                and track crypto-agility modernization.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          SECTION 5: FREE SCANNER PROMINENT CTA
          ========================================================================= */}
      <section
        style={{
          maxWidth: "1000px",
          margin: "0 auto",
          padding: "0 2rem",
          width: "100%",
        }}
      >
        <div
          style={{
            backgroundColor: "var(--olive-light)",
            border: "1px solid var(--olive-border)",
            borderRadius: "16px",
            padding: "3.5rem 2.5rem",
            textAlign: "center",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "1.5rem",
          }}
        >
          <div
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "10px",
              backgroundColor: "#FFFFFF",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--olive-primary)",
              boxShadow: "0 2px 4px rgba(59, 82, 64, 0.1)",
            }}
          >
            <Radar size={26} />
          </div>

          <h2
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: "2.25rem",
              fontWeight: 700,
              color: "var(--text-primary)",
              margin: 0,
            }}
          >
            Understand Your Website's Observable Quantum Exposure
          </h2>

          <p
            style={{
              fontSize: "1.05rem",
              color: "var(--text-secondary)",
              maxWidth: "680px",
              lineHeight: 1.6,
              margin: 0,
            }}
          >
            Run an instant, bounded public TLS assessment to inspect negotiated cryptographic parameters,
            evaluate key exchange curves, and identify visible post-quantum readiness signals.
          </p>

          {/* Quick Domain Input Box */}
          <form
            onSubmit={handleQuickScan}
            style={{
              display: "flex",
              gap: "0.75rem",
              maxWidth: "520px",
              width: "100%",
              marginTop: "0.5rem",
            }}
          >
            <input
              type="text"
              placeholder="e.g. example.com"
              value={quickDomain}
              onChange={(e) => setQuickDomain(e.target.value)}
              style={{
                flex: 1,
                padding: "0.85rem 1.15rem",
                borderRadius: "8px",
                border: "1px solid var(--olive-border)",
                fontSize: "0.95rem",
                backgroundColor: "#FFFFFF",
                color: "var(--text-primary)",
                outline: "none",
              }}
            />
            <button
              type="submit"
              className="qf-btn-primary"
              style={{
                padding: "0.85rem 1.5rem",
                borderRadius: "8px",
                backgroundColor: "var(--olive-primary)",
                color: "#FFFFFF",
                fontWeight: 600,
                border: "none",
                cursor: "pointer",
                whiteSpace: "nowrap",
              }}
            >
              Scan Domain
            </button>
          </form>

          <div
            style={{
              fontSize: "0.775rem",
              color: "var(--text-muted)",
              maxWidth: "620px",
              lineHeight: 1.45,
            }}
          >
            <strong>Scope Notice:</strong> The free scanner inspects publicly observable TLS handshake negotiation on port 443.
            It does not scan internal microservices, private keys, or enterprise repositories.
          </div>
        </div>
      </section>

      {/* =========================================================================
          SECTION 6: ENTERPRISE CAPABILITIES MATRIX
          ========================================================================= */}
      <section
        style={{
          maxWidth: "1280px",
          margin: "0 auto",
          padding: "0 2rem",
          width: "100%",
        }}
      >
        <div style={{ textAlign: "center", maxWidth: "680px", margin: "0 auto 3rem auto" }}>
          <h2
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: "2.25rem",
              fontWeight: 700,
              color: "var(--text-primary)",
              margin: "0 0 1rem 0",
            }}
          >
            From Public Perimeter to Full Enterprise Estate
          </h2>
          <p style={{ fontSize: "1rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
            See how the free public TLS scanner compares with the Quantum Flow Enterprise Platform.
          </p>
        </div>

        <div
          style={{
            backgroundColor: "#FFFFFF",
            border: "1px solid var(--border-color)",
            borderRadius: "12px",
            overflow: "hidden",
            boxShadow: "0 4px 12px rgba(15, 23, 42, 0.03)",
          }}
        >
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.9rem" }}>
            <thead>
              <tr style={{ backgroundColor: "var(--bg-tertiary)", borderBottom: "1px solid var(--border-color)" }}>
                <th style={{ padding: "1.25rem 1.5rem", fontWeight: 700, color: "var(--text-primary)" }}>Capability & Scope</th>
                <th style={{ padding: "1.25rem 1.5rem", fontWeight: 700, color: "var(--text-secondary)", width: "30%" }}>Free Public Scanner</th>
                <th style={{ padding: "1.25rem 1.5rem", fontWeight: 700, color: "var(--olive-primary)", width: "35%" }}>Quantum Flow Enterprise</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: "1px solid var(--border-light)" }}>
                <td style={{ padding: "1rem 1.5rem", fontWeight: 600 }}>Inspection Scope</td>
                <td style={{ padding: "1rem 1.5rem", color: "var(--text-secondary)" }}>Public TLS Handshake (Port 443)</td>
                <td style={{ padding: "1rem 1.5rem", color: "var(--olive-primary)", fontWeight: 600 }}>Multi-collector: TLS + Code AST + Configs + Manifests</td>
              </tr>
              <tr style={{ borderBottom: "1px solid var(--border-light)" }}>
                <td style={{ padding: "1rem 1.5rem", fontWeight: 600 }}>Cryptographic Bill of Materials (CBOM)</td>
                <td style={{ padding: "1rem 1.5rem", color: "var(--text-muted)" }}>Handshake Summary Only</td>
                <td style={{ padding: "1rem 1.5rem", color: "var(--olive-primary)", fontWeight: 600 }}>Full CycloneDX 1.6 Cryptography JSON</td>
              </tr>
              <tr style={{ borderBottom: "1px solid var(--border-light)" }}>
                <td style={{ padding: "1rem 1.5rem", fontWeight: 600 }}>Risk Scoring Framework</td>
                <td style={{ padding: "1rem 1.5rem", color: "var(--text-secondary)" }}>Readiness Signal</td>
                <td style={{ padding: "1rem 1.5rem", color: "var(--olive-primary)", fontWeight: 600 }}>Deterministic 7-Dimension QVI (0–1000)</td>
              </tr>
              <tr style={{ borderBottom: "1px solid var(--border-light)" }}>
                <td style={{ padding: "1rem 1.5rem", fontWeight: 600 }}>Report Verification & Sealing</td>
                <td style={{ padding: "1rem 1.5rem", color: "var(--text-muted)" }}>Web Findings Display</td>
                <td style={{ padding: "1rem 1.5rem", color: "var(--olive-primary)", fontWeight: 600 }}>RFC 8785 Canonical JSON SHA-256 Digest</td>
              </tr>
              <tr>
                <td style={{ padding: "1rem 1.5rem", fontWeight: 600 }}>Remediation Roadmap</td>
                <td style={{ padding: "1rem 1.5rem", color: "var(--text-muted)" }}>General Guidance</td>
                <td style={{ padding: "1rem 1.5rem", color: "var(--olive-primary)", fontWeight: 600 }}>NIST FIPS 203/204/205 Transition Workflows</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* =========================================================================
          SECTION 7: REQUEST DEMO CALL TO ACTION
          ========================================================================= */}
      <section
        style={{
          maxWidth: "1280px",
          margin: "0 auto",
          padding: "0 2rem",
          width: "100%",
        }}
      >
        <div
          style={{
            backgroundColor: "#FFFFFF",
            border: "1px solid var(--border-color)",
            borderRadius: "16px",
            padding: "4rem 2.5rem",
            textAlign: "center",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "1.5rem",
            boxShadow: "0 4px 20px rgba(15, 23, 42, 0.04)",
          }}
        >
          <div
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "10px",
              backgroundColor: "var(--olive-light)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--olive-primary)",
            }}
          >
            <Lock size={24} />
          </div>

          <h2
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: "2.4rem",
              fontWeight: 700,
              color: "var(--text-primary)",
              margin: 0,
            }}
          >
            Build Your Post-Quantum Readiness Roadmap
          </h2>

          <p
            style={{
              fontSize: "1.05rem",
              color: "var(--text-secondary)",
              maxWidth: "640px",
              lineHeight: 1.6,
              margin: 0,
            }}
          >
            Transitioning enterprise cryptography requires inventory certainty, deterministic risk prioritization,
            and cryptographic agility. Speak with our security engineering team today.
          </p>

          <button
            type="button"
            className="qf-btn-primary"
            onClick={() => navigate("/request-demo")}
            style={{
              padding: "0.95rem 2rem",
              fontSize: "1rem",
              fontWeight: 600,
              display: "inline-flex",
              alignItems: "center",
              gap: "0.5rem",
              borderRadius: "8px",
              border: "none",
              backgroundColor: "var(--olive-primary)",
              color: "#FFFFFF",
              cursor: "pointer",
              boxShadow: "0 2px 6px rgba(59, 82, 64, 0.2)",
            }}
          >
            <span>Request an Enterprise Demo</span>
            <ArrowRight size={16} />
          </button>
        </div>
      </section>
    </div>
  );
};
