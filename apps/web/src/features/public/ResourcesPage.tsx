import React from "react";
import { FileCode, ShieldCheck, ExternalLink } from "lucide-react";

export const ResourcesPage: React.FC = () => {

  return (
    <div style={{ maxWidth: "1280px", margin: "0 auto", padding: "4rem 2rem 6rem 2rem", display: "flex", flexDirection: "column", gap: "4rem" }}>
      {/* Header */}
      <div style={{ maxWidth: "800px" }}>
        <div style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--olive-primary)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>
          Knowledge Base & Documentation
        </div>
        <h1 style={{ fontFamily: "var(--font-serif)", fontSize: "clamp(2.2rem, 4vw, 3.2rem)", fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.15, margin: "0 0 1.25rem 0" }}>
          Post-Quantum Cryptography Technical Resources
        </h1>
        <p style={{ fontSize: "1.1rem", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
          Authoritative technical specifications, regulatory migration guidance, and architecture whitepapers.
        </p>
      </div>

      {/* Standards & Specs Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "2rem" }}>
        {/* Resource 1 */}
        <div style={{ backgroundColor: "#FFFFFF", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "2rem" }}>
          <div style={{ width: "40px", height: "40px", borderRadius: "8px", backgroundColor: "var(--olive-light)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--olive-primary)", marginBottom: "1rem" }}>
            <ShieldCheck size={20} />
          </div>
          <h3 style={{ fontSize: "1.15rem", fontWeight: 700, margin: "0 0 0.5rem 0" }}>NIST FIPS 203 (ML-KEM)</h3>
          <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.55, margin: "0 0 1.25rem 0" }}>
            Module-Lattice-Based Key-Encapsulation Mechanism standard derived from CRYSTALS-Kyber.
            Primary standard for general encryption and hybrid TLS key agreement.
          </p>
          <a
            href="https://csrc.nist.gov/pubs/fips/203/final"
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontSize: "0.85rem", color: "var(--olive-primary)", fontWeight: 600, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "0.3rem" }}
          >
            <span>Read Official FIPS 203 Spec</span>
            <ExternalLink size={13} />
          </a>
        </div>

        {/* Resource 2 */}
        <div style={{ backgroundColor: "#FFFFFF", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "2rem" }}>
          <div style={{ width: "40px", height: "40px", borderRadius: "8px", backgroundColor: "var(--olive-light)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--olive-primary)", marginBottom: "1rem" }}>
            <ShieldCheck size={20} />
          </div>
          <h3 style={{ fontSize: "1.15rem", fontWeight: 700, margin: "0 0 0.5rem 0" }}>NIST FIPS 204 (ML-DSA)</h3>
          <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.55, margin: "0 0 1.25rem 0" }}>
            Module-Lattice-Based Digital Signature Algorithm standard derived from CRYSTALS-Dilithium.
            Primary standard for digital certificates, code signing, and server authentication.
          </p>
          <a
            href="https://csrc.nist.gov/pubs/fips/204/final"
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontSize: "0.85rem", color: "var(--olive-primary)", fontWeight: 600, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "0.3rem" }}
          >
            <span>Read Official FIPS 204 Spec</span>
            <ExternalLink size={13} />
          </a>
        </div>

        {/* Resource 3 */}
        <div style={{ backgroundColor: "#FFFFFF", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "2rem" }}>
          <div style={{ width: "40px", height: "40px", borderRadius: "8px", backgroundColor: "var(--olive-light)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--olive-primary)", marginBottom: "1rem" }}>
            <FileCode size={20} />
          </div>
          <h3 style={{ fontSize: "1.15rem", fontWeight: 700, margin: "0 0 0.5rem 0" }}>CycloneDX 1.6 CBOM Spec</h3>
          <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.55, margin: "0 0 1.25rem 0" }}>
            Official Cryptographic Bill of Materials specification extending Software Bill of Materials (SBOM)
            with algorithm primitives, key lengths, curves, and certificate chains.
          </p>
          <a
            href="https://cyclonedx.org/capabilities/cbom/"
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontSize: "0.85rem", color: "var(--olive-primary)", fontWeight: 600, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "0.3rem" }}
          >
            <span>Explore CBOM Standard</span>
            <ExternalLink size={13} />
          </a>
        </div>
      </div>
    </div>
  );
};
