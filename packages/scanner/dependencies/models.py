"""Quantum Flow Technologies — Software Dependency Data Models."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class DependencyItem:
    """Represents a discovered third-party software package dependency."""

    ecosystem: str  # pypi, npm, maven
    name: str
    version: str
    is_direct: bool
    manifest_path: str
    declaration_type: str = "declared"  # "declared" (manifest) or "lockfile_resolved" (lockfile)
    checksum: str | None = None
    license: str | None = None
    relationship: str = "runtime"  # runtime, development
    is_known_crypto: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert dependency dataclass to dictionary."""
        return asdict(self)
