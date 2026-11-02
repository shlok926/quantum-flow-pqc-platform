import React, { useState } from "react";
import { Header } from "../components/Header";
import { Sidebar } from "../components/Sidebar";
import { Footer } from "../components/Footer";
import { DashboardOverview } from "../features/dashboard/DashboardOverview";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>("diagnostics");

  return (
    <div className="qf-app-layout">
      <Header />
      <div className="qf-body-layout">
        <Sidebar activeTab={activeTab} onSelectTab={setActiveTab} />
        <main className="qf-main-content" role="main">
          {activeTab === "diagnostics" && <DashboardOverview />}
          {activeTab !== "diagnostics" && (
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

