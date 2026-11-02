import React from "react";
import {
  ShieldAlert,
  Terminal,
  Code2,
  Database,
  Cpu,
  Layers,
  CheckCircle,
  FileText,
} from "lucide-react";
import { HealthWidget } from "../health/HealthWidget";

export const DashboardOverview: React.FC = () => {
  return (
    <div className="qf-dashboard">
      <div className="qf-welcome-card">
        <div className="qf-welcome-header">
          <div className="qf-welcome-tag">Sprint 0 Implementation Complete</div>
          <h2>Post-Quantum Cryptography Control Plane</h2>
          <p>
            The engineering foundation for Quantum Flow Technologies is established.
            The modular monolith architecture, typed settings, dual liveness/readiness probes,
            asynchronous database and cache layers, and frontend interface are active.
          </p>
        </div>
        <div className="qf-status-pill-row">
          <span className="qf-pill qf-pill-ok">
            <CheckCircle size={14} /> Modular Monolith Active
          </span>
          <span className="qf-pill qf-pill-ok">
            <CheckCircle size={14} /> SQLAlchemy 2.x + Alembic
          </span>
          <span className="qf-pill qf-pill-ok">
            <CheckCircle size={14} /> React 18 + TypeScript + Vite
          </span>
          <span className="qf-pill qf-pill-ok">
            <CheckCircle size={14} /> Scanner Safety Sandbox RFC 5737
          </span>
        </div>
      </div>

      <div className="qf-section-title">
        <Terminal size={18} />
        <h3>System Diagnostics & Real-Time Probes</h3>
      </div>
      <HealthWidget />

      <div className="qf-section-title">
        <Layers size={18} />
        <h3>Foundational Architecture Subsystems</h3>
      </div>
      <div className="qf-subsystems-grid">
        <div className="qf-subsystem-card">
          <div className="qf-subsystem-header">
            <Cpu size={20} className="text-cyan" />
            <h4>FastAPI Modular Monolith</h4>
            <span className="qf-tag-ready">READY</span>
          </div>
          <p>
            High-performance async control plane located in <code>services/api</code>.
            Configured with typed pydantic-settings, structured error envelopes,
            and CORS origin whitelisting.
          </p>
        </div>

        <div className="qf-subsystem-card">
          <div className="qf-subsystem-header">
            <Database size={20} className="text-emerald" />
            <h4>PostgreSQL & Alembic Migrations</h4>
            <span className="qf-tag-ready">CONFIGURED</span>
          </div>
          <p>
            Async SQLAlchemy 2.x engine using asyncpg for application workloads
            and Psycopg for synchronous schema migrations in <code>migrations/</code>.
          </p>
        </div>

        <div className="qf-subsystem-card">
          <div className="qf-subsystem-header">
            <Layers size={20} className="text-purple" />
            <h4>Asynchronous Worker Daemon</h4>
            <span className="qf-tag-ready">SCAFFOLDED</span>
          </div>
          <p>
            Decoupled worker daemon in <code>services/worker</code> running
            background tasks, cryptographic scans, and heavy QVI risk computations
            via Redis queue.
          </p>
        </div>

        <div className="qf-subsystem-card">
          <div className="qf-subsystem-header">
            <ShieldAlert size={20} className="text-amber" />
            <h4>Scanner Safety Safeguards</h4>
            <span className="qf-tag-ready">ENFORCED</span>
          </div>
          <p>
            Package boundary in <code>packages/scanner</code> strictly prohibits scanning
            external or production targets. Restricted to RFC 5737 / RFC 3849 testnets
            and explicitly authorised local IP ranges.
          </p>
        </div>

        <div className="qf-subsystem-card">
          <div className="qf-subsystem-header">
            <Code2 size={20} className="text-blue" />
            <h4>React 18 + Vite Frontend Shell</h4>
            <span className="qf-tag-ready">ACTIVE</span>
          </div>
          <p>
            Responsive enterprise interface in <code>apps/web</code> featuring TypeScript,
            strict ESLint, Vitest integration, and live diagnostic widgets.
          </p>
        </div>

        <div className="qf-subsystem-card">
          <div className="qf-subsystem-header">
            <FileText size={20} className="text-pink" />
            <h4>Documentation & Governance Baseline</h4>
            <span className="qf-tag-ready">VERIFIED</span>
          </div>
          <p>
            Complete architectural documents, PRD, TRD, SAD, Threat Model, and ADR
            records preserved and organized in <code>docs/</code>.
          </p>
        </div>
      </div>
    </div>
  );
};

