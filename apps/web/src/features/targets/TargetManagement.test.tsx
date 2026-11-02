import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TargetManagement } from "./TargetManagement";
import * as api from "../../services/api";
import { Observation, Scan, Target } from "../../types";

describe("TargetManagement Feature", () => {
  const mockTargets: Target[] = [
    {
      id: "tgt-001",
      hostname: "testnet-target.example.org",
      environment: "production",
      criticality: "critical",
      status: "verified",
      authorisation_status: "confirmed",
      verification_token: "tok-abc-123",
      description: "Primary auth portal",
      created_at: "2026-11-02T10:00:00Z",
      updated_at: "2026-11-02T10:00:00Z",
      verified_at: "2026-11-02T10:05:00Z",
    },
    {
      id: "tgt-002",
      hostname: "staging.example.org",
      environment: "staging",
      criticality: "medium",
      status: "pending_verification",
      authorisation_status: "pending",
      verification_token: "tok-xyz-789",
      description: "Staging cluster",
      created_at: "2026-11-02T11:00:00Z",
      updated_at: "2026-11-02T11:00:00Z",
      verified_at: null,
    },
  ];

  const mockObservation: Observation = {
    id: "obs-001",
    scan_id: "scan-001",
    target_id: "tgt-001",
    observation_type: "network_tls_endpoint",
    evidence_sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    collector_version: "1.0.0-sprint1",
    observed_at: "2026-11-02T10:10:00Z",
    evidence_payload: {
      endpoint: {
        target_hostname: "testnet-target.example.org",
        target_ip: "192.0.2.1",
        port: 443,
        scan_timestamp: "2026-11-02T10:10:00Z",
        collector_version: "1.0.0-sprint1",
        connection_status: "CONNECTED",
        negotiated_protocol: "TLSv1.3",
        negotiated_cipher_name: "TLS_AES_256_GCM_SHA384",
        alpn_protocol: "h2",
        peer_certificate_chain_length: 1,
      },
      certificate: {
        subject_dn: "CN=testnet-target.example.org, O=Quantum Flow",
        issuer_dn: "CN=Quantum Flow CA",
        serial_number_hex: "0102030405",
        not_valid_before: "2026-01-01T00:00:00Z",
        not_valid_after: "2027-01-01T00:00:00Z",
        is_currently_valid: true,
        san_dns_names: ["testnet-target.example.org"],
        sha256_fingerprint: "A1B2C3D4E5F67890A1B2C3D4E5F67890A1B2C3D4E5F67890A1B2C3D4E5F67890",
        public_key_algorithm: "RSA",
        key_size_bits: 2048,
        curve_name: null,
      },
    },
  };

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders target inventory table and allows filtering", async () => {
    vi.spyOn(api, "listTargets").mockResolvedValue({
      total: 2,
      items: mockTargets,
    });

    render(<TargetManagement />);

    expect(screen.getByText("Target Discovery & Bounded TLS Inspection")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("testnet-target.example.org")).toBeInTheDocument();
      expect(screen.getByText("staging.example.org")).toBeInTheDocument();
    });

    // Check badges
    expect(screen.getAllByText("Verified").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("Pending Verification").length).toBeGreaterThanOrEqual(2);
  });

  it("enforces client-side validation on domain registration form", async () => {
    vi.spyOn(api, "listTargets").mockResolvedValue({ total: 0, items: [] });

    render(<TargetManagement />);

    const registerBtn = screen.getByRole("button", { name: /register domain target/i });
    await userEvent.click(registerBtn);

    expect(screen.getByText("Register Domain Target for Discovery")).toBeInTheDocument();

    const hostInput = screen.getByLabelText(/fully qualified domain name/i);

    // Invalid scheme
    await userEvent.type(hostInput, "https://invalid.com");
    expect(screen.getByText(/exclude schemes/i)).toBeInTheDocument();

    // Invalid IP literal
    await userEvent.clear(hostInput);
    await userEvent.type(hostInput, "127.0.0.1");
    expect(screen.getByText(/IP literals are prohibited/i)).toBeInTheDocument();

    // Invalid single-label
    await userEvent.clear(hostInput);
    await userEvent.type(hostInput, "localhost");
    expect(screen.getByText(/at least two labels/i)).toBeInTheDocument();
  });

  it("triggers discovery scan and displays TLS evidence record", async () => {
    vi.spyOn(api, "listTargets").mockResolvedValue({
      total: 1,
      items: [mockTargets[0]],
    });

    const mockScan: Scan = {
      id: "scan-001",
      target_id: "tgt-001",
      status: "completed",
      target_ip: "192.0.2.1",
      port: 443,
      collector_version: "1.0.0-sprint1",
      error_code: null,
      error_message: null,
      created_at: "2026-11-02T10:10:00Z",
      completed_at: "2026-11-02T10:10:02Z",
    };

    vi.spyOn(api, "triggerScan").mockResolvedValue(mockScan);
    vi.spyOn(api, "listTargetObservations").mockResolvedValue([mockObservation]);

    render(<TargetManagement />);

    await waitFor(() => {
      expect(screen.getByText("testnet-target.example.org")).toBeInTheDocument();
    });

    const scanBtn = screen.getByRole("button", { name: /scan/i });
    await userEvent.click(scanBtn);

    await waitFor(() => {
      expect(screen.getByText(/Discovery scan completed/i)).toBeInTheDocument();
      expect(screen.getByText("Observation Record —")).toBeInTheDocument();
      expect(screen.getByText("TLSv1.3")).toBeInTheDocument();
      expect(screen.getByText("TLS_AES_256_GCM_SHA384")).toBeInTheDocument();
      expect(screen.getByText("RSA (2048 bits)")).toBeInTheDocument();
    });
  });

  it("displays security alert banner when SSRF guard blocks connection", async () => {
    vi.spyOn(api, "listTargets").mockResolvedValue({
      total: 1,
      items: [mockTargets[0]],
    });

    const mockFailedScan: Scan = {
      id: "scan-002",
      target_id: "tgt-001",
      status: "failed",
      target_ip: "127.0.0.1",
      port: 443,
      collector_version: "1.0.0-sprint1",
      error_code: "SSRF_DESTINATION_REJECTED",
      error_message: "Address 127.0.0.1 belongs to prohibited loopback subnet 127.0.0.0/8",
      created_at: "2026-11-02T10:10:00Z",
      completed_at: "2026-11-02T10:10:01Z",
    };

    vi.spyOn(api, "triggerScan").mockResolvedValue(mockFailedScan);

    render(<TargetManagement />);

    await waitFor(() => {
      expect(screen.getByText("testnet-target.example.org")).toBeInTheDocument();
    });

    const scanBtn = screen.getByRole("button", { name: /scan/i });
    await userEvent.click(scanBtn);

    await waitFor(() => {
      expect(
        screen.getByText(/SSRF Guard \/ Security Engine Intercepted Request:/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/belongs to prohibited loopback subnet/i)
      ).toBeInTheDocument();
    });
  });
});
