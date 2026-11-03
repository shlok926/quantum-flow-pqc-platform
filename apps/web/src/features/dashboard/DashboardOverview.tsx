import React, { useEffect, useState } from "react";
import {
  ShieldAlert,
  Terminal,
  Code2,
  Database,
  Cpu,
  Layers,
  CheckCircle,
  FileText,
  Plus,
  ShieldCheck,
  ArrowRight,
} from "lucide-react";
import { HealthWidget } from "../health/HealthWidget";
import { AssessmentResponse } from "../../types";
import { listAssessments } from "../../services/api";
import { Button } from "../../components/common/Button";
import { Badge } from "../../components/common/Badge";
import { Card } from "../../components/common/Card";

interface DashboardOverviewProps {
  onNewAssessment?: () => void;
  onSelectAssessment?: (id: string, stage: string) => void;
}

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({
  onNewAssessment,
  onSelectAssessment,
}) => {
  const [recentAssessments, setRecentAssessments] = useState<AssessmentResponse[]>([]);

  useEffect(() => {
    let mounted = true;
    async function fetchRecent() {
      try {
        const res = await listAssessments({ limit: 4 });
        if (mounted) {
          setRecentAssessments(res.items || []);
        }
      } catch {
        // Fallback silently if offline or initial load
      }
    }
    fetchRecent();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="qf-dashboard">
      {/* Enterprise Executive Banner */}
      <div className="qf-welcome-card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
          <div className="qf-welcome-header" style={{ maxWidth: "720px" }}>
            <div className="qf-welcome-tag">Sprint 0 Implementation Complete</div>
            <h2>Post-Quantum Cryptography Control Plane</h2>
            <p>
              The engineering foundation for Quantum Flow Technologies is established.
              The modular monolith architecture, typed settings, dual liveness/readiness probes,
              asynchronous database and cache layers, and frontend interface are active.
            </p>
          </div>
          {onNewAssessment && (
            <div style={{ alignSelf: "center" }}>
              <Button
                variant="primary"
                size="md"
                onClick={onNewAssessment}
                icon={<Plus size={15} />}
              >
                Launch Assessment
              </Button>
            </div>
          )}
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

      {/* Quick Launch & Recent Assessments Strip */}
      {recentAssessments.length > 0 && (
        <div>
          <div className="qf-section-title" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <ShieldCheck size={18} style={{ color: "var(--olive-primary)" }} />
              <h3>Recent Cryptographic Assessments</h3>
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: "1rem",
              marginTop: "0.75rem",
            }}
          >
            {recentAssessments.map((a) => {
              const target = (a.target_snapshot?.hostname as string) || "General Scope";
              const score = Number(a.risk_summary?.max_asset_qvi ?? a.risk_summary?.qvi_score ?? a.risk_summary?.overall_score ?? -1);
              return (
                <Card
                  key={a.id}
                  style={{
                    padding: "1rem",
                    cursor: onSelectAssessment ? "pointer" : "default",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    gap: "0.75rem",
                  }}
                  onClick={() => onSelectAssessment && onSelectAssessment(a.id, a.progress_stage)}
                >
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.4rem" }}>
                      <Badge variant={a.status === "completed" ? "low" : a.status === "failed" ? "critical" : "inferred"}>
                        {a.status}
                      </Badge>
                      {score >= 0 && (
                        <span
                          style={{
                            fontWeight: 700,
                            fontSize: "0.85rem",
                            color: score >= 600 ? "var(--rose-primary)" : score >= 400 ? "#D97706" : "var(--olive-primary)",
                          }}
                        >
                          QVI {score}
                        </span>
                      )}
                    </div>
                    <div style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--text-primary)" }}>
                      {a.title}
                    </div>
                    <div className="font-mono" style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
                      {target}
                    </div>
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                    <span>{new Date(a.created_at).toLocaleDateString()}</span>
                    <span style={{ color: "var(--olive-primary)", fontWeight: 500, display: "flex", alignItems: "center", gap: "0.2rem" }}>
                      Inspect <ArrowRight size={12} />
                    </span>
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* Health Probes & Platform Diagnostics */}
      <div className="qf-section-title">
        <Terminal size={18} />
        <h3>System Diagnostics & Real-Time Probes</h3>
      </div>
      <HealthWidget />

      {/* Foundational Architecture Subsystems */}
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
