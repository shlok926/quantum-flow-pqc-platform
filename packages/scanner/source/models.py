"""Quantum Flow Technologies — Source Finding and Coverage Data Models."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SourceFinding:
    """Represents a discovered cryptographic primitive or pattern in source code."""

    finding_id: str
    file_path: str
    line_number: int
    column_number: int | None
    language: str
    primitive: str
    algorithm: str
    library: str
    rule_id: str
    snippet: str
    confidence: float
    classification: str  # OBSERVED, INFERRED, IMPORTED, UNKNOWN
    parameters: dict[str, Any] = field(default_factory=dict)
    parser_strategy: str = "pattern_matching"  # "ast" or "pattern_matching"

    def to_dict(self) -> dict[str, Any]:
        """Convert finding dataclass to dictionary."""
        return asdict(self)


@dataclass
class SourceScanCoverage:
    """Coverage accounting report for static source analysis."""

    total_files_examined: int = 0
    scanned_files_count: int = 0
    skipped_files_count: int = 0
    unsupported_files_count: int = 0
    failed_files_count: int = 0
    skipped_reasons: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert coverage report to dictionary."""
        return asdict(self)
