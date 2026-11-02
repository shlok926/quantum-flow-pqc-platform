"""Quantum Flow Technologies — Java Cryptographic Source Parser.

Analyzes Java source files (.java) using heuristic regex and token pattern matching
(not AST parsing) to identify JCA/JCE (Java Cryptography Architecture) patterns,
BouncyCastle usages, and Cipher/MessageDigest/KeyPairGenerator instances.
"""

import re
import uuid
from pathlib import Path

from packages.scanner.source.models import SourceFinding

JAVA_PATTERNS = [
    # 1. Imports
    (
        re.compile(r"""import\s+(?:java\.security|javax\.crypto|org\.bouncycastle)\.([\w.*]+);"""),
        "CryptoLibrary",
        "JCA_JCE",
        "java.security",
        "QF-SRC-JAVA-IMP",
        "IMPORTED",
        0.90,
    ),
    # 2. KeyPairGenerator (RSA, EC, DiffieHellman)
    (
        re.compile(
            r"""KeyPairGenerator\.getInstance\s*\(\s*["'](RSA|EC|DiffieHellman|DSA)["']""",
            re.IGNORECASE,
        ),
        "AsymmetricKeyGen",
        "Asymmetric",
        "java.security",
        "QF-SRC-JAVA-KEYGEN",
        "OBSERVED",
        0.98,
    ),
    # 3. Cipher.getInstance("AES/...") or ("RSA/...")
    (
        re.compile(r"""Cipher\.getInstance\s*\(\s*["']([^"']+)["']""", re.IGNORECASE),
        "Cipher",
        "Cipher",
        "javax.crypto",
        "QF-SRC-JAVA-CIPHER",
        "OBSERVED",
        0.98,
    ),
    # 4. MessageDigest.getInstance("SHA-256") etc.
    (
        re.compile(
            r"""MessageDigest\.getInstance\s*\(\s*["'](SHA-256|SHA-384|SHA-512|SHA-1|MD5|SHA3-\d+)["']""",
            re.IGNORECASE,
        ),
        "Hash",
        "Hash",
        "java.security",
        "QF-SRC-JAVA-DIGEST",
        "OBSERVED",
        0.99,
    ),
    # 5. Mac.getInstance("HmacSHA256")
    (
        re.compile(r"""Mac\.getInstance\s*\(\s*["']([^"']+)["']""", re.IGNORECASE),
        "HMAC",
        "HMAC",
        "javax.crypto",
        "QF-SRC-JAVA-MAC",
        "OBSERVED",
        0.98,
    ),
    # 6. Signature.getInstance("SHA256withRSA")
    (
        re.compile(r"""Signature\.getInstance\s*\(\s*["']([^"']+)["']""", re.IGNORECASE),
        "Signature",
        "Signature",
        "java.security",
        "QF-SRC-JAVA-SIG",
        "OBSERVED",
        0.98,
    ),
]


def parse_java_file(file_path: Path, root_path: Path) -> list[SourceFinding]:
    """Parse a Java file for cryptographic primitives."""
    findings: list[SourceFinding] = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        rel_path = str(file_path.relative_to(root_path)).replace("\\", "/")

        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith(("//", "/*", "*")):
                continue

            for (
                regex,
                default_prim,
                default_algo,
                library,
                rule_id,
                classification,
                conf,
            ) in JAVA_PATTERNS:
                match = regex.search(line)
                if match:
                    algo = default_algo
                    prim = default_prim
                    matched_val = match.group(1) if match.groups() else ""

                    if prim == "Cipher":
                        if "AES" in matched_val.upper():
                            prim = "AES"
                            algo = matched_val
                        elif "RSA" in matched_val.upper():
                            prim = "RSA"
                            algo = matched_val
                        elif "DES" in matched_val.upper():
                            prim = "DES"
                            algo = matched_val
                    elif prim == "AsymmetricKeyGen":
                        prim = matched_val.upper()
                        algo = matched_val.upper()
                    elif prim in ("Hash", "HMAC", "Signature"):
                        algo = matched_val

                    findings.append(
                        SourceFinding(
                            finding_id=f"java-find-{uuid.uuid4().hex[:8]}",
                            file_path=rel_path,
                            line_number=lineno,
                            column_number=match.start(),
                            language="java",
                            primitive=prim,
                            algorithm=algo,
                            library=library,
                            rule_id=rule_id,
                            snippet=stripped[:150],
                            confidence=conf,
                            classification=classification,
                            parameters={"algorithm": algo, "matched_pattern": matched_val},
                        )
                    )
        return findings
    except Exception:
        return []
