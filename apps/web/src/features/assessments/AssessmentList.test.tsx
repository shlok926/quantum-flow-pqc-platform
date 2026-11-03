import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AssessmentList } from "./AssessmentList";
import * as api from "../../services/api";
import { AssessmentResponse, AssessmentListResponse } from "../../types";

const mockAssessments: AssessmentResponse[] = [
  {
    id: "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    target_id: "a1111111-2222-3333-4444-555555555555",
    title: "Production E-Commerce Gateways",
    status: "completed",
    progress_stage: "COMPLETED",
    progress_percent: 100,
    discovery_sources: ["network_tls", "source_code"],
    target_snapshot: {
      hostname: "api.payment.internal",
      port: 443,
      environment: "production",
    },
    collector_results: {},
    asset_counts: {
      total_assets: 14,
      by_type: { certificate: 2, algorithm_usage: 12 },
    },
    risk_summary: {
      overall_score: 820,
      overall_category: "critical",
      max_asset_qvi: 820,
      shor_vulnerable_count: 5,
      grover_margin_count: 6,
      pqc_recognised_count: 3,
    },
    scope_hash: "hash-scope-1",
    coverage_summary: {},
    error_summary: null,
    methodology_version: "QFT-RISK-v1.0",
    engine_version: "v1.0.0",
    retry_count: 0,
    max_retries: 3,
    created_at: "2026-11-03T10:00:00Z",
    updated_at: "2026-11-03T10:00:00Z",
    started_at: "2026-11-03T10:00:01Z",
    completed_at: "2026-11-03T10:02:15Z",
    report_snapshot_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  },
  {
    id: "b2222222-3333-4444-5555-666666666666",
    target_id: "c3333333-4444-5555-6666-777777777777",
    title: "Legacy Staging Core",
    status: "failed",
    progress_stage: "DISCOVERY",
    progress_percent: 35,
    discovery_sources: ["network_tls"],
    target_snapshot: {
      hostname: "staging.internal",
      port: 8443,
      environment: "staging",
    },
    collector_results: {
      network_tls: { status: "failed", error: "Connection reset by peer" },
    },
    asset_counts: { total_assets: 0 },
    risk_summary: {},
    scope_hash: "hash-scope-2",
    coverage_summary: {},
    error_summary: "Connection reset by peer",
    methodology_version: "QFT-RISK-v1.0",
    engine_version: "v1.0.0",
    retry_count: 1,
    max_retries: 3,
    created_at: "2026-11-03T11:00:00Z",
    updated_at: "2026-11-03T11:00:00Z",
    started_at: "2026-11-03T11:00:01Z",
    completed_at: null,
    report_snapshot_hash: null,
  },
];

describe("AssessmentList Feature", () => {
  const onSelectAssessment = vi.fn();
  const onNewAssessment = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders assessments table with QVI badges, hosts, and actions", async () => {
    const listRes: AssessmentListResponse = {
      total: 2,
      limit: 50,
      offset: 0,
      items: mockAssessments,
    };
    vi.spyOn(api, "listAssessments").mockResolvedValue(listRes);

    render(
      <AssessmentList
        onSelectAssessment={onSelectAssessment}
        onNewAssessment={onNewAssessment}
      />
    );

    expect(screen.getByText("Enterprise Cryptographic Assessments")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Production E-Commerce Gateways")).toBeInTheDocument();
      expect(screen.getByText("api.payment.internal")).toBeInTheDocument();
      expect(screen.getByText("Legacy Staging Core")).toBeInTheDocument();
      expect(screen.getByText("staging.internal")).toBeInTheDocument();
    });

    // Check QVI Score badge
    expect(screen.getByText("QVI 820")).toBeInTheDocument();

    // Check actions
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reports/i })).toBeInTheDocument();
  });

  it("navigates to assessment details when row is clicked", async () => {
    const listRes: AssessmentListResponse = {
      total: 2,
      limit: 50,
      offset: 0,
      items: mockAssessments,
    };
    vi.spyOn(api, "listAssessments").mockResolvedValue(listRes);

    render(
      <AssessmentList
        onSelectAssessment={onSelectAssessment}
        onNewAssessment={onNewAssessment}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Production E-Commerce Gateways")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Production E-Commerce Gateways"));

    expect(onSelectAssessment).toHaveBeenCalledWith(
      "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "COMPLETED"
    );
  });

  it("triggers onNewAssessment when 'New Assessment' CTA button is clicked", async () => {
    const emptyRes: AssessmentListResponse = {
      total: 0,
      limit: 50,
      offset: 0,
      items: [],
    };
    vi.spyOn(api, "listAssessments").mockResolvedValue(emptyRes);

    render(
      <AssessmentList
        onSelectAssessment={onSelectAssessment}
        onNewAssessment={onNewAssessment}
      />
    );

    const newBtn = screen.getByRole("button", { name: /new assessment/i });
    await userEvent.click(newBtn);

    expect(onNewAssessment).toHaveBeenCalledTimes(1);
  });
});
