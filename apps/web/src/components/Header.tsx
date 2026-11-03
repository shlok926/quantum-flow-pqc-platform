import React from "react";
import { ShieldCheck, Plus, BookOpen, Layers, Terminal } from "lucide-react";

interface HeaderProps {
  onNewAssessment?: () => void;
  tenantName?: string;
  environment?: string;
}

export const Header: React.FC<HeaderProps> = ({
  onNewAssessment,
  tenantName = "Default Enterprise Tenant",
  environment = "production",
}) => {
  return (
    <header className="qf-header">
      <div className="qf-brand">
        <div
          style={{
            width: "36px",
            height: "36px",
            borderRadius: "8px",
            backgroundColor: "var(--olive-light)",
            border: "1px solid var(--olive-border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--olive-primary)",
          }}
        >
          <ShieldCheck size={22} />
        </div>
        <div>
          <h1
            className="qf-title"
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: "1.25rem",
              fontWeight: 600,
              letterSpacing: "-0.01em",
              color: "var(--text-primary)",
            }}
          >
            QUANTUM FLOW
          </h1>
          <span className="qf-subtitle">
            Cryptographic Discovery & Quantum Risk Intelligence Platform
          </span>
        </div>
      </div>

      <div className="qf-header-meta">
        {/* Stage Badge */}
        <div className="qf-badge qf-badge-stage">
          <Terminal size={14} />
          <span>Sprint 0: Engineering Foundation</span>
        </div>

        {/* Tenant & Environment Pill */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            backgroundColor: "var(--bg-tertiary)",
            border: "1px solid var(--border-color)",
            padding: "0.25rem 0.65rem",
            borderRadius: "6px",
            fontSize: "0.775rem",
            color: "var(--text-secondary)",
          }}
        >
          <Layers size={14} style={{ color: "var(--olive-primary)" }} />
          <span style={{ fontWeight: 600 }}>{tenantName}</span>
          <span
            style={{
              fontSize: "0.65rem",
              textTransform: "uppercase",
              backgroundColor: "var(--olive-light)",
              color: "var(--olive-primary)",
              padding: "0.1rem 0.35rem",
              borderRadius: "3px",
              fontWeight: 700,
            }}
          >
            {environment}
          </span>
        </div>

        {/* Live Status */}
        <div className="qf-badge qf-badge-status">
          <span className="qf-pulse-dot"></span>
          <span>Control Plane Online</span>
        </div>

        {/* Documentation Link */}
        <a
          href="https://github.com/shlok926/quantum-flow-pqc-platform/tree/main/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="qf-doc-link"
        >
          <BookOpen size={14} />
          <span>Documentation</span>
        </a>

        {/* New Assessment Quick CTA */}
        {onNewAssessment && (
          <button
            type="button"
            className="qf-btn-primary"
            style={{ padding: "0.45rem 0.9rem", fontSize: "0.8rem" }}
            onClick={onNewAssessment}
          >
            <Plus size={15} />
            <span>New Assessment</span>
          </button>
        )}
      </div>
    </header>
  );
};
