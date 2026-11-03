"""Quantum Flow Technologies — Bounded TLS Handshake Collector.

Performs non-destructive, bounded TLS 1.2 / TLS 1.3 handshake inspection on port 443
using pinned, pre-validated destination IP addresses and strict SNI/hostname verification.
"""

import contextlib
import dataclasses
import socket
import ssl
from datetime import UTC, datetime

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import dsa, ec, ed448, ed25519, rsa

from packages.scanner.safety.resolver import SafeDestinationResolver


@dataclasses.dataclass(frozen=True)
class TLSEndpointEvidence:
    """Observable facts from the negotiated TLS transport connection."""

    target_hostname: str
    target_ip: str
    port: int
    scan_timestamp: datetime
    collector_version: str
    connection_status: str
    negotiated_protocol: str | None
    negotiated_cipher_name: str | None
    negotiated_cipher_bits: int | None
    negotiated_alpn: str | None
    key_exchange_group: str | None
    key_exchange_status: str


@dataclasses.dataclass(frozen=True)
class CertificateEvidence:
    """Observable facts from the peer X.509 leaf certificate."""

    subject_dn: str
    issuer_dn: str
    serial_number_hex: str
    valid_from: datetime
    valid_to: datetime
    is_currently_valid: bool
    san_dns_names: list[str]
    sha256_fingerprint: str
    public_key_algorithm: str
    public_key_size_bits: int | None
    elliptic_curve_name: str | None
    signature_algorithm: str


@dataclasses.dataclass(frozen=True)
class TLSCollectionResult:
    """Consolidated result returned by the bounded TLS collector."""

    success: bool
    target_hostname: str
    pinned_ip: str | None
    endpoint_evidence: TLSEndpointEvidence | None
    certificate_evidence: CertificateEvidence | None
    error_code: str | None = None
    error_message: str | None = None


