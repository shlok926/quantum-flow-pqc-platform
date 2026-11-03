import React from "react";
import { useRouter } from "../../router";

export const IntelligencePage: React.FC = () => {
  const { navigate } = useRouter();

  return (
    <div style={{ maxWidth: "1280px", margin: "0 auto", padding: "4rem 2rem 6rem 2rem", display: "flex", flexDirection: "column", gap: "4.5rem" }}>
      {/* Header */}
      <div style={{ maxWidth: "800px" }}>
        <div style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--olive-primary)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
          Cryptographic Intelligence & Threat Modeling
        </div>
        <h1 style={{ fontFamily: "var(--font-serif)", fontSize: "clamp(2.2rem, 4vw, 3.2rem)", fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.15, margin: "0 0 1.25rem 0" }}>
          Understanding Post-Quantum Vulnerability
        </h1>
        <p style={{ fontSize: "1.1rem", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
          The transition to post-quantum cryptography requires clear technical differentiation between
          discrete algorithmic threats. Quantum Flow provides explainable, deterministic intelligence.
        </p>
      </div>

      {/* Threat Comparison: Shor vs Grover */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "2rem" }}>
        <div style={{ backgroundColor: "#FFFFFF", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "2.25rem", borderLeft: "5px solid var(--rose-primary)" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--rose-primary)", backgroundColor: "#FEE2E2", padding: "0.2rem 0.5rem", borderRadius: "4px" }}>
              POLYNOMIAL BREAK
            </span>
            <span className="font-mono" style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>O((log N)³)</span>
          </div>
          <h3 style={{ fontSize: "1.35rem", fontWeight: 700, color: "var(--text-primary)", margin: "0 0 0.75rem 0" }}>
            Shor's Algorithm Threat
          </h3>
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.6, margin: "0 0 1.25rem 0" }}>
            Runs in polynomial time on Cryptographically Relevant Quantum Computers (CRQC). Solves prime factorization
            and discrete logarithms, completely breaking all widely deployed public-key primitives.
          </p>
          <div style={{ padding: "0.85rem", backgroundColor: "var(--bg-tertiary)", borderRadius: "6px", fontSize: "0.8rem" }}>
            <strong>Compromised Algorithms:</strong> RSA (all key lengths), ECDSA, Ed25519, Diffie-Hellman (DH/ECDH).
            <div style={{ marginTop: "0.5rem", color: "var(--rose-primary)", fontWeight: 600 }}>
              Remediation: Migrate to ML-KEM (FIPS 203) and ML-DSA (FIPS 204).
            </div>
          </div>
        </div>

        <div style={{ backgroundColor: "#FFFFFF", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "2.25rem", borderLeft: "5px solid #D97706" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#D97706", backgroundColor: "#FEF3C7", padding: "0.2rem 0.5rem", borderRadius: "4px" }}>
              QUADRATIC SPEEDUP
            </span>
            <span className="font-mono" style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>O(√N)</span>
          </div>
          <h3 style={{ fontSize: "1.35rem", fontWeight: 700, color: "var(--text-primary)", margin: "0 0 0.75rem 0" }}>
            Grover's Algorithm Threat
          </h3>
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.6, margin: "0 0 1.25rem 0" }}>
            Provides a quadratic speedup for unstructured database searches. Effectively halves the symmetric key length
            and collision security margin without invalidating the mathematical structure.
          </p>
          <div style={{ padding: "0.85rem", backgroundColor: "var(--bg-tertiary)", borderRadius: "6px", fontSize: "0.8rem" }}>
            <strong>Affected Algorithms:</strong> AES-128 (reduced to 64-bit strength), SHA-256 (reduced collision margin).
            <div style={{ marginTop: "0.5rem", color: "var(--olive-primary)", fontWeight: 600 }}>
              Remediation: Enforce minimum AES-256 (maintains 128-bit quantum security) and SHA-384+.
            </div>
          </div>
        </div>
      </div>

      {/* QVI Methodology v1.0 Breakdown */}
      <div style={{ backgroundColor: "#FFFFFF", border: "1px solid var(--border-color)", borderRadius: "14px", padding: "2.5rem" }}>
        <h2 style={{ fontFamily: "var(--font-serif)", fontSize: "1.85rem", color: "var(--text-primary)", margin: "0 0 1rem 0" }}>
          Quantum Vulnerability Index (QVI) Methodology v1.0
        </h2>
        <p style={{ fontSize: "0.95rem", color: "var(--text-secondary)", lineHeight: 1.55, maxWidth: "800px", margin: "0 0 2rem 0" }}>
          QVI evaluates 7 weighted technical dimensions (0–950 raw points normalized to 0–1000 scale).
          It replaces arbitrary vendor risk scores with explainable, deterministic mathematical contributions.
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "1.5rem" }}>
          <div style={{ padding: "1rem", backgroundColor: "var(--bg-tertiary)", borderRadius: "8px" }}>
            <div style={{ fontWeight: 700, fontSize: "0.9rem", color: "var(--text-primary)" }}>Q: Quantum Threat (300 pts)</div>
            <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "0.3rem" }}>
              Differentiates Shor-breakable asymmetric schemes (300 pts) from Grover symmetric degradation (100 pts) and recognized PQC (0 pts).
            </div>
          </div>

          <div style={{ padding: "1rem", backgroundColor: "var(--bg-tertiary)", borderRadius: "8px" }}>
            <div style={{ fontWeight: 700, fontSize: "0.9rem", color: "var(--text-primary)" }}>R: Residual Security (150 pts)</div>
            <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "0.3rem" }}>
              Evaluates classical and post-quantum effective bit strength under known cryptanalytic bounds.
            </div>
          </div>

          <div style={{ padding: "1rem", backgroundColor: "var(--bg-tertiary)", borderRadius: "8px" }}>
            <div style={{ fontWeight: 700, fontSize: "0.9rem", color: "var(--text-primary)" }}>L: Lifespan & Retention (150 pts)</div>
            <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "0.3rem" }}>
              Quantifies exposure to Harvest Now, Decrypt Later (HNDL) based on confidential data retention requirements.
            </div>
          </div>

          <div style={{ padding: "1rem", backgroundColor: "var(--bg-tertiary)", borderRadius: "8px" }}>
            <div style={{ fontWeight: 700, fontSize: "0.9rem", color: "var(--text-primary)" }}>E: Environment Exposure (100 pts)</div>
            <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "0.3rem" }}>
              Public Internet-facing perimeter endpoints vs isolated internal private networks.
            </div>
          </div>

          <div style={{ padding: "1rem", backgroundColor: "var(--bg-tertiary)", borderRadius: "8px" }}>
            <div style={{ fontWeight: 700, fontSize: "0.9rem", color: "var(--text-primary)" }}>B: Business Criticality (100 pts)</div>
            <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "0.3rem" }}>
              Tier-1 core transactional systems vs developer environments and non-critical workloads.
            </div>
          </div>

          <div style={{ padding: "1rem", backgroundColor: "var(--bg-tertiary)", borderRadius: "8px" }}>
            <div style={{ fontWeight: 700, fontSize: "0.9rem", color: "var(--text-primary)" }}>M & V: Complexity & Protocol (150 pts)</div>
            <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "0.3rem" }}>
              Crypto-agility migration difficulty (75 pts) and modern vs legacy protocol version support (75 pts).
            </div>
          </div>
        </div>
      </div>

      {/* Action CTA */}
      <div style={{ textAlign: "center" }}>
        <button
          type="button"
          className="qf-btn-primary"
          onClick={() => navigate("/scan")}
          style={{ padding: "0.9rem 2rem", fontSize: "1rem", borderRadius: "8px", backgroundColor: "var(--olive-primary)", color: "#FFFFFF", fontWeight: 600, border: "none", cursor: "pointer" }}
        >
          Check Your Domain's Quantum Readiness
        </button>
      </div>
    </div>
  );
};
