"""Quantum Flow Technologies — Cryptographic Configuration Data Models."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ConfigFinding:
    """Represents an imported cryptographic configuration finding."""

    config_type: str  # nginx, apache, kubernetes
    file_path: str
    line_number: int | None
    directive: str
    raw_value: str
    protocols: list[str] = field(default_factory=list)
    ciphers: list[str] = field(default_factory=list)
    certificate_reference: str | None = None
    key_reference: str | None = None  # Reference / file path only, NEVER secret bytes
    unsupported_directives: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert finding dataclass to dictionary."""
        return asdict(self)
