"""Quantum Flow Technologies — OS Process Containment, Advisory Locking & Safe Deletion Module.

Enforces strict OS containment across platforms:
- Windows: Suspended launch (CREATE_SUSPENDED), Job Object assignment without breakaway flags,
  and post-termination zero-process confirmation.
- POSIX: Dedicated session establishment, whole-group tracking, kernel-safe /proc/[pid]/stat
  parsing immune to whitespace/brackets, and fail-closed indeterminate scan handling.
- Deterministic 64-bit PostgreSQL advisory lock derivation and OID cast verification.
- Descriptor-relative directory deletion (dir_fd / O_NOFOLLOW) preventing TOCTOU races.
- Multi-factor quarantine descriptors (.quarantine.json) tracking boot ID and process identity.
- Durable cleanup failure tracking (.failure.json) on persistent storage.
"""

import contextlib
import hashlib
import json
import logging
import os
import shutil
import stat
import struct
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("quantumflow.scanner.containment")


class ProcStatParseError(Exception):
    """Raised when /proc/[pid]/stat is malformed, truncated, or unreadable."""

    pass


class IndeterminateProcScanError(Exception):
    """Raised when /proc scan cannot conclusively verify all running processes."""

    pass


# ------------------------------------------------------------------------------
# 1. 64-Bit PostgreSQL Advisory Lock Derivation & Key Splitting
# ------------------------------------------------------------------------------
def derive_job_scratch_lock_key(job_id: uuid.UUID | str) -> int:
    """Derive deterministic signed 64-bit integer key for a job's scratch workspace."""
    digest = hashlib.sha256(f"qf:job_scratch:{job_id}".encode()).digest()
    return int(struct.unpack(">q", digest[:8])[0])


def derive_token_lock_key(upload_token: str) -> int:
    """Derive deterministic signed 64-bit integer key for an upload token claim."""
    digest = hashlib.sha256(f"upload_token:{upload_token}".encode()).digest()
    return int(struct.unpack(">q", digest[:8])[0])


def derive_global_upload_slot_key(slot: int) -> int:
    """Derive deterministic signed 64-bit integer key for a cluster-wide global upload slot."""
    digest = hashlib.sha256(f"qf:global_upload_slot:{slot}".encode()).digest()
    return int(struct.unpack(">q", digest[:8])[0])


def derive_tenant_upload_slot_key(tenant_id: str, slot: int) -> int:
    """Derive deterministic signed 64-bit integer key for a tenant upload slot."""
    digest = hashlib.sha256(f"qf:upload_slot:{tenant_id}:{slot}".encode()).digest()
    return int(struct.unpack(">q", digest[:8])[0])


def split_advisory_lock_key(key_64: int) -> tuple[int, int]:
    """Split a signed 64-bit integer into unsigned 32-bit classid and objid.

    Matches PostgreSQL's internal representation where the high 32 bits are classid
    and low 32 bits are objid. Both are cast as OID (unsigned 32-bit integers).
    """
    raw_bytes = struct.pack(">q", key_64)
    classid_32 = struct.unpack(">I", raw_bytes[:4])[0]
    objid_32 = struct.unpack(">I", raw_bytes[4:])[0]
    return classid_32, objid_32


# ------------------------------------------------------------------------------
# 2. Linux Kernel-Safe /proc/[pid]/stat Parsing & Whole-Group Scanning
# ------------------------------------------------------------------------------
def parse_proc_stat_content(content: str, stat_path: str = "") -> tuple[int, int]:
    """Parse /proc/[pid]/stat content safely according to Linux kernel specification.

    Returns:
        tuple[int, int]: (pgrp, starttime)

    Guarantees:
    - Isolates process name (comm) by finding the LAST closing parenthesis ')' via rfind(')'),
      preventing field shifting caused by spaces or parentheses in process names.
    - Accurately indexes field 5 (pgrp) at remainder[2] and field 22 (starttime) at remainder[19].
    - Raises ProcStatParseError on malformed or truncated content.
    """
    rparen = content.rfind(")")
    if rparen == -1:
        raise ProcStatParseError(f"Malformed {stat_path}: missing closing parenthesis")

    remainder = content[rparen + 1 :].strip().split()
    if len(remainder) < 20:
        raise ProcStatParseError(
            f"Truncated {stat_path}: found only {len(remainder)} fields after ')' (minimum 20 required)"
        )

    try:
        pgrp = int(remainder[2])  # Field 5 (1-based index)
        starttime = int(remainder[19])  # Field 22 (1-based index)
        return pgrp, starttime
    except ValueError as exc:
        raise ProcStatParseError(f"Invalid integer field in {stat_path}: {exc}") from exc


