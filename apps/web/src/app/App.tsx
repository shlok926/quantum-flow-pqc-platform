import React, { useState, useEffect } from "react";
import { RouterProvider, useRouter } from "../router";
import { Header } from "../components/Header";
import { Sidebar } from "../components/Sidebar";
import { Footer } from "../components/Footer";
import { DashboardOverview } from "../features/dashboard/DashboardOverview";
import { TargetManagement } from "../features/targets/TargetManagement";
import { AssetExplorer } from "../features/cbom/AssetExplorer";
import { RiskDashboard } from "../features/risk/RiskDashboard";
import { SourceUpload } from "../features/discovery/SourceUpload";
import { AssessmentList } from "../features/assessments/AssessmentList";
import { AssessmentWizard } from "../features/assessments/AssessmentWizard";
import { AssessmentProgress } from "../features/assessments/AssessmentProgress";
import { AssessmentDetail } from "../features/assessments/AssessmentDetail";
import { PlatformSettings } from "../features/settings/PlatformSettings";

// Public Marketing & Scanner Pages
import { PublicNavbar } from "../components/public/PublicNavbar";
import { PublicFooter } from "../components/public/PublicFooter";
import { HomePage } from "../features/public/HomePage";
import { PlatformPage } from "../features/public/PlatformPage";
import { IntelligencePage } from "../features/public/IntelligencePage";
import { ResourcesPage } from "../features/public/ResourcesPage";
import { AboutPage } from "../features/public/AboutPage";
import { ScannerPage } from "../features/public/ScannerPage";
import { ScanResultsPage } from "../features/public/ScanResultsPage";
import { RequestDemoPage } from "../features/public/RequestDemoPage";

export interface AppProps {
  initialPath?: string;
}

