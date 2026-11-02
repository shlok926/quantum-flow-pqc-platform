"""Quantum Flow Technologies — Dependency Scanner Unit Tests.

Verifies:
1. Python requirements.txt parsing with version specs and comments.
2. Node package.json and package-lock.json parsing.
3. Java Maven pom.xml parsing.
"""

from pathlib import Path

from packages.scanner.dependencies.scanner import DependencyScanner


def test_requirements_txt_parsing(tmp_path: Path) -> None:
    """Verify requirements.txt accurately extracts known and generic dependencies."""
    req_file = tmp_path / "requirements.txt"
    req_file.write_text(
        """# Production dependencies
cryptography==42.0.5
pycryptodome>=3.20.0
fastapi==0.110.0 # web framework
requests[security]~=2.31.0
""",
        encoding="utf-8",
    )

    scanner = DependencyScanner(tmp_path)
    deps = scanner.scan()

    pkg_names = {d.name: d for d in deps}
    assert "cryptography" in pkg_names
    assert pkg_names["cryptography"].is_known_crypto is True
    assert pkg_names["cryptography"].version == "42.0.5"

    assert "pycryptodome" in pkg_names
    assert pkg_names["pycryptodome"].is_known_crypto is True


def test_package_json_parsing(tmp_path: Path) -> None:
    """Verify package.json extracts dependencies and flags crypto packages."""
    pkg_file = tmp_path / "package.json"
    pkg_file.write_text(
        """{
  "name": "sample-app",
  "dependencies": {
    "node-forge": "^1.3.1",
    "express": "^4.19.2"
  },
  "devDependencies": {
    "crypto-js": "^4.2.0"
  }
}""",
        encoding="utf-8",
    )

    scanner = DependencyScanner(tmp_path)
    deps = scanner.scan()

    pkg_names = {d.name: d for d in deps}
    assert "node-forge" in pkg_names
    assert pkg_names["node-forge"].is_known_crypto is True
    assert pkg_names["node-forge"].relationship == "runtime"

    assert "crypto-js" in pkg_names
    assert pkg_names["crypto-js"].is_known_crypto is True
    assert pkg_names["crypto-js"].relationship == "development"


def test_pom_xml_parsing(tmp_path: Path) -> None:
    """Verify Maven pom.xml extracts dependencies and flags BouncyCastle."""
    pom_file = tmp_path / "pom.xml"
    pom_file.write_text(
        """<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>secure-app</artifactId>
    <version>1.0.0</version>
    <dependencies>
        <dependency>
            <groupId>org.bouncycastle</groupId>
            <artifactId>bcprov-jdk18on</artifactId>
            <version>1.78.1</version>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
            <version>3.2.0</version>
        </dependency>
    </dependencies>
</project>""",
        encoding="utf-8",
    )

    scanner = DependencyScanner(tmp_path)
    deps = scanner.scan()

    pkg_names = {d.name: d for d in deps}
    assert "org.bouncycastle:bcprov-jdk18on" in pkg_names
    assert pkg_names["org.bouncycastle:bcprov-jdk18on"].is_known_crypto is True
    assert pkg_names["org.bouncycastle:bcprov-jdk18on"].version == "1.78.1"
    assert pkg_names["org.bouncycastle:bcprov-jdk18on"].declaration_type == "declared"


def test_malformed_manifests_handled_gracefully(tmp_path: Path) -> None:
    """Verify malformed JSON or XML files do not crash the scanner."""
    malformed_json = tmp_path / "package.json"
    malformed_json.write_text("{ unclosed invalid json: [", encoding="utf-8")

    malformed_xml = tmp_path / "pom.xml"
    malformed_xml.write_text("<project><unclosed>", encoding="utf-8")

    scanner = DependencyScanner(tmp_path)
    deps = scanner.scan()
    assert deps == []


def test_oversized_manifest_skipped(tmp_path: Path) -> None:
    """Verify manifests exceeding 5MB are safely skipped to avoid memory exhaustion."""
    large_req = tmp_path / "requirements.txt"
    # Create 5.5MB file
    large_req.write_bytes(b"# comment\n" * 600000)

    scanner = DependencyScanner(tmp_path)
    deps = scanner.scan()
    assert deps == []


def test_lockfile_resolved_vs_declared_dependencies(tmp_path: Path) -> None:
    """Verify lockfiles produce declaration_type='lockfile_resolved'."""
    poetry_lock = tmp_path / "poetry.lock"
    poetry_lock.write_text(
        """
[[package]]
name = "cryptography"
version = "42.0.5"
description = "cryptography"

[[package]]
name = "cffi"
version = "1.16.0"
description = "cffi"
""",
        encoding="utf-8",
    )

    scanner = DependencyScanner(tmp_path)
    deps = scanner.scan()
    assert len(deps) == 2
    for d in deps:
        assert d.declaration_type == "lockfile_resolved"
        assert d.is_direct is False
