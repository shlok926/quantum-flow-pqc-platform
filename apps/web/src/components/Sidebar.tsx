import React from "react";
import {
  Activity,
  Server,
  Radar,
  Layers,
  Flame,
  GitBranch,
  ShieldAlert,
  PlusCircle,
  Settings,
} from "lucide-react";

interface SidebarProps {
  activeTab?: string;
  onSelectTab?: (tab: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab = "diagnostics",
  onSelectTab,
}) => {
  const workflowStages = [
    { id: "assessments", label: "Assessments", icon: ShieldAlert, badge: "Enterprise" },
    { id: "assessments-new", label: "New Assessment", icon: PlusCircle },
    { id: "discover", label: "1. Discover", icon: Radar, status: "Active" },
    { id: "inventory", label: "2. Inventory (CBOM)", icon: Layers, status: "Active" },
    { id: "prioritise", label: "3. Prioritise (QVI)", icon: Flame, status: "Active" },
    { id: "plan", label: "4. Plan & Roadmap", icon: GitBranch, status: "Planned" },
  ];

  const handleSelect = (id: string) => {
    if (onSelectTab) {
      onSelectTab(id);
    }
  };

  return (
    <nav className="qf-sidebar" aria-label="Workflow Navigation">
      {/* Foundation & Diagnostics */}
      <div className="qf-sidebar-section">
        <div className="qf-sidebar-heading">Foundation & Diagnostics</div>
        <ul className="qf-nav-list">
          <li>
            <button
              type="button"
              className={`qf-nav-item ${activeTab === "diagnostics" ? "active" : ""}`}
              onClick={() => handleSelect("diagnostics")}
              style={{
                backgroundColor: activeTab === "diagnostics" ? "var(--olive-light)" : "transparent",
                color: activeTab === "diagnostics" ? "var(--olive-primary)" : "var(--text-secondary)",
                fontWeight: activeTab === "diagnostics" ? 600 : 500,
              }}
            >
              <Activity size={18} />
              <span>Platform Health</span>
              <span className="qf-nav-tag qf-nav-tag-live">Active</span>
            </button>
          </li>
          <li>
            <button
              type="button"
              className={`qf-nav-item ${activeTab === "architecture" ? "active" : ""}`}
              onClick={() => handleSelect("architecture")}
              style={{
                backgroundColor: activeTab === "architecture" ? "var(--olive-light)" : "transparent",
                color: activeTab === "architecture" ? "var(--olive-primary)" : "var(--text-secondary)",
                fontWeight: activeTab === "architecture" ? 600 : 500,
              }}
            >
              <Server size={18} />
              <span>Architecture Map</span>
            </button>
          </li>
        </ul>
      </div>

      {/* PQC Lifecycle Workflow */}
      <div className="qf-sidebar-section">
        <div className="qf-sidebar-heading">PQC Lifecycle Workflow</div>
        <ul className="qf-nav-list">
          {workflowStages.map((stage) => {
            const Icon = stage.icon;
            const isActive = activeTab === stage.id;
            return (
              <li key={stage.id}>
                <button
                  type="button"
                  className={`qf-nav-item ${isActive ? "active" : ""}`}
                  onClick={() => handleSelect(stage.id)}
                  style={{
                    backgroundColor: isActive ? "var(--olive-light)" : "transparent",
                    color: isActive ? "var(--olive-primary)" : "var(--text-secondary)",
                    fontWeight: isActive ? 600 : 500,
                  }}
                >
                  <Icon size={18} style={{ color: isActive ? "var(--olive-primary)" : "inherit" }} />
                  <span>{stage.label}</span>
                  {stage.badge ? (
                    <span
                      style={{
                        marginLeft: "auto",
                        fontSize: "0.65rem",
                        padding: "0.15rem 0.4rem",
                        borderRadius: "4px",
                        backgroundColor: "var(--olive-primary)",
                        color: "#FFFFFF",
                        fontWeight: 700,
                      }}
                    >
                      {stage.badge}
                    </span>
                  ) : (
                    stage.status && (
                      <span
                        className={`qf-nav-tag ${
                          stage.status === "Active" ? "qf-nav-tag-live" : "qf-nav-tag-planned"
                        }`}
                      >
                        {stage.status}
                      </span>
                    )
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      {/* Administration & Governance */}
      <div className="qf-sidebar-section">
        <div className="qf-sidebar-heading">Governance & Policy</div>
        <ul className="qf-nav-list">
          <li>
            <button
              type="button"
              className={`qf-nav-item ${activeTab === "settings" ? "active" : ""}`}
              onClick={() => handleSelect("settings")}
              style={{
                backgroundColor: activeTab === "settings" ? "var(--olive-light)" : "transparent",
                color: activeTab === "settings" ? "var(--olive-primary)" : "var(--text-secondary)",
                fontWeight: activeTab === "settings" ? 600 : 500,
              }}
            >
              <Settings size={18} />
              <span>Platform Settings</span>
            </button>
          </li>
        </ul>
      </div>
    </nav>
  );
};
