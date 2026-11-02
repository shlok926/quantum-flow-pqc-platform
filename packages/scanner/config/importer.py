"""Quantum Flow Technologies — Read-Only Cryptographic Configuration Parser.

Safely parses Nginx TLS directives, Apache SSL directives, and Kubernetes Ingress
manifests. Extracts configured protocols, cipher suites, and cert references without
executing files or accessing private key material.
"""

import re

from packages.scanner.config.models import ConfigFinding


class ConfigImporter:
    """Parses cryptographic configuration files."""

    @staticmethod
    def parse_nginx(content: str, file_path: str = "nginx.conf") -> list[ConfigFinding]:
        """Parse Nginx configuration text for SSL/TLS directives."""
        findings: list[ConfigFinding] = []
        protocols: list[str] = []
        ciphers: list[str] = []
        cert_ref: str | None = None
        key_ref: str | None = None
        unsupported: list[str] = []

        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # ssl_protocols TLSv1.2 TLSv1.3;
            proto_match = re.match(r"^ssl_protocols\s+([^;]+);", line)
            if proto_match:
                protos = proto_match.group(1).split()
                protocols.extend(protos)
                findings.append(
                    ConfigFinding(
                        config_type="nginx",
                        file_path=file_path,
                        line_number=idx,
                        directive="ssl_protocols",
                        raw_value=proto_match.group(1),
                        protocols=protos,
                    )
                )

            # ssl_ciphers HIGH:!aNULL:!MD5;
            cipher_match = re.match(r"^ssl_ciphers\s+['\"]?([^;'\"]+)['\"]?;", line)
            if cipher_match:
                c_str = cipher_match.group(1)
                c_list = [c.strip() for c in c_str.split(":") if c.strip()]
                ciphers.extend(c_list)
                findings.append(
                    ConfigFinding(
                        config_type="nginx",
                        file_path=file_path,
                        line_number=idx,
                        directive="ssl_ciphers",
                        raw_value=c_str,
                        ciphers=c_list,
                    )
                )

            # ssl_certificate /path/to/cert.crt;
            cert_match = re.match(r"^ssl_certificate\s+([^;]+);", line)
            if cert_match:
                cert_ref = cert_match.group(1).strip()
                findings.append(
                    ConfigFinding(
                        config_type="nginx",
                        file_path=file_path,
                        line_number=idx,
                        directive="ssl_certificate",
                        raw_value=cert_ref,
                        certificate_reference=cert_ref,
                    )
                )

            # ssl_certificate_key /path/to/key.key;
            key_match = re.match(r"^ssl_certificate_key\s+([^;]+);", line)
            if key_match:
                key_ref = key_match.group(1).strip()
                findings.append(
                    ConfigFinding(
                        config_type="nginx",
                        file_path=file_path,
                        line_number=idx,
                        directive="ssl_certificate_key",
                        raw_value="[REDACTED_PATH_REFERENCE]",
                        key_reference=key_ref,
                    )
                )

            # Track unknown ssl_ directives
            if line.startswith("ssl_") and not any(
                line.startswith(p)
                for p in (
                    "ssl_protocols",
                    "ssl_ciphers",
                    "ssl_certificate",
                    "ssl_certificate_key",
                    "ssl_session",
                    "ssl_prefer_server_ciphers",
                )
            ):
                unsupported.append(line.split()[0])

        return findings

    @staticmethod
    def parse_apache(content: str, file_path: str = "httpd.conf") -> list[ConfigFinding]:
        """Parse Apache HTTPD configuration for SSL directives."""
        findings: list[ConfigFinding] = []
        lines = content.splitlines()

        for idx, line in enumerate(lines, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # SSLProtocol all -SSLv3 -TLSv1
            proto_match = re.match(r"^SSLProtocol\s+(.+)$", line, re.IGNORECASE)
            if proto_match:
                tokens = proto_match.group(1).split()
                findings.append(
                    ConfigFinding(
                        config_type="apache",
                        file_path=file_path,
                        line_number=idx,
                        directive="SSLProtocol",
                        raw_value=proto_match.group(1),
                        protocols=tokens,
                    )
                )

            # SSLCipherSuite HIGH:!aNULL
            cipher_match = re.match(r"^SSLCipherSuite\s+(.+)$", line, re.IGNORECASE)
            if cipher_match:
                c_str = cipher_match.group(1)
                c_list = [c.strip() for c in c_str.split(":") if c.strip()]
                findings.append(
                    ConfigFinding(
                        config_type="apache",
                        file_path=file_path,
                        line_number=idx,
                        directive="SSLCipherSuite",
                        raw_value=c_str,
                        ciphers=c_list,
                    )
                )

            # SSLCertificateFile /path/to/cert.pem
            cert_match = re.match(r"^SSLCertificateFile\s+(.+)$", line, re.IGNORECASE)
            if cert_match:
                cert_ref = cert_match.group(1).strip()
                findings.append(
                    ConfigFinding(
                        config_type="apache",
                        file_path=file_path,
                        line_number=idx,
                        directive="SSLCertificateFile",
                        raw_value=cert_ref,
                        certificate_reference=cert_ref,
                    )
                )

            # SSLCertificateKeyFile /path/to/key.pem
            key_match = re.match(r"^SSLCertificateKeyFile\s+(.+)$", line, re.IGNORECASE)
            if key_match:
                key_ref = key_match.group(1).strip()
                findings.append(
                    ConfigFinding(
                        config_type="apache",
                        file_path=file_path,
                        line_number=idx,
                        directive="SSLCertificateKeyFile",
                        raw_value="[REDACTED_PATH_REFERENCE]",
                        key_reference=key_ref,
                    )
                )

        return findings

    @staticmethod
    def parse_kubernetes_ingress(
        content: str, file_path: str = "ingress.yaml"
    ) -> list[ConfigFinding]:
        """Parse simple Kubernetes Ingress YAML/JSON text for TLS blocks."""
        findings: list[ConfigFinding] = []
        lines = content.splitlines()

        in_tls = False
        current_hosts: list[str] = []
        secret_name: str | None = None
        start_line = 1

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("tls:"):
                in_tls = True
                start_line = idx
                continue

            if in_tls:
                if stripped.startswith("- hosts:") or stripped.startswith("hosts:"):
                    continue
                elif stripped.startswith("- ") and not stripped.startswith("- secretName:"):
                    host = stripped.lstrip("- ").strip("'\"")
                    current_hosts.append(host)
                elif stripped.startswith("secretName:"):
                    secret_name = stripped.split("secretName:")[-1].strip().strip("'\"")
                elif not line.startswith(" ") and not line.startswith("\t"):
                    # Exited TLS block
                    if current_hosts or secret_name:
                        findings.append(
                            ConfigFinding(
                                config_type="kubernetes",
                                file_path=file_path,
                                line_number=start_line,
                                directive="spec.tls",
                                raw_value=f"hosts={current_hosts}, secretName={secret_name}",
                                certificate_reference=f"k8s-secret:{secret_name}"
                                if secret_name
                                else None,
                            )
                        )
                        current_hosts = []
                        secret_name = None
                    in_tls = False

        if in_tls and (current_hosts or secret_name):
            findings.append(
                ConfigFinding(
                    config_type="kubernetes",
                    file_path=file_path,
                    line_number=start_line,
                    directive="spec.tls",
                    raw_value=f"hosts={current_hosts}, secretName={secret_name}",
                    certificate_reference=f"k8s-secret:{secret_name}" if secret_name else None,
                )
            )

        return findings
