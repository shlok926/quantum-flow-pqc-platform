import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "./App";
import * as api from "../services/api";

describe("App Shell", () => {
  it("renders header, sidebar, dashboard overview, and footer", async () => {
    vi.spyOn(api, "fetchHealthLive").mockResolvedValue({
      status: "healthy",
      version: "0.1.0",
      service: "quantum-flow-api",
      timestamp: "2026-11-02T12:00:00Z",
    });

    vi.spyOn(api, "fetchHealthReady").mockResolvedValue({
      status: "ready",
      version: "0.1.0",
      timestamp: "2026-11-02T12:00:00Z",
      dependencies: {
        database: { status: "connected", detail: "healthy" },
        redis: { status: "connected", detail: "healthy" },
      },
    });

    render(<App />);

    // Header
    expect(screen.getByText("QUANTUM FLOW")).toBeInTheDocument();
    expect(screen.getByText("Sprint 0: Engineering Foundation")).toBeInTheDocument();

    // Sidebar navigation
    expect(screen.getByRole("navigation", { name: /workflow navigation/i })).toBeInTheDocument();
    expect(screen.getByText("1. Discover")).toBeInTheDocument();
    expect(screen.getByText("2. Inventory (CBOM)")).toBeInTheDocument();

    // Dashboard Overview
    expect(screen.getByText("Post-Quantum Cryptography Control Plane")).toBeInTheDocument();

    // Footer
    expect(screen.getByText(/NIST SP 800-208 \/ FIPS 203 \/ 204 \/ 205 Architecture/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("All Systems Operational")).toBeInTheDocument();
    });
  });

  it("handles sidebar navigation to discovery workflow and future planned stages", async () => {
    vi.spyOn(api, "fetchHealthLive").mockResolvedValue({
      status: "healthy",
      version: "0.1.0",
      service: "quantum-flow-api",
      timestamp: "2026-11-02T12:00:00Z",
    });

    vi.spyOn(api, "fetchHealthReady").mockResolvedValue({
      status: "ready",
      version: "0.1.0",
      timestamp: "2026-11-02T12:00:00Z",
      dependencies: {
        database: { status: "connected", detail: "healthy" },
        redis: { status: "connected", detail: "healthy" },
      },
    });

    vi.spyOn(api, "listTargets").mockResolvedValue({
      total: 0,
      items: [],
    });

    render(<App />);

    // 1. Navigate to Sprint 1 implemented Discover module
    const discoverNavButton = screen.getByText("1. Discover");
    await userEvent.click(discoverNavButton);

    expect(screen.getByText("Target Discovery & Bounded TLS Inspection")).toBeInTheDocument();
    expect(screen.getByText("Register Domain Target")).toBeInTheDocument();

    // 2. Navigate to future planned module (Stage 3: Prioritise)
    const prioritiseNavButton = screen.getByText("3. Prioritise (QVI)");
    await userEvent.click(prioritiseNavButton);

    expect(screen.getByText("Module Scheduled for Upcoming Sprint")).toBeInTheDocument();
    expect(screen.getByText("PRIORITISE")).toBeInTheDocument();

    // 3. Return to diagnostics
    const returnBtn = screen.getByRole("button", { name: /return to system diagnostics/i });
    await userEvent.click(returnBtn);

    expect(screen.getByText("Post-Quantum Cryptography Control Plane")).toBeInTheDocument();
  });
});
