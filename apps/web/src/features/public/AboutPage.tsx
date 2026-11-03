import React from "react";
import { ShieldCheck, Target, Award } from "lucide-react";

export const AboutPage: React.FC = () => {

  return (
    <div style={{ maxWidth: "1280px", margin: "0 auto", padding: "4rem 2rem 6rem 2rem", display: "flex", flexDirection: "column", gap: "4rem" }}>
      {/* Header */}
      <div style={{ maxWidth: "800px" }}>
        <div style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--olive-primary)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
          Company & Product Mission
        </div>
        <h1 style={{ fontFamily: "var(--font-serif)", fontSize: "clamp(2.2rem, 4vw, 3.2rem)", fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.15, margin: "0 0 1.25rem 0" }}>
          Securing Modern Infrastructure for the Quantum Future
        </h1>
        <p style={{ fontSize: "1.1rem", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
          Quantum Flow was conceived to address the critical lack of automated cryptographic visibility
          facing enterprises ahead of global post-quantum compliance mandates.
        </p>
      </div>

      {/* Core Principles */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "2rem" }}>
        <div style={{ backgroundColor: "#FFFFFF", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "2.25rem" }}>
          <div style={{ width: "42px", height: "42px", borderRadius: "8px", backgroundColor: "var(--olive-light)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--olive-primary)", marginBottom: "1.25rem" }}>
            <Target size={22} />
          </div>
          <h3 style={{ fontSize: "1.25rem", fontWeight: 700, margin: "0 0 0.75rem 0" }}>Deterministic Discovery</h3>
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
            We reject probabilistic or generative assumptions in cybersecurity telemetry.
            Every finding reported by Quantum Flow is backed by verifiable cryptographic evidence—from byte-level
            TLS socket handshakes to compiler-parsed AST node traces.
          </p>
        </div>

        <div style={{ backgroundColor: "#FFFFFF", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "2.25rem" }}>
          <div style={{ width: "42px", height: "42px", borderRadius: "8px", backgroundColor: "var(--olive-light)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--olive-primary)", marginBottom: "1.25rem" }}>
            <ShieldCheck size={22} />
          </div>
          <h3 style={{ fontSize: "1.25rem", fontWeight: 700, margin: "0 0 0.75rem 0" }}>Open Compliance Standards</h3>
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
            Our architecture is rooted in open standards: CycloneDX 1.6 Cryptographic Bill of Materials,
            NIST SP 800-208 stateful hash-based signatures, and RFC 8785 Canonical JSON sealing for cryptographic tamper proofing.
          </p>
        </div>

        <div style={{ backgroundColor: "#FFFFFF", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "2.25rem" }}>
          <div style={{ width: "42px", height: "42px", borderRadius: "8px", backgroundColor: "var(--olive-light)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--olive-primary)", marginBottom: "1.25rem" }}>
            <Award size={22} />
          </div>
          <h3 style={{ fontSize: "1.25rem", fontWeight: 700, margin: "0 0 0.75rem 0" }}>Kernel-Enforced Safety</h3>
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
            Security scanners must never introduce operational risk. All scanner sub-processes execute under
            kernel containment (Windows Job Objects and POSIX Process Groups) with strictly bounded timeouts and memory limits.
          </p>
        </div>
      </div>
    </div>
  );
};
