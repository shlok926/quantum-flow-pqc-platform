import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider } from "../../router";
import { HomePage } from "./HomePage";
import { ScannerPage } from "./ScannerPage";
import { ScanResultsPage } from "./ScanResultsPage";
import { RequestDemoPage } from "./RequestDemoPage";
import * as api from "../../services/api";
import { Scan, Target, Observation } from "../../types";

describe("Public Website & Scanner Suite", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders HomePage with hero, capabilities, and quick scan form", () => {
    render(
      <RouterProvider initialPath="/">
        <HomePage />
      </RouterProvider>
    );

    expect(screen.getByText(/Discover Your Cryptographic Exposure/i)).toBeInTheDocument();
    expect(screen.getByText(/NIST FIPS 203 \/ 204 \/ 205 Standards Alignment/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/e\.g\. example\.com/i)).toBeInTheDocument();
    expect(screen.getByText("1. Cryptographic Discovery")).toBeInTheDocument();
    expect(screen.getByText("2. Cryptographic Inventory")).toBeInTheDocument();
  });

  it("validates domain syntax on ScannerPage before initiating scan", async () => {
    render(
      <RouterProvider initialPath="/scan">
        <ScannerPage />
      </RouterProvider>
    );

    expect(screen.getByText(/Free Quantum Readiness Scanner/i)).toBeInTheDocument();
    const input = screen.getByPlaceholderText(/e\.g\. example\.com or api\.company\.corp/i);
    const scanBtn = screen.getByRole("button", { name: /scan domain/i });

    // Try without input
    await userEvent.click(scanBtn);
    expect(screen.getByText(/Please enter a domain name/i)).toBeInTheDocument();

    // Try with IP literal
    await userEvent.type(input, "192.168.1.1");
    await userEvent.click(scanBtn);
    expect(screen.getByText(/IP literals are prohibited/i)).toBeInTheDocument();

    // Try with invalid single-label domain
    await userEvent.clear(input);
    await userEvent.type(input, "localhost");
    await userEvent.click(scanBtn);
    expect(screen.getByText(/Domain must contain at least two labels/i)).toBeInTheDocument();

    // Valid domain without auth checkbox
    await userEvent.clear(input);
    await userEvent.type(input, "example.com");
    await userEvent.click(scanBtn);
    expect(screen.getByText(/Please check the authorization declaration/i)).toBeInTheDocument();
  });

  it("renders ScanResultsPage with 6 findings cards, exposure map, and scope notice", async () => {
    const mockScan: Scan = {
      id: "scan-pub-001",
      target_id: "tgt-pub-001",
      status: "completed",
      target_ip: "93.184.216.34",
      port: 443,
      collector_version: "1.0.0-sprint1",
      created_at: "2026-11-03T10:00:00Z",
      completed_at: "2026-11-03T10:00:03Z",
    };

    const mockTarget: Target = {
      id: "tgt-pub-001",
      hostname: "example.com",
      environment: "production",
      criticality: "high",
      status: "verified",
      authorisation_status: "confirmed",
      verification_token: "tok-pub-123",
      created_at: "2026-11-03T10:00:00Z",
      updated_at: "2026-11-03T10:00:00Z",
    };

    const mockObservation: Observation = {
      id: "obs-pub-001",
      scan_id: "scan-pub-001",
      target_id: "tgt-pub-001",
      observation_type: "network_tls_endpoint",
      evidence_sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      collector_version: "1.0.0-sprint1",
      observed_at: "2026-11-03T10:00:03Z",
      evidence_payload: {
        endpoint: {
          target_hostname: "example.com",
          target_ip: "93.184.216.34",
          port: 443,
          scan_timestamp: "2026-11-03T10:00:03Z",
          collector_version: "1.0.0-sprint1",
          connection_status: "CONNECTED",
          negotiated_protocol: "TLSv1.3",
          negotiated_cipher_name: "TLS_AES_256_GCM_SHA384",
          alpn_protocol: "h2",
          peer_certificate_chain_length: 2,
        },
        certificate: {
          subject_dn: "CN=example.com, O=Internet Assigned Numbers Authority",
          issuer_dn: "CN=DigiCert Global Root CA",
          serial_number_hex: "010203040506",
          not_valid_before: "2026-01-01T00:00:00Z",
          not_valid_after: "2027-01-01T00:00:00Z",
          is_currently_valid: true,
          san_dns_names: ["example.com", "www.example.com"],
          sha256_fingerprint: "A1B2C3D4E5F67890",
          public_key_algorithm: "RSA",
          key_size_bits: 2048,
          curve_name: null,
        },
      },
    };

    vi.spyOn(api, "getScan").mockResolvedValue(mockScan);
    vi.spyOn(api, "getTarget").mockResolvedValue(mockTarget);
    vi.spyOn(api, "listTargetObservations").mockResolvedValue([mockObservation]);

    render(
      <RouterProvider initialPath="/scan/results/scan-pub-001">
        <ScanResultsPage />
      </RouterProvider>
    );

    await waitFor(() => {
      expect(screen.getAllByText("example.com").length).toBeGreaterThanOrEqual(1);
    });

    // Executive banner quantum signals
    expect(screen.getByText(/SHOR'S ALGORITHM EXPOSURE/i)).toBeInTheDocument();
    expect(screen.getByText(/GROVER'S ALGORITHM POSTURE/i)).toBeInTheDocument();
    expect(screen.getByText(/STORE NOW, DECRYPT LATER/i)).toBeInTheDocument();

    // QVI Risk Score card
    expect(screen.getByText(/Perimeter Quantum Threat Assessment/i)).toBeInTheDocument();
    expect(screen.getByText(/Quantum Vulnerability Index/i)).toBeInTheDocument();
    expect(screen.getByText(/CRITICAL QUANTUM RISK/i)).toBeInTheDocument();

    // 6 Findings Cards
    expect(screen.getByText("TLS Protocol Version")).toBeInTheDocument();
    expect(screen.getByText("Key-Exchange Group")).toBeInTheDocument();
    expect(screen.getByText("Leaf Certificate Public Key")).toBeInTheDocument();
    expect(screen.getByText("Signature Algorithm")).toBeInTheDocument();
    expect(screen.getByText("Bulk Cipher Suite")).toBeInTheDocument();
    expect(screen.getByText("Chain Depth & Validity")).toBeInTheDocument();

    // Scope & Visibility notice
    expect(screen.getByText("What This Public Scan Measured")).toBeInTheDocument();
    expect(screen.getByText("What Was NOT Visible (Beyond Perimeter)")).toBeInTheDocument();

    // Enterprise CTA
    expect(screen.getByText(/Your public TLS scan is only the starting point/i)).toBeInTheDocument();
  });

  it("handles RequestDemoPage submission validation", async () => {
    render(
      <RouterProvider initialPath="/request-demo">
        <RequestDemoPage />
      </RouterProvider>
    );

    expect(screen.getByText(/Request an Enterprise Architecture Demo/i)).toBeInTheDocument();
    const submitBtn = screen.getByRole("button", { name: /submit technical demo request/i });

    // Submit with empty fields
    await userEvent.click(submitBtn);
    expect(screen.getByText(/Full name is required/i)).toBeInTheDocument();

    // Enter fields
    const nameInput = screen.getByPlaceholderText(/e\.g\. Elena Rostova/i);
    const emailInput = screen.getByPlaceholderText(/e\.g\. elena@enterprise\.corp/i);
    const orgInput = screen.getByPlaceholderText(/e\.g\. Acme Financial/i);
    const titleInput = screen.getByPlaceholderText(/e\.g\. CISO \/ Security Architect/i);

    await userEvent.type(nameInput, "Dr. Jane Smith");
    await userEvent.type(emailInput, "jane.smith@enterprise.com");
    await userEvent.type(orgInput, "Acme Financial");
    await userEvent.type(titleInput, "Head of Cryptography");

    await userEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Demo Request Received/i)).toBeInTheDocument();
      expect(screen.getByText(/Acme Financial/i)).toBeInTheDocument();
    });
  });
});
