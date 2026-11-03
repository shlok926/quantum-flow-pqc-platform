import React, { useEffect, useState } from "react";
import {
  ShieldCheck,
  Upload,
  ArrowRight,
  ArrowLeft,
  FileCheck,
  AlertTriangle,
  FileArchive,
  Radar,
  Code,
  FileCode,
  Package,
} from "lucide-react";
import { Target } from "../../types";
import { listTargets, stageArchiveUpload, createAssessment } from "../../services/api";
import { Button } from "../../components/common/Button";
import { Card } from "../../components/common/Card";
import { Badge } from "../../components/common/Badge";

interface AssessmentWizardProps {
  onCancel: () => void;
  onLaunchSuccess: (assessmentId: string) => void;
}

export const AssessmentWizard: React.FC<AssessmentWizardProps> = ({
  onCancel,
  onLaunchSuccess,
}) => {
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [targets, setTargets] = useState<Target[]>([]);
  const [loadingTargets, setLoadingTargets] = useState<boolean>(true);

  // Form State
  const [title, setTitle] = useState<string>("Quarterly Cryptographic Assessment");
  const [selectedTargetId, setSelectedTargetId] = useState<string>("");
  const [customHostname, setCustomHostname] = useState<string>("");
  const [authConfirmed, setAuthConfirmed] = useState<boolean>(false);

  // Collectors
  const [enableTls, setEnableTls] = useState<boolean>(true);
  const [enableSource, setEnableSource] = useState<boolean>(false);
  const [enableConfig, setEnableConfig] = useState<boolean>(false);
  const [enableDeps, setEnableDeps] = useState<boolean>(false);

  // Staged Upload State
  const [fileToUpload, setFileToUpload] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadToken, setUploadToken] = useState<string | null>(null);
  const [stagedFileInfo, setStagedFileInfo] = useState<{ filename: string; size: number; sha256: string } | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Launching state
  const [launching, setLaunching] = useState<boolean>(false);
  const [launchError, setLaunchError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoadingTargets(true);
      try {
        const res = await listTargets({ limit: 100 });
        setTargets(res.items || []);
        if (res.items && res.items.length > 0) {
          setSelectedTargetId(res.items[0].id);
        }
      } catch {
        // targets list failure tolerated
      } finally {
        setLoadingTargets(false);
      }
    }
    load();
  }, []);

  // Handle Staged Archive Upload
  const handleUploadArchive = async () => {
    if (!fileToUpload) return;
    setUploading(true);
    setUploadError(null);
    setUploadProgress(20);

    try {
      if (fileToUpload.size > 25 * 1024 * 1024) {
        throw new Error("Archive file exceeds 25MB ceiling. Please stage a smaller bundle.");
      }

      setUploadProgress(50);
      const res = await stageArchiveUpload(fileToUpload);
      setUploadProgress(100);
      setUploadToken(res.upload_token);
      setStagedFileInfo({
        filename: res.filename,
        size: res.byte_size,
        sha256: res.sha256,
      });
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : "Failed to stage archive upload");
      setUploadProgress(0);
    } finally {
      setUploading(false);
    }
  };

  // Handle Assessment Launch
  const handleLaunch = async () => {
    setLaunching(true);
    setLaunchError(null);

    const sources: string[] = [];
    if (enableTls) sources.push("network_tls");
    if (enableSource) sources.push("static_source");
    if (enableConfig) sources.push("config_import");
    if (enableDeps) sources.push("dependency_manifest");

    if (sources.length === 0) {
      setLaunchError("Please select at least one discovery source.");
      setLaunching(false);
      return;
    }

    try {
      const payload = {
        title: title.trim(),
        target_id: selectedTargetId || undefined,
        discovery_sources: sources,
        upload_token: uploadToken || undefined,
        input_payload: {
          hostname: customHostname || undefined,
        },
      };

      const res = await createAssessment(payload);
      onLaunchSuccess(res.id);
    } catch (err: unknown) {
      setLaunchError(err instanceof Error ? err.message : "Failed to launch assessment");
      setLaunching(false);
    }
  };

  return (
    <div className="qf-wizard-container">
      {/* Wizard Header */}
      <div>
        <h2 style={{ fontFamily: "var(--font-serif)", fontSize: "1.65rem", margin: 0 }}>
          Launch Cryptographic Assessment
        </h2>
        <p className="qf-view-description">
          Configure discovery collectors, stage source code archives, and initiate quantum risk assessment.
        </p>
      </div>

      {/* Stepper Navigation */}
      <div className="qf-stepper">
        <div className={`qf-step-item ${currentStep === 1 ? "active" : currentStep > 1 ? "completed" : ""}`}>
          <div className="qf-step-circle">1</div>
          <span>Target Scope</span>
        </div>
        <div className="qf-step-divider" />
        <div className={`qf-step-item ${currentStep === 2 ? "active" : currentStep > 2 ? "completed" : ""}`}>
          <div className="qf-step-circle">2</div>
          <span>Collectors</span>
        </div>
        <div className="qf-step-divider" />
        <div className={`qf-step-item ${currentStep === 3 ? "active" : currentStep > 3 ? "completed" : ""}`}>
          <div className="qf-step-circle">3</div>
          <span>Archive Staging</span>
        </div>
        <div className="qf-step-divider" />
        <div className={`qf-step-item ${currentStep === 4 ? "active" : ""}`}>
          <div className="qf-step-circle">4</div>
          <span>Review & Launch</span>
        </div>
      </div>

      {/* Step 1: Target Scope */}
      {currentStep === 1 && (
        <Card>
          <h3 style={{ fontFamily: "var(--font-serif)", fontSize: "1.2rem", marginBottom: "1rem" }}>
            Step 1: Define Assessment Scope & Title
          </h3>

          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.4rem" }}>
                Assessment Title *
              </label>
              <input
                type="text"
                className="qf-form-input"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Production Perimeter TLS & Core App Audit"
                style={{ width: "100%" }}
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.4rem" }}>
                Registered Target Domain
              </label>
              {loadingTargets ? (
                <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Loading targets...</div>
              ) : (
                <select
                  className="qf-form-select"
                  value={selectedTargetId}
                  onChange={(e) => setSelectedTargetId(e.target.value)}
                  style={{ width: "100%" }}
                >
                  <option value="">-- Or enter custom hostname below --</option>
                  {targets.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.hostname} ({t.environment} - {t.criticality})
                    </option>
                  ))}
                </select>
              )}
            </div>

            {!selectedTargetId && (
              <div>
                <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.4rem" }}>
                  Direct Target Hostname
                </label>
                <input
                  type="text"
                  className="qf-form-input"
                  value={customHostname}
                  onChange={(e) => setCustomHostname(e.target.value)}
                  placeholder="e.g. secure.quantumflow.internal"
                  style={{ width: "100%" }}
                />
              </div>
            )}

            <div className="qf-form-checkbox-group">
              <label className="qf-checkbox-label">
                <input
                  type="checkbox"
                  className="qf-checkbox"
                  checked={authConfirmed}
                  onChange={(e) => setAuthConfirmed(e.target.checked)}
                />
                <span>
                  <strong>Explicit Authorization Confirmed:</strong> I hereby certify that our organization owns or has
                  obtained full authorization to discover cryptographic endpoints and telemetry on this target.
                </span>
              </label>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "1rem", marginTop: "2rem" }}>
            <Button variant="secondary" onClick={onCancel}>
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={!title.trim() || !authConfirmed || (!selectedTargetId && !customHostname)}
              onClick={() => setCurrentStep(2)}
              icon={<ArrowRight size={15} />}
            >
              Next: Collectors
            </Button>
          </div>
        </Card>
      )}

      {/* Step 2: Collector Selection */}
      {currentStep === 2 && (
        <Card>
          <h3 style={{ fontFamily: "var(--font-serif)", fontSize: "1.2rem", marginBottom: "1rem" }}>
            Step 2: Select Discovery Collectors
          </h3>
          <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: "1.5rem" }}>
            Select the cryptographic inspection channels to execute. Collectors run concurrently via autonomous background workers.
          </p>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1rem" }}>
            {/* Collector: Network TLS */}
            <div
              style={{
                border: enableTls ? "2px solid var(--olive-primary)" : "1px solid var(--border-color)",
                borderRadius: "8px",
                padding: "1.25rem",
                backgroundColor: enableTls ? "var(--olive-light)" : "#FFFFFF",
                cursor: "pointer",
              }}
              onClick={() => setEnableTls(!enableTls)}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
                <input type="checkbox" checked={enableTls} onChange={() => {}} />
                <Radar size={18} style={{ color: "var(--olive-primary)" }} />
                <h4 style={{ margin: 0, fontSize: "0.95rem" }}>Network TLS Endpoint Discovery</h4>
              </div>
              <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", margin: 0 }}>
                Probes public TLS handshakes, certificate chains, negotiated key exchange groups, and cipher suites.
              </p>
            </div>

            {/* Collector: Static Source Code */}
            <div
              style={{
                border: enableSource ? "2px solid var(--olive-primary)" : "1px solid var(--border-color)",
                borderRadius: "8px",
                padding: "1.25rem",
                backgroundColor: enableSource ? "var(--olive-light)" : "#FFFFFF",
                cursor: "pointer",
              }}
              onClick={() => setEnableSource(!enableSource)}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
                <input type="checkbox" checked={enableSource} onChange={() => {}} />
                <Code size={18} style={{ color: "var(--olive-primary)" }} />
                <h4 style={{ margin: 0, fontSize: "0.95rem" }}>Static Source Code AST Scanner</h4>
              </div>
              <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", margin: 0 }}>
                Analyzes application source code AST for cryptographic API invocations (OpenSSL, WebCrypto, PyCryptodome).
              </p>
            </div>

            {/* Collector: Config Ingestion */}
            <div
              style={{
                border: enableConfig ? "2px solid var(--olive-primary)" : "1px solid var(--border-color)",
                borderRadius: "8px",
                padding: "1.25rem",
                backgroundColor: enableConfig ? "var(--olive-light)" : "#FFFFFF",
                cursor: "pointer",
              }}
              onClick={() => setEnableConfig(!enableConfig)}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
                <input type="checkbox" checked={enableConfig} onChange={() => {}} />
                <FileCode size={18} style={{ color: "var(--olive-primary)" }} />
                <h4 style={{ margin: 0, fontSize: "0.95rem" }}>Server Configuration Ingestion</h4>
              </div>
              <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", margin: 0 }}>
                Parses Nginx, Apache, or Kubernetes ingress configs to identify supported ciphers and SSL protocols.
              </p>
            </div>

            {/* Collector: Dependency Manifests */}
            <div
              style={{
                border: enableDeps ? "2px solid var(--olive-primary)" : "1px solid var(--border-color)",
                borderRadius: "8px",
                padding: "1.25rem",
                backgroundColor: enableDeps ? "var(--olive-light)" : "#FFFFFF",
                cursor: "pointer",
              }}
              onClick={() => setEnableDeps(!enableDeps)}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
                <input type="checkbox" checked={enableDeps} onChange={() => {}} />
                <Package size={18} style={{ color: "var(--olive-primary)" }} />
                <h4 style={{ margin: 0, fontSize: "0.95rem" }}>Dependency Manifest Scanner</h4>
              </div>
              <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", margin: 0 }}>
                Scans package manifests (package.json, requirements.txt, go.mod) for vulnerable cryptographic libraries.
              </p>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", marginTop: "2rem" }}>
            <Button variant="secondary" onClick={() => setCurrentStep(1)} icon={<ArrowLeft size={15} />}>
              Back
            </Button>
            <Button
              variant="primary"
              disabled={!enableTls && !enableSource && !enableConfig && !enableDeps}
              onClick={() => setCurrentStep(3)}
              icon={<ArrowRight size={15} />}
            >
              Next: Archive Staging
            </Button>
          </div>
        </Card>
      )}

      {/* Step 3: Archive Staging */}
      {currentStep === 3 && (
        <Card>
          <h3 style={{ fontFamily: "var(--font-serif)", fontSize: "1.2rem", marginBottom: "0.5rem" }}>
            Step 3: Stage Source Code Archive (Optional)
          </h3>
          <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: "1.5rem" }}>
            If you enabled source code or configuration discovery, stage your archive bundle (`.tar.gz` or `.zip` up to 25MB)
            via the secure PostgreSQL advisory-locked staging facility.
          </p>

          {!uploadToken ? (
            <div>
              <div
                className="qf-dropzone"
                onClick={() => document.getElementById("wizard-file-input")?.click()}
              >
                <FileArchive className="qf-dropzone-icon" />
                <div>
                  <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                    {fileToUpload ? fileToUpload.name : "Choose an archive file or drag & drop"}
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                    Supported: .zip, .tar.gz, .tgz (Maximum 25MB)
                  </div>
                </div>
                <input
                  id="wizard-file-input"
                  type="file"
                  style={{ display: "none" }}
                  accept=".zip,.tar.gz,.tgz,.tar"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setFileToUpload(e.target.files[0]);
                    }
                  }}
                />
              </div>

              {fileToUpload && (
                <div style={{ marginTop: "1rem", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ fontSize: "0.85rem" }}>
                    Selected: <strong>{fileToUpload.name}</strong> ({(fileToUpload.size / (1024 * 1024)).toFixed(2)} MB)
                  </span>
                  <Button
                    variant="primary"
                    size="sm"
                    isLoading={uploading}
                    onClick={handleUploadArchive}
                    icon={<Upload size={14} />}
                  >
                    Upload & Stage Token
                  </Button>
                </div>
              )}

              {uploading && (
                <div className="qf-progress-track">
                  <div className="qf-progress-fill" style={{ width: `${uploadProgress}%` }} />
                </div>
              )}

              {uploadError && (
                <div style={{ marginTop: "1rem", color: "var(--rose-primary)", fontSize: "0.85rem" }}>
                  <AlertTriangle size={15} style={{ display: "inline", marginRight: "0.4rem" }} />
                  {uploadError}
                </div>
              )}
            </div>
          ) : (
            <div
              style={{
                backgroundColor: "var(--olive-light)",
                border: "1px solid var(--olive-border)",
                borderRadius: "8px",
                padding: "1.25rem",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--olive-primary)" }}>
                <FileCheck size={20} />
                <h4 style={{ margin: 0, fontSize: "1rem" }}>Archive Staged Successfully</h4>
              </div>
              <div style={{ marginTop: "0.75rem", fontSize: "0.85rem", display: "flex", flexDirection: "column", gap: "0.3rem" }}>
                <div>Filename: <strong>{stagedFileInfo?.filename}</strong></div>
                <div>Size: <strong>{stagedFileInfo?.size} bytes</strong></div>
                <div>
                  Upload Token: <span className="font-mono">{uploadToken}</span>
                </div>
                <div>
                  SHA-256: <span className="font-mono">{stagedFileInfo?.sha256}</span>
                </div>
              </div>
            </div>
          )}

          <div style={{ display: "flex", justifyContent: "space-between", marginTop: "2rem" }}>
            <Button variant="secondary" onClick={() => setCurrentStep(2)} icon={<ArrowLeft size={15} />}>
              Back
            </Button>
            <Button
              variant="primary"
              onClick={() => setCurrentStep(4)}
              icon={<ArrowRight size={15} />}
            >
              Next: Review & Launch
            </Button>
          </div>
        </Card>
      )}

      {/* Step 4: Review & Launch */}
      {currentStep === 4 && (
        <Card>
          <h3 style={{ fontFamily: "var(--font-serif)", fontSize: "1.2rem", marginBottom: "1rem" }}>
            Step 4: Review Scope & Launch Assessment
          </h3>

          <div style={{ display: "flex", flexDirection: "column", gap: "1rem", backgroundColor: "var(--bg-tertiary)", padding: "1.25rem", borderRadius: "8px" }}>
            <div>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Title:</span>
              <div style={{ fontWeight: 600, fontSize: "1.05rem" }}>{title}</div>
            </div>

            <div>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Target Scope:</span>
              <div className="font-mono" style={{ fontSize: "0.95rem" }}>
                {targets.find((t) => t.id === selectedTargetId)?.hostname || customHostname}
              </div>
            </div>

            <div>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Active Collectors:</span>
              <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.35rem" }}>
                {enableTls && <Badge variant="observed">Network TLS</Badge>}
                {enableSource && <Badge variant="imported">Source AST</Badge>}
                {enableConfig && <Badge variant="imported">Server Config</Badge>}
                {enableDeps && <Badge variant="imported">Dependencies</Badge>}
              </div>
            </div>

            {uploadToken && (
              <div>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Bound Upload Token:</span>
                <div className="font-mono" style={{ fontSize: "0.8rem", color: "var(--olive-primary)" }}>
                  {uploadToken}
                </div>
              </div>
            )}
          </div>

          {launchError && (
            <div style={{ marginTop: "1rem", color: "var(--rose-primary)", fontSize: "0.85rem" }}>
              <AlertTriangle size={15} style={{ display: "inline", marginRight: "0.4rem" }} />
              {launchError}
            </div>
          )}

          <div style={{ display: "flex", justifyContent: "space-between", marginTop: "2rem" }}>
            <Button variant="secondary" onClick={() => setCurrentStep(3)} icon={<ArrowLeft size={15} />}>
              Back
            </Button>
            <Button
              variant="primary"
              size="lg"
              isLoading={launching}
              onClick={handleLaunch}
              icon={<ShieldCheck size={18} />}
            >
              Launch Assessment
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
};

