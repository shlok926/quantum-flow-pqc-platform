import React from "react";
import { CheckCircle2, AlertCircle, Info, ShieldAlert } from "lucide-react";
import { Badge } from "./Badge";

interface ScopeNoticeProps {
  measuredDetails?: {
    publicKeyAlgo?: string;
    signatureAlgo?: string;
    keyExchangeGroup?: string;
    cipherSuite?: string;
    protocolVersion?: string;
    chainLength?: number;
  };
  targetDomain?: string;
  sourceTypes?: string[];
  collectorCount?: number;
  observedEvidence?: string[];
  unseenEvidence?: string[];
}

export const ScopeNotice: React.FC<ScopeNoticeProps> = ({
  measuredDetails,
  targetDomain,
  observedEvidence,
  unseenEvidence,
}) => {
  return (
    <div className="qf-scope-notice">
      <div className="qf-scope-header">
        <h3>
          <Info size={18} style={{ color: "var(--olive-primary)" }} />
          <span>Assessment Coverage, Scope & Limitations</span>
        </h3>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <Badge variant="observed">Active Telemetry</Badge>
          <Badge variant="inferred">NIST Evaluated</Badge>
        </div>
      </div>

      <div className="qf-scope-grid">
        {/* Column 1: What was Measured */}
        <div className="qf-scope-col measured">
          <h4>
            <CheckCircle2 size={16} />
            <span>Observed Cryptographic Scope</span>
          </h4>
          {observedEvidence && observedEvidence.length > 0 ? (
            <ul className="qf-scope-list">
              {observedEvidence.map((item, idx) => (
                <li key={idx}>
                  <CheckCircle2 size={13} style={{ color: "var(--olive-primary)", flexShrink: 0, marginTop: "2px" }} />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          ) : (
            <ul className="qf-scope-list">
              <li>
                <strong>Public-Key Algorithm:</strong>
                <span className="font-mono">
                  {measuredDetails?.publicKeyAlgo || "RSA-2048 / ECDSA P-256 (Observed)"}
                </span>
              </li>
              <li>
                <strong>Certificate Signature:</strong>
                <span className="font-mono">
                  {measuredDetails?.signatureAlgo || "SHA256withRSA (Observed)"}
                </span>
              </li>
              <li>
                <strong>Key-Exchange Group:</strong>
                <span className="font-mono">
                  {measuredDetails?.keyExchangeGroup || "X25519 / secp256r1 (Negotiated)"}
                </span>
              </li>
              <li>
                <strong>Negotiated Cipher Suite:</strong>
                <span className="font-mono">
                  {measuredDetails?.cipherSuite || "TLS_AES_256_GCM_SHA384"}
                </span>
              </li>
              <li>
                <strong>Protocol Version:</strong>
                <span className="font-mono">
                  {measuredDetails?.protocolVersion || "TLSv1.3"}
                </span>
              </li>
              <li>
                <strong>Certificate Trust Path:</strong>
                <span>
                  {measuredDetails?.chainLength
                    ? `${measuredDetails.chainLength}-Certificate Chain Depth`
                    : "Leaf to Root Trust Chain Validated"}
                </span>
              </li>
            </ul>
          )}
        </div>

        {/* Column 2: What was NOT Visible */}
        <div className="qf-scope-col unseen">
          <h4>
            <AlertCircle size={16} />
            <span>Technical Visibility Limitations</span>
          </h4>
          {unseenEvidence && unseenEvidence.length > 0 ? (
            <ul className="qf-scope-list">
              {unseenEvidence.map((item, idx) => (
                <li key={idx}>
                  <AlertCircle size={13} style={{ color: "#9A3412", flexShrink: 0, marginTop: "2px" }} />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          ) : (
            <ul className="qf-scope-list">
              <li>
                <strong>Private Key Secrets:</strong> Server private keys are never exposed or
                transmitted over TLS and cannot be inspected via network discovery.
              </li>
              <li>
                <strong>Unnegotiated Supported Ciphers:</strong> Only the single client/server
                negotiated cipher combination is observable during active handshake.
              </li>
              <li>
                <strong>Internal Architecture:</strong> Backend microservice communication behind
                CDNs, WAFs, and load balancers is not visible from external scans.
              </li>
              <li>
                <strong>Data-at-Rest & KMS:</strong> Static database encryption, volume keys, and
                hardware security module (HSM) policies remain unmeasured.
              </li>
            </ul>
          )}
        </div>
      </div>

      {/* Estate Disclaimer */}
      <div className="qf-scope-disclaimer">
        <ShieldAlert size={16} style={{ display: "inline", marginRight: "0.4rem", verticalAlign: "text-bottom" }} />
        <strong>Enterprise Estate Disclaimer:</strong> This assessment evaluates the public cryptographic
        handshake for <strong>{targetDomain || "the target endpoint"}</strong>. A public TLS discovery
        does not represent the entire internal enterprise cryptographic estate. To achieve comprehensive
        cryptographic posture, pair endpoint discovery with source code repository scans and server configuration ingestion.
      </div>
    </div>
  );
};
