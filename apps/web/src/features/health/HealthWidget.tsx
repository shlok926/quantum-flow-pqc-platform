import React, { useEffect, useState, useCallback } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Database,
  Layers,
  Cpu,
  Clock,
} from "lucide-react";
import { fetchHealthLive, fetchHealthReady } from "../../services/api";
import { HealthLiveResponse, HealthReadyResponse } from "../../types";

export const HealthWidget: React.FC = () => {
  const [live, setLive] = useState<HealthLiveResponse | null>(null);
  const [ready, setReady] = useState<HealthReadyResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const checkHealth = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [liveData, readyData] = await Promise.all([
        fetchHealthLive(),
        fetchHealthReady(),
      ]);
      setLive(liveData);
      setReady(readyData);
      setLastChecked(new Date());
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to connect to backend control plane";
      setError(errorMessage);
      setLastChecked(new Date());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  const getSystemStatus = () => {
    if (error) {
      return {
        label: "Control Plane Offline",
        type: "error",
        icon: XCircle,
        desc: "Unable to reach FastAPI backend service. Verify server is running on configured API URL.",
      };
    }
    if (!ready) {
      return {
        label: "Checking System...",
        type: "pending",
        icon: RefreshCw,
        desc: "Probing liveness and dependency status.",
      };
    }
    if (ready.status === "ready") {
      return {
        label: "All Systems Operational",
        type: "healthy",
        icon: CheckCircle2,
        desc: "API, PostgreSQL database, and Redis cache are fully connected.",
      };
    }
    return {
      label: "System Degraded",
      type: "degraded",
      icon: AlertTriangle,
      desc: "API is live, but one or more backing dependencies are currently unavailable.",
    };
  };

  const sysStatus = getSystemStatus();
  const StatusIcon = sysStatus.icon;

  return (
    <section className="qf-health-widget" aria-label="System Health Diagnostics">
      <div className={`qf-banner qf-banner-${sysStatus.type}`}>
        <div className="qf-banner-left">
          <StatusIcon
            className={`qf-status-icon ${loading ? "qf-spin" : ""}`}
            size={24}
            data-testid="status-icon"
          />
          <div>
            <h3 className="qf-banner-title">{sysStatus.label}</h3>
            <p className="qf-banner-desc">{sysStatus.desc}</p>
          </div>
        </div>
        <div className="qf-banner-actions">
          <button
            type="button"
            className="qf-btn-refresh"
            onClick={checkHealth}
            disabled={loading}
            aria-label="Refresh health status"
          >
            <RefreshCw size={14} className={loading ? "qf-spin" : ""} />
            <span>{loading ? "Checking..." : "Refresh Status"}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="qf-alert-box qf-alert-error" role="alert">
          <p>
            <strong>Connection Error:</strong> {error}
          </p>
          <small>
            Verify that <code>services/api</code> is running at the configured endpoint
            or launch containers using <code>docker compose up -d</code>.
          </small>
        </div>
      )}

      <div className="qf-metrics-grid">
        {/* API Subsystem */}
        <div className="qf-metric-card" data-testid="metric-api">
          <div className="qf-card-header">
            <Cpu size={18} className="qf-card-icon" />
            <span className="qf-card-title">FastAPI Control Plane</span>
            <span
              className={`qf-status-badge ${
                live?.status === "healthy" || live?.status === "alive" ? "badge-healthy" : "badge-offline"
              }`}
            >
              {live?.status === "healthy" || live?.status === "alive" ? "Healthy" : "Offline"}
            </span>
          </div>
          <div className="qf-card-body">
            <div className="qf-prop-row">
              <span className="qf-prop-name">Version:</span>
              <span className="qf-prop-value">{live?.version ?? "N/A"}</span>
            </div>
            <div className="qf-prop-row">
              <span className="qf-prop-name">Service:</span>
              <span className="qf-prop-value">{live?.service ?? "N/A"}</span>
            </div>
            <div className="qf-prop-row">
              <span className="qf-prop-name">Probe Route:</span>
              <span className="qf-prop-value font-mono">/health/live</span>
            </div>
          </div>
        </div>

        {/* PostgreSQL Database Subsystem */}
        <div className="qf-metric-card" data-testid="metric-database">
          <div className="qf-card-header">
            <Database size={18} className="qf-card-icon" />
            <span className="qf-card-title">PostgreSQL 16 (AsyncPG)</span>
            <span
              className={`qf-status-badge ${
                ready?.dependencies?.database?.status === "connected"
                  ? "badge-healthy"
                  : ready
                  ? "badge-degraded"
                  : "badge-offline"
              }`}
            >
              {ready?.dependencies?.database?.status === "connected"
                ? "Connected"
                : ready
                ? "Degraded"
                : "Unknown"}
            </span>
          </div>
          <div className="qf-card-body">
            <div className="qf-prop-row">
              <span className="qf-prop-name">Driver:</span>
              <span className="qf-prop-value font-mono">postgresql+asyncpg</span>
            </div>
            <div className="qf-prop-row">
              <span className="qf-prop-name">Detail:</span>
              <span className="qf-prop-value">
                {ready?.dependencies?.database?.detail ?? "No signal received"}
              </span>
            </div>
            <div className="qf-prop-row">
              <span className="qf-prop-name">ORM / Migrations:</span>
              <span className="qf-prop-value font-mono">SQLAlchemy 2.x / Alembic</span>
            </div>
          </div>
        </div>

        {/* Redis Cache Subsystem */}
        <div className="qf-metric-card" data-testid="metric-redis">
          <div className="qf-card-header">
            <Layers size={18} className="qf-card-icon" />
            <span className="qf-card-title">Redis 7 (Async Redis)</span>
            <span
              className={`qf-status-badge ${
                ready?.dependencies?.redis?.status === "connected"
                  ? "badge-healthy"
                  : ready
                  ? "badge-degraded"
                  : "badge-offline"
              }`}
            >
              {ready?.dependencies?.redis?.status === "connected"
                ? "Connected"
                : ready
                ? "Degraded"
                : "Unknown"}
            </span>
          </div>
          <div className="qf-card-body">
            <div className="qf-prop-row">
              <span className="qf-prop-name">Role:</span>
              <span className="qf-prop-value">Task Queue / Cache / Broker</span>
            </div>
            <div className="qf-prop-row">
              <span className="qf-prop-name">Detail:</span>
              <span className="qf-prop-value">
                {ready?.dependencies?.redis?.detail ?? "No signal received"}
              </span>
            </div>
            <div className="qf-prop-row">
              <span className="qf-prop-name">Client:</span>
              <span className="qf-prop-value font-mono">redis.asyncio</span>
            </div>
          </div>
        </div>
      </div>

      <div className="qf-timestamp-bar">
        <Clock size={12} />
        <span>
          Last Telemetry Check:{" "}
          {lastChecked ? lastChecked.toLocaleTimeString() : "Never"}
        </span>
        <span className="qf-divider">&bull;</span>
        <span>Environment Target: Local Development (127.0.0.1:8000)</span>
      </div>
    </section>
  );
};

