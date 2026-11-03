import React, { useEffect, useState, useCallback, useRef } from "react";
import {
  Activity,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Ban,
  ArrowRight,
  Server,
  FileCheck,
} from "lucide-react";
import { AssessmentResponse, AssessmentJobSummary } from "../../types";
import { getAssessment, listAssessmentJobs, cancelAssessment, retryAssessment } from "../../services/api";
import { Button } from "../../components/common/Button";
import { Card } from "../../components/common/Card";
import { Badge } from "../../components/common/Badge";

interface AssessmentProgressProps {
  assessmentId: string;
  onViewResults: (id: string) => void;
  onBackToList: () => void;
}

const STAGES = [
  { key: "QUEUED", label: "1. Queued" },
  { key: "DISCOVERY", label: "2. Discovery" },
  { key: "CBOM_INGESTION", label: "3. CBOM Ingestion" },
  { key: "RISK_ASSESSMENT", label: "4. Risk Scoring" },
  { key: "REPORT_FROZEN", label: "5. Report Seal" },
  { key: "COMPLETED", label: "6. Completed" },
];

export const AssessmentProgress: React.FC<AssessmentProgressProps> = ({
  assessmentId,
  onViewResults,
  onBackToList,
}) => {
  const [assessment, setAssessment] = useState<AssessmentResponse | null>(null);
  const [jobs, setJobs] = useState<AssessmentJobSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState<boolean>(false);
  const [retrying, setRetrying] = useState<boolean>(false);

  // Visibility-aware polling
  const isTerminalRef = useRef<boolean>(false);

  const pollData = useCallback(async () => {
    try {
      const [aData, jData] = await Promise.all([
        getAssessment(assessmentId),
        listAssessmentJobs(assessmentId).catch(() => ({ total_jobs: 0, jobs: [] })),
      ]);

      setAssessment(aData);
      setJobs(jData.jobs || []);

      if (["completed", "failed", "cancelled"].includes(aData.status)) {
        isTerminalRef.current = true;
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load assessment status");
    } finally {
      setLoading(false);
    }
  }, [assessmentId]);

  useEffect(() => {
    isTerminalRef.current = false;
    pollData();

    const interval = window.setInterval(() => {
      // Pause polling if user switched away from the browser tab or status is terminal
      if (document.visibilityState === "hidden" || isTerminalRef.current) {
        return;
      }
      pollData();
    }, 2000);

    return () => clearInterval(interval);
  }, [pollData]);

  const handleCancel = async () => {
    if (!window.confirm("Are you sure you want to cancel this in-progress assessment?")) return;
    setCancelling(true);
    try {
      await cancelAssessment(assessmentId, { reason: "User cancelled from web console" });
      await pollData();
    } catch (err: unknown) {
      alert(`Cancel failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setCancelling(false);
    }
  };

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await retryAssessment(assessmentId);
      isTerminalRef.current = false;
      await pollData();
    } catch (err: unknown) {
      alert(`Retry failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setRetrying(false);
    }
  };

  const getStageIndex = (stageKey: string): number => {
    const idx = STAGES.findIndex((s) => s.key === stageKey);
    return idx === -1 ? 0 : idx;
  };

  if (loading && !assessment) {
    return (
      <Card style={{ textAlign: "center", padding: "4rem" }}>
        <Activity className="qf-spin" size={28} style={{ color: "var(--olive-primary)", margin: "0 auto 1rem auto" }} />
        <h3 style={{ fontFamily: "var(--font-serif)" }}>Connecting to Assessment Control Plane...</h3>
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
          Retrieving real-time discovery job states for assessment <span className="font-mono">{assessmentId}</span>
        </p>
      </Card>
    );
  }

  if (error || !assessment) {
    return (
      <Card style={{ textAlign: "center", padding: "3rem" }}>
        <AlertTriangle size={32} style={{ color: "var(--rose-primary)", margin: "0 auto 1rem auto" }} />
        <h3 style={{ fontFamily: "var(--font-serif)" }}>Unable to Track Assessment</h3>
        <p style={{ color: "var(--text-secondary)", marginBottom: "1.5rem" }}>{error || "Assessment not found"}</p>
        <Button variant="secondary" onClick={onBackToList}>
          Return to Assessments
        </Button>
      </Card>
    );
  }

  const currentStageIdx = getStageIndex(assessment.progress_stage);
  const isCompleted = assessment.status === "completed";
  const isFailed = assessment.status === "failed";
  const isCancelled = assessment.status === "cancelled";

  return (
    <div style={{ maxWidth: "1000px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header Bar */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.25rem" }}>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
              Assessment Monitor
            </span>
            <span className="font-mono" style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              {assessment.id}
            </span>
          </div>
          <h2 style={{ fontFamily: "var(--font-serif)", fontSize: "1.65rem", margin: 0 }}>
            {assessment.title}
          </h2>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginTop: "0.4rem" }}>
            <span className="font-mono" style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
              Target: {(assessment.target_snapshot?.hostname as string) || "General Scope"}
            </span>
            <span style={{ color: "var(--border-color)" }}>•</span>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
              Started: {assessment.started_at ? new Date(assessment.started_at).toLocaleTimeString() : "Pending"}
            </span>
          </div>
        </div>

        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          {isCompleted && (
            <Button
              variant="primary"
              onClick={() => onViewResults(assessment.id)}
              icon={<FileCheck size={16} />}
            >
              View Results & Reports
            </Button>
          )}

          {isFailed && (
            <Button
              variant="primary"
              isLoading={retrying}
              onClick={handleRetry}
              icon={<RotateCcw size={15} />}
            >
              Retry Execution
            </Button>
          )}

          {!isCompleted && !isFailed && !isCancelled && (
            <Button
              variant="danger"
              size="sm"
              isLoading={cancelling}
              onClick={handleCancel}
              icon={<Ban size={14} />}
            >
              Cancel Scan
            </Button>
          )}

          <Button variant="secondary" size="sm" onClick={onBackToList}>
            All Assessments
          </Button>
        </div>
      </div>

      {/* Primary Progress Card */}
      <Card>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
            <span style={{ fontWeight: 600, fontSize: "1rem" }}>Execution Stage:</span>
            <Badge variant={isCompleted ? "low" : isFailed ? "critical" : "inferred"}>
              {assessment.status.toUpperCase()} — {assessment.progress_stage}
            </Badge>
          </div>
          <span style={{ fontSize: "1.2rem", fontWeight: 700, fontFamily: "var(--font-mono)" }}>
            {assessment.progress_percent}%
          </span>
        </div>

        {/* Progress Bar */}
        <div className="qf-progress-track">
          <div
            className="qf-progress-fill"
            style={{
              width: `${assessment.progress_percent}%`,
              backgroundColor: isFailed ? "var(--rose-primary)" : "var(--olive-primary)",
            }}
          />
        </div>

        {/* Stages Stepper */}
        <div className="qf-stages-stepper">
          {STAGES.map((s, idx) => {
            const isStageCompleted = isCompleted || idx < currentStageIdx;
            const isStageActive = idx === currentStageIdx && !isCompleted && !isFailed;
            return (
              <div
                key={s.key}
                className={`qf-stage-chip ${isStageCompleted ? "completed" : isStageActive ? "active" : ""}`}
              >
                {s.label}
              </div>
            );
          })}
        </div>

        {/* Error message banner if failed */}
        {assessment.error_summary && (
          <div
            style={{
              marginTop: "1.25rem",
              backgroundColor: "#FEF2F2",
              border: "1px solid #FECACA",
              borderRadius: "6px",
              padding: "0.85rem 1rem",
              color: "var(--rose-primary)",
              fontSize: "0.85rem",
            }}
          >
            <strong>Failure Diagnostics:</strong> {assessment.error_summary}
          </div>
        )}
      </Card>

      {/* Child Discovery Jobs Table */}
      <Card style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "1rem 1.25rem", borderBottom: "1px solid var(--border-light)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Server size={18} style={{ color: "var(--olive-primary)" }} />
          <h3 style={{ fontFamily: "var(--font-serif)", fontSize: "1.05rem", margin: 0 }}>
            Active Discovery Jobs & Worker Telemetry ({jobs.length})
          </h3>
        </div>

        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
          <thead>
            <tr style={{ backgroundColor: "var(--bg-tertiary)", textAlign: "left", fontSize: "0.75rem", textTransform: "uppercase" }}>
              <th style={{ padding: "0.6rem 1rem" }}>Job Type</th>
              <th style={{ padding: "0.6rem 1rem" }}>Status</th>
              <th style={{ padding: "0.6rem 1rem" }}>Progress</th>
              <th style={{ padding: "0.6rem 1rem" }}>Worker ID</th>
              <th style={{ padding: "0.6rem 1rem" }}>Retries</th>
              <th style={{ padding: "0.6rem 1rem" }}>Results</th>
            </tr>
          </thead>
          <tbody>
            {jobs.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", padding: "2rem", color: "var(--text-muted)" }}>
                  No child jobs dispatched yet. Enqueueing discovery workers...
                </td>
              </tr>
            ) : (
              jobs.map((j) => (
                <tr key={j.id} style={{ borderBottom: "1px solid var(--border-light)" }}>
                  <td style={{ padding: "0.75rem 1rem", fontWeight: 600 }}>
                    <span className="font-mono">{j.job_type}</span>
                  </td>
                  <td style={{ padding: "0.75rem 1rem" }}>
                    <Badge variant={j.status === "completed" ? "low" : j.status === "failed" ? "critical" : "inferred"}>
                      {j.status}
                    </Badge>
                  </td>
                  <td style={{ padding: "0.75rem 1rem" }}>
                    {j.progress_percent}%
                  </td>
                  <td style={{ padding: "0.75rem 1rem", fontSize: "0.75rem" }} className="font-mono">
                    {j.worker_id || "Unassigned"}
                  </td>
                  <td style={{ padding: "0.75rem 1rem" }}>
                    {j.retry_count}
                  </td>
                  <td style={{ padding: "0.75rem 1rem", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                    {j.result_summary ? `${Object.keys(j.result_summary).length} metrics` : "-"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </Card>

      {/* Transition CTA if completed */}
      {isCompleted && (
        <Card style={{ backgroundColor: "var(--olive-light)", border: "1px solid var(--olive-border)", textAlign: "center", padding: "1.75rem" }}>
          <CheckCircle2 size={32} style={{ color: "var(--olive-primary)", margin: "0 auto 0.75rem auto" }} />
          <h3 style={{ fontFamily: "var(--font-serif)", fontSize: "1.25rem", color: "var(--olive-primary)", margin: "0 0 0.5rem 0" }}>
            Cryptographic Assessment Complete
          </h3>
          <p style={{ fontSize: "0.9rem", color: "var(--text-secondary)", maxWidth: "600px", margin: "0 auto 1.25rem auto" }}>
            Discovered cryptographic primitives have been correlated, quantum risk scores calculated,
            and the immutable report snapshot has been cryptographically sealed with RFC 8785 SHA-256 integrity.
          </p>
          <Button
            variant="primary"
            size="lg"
            onClick={() => onViewResults(assessment.id)}
            icon={<ArrowRight size={16} />}
          >
            Explore Assessment Findings & Reports
          </Button>
        </Card>
      )}
    </div>
  );
};

