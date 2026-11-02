import { HealthLiveResponse, HealthReadyResponse } from "../types";

/**
 * API client configured with environment-based base URL.
 */
export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string) || "http://localhost:8000";

/**
 * Fetch liveness status from the backend control plane.
 */
export async function fetchHealthLive(): Promise<HealthLiveResponse> {
  const response = await fetch(`${API_BASE_URL}/health/live`, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Liveness probe failed with HTTP status ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch readiness status (backing database and cache) from the backend.
 */
export async function fetchHealthReady(): Promise<HealthReadyResponse> {
  const response = await fetch(`${API_BASE_URL}/health/ready`, {
    headers: {
      Accept: "application/json",
    },
  });

  // Readiness returns 200 when ready, 503 when dependencies are down
  const data = await response.json();
  if (response.status !== 200 && response.status !== 503) {
    throw new Error(`Readiness probe failed with unexpected HTTP ${response.status}`);
  }

  return data;
}

