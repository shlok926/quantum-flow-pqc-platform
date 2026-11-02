"""Quantum Flow Technologies — Safe Archive Extractor Unit Tests.

Verifies:
1. Normal clean zip extraction.
2. Zip Slip directory traversal rejection ('../' and absolute paths).
3. Decompression bomb rejection (file count and uncompressed byte budget).
4. Symlink rejection in tar archives.
"""

import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from packages.scanner.source.archive import ArchiveSecurityError, extract_archive_safely


def test_safe_zip_extraction(tmp_path: Path) -> None:
    """Verify normal valid ZIP extraction succeeds within temporary directory."""
    zip_path = tmp_path / "valid.zip"
    target_dir = tmp_path / "extracted"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("src/main.py", "print('hello world')\n")
        zf.writestr("README.md", "# Valid Repo\n")

    extracted = extract_archive_safely(zip_path, target_dir)
    assert len(extracted) == 2
    assert (target_dir / "src/main.py").exists()
    assert (target_dir / "README.md").exists()


def test_zip_slip_traversal_rejected(tmp_path: Path) -> None:
    """Verify Zip Slip path traversal attempts are detected and rejected."""
    zip_path = tmp_path / "malicious.zip"
    target_dir = tmp_path / "extracted"

    with zipfile.ZipFile(zip_path, "w") as zf:
        # Attempt traversal entry
        zf.writestr("../evil.txt", "malicious payload")

    with pytest.raises(ArchiveSecurityError, match="Illegal path traversal|escape detected"):
        extract_archive_safely(zip_path, target_dir)


def test_zip_file_count_bomb_rejected(tmp_path: Path) -> None:
    """Verify archives exceeding maximum file count budget are rejected."""
    zip_path = tmp_path / "many_files.zip"
    target_dir = tmp_path / "extracted"

    with zipfile.ZipFile(zip_path, "w") as zf:
        for i in range(15):
            zf.writestr(f"file_{i}.txt", "test")

    with pytest.raises(ArchiveSecurityError, match="maximum file count limit"):
        extract_archive_safely(zip_path, target_dir, max_file_count=10)


def test_zip_size_bomb_rejected(tmp_path: Path) -> None:
    """Verify archives exceeding uncompressed byte budget are rejected."""
    zip_path = tmp_path / "bomb.zip"
    target_dir = tmp_path / "extracted"

    with zipfile.ZipFile(zip_path, "w") as zf:
        # 2KB payload with max budget 1KB
        zf.writestr("large.txt", "A" * 2048)

    with pytest.raises(ArchiveSecurityError, match="maximum uncompressed size budget"):
        extract_archive_safely(zip_path, target_dir, max_uncompressed_bytes=1024)


def test_tar_symlink_ignored(tmp_path: Path) -> None:
    """Verify symlink entries in tar archives are ignored and not extracted."""
    tar_path = tmp_path / "symlink.tar"
    target_dir = tmp_path / "extracted"

    with tarfile.open(tar_path, "w") as tf:
        # Add normal file
        data = b"normal content"
        ti = tarfile.TarInfo("safe.txt")
        ti.size = len(data)
        tf.addfile(ti, io.BytesIO(data))

        # Add symlink pointing outside
        sym_ti = tarfile.TarInfo("link_to_etc")
        sym_ti.type = tarfile.SYMTYPE
        sym_ti.linkname = "/etc/passwd"
        tf.addfile(sym_ti)

    extracted = extract_archive_safely(tar_path, target_dir)
    assert len(extracted) == 1
    assert (target_dir / "safe.txt").exists()
    assert not (target_dir / "link_to_etc").exists()


def test_private_key_files_excluded_from_archive(tmp_path: Path) -> None:
    """Verify private key and keystore files (.key, .p12, .jks, id_rsa) are excluded."""
    zip_path = tmp_path / "mixed_keys.zip"
    target_dir = tmp_path / "extracted_keys"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("app/server.py", "import ssl\n")
        zf.writestr("keys/server.key", "PRIVATE KEY PLACEHOLDER")
        zf.writestr("certs/client.p12", "PKCS12 BYTES")
        zf.writestr("keystore.jks", "JAVA KEYSTORE")
        zf.writestr(".ssh/id_rsa", "OPENSSH PRIVATE KEY")

    extracted = extract_archive_safely(zip_path, target_dir)
    extracted_names = [p.name for p in extracted]

    assert "server.py" in extracted_names
    assert "server.key" not in extracted_names
    assert "client.p12" not in extracted_names
    assert "keystore.jks" not in extracted_names
    assert "id_rsa" not in extracted_names
    assert not (target_dir / "keys/server.key").exists()