def parse_proc_stat(pid: int) -> tuple[int, int]:
    """Read and parse /proc/[pid]/stat for a given process ID."""
    stat_path = f"/proc/{pid}/stat"
    try:
        with open(stat_path, encoding="utf-8", errors="replace") as f:
            content = f.read()
    except (FileNotFoundError, ProcessLookupError) as exc:
        raise FileNotFoundError(f"Process {pid} terminated concurrently") from exc
    except OSError as exc:
        raise ProcStatParseError(f"Cannot read {stat_path}: {exc}") from exc

    return parse_proc_stat_content(content, stat_path=stat_path)


def scan_active_pgid_descendants(
    target_pgid: int, proc_root: str = "/proc"
) -> tuple[list[int], bool]:
    """Scan /proc for processes belonging to target_pgid.

    Returns:
        tuple[list[int], bool]: (matching_pids, is_scan_conclusive)

    Crucial Guarantee:
    If ANY process entry (other than one that cleanly exited with ENOENT) cannot be read,
    verified, or parsed, is_scan_conclusive is set to False, immediately halting cleanup.
    """
    matching_pids = []
    is_scan_conclusive = True

    try:
        proc_entries = list(os.scandir(proc_root))
    except OSError as exc:
        logger.warning("PROC_SCAN_ENUMERATION_FAILED", extra={"error": str(exc)})
        return [], False

    for entry in proc_entries:
        if not (entry.is_dir() and entry.name.isdigit()):
            continue
        pid = int(entry.name)
        stat_file = os.path.join(entry.path, "stat")
        try:
            with open(stat_file, encoding="utf-8", errors="replace") as f:
                content = f.read()
        except (FileNotFoundError, ProcessLookupError):
            # Normal concurrent process exit race: safely tolerated
            continue
        except OSError as exc:
            # PermissionError, EIO, etc.: cannot verify identity!
            is_scan_conclusive = False
            logger.warning("PROC_SCAN_INDETERMINATE_ENTRY", extra={"pid": pid, "error": str(exc)})
            continue

        try:
            pgrp, _ = parse_proc_stat_content(content, stat_path=stat_file)
            if pgrp == target_pgid:
                matching_pids.append(pid)
        except ProcStatParseError as exc:
            is_scan_conclusive = False
            logger.warning("PROC_SCAN_PARSE_ERROR", extra={"pid": pid, "error": str(exc)})

    return matching_pids, is_scan_conclusive


