/**
 * Core type definitions for Quantum Flow Frontend.
 */

export interface HealthLiveResponse {
  status: string;
  version: string;
  service: string;
  timestamp: string;
}

export interface DependencyStatus {
  status: string;
  detail: string | null;
}

export interface HealthReadyResponse {
  status: string;
  version: string;
  timestamp: string;
  dependencies: {
    database: DependencyStatus;
    redis: DependencyStatus;
    [key: string]: DependencyStatus;
  };
}

export interface SystemHealthState {
  live: HealthLiveResponse | null;
  ready: HealthReadyResponse | null;
  loading: boolean;
  error: string | null;
}

/**
 * Target Domain Entity types.
 */
export type TargetEnvironment = "development" | "testing" | "staging" | "production";
export type TargetCriticality = "low" | "medium" | "high" | "critical";
export type TargetStatus = "pending_verification" | "verified" | "disabled";
export type AuthorisationStatus = "pending" | "confirmed" | "revoked";

export interface Target {
  id: string;
  hostname: string;
  environment: TargetEnvironment;
  criticality: TargetCriticality;
  status: TargetStatus;
  authorisation_status: AuthorisationStatus;
  verification_token: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
  verified_at?: string | null;
}

export interface TargetCreate {
  hostname: string;
  environment?: TargetEnvironment;
  criticality?: TargetCriticality;
  description?: string | null;
  explicit_authorisation_confirmed: boolean;
  authorisation_declared?: boolean;
}

export interface TargetVerifyResponse {
  target_id: string;
  hostname: string;
  status: TargetStatus;
  authorisation_status: AuthorisationStatus;
  verified_at: string;
  message: string;
}

export interface TargetListResponse {
  total: number;
  items: Target[];
}

/**
 * Scan Execution types.
 */
export type ScanStatus = "pending" | "in_progress" | "completed" | "failed";

export interface Scan {
  id: string;
  target_id: string;
  status: ScanStatus;
  target_ip?: string | null;
  port: number;
  collector_version: string;
  error_code?: string | null;
  error_message?: string | null;
  created_at: string;
  completed_at?: string | null;
}

/**
 * Observation and Cryptographic Evidence types.
 */
export interface TLSEndpointEvidence {
  target_hostname: string;
  target_ip: string;
  port: number;
  scan_timestamp: string;
  collector_version: string;
  connection_status: string;
  negotiated_protocol: string | null;
  negotiated_cipher_name: string | null;
  alpn_protocol: string | null;
  peer_certificate_chain_length: number;
}

export interface CertificateEvidence {
  subject_dn: string;
  issuer_dn: string;
  serial_number_hex: string;
  not_valid_before: string;
  not_valid_after: string;
  is_currently_valid: boolean;
  san_dns_names: string[];
  sha256_fingerprint: string;
  public_key_algorithm: string;
  key_size_bits: number | null;
  curve_name: string | null;
}

export interface ObservationPayload {
  endpoint: TLSEndpointEvidence;
  certificate: CertificateEvidence | null;
}

export interface Observation {
  id: string;
  scan_id: string;
  target_id: string;
  observation_type: string;
  evidence_payload: ObservationPayload;
  evidence_sha256: string;
  collector_version: string;
  observed_at: string;
}

/**
 * Sprint 2: Cryptographic Assets & CBOM Inventory types
 */
export interface CryptographicAsset {
  id: string;
  target_id: string | null;
  asset_type: string;
  asset_key: string;
  display_name: string;
  locator: string | null;
  environment: string;
  business_criticality: string;
  algorithm_family: string | null;
  algorithm_name: string | null;
  cryptographic_purpose: string;
  parameters: Record<string, unknown>;
  lifecycle_status: string;
  classification: string;
  confidence_score: number;
  first_seen_at: string;
  last_seen_at: string;
}

export interface AssetListResponse {
  total: number;
  items: CryptographicAsset[];
  skip: number;
  limit: number;
}

