import React from "react";
import { ShieldCheck, GitCommit, FileCode, CheckCircle } from "lucide-react";

export const Footer: React.FC = () => {
  return (
    <footer className="qf-footer">
      <div className="qf-footer-content">
        <div className="qf-footer-brand">
          <ShieldCheck size={16} style={{ color: "var(--olive-primary)" }} />
          <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>
            Quantum Flow Technologies
          </span>
          <span style={{ color: "var(--border-color)", margin: "0 0.5rem" }}>|</span>
          <span>NIST SP 800-208 / FIPS 203 / 204 / 205 Architecture</span>
        </div>

        <div className="qf-footer-meta">
          <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <CheckCircle size={13} style={{ color: "var(--emerald-primary)" }} />
            <span>PostgreSQL 16 Storage Pinned</span>
          </div>
          <span style={{ color: "var(--border-color)", margin: "0 0.25rem" }}>•</span>
          <div className="qf-commit">
            <GitCommit size={14} />
            <span>Sprint 3 Step 4 (Enterprise UI/UX Phase 3)</span>
          </div>
          <span style={{ color: "var(--border-color)", margin: "0 0.25rem" }}>•</span>
          <a
            href="https://github.com/shlok926/quantum-flow-pqc-platform/tree/main/docs"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.3rem",
              color: "var(--olive-primary)",
              textDecoration: "none",
              fontWeight: 600,
            }}
          >
            <FileCode size={13} />
            <span>Security Specifications</span>
          </a>
        </div>
      </div>
    </footer>
  );
};
