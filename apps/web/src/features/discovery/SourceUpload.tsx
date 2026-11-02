import React, { useState } from "react";
import { UploadCloud, FileCode, CheckCircle2, AlertCircle } from "lucide-react";
import { uploadSourceArchive, importConfiguration } from "../../services/api";

export const SourceUpload: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadResult, setUploadResult] = useState<unknown | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Config import state
  const [configType, setConfigType] = useState<"nginx" | "apache" | "kubernetes">("nginx");
  const [configContent, setConfigContent] = useState<string>("");
  const [configImporting, setConfigImporting] = useState<boolean>(false);
  const [configResult, setConfigResult] = useState<unknown | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      // 50MB ceiling client-side check
      if (selected.size > 50 * 1024 * 1024) {
        setUploadError("Selected archive exceeds the 50MB maximum safety ceiling.");
        setFile(null);
        return;
      }
      setFile(selected);
      setUploadError(null);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setUploadError(null);
    setUploadResult(null);

    try {
      const res = await uploadSourceArchive(file);
      setUploadResult(res);
      setFile(null);
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : "Source archive upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleConfigSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!configContent.trim()) return;

    setConfigImporting(true);
    setConfigError(null);
    setConfigResult(null);

    try {
      const res = await importConfiguration(configType, configContent);
      setConfigResult(res);
      setConfigContent("");
    } catch (err: unknown) {
      setConfigError(err instanceof Error ? err.message : "Configuration import failed");
    } finally {
      setConfigImporting(false);
    }
  };

  return (
    <div className="qf-source-discovery">
      <div className="qf-page-header">
        <div>
          <h2>Static Cryptographic Discovery</h2>
          <p className="qf-text-muted">
            Upload authorized source repositories (.zip/.tar.gz) or import web server & Kubernetes
            TLS configurations for cryptographic discovery and dependency parsing.
          </p>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginTop: "1rem" }}>
        {/* Source Archive Upload Card */}
        <div className="qf-card">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <UploadCloud size={20} />
            <h3>Source Code Archive Upload</h3>
          </div>
          <p className="qf-text-sm qf-text-muted" style={{ margin: "0.5rem 0 0.75rem" }}>
            Scans source code for cryptographic primitives using Python AST analysis, and JS/TS & Java
            lexical pattern matching. Extracts declared dependencies and lockfile records.
          </p>

          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "1rem", fontSize: "0.75rem" }}>
            <span style={{ background: "var(--qf-bg-subtle, #f1f5f9)", padding: "0.2rem 0.5rem", borderRadius: "4px" }}>
              Python: AST Parser
            </span>
            <span style={{ background: "var(--qf-bg-subtle, #f1f5f9)", padding: "0.2rem 0.5rem", borderRadius: "4px" }}>
              JS/TS: Regex / Pattern
            </span>
            <span style={{ background: "var(--qf-bg-subtle, #f1f5f9)", padding: "0.2rem 0.5rem", borderRadius: "4px" }}>
              Java: Regex / Pattern
            </span>
            <span style={{ background: "var(--qf-bg-subtle, #f1f5f9)", padding: "0.2rem 0.5rem", borderRadius: "4px" }}>
              Dependencies: Declared + Lockfiles
            </span>
          </div>

          <form onSubmit={handleUpload}>
            <div className="qf-file-dropzone" style={{ border: "2px dashed var(--qf-border, #cbd5e1)", padding: "1.5rem", textAlign: "center", borderRadius: "8px" }}>
              <input
                type="file"
                accept=".zip,.tar,.gz,.tar.gz"
                onChange={handleFileChange}
                disabled={uploading}
                id="source-file-input"
              />
              <div className="qf-text-xs qf-text-muted" style={{ marginTop: "0.5rem" }}>
                Permitted: .zip, .tar, .tar.gz (Max 50MB expansion budget; private keys rejected)
              </div>
            </div>

            {uploadError && (
              <div className="qf-alert qf-alert-error" style={{ marginTop: "1rem" }}>
                <AlertCircle size={16} /> {uploadError}
              </div>
            )}

            {uploadResult !== null && (
              <div className="qf-alert qf-alert-success" style={{ marginTop: "1rem" }}>
                <CheckCircle2 size={16} /> Discovery completed! Observations ingested into CBOM.
              </div>
            )}

            <button
              type="submit"
              className="qf-btn-primary"
              style={{ marginTop: "1rem", width: "100%" }}
              disabled={!file || uploading}
            >
              {uploading ? "Extracting & Scanning Source..." : "Upload & Analyze Repository"}
            </button>
          </form>
        </div>

        {/* Configuration Import Card */}
        <div className="qf-card">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <FileCode size={20} />
            <h3>TLS Configuration Import</h3>
          </div>
          <p className="qf-text-sm qf-text-muted" style={{ margin: "0.5rem 0 1rem" }}>
            Paste Nginx ssl directives, Apache SSLEngine configs, or Kubernetes Ingress TLS definitions.
            Private key secrets are never stored.
          </p>

          <form onSubmit={handleConfigSubmit}>
            <div style={{ marginBottom: "0.75rem" }}>
              <label className="qf-label">Configuration Type:</label>
              <select
                value={configType}
                onChange={(e) => setConfigType(e.target.value as "nginx" | "apache" | "kubernetes")}
                className="qf-select"
                style={{ width: "100%", marginTop: "0.25rem" }}
              >
                <option value="nginx">Nginx (ssl_protocols, ssl_ciphers)</option>
                <option value="apache">Apache HTTPD (SSLProtocol, SSLCipherSuite)</option>
                <option value="kubernetes">Kubernetes Ingress (spec.tls)</option>
              </select>
            </div>

            <div style={{ marginBottom: "0.75rem" }}>
              <label className="qf-label">Configuration Snippet:</label>
              <textarea
                value={configContent}
                onChange={(e) => setConfigContent(e.target.value)}
                placeholder="Paste configuration text here..."
                rows={6}
                className="qf-input"
                style={{ width: "100%", fontFamily: "monospace", fontSize: "0.85rem", marginTop: "0.25rem" }}
              />
            </div>

            {configError && (
              <div className="qf-alert qf-alert-error" style={{ marginTop: "1rem" }}>
                <AlertCircle size={16} /> {configError}
              </div>
            )}

            {configResult !== null && (
              <div className="qf-alert qf-alert-success" style={{ marginTop: "1rem" }}>
                <CheckCircle2 size={16} /> Configuration parsed and converted to CBOM assets!
              </div>
            )}

            <button
              type="submit"
              className="qf-btn-primary"
              style={{ marginTop: "1rem", width: "100%" }}
              disabled={!configContent.trim() || configImporting}
            >
              {configImporting ? "Parsing Directives..." : "Import Configuration"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
