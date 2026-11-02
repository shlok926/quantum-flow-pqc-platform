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