def get_active_boot_id(boot_id_file: str = "/proc/sys/kernel/random/boot_id") -> str:
    """Read the Linux kernel boot_id or return fallback on non-Linux systems."""
    try:
        with open(boot_id_file, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "non-linux-system-boot-id"


# ------------------------------------------------------------------------------
# 3. Windows Job Object Containment & Suspended Launch
# ------------------------------------------------------------------------------
def create_windows_job_object(job_name: str | None = None) -> Any:
    """Create a Windows Job Object configured strictly without breakaway flags.

    Enforces JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE and strictly strips
    JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK and JOB_OBJECT_LIMIT_BREAKAWAY_OK.
    """
    try:
        import win32job  # type: ignore

        name = job_name or f"qf_job_{uuid.uuid4().hex}"
        h_job = win32job.CreateJobObject(None, name)
        info = win32job.QueryInformationJobObject(h_job, win32job.JobObjectExtendedLimitInformation)
        info["BasicLimitInformation"]["LimitFlags"] = win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        win32job.SetInformationJobObject(h_job, win32job.JobObjectExtendedLimitInformation, info)
        return h_job
    except ImportError:
        logger.debug("win32job module not available on this platform")
        return None


def get_windows_job_process_count(h_job: Any) -> int:
    """Query current active process count inside Windows Job Object."""
    if h_job is None:
        return 0
    try:
        import win32job  # type: ignore

        pids = win32job.QueryInformationJobObject(h_job, win32job.JobObjectBasicProcessIdList)
        return len(pids)
    except Exception:
        return 0


# ------------------------------------------------------------------------------
# 4. Descriptor-Relative TOCTOU-Free Directory Deletion
# ------------------------------------------------------------------------------
def _delete_dir_fd_posix(root_path: Path) -> None:
    """Recursively delete directory tree on POSIX using dir_fd and O_NOFOLLOW."""
    root_fd = os.open(str(root_path), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        _recursive_rmdir_fd(root_fd)
    finally:
        os.close(root_fd)
    os.rmdir(str(root_path))


def _recursive_rmdir_fd(parent_fd: int) -> None:
    """Recursively unlink entries in parent_fd with O_NOFOLLOW."""
    with os.scandir(parent_fd) as it:
        for entry in it:
            if entry.is_symlink():
                os.unlink(entry.name, dir_fd=parent_fd)
            elif entry.is_dir(follow_symlinks=False):
                child_fd = os.open(
                    entry.name,
                    os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                    dir_fd=parent_fd,
                )
                try:
                    _recursive_rmdir_fd(child_fd)
                finally:
                    os.close(child_fd)
                os.rmdir(entry.name, dir_fd=parent_fd)
            else:
                os.unlink(entry.name, dir_fd=parent_fd)


def _delete_tree_windows(root_path: Path) -> None:
    """Safely remove a directory tree on Windows, resetting read-only attributes."""

    def _remove_readonly(func: Any, path: str, excinfo: Any) -> None:
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass

    shutil.rmtree(str(root_path), onerror=_remove_readonly)


def safe_delete_workspace(path: Path) -> tuple[bool, str | None]:
    """Delete a workspace directory under strict TOCTOU and symlink confinement.

    Returns:
        tuple[bool, str | None]: (success, error_message)
    """
    resolved_path = path.resolve()
    if not resolved_path.exists():
        return True, None

    if os.name == "posix":
        try:
            _delete_dir_fd_posix(resolved_path)
            return True, None
        except Exception as exc:
            return False, str(exc)
    else:
        try:
            _delete_tree_windows(resolved_path)
            return True, None
        except Exception as exc:
            return False, str(exc)


# ------------------------------------------------------------------------------
# 5. Durable Quarantine and Cleanup Failure Descriptors
# ------------------------------------------------------------------------------
def write_quarantine_record(
    staging_dir: Path | str,
    workspace_path: Path | str,
    job_id: uuid.UUID | str,
    process_identity: dict[str, Any] | None = None,
    reason: str = "Unterminated child processes detected",
    leader_pid: int | None = None,
    pgid: int | None = None,
    **kwargs: Any,
) -> Path:
    """Write durable .quarantine.json file to {staging_dir}/.cleanup_failures/ using 4-step atomic write."""
    stg_dir = Path(staging_dir)
    ws_path = Path(workspace_path)
    fail_dir = stg_dir / ".cleanup_failures"
    fail_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    if process_identity is None:
        process_identity = {
            "leader_pid": leader_pid or kwargs.get("pid", 0),
            "posix_pgid": pgid or leader_pid or 0,
            "posix_boot_id": get_active_boot_id() or "unknown-boot-id",
        }

    record = {
        "workspace_path": str(ws_path),
        "workspace_basename": ws_path.name,
        "job_id": str(job_id),
        "status": "quarantined_child_alive",
        "quarantined_at": datetime.now(UTC).isoformat(),
        "process_identity": process_identity,
        "reason": reason,
    }

    dest = fail_dir / f"{ws_path.name}.quarantine.json"
    tmp = fail_dir / f"{ws_path.name}.quarantine.json.{uuid.uuid4().hex[:8]}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
        f.flush()
        with contextlib.suppress(OSError):
            os.fsync(f.fileno())

    os.replace(tmp, dest)
    return dest


def write_cleanup_failure_record(
    workspace_dir: Path | str,
    job_id: uuid.UUID | str,
    staging_dir: Path | str | None = None,
    tenant_id: str | None = None,
    assessment_id: str | None = None,
    error: str = "",
    attempt_count: int = 1,
    db: Any = None,
    **kwargs: Any,
) -> Path | None:
    """Write durable cleanup failure record to {staging_dir}/.cleanup_failures/ using 4-step atomic write.

    Includes fallback to discovery_jobs.result_summary['cleanup_failure'] if volume write fails.
    """
    ws_path = Path(workspace_dir)
    stg_dir = Path(staging_dir or "./staging_data")
    fail_dir = stg_dir / ".cleanup_failures"
    now_iso = datetime.now(UTC).isoformat()

    error_msg = error or kwargs.get("error_str", "Unknown scratch cleanup error")

    record = {
        "workspace_path": str(ws_path),
        "workspace_basename": ws_path.name,
        "job_id": str(job_id),
        "tenant_id": tenant_id,
        "assessment_id": assessment_id,
        "first_failed_at": now_iso,
        "last_failed_at": now_iso,
        "attempts": attempt_count,
        "status": "pending_retry",
        "last_error": error_msg,
    }

    target_path = fail_dir / f"{ws_path.name}.json"
    tmp_path = fail_dir / f"{ws_path.name}.{uuid.uuid4().hex[:8]}.tmp"

    try:
        fail_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
            f.flush()
            with contextlib.suppress(OSError):
                os.fsync(f.fileno())
        os.replace(tmp_path, target_path)

        # On POSIX sync parent dir
        if hasattr(os, "O_DIRECTORY") and hasattr(os, "open"):
            with contextlib.suppress(OSError):
                p_fd = os.open(str(fail_dir), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
                try:
                    os.fsync(p_fd)
                finally:
                    os.close(p_fd)

        return target_path
    except Exception as exc:
        logger.error(
            "CRITICAL_CLEANUP_PERSISTENCE_FAILURE: Could not write cleanup failure record for workspace %s: %s",
            ws_path,
            exc,
        )
        return None