def extract_certificate_evidence(cert_der: bytes) -> CertificateEvidence:
    """Parse raw X.509 certificate DER bytes using cryptography library."""
    cert = x509.load_der_x509_certificate(cert_der)
    now = datetime.now(UTC)

    # Subject and Issuer DNs
    subject_dn = cert.subject.rfc4514_string()
    issuer_dn = cert.issuer.rfc4514_string()
    serial_hex = f"{cert.serial_number:X}"

    # Validity
    valid_from = cert.not_valid_before_utc
    valid_to = cert.not_valid_after_utc
    is_valid = valid_from <= now <= valid_to

    # Subject Alternative Names (SANs)
    san_names: list[str] = []
    try:
        san_ext = cert.extensions.get_extension_for_oid(x509.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
        san_val = san_ext.value
        if isinstance(san_val, x509.SubjectAlternativeName):
            san_names = list(san_val.get_values_for_type(x509.DNSName))
    except x509.ExtensionNotFound:
        pass

    # SHA-256 Fingerprint
    fingerprint_sha256 = cert.fingerprint(hashes.SHA256()).hex().upper()

    # Public Key Parameters
    pub_key = cert.public_key()
    pub_algo = "Unknown"
    key_bits: int | None = None
    curve_name: str | None = None

    if isinstance(pub_key, rsa.RSAPublicKey):
        pub_algo = "RSA"
        key_bits = pub_key.key_size
    elif isinstance(pub_key, ec.EllipticCurvePublicKey):
        pub_algo = "EC"
        key_bits = pub_key.key_size
        curve_name = pub_key.curve.name
    elif isinstance(pub_key, ed25519.Ed25519PublicKey):
        pub_algo = "Ed25519"
        key_bits = 256
    elif isinstance(pub_key, ed448.Ed448PublicKey):
        pub_algo = "Ed448"
        key_bits = 448
    elif isinstance(pub_key, dsa.DSAPublicKey):
        pub_algo = "DSA"
        key_bits = pub_key.key_size

    # Signature Algorithm
    sig_algo = cert.signature_algorithm_oid._name

    return CertificateEvidence(
        subject_dn=subject_dn,
        issuer_dn=issuer_dn,
        serial_number_hex=serial_hex,
        valid_from=valid_from,
        valid_to=valid_to,
        is_currently_valid=is_valid,
        san_dns_names=san_names,
        sha256_fingerprint=fingerprint_sha256,
        public_key_algorithm=pub_algo,
        public_key_size_bits=key_bits,
        elliptic_curve_name=curve_name,
        signature_algorithm=sig_algo,
    )


class BoundedTLSCollector:
    """Executes safe, non-destructive, bounded TLS handshakes on port 443."""

    def __init__(
        self,
        resolver: SafeDestinationResolver,
        collector_version: str = "1.0.0",
        connect_timeout_seconds: float = 8.0,
        allow_unverified_certificates: bool = False,
    ) -> None:
        self.resolver = resolver
        self.collector_version = collector_version
        self.connect_timeout_seconds = connect_timeout_seconds
        self.allow_unverified_certificates = allow_unverified_certificates

    def inspect_target(self, hostname: str) -> TLSCollectionResult:
        """Execute destination-validated TLS inspection against hostname on port 443."""
        # 1. Resolve and validate destination (SSRF & Rebinding defense)
        resolution = self.resolver.resolve_destination(hostname)
        if not resolution.is_safe or not resolution.selected_ip:
            return TLSCollectionResult(
                success=False,
                target_hostname=hostname,
                pinned_ip=None,
                endpoint_evidence=None,
                certificate_evidence=None,
                error_code="SSRF_DESTINATION_REJECTED",
                error_message=resolution.rejection_reason
                or "Destination rejected by safety policy",
            )

        pinned_ip = resolution.selected_ip

        # 2. Re-verify the pinned IP immediately before socket creation
        if not self.resolver.revalidate_pinned_ip(pinned_ip):
            return TLSCollectionResult(
                success=False,
                target_hostname=hostname,
                pinned_ip=pinned_ip,
                endpoint_evidence=None,
                certificate_evidence=None,
                error_code="PINNED_IP_REVALIDATION_FAILED",
                error_message="Destination IP failed pre-connection re-validation",
            )

        # 3. Create strict SSL context with certificate and hostname verification enabled
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = True
        ssl_ctx.verify_mode = ssl.CERT_REQUIRED

        # Request HTTP/2 and HTTP/1.1 ALPN if available
        with contextlib.suppress(NotImplementedError, AttributeError):
            ssl_ctx.set_alpn_protocols(["h2", "http/1.1"])

        raw_sock: socket.socket | None = None
        ssl_sock: ssl.SSLSocket | None = None
        scan_time = datetime.now(UTC)

        try:
            # 4. Open TCP socket directly to pinned IP address on port 443
            family = socket.AF_INET6 if ":" in pinned_ip else socket.AF_INET
            raw_sock = socket.socket(family, socket.SOCK_STREAM)
            raw_sock.settimeout(self.connect_timeout_seconds)

            raw_sock.connect((pinned_ip, 443))

            # 5. Wrap socket with TLS; SNI and hostname check use the original verified hostname
            ssl_sock = ssl_ctx.wrap_socket(
                raw_sock,
                server_hostname=hostname,
                do_handshake_on_connect=True,
            )

            # 6. Extract negotiated connection properties
            negotiated_proto = ssl_sock.version()
            cipher_info = ssl_sock.cipher()
            cipher_name = cipher_info[0] if cipher_info else None
            cipher_bits = cipher_info[2] if cipher_info else None
            selected_alpn = ssl_sock.selected_alpn_protocol()

            # Key exchange group: in standard library Python ssl, negotiated key exchange group
            # (e.g. X25519, secp256r1) is not reliably exposed on the SSLSocket.
            # Honest provenance rule: mark as unobserved rather than guessing from certificate.
            key_exchange_group = None
            key_exchange_status = "unobserved"

            endpoint_ev = TLSEndpointEvidence(
                target_hostname=hostname,
                target_ip=pinned_ip,
                port=443,
                scan_timestamp=scan_time,
                collector_version=self.collector_version,
                connection_status="connected",
                negotiated_protocol=negotiated_proto,
                negotiated_cipher_name=cipher_name,
                negotiated_cipher_bits=cipher_bits,
                negotiated_alpn=selected_alpn,
                key_exchange_group=key_exchange_group,
                key_exchange_status=key_exchange_status,
            )

            # 7. Extract peer certificate
            der_cert = ssl_sock.getpeercert(binary_form=True)
            if not der_cert:
                return TLSCollectionResult(
                    success=False,
                    target_hostname=hostname,
                    pinned_ip=pinned_ip,
                    endpoint_evidence=endpoint_ev,
                    certificate_evidence=None,
                    error_code="PEER_CERTIFICATE_UNAVAILABLE",
                    error_message="TLS handshake completed but peer certificate was not returned",
                )

            cert_ev = extract_certificate_evidence(der_cert)

            return TLSCollectionResult(
                success=True,
                target_hostname=hostname,
                pinned_ip=pinned_ip,
                endpoint_evidence=endpoint_ev,
                certificate_evidence=cert_ev,
            )

        except ssl.SSLCertVerificationError as exc:
            if self.allow_unverified_certificates:
                with contextlib.suppress(Exception):
                    fallback_ctx = ssl.create_default_context()
                    fallback_ctx.check_hostname = False
                    fallback_ctx.verify_mode = ssl.CERT_NONE
                    fallback_sock = socket.socket(family, socket.SOCK_STREAM)
                    fallback_sock.settimeout(self.connect_timeout_seconds)
                    fallback_sock.connect((pinned_ip, 443))
                    ssl_fallback = fallback_ctx.wrap_socket(
                        fallback_sock,
                        server_hostname=hostname,
                        do_handshake_on_connect=True,
                    )
                    proto = ssl_fallback.version()
                    c_info = ssl_fallback.cipher()
                    der = ssl_fallback.getpeercert(binary_form=True)
                    if der:
                        cert_ev = extract_certificate_evidence(der)
                        endpoint_ev = TLSEndpointEvidence(
                            target_hostname=hostname,
                            target_ip=pinned_ip,
                            port=443,
                            scan_timestamp=scan_time,
                            collector_version=self.collector_version,
                            connection_status="connected_unverified_cert",
                            negotiated_protocol=proto,
                            negotiated_cipher_name=c_info[0] if c_info else None,
                            negotiated_cipher_bits=c_info[2] if c_info else None,
                            negotiated_alpn=ssl_fallback.selected_alpn_protocol(),
                            key_exchange_group=None,
                            key_exchange_status="unobserved",
                        )
                        return TLSCollectionResult(
                            success=True,
                            target_hostname=hostname,
                            pinned_ip=pinned_ip,
                            endpoint_evidence=endpoint_ev,
                            certificate_evidence=cert_ev,
                        )

            return TLSCollectionResult(
                success=False,
                target_hostname=hostname,
                pinned_ip=pinned_ip,
                endpoint_evidence=None,
                certificate_evidence=None,
                error_code="TLS_CERT_VERIFICATION_FAILED",
                error_message=f"Certificate verification failed: {exc.verify_message}",
            )
        except ssl.SSLError as exc:
            return TLSCollectionResult(
                success=False,
                target_hostname=hostname,
                pinned_ip=pinned_ip,
                endpoint_evidence=None,
                certificate_evidence=None,
                error_code="TLS_HANDSHAKE_FAILED",
                error_message=f"TLS handshake failed: {exc.strerror or exc}",
            )
        except TimeoutError:
            return TLSCollectionResult(
                success=False,
                target_hostname=hostname,
                pinned_ip=pinned_ip,
                endpoint_evidence=None,
                certificate_evidence=None,
                error_code="CONNECTION_TIMEOUT",
                error_message=f"Connection timed out after {self.connect_timeout_seconds}s",
            )
        except OSError as exc:
            return TLSCollectionResult(
                success=False,
                target_hostname=hostname,
                pinned_ip=pinned_ip,
                endpoint_evidence=None,
                certificate_evidence=None,
                error_code="NETWORK_CONNECTION_ERROR",
                error_message=f"TCP connection failed to {pinned_ip}:443: {exc.strerror or exc}",
            )
        finally:
            if ssl_sock is not None:
                with contextlib.suppress(Exception):
                    ssl_sock.close()
            elif raw_sock is not None:
                with contextlib.suppress(Exception):
                    raw_sock.close()
