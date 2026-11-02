"""Quantum Flow Technologies — Safe Source Archive Extraction Sandbox.

Enforces strict defense-in-depth security bounds against Zip Slip (path traversal),
Zip Bombs (decompression multiplication), symlink escaping, and resource exhaustion.
"""

import logging
import shutil
import tarfile
import zipfile
from pathlib import Path

logger = logging.getLogger("quantumflow.scanner.archive")

# Security policy constants
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024  # 50 MB total expansion ceiling
MAX_FILE_COUNT = 500  # 500 files maximum
MAX_SINGLE_FILE_BYTES = 5 * 1024 * 1024  # 5 MB maximum per single file

# Secret and key file exclusion policies
EXCLUDED_EXTENSIONS = {
    ".key",
    ".p12",
    ".pfx",
    ".pkcs12",
    ".jks",
    ".keystore",
}
EXCLUDED_FILENAMES = {
    "id_rsa",
    "id_ecdsa",
    "id_ed25519",
    "id_dsa",
    "id_rsa.pub",
    "id_ecdsa.pub",
    "id_ed25519.pub",
}
NESTED_ARCHIVE_EXTENSIONS = {
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".bz2",
    ".xz",
    ".7z",
}
PRIVATE_KEY_MARKERS = [
    b"-----BEGIN PRIVATE KEY-----",
    b"-----BEGIN RSA PRIVATE KEY-----",
    b"-----BEGIN EC PRIVATE KEY-----",
    b"-----BEGIN DSA PRIVATE KEY-----",
    b"-----BEGIN OPENSSH PRIVATE KEY-----",
    b"-----BEGIN ENCRYPTED PRIVATE KEY-----",
]


class ArchiveSecurityError(Exception):
    """Raised when an uploaded archive violates security boundaries."""


def _is_private_key_file(file_path: Path) -> bool:
    """Check if file matches known private key extensions, names, or PEM headers."""
    name_lower = file_path.name.lower()
    suffix_lower = file_path.suffix.lower()

    if suffix_lower in EXCLUDED_EXTENSIONS:
        return True
    if name_lower in EXCLUDED_FILENAMES:
        return True

    # Sniff first 4KB of content for private key headers
    try:
        with open(file_path, "rb") as f:
            header = f.read(4096)
            for marker in PRIVATE_KEY_MARKERS:
                if marker in header:
                    return True
    except OSError:
        pass

    return False


