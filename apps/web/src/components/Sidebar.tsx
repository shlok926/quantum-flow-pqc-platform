import React from "react";
import {
  Radar,
  Layers,
  Flame,
  GitBranch,
  KeyRound,
  ShieldCheck,
  Activity,
  Server,
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
    { id: "discover", label: "1. Discover", icon: Radar, status: "Sprint 1" },
    { id: "inventory", label: "2. Inventory (CBOM)", icon: Layers, status: "Sprint 1" },
    { id: "prioritise", label: "3. Prioritise (QVI)", icon: Flame, status: "Sprint 2" },
    { id: "plan", label: "4. Plan & Roadmap", icon: GitBranch, status: "Sprint 3" },
    { id: "migrate", label: "5. Migrate (PQC)", icon: KeyRound, status: "Sprint 4" },
    { id: "assure", label: "6. Assure & Audit", icon: ShieldCheck, status: "Sprint 5" },
  ];

  return (
    <nav className="qf-sidebar" aria-label="Workflow Navigation">
      <div className="qf-sidebar-section">
        <div className="qf-sidebar-heading">Foundation & Diagnostics</div>
        <ul className="qf-nav-list">
          <li>
            <button
              type="button"
              className={`qf-nav-item ${activeTab === "diagnostics" ? "active" : ""}`}
              onClick={() => onSelectTab && onSelectTab("diagnostics")}
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
              onClick={() => onSelectTab && onSelectTab("architecture")}
            >
              <Server size={18} />
              <span>Architecture Map</span>
            </button>
          </li>
        </ul>
      </div>

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
                  onClick={() => onSelectTab && onSelectTab(stage.id)}
                >
                  <Icon size={18} />
                  <span>{stage.label}</span>
                  <span className="qf-nav-tag qf-nav-tag-planned">{stage.status}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </nav>
  );
};
