"""Quantum Flow Technologies — Configuration Importer Unit Tests.

Verifies:
1. Nginx ssl_protocols and ssl_ciphers parsing.
2. Apache SSLProtocol and SSLCipherSuite parsing.
3. Kubernetes Ingress TLS specification parsing.
"""

from packages.scanner.config.importer import ConfigImporter


def test_nginx_config_parsing() -> None:
    """Verify Nginx SSL configuration extraction."""
    content = """
server {
    listen 443 ssl;
    server_name api.enterprise.com;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_certificate /etc/ssl/certs/bundle.crt;
}
"""
    findings = ConfigImporter.parse_nginx(content, "nginx.conf")
    assert len(findings) >= 2

    keys = {f.directive for f in findings}
    assert "ssl_protocols" in keys
    assert "ssl_ciphers" in keys

    ciphers_finding = next(f for f in findings if f.directive == "ssl_ciphers")
    assert "AES256" in ciphers_finding.raw_value


def test_apache_config_parsing() -> None:
    """Verify Apache SSL configuration extraction."""
    content = """
<VirtualHost *:443>
    ServerName secure.example.com
    SSLEngine on
    SSLProtocol all -SSLv3 -TLSv1 -TLSv1.1 +TLSv1.2 +TLSv1.3
    SSLCipherSuite HIGH:!aNULL:!MD5:!3DES
    SSLCertificateFile /path/to/cert.crt
</VirtualHost>
"""
    findings = ConfigImporter.parse_apache(content, "httpd-ssl.conf")
    assert len(findings) >= 2

    keys = {f.directive for f in findings}
    assert "SSLProtocol" in keys
    assert "SSLCipherSuite" in keys


def test_kubernetes_ingress_parsing() -> None:
    """Verify Kubernetes Ingress TLS extraction."""
    content = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: secured-ingress
spec:
  tls:
  - hosts:
      - secure.k8s.local
    secretName: secure-tls-secret
"""
    findings = ConfigImporter.parse_kubernetes_ingress(content, "ingress.yaml")
    assert len(findings) >= 1
    assert findings[0].directive == "spec.tls"
    assert "secure.k8s.local" in findings[0].raw_value
