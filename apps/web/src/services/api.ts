import {
  HealthLiveResponse,
  HealthReadyResponse,
  Observation,
  Scan,
  Target,
  TargetCreate,
  TargetListResponse,
  TargetVerifyResponse,
} from "../types";

/**
 * API client configured with environment-based base URL.
 */
export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string) || "http://localhost:8000";

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const data = await response.json();
      if (data && data.detail) {
        errorDetail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // Ignore JSON parse failure
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

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

/**
 * Target Management APIs (QF-001)
 */
export async function registerTarget(payload: TargetCreate): Promise<Target> {
  const response = await fetch(`${API_BASE_URL}/api/v1/targets`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });
  return handleResponse<Target>(response);
}

export async function listTargets(params?: {
  status?: string;
  environment?: string;
  skip?: number;
  limit?: number;
}): Promise<TargetListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.environment) query.set("environment", params.environment);
  if (params?.skip !== undefined) query.set("skip", params.skip.toString());
  if (params?.limit !== undefined) query.set("limit", params.limit.toString());

  const qs = query.toString() ? `?${query.toString()}` : "";
  const response = await fetch(`${API_BASE_URL}/api/v1/targets${qs}`, {
    headers: { Accept: "application/json" },
  });
  return handleResponse<TargetListResponse>(response);
}

export async function getTarget(id: string): Promise<Target> {
  const response = await fetch(`${API_BASE_URL}/api/v1/targets/${id}`, {
    headers: { Accept: "application/json" },
  });
  return handleResponse<Target>(response);
}

export async function verifyTarget(id: string): Promise<TargetVerifyResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/targets/${id}/verify`, {
    method: "POST",
    headers: { Accept: "application/json" },
  });
  return handleResponse<TargetVerifyResponse>(response);
}

export async function disableTarget(id: string): Promise<Target> {
  const response = await fetch(`${API_BASE_URL}/api/v1/targets/${id}/disable`, {
    method: "POST",
    headers: { Accept: "application/json" },
  });
  return handleResponse<Target>(response);
}

/**
 * Discovery Scan APIs (QF-003)
 */
export async function triggerScan(targetId: string, timeoutSeconds?: number): Promise<Scan> {
  const response = await fetch(`${API_BASE_URL}/api/v1/targets/${targetId}/scans`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(timeoutSeconds ? { timeout_seconds: timeoutSeconds } : {}),
  });
  return handleResponse<Scan>(response);
}

export async function listTargetScans(targetId: string): Promise<Scan[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/targets/${targetId}/scans`, {
    headers: { Accept: "application/json" },
  });
  return handleResponse<Scan[]>(response);
}

export async function getScan(id: string): Promise<Scan> {
  const response = await fetch(`${API_BASE_URL}/api/v1/scans/${id}`, {
    headers: { Accept: "application/json" },
  });
  return handleResponse<Scan>(response);
}

/**
 * Observation APIs (QF-007)
 */
export async function listTargetObservations(targetId: string): Promise<Observation[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/targets/${targetId}/observations`, {
    headers: { Accept: "application/json" },
  });
  return handleResponse<Observation[]>(response);
}

export async function getObservation(id: string): Promise<Observation> {
  const response = await fetch(`${API_BASE_URL}/api/v1/observations/${id}`, {
    headers: { Accept: "application/json" },
  });
  return handleResponse<Observation>(response);
}

