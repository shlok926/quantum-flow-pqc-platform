import React from "react";
import { ShieldCheck, ArrowRight, ExternalLink } from "lucide-react";
import { useRouter } from "../../router";

export const PublicFooter: React.FC = () => {
  const { navigate } = useRouter();

  return (
    <footer
      style={{
        backgroundColor: "#FFFFFF",
        borderTop: "1px solid var(--border-color)",
        padding: "4rem 2rem 2.5rem 2rem",
        marginTop: "auto",
      }}
    >
      <div
        style={{
          maxWidth: "1280px",
          margin: "0 auto",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "2.5rem",
          marginBottom: "3rem",
        }}
      >
        {/* Brand Column */}
        <div style={{ maxWidth: "340px" }}>
          <div
            onClick={() => navigate("/")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.6rem",
              cursor: "pointer",
              marginBottom: "1rem",
            }}
          >
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "6px",
                backgroundColor: "var(--olive-light)",
                border: "1px solid var(--olive-border)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--olive-primary)",
              }}
            >
              <ShieldCheck size={18} />
            </div>
            <span
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: "1.15rem",
                fontWeight: 700,
                color: "var(--text-primary)",
              }}
            >
              QUANTUM FLOW
            </span>
          </div>
          <p
            style={{
              fontSize: "0.85rem",
              color: "var(--text-secondary)",
              lineHeight: 1.55,
              margin: "0 0 1.25rem 0",
            }}
          >
            Cryptographic discovery, automated CBOM generation, and deterministic quantum risk intelligence
            for modern enterprise infrastructure.
          </p>
          <div
            style={{
              fontSize: "0.75rem",
              color: "var(--text-muted)",
              lineHeight: 1.5,
              padding: "0.6rem 0.8rem",
              backgroundColor: "var(--bg-tertiary)",
              borderRadius: "6px",
              border: "1px solid var(--border-light)",
            }}
          >
            <strong>Standards-Aligned:</strong> NIST SP 800-208, FIPS 203 (ML-KEM), FIPS 204 (ML-DSA), and FIPS 205 (SLH-DSA).
          </div>
        </div>

        {/* Platform Column */}
        <div>
          <h4
            style={{
              fontSize: "0.85rem",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              color: "var(--text-primary)",
              marginBottom: "1rem",
            }}
          >
            Platform
          </h4>
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.6rem", fontSize: "0.85rem" }}>
            <li>
              <button
                type="button"
                onClick={() => navigate("/platform")}
                style={{ background: "none", border: "none", padding: 0, color: "var(--text-secondary)", cursor: "pointer", textAlign: "left" }}
              >
                Platform Capabilities
              </button>
            </li>
            <li>
              <button
                type="button"
                onClick={() => navigate("/intelligence")}
                style={{ background: "none", border: "none", padding: 0, color: "var(--text-secondary)", cursor: "pointer", textAlign: "left" }}
              >
                Quantum Risk Intelligence
              </button>
            </li>
            <li>
              <button
                type="button"
                onClick={() => navigate("/scan")}
                style={{ background: "none", border: "none", padding: 0, color: "var(--olive-primary)", fontWeight: 600, cursor: "pointer", textAlign: "left" }}
              >
                Free Public TLS Scanner
              </button>
            </li>
            <li>
              <button
                type="button"
                onClick={() => navigate("/app")}
                style={{ background: "none", border: "none", padding: 0, color: "var(--text-secondary)", cursor: "pointer", textAlign: "left" }}
              >
                Enterprise Console
              </button>
            </li>
          </ul>
        </div>

        {/* Methodology & Standards Column */}
        <div>
          <h4
            style={{
              fontSize: "0.85rem",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              color: "var(--text-primary)",
              marginBottom: "1rem",
            }}
          >
            Methodology & Standards
          </h4>
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.6rem", fontSize: "0.85rem" }}>
            <li>
              <button
                type="button"
                onClick={() => navigate("/intelligence")}
                style={{ background: "none", border: "none", padding: 0, color: "var(--text-secondary)", cursor: "pointer", textAlign: "left" }}
              >
                QVI Methodology v1.0
              </button>
            </li>
            <li>
              <button
                type="button"
                onClick={() => navigate("/resources")}
                style={{ background: "none", border: "none", padding: 0, color: "var(--text-secondary)", cursor: "pointer", textAlign: "left" }}
              >
                CycloneDX 1.6 CBOM
              </button>
            </li>
            <li>
              <button
                type="button"
                onClick={() => navigate("/resources")}
                style={{ background: "none", border: "none", padding: 0, color: "var(--text-secondary)", cursor: "pointer", textAlign: "left" }}
              >
                Shor & Grover Threat Models
              </button>
            </li>
            <li>
              <a
                href="https://csrc.nist.gov/Projects/post-quantum-cryptography"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: "var(--text-secondary)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "0.3rem" }}
              >
                <span>NIST PQC Standardization</span>
                <ExternalLink size={12} />
              </a>
            </li>
          </ul>
        </div>

        {/* Enterprise & Engagement Column */}
        <div>
          <h4
            style={{
              fontSize: "0.85rem",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              color: "var(--text-primary)",
              marginBottom: "1rem",
            }}
          >
            Enterprise
          </h4>
          <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)", lineHeight: 1.5, margin: "0 0 1rem 0" }}>
            Assess production source repositories, internal PKI, and reverse proxies with deterministic risk guarantees.
          </p>
          <button
            type="button"
            className="qf-btn-primary"
            onClick={() => navigate("/request-demo")}
            style={{
              padding: "0.55rem 1rem",
              fontSize: "0.825rem",
              fontWeight: 600,
              display: "inline-flex",
              alignItems: "center",
              gap: "0.4rem",
              borderRadius: "6px",
              border: "none",
              color: "#FFFFFF",
              backgroundColor: "var(--olive-primary)",
              cursor: "pointer",
            }}
          >
            <span>Request Enterprise Demo</span>
            <ArrowRight size={13} />
          </button>
        </div>
      </div>

      {/* Bottom Bar */}
      <div
        style={{
          maxWidth: "1280px",
          margin: "0 auto",
          paddingTop: "1.5rem",
          borderTop: "1px solid var(--border-light)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1rem",
          fontSize: "0.775rem",
          color: "var(--text-muted)",
        }}
      >
        <div>
          © {new Date().getFullYear()} Quantum Flow Technologies. All rights reserved.
        </div>
        <div style={{ display: "flex", gap: "1.5rem" }}>
          <button
            type="button"
            onClick={() => navigate("/about")}
            style={{ background: "none", border: "none", padding: 0, color: "var(--text-muted)", cursor: "pointer", fontSize: "0.775rem" }}
          >
            About
          </button>
          <button
            type="button"
            onClick={() => navigate("/resources")}
            style={{ background: "none", border: "none", padding: 0, color: "var(--text-muted)", cursor: "pointer", fontSize: "0.775rem" }}
          >
            Security & Architecture
          </button>
          <button
            type="button"
            onClick={() => navigate("/scan")}
            style={{ background: "none", border: "none", padding: 0, color: "var(--text-muted)", cursor: "pointer", fontSize: "0.775rem" }}
          >
            Public Scanner
          </button>
        </div>
      </div>
    </footer>
  );
};

