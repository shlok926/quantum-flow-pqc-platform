"""Quantum Flow Technologies — JavaScript / TypeScript Cryptographic Parser.

Analyzes JavaScript, TypeScript, JSX, and TSX source files using heuristic regex
and lexical pattern matching (not AST parsing) to identify Node.js and WebCrypto
API usages, cryptographic imports, and cipher initializations.
"""

import re
import uuid
from pathlib import Path

from packages.scanner.source.models import SourceFinding

PATTERNS = [
    # 1. Imports
    (
        re.compile(
            r"""(?:require\(|import\s+.*from\s+)['"](node:crypto|crypto|crypto-js|bcrypt|jose)['"]"""
        ),
        "CryptoLibrary",
        "Generic",
        "node:crypto",
        "QF-SRC-JS-IMP",
        "IMPORTED",
        0.90,
    ),
    # 2. RSA KeyGen
    (
        re.compile(
            r"""generateKeyPair\s*\(\s*['"]rsa['"](?:[^)]*modulusLength:\s*(\d+))?""", re.IGNORECASE
        ),
        "RSA",
        "RSA",
        "node:crypto",
        "QF-SRC-JS-RSA",
        "OBSERVED",
        0.98,
    ),
    # 3. WebCrypto RSA
    (
        re.compile(r"""(?:RSASSA-PKCS1-v1_5|RSA-PSS|RSA-OAEP)"""),
        "RSA",
        "RSA",
        "WebCrypto",
        "QF-SRC-JS-WEBCRYPTO-RSA",
        "OBSERVED",
        0.95,
    ),
    # 4. WebCrypto ECDSA / ECDH
    (
        re.compile(r"""(?:ECDSA|ECDH).*?['"](?:P-256|P-384|P-521)['"]""", re.DOTALL),
        "ECC",
        "ECDSA",
        "WebCrypto",
        "QF-SRC-JS-WEBCRYPTO-ECC",
        "OBSERVED",
        0.95,
    ),
    # 5. createCipheriv (AES)
    (
        re.compile(r"""createCipheriv\s*\(\s*['"](aes-\d+-[a-z]+)['"]""", re.IGNORECASE),
        "SymmetricCipher",
        "AES",
        "node:crypto",
        "QF-SRC-JS-AES",
        "OBSERVED",
        0.98,
    ),
    # 6. createHash (SHA256, SHA512, SHA1, MD5)
    (
        re.compile(r"""createHash\s*\(\s*['"](sha256|sha384|sha512|sha1|md5)['"]""", re.IGNORECASE),
        "Hash",
        "Hash",
        "node:crypto",
        "QF-SRC-JS-HASH",
        "OBSERVED",
        0.98,
    ),
]


def parse_js_file(file_path: Path, root_path: Path) -> list[SourceFinding]:
    """Parse a JavaScript or TypeScript file for cryptographic primitives."""
    findings: list[SourceFinding] = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        rel_path = str(file_path.relative_to(root_path)).replace("\\", "/")

        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith(("//", "/*", "*")):
                continue

            for regex, primitive, default_algo, library, rule_id, classification, conf in PATTERNS:
                match = regex.search(line)
                if match:
                    algo = default_algo
                    if (
                        primitive == "Hash"
                        and match.groups()
                        and match.group(1)
                        or primitive == "SymmetricCipher"
                        and match.groups()
                        and match.group(1)
                    ):
                        algo = match.group(1).upper()
                    elif primitive == "RSA" and match.groups() and match.group(1):
                        algo = f"RSA-{match.group(1)}"

                    findings.append(
                        SourceFinding(
                            finding_id=f"js-find-{uuid.uuid4().hex[:8]}",
                            file_path=rel_path,
                            line_number=lineno,
                            column_number=match.start(),
                            language="javascript"
                            if file_path.suffix in (".js", ".jsx")
                            else "typescript",
                            primitive=primitive,
                            algorithm=algo,
                            library=library,
                            rule_id=rule_id,
                            snippet=stripped[:150],
                            confidence=conf,
                            classification=classification,
                            parameters={"algorithm": algo},
                        )
                    )
        return findings
    except Exception:
        return []
