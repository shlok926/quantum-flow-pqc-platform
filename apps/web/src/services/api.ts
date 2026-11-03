import {
  AssessmentCancelRequest,
  AssessmentCreateRequest,
  AssessmentJobListResponse,
  AssessmentListResponse,
  AssessmentReportResponse,
  AssessmentResponse,
  AssetListResponse,
  DiscoveryJobListResponse,
  HealthLiveResponse,
  HealthReadyResponse,
  Observation,
  RiskAssessment,
  RiskAssessmentListResponse,
  Scan,
  StagedUploadResponse,
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
      if (data) {
        if (typeof data.detail === "string") {
          errorDetail = data.detail;
        } else if (data.error && typeof data.error.message === "string") {
          errorDetail = data.error.message;
        } else if (typeof data.message === "string") {
          errorDetail = data.message;
        } else if (data.detail) {
          errorDetail = JSON.stringify(data.detail);
        } else if (data.error) {
          errorDetail = JSON.stringify(data.error);
        }
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
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({}),
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
  const data = await handleResponse<{ items?: Scan[] } | Scan[]>(response);
  if (Array.isArray(data)) return data;
  return data.items || [];
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
  const data = await handleResponse<{ items?: Observation[] } | Observation[]>(response);
  if (Array.isArray(data)) return data;
  return data.items || [];
}

export async function getObservation(id: string): Promise<Observation> {
  const response = await fetch(`${API_BASE_URL}/api/v1/observations/${id}`, {
    headers: { Accept: "application/json" },
  });
  return handleResponse<Observation>(response);
}

/**
 * Cryptographic Asset & CBOM APIs (Sprint 2)
 */
export async function listAssets(params?: {
  asset_type?: string;
  classification?: string;
  skip?: number;
  limit?: number;
}): Promise<AssetListResponse> {
  const query = new URLSearchParams();
  if (params?.asset_type) query.set("asset_type", params.asset_type);
  if (params?.classification) query.set("classification", params.classification);
  if (params?.skip !== undefined) query.set("skip", params.skip.toString());
  if (params?.limit !== undefined) query.set("limit", params.limit.toString());

  const qs = query.toString() ? `?${query.toString()}` : "";
  const response = await fetch(`${API_BASE_URL}/api/v1/assets${qs}`, {
    headers: { Accept: "application/json" },
  });
  return handleResponse<AssetListResponse>(response);
}

export function getExportCbomUrl(): string {
  return `${API_BASE_URL}/api/v1/cbom/export`;
}

export function getExportAssetsCsvUrl(): string {
  return `${API_BASE_URL}/api/v1/assets/export/csv`;
}

/**
 * Quantum Risk Assessment APIs (Sprint 2)
 */
export async function listRiskAssessments(params?: {
  risk_category?: string;
  skip?: number;
  limit?: number;
}): Promise<RiskAssessmentListResponse> {
  const query = new URLSearchParams();
  if (params?.risk_category) query.set("risk_category", params.risk_category);
  if (params?.skip !== undefined) query.set("skip", params.skip.toString());
  if (params?.limit !== undefined) query.set("limit", params.limit.toString());

  const qs = query.toString() ? `?${query.toString()}` : "";
  const response = await fetch(`${API_BASE_URL}/api/v1/risk-assessments${qs}`, {
    headers: { Accept: "application/json" },
  });
  return handleResponse<RiskAssessmentListResponse>(response);
}

export async function assessAsset(assetId: string): Promise<RiskAssessment> {
  const response = await fetch(`${API_BASE_URL}/api/v1/assets/${assetId}/assessments`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
  });
  return handleResponse<RiskAssessment>(response);
}

/**
 * Source Code & Configuration Discovery APIs (Sprint 2)
 */
