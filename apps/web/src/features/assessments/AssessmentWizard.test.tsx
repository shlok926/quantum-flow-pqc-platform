import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AssessmentWizard } from "./AssessmentWizard";
import * as api from "../../services/api";
import { AssessmentResponse } from "../../types";

describe("AssessmentWizard Feature", () => {
  const onCancel = vi.fn();
  const onLaunchSuccess = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(api, "listTargets").mockResolvedValue({
      total: 1,
      items: [
        {
          id: "t1111111-2222-3333-4444-555555555555",
          hostname: "gw.internal.corp",
          environment: "production",
          criticality: "high",
          status: "verified",
          authorisation_status: "confirmed",
          verification_token: "token-123",
          created_at: "2026-11-02T10:00:00Z",
          updated_at: "2026-11-02T10:00:00Z",
        },
      ],
    });
  });

  it("navigates through the 4 steps and launches assessment successfully", async () => {
    const mockCreated: AssessmentResponse = {
      id: "a9999999-8888-7777-6666-555555555555",
      target_id: "t1111111-2222-3333-4444-555555555555",
      title: "Quarterly Cryptographic Assessment",
      status: "queued",
      progress_stage: "QUEUED",
      progress_percent: 0,
      discovery_sources: ["network_tls"],
      target_snapshot: { hostname: "gw.internal.corp" },
      collector_results: {},
      asset_counts: {},
      risk_summary: {},
      scope_hash: "hash-mock",
      coverage_summary: {},
      error_summary: null,
      methodology_version: "QFT-RISK-v1.0",
      engine_version: "v1.0.0",
      retry_count: 0,
      max_retries: 3,
      created_at: "2026-11-03T12:00:00Z",
      updated_at: "2026-11-03T12:00:00Z",
      started_at: null,
      completed_at: null,
      report_snapshot_hash: null,
    };
    vi.spyOn(api, "createAssessment").mockResolvedValue(mockCreated);

    render(
      <AssessmentWizard
        onCancel={onCancel}
        onLaunchSuccess={onLaunchSuccess}
      />
    );

    // Step 1: Target Scope
    expect(screen.getByText(/Step 1: Define Assessment Scope & Title/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("gw.internal.corp (production - high)")).toBeInTheDocument();
    });

    // Select the target
    const targetSelect = screen.getByRole("combobox");
    await userEvent.selectOptions(targetSelect, "t1111111-2222-3333-4444-555555555555");

    // Check authorization checkbox
    const authCheckbox = screen.getByRole("checkbox");
    await userEvent.click(authCheckbox);

    // Advance to Step 2
    const toStep2Btn = screen.getByRole("button", { name: /next: collectors/i });
    expect(toStep2Btn).not.toBeDisabled();
    await userEvent.click(toStep2Btn);

    // Step 2: Configure Collectors
    expect(screen.getByText(/Step 2: Select Discovery Collectors/i)).toBeInTheDocument();
    expect(screen.getByText("Network TLS Endpoint Discovery")).toBeInTheDocument();

    // Advance to Step 3
    const toStep3Btn = screen.getByRole("button", { name: /next: archive staging/i });
    await userEvent.click(toStep3Btn);

    // Step 3: Archive Staging Upload
    expect(screen.getByText(/Step 3: Stage Source Code Archive/i)).toBeInTheDocument();

    // Skip/advance to Step 4
    const toStep4Btn = screen.getByRole("button", { name: /next: review & launch/i });
    await userEvent.click(toStep4Btn);

    // Step 4: Review & Launch
    expect(screen.getByText(/Step 4: Review Scope & Launch Assessment/i)).toBeInTheDocument();
    expect(screen.getByText("gw.internal.corp")).toBeInTheDocument();

    // Launch
    const launchBtn = screen.getByRole("button", { name: /launch assessment/i });
    await userEvent.click(launchBtn);

    await waitFor(() => {
      expect(api.createAssessment).toHaveBeenCalledWith(
        expect.objectContaining({
          target_id: "t1111111-2222-3333-4444-555555555555",
          discovery_sources: ["network_tls"],
        })
      );
      expect(onLaunchSuccess).toHaveBeenCalledWith("a9999999-8888-7777-6666-555555555555");
    });
  });
});
