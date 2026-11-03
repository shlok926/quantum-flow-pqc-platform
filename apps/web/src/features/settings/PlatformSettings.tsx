import React from "react";
import {
  HardDrive,
  Cpu,
  Lock,
  Database,
} from "lucide-react";
import { Card, CardHeader } from "../../components/common/Card";
import { Badge } from "../../components/common/Badge";

export const PlatformSettings: React.FC = () => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
      {/* Page Header */}
      <div className="qf-view-header">
        <div>
          <h2 style={{ fontFamily: "var(--font-serif)", fontSize: "1.65rem", margin: 0 }}>
            Platform Settings & Governance
          </h2>
          <p className="qf-view-description">
            Tenant quota allocations, process isolation policies, upload concurrency limits,
            and cryptographic standards compliance configuration.
          </p>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.5rem" }}>
        {/* Storage & Staging Quotas (Sprint 3 Phase 2) */}
        <Card>
          <CardHeader
            title="Tenant Staging & Storage Quotas"
            subtitle="Phase 2 atomic reservation and quota tracking limits"
            icon={<HardDrive size={20} />}
          />

          <div style={{ display: "flex", flexDirection: "column", gap: "1rem", marginTop: "1rem" }}>
            <div style={{ padding: "0.85rem", backgroundColor: "var(--bg-tertiary)", borderRadius: "6px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "0.825rem", color: "var(--text-secondary)" }}>Tenant Storage Quota</span>
                <span className="font-mono" style={{ fontWeight: 600 }}>100.0 MB</span>
              </div>
              <div className="qf-progress-track" style={{ margin: "0.5rem 0 0.25rem 0", height: "6px" }}>
                <div className="qf-progress-fill" style={{ width: "12%" }}></div>
              </div>
              <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                Enforced via atomic reservations before staging upload stream
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", padding: "0.5rem 0", borderBottom: "1px solid var(--border-light)" }}>
              <span style={{ fontSize: "0.825rem", color: "var(--text-secondary)" }}>Max Concurrent Uploads / Tenant</span>
              <span className="font-mono" style={{ fontWeight: 600 }}>3 slots (Advisory Locked)</span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", padding: "0.5rem 0", borderBottom: "1px solid var(--border-light)" }}>
              <span style={{ fontSize: "0.825rem", color: "var(--text-secondary)" }}>Cluster Global Concurrency</span>
              <span className="font-mono" style={{ fontWeight: 600 }}>10 slots</span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", padding: "0.5rem 0" }}>
              <span style={{ fontSize: "0.825rem", color: "var(--text-secondary)" }}>Upload Token Validity Window</span>
              <span className="font-mono" style={{ fontWeight: 600 }}>15 minutes (HMAC-SHA256)</span>
            </div>
          </div>
        </Card>

        {/* Process Containment & OS Isolation */}
        <Card>
          <CardHeader
            title="Worker & Scanner Process Containment"
            subtitle="Job Objects (Windows) and Process Groups (POSIX)"
            icon={<Cpu size={20} />}
          />

          <div style={{ display: "flex", flexDirection: "column", gap: "1rem", marginTop: "1rem" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>Job Object Containment</span>
              <Badge variant="low">Active</Badge>
            </div>
            <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", margin: 0, lineHeight: 1.45 }}>
              All scanner child processes are launched in a suspended state, assigned to a Windows Job Object
              without breakaway permissions, and resumed under <code>JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE</code>.
            </p>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: "0.5rem", borderTop: "1px solid var(--border-light)" }}>
              <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>SSRF Protection</span>
              <Badge variant="low">Pinned IP Enforced</Badge>
            </div>
            <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", margin: 0, lineHeight: 1.45 }}>
              Target DNS resolution verifies private IP exclusions (RFC 1918, RFC 3927, loopback) and binds directly
              to validated IP address before socket connect.
            </p>
          </div>
        </Card>

        {/* Cryptographic Standards */}
        <Card>
          <CardHeader
            title="Cryptographic Standards & Methodology"
            subtitle="Configured risk engine formulas and report formats"
            icon={<Lock size={20} />}
          />

          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginTop: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "0.825rem", color: "var(--text-secondary)" }}>Risk Methodology</span>
              <Badge variant="inferred">Methodology v1.0 (7 Weighted Dims)</Badge>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "0.825rem", color: "var(--text-secondary)" }}>Report Seal Canonicalization</span>
              <span className="font-mono" style={{ fontSize: "0.8rem", fontWeight: 600 }}>RFC 8785 JSON + SHA-256</span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "0.825rem", color: "var(--text-secondary)" }}>CBOM Export Standard</span>
              <span className="font-mono" style={{ fontSize: "0.8rem", fontWeight: 600 }}>CycloneDX 1.6 Cryptography</span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "0.825rem", color: "var(--text-secondary)" }}>CSV Export Hardening</span>
              <span className="font-mono" style={{ fontSize: "0.8rem", fontWeight: 600 }}>RFC 4180 CRLF + CWE-1236 Neutralized</span>
            </div>
          </div>
        </Card>

        {/* Database & Advisory Locking */}
        <Card>
          <CardHeader
            title="Database Infrastructure & Concurrency"
            subtitle="Advisory locking and transactional integrity"
            icon={<Database size={20} />}
          />

          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginTop: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "0.825rem", color: "var(--text-secondary)" }}>PostgreSQL Advisory Locks</span>
              <span className="font-mono" style={{ fontSize: "0.8rem", fontWeight: 600 }}>64-bit Signed Key Space</span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "0.825rem", color: "var(--text-secondary)" }}>Lock Verification Types</span>
              <span className="font-mono" style={{ fontSize: "0.8rem", fontWeight: 600 }}>classid / objid CAST(:val AS oid)</span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "0.825rem", color: "var(--text-secondary)" }}>Workspace Cleanup Verification</span>
              <span className="font-mono" style={{ fontSize: "0.8rem", fontWeight: 600 }}>Zero Process Confirmation</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};