def test_private_key_content_sniffing_excluded(tmp_path: Path) -> None:
    """Verify PEM files containing private key headers are unlinked and excluded."""
    zip_path = tmp_path / "pem_sniff.zip"
    target_dir = tmp_path / "extracted_pem"

    private_pem = (
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0Y3...\n-----END RSA PRIVATE KEY-----\n"
    )
    public_pem = (
        "-----BEGIN CERTIFICATE-----\nMIIDXTCCAkWgAwIBAgIJAP...\n-----END CERTIFICATE-----\n"
    )

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("certs/public.crt", public_pem)
        zf.writestr("certs/secret.pem", private_pem)

    extracted = extract_archive_safely(zip_path, target_dir)
    extracted_names = [p.name for p in extracted]

    assert "public.crt" in extracted_names
    assert "secret.pem" not in extracted_names
    assert not (target_dir / "certs/secret.pem").exists()


def test_nested_archive_skipped(tmp_path: Path) -> None:
    """Verify nested archives (.zip, .tar.gz) inside uploads are skipped to prevent recursion."""
    zip_path = tmp_path / "outer.zip"
    target_dir = tmp_path / "extracted_outer"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("code.py", "print('hello')\n")
        zf.writestr("nested.zip", "PK...")
        zf.writestr("bundle.tar.gz", "tar bytes...")

    extracted = extract_archive_safely(zip_path, target_dir)
    extracted_names = [p.name for p in extracted]

    assert "code.py" in extracted_names
    assert "nested.zip" not in extracted_names
    assert "bundle.tar.gz" not in extracted_names


def test_private_key_files_excluded_from_archive(tmp_path: Path) -> None:
    """Verify private key and keystore files (.key, .p12, .jks, id_rsa) are excluded."""
    zip_path = tmp_path / "mixed_keys.zip"
    target_dir = tmp_path / "extracted_keys"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("app/server.py", "import ssl\n")
        zf.writestr("keys/server.key", "PRIVATE KEY PLACEHOLDER")
        zf.writestr("certs/client.p12", "PKCS12 BYTES")
        zf.writestr("keystore.jks", "JAVA KEYSTORE")
        zf.writestr(".ssh/id_rsa", "OPENSSH PRIVATE KEY")

    extracted = extract_archive_safely(zip_path, target_dir)
    extracted_names = [p.name for p in extracted]

    assert "server.py" in extracted_names
    assert "server.key" not in extracted_names
    assert "client.p12" not in extracted_names
    assert "keystore.jks" not in extracted_names
    assert "id_rsa" not in extracted_names
    assert not (target_dir / "keys/server.key").exists()


def test_private_key_content_sniffing_excluded(tmp_path: Path) -> None:
    """Verify PEM files containing private key headers are unlinked and excluded."""
    zip_path = tmp_path / "pem_sniff.zip"
    target_dir = tmp_path / "extracted_pem"

    private_pem = (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEA0Y3...\n"
        "-----END RSA PRIVATE KEY-----\n"
    )
    public_pem = (
        "-----BEGIN CERTIFICATE-----\n"
        "MIIDXTCCAkWgAwIBAgIJAP...\n"
        "-----END CERTIFICATE-----\n"
    )

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("certs/public.crt", public_pem)
        zf.writestr("certs/secret.pem", private_pem)

    extracted = extract_archive_safely(zip_path, target_dir)
    extracted_names = [p.name for p in extracted]

    assert "public.crt" in extracted_names
    assert "secret.pem" not in extracted_names
    assert not (target_dir / "certs/secret.pem").exists()


def test_nested_archive_skipped(tmp_path: Path) -> None:
    """Verify nested archives (.zip, .tar.gz) inside uploads are skipped to prevent recursion."""
    zip_path = tmp_path / "outer.zip"
    target_dir = tmp_path / "extracted_outer"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("code.py", "print('hello')\n")
        zf.writestr("nested.zip", "PK...")
        zf.writestr("bundle.tar.gz", "tar bytes...")

    extracted = extract_archive_safely(zip_path, target_dir)
    extracted_names = [p.name for p in extracted]

    assert "code.py" in extracted_names
    assert "nested.zip" not in extracted_names
    assert "bundle.tar.gz" not in extracted_names

