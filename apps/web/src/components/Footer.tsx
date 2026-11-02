import React from "react";
import { Lock, GitCommit } from "lucide-react";

export const Footer: React.FC = () => {
  return (
    <footer className="qf-footer">
      <div className="qf-footer-content">
        <div className="qf-footer-brand">
          <Lock size={14} className="qf-footer-icon" />
          <span>Quantum Flow Technologies &bull; Post-Quantum Cryptography Platform</span>
        </div>
        <div className="qf-footer-meta">
          <span>Release: v0.1.0-sprint0</span>
          <span className="qf-divider">&bull;</span>
          <span className="qf-commit">
            <GitCommit size={14} />
            <code>Sprint 0 Base</code>
          </span>
          <span className="qf-divider">&bull;</span>
          <span>NIST SP 800-208 / FIPS 203 / 204 / 205 Architecture</span>
        </div>
      </div>
    </footer>
  );
};

