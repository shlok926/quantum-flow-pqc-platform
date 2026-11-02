"""Tests for typed application configuration and environment parsing."""

import pytest
from pydantic import ValidationError

from services.api.app.core.config import Settings, _parse_cors_origins


def test_default_settings_instantiation() -> None:
    """Verify that default settings instantiate with expected safe defaults."""
    s = Settings()
    assert s.app_env in {"local", "test"}
    assert s.app_name == "quantum-flow-pqc-platform"
    assert s.api_port == 8000
    assert s.scan_allow_private_networks is False
    assert 443 in s.scan_allowed_ports
    assert s.collector_version.startswith("1.0.0")


def test_parse_cors_origins_json_list() -> None:
    """Verify parsing CORS origins from a JSON-formatted string."""
    raw = '["http://localhost:3000", "https://app.example.com"]'
    parsed = _parse_cors_origins(raw)
    assert parsed == ["http://localhost:3000", "https://app.example.com"]


def test_parse_cors_origins_comma_separated() -> None:
    """Verify parsing CORS origins from a comma-separated list."""
    raw = "http://localhost:3000, https://app.example.com"
    parsed = _parse_cors_origins(raw)
    assert parsed == ["http://localhost:3000", "https://app.example.com"]


def test_parse_cors_origins_empty_fallback() -> None:
    """Verify fallback when an empty or invalid origin value is provided."""
    parsed = _parse_cors_origins("")
    assert len(parsed) > 0
    assert "http://localhost:5173" in parsed


def test_invalid_port_type_handling() -> None:
    """Verify that invalid typed values raise validation errors."""
    with pytest.raises(ValidationError):
        Settings(api_port="not-a-port")  # type: ignore[arg-type]