def extract_archive_safely(
    archive_path: Path,
    target_dir: Path,
    max_uncompressed_bytes: int = MAX_UNCOMPRESSED_BYTES,
    max_file_count: int = MAX_FILE_COUNT,
) -> list[Path]:
    """Safely extracts a ZIP or TAR archive into target_dir under strict resource limits.

    Enforces:
    - Path traversal prevention (Zip Slip)
    - Decompression bomb limits (uncompressed bytes + file count)
    - Rejection of symlinks and hardlinks
    - Prevention of nested archive recursion
    - Immediate rejection/exclusion of private keys and secret keystores

    Returns the list of valid extracted file paths.
    """
    extracted_files: list[Path] = []
    total_extracted_bytes = 0
    target_dir = target_dir.resolve()

    if not archive_path.exists():
        raise ArchiveSecurityError(f"Archive file not found: {archive_path}")

    is_zip = zipfile.is_zipfile(archive_path)
    is_tar = tarfile.is_tarfile(archive_path)

    if not is_zip and not is_tar:
        raise ArchiveSecurityError(
            "Unsupported archive format. Only valid ZIP and TAR files are permitted."
        )

    if is_zip:
        with zipfile.ZipFile(archive_path, "r") as zf:
            infolist = zf.infolist()
            if len(infolist) > max_file_count:
                raise ArchiveSecurityError(
                    f"Archive exceeds maximum file count limit ({len(infolist)} > {max_file_count})"
                )

            for member in infolist:
                # Reject directory traversal (Zip Slip)
                normalized_name = member.filename.replace("\\", "/")
                if normalized_name.startswith("/") or ".." in normalized_name.split("/"):
                    raise ArchiveSecurityError(
                        f"Illegal path traversal detected in archive entry: {member.filename}"
                    )

                # Reject symlinks in zip archives
                if (member.external_attr >> 16) & 0o170000 == 0o120000:
                    logger.warning("Skipping symlink in zip archive: %s", member.filename)
                    continue

                # Skip nested archives to prevent recursion bombs
                file_ext = Path(normalized_name).suffix.lower()
                if file_ext in NESTED_ARCHIVE_EXTENSIONS:
                    logger.warning("Skipping nested archive in zip upload: %s", member.filename)
                    continue

                # Reject uncompressed size exceeding limits (Zip Bomb early check)
                if member.file_size > MAX_SINGLE_FILE_BYTES:
                    continue  # Safely skip oversized file

                destination = (target_dir / member.filename).resolve()
                if not destination.is_relative_to(target_dir):
                    raise ArchiveSecurityError(f"Path traversal escape detected: {member.filename}")

                if member.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue

                # Pre-extraction exclusion for private key filename/extension
                dest_name_lower = destination.name.lower()
                dest_suffix_lower = destination.suffix.lower()
                if (
                    dest_suffix_lower in EXCLUDED_EXTENSIONS
                    or dest_name_lower in EXCLUDED_FILENAMES
                ):
                    logger.warning(
                        "Excluding private key / keystore file from extraction: %s", member.filename
                    )
                    continue

                total_extracted_bytes += member.file_size
                if total_extracted_bytes > max_uncompressed_bytes:
                    raise ArchiveSecurityError(
                        "Archive exceeds maximum uncompressed size budget (Zip Bomb protection)"
                    )

                destination.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as source_file, open(destination, "wb") as dest_file:
                    shutil.copyfileobj(source_file, dest_file)

                # Post-extraction content sniffing: reject private keys
                if _is_private_key_file(destination):
                    logger.warning(
                        "Excluding detected private key content from extraction: %s",
                        member.filename,
                    )
                    destination.unlink(missing_ok=True)
                    continue

                extracted_files.append(destination)

    elif is_tar:
        with tarfile.open(archive_path, "r:*") as tf:
            members = tf.getmembers()
            if len(members) > max_file_count:
                raise ArchiveSecurityError(
                    f"Archive exceeds maximum file count limit ({len(members)} > {max_file_count})"
                )

            for tar_member in members:
                # Reject symlinks and hardlinks
                if tar_member.issym() or tar_member.islnk():
                    logger.warning("Skipping symlink/hardlink in tar: %s", tar_member.name)
                    continue

                normalized_name = tar_member.name.replace("\\", "/")
                if normalized_name.startswith("/") or ".." in normalized_name.split("/"):
                    raise ArchiveSecurityError(
                        f"Illegal path traversal in tar member: {tar_member.name}"
                    )

                # Skip nested archives
                file_ext = Path(normalized_name).suffix.lower()
                if file_ext in NESTED_ARCHIVE_EXTENSIONS:
                    logger.warning("Skipping nested archive in tar upload: %s", tar_member.name)
                    continue

                if tar_member.size > MAX_SINGLE_FILE_BYTES:
                    continue

                destination = (target_dir / tar_member.name).resolve()
                if not destination.is_relative_to(target_dir):
                    raise ArchiveSecurityError(f"Path traversal escape detected: {tar_member.name}")

                if tar_member.isdir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue

                # Pre-extraction exclusion for private key filename/extension
                dest_name_lower = destination.name.lower()
                dest_suffix_lower = destination.suffix.lower()
                if (
                    dest_suffix_lower in EXCLUDED_EXTENSIONS
                    or dest_name_lower in EXCLUDED_FILENAMES
                ):
                    logger.warning(
                        "Excluding private key / keystore file from extraction: %s", tar_member.name
                    )
                    continue

                total_extracted_bytes += tar_member.size
                if total_extracted_bytes > max_uncompressed_bytes:
                    raise ArchiveSecurityError(
                        "Archive exceeds maximum uncompressed size budget (Tar Bomb protection)"
                    )

                destination.parent.mkdir(parents=True, exist_ok=True)
                tar_source_file = tf.extractfile(tar_member)
                if tar_source_file is not None:
                    with open(destination, "wb") as dest_file:
                        shutil.copyfileobj(tar_source_file, dest_file)

                    # Post-extraction content sniffing: reject private keys
                    if _is_private_key_file(destination):
                        logger.warning(
                            "Excluding detected private key content from extraction: %s",
                            tar_member.name,
                        )
                        destination.unlink(missing_ok=True)
                        continue

                    extracted_files.append(destination)

    return extracted_files