export async function uploadSourceArchive(file: File): Promise<{
  observation_id: string;
  files_scanned: number;
  findings_count: number;
  dependencies_count: number;
}> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/v1/source/upload`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

export async function importConfiguration(
  configType: "nginx" | "apache" | "kubernetes",
  content: string,
  filePath: string = "imported.conf"
): Promise<{
  observation_id: string;
  findings_count: number;
  findings: unknown[];
}> {
  const response = await fetch(`${API_BASE_URL}/api/v1/config/import`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      config_type: configType,
      file_path: filePath,
      content,
    }),
  });
  return handleResponse(response);
}

/**
 * Discovery Job Execution APIs (Sprint 2)
 */
export async function listDiscoveryJobs(params?: {
  status?: string;
  job_type?: string;
  skip?: number;
  limit?: number;
}): Promise<DiscoveryJobListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.job_type) query.set("job_type", params.job_type);
  if (params?.skip !== undefined) query.set("skip", params.skip.toString());
  if (params?.limit !== undefined) query.set("limit", params.limit.toString());

  const qs = query.toString() ? `?${query.toString()}` : "";
  const response = await fetch(`${API_BASE_URL}/api/v1/jobs${qs}`, {
    headers: { Accept: "application/json" },
  });
  return handleResponse<DiscoveryJobListResponse>(response);
}


/**
 * Sprint 3 Step 4: Unified Assessment Lifecycle APIs
 */

export async function listAssessments(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<AssessmentListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.limit !== undefined) query.set("limit", params.limit.toString());
  if (params?.offset !== undefined) query.set("offset", params.offset.toString());

  const qs = query.toString() ? `?${query.toString()}` : "";
  const response = await fetch(`${API_BASE_URL}/api/v1/assessments${qs}`, {
    headers: { Accept: "application/json" },
  });
  return handleResponse<AssessmentListResponse>(response);
}

export async function getAssessment(id: string): Promise<AssessmentResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/assessments/${id}`, {
    headers: { Accept: "application/json" },
  });
  return handleResponse<AssessmentResponse>(response);
}

export async function createAssessment(
  payload: AssessmentCreateRequest
): Promise<AssessmentResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/assessments`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });
  return handleResponse<AssessmentResponse>(response);
}

export async function cancelAssessment(
  id: string,
  payload: AssessmentCancelRequest = { reason: "User cancelled in dashboard" }
): Promise<AssessmentResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/assessments/${id}/cancel`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });
  return handleResponse<AssessmentResponse>(response);
}

export async function retryAssessment(id: string): Promise<AssessmentResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/assessments/${id}/retry`, {
    method: "POST",
    headers: {
      Accept: "application/json",
    },
  });
  return handleResponse<AssessmentResponse>(response);
}

export async function stageArchiveUpload(file: File): Promise<StagedUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/v1/assessments/stage-upload`, {
    method: "POST",
    body: formData,
  });
  return handleResponse<StagedUploadResponse>(response);
}

export async function getAssessmentReport(id: string): Promise<AssessmentReportResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/assessments/${id}/report`, {
    headers: { Accept: "application/json" },
  });
  return handleResponse<AssessmentReportResponse>(response);
}

export async function listAssessmentJobs(id: string): Promise<AssessmentJobListResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/assessments/${id}/jobs`, {
    headers: { Accept: "application/json" },
  });
  return handleResponse<AssessmentJobListResponse>(response);
}

/**
 * Verified Report Streaming Downloads (Phase 2 RFC 5987 & CycloneDX 1.6)
 */
export async function downloadCycloneDxReport(id: string): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/api/v1/assessments/${id}/reports/cyclonedx`);
  if (!response.ok) {
    throw new Error(`Failed to download CycloneDX report (HTTP ${response.status})`);
  }
  return response.blob();
}

export async function downloadCsvReport(id: string): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/api/v1/assessments/${id}/reports/csv`);
  if (!response.ok) {
    throw new Error(`Failed to download CSV report (HTTP ${response.status})`);
  }
  return response.blob();
}

export async function downloadMarkdownReport(id: string): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/api/v1/assessments/${id}/reports/markdown`);
  if (!response.ok) {
    throw new Error(`Failed to download Markdown report (HTTP ${response.status})`);
  }
  return response.blob();
}

/**
 * Safe Browser Blob Trigger with Asynchronous Object URL Revocation
 */
export function triggerBlobDownload(blob: Blob, filename: string): void {
  const objectUrl = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  setTimeout(() => {
    try {
      window.URL.revokeObjectURL(objectUrl);
      if (link.parentNode) {
        link.parentNode.removeChild(link);
      }
    } catch {
      // Ignored
    }
  }, 1000);
}
