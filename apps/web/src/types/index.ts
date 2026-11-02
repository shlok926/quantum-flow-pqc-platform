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

