import React, { useCallback, useEffect, useState } from "react";
import { Download, FileSpreadsheet, RefreshCw, Layers } from "lucide-react";
import { CryptographicAsset } from "../../types";
import {
  listAssets,
  getExportCbomUrl,
  getExportAssetsCsvUrl,
} from "../../services/api";

export const AssetExplorer: React.FC = () => {
  const [assets, setAssets] = useState<CryptographicAsset[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>("");

  const loadAssets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listAssets({
        asset_type: filterType || undefined,
        limit: 100,
      });
      setAssets(res.items);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load cryptographic assets");
    } finally {
      setLoading(false);
    }
  }, [filterType]);

  useEffect(() => {
    loadAssets();
  }, [loadAssets]);

  return (
    <div className="qf-asset-explorer">
      <div className="qf-page-header">
        <div>
          <h2>Cryptographic Bill of Materials (CBOM)</h2>
          <p className="qf-text-muted">
            Correlated cryptographic asset inventory across TLS handshakes, source code AST,
            package dependencies, and server configurations.
          </p>
        </div>
        <div className="qf-actions-bar" style={{ display: "flex", gap: "0.5rem" }}>
          <button
            type="button"
            className="qf-btn-secondary"
            onClick={loadAssets}
            disabled={loading}
          >
            <RefreshCw size={16} className={loading ? "qf-spin" : ""} /> Refresh
          </button>
          <a
            href={getExportAssetsCsvUrl()}
            className="qf-btn-secondary"
            download="cbom_inventory.csv"
            style={{ textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "0.25rem" }}
          >
            <FileSpreadsheet size={16} /> Export CSV
          </a>
          <a
            href={getExportCbomUrl()}
            className="qf-btn-primary"
            download="cbom_cyclonedx_1.6.json"
            style={{ textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "0.25rem" }}
          >
            <Download size={16} /> CycloneDX 1.6 JSON
          </a>
        </div>
      </div>

      <div className="qf-filter-row" style={{ margin: "1rem 0", display: "flex", gap: "1rem" }}>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="qf-select"
        >
          <option value="">All Asset Types</option>
          <option value="certificate">Certificates (X.509)</option>
          <option value="endpoint_config">TLS Endpoints</option>
          <option value="algorithm_usage">Source Algorithm Usage</option>
          <option value="library">Library Dependencies</option>
          <option value="protocol_config">Protocol Configurations</option>
        </select>
      </div>

      {error && <div className="qf-alert qf-alert-error">{error}</div>}

      {loading ? (
        <div className="qf-card qf-loading-state">Scanning correlated asset inventory...</div>
      ) : assets.length === 0 ? (
        <div className="qf-card qf-empty-state" style={{ textAlign: "center", padding: "2rem" }}>
          <Layers size={40} className="qf-text-muted" style={{ margin: "0 auto 1rem" }} />
          <h3>No Cryptographic Assets Ingested Yet</h3>
          <p className="qf-text-muted">
            Run a domain discovery scan or upload source archives and configuration files
            to populate the CBOM inventory.
          </p>
        </div>
      ) : (
        <div className="qf-table-container">
          <table className="qf-table">
            <thead>
              <tr>
                <th>Asset Type</th>
                <th>Display Name</th>
                <th>Algorithm / Family</th>
                <th>Purpose</th>
                <th>Classification</th>
                <th>Confidence</th>
                <th>Location Reference</th>
              </tr>
            </thead>
            <tbody>
              {assets.map((a) => (
                <tr key={a.id}>
                  <td>
                    <span className="qf-badge qf-badge-neutral">{a.asset_type}</span>
                  </td>
                  <td>
                    <strong>{a.display_name}</strong>
                    <div className="qf-text-mono qf-text-xs qf-text-muted">{a.asset_key}</div>
                  </td>
                  <td>
                    {a.algorithm_name || a.algorithm_family || "Unspecified"}
                  </td>
                  <td>{a.cryptographic_purpose}</td>
                  <td>
                    <span className={`qf-badge qf-badge-${a.classification.toLowerCase()}`}>
                      {a.classification}
                    </span>
                  </td>
                  <td>{(a.confidence_score * 100).toFixed(0)}%</td>
                  <td className="qf-text-xs qf-text-muted">
                    {a.locator || "Observed in scan"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
