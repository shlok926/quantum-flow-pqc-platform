"""Quantum Flow Technologies — Source & Config Discovery Schemas."""

from typing import Any

from pydantic import BaseModel, Field


class SourceUploadResponse(BaseModel):
    """Result of source archive analysis."""

    archive_name: str
    files_scanned: int
    findings_count: int
    dependencies_count: int
    coverage: dict[str, Any]
    sample_findings: list[dict[str, Any]] = Field(default_factory=list)


class ConfigImportRequest(BaseModel):
    """Raw configuration import payload."""

    config_type: str = Field(..., description="Configuration type: nginx, apache, kubernetes")
    file_path: str = Field(
        default="imported.conf", description="Originating file path or reference"
    )
    content: str = Field(..., description="Configuration text content")


class ConfigImportResponse(BaseModel):
    """Result of configuration import parsing."""

    config_type: str
    file_path: str
    findings_count: int
    assets_created: int
    findings: list[dict[str, Any]]
