import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ReportDownloadHub } from "./ReportDownloadHub";
import * as api from "../../services/api";

describe("ReportDownloadHub Feature", () => {
  const assessmentId = "a1111111-2222-3333-4444-555555555555";
  const fakeHash = "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a";

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock window.URL.createObjectURL and revokeObjectURL
    window.URL.createObjectURL = vi.fn().mockReturnValue("blob:mock-url");
    window.URL.revokeObjectURL = vi.fn();
  });

  it("renders 3 download options and verified RFC 8785 canonical hash", () => {
    render(
      <ReportDownloadHub
        assessmentId={assessmentId}
        reportSnapshotHash={fakeHash}
        isHashVerified={true}
      />
    );

    expect(screen.getByText("Cryptographic Report Seal")).toBeInTheDocument();
    expect(screen.getByText(/RFC 8785 Canonical Digest Verified/i)).toBeInTheDocument();
    expect(screen.getByTitle(fakeHash)).toBeInTheDocument();

    expect(screen.getByText("CycloneDX 1.6 CBOM")).toBeInTheDocument();
    expect(screen.getByText("RFC 4180 CRLF CSV Export")).toBeInTheDocument();
    expect(screen.getByText("Executive Markdown Report")).toBeInTheDocument();
  });

  it("triggers CycloneDX download when requested", async () => {
    const mockBlob = new Blob(['{"bomFormat":"CycloneDX"}'], { type: "application/json" });
    vi.spyOn(api, "downloadCycloneDxReport").mockResolvedValue(mockBlob);

    render(
      <ReportDownloadHub
        assessmentId={assessmentId}
        reportSnapshotHash={fakeHash}
        isHashVerified={true}
      />
    );

    const cdxBtn = screen.getByRole("button", { name: /download cyclonedx json/i });
    await userEvent.click(cdxBtn);

    await waitFor(() => {
      expect(api.downloadCycloneDxReport).toHaveBeenCalledWith(assessmentId);
      expect(window.URL.createObjectURL).toHaveBeenCalledWith(mockBlob);
    });
  });

  it("triggers CSV download when requested", async () => {
    const mockBlob = new Blob(["asset_key,algorithm\n"], { type: "text/csv" });
    vi.spyOn(api, "downloadCsvReport").mockResolvedValue(mockBlob);

    render(
      <ReportDownloadHub
        assessmentId={assessmentId}
        reportSnapshotHash={fakeHash}
        isHashVerified={true}
      />
    );

    const csvBtn = screen.getByRole("button", { name: /download csv inventory/i });
    await userEvent.click(csvBtn);

    await waitFor(() => {
      expect(api.downloadCsvReport).toHaveBeenCalledWith(assessmentId);
      expect(window.URL.createObjectURL).toHaveBeenCalledWith(mockBlob);
    });
  });

  it("triggers Markdown download when requested", async () => {
    const mockBlob = new Blob(["# Report\n"], { type: "text/markdown" });
    vi.spyOn(api, "downloadMarkdownReport").mockResolvedValue(mockBlob);

    render(
      <ReportDownloadHub
        assessmentId={assessmentId}
        reportSnapshotHash={fakeHash}
        isHashVerified={true}
      />
    );

    const mdBtn = screen.getByRole("button", { name: /download markdown report/i });
    await userEvent.click(mdBtn);

    await waitFor(() => {
      expect(api.downloadMarkdownReport).toHaveBeenCalledWith(assessmentId);
      expect(window.URL.createObjectURL).toHaveBeenCalledWith(mockBlob);
    });
  });
});

