"""Quantum Flow Technologies — Application Configuration Module.

Loads typed configuration from environment variables with safe development defaults.
"""

from typing import Annotated, Any

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_cors_origins(v: object) -> list[str]:
    """Parse CORS origins from a comma-separated string or list."""
    default_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    if isinstance(v, str):
        v = v.strip()
        if not v:
            return default_origins
        if v.startswith("[") and v.endswith("]"):
            import json

            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                pass
        return [origin.strip() for origin in v.split(",") if origin.strip()]
    if isinstance(v, list):
        return [str(origin).strip() for origin in v if str(origin).strip()]
    return default_origins


CorsOriginsType = Annotated[Any, BeforeValidator(_parse_cors_origins)]


class Settings(BaseSettings):
    """Application settings derived from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application & Environment Metadata
    app_env: str = Field(default="local", description="Runtime environment profile")
    app_name: str = Field(
        default="quantum-flow-pqc-platform", description="Canonical application identifier"
    )
    app_version: str = Field(default="0.1.0", description="SemVer application version")
    api_v1_prefix: str = Field(default="/api/v1", description="Prefix for version 1 API endpoints")
    log_level: str = Field(default="INFO", description="Log level verbosity")

    # Host & Port Binding
    api_host: str = Field(default="127.0.0.1", description="Bind address for the API server")
    api_port: int = Field(default=8000, description="Listening TCP port for the API server")

    # Persistence & Caching
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/quantum_flow_dev",
        description="Async connection URL for PostgreSQL database",
    )
    database_url_sync: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/quantum_flow_dev",
        description="Synchronous connection URL for Alembic migrations and tooling",
    )
    redis_url: str = Field(
        default="redis://127.0.0.1:6379/0",
        description="Connection URL for Redis task broker and caching",
    )
    staging_dir: str = Field(
        default="./staging_data",
        description="Path to staged archive storage volume",
    )
    scratch_dir: str = Field(
        default="./scratch",
        description="Path to isolated worker scratch directory",
    )

    # Security & Access Controls
    cors_origins: CorsOriginsType = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        description="Allowed CORS origin URLs for browser clients",
    )
    scan_allow_private_networks: bool = Field(
        default=False,
        description="Allow scanning RFC 1918 private subnets (Strictly False in production)",
    )
    scan_allowed_ports: list[int] = Field(
        default=[443, 8443],
        description="Permitted TCP ports for network TLS inspection",
    )
    scan_default_timeout_seconds: int = Field(
        default=10, description="Default socket connection timeout in seconds"
    )
    scan_max_timeout_seconds: int = Field(
        default=30, description="Maximum bounded timeout for scan jobs in seconds"
    )

    # Engine & Catalogue Versions
    allow_test_targets_only: bool = Field(
        default=True,
        description="Strict safety flag restricting scans to RFC 5737 / RFC 3849 testnets",
    )
    collector_version: str = Field(
        default="1.0.0-sprint0", description="Collector version identifier stamped on observations"
    )
    risk_ruleset_version: str = Field(
        default="2026.11-draft", description="Ruleset version used for quantum risk evaluation"
    )


settings = Settings()
