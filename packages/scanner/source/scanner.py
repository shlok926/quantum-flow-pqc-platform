"""Quantum Flow Technologies — Source Code Cryptographic Discovery Scanner.

Coordinates language-specific AST and pattern parsers across Python, JavaScript,
TypeScript, and Java files, generating traceable findings and a coverage accounting report.
"""

import os
from pathlib import Path

from packages.scanner.source.models import SourceFinding, SourceScanCoverage
from packages.scanner.source.parsers.java_parser import parse_java_file
from packages.scanner.source.parsers.js_parser import parse_js_file
from packages.scanner.source.parsers.python_parser import parse_python_file

# Supported file extensions
PYTHON_EXTS = {".py", ".pyw"}
JS_TS_EXTS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
JAVA_EXTS = {".java"}
SUPPORTED_EXTENSIONS = PYTHON_EXTS | JS_TS_EXTS | JAVA_EXTS

# Ignore directories for scanning performance and safety
IGNORED_DIRS = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    "target",
    ".idea",
    ".vscode",
}


class SourceScanner:
    """Orchestrates static analysis of source directories for cryptographic assets."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir.resolve()

    def scan(self) -> tuple[list[SourceFinding], SourceScanCoverage]:
        """Scan all eligible source files under root_dir."""
        findings: list[SourceFinding] = []
        coverage = SourceScanCoverage()

        if not self.root_dir.exists():
            return findings, coverage

        for current_root, dirs, files in os.walk(self.root_dir):
            # Prune ignored directories in-place
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

            for file_name in files:
                coverage.total_files_examined += 1
                file_path = Path(current_root) / file_name
                ext = file_path.suffix.lower()

                if ext not in SUPPORTED_EXTENSIONS:
                    coverage.unsupported_files_count += 1
                    continue

                # File size check (skip files > 5 MB)
                try:
                    size = file_path.stat().st_size
                    if size > 5 * 1024 * 1024:
                        coverage.skipped_files_count += 1
                        coverage.skipped_reasons[str(file_path.relative_to(self.root_dir))] = (
                            "File exceeds 5MB size ceiling"
                        )
                        continue
                except OSError:
                    coverage.failed_files_count += 1
                    continue

                try:
                    file_findings: list[SourceFinding] = []
                    if ext in PYTHON_EXTS:
                        file_findings = parse_python_file(file_path, self.root_dir)
                    elif ext in JS_TS_EXTS:
                        file_findings = parse_js_file(file_path, self.root_dir)
                    elif ext in JAVA_EXTS:
                        file_findings = parse_java_file(file_path, self.root_dir)

                    findings.extend(file_findings)
                    coverage.scanned_files_count += 1
                except Exception as exc:
                    coverage.failed_files_count += 1
                    coverage.skipped_reasons[str(file_path.relative_to(self.root_dir))] = (
                        f"Parser error: {exc}"
                    )

        return findings, coverage
