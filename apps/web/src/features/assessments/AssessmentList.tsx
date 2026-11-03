import React, { useCallback, useEffect, useState } from "react";
import {
  ShieldAlert,
  Search,
  Plus,
  RefreshCw,
  Clock,
  ArrowRight,
  RotateCcw,
  FileCheck,
} from "lucide-react";
import { AssessmentResponse, AssessmentStatus } from "../../types";
import { listAssessments, retryAssessment } from "../../services/api";
import { Badge } from "../../components/common/Badge";
import { Button } from "../../components/common/Button";
import { Card } from "../../components/common/Card";

interface AssessmentListProps {
  onSelectAssessment: (assessmentId: string, stage: string) => void;
  onNewAssessment: () => void;
}

export const AssessmentList: React.FC<AssessmentListProps> = ({
  onSelectAssessment,
  onNewAssessment,
}) => {
  const [assessments, setAssessments] = useState<AssessmentResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [retryingId, setRetryingId] = useState<string | null>(null);

  const fetchList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listAssessments({
        status: statusFilter === "all" ? undefined : statusFilter,
        limit: 50,
      });
      setAssessments(res.items || []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load assessments");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  const handleRetry = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setRetryingId(id);
    try {
      await retryAssessment(id);
      await fetchList();
    } catch (err: unknown) {
      alert(`Retry failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setRetryingId(null);
    }
  };

  const filteredAssessments = assessments.filter((a) => {
    const q = searchQuery.toLowerCase();
    const titleMatch = (a.title || "").toLowerCase().includes(q);
    const targetMatch = (a.target_snapshot?.hostname as string || "").toLowerCase().includes(q);
    return titleMatch || targetMatch;
  });

  const getStatusBadge = (status: AssessmentStatus) => {
    switch (status) {
      case "completed":
        return <Badge variant="low">Completed</Badge>;
      case "running":
        return <Badge variant="inferred">Running ({assessments.find((a) => a.status === "running")?.progress_percent || 0}%)</Badge>;
      case "queued":
        return <Badge variant="unknown">Queued</Badge>;
      case "failed":
        return <Badge variant="critical">Failed</Badge>;
      case "cancelled":
        return <Badge variant="unknown">Cancelled</Badge>;
      default:
        return <Badge variant="default">{status}</Badge>;
    }
  };

  const getQviBadge = (riskSummary: Record<string, unknown>) => {
    const score = Number(
      riskSummary?.max_asset_qvi ??
      riskSummary?.overall_score ??
      riskSummary?.qvi_score ??
      riskSummary?.max_qvi ??
      -1
    );
    if (score < 0) return <span style={{ color: "var(--text-muted)" }}>Pending</span>;
    if (score >= 800) return <Badge variant="critical">QVI {score}</Badge>;
    if (score >= 600) return <Badge variant="high">QVI {score}</Badge>;
    if (score >= 400) return <Badge variant="elevated">QVI {score}</Badge>;
    if (score >= 200) return <Badge variant="guarded">QVI {score}</Badge>;
    return <Badge variant="low">QVI {score}</Badge>;
  };

  return (
    <div className="qf-target-management">
      {/* Header */}
      <div className="qf-view-header">
        <div>
          <h2 style={{ fontFamily: "var(--font-serif)", fontSize: "1.65rem", margin: 0 }}>
            Enterprise Cryptographic Assessments
          </h2>
          <p className="qf-view-description">
            Centrally orchestrate multi-collector discovery, CBOM correlation, deterministic QVI evaluation,
            and cryptographically signed compliance reports.
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <Button variant="outline" size="sm" onClick={fetchList} isLoading={loading} icon={<RefreshCw size={14} />}>
            Refresh
          </Button>
          <Button variant="primary" size="sm" onClick={onNewAssessment} icon={<Plus size={15} />}>
            New Assessment
          </Button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="qf-filter-bar">
        <div className="qf-search-input-wrap">
          <Search className="qf-search-icon" size={16} />
          <input
            type="text"
            className="qf-search-input"
            placeholder="Search by assessment title or target hostname..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Status:</span>
          <select
            className="qf-filter-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All States</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="queued">Queued</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="qf-alert-box qf-alert-security">
          <div className="qf-alert-inner">
            <ShieldAlert className="qf-security-icon" size={18} />
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Table / List */}
      <Card style={{ padding: 0, overflow: "hidden" }}>
        <table className="qf-targets-table" style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ backgroundColor: "var(--bg-tertiary)", textAlign: "left", fontSize: "0.775rem" }}>
              <th style={{ padding: "0.75rem 1rem" }}>Assessment</th>
              <th style={{ padding: "0.75rem 1rem" }}>Target Scope</th>
              <th style={{ padding: "0.75rem 1rem" }}>Status / Stage</th>
              <th style={{ padding: "0.75rem 1rem" }}>Discovered Assets</th>
              <th style={{ padding: "0.75rem 1rem" }}>Quantum Risk (QVI)</th>
              <th style={{ padding: "0.75rem 1rem" }}>Created At</th>
              <th style={{ padding: "0.75rem 1rem", textAlign: "right" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && assessments.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: "center", padding: "3rem", color: "var(--text-muted)" }}>
                  <RefreshCw className="qf-spin" size={20} style={{ display: "inline", marginRight: "0.5rem" }} />
                  Loading assessments...
                </td>
              </tr>
            ) : filteredAssessments.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: "center", padding: "3rem" }}>
                  <div style={{ color: "var(--text-muted)", marginBottom: "1rem" }}>
                    No assessments match the current filter.
                  </div>
                  <Button variant="outline" size="sm" onClick={onNewAssessment}>
                    Launch New Assessment
                  </Button>
                </td>
              </tr>
            ) : (
              filteredAssessments.map((a) => {
                const targetHost = (a.target_snapshot?.hostname as string) || "General Scope";
                const totalAssets = Number(a.asset_counts?.total_assets ?? a.asset_counts?.assets_discovered ?? 0);
                return (
                  <tr
                    key={a.id}
                    style={{
                      borderBottom: "1px solid var(--border-light)",
                      cursor: "pointer",
                      transition: "background-color 0.15s",
                    }}
                    onClick={() => onSelectAssessment(a.id, a.progress_stage)}
                  >
                    <td style={{ padding: "1rem" }}>
                      <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{a.title}</div>
                      <div className="font-mono" style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                        {a.id.slice(0, 8)}...{a.id.slice(-4)}
                      </div>
                    </td>
                    <td style={{ padding: "1rem" }}>
                      <span className="font-mono" style={{ fontSize: "0.85rem", color: "var(--text-primary)" }}>
                        {targetHost}
                      </span>
                    </td>
                    <td style={{ padding: "1rem" }}>
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", alignItems: "flex-start" }}>
                        {getStatusBadge(a.status)}
                        <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                          {a.progress_stage}
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: "1rem", fontWeight: 600 }}>
                      {totalAssets} Primitives
                    </td>
                    <td style={{ padding: "1rem" }}>
                      {getQviBadge(a.risk_summary)}
                    </td>
                    <td style={{ padding: "1rem", fontSize: "0.8rem", color: "var(--text-muted)" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
                        <Clock size={13} />
                        <span>{new Date(a.created_at).toLocaleDateString()}</span>
                      </div>
                    </td>
                    <td style={{ padding: "1rem", textAlign: "right" }}>
                      <div style={{ display: "inline-flex", gap: "0.5rem" }}>
                        {a.status === "failed" && (
                          <Button
                            variant="danger"
                            size="sm"
                            isLoading={retryingId === a.id}
                            onClick={(e) => handleRetry(e, a.id)}
                            icon={<RotateCcw size={13} />}
                          >
                            Retry
                          </Button>
                        )}
                        {a.status === "completed" && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              onSelectAssessment(a.id, "COMPLETED");
                            }}
                            icon={<FileCheck size={13} />}
                          >
                            Reports
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onSelectAssessment(a.id, a.progress_stage)}
                          icon={<ArrowRight size={13} />}
                        >
                          View
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
};
