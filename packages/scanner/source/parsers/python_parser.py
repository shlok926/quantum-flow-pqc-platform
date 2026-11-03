"""Quantum Flow Technologies — Python Cryptographic AST Parser.

Analyzes Python source trees using Python's native AST engine to identify
cryptographic imports, primitives, key generation calls, and cipher configurations.
"""

import ast
import uuid
from pathlib import Path

from packages.scanner.source.models import SourceFinding


class PythonCryptoVisitor(ast.NodeVisitor):
    """AST visitor extracting cryptographic primitives from Python source code."""

    def __init__(self, relative_path: str, source_lines: list[str]) -> None:
        self.relative_path = relative_path
        self.source_lines = source_lines
        self.findings: list[SourceFinding] = []

    def _get_snippet(self, lineno: int) -> str:
        """Extract a single line snippet around lineno, stripping extraneous whitespace."""
        if 1 <= lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1].strip()[:150]
        return ""

    def visit_Import(self, node: ast.Import) -> None:
        """Inspect direct imports."""
        for alias in node.names:
            name = alias.name
            if name in ("hashlib", "hmac"):
                self.findings.append(
                    SourceFinding(
                        finding_id=f"py-imp-{uuid.uuid4().hex[:8]}",
                        file_path=self.relative_path,
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        language="python",
                        primitive="CryptoModule",
                        algorithm=name.upper(),
                        library="standard_library",
                        rule_id="QF-SRC-PY-001",
                        snippet=self._get_snippet(node.lineno),
                        confidence=0.85,
                        classification="IMPORTED",
                    )
                )
            elif (
                name.startswith("cryptography")
                or name.startswith("Crypto")
                or name.startswith("nacl")
            ):
                self.findings.append(
                    SourceFinding(
                        finding_id=f"py-imp-{uuid.uuid4().hex[:8]}",
                        file_path=self.relative_path,
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        language="python",
                        primitive="CryptoLibrary",
                        algorithm="Generic",
                        library=name.split(".")[0],
                        rule_id="QF-SRC-PY-002",
                        snippet=self._get_snippet(node.lineno),
                        confidence=0.9,
                        classification="IMPORTED",
                    )
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Inspect from ... import ... statements."""
        module = node.module or ""
        if "asymmetric.rsa" in module:
            self.findings.append(
                SourceFinding(
                    finding_id=f"py-imp-{uuid.uuid4().hex[:8]}",
                    file_path=self.relative_path,
                    line_number=node.lineno,
                    column_number=node.col_offset,
                    language="python",
                    primitive="RSA",
                    algorithm="RSA",
                    library="cryptography",
                    rule_id="QF-SRC-PY-RSA-IMP",
                    snippet=self._get_snippet(node.lineno),
                    confidence=0.9,
                    classification="IMPORTED",
                )
            )
        elif "asymmetric.ec" in module:
            self.findings.append(
                SourceFinding(
                    finding_id=f"py-imp-{uuid.uuid4().hex[:8]}",
                    file_path=self.relative_path,
                    line_number=node.lineno,
                    column_number=node.col_offset,
                    language="python",
                    primitive="ECC",
                    algorithm="ECDSA",
                    library="cryptography",
                    rule_id="QF-SRC-PY-ECC-IMP",
                    snippet=self._get_snippet(node.lineno),
                    confidence=0.9,
                    classification="IMPORTED",
                )
            )
        elif "ciphers.algorithms" in module or "ciphers" in module:
            self.findings.append(
                SourceFinding(
                    finding_id=f"py-imp-{uuid.uuid4().hex[:8]}",
                    file_path=self.relative_path,
                    line_number=node.lineno,
                    column_number=node.col_offset,
                    language="python",
                    primitive="SymmetricCipher",
                    algorithm="AES",
                    library="cryptography",
                    rule_id="QF-SRC-PY-SYM-IMP",
                    snippet=self._get_snippet(node.lineno),
                    confidence=0.9,
                    classification="IMPORTED",
                )
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Inspect function and method invocations for cryptographic operations."""
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        caller_id = getattr(getattr(node.func, "value", None), "id", "")
        caller_attr = getattr(getattr(node.func, "value", None), "attr", "")
        caller = (caller_id or caller_attr or "").lower()

        # 1. ECC Key Generation
        if func_name == "generate_private_key" and (
            "ec" in caller
            or any(
                "ec" in str(getattr(a, "id", "")).lower()
                or "secp" in str(getattr(a, "attr", "")).lower()
                for a in node.args
            )
        ):
            curve_name = "SECP256R1"
            if node.args:
                arg_attr = getattr(node.args[0], "attr", "")
                if arg_attr:
                    curve_name = arg_attr
            self.findings.append(
                SourceFinding(
                    finding_id=f"py-ec-{uuid.uuid4().hex[:8]}",
                    file_path=self.relative_path,
                    line_number=node.lineno,
                    column_number=node.col_offset,
                    language="python",
                    primitive="ECC",
                    algorithm=f"ECDSA-{curve_name}",
                    library="cryptography",
                    rule_id="QF-SRC-PY-ECC-CALL",
                    snippet=self._get_snippet(node.lineno),
                    confidence=0.98,
                    classification="OBSERVED",
                    parameters={"curve": curve_name, "purpose": "signature_or_key_exchange"},
                )
            )
        # 2. RSA Key Generation
        elif (
            func_name == "generate_private_key"
            or "rsa" in str(getattr(node.func, "attr", "")).lower()
        ):
            key_size = 2048
            for kw in node.keywords:
                if (
                    kw.arg == "key_size"
                    and isinstance(kw.value, ast.Constant)
                    and isinstance(kw.value.value, int | str)
                ):
                    key_size = int(kw.value.value)
            self.findings.append(
                SourceFinding(
                    finding_id=f"py-call-{uuid.uuid4().hex[:8]}",
                    file_path=self.relative_path,
                    line_number=node.lineno,
                    column_number=node.col_offset,
                    language="python",
                    primitive="RSA",
                    algorithm=f"RSA-{key_size}",
                    library="cryptography",
                    rule_id="QF-SRC-PY-RSA-CALL",
                    snippet=self._get_snippet(node.lineno),
                    confidence=0.98,
                    classification="OBSERVED",
                    parameters={"key_size": key_size, "purpose": "key_establishment_or_signature"},
                )
            )

        # 2. Hash algorithms (hashlib.sha256, sha1, md5, etc.)
        if func_name in ("sha256", "sha384", "sha512", "sha1", "md5"):
            algo = func_name.upper()
            if "SHA" in algo and not algo.startswith("SHA-"):
                algo = f"SHA-{algo[3:]}"
            self.findings.append(
                SourceFinding(
                    finding_id=f"py-hash-{uuid.uuid4().hex[:8]}",
                    file_path=self.relative_path,
                    line_number=node.lineno,
                    column_number=node.col_offset,
                    language="python",
                    primitive="Hash",
                    algorithm=algo,
                    library="hashlib",
                    rule_id=f"QF-SRC-PY-{algo}",
                    snippet=self._get_snippet(node.lineno),
                    confidence=0.99,
                    classification="OBSERVED",
                    parameters={"algorithm": algo, "purpose": "integrity_or_digest"},
                )
            )

        # 3. Symmetric Cipher initialization (AES, ChaCha20)
        if func_name in ("AES", "ChaCha20", "TripleDES", "Blowfish"):
            algo = func_name
            self.findings.append(
                SourceFinding(
                    finding_id=f"py-sym-{uuid.uuid4().hex[:8]}",
                    file_path=self.relative_path,
                    line_number=node.lineno,
                    column_number=node.col_offset,
                    language="python",
                    primitive="SymmetricCipher",
                    algorithm=algo,
                    library="cryptography",
                    rule_id=f"QF-SRC-PY-{algo.upper()}",
                    snippet=self._get_snippet(node.lineno),
                    confidence=0.98,
                    classification="OBSERVED",
                    parameters={"algorithm": algo, "purpose": "encryption"},
                )
            )

        # 4. HMAC
        if func_name in ("new", "hmac") and "hmac" in str(getattr(node.func, "value", "")).lower():
            self.findings.append(
                SourceFinding(
                    finding_id=f"py-mac-{uuid.uuid4().hex[:8]}",
                    file_path=self.relative_path,
                    line_number=node.lineno,
                    column_number=node.col_offset,
                    language="python",
                    primitive="HMAC",
                    algorithm="HMAC",
                    library="hmac",
                    rule_id="QF-SRC-PY-HMAC",
                    snippet=self._get_snippet(node.lineno),
                    confidence=0.95,
                    classification="OBSERVED",
                    parameters={"purpose": "message_authentication"},
                )
            )

        self.generic_visit(node)


def parse_python_file(file_path: Path, root_path: Path) -> list[SourceFinding]:
    """Parse a single Python file for cryptographic primitives using AST."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        tree = ast.parse(content, filename=str(file_path))
        rel_path = str(file_path.relative_to(root_path)).replace("\\", "/")
        visitor = PythonCryptoVisitor(relative_path=rel_path, source_lines=lines)
        visitor.visit(tree)
        for f in visitor.findings:
            f.parser_strategy = "ast"
        return visitor.findings
    except Exception:
        return []
