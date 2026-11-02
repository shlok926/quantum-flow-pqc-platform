"""Quantum Flow Technologies — Deterministic Asset Identity Key Generators.

Ensures idempotent, reproducible asset identity resolution across discovery scans.
"""


def build_certificate_key(fingerprint_sha256: str) -> str:
    """Generate canonical asset key for an X.509 certificate."""
    clean = fingerprint_sha256.lower().replace(":", "").replace(" ", "").strip()
    return f"cert:sha256:{clean}"


def build_endpoint_key(hostname: str, port: int = 443) -> str:
    """Generate canonical asset key for a TLS network endpoint."""
    return f"tls:{hostname.lower().strip()}:{port}"


def build_source_asset_key(file_path: str, primitive: str, line_number: int) -> str:
    """Generate canonical asset key for source code cryptographic primitive usage."""
    clean_path = file_path.replace("\\", "/").strip().lstrip("/")
    return f"code:{clean_path}:{primitive.lower().strip()}:{line_number}"


def build_dependency_key(ecosystem: str, name: str, version: str) -> str:
    """Generate canonical asset key for a third-party software package dependency."""
    clean_name = name.lower().strip()
    clean_ver = version.strip()
    return f"dep:{ecosystem.lower().strip()}:{clean_name}:{clean_ver}"


def build_config_key(file_path: str, directive: str) -> str:
    """Generate canonical asset key for imported cryptographic configuration item."""
    clean_path = file_path.replace("\\", "/").strip().lstrip("/")
    return f"cfg:{clean_path}:{directive.lower().strip()}"
