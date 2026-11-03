import React from "react";
import { Radar, Layers, Cpu } from "lucide-react";
import { useRouter } from "../../router";

export const PlatformPage: React.FC = () => {
  const { navigate } = useRouter();

  return (
    <div style={{ maxWidth: "1280px", margin: "0 auto", padding: "4rem 2rem 6rem 2rem", display: "flex", flexDirection: "column", gap: "4.5rem" }}>
      {/* Header */}
      <div style={{ maxWidth: "800px" }}>
        <div style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--olive-primary)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
          Platform Architecture & Capabilities
        </div>
        <h1 style={{ fontFamily: "var(--font-serif)", fontSize: "clamp(2.2rem, 4vw, 3.2rem)", fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.15, margin: "0 0 1.25rem 0" }}>
          Unified Cryptographic Discovery & Quantum Risk Management
        </h1>
        <p style={{ fontSize: "1.1rem", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
          Quantum Flow bridges the gap between active network telemetry, static source code AST analysis,
          and compliance automation. Built for regulated environments where deterministic accuracy is non-negotiable.
        </p>
      </div>

      {/* Deep Dive Pillars */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "2rem" }}>
        {/* Pillar 1 */}
        <div style={{ backgroundColor: "#FFFFFF", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "2.25rem" }}>
          <div style={{ width: "42px", height: "42px", borderRadius: "8px", backgroundColor: "var(--olive-light)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--olive-primary)", marginBottom: "1.25rem" }}>
            <Radar size={22} />
          </div>
          <h3 style={{ fontSize: "1.25rem", fontWeight: 700, margin: "0 0 0.75rem 0" }}>Multi-Collector Ingestion</h3>
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.55, margin: "0 0 1rem 0" }}>
            Autonomous discovery workers isolate and execute specialized collectors:
          </p>
          <ul style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.6, paddingLeft: "1.25rem", margin: 0 }}>
            <li><strong>Network TLS Handshake:</strong> Pinned-IP socket inspection, leaf certificates, and cipher suites.</li>
            <li><strong>Python Source AST:</strong> Compiler-grade AST node visiting for cryptographic calls and algorithms.</li>
            <li><strong>Package Manifests:</strong> Automated dependency lockfile ingestion (requirements.txt, package.json).</li>
            <li><strong>Ingress Configurations:</strong> Nginx, Apache, and Envoy reverse proxy SSL directives.</li>
          </ul>
        </div>

        {/* Pillar 2 */}
        <div style={{ backgroundColor: "#FFFFFF", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "2.25rem" }}>
          <div style={{ width: "42px", height: "42px", borderRadius: "8px", backgroundColor: "var(--olive-light)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--olive-primary)", marginBottom: "1.25rem" }}>
            <Layers size={22} />
          </div>
          <h3 style={{ fontSize: "1.25rem", fontWeight: 700, margin: "0 0 0.75rem 0" }}>CycloneDX 1.6 CBOM</h3>
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.55, margin: "0 0 1rem 0" }}>
            A Cryptographic Bill of Materials (CBOM) serves as the source of truth for cryptographic posture:
          </p>
          <ul style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.6, paddingLeft: "1.25rem", margin: 0 }}>
            <li>Standardized schema mapping conforming to CycloneDX 1.6 Cryptography extension.</li>
            <li>Detailed primitive classifications: PKE, Signature, Key-Agreement, KEM, AE, Block Cipher.</li>
            <li>Evidence quality tracking: OBSERVED (direct socket), INFERRED (heuristic), IMPORTED (manifest).</li>
            <li>RFC 4180 CSV and CycloneDX JSON automated streaming export.</li>
          </ul>
        </div>

        {/* Pillar 3 */}
        <div style={{ backgroundColor: "#FFFFFF", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "2.25rem" }}>
          <div style={{ width: "42px", height: "42px", borderRadius: "8px", backgroundColor: "var(--olive-light)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--olive-primary)", marginBottom: "1.25rem" }}>
            <Cpu size={22} />
          </div>
          <h3 style={{ fontSize: "1.25rem", fontWeight: 700, margin: "0 0 0.75rem 0" }}>Process Isolation & Containment</h3>
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.55, margin: "0 0 1rem 0" }}>
            Enterprise scanner executions run under strict kernel-enforced sandboxes:
          </p>
          <ul style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.6, paddingLeft: "1.25rem", margin: 0 }}>
            <li>Windows Job Object containment with <code>JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE</code>.</li>
            <li>POSIX process groups with suspended launch and verified pgid group termination.</li>
            <li>SafeDestinationResolver preventing SSRF attacks against private and cloud metadata endpoints.</li>
            <li>PostgreSQL 64-bit advisory locking serializing concurrent worker leases.</li>
          </ul>
        </div>
      </div>

      {/* CTA Box */}
      <div style={{ backgroundColor: "var(--olive-light)", border: "1px solid var(--olive-border)", borderRadius: "12px", padding: "3rem 2rem", textAlign: "center" }}>
        <h2 style={{ fontFamily: "var(--font-serif)", fontSize: "1.85rem", color: "var(--text-primary)", margin: "0 0 1rem 0" }}>
          Ready to inspect your organization's cryptographic footprint?
        </h2>
        <div style={{ display: "flex", justifyContent: "center", gap: "1rem", flexWrap: "wrap", marginTop: "1.5rem" }}>
          <button
            type="button"
            className="qf-btn-primary"
            onClick={() => navigate("/scan")}
            style={{ padding: "0.85rem 1.75rem", borderRadius: "8px", backgroundColor: "var(--olive-primary)", color: "#FFFFFF", fontWeight: 600, border: "none", cursor: "pointer" }}
          >
            Run Free TLS Scan
          </button>
          <button
            type="button"
            className="qf-btn-outline"
            onClick={() => navigate("/request-demo")}
            style={{ padding: "0.85rem 1.5rem", borderRadius: "8px", border: "1px solid var(--olive-border)", backgroundColor: "#FFFFFF", color: "var(--text-primary)", fontWeight: 600, cursor: "pointer" }}
          >
            Request Enterprise Demo
          </button>
        </div>
      </div>
    </div>
  );
};
