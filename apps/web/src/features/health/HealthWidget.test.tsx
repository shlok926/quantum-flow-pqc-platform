import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HealthWidget } from "./HealthWidget";
import * as api from "../../services/api";

describe("HealthWidget", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders healthy state when API, DB and Redis are operational", async () => {
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
        database: { status: "connected", detail: "PostgreSQL 16 connection established" },
        redis: { status: "connected", detail: "Redis 7 ping successful" },
      },
    });

    render(<HealthWidget />);

    expect(screen.getByText(/Checking System/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("All Systems Operational")).toBeInTheDocument();
    });

    expect(screen.getByText(/API, PostgreSQL database, and Redis cache are fully connected/i)).toBeInTheDocument();
    expect(screen.getByText("FastAPI Control Plane")).toBeInTheDocument();
    expect(screen.getByText("PostgreSQL 16 (AsyncPG)")).toBeInTheDocument();
    expect(screen.getByText("Redis 7 (Async Redis)")).toBeInTheDocument();
    expect(screen.getAllByText("Connected").length).toBe(2);
  });

  it("renders degraded state when backend reports dependencies down", async () => {
    vi.spyOn(api, "fetchHealthLive").mockResolvedValue({
      status: "healthy",
      version: "0.1.0",
      service: "quantum-flow-api",
      timestamp: "2026-11-02T12:00:00Z",
    });

    vi.spyOn(api, "fetchHealthReady").mockResolvedValue({
      status: "degraded",
      version: "0.1.0",
      timestamp: "2026-11-02T12:00:00Z",
      dependencies: {
        database: { status: "disconnected", detail: "Database connection failed" },
        redis: { status: "connected", detail: "Redis 7 ping successful" },
      },
    });

    render(<HealthWidget />);

    await waitFor(() => {
      expect(screen.getByText("System Degraded")).toBeInTheDocument();
    });

    expect(screen.getByText("Degraded")).toBeInTheDocument();
    expect(screen.getByText("Database connection failed")).toBeInTheDocument();
  });

  it("renders offline error state when fetch fails", async () => {
    vi.spyOn(api, "fetchHealthLive").mockRejectedValue(
      new Error("Failed to connect to host (connection refused)")
    );
    vi.spyOn(api, "fetchHealthReady").mockRejectedValue(
      new Error("Failed to connect to host (connection refused)")
    );

    render(<HealthWidget />);

    await waitFor(() => {
      expect(screen.getByText("Control Plane Offline")).toBeInTheDocument();
    });

    expect(
      screen.getByText(/Failed to connect to host/i)
    ).toBeInTheDocument();
  });

  it("refreshes status on button click", async () => {
    const liveSpy = vi.spyOn(api, "fetchHealthLive").mockResolvedValue({
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

    render(<HealthWidget />);

    await waitFor(() => {
      expect(screen.getByText("All Systems Operational")).toBeInTheDocument();
    });

    const refreshButton = screen.getByRole("button", { name: /refresh health status/i });
    await userEvent.click(refreshButton);

    expect(liveSpy).toHaveBeenCalledTimes(2);
  });
});

