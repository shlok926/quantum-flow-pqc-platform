"""Quantum Flow Technologies — Dependency and Software Manifest Scanner.

Extracts inventory records from Python (requirements.txt, poetry.lock),
JavaScript/Node (package.json, package-lock.json), and Java (pom.xml) manifests.
"""

import json
import logging
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from packages.scanner.dependencies.models import DependencyItem

logger = logging.getLogger("quantumflow.scanner.dependencies")

# Security limits: skip manifest files larger than 5MB to avoid memory exhaustion
MAX_MANIFEST_BYTES = 5 * 1024 * 1024

# Known cryptographic libraries by ecosystem
KNOWN_CRYPTO_LIBRARIES = {
    "pypi": {
        "cryptography",
        "pycryptodome",
        "pycrypto",
        "pynacl",
        "bcrypt",
        "rsa",
        "ecdsa",
        "paramiko",
        "m2crypto",
        "tls-parser",
    },
    "npm": {
        "crypto-js",
        "jose",
        "bcrypt",
        "bcryptjs",
        "@noble/curves",
        "@noble/hashes",
        "elliptic",
        "node-forge",
        "forge",
        "ursa",
        "tweetnacl",
        "libsodium-wrappers",
    },
    "maven": {
        "bcprov-jdk18on",
        "bcpkix-jdk18on",
        "bcprov-jdk15on",
        "bcpkix-jdk15on",
        "bouncycastle",
        "conscrypt-openjdk-uber",
        "tink",
    },
}


