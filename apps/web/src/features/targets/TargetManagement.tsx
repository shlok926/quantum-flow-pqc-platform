import React, { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Copy,
  Lock,
  Play,
  Plus,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import {
  disableTarget,
  listTargetObservations,
  listTargets,
  registerTarget,
  triggerScan,
  verifyTarget,
} from "../../services/api";
import {
  Observation,
  Target,
  TargetCriticality,
  TargetEnvironment,
} from "../../types";

export const TargetManagement: React.FC = () => {
  // Target List & Filtering State
  const [targets, setTargets] = useState<Target[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [filterEnv, setFilterEnv] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Target Registration Form State
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [regHostname, setRegHostname] = useState<string>("");
  const [regEnv, setRegEnv] = useState<TargetEnvironment>("production");
  const [regCriticality, setRegCriticality] = useState<TargetCriticality>("high");
  const [regDescription, setRegDescription] = useState<string>("");
  const [regAuthConfirmed, setRegAuthConfirmed] = useState<boolean>(false);
  const [regError, setRegError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Verification & Challenge Modal State
  const [activeChallengeTarget, setActiveChallengeTarget] = useState<Target | null>(null);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);

  // Scan & Evidence State
  const [scanningTargetId, setScanningTargetId] = useState<string | null>(null);
  const [activeObservation, setActiveObservation] = useState<Observation | null>(null);
  const [scanSafetyAlert, setScanSafetyAlert] = useState<string | null>(null);

  // Domain syntax validation rules
  const validateHostname = (val: string): string | null => {
    const trimmed = val.trim();
    if (!trimmed) return "Hostname is required.";
    if (trimmed.includes("://")) return "Enter only the domain name (exclude schemes like https://).";
    if (trimmed.includes(":") || trimmed.includes("/")) return "Port numbers and paths are not permitted.";
    if (trimmed.includes("@") || trimmed.includes("?") || trimmed.includes("#")) {
      return "Hostname contains invalid characters.";
    }
    const ipv4Regex = /^(\d{1,3}\.){3}\d{1,3}$/;
    if (ipv4Regex.test(trimmed) || trimmed.includes("::")) {
      return "IP literals are prohibited. Please provide a registered domain name.";
    }
    const cleanHost = trimmed.endsWith(".") ? trimmed.slice(0, -1) : trimmed;
    const labels = cleanHost.split(".");
    if (labels.length < 2) {
      return "Hostname must include at least two labels (e.g., example.com).";
    }
    for (const label of labels) {
      if (!label) return "Hostname cannot have empty labels (e.g. '..').";
      if (label.length > 63) return "Domain labels cannot exceed 63 characters.";
      if (label.startsWith("-") || label.endsWith("-")) return "Domain labels cannot start or end with hyphens.";
    }
    return null;
  };

  const hostnameValidationError = regHostname ? validateHostname(regHostname) : null;

  const loadTargets = useCallback(async () => {
    try {
      setLoading(true);
      const res = await listTargets({
        status: filterStatus !== "all" ? filterStatus : undefined,
        environment: filterEnv !== "all" ? filterEnv : undefined,
      });
      setTargets(res.items);
      setErrorMessage(null);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to load targets");
    } finally {
      setLoading(false);
    }
  }, [filterStatus, filterEnv]);

  useEffect(() => {
    loadTargets();
  }, [loadTargets]);

  const handleRegisterTarget = async (e: React.FormEvent) => {
    e.preventDefault();
    const valErr = validateHostname(regHostname);
    if (valErr) {
      setRegError(valErr);
      return;
    }
    if (!regAuthConfirmed) {
      setRegError("You must explicitly certify authorization before registering a target.");
      return;
    }

    try {
      setIsSubmitting(true);
      setRegError(null);
      const newTarget = await registerTarget({
        hostname: regHostname.trim().toLowerCase(),
        environment: regEnv,
        criticality: regCriticality,
        description: regDescription.trim() || undefined,
        explicit_authorisation_confirmed: regAuthConfirmed,
      });

      setShowAddModal(false);
      setRegHostname("");
      setRegDescription("");
      setRegAuthConfirmed(false);
      setSuccessMessage(`Target '${newTarget.hostname}' registered successfully.`);
      await loadTargets();
      setActiveChallengeTarget(newTarget);
    } catch (err) {
      setRegError(err instanceof Error ? err.message : "Registration failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerify = async (target: Target) => {
    try {
      setIsVerifying(true);
      setErrorMessage(null);
      const result = await verifyTarget(target.id);
      setSuccessMessage(result.message);
      setActiveChallengeTarget(null);
      await loadTargets();
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Verification failed.");
    } finally {
      setIsVerifying(false);
    }
  };

  const handleDisable = async (target: Target) => {
    if (!window.confirm(`Are you sure you want to disable '${target.hostname}'? Scans will be blocked.`)) {
      return;
    }
    try {
      await disableTarget(target.id);
      setSuccessMessage(`Target '${target.hostname}' disabled.`);
      await loadTargets();
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Disable target failed.");
    }
  };

  const handleRunScan = async (target: Target) => {
    try {
      setScanningTargetId(target.id);
      setScanSafetyAlert(null);
      setActiveObservation(null);
      setErrorMessage(null);

      const scan = await triggerScan(target.id);

      if (scan.status === "failed") {
        setScanSafetyAlert(
          scan.error_message || `Scan failed: ${scan.error_code || "Unknown security error"}`
        );
      } else {
        // Fetch observations
        const observations = await listTargetObservations(target.id);
        if (observations.length > 0) {
          setActiveObservation(observations[0]);
          setSuccessMessage(`Discovery scan completed for ${target.hostname}. Evidence captured.`);
        }
      }
    } catch (err) {
      setScanSafetyAlert(err instanceof Error ? err.message : "Failed to execute discovery scan");
    } finally {
      setScanningTargetId(null);
    }
  };

  const handleViewEvidence = async (target: Target) => {
    try {
      setLoading(true);
      setScanSafetyAlert(null);
      const observations = await listTargetObservations(target.id);
      if (observations.length > 0) {
        setActiveObservation(observations[0]);
      } else {
        setErrorMessage(`No observations found for ${target.hostname}. Run a scan first.`);
      }
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to retrieve observations");
    } finally {
      setLoading(false);
    }
  };

  const filteredTargets = targets.filter((t) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return t.hostname.toLowerCase().includes(q) || (t.description && t.description.toLowerCase().includes(q));
  });

  return (
    <div className="qf-target-management">
      {/* Header section */}
      <div className="qf-view-header">
        <div>
          <div className="qf-welcome-tag">Sprint 1 Discovery & Target Control</div>
          <h2>Target Discovery & Bounded TLS Inspection</h2>
          <p className="qf-view-description">
            Register authorized domain boundaries, verify scope ownership, and execute bounded,
            SSRF-guarded TLS handshakes for quantum cryptographic posture assessment.
          </p>
        </div>
        <div className="qf-header-actions">
          <button
            type="button"
            className="qf-btn-primary qf-btn-with-icon"
            onClick={() => setShowAddModal(true)}
          >
            <Plus size={16} />
            <span>Register Domain Target</span>
          </button>
        </div>
      </div>

      {/* Global Alerts */}
      {errorMessage && (
        <div className="qf-alert-box qf-alert-error" role="alert">
          <div className="qf-alert-inner">
            <AlertCircle size={18} />
            <span>{errorMessage}</span>
          </div>
          <button type="button" className="qf-alert-close" onClick={() => setErrorMessage(null)}>
            &times;
          </button>
        </div>
      )}

      {successMessage && (
        <div className="qf-alert-box qf-alert-success" role="status">
          <div className="qf-alert-inner">
            <CheckCircle2 size={18} />
            <span>{successMessage}</span>
          </div>
          <button type="button" className="qf-alert-close" onClick={() => setSuccessMessage(null)}>
            &times;
          </button>
        </div>
      )}

      {scanSafetyAlert && (
        <div className="qf-alert-box qf-alert-security" role="alert">
          <div className="qf-alert-inner">
            <ShieldAlert size={20} className="qf-security-icon" />
            <div>
              <strong>SSRF Guard / Security Engine Intercepted Request:</strong>
              <p>{scanSafetyAlert}</p>
            </div>
          </div>
          <button type="button" className="qf-alert-close" onClick={() => setScanSafetyAlert(null)}>
            &times;
          </button>
        </div>
      )}

      {/* Filter and Control Bar */}
      <div className="qf-filter-bar">
        <div className="qf-search-input-wrap">
          <Search size={16} className="qf-search-icon" />
          <input
            type="text"
            className="qf-search-input"
            placeholder="Search targets by hostname..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="qf-filter-selectors">
          <select
            className="qf-select"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="pending_verification">Pending Verification</option>
            <option value="verified">Verified</option>
            <option value="disabled">Disabled</option>
          </select>
          <select
            className="qf-select"
            value={filterEnv}
            onChange={(e) => setFilterEnv(e.target.value)}
          >
            <option value="all">All Environments</option>
            <option value="production">Production</option>
            <option value="staging">Staging</option>
            <option value="development">Development</option>
            <option value="testing">Testing</option>
          </select>
          <button
            type="button"
            className="qf-btn-refresh"
            onClick={loadTargets}
            disabled={loading}
            title="Refresh Target List"
          >
            <RefreshCw size={14} className={loading ? "qf-spin" : ""} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Target Inventory Table */}
      <div className="qf-table-container">
        <table className="qf-data-table" aria-label="Target Domains Inventory">
          <thead>
            <tr>
              <th>Target Domain</th>
              <th>Environment</th>
              <th>Criticality</th>
              <th>Authorisation & Status</th>
              <th>Verification</th>
              <th className="qf-text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && targets.length === 0 ? (
              <tr>
                <td colSpan={6} className="qf-empty-cell">
                  <div className="qf-loading-spinner">
                    <RefreshCw size={24} className="qf-spin" />
                    <span>Loading registered domain targets...</span>
                  </div>
                </td>
              </tr>
            ) : filteredTargets.length === 0 ? (
              <tr>
                <td colSpan={6} className="qf-empty-cell">
                  <div className="qf-empty-state">
                    <Shield size={36} className="qf-empty-icon" />
                    <h4>No Targets Found</h4>
                    <p>No domain targets match your filter. Register an authorized domain above.</p>
                  </div>
                </td>
              </tr>
            ) : (
              filteredTargets.map((target) => (
                <tr key={target.id} className={target.status === "disabled" ? "qf-row-disabled" : ""}>
                  <td>
                    <div className="qf-target-name-cell">
                      <span className="qf-target-hostname font-mono">{target.hostname}</span>
                      {target.description && (
                        <span className="qf-target-desc">{target.description}</span>
                      )}
                    </div>
                  </td>
                  <td>
                    <span className={`qf-env-pill qf-env-${target.environment}`}>
                      {target.environment}
                    </span>
                  </td>
                  <td>
                    <span className={`qf-crit-pill qf-crit-${target.criticality}`}>
                      {target.criticality}
                    </span>
                  </td>
                  <td>
                    <div className="qf-status-cell">
                      {target.status === "verified" && (
                        <span className="qf-badge-verified">
                          <CheckCircle2 size={12} />
                          <span>Verified</span>
                        </span>
                      )}
                      {target.status === "pending_verification" && (
                        <span className="qf-badge-pending">
                          <AlertCircle size={12} />
                          <span>Pending Verification</span>
                        </span>
                      )}
                      {target.status === "disabled" && (
                        <span className="qf-badge-disabled">
                          <XCircle size={12} />
                          <span>Disabled</span>
                        </span>
                      )}
                    </div>
                  </td>
                  <td>
                    {target.status === "verified" ? (
                      <span className="qf-verified-timestamp">
                        {target.verified_at ? new Date(target.verified_at).toLocaleDateString() : "Verified"}
                      </span>
                    ) : (
                      <button
                        type="button"
                        className="qf-btn-link"
                        onClick={() => setActiveChallengeTarget(target)}
                      >
                        Challenge Token
                      </button>
                    )}
                  </td>
                  <td className="qf-text-right">
                    <div className="qf-table-actions">
                      {target.status === "verified" && (
                        <button
                          type="button"
                          className="qf-btn-scan"
                          disabled={scanningTargetId === target.id}
                          onClick={() => handleRunScan(target)}
                          title="Run bounded TLS handshake discovery"
                        >
                          {scanningTargetId === target.id ? (
                            <>
                              <RefreshCw size={13} className="qf-spin" />
                              <span>Scanning...</span>
                            </>
                          ) : (
                            <>
                              <Play size={13} />
                              <span>Scan</span>
                            </>
                          )}
                        </button>
                      )}
                      {target.status === "pending_verification" && (
                        <button
                          type="button"
                          className="qf-btn-verify-action"
                          onClick={() => handleVerify(target)}
                          disabled={isVerifying}
                        >
                          <ShieldCheck size={13} />
                          <span>Verify</span>
                        </button>
                      )}
                      <button
                        type="button"
                        className="qf-btn-secondary-sm"
                        onClick={() => handleViewEvidence(target)}
                        title="View CBOM observations"
                      >
                        Evidence
                      </button>
                      {target.status !== "disabled" && (
                        <button
                          type="button"
                          className="qf-btn-disable-action"
                          onClick={() => handleDisable(target)}
                          title="Disable domain scanning"
                        >
                          Disable
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Observation Evidence View Drawer / Card */}
      {activeObservation && (
        <div className="qf-evidence-card">
          <div className="qf-evidence-header">
            <div className="qf-evidence-title-wrap">
              <Lock size={20} className="text-cyan" />
              <div>
                <h3>
                  Observation Record —{" "}
                  <span className="font-mono">
                    {activeObservation.evidence_payload.endpoint.target_hostname}
                  </span>
                </h3>
                <span className="qf-evidence-subtitle">
                  Bounded TLS 443 Handshake Observation (CBOM Ingestion)
                </span>
              </div>
            </div>
            <button
              type="button"
              className="qf-close-btn"
              onClick={() => setActiveObservation(null)}
            >
              &times;
            </button>
          </div>

          <div className="qf-evidence-grid">
            {/* Endpoint Connection Panel */}
            <div className="qf-detail-panel">
              <div className="qf-panel-heading">Negotiated Transport Details</div>
              <div className="qf-prop-row">
                <span className="qf-prop-name">Target IP (Pinned)</span>
                <span className="qf-prop-value font-mono">
                  {activeObservation.evidence_payload.endpoint.target_ip}:443
                </span>
              </div>
              <div className="qf-prop-row">
                <span className="qf-prop-name">Negotiated Protocol</span>
                <span className="qf-prop-value font-mono text-cyan">
                  {activeObservation.evidence_payload.endpoint.negotiated_protocol || "Unknown"}
                </span>
              </div>
              <div className="qf-prop-row">
                <span className="qf-prop-name">Negotiated Cipher Suite</span>
                <span className="qf-prop-value font-mono">
                  {activeObservation.evidence_payload.endpoint.negotiated_cipher_name || "Unknown"}
                </span>
              </div>
              <div className="qf-prop-row">
                <span className="qf-prop-name">ALPN Protocol</span>
                <span className="qf-prop-value font-mono">
                  {activeObservation.evidence_payload.endpoint.alpn_protocol || "None"}
                </span>
              </div>
              <div className="qf-prop-row">
                <span className="qf-prop-name">Collector Version</span>
                <span className="qf-prop-value font-mono">
                  {activeObservation.collector_version}
                </span>
              </div>
            </div>

            {/* Certificate Panel */}
            <div className="qf-detail-panel">
              <div className="qf-panel-heading">X.509 Server Certificate Cryptography</div>
              {activeObservation.evidence_payload.certificate ? (
                <>
                  <div className="qf-prop-row">
                    <span className="qf-prop-name">Public Key Algorithm</span>
                    <span className="qf-prop-value font-mono text-emerald">
                      {activeObservation.evidence_payload.certificate.public_key_algorithm}{" "}
                      {activeObservation.evidence_payload.certificate.key_size_bits
                        ? `(${activeObservation.evidence_payload.certificate.key_size_bits} bits)`
                        : ""}
                    </span>
                  </div>
                  {activeObservation.evidence_payload.certificate.curve_name && (
                    <div className="qf-prop-row">
                      <span className="qf-prop-name">Elliptic Curve</span>
                      <span className="qf-prop-value font-mono">
                        {activeObservation.evidence_payload.certificate.curve_name}
                      </span>
                    </div>
                  )}
                  <div className="qf-prop-row">
                    <span className="qf-prop-name">Validity Window</span>
                    <span className="qf-prop-value">
                      {new Date(
                        activeObservation.evidence_payload.certificate.not_valid_before
                      ).toLocaleDateString()}{" "}
                      to{" "}
                      {new Date(
                        activeObservation.evidence_payload.certificate.not_valid_after
                      ).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="qf-prop-row">
                    <span className="qf-prop-name">Subject DN</span>
                    <span className="qf-prop-value font-mono qf-truncate" title={activeObservation.evidence_payload.certificate.subject_dn}>
                      {activeObservation.evidence_payload.certificate.subject_dn}
                    </span>
                  </div>
                  <div className="qf-prop-row">
                    <span className="qf-prop-name">Issuer DN</span>
                    <span className="qf-prop-value font-mono qf-truncate" title={activeObservation.evidence_payload.certificate.issuer_dn}>
                      {activeObservation.evidence_payload.certificate.issuer_dn}
                    </span>
                  </div>
                </>
              ) : (
                <div className="qf-empty-subpanel">No server certificate extracted.</div>
              )}
            </div>
          </div>

          {/* Cryptographic Hash and Fingerprint Bar */}
          {activeObservation.evidence_payload.certificate && (
            <div className="qf-fingerprint-box">
              <div className="qf-hash-row">
                <span className="qf-hash-label">Certificate SHA-256 Fingerprint:</span>
                <code className="qf-hash-code font-mono">
                  {activeObservation.evidence_payload.certificate.sha256_fingerprint}
                </code>
              </div>
              <div className="qf-hash-row">
                <span className="qf-hash-label">Observation Evidence Hash (Provenance):</span>
                <code className="qf-hash-code font-mono text-cyan">
                  {activeObservation.evidence_sha256}
                </code>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Target Registration Modal */}
      {showAddModal && (
        <div className="qf-modal-backdrop" role="dialog" aria-modal="true">
          <div className="qf-modal-card">
            <div className="qf-modal-header">
              <div className="qf-modal-title-wrap">
                <Shield size={20} className="text-cyan" />
                <h3>Register Domain Target for Discovery</h3>
              </div>
              <button
                type="button"
                className="qf-modal-close"
                onClick={() => setShowAddModal(false)}
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleRegisterTarget} className="qf-modal-form">
              {regError && (
                <div className="qf-alert-box qf-alert-error">
                  <AlertCircle size={16} />
                  <span>{regError}</span>
                </div>
              )}

              <div className="qf-form-group">
                <label htmlFor="reg-hostname" className="qf-form-label">
                  Fully Qualified Domain Name (FQDN) *
                </label>
                <input
                  id="reg-hostname"
                  type="text"
                  className={`qf-form-input font-mono ${hostnameValidationError ? "qf-input-invalid" : ""}`}
                  placeholder="e.g. portal.example.com"
                  value={regHostname}
                  onChange={(e) => setRegHostname(e.target.value)}
                  required
                />
                {hostnameValidationError && (
                  <span className="qf-field-validation-error">{hostnameValidationError}</span>
                )}
                <span className="qf-form-hint">
                  Only domain names are allowed. Schemes, port numbers, paths, and raw IP literals are blocked.
                </span>
              </div>

              <div className="qf-form-row">
                <div className="qf-form-group qf-flex-1">
                  <label htmlFor="reg-env" className="qf-form-label">
                    Environment Profile
                  </label>
                  <select
                    id="reg-env"
                    className="qf-form-select"
                    value={regEnv}
                    onChange={(e) => setRegEnv(e.target.value as TargetEnvironment)}
                  >
                    <option value="production">Production</option>
                    <option value="staging">Staging</option>
                    <option value="development">Development</option>
                    <option value="testing">Testing</option>
                  </select>
                </div>

                <div className="qf-form-group qf-flex-1">
                  <label htmlFor="reg-criticality" className="qf-form-label">
                    Asset Criticality
                  </label>
                  <select
                    id="reg-criticality"
                    className="qf-form-select"
                    value={regCriticality}
                    onChange={(e) => setRegCriticality(e.target.value as TargetCriticality)}
                  >
                    <option value="critical">Critical (Tier 1)</option>
                    <option value="high">High (Tier 2)</option>
                    <option value="medium">Medium (Tier 3)</option>
                    <option value="low">Low (Tier 4)</option>
                  </select>
                </div>
              </div>

              <div className="qf-form-group">
                <label htmlFor="reg-desc" className="qf-form-label">
                  Scope Description / Asset Notes (Optional)
                </label>
                <textarea
                  id="reg-desc"
                  className="qf-form-textarea"
                  placeholder="e.g. Core customer authentication gateway."
                  rows={2}
                  value={regDescription}
                  onChange={(e) => setRegDescription(e.target.value)}
                />
              </div>

              <div className="qf-form-checkbox-group">
                <label className="qf-checkbox-label">
                  <input
                    type="checkbox"
                    className="qf-checkbox"
                    checked={regAuthConfirmed}
                    onChange={(e) => setRegAuthConfirmed(e.target.checked)}
                    required
                  />
                  <span>
                    <strong>Authorisation Certification:</strong> I certify that I have explicit legal
                    authority to register and scan this domain. Unauthorized scanning is prohibited.
                  </span>
                </label>
              </div>

              <div className="qf-modal-footer">
                <button
                  type="button"
                  className="qf-btn-secondary"
                  onClick={() => setShowAddModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="qf-btn-primary"
                  disabled={isSubmitting || Boolean(hostnameValidationError) || !regAuthConfirmed}
                >
                  {isSubmitting ? "Registering..." : "Register Domain Target"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Verification Challenge Modal */}
      {activeChallengeTarget && (
        <div className="qf-modal-backdrop" role="dialog" aria-modal="true">
          <div className="qf-modal-card">
            <div className="qf-modal-header">
              <div className="qf-modal-title-wrap">
                <ShieldCheck size={20} className="text-emerald" />
                <h3>Domain Ownership Verification Challenge</h3>
              </div>
              <button
                type="button"
                className="qf-modal-close"
                onClick={() => setActiveChallengeTarget(null)}
              >
                &times;
              </button>
            </div>

            <div className="qf-modal-body">
              <p>
                To enable discovery scans on{" "}
                <strong className="font-mono">{activeChallengeTarget.hostname}</strong>, verify domain
                control using the challenge token below:
              </p>

              <div className="qf-challenge-box">
                <div className="qf-challenge-field">
                  <span className="qf-challenge-label">DNS TXT Host:</span>
                  <code className="qf-challenge-code font-mono">
                    _pqc-challenge.{activeChallengeTarget.hostname}
                  </code>
                </div>
                <div className="qf-challenge-field">
                  <span className="qf-challenge-label">TXT Record Value:</span>
                  <div className="qf-token-copy-row">
                    <code className="qf-challenge-code font-mono">
                      quantum-flow-verify={activeChallengeTarget.verification_token}
                    </code>
                    <button
                      type="button"
                      className="qf-btn-icon"
                      onClick={() => {
                        navigator.clipboard.writeText(
                          `quantum-flow-verify=${activeChallengeTarget.verification_token}`
                        );
                      }}
                      title="Copy challenge value"
                    >
                      <Copy size={14} />
                    </button>
                  </div>
                </div>
              </div>

              <p className="qf-modal-hint">
                In local development or test mode, clicking <strong>Verify Domain Scope</strong> will
                complete the validation challenge immediately.
              </p>
            </div>

            <div className="qf-modal-footer">
              <button
                type="button"
                className="qf-btn-secondary"
                onClick={() => setActiveChallengeTarget(null)}
              >
                Close
              </button>
              <button
                type="button"
                className="qf-btn-primary"
                disabled={isVerifying}
                onClick={() => handleVerify(activeChallengeTarget)}
              >
                {isVerifying ? "Verifying..." : "Verify Domain Scope"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