/**
 * Sprint 2: Quantum Risk Assessment types
 */
export interface RiskFactor {
  id: string;
  dimension: string;
  code: string;
  title: string;
  weight: number;
  rating: number;
  contribution: number;
  rationale: string;
}

export interface Recommendation {
  id: string;
  title: string;
  description: string;
  remediation_category: string;
  priority: string;
  validation_steps: string[];
  known_limitations?: string | null;
}

export interface RiskAssessment {
  id: string;
  asset_id: string;
  assessment_number: number;
  status: string;
  score: number;
  risk_category: "critical" | "high" | "elevated" | "guarded" | "low";
  quantum_threat_type: string;
  threat_summary: string;
  evidence_quality: string;
  created_at: string;
  factors: RiskFactor[];
  recommendations: Recommendation[];
}

export interface RiskAssessmentListResponse {
  total: number;
  items: RiskAssessment[];
  skip: number;
  limit: number;
}

/**
 * Sprint 2: Discovery Job types
 */
export interface DiscoveryJob {
  id: string;
  job_type: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  target_id: string | null;
  input_params: Record<string, unknown>;
  result_summary: Record<string, unknown> | null;
  error_message: string | null;
  retry_count: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface DiscoveryJobListResponse {
  total: number;
  items: DiscoveryJob[];
  skip: number;
  limit: number;
}


/**
 * Sprint 3 Step 4: Unified Assessment Types (Mapping 1:1 to FastAPI backend schemas)
 */
export type AssessmentStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export type AssessmentStage =
  | "QUEUED"
  | "DISCOVERY"
  | "CBOM_INGESTION"
  | "RISK_ASSESSMENT"
  | "REPORT_FROZEN"
  | "COMPLETED";

export interface AssessmentCreateRequest {
  title: string;
  target_id?: string | null;
  discovery_sources?: string[];
  input_payload?: Record<string, unknown>;
  upload_token?: string | null;
  extra_params?: Record<string, unknown>;
}

export interface AssessmentCancelRequest {
  reason: string;
}

export interface AssessmentResponse {
  id: string;
  title: string;
  target_id: string | null;
  target_snapshot: Record<string, unknown>;
  scope_hash: string;
  status: AssessmentStatus;
  progress_stage: AssessmentStage;
  progress_percent: number;
  discovery_sources: string[];
  collector_results: Record<string, unknown>;
  coverage_summary: Record<string, unknown>;
  asset_counts: Record<string, unknown>;
  risk_summary: Record<string, unknown>;
  error_summary: string | null;
  report_snapshot_hash: string | null;
  methodology_version: string;
  engine_version: string;
  retry_count: number;
  max_retries: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AssessmentListResponse {
  items: AssessmentResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface AssessmentReportResponse {
  assessment_id: string;
  status: string;
  methodology_version: string;
  engine_version: string;
  report_snapshot: Record<string, unknown>;
  report_snapshot_hash: string;
  is_hash_verified: boolean;
  is_immutable: boolean;
  completed_at: string | null;
}

export interface AssessmentJobSummary {
  id: string;
  job_type: string;
  status: string;
  progress_percent: number;
  worker_id: string | null;
  lease_expires_at: string | null;
  retry_count: number;
  error_message: string | null;
  result_summary: Record<string, unknown> | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface AssessmentJobListResponse {
  assessment_id: string;
  total_jobs: number;
  jobs: AssessmentJobSummary[];
}

export interface StagedUploadResponse {
  upload_token: string;
  filename: string;
  byte_size: number;
  sha256: string;
  status: string;
  uploaded_at: string;
}

export interface UploadTokenMetadata {
  upload_token: string;
  tenant_id: string;
  filename: string;
  byte_size: number;
  sha256: string;
  content_type: string;
  status: string;
  uploaded_at: string;
  assessment_id: string | null;
  retry_count: number;
}
