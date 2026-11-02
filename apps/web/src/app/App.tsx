import React, { useState } from "react";
import { Header } from "../components/Header";
import { Sidebar } from "../components/Sidebar";
import { Footer } from "../components/Footer";
import { DashboardOverview } from "../features/dashboard/DashboardOverview";
import { TargetManagement } from "../features/targets/TargetManagement";
import { AssetExplorer } from "../features/cbom/AssetExplorer";
import { RiskDashboard } from "../features/risk/RiskDashboard";
import { SourceUpload } from "../features/discovery/SourceUpload";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>("diagnostics");

  return (
    <div className="qf-app-layout">
      <Header />
      <div className="qf-body-layout">
        <Sidebar activeTab={activeTab} onSelectTab={setActiveTab} />
        <main className="qf-main-content" role="main">
          {activeTab === "diagnostics" && <DashboardOverview />}
          {activeTab === "discover" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
              <TargetManagement />
              <SourceUpload />
            </div>
          )}
          {activeTab === "inventory" && <AssetExplorer />}
          {activeTab === "prioritise" && <RiskDashboard />}
          {activeTab !== "diagnostics" &&
            activeTab !== "discover" &&
            activeTab !== "inventory" &&
            activeTab !== "prioritise" && (
              <div className="qf-placeholder-view">
                <h2>Module Scheduled for Upcoming Sprint</h2>
                <p>
                  The <strong>{activeTab.toUpperCase()}</strong> workflow component is
                  currently in the design phase per the Implementation Roadmap.
                </p>
                <button
                  type="button"
                  className="qf-btn-primary"
                  onClick={() => setActiveTab("diagnostics")}
                >
                  Return to System Diagnostics
                </button>
              </div>
            )}
        </main>
      </div>
      <Footer />
    </div>
  );
};

export default App;

