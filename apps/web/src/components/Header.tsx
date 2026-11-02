import React from "react";
import { ShieldCheck, Terminal, BookOpen } from "lucide-react";

export const Header: React.FC = () => {
  return (
    <header className="qf-header">
      <div className="qf-brand">
        <ShieldCheck className="qf-brand-icon" size={28} />
        <div>
          <h1 className="qf-title">QUANTUM FLOW</h1>
          <span className="qf-subtitle">PQC Discovery & Risk Assessment Platform</span>
        </div>
      </div>
      <div className="qf-header-meta">
        <div className="qf-badge qf-badge-stage">
          <Terminal size={14} />
          <span>Sprint 0: Engineering Foundation</span>
        </div>
        <div className="qf-badge qf-badge-status">
          <span className="qf-pulse-dot"></span>
          <span>Control Plane Online</span>
        </div>
        <a
          href="https://github.com/shlok926/quantum-flow-pqc-platform/tree/main/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="qf-doc-link"
        >
          <BookOpen size={16} />
          <span>Documentation</span>
        </a>
      </div>
    </header>
  );
};

