import React, { useEffect, useState } from "react";
import { AlertTriangle, Flame, ShieldAlert, CheckCircle, RefreshCw } from "lucide-react";
import { RiskAssessment } from "../../types";
import { listRiskAssessments } from "../../services/api";

export const RiskDashboard: React.FC = () => {
  const [assessments, setAssessments] = useState<RiskAssessment[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAssessment, setSelectedAssessment] = useState<RiskAssessment | null>(null);

  const loadAssessments = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listRiskAssessments({ limit: 50 });
      setAssessments(res.items);
      if (res.items.length > 0) {
        setSelectedAssessment(res.items[0]);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load risk assessments");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAssessments();
  }, []);

  const getCategoryBadgeClass = (category: string) => {
    switch (category) {
      case "critical":
        return "qf-badge-danger";
      case "high":
        return "qf-badge-warning";
      case "elevated":
        return "qf-badge-elevated";
      case "guarded":
        return "qf-badge-info";
      default:
        return "qf-badge-success";
    }
  };

  return (
    <div className="qf-risk-dashboard">
      <div className="qf-page-header">
        <div>
          <h2>Quantum Vulnerability Index (QVI) & Risk Intelligence</h2>
          <p className="qf-text-muted">
            Explainable quantum risk scores (Methodology v1.0, 0–1000 scale) with Shor vs. Grover
            threat classifications and traceable remediation guidance.
          </p>
        </div>
        <button
          type="button"
          className="qf-btn-secondary"
          onClick={loadAssessments}
          disabled={loading}
        >
          <RefreshCw size={16} className={loading ? "qf-spin" : ""} /> Refresh
        </button>
      </div>

      {error && <div className="qf-alert qf-alert-error">{error}</div>}

      {loading ? (
        <div className="qf-card qf-loading-state">Evaluating quantum vulnerability indices...</div>
      ) : assessments.length === 0 ? (
        <div className="qf-card qf-empty-state" style={{ textAlign: "center", padding: "2rem" }}>
          <Flame size={40} className="qf-text-muted" style={{ margin: "0 auto 1rem" }} />
          <h3>No Risk Evaluations Available</h3>
          <p className="qf-text-muted">
            Discover cryptographic assets or trigger an evaluation from the CBOM inventory to generate
            risk scores and migration recommendations.
          </p>
        </div>
      ) : (
        <div className="qf-split-view" style={{ display: "grid", gridTemplateColumns: "1fr 1.5fr", gap: "1.5rem" }}>
          {/* Assessment List */}
          <div className="qf-card">
            <h3>Evaluated Assets ({assessments.length})</h3>
            <div className="qf-list-group" style={{ marginTop: "1rem" }}>
              {assessments.map((item) => (
                <div
                  key={item.id}
                  onClick={() => setSelectedAssessment(item)}
                  style={{
                    padding: "0.75rem",
                    borderBottom: "1px solid var(--qf-border, #e2e8f0)",
                    cursor: "pointer",
                    background: selectedAssessment?.id === item.id ? "rgba(37, 99, 235, 0.08)" : "transparent",
                    borderRadius: "4px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <strong>Score: {item.score} / 1000</strong>
                    <span className={`qf-badge ${getCategoryBadgeClass(item.risk_category)}`}>
                      {item.risk_category.toUpperCase()}
                    </span>
                  </div>
                  <div className="qf-text-xs qf-text-muted" style={{ marginTop: "0.25rem" }}>
                    Threat: {item.quantum_threat_type}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Assessment Detail */}
          {selectedAssessment && (
            <div className="qf-card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h3>Assessment Detail</h3>
                <span className={`qf-badge ${getCategoryBadgeClass(selectedAssessment.risk_category)}`}>
                  {selectedAssessment.risk_category.toUpperCase()} ({selectedAssessment.score} / 1000)
                </span>
              </div>

              <div style={{ marginTop: "1rem", padding: "1rem", background: "var(--qf-bg-subtle, #f8fafc)", borderRadius: "6px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  {selectedAssessment.quantum_threat_type.includes("shor") ? (
                    <ShieldAlert size={20} color="#ef4444" />
                  ) : selectedAssessment.quantum_threat_type.includes("grover") ? (
                    <AlertTriangle size={20} color="#f59e0b" />
                  ) : (
                    <CheckCircle size={20} color="#10b981" />
                  )}
                  <strong>{selectedAssessment.quantum_threat_type.replace(/_/g, " ").toUpperCase()}</strong>
                </div>
                <p className="qf-text-sm" style={{ marginTop: "0.5rem" }}>
                  {selectedAssessment.threat_summary}
                </p>
              </div>

              {/* 8-Dimension Factor Breakdown Table */}
              <h4 style={{ marginTop: "1.5rem" }}>Methodology v1.0 Factor Contributions</h4>
              <table className="qf-table" style={{ marginTop: "0.5rem" }}>
                <thead>
                  <tr>
                    <th>Dim</th>
                    <th>Factor Title</th>
                    <th>Weight</th>
                    <th>Rating</th>
                    <th>Contribution</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedAssessment.factors.map((f) => (
                    <tr key={f.id}>
                      <td><strong>{f.dimension}</strong></td>
                      <td>{f.title}</td>
                      <td>{f.weight}</td>
                      <td>{f.rating} / 5</td>
                      <td><strong>+{f.contribution}</strong></td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Recommendations */}
              <h4 style={{ marginTop: "1.5rem" }}>Remediation Recommendations</h4>
              {selectedAssessment.recommendations.length === 0 ? (
                <p className="qf-text-muted qf-text-sm">No critical remediations required for this asset.</p>
              ) : (
                <div style={{ marginTop: "0.5rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                  {selectedAssessment.recommendations.map((r) => (
                    <div key={r.id} style={{ border: "1px solid var(--qf-border, #e2e8f0)", padding: "0.75rem", borderRadius: "6px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <strong>{r.title}</strong>
                        <span className="qf-badge qf-badge-warning">{r.priority.toUpperCase()}</span>
                      </div>
                      <p className="qf-text-sm" style={{ margin: "0.5rem 0" }}>{r.description}</p>
                      {r.validation_steps && r.validation_steps.length > 0 && (
                        <div className="qf-text-xs qf-text-muted">
                          <strong>Verification steps:</strong>
                          <ul style={{ margin: "0.25rem 0 0 1rem" }}>
                            {r.validation_steps.map((step, idx) => (
                              <li key={idx}>{step}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