class DependencyScanner:
    """Discovers and parses software dependencies across project trees."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir.resolve()

    def scan(self) -> list[DependencyItem]:
        """Scan root_dir for all recognized manifest files."""
        dependencies: list[DependencyItem] = []
        if not self.root_dir.exists():
            return dependencies

        for current_root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".") and d not in ("node_modules", "venv", ".venv")
            ]

            for file_name in files:
                file_path = Path(current_root) / file_name
                rel_path = str(file_path.relative_to(self.root_dir)).replace("\\", "/")

                # Skip oversized manifest files to protect against DoS
                try:
                    if file_path.stat().st_size > MAX_MANIFEST_BYTES:
                        logger.warning("Skipping oversized manifest file (>5MB): %s", rel_path)
                        continue
                except OSError:
                    continue

                # Skip oversized manifest files to protect against DoS
                try:
                    if file_path.stat().st_size > MAX_MANIFEST_BYTES:
                        logger.warning("Skipping oversized manifest file (>5MB): %s", rel_path)
                        continue
                except OSError:
                    continue

                if file_name in ("requirements.txt", "requirements.lock", "requirements-dev.lock"):
                    dependencies.extend(self._parse_requirements_txt(file_path, rel_path))
                elif file_name == "poetry.lock":
                    dependencies.extend(self._parse_poetry_lock(file_path, rel_path))
                elif file_name == "package.json":
                    dependencies.extend(self._parse_package_json(file_path, rel_path))
                elif file_name == "package-lock.json":
                    dependencies.extend(self._parse_package_lock_json(file_path, rel_path))
                elif file_name == "pom.xml":
                    dependencies.extend(self._parse_pom_xml(file_path, rel_path))

        return dependencies

    def _parse_requirements_txt(self, file_path: Path, rel_path: str) -> list[DependencyItem]:
        items: list[DependencyItem] = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue

                # Match name==version or name>=version
                match = re.match(
                    r"^([a-zA-Z0-9_\-\.]+)\s*(?:==|>=|<=|~=)\s*([a-zA-Z0-9_\-\.]+)", line
                )
                if match:
                    name, version = match.group(1), match.group(2)
                    norm_name = name.lower().replace("_", "-")
                    is_crypto = norm_name in KNOWN_CRYPTO_LIBRARIES["pypi"]
                    items.append(
                        DependencyItem(
                            ecosystem="pypi",
                            name=name,
                            version=version,
                            is_direct=True,
                            manifest_path=rel_path,
                            declaration_type="declared",
                            relationship="development" if "dev" in rel_path.lower() else "runtime",
                            is_known_crypto=is_crypto,
                        )
                    )
        except Exception as e:
            logger.warning("Failed to parse requirements manifest %s: %s", rel_path, e)
        return items

    def _parse_poetry_lock(self, file_path: Path, rel_path: str) -> list[DependencyItem]:
        items: list[DependencyItem] = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            package_blocks = content.split("[[package]]")
            for block in package_blocks[1:]:
                name_match = re.search(r'name\s*=\s*"([^"]+)"', block)
                version_match = re.search(r'version\s*=\s*"([^"]+)"', block)
                if name_match and version_match:
                    name = name_match.group(1)
                    version = version_match.group(1)
                    norm_name = name.lower().replace("_", "-")
                    is_crypto = norm_name in KNOWN_CRYPTO_LIBRARIES["pypi"]
                    items.append(
                        DependencyItem(
                            ecosystem="pypi",
                            name=name,
                            version=version,
                            is_direct=False,
                            manifest_path=rel_path,
                            declaration_type="lockfile_resolved",
                            is_known_crypto=is_crypto,
                        )
                    )
        except Exception as e:
            logger.warning("Failed to parse poetry lockfile %s: %s", rel_path, e)
        return items

    def _parse_package_json(self, file_path: Path, rel_path: str) -> list[DependencyItem]:
        items: list[DependencyItem] = []
        try:
            data = json.loads(file_path.read_text(encoding="utf-8", errors="replace"))
            for rel_type, deps_dict in (
                ("runtime", data.get("dependencies", {})),
                ("development", data.get("devDependencies", {})),
            ):
                if isinstance(deps_dict, dict):
                    for name, ver in deps_dict.items():
                        is_crypto = name.lower() in KNOWN_CRYPTO_LIBRARIES["npm"]
                        items.append(
                            DependencyItem(
                                ecosystem="npm",
                                name=name,
                                version=str(ver).lstrip("^~"),
                                is_direct=True,
                                manifest_path=rel_path,
                                declaration_type="declared",
                                relationship=rel_type,
                                is_known_crypto=is_crypto,
                            )
                        )
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
            logger.warning("Malformed package.json in %s: %s", rel_path, e)
        return items

    def _parse_package_lock_json(self, file_path: Path, rel_path: str) -> list[DependencyItem]:
        items: list[DependencyItem] = []
        try:
            data = json.loads(file_path.read_text(encoding="utf-8", errors="replace"))
            packages = data.get("packages", {})
            for pkg_path, pkg_info in packages.items():
                if not pkg_path:  # root project
                    continue
                name = pkg_info.get("name") or pkg_path.split("node_modules/")[-1]
                version = pkg_info.get("version", "unknown")
                integrity = pkg_info.get("integrity")
                is_crypto = name.lower() in KNOWN_CRYPTO_LIBRARIES["npm"]
                items.append(
                    DependencyItem(
                        ecosystem="npm",
                        name=name,
                        version=version,
                        is_direct="node_modules/" not in pkg_path[13:]
                        if len(pkg_path) > 13
                        else True,
                        manifest_path=rel_path,
                        declaration_type="lockfile_resolved",
                        checksum=integrity,
                        relationship="development" if pkg_info.get("dev") else "runtime",
                        is_known_crypto=is_crypto,
                    )
                )
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
            logger.warning("Malformed package-lock.json in %s: %s", rel_path, e)
        return items

    def _parse_pom_xml(self, file_path: Path, rel_path: str) -> list[DependencyItem]:
        items: list[DependencyItem] = []
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            # Handle XML namespaces dynamically
            ns = ""
            if root.tag.startswith("{"):
                ns = root.tag.split("}")[0] + "}"

            for dep in root.findall(f".//{ns}dependency"):
                group_id_el = dep.find(f"{ns}groupId")
                artifact_id_el = dep.find(f"{ns}artifactId")
                version_el = dep.find(f"{ns}version")
                scope_el = dep.find(f"{ns}scope")

                if artifact_id_el is not None and artifact_id_el.text:
                    artifact_id = artifact_id_el.text.strip()
                    group_id = (
                        group_id_el.text.strip()
                        if group_id_el is not None and group_id_el.text
                        else ""
                    )
                    version = (
                        version_el.text.strip()
                        if version_el is not None and version_el.text
                        else "managed"
                    )
                    scope = (
                        scope_el.text.strip()
                        if scope_el is not None and scope_el.text
                        else "compile"
                    )

                    full_name = f"{group_id}:{artifact_id}" if group_id else artifact_id
                    is_crypto = (
                        artifact_id.lower() in KNOWN_CRYPTO_LIBRARIES["maven"]
                        or "bouncycastle" in group_id.lower()
                    )
                    items.append(
                        DependencyItem(
                            ecosystem="maven",
                            name=full_name,
                            version=version,
                            is_direct=True,
                            manifest_path=rel_path,
                            declaration_type="declared",
                            relationship="development" if scope == "test" else "runtime",
                            is_known_crypto=is_crypto,
                        )
                    )
        except (ET.ParseError, UnicodeDecodeError, OSError) as e:
            logger.warning("Malformed pom.xml in %s: %s", rel_path, e)
        return items