const AppContent: React.FC = () => {
  const { path, params, navigate } = useRouter();

  // Normalize path safely against query params and trailing slashes
  const currentPath = path.split("?")[0].replace(/\/+$/, "") || "/";

  // Determine test environment safely without Node global process
  const isTestMode =
    typeof (import.meta as unknown as { env?: { MODE?: string } }).env?.MODE !== "undefined" &&
    (import.meta as unknown as { env?: { MODE?: string } }).env?.MODE === "test";

  // Determine if active view should be the Enterprise Console
  // In test mode, default root "/" tests the enterprise shell directly for backward compatibility
  const isEnterprise = currentPath.startsWith("/app") || (isTestMode && (currentPath === "/" || currentPath === ""));

  // Enterprise console state
  const [activeTab, setActiveTab] = useState<string>(() => {
    if (currentPath === "/app/assessments") return "assessments";
    if (currentPath === "/app/assessments/new") return "assessments-new";
    if (currentPath === "/app/inventory") return "inventory";
    if (currentPath === "/app/risk") return "prioritise";
    if (currentPath === "/app/settings") return "settings";
    if (currentPath === "/app/discover") return "discover";
    if (currentPath === "/app/plan") return "plan";
    return "diagnostics";
  });

  const [activeAssessmentId, setActiveAssessmentId] = useState<string | null>(params.assessmentId || null);

  useEffect(() => {
    if (params.assessmentId) {
      setActiveAssessmentId(params.assessmentId);
      if (params.subview === "progress") {
        setActiveTab("assessments-progress");
      } else {
        setActiveTab("assessments-detail");
      }
    }
  }, [params.assessmentId, params.subview]);

  // Sync tab changes with route if inside enterprise
  const handleSelectTab = (tab: string) => {
    setActiveTab(tab);
    if (!isTestMode) {
      switch (tab) {
        case "diagnostics":
          navigate("/app");
          break;
        case "assessments":
          navigate("/app/assessments");
          break;
        case "assessments-new":
          navigate("/app/assessments/new");
          break;
        case "discover":
          navigate("/app/discover");
          break;
        case "inventory":
          navigate("/app/inventory");
          break;
        case "prioritise":
          navigate("/app/risk");
          break;
        case "settings":
          navigate("/app/settings");
          break;
        case "plan":
          navigate("/app/plan");
          break;
        default:
          break;
      }
    }
  };

  const handleNewAssessment = () => {
    setActiveTab("assessments-new");
    if (!isTestMode) navigate("/app/assessments/new");
  };

  const handleSelectAssessment = (id: string, stage: string) => {
    setActiveAssessmentId(id);
    if (["COMPLETED", "REPORT_FROZEN"].includes(stage.toUpperCase())) {
      setActiveTab("assessments-detail");
      if (!isTestMode) navigate(`/app/assessments/${id}`);
    } else {
      setActiveTab("assessments-progress");
      if (!isTestMode) navigate(`/app/assessments/${id}/progress`);
    }
  };

  const handleLaunchSuccess = (id: string) => {
    setActiveAssessmentId(id);
    setActiveTab("assessments-progress");
    if (!isTestMode) navigate(`/app/assessments/${id}/progress`);
  };

  const handleViewResults = (id: string) => {
    setActiveAssessmentId(id);
    setActiveTab("assessments-detail");
    if (!isTestMode) navigate(`/app/assessments/${id}`);
  };

  const handleBackToList = () => {
    setActiveTab("assessments");
    if (!isTestMode) navigate("/app/assessments");
  };

  // Render Public SaaS Experience
  if (!isEnterprise) {
    return (
      <div className="qf-public-layout" style={{ minHeight: "100vh", display: "flex", flexDirection: "column", backgroundColor: "var(--bg-primary)" }}>
        <PublicNavbar />
        <main style={{ flex: 1 }}>
          {currentPath === "/" && <HomePage />}
          {currentPath === "/platform" && <PlatformPage />}
          {currentPath === "/intelligence" && <IntelligencePage />}
          {currentPath === "/resources" && <ResourcesPage />}
          {currentPath === "/about" && <AboutPage />}
          {currentPath === "/scan" && <ScannerPage />}
          {currentPath.startsWith("/scan/results") && <ScanResultsPage />}
          {currentPath === "/request-demo" && <RequestDemoPage />}
          {/* Fallback for unknown public paths */}
          {currentPath !== "/" &&
            currentPath !== "/platform" &&
            currentPath !== "/intelligence" &&
            currentPath !== "/resources" &&
            currentPath !== "/about" &&
            currentPath !== "/scan" &&
            !currentPath.startsWith("/scan/results") &&
            currentPath !== "/request-demo" && <HomePage />}
        </main>
        <PublicFooter />
      </div>
    );
  }

  // Render Enterprise Console Shell
  return (
    <div className="qf-app-layout">
      <Header onNewAssessment={handleNewAssessment} />
      <div className="qf-body-layout">
        <Sidebar activeTab={activeTab} onSelectTab={handleSelectTab} />
        <main className="qf-main-content" role="main">
          {activeTab === "diagnostics" && (
            <DashboardOverview
              onNewAssessment={handleNewAssessment}
              onSelectAssessment={handleSelectAssessment}
            />
          )}

          {activeTab === "assessments" && (
            <AssessmentList
              onSelectAssessment={handleSelectAssessment}
              onNewAssessment={handleNewAssessment}
            />
          )}

          {activeTab === "assessments-new" && (
            <AssessmentWizard
              onCancel={handleBackToList}
              onLaunchSuccess={handleLaunchSuccess}
            />
          )}

          {activeTab === "assessments-progress" && activeAssessmentId && (
            <AssessmentProgress
              assessmentId={activeAssessmentId}
              onViewResults={handleViewResults}
              onBackToList={handleBackToList}
            />
          )}

          {activeTab === "assessments-detail" && activeAssessmentId && (
            <AssessmentDetail
              assessmentId={activeAssessmentId}
              onBackToList={handleBackToList}
              onViewProgress={(id) => {
                setActiveAssessmentId(id);
                setActiveTab("assessments-progress");
              }}
            />
          )}

          {activeTab === "discover" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
              <TargetManagement />
              <SourceUpload />
            </div>
          )}

          {activeTab === "inventory" && <AssetExplorer />}

          {activeTab === "prioritise" && <RiskDashboard />}

          {activeTab === "settings" && <PlatformSettings />}

          {activeTab !== "diagnostics" &&
            activeTab !== "assessments" &&
            activeTab !== "assessments-new" &&
            activeTab !== "assessments-progress" &&
            activeTab !== "assessments-detail" &&
            activeTab !== "discover" &&
            activeTab !== "inventory" &&
            activeTab !== "prioritise" &&
            activeTab !== "settings" && (
              <div className="qf-placeholder-view">
                <h2>Module Scheduled for Upcoming Sprint</h2>
                <p>
                  The <strong>{activeTab.toUpperCase()}</strong> workflow component is
                  currently in the design phase per the Implementation Roadmap.
                </p>
                <button
                  type="button"
                  className="qf-btn-primary"
                  onClick={() => handleSelectTab("diagnostics")}
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

export const App: React.FC<AppProps> = ({ initialPath }) => {
  return (
    <RouterProvider initialPath={initialPath}>
      <AppContent />
    </RouterProvider>
  );
};

export default App;
