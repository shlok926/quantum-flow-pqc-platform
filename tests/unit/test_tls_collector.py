"""Unit tests for bounded TLS collector and certificate evidence extraction."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from packages.scanner.safety.resolver import ResolutionResult, SafeDestinationResolver
from packages.scanner.tls.collector import (
    BoundedTLSCollector,
    extract_certificate_evidence,
)


def generate_test_certificate_der() -> bytes:
    """Generate a valid in-memory self-signed X.509 certificate DER representation for testing."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Quantum Flow Technologies"),
            x509.NameAttribute(NameOID.COMMON_NAME, "test.example.com"),
        ]
    )

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC) - timedelta(days=1))
        .not_valid_after(datetime.now(UTC) + timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("test.example.com"),
                    x509.DNSName("alt.example.com"),
                ]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    return cert.public_bytes(serialization.Encoding.DER)


def test_extract_certificate_evidence() -> None:
    """Verify that certificate evidence is extracted accurately without fabrication."""
    der_bytes = generate_test_certificate_der()
    evidence = extract_certificate_evidence(der_bytes)

    assert "test.example.com" in evidence.subject_dn
    assert "Quantum Flow Technologies" in evidence.issuer_dn
    assert len(evidence.serial_number_hex) > 0
    assert evidence.is_currently_valid is True
    assert "test.example.com" in evidence.san_dns_names
    assert "alt.example.com" in evidence.san_dns_names
    assert len(evidence.sha256_fingerprint) == 64
    assert evidence.public_key_algorithm == "RSA"
    assert evidence.public_key_size_bits == 2048
    assert evidence.signature_algorithm == "sha256WithRSAEncryption"


def test_collector_aborts_on_unsafe_destination() -> None:
    """Verify that the collector aborts immediately if resolver rejects destination."""
    mock_resolver = MagicMock(spec=SafeDestinationResolver)
    mock_resolver.resolve_destination.return_value = ResolutionResult(
        original_hostname="blocked.example.com",
        resolved_ips=["10.0.0.1"],
        selected_ip=None,
        resolved_at=datetime.now(UTC),
        is_safe=False,
        rejection_reason="Destination resolves to private RFC 1918 address",
    )

    collector = BoundedTLSCollector(resolver=mock_resolver)
    result = collector.inspect_target("blocked.example.com")

    assert result.success is False
    assert result.error_code == "SSRF_DESTINATION_REJECTED"
    assert "private RFC 1918" in (result.error_message or "")
    assert result.endpoint_evidence is None
    assert result.certificate_evidence is None


def test_collector_handles_timeout() -> None:
    """Verify that socket timeouts are captured as clean structured errors."""
    mock_resolver = MagicMock(spec=SafeDestinationResolver)
    mock_resolver.resolve_destination.return_value = ResolutionResult(
        original_hostname="timeout.example.com",
        resolved_ips=["93.184.216.34"],
        selected_ip="93.184.216.34",
        resolved_at=datetime.now(UTC),
        is_safe=True,
    )
    mock_resolver.revalidate_pinned_ip.return_value = True

    collector = BoundedTLSCollector(resolver=mock_resolver, connect_timeout_seconds=0.1)

    with patch("socket.socket.connect", side_effect=TimeoutError("Connection timed out")):
        result = collector.inspect_target("timeout.example.com")
        assert result.success is False
        assert result.error_code == "CONNECTION_TIMEOUT"
        assert result.pinned_ip == "93.184.216.34"


def test_tls_sni_and_pinned_ip_enforcement() -> None:
    """Verify that TLS handshake uses exact pinned IP for TCP and unmutated hostname for SNI."""
    import ssl

    mock_resolver = MagicMock(spec=SafeDestinationResolver)
    mock_resolver.resolve_destination.return_value = ResolutionResult(
        original_hostname="secure.example.com",
        resolved_ips=["93.184.216.34"],
        selected_ip="93.184.216.34",
        resolved_at=datetime.now(UTC),
        is_safe=True,
    )
    mock_resolver.revalidate_pinned_ip.return_value = True

    collector = BoundedTLSCollector(resolver=mock_resolver)
    test_cert_der = generate_test_certificate_der()

    # Mock SSLSocket
    mock_ssl_sock = MagicMock()
    mock_ssl_sock.version.return_value = "TLSv1.3"
    mock_ssl_sock.cipher.return_value = ("TLS_AES_256_GCM_SHA384", "TLSv1.3", 256)
    mock_ssl_sock.selected_alpn_protocol.return_value = "h2"
    mock_ssl_sock.getpeercert.return_value = test_cert_der

    captured_ssl_ctx: list[ssl.SSLContext] = []

    def mock_wrap_socket(
        sock: object, server_hostname: str | None = None, **kwargs: object
    ) -> MagicMock:
        return mock_ssl_sock

    with (
        patch("socket.socket.connect") as mock_connect,
        patch("ssl.create_default_context") as mock_create_ctx,
    ):
        real_ctx = ssl.create_default_context()
        captured_ssl_ctx.append(real_ctx)
        real_ctx.wrap_socket = MagicMock(side_effect=mock_wrap_socket)  # type: ignore[method-assign]
        mock_create_ctx.return_value = real_ctx

        result = collector.inspect_target("secure.example.com")

        # 1. Assert TCP connection uses pinned IP on port 443
        mock_connect.assert_called_once_with(("93.184.216.34", 443))

        # 2. Assert TLS wrap_socket received the original FQDN hostname as server_hostname (SNI)
        real_ctx.wrap_socket.assert_called_once()
        wrap_kwargs = real_ctx.wrap_socket.call_args.kwargs
        assert wrap_kwargs["server_hostname"] == "secure.example.com"
        assert wrap_kwargs["server_hostname"] != "93.184.216.34"
        assert wrap_kwargs["do_handshake_on_connect"] is True

        # 3. Assert certificate hostname verification remains strictly enabled
        assert real_ctx.check_hostname is True

        # 4. Assert certificate verification mode is strictly CERT_REQUIRED
        assert real_ctx.verify_mode == ssl.CERT_REQUIRED

        assert result.success is True
        assert result.pinned_ip == "93.184.216.34"
        assert result.target_hostname == "secure.example.com"
        assert result.endpoint_evidence is not None
        assert result.endpoint_evidence.negotiated_protocol == "TLSv1.3"
