"""Quantum Flow Technologies — Scanner Safety Package."""

from packages.scanner.safety.canonical import (
    canonicalize_payload,
    compute_canonical_evidence_sha256,
    verify_evidence_integrity,
)
from packages.scanner.safety.containment import (
    IndeterminateProcScanError,
    ProcStatParseError,
    create_windows_job_object,
    derive_global_upload_slot_key,
    derive_job_scratch_lock_key,
    derive_tenant_upload_slot_key,
    derive_token_lock_key,
    get_active_boot_id,
    parse_proc_stat,
    parse_proc_stat_content,
    safe_delete_workspace,
    scan_active_pgid_descendants,
    split_advisory_lock_key,
    write_cleanup_failure_record,
    write_quarantine_record,
)
from packages.scanner.safety.hostname import (
    HostnameValidationError,
    normalize_hostname,
)
from packages.scanner.safety.resolver import (
    ResolutionResult,
    ResolutionSecurityError,
    SafeDestinationResolver,
    is_ip_prohibited,
)
from packages.scanner.safety.validator import (
    TargetSafetyViolation,
    is_safe_test_target,
)

__all__ = [
    "HostnameValidationError",
    "IndeterminateProcScanError",
    "ProcStatParseError",
    "ResolutionResult",
    "ResolutionSecurityError",
    "SafeDestinationResolver",
    "TargetSafetyViolation",
    "canonicalize_payload",
    "compute_canonical_evidence_sha256",
    "create_windows_job_object",
    "derive_global_upload_slot_key",
    "derive_job_scratch_lock_key",
    "derive_tenant_upload_slot_key",
    "derive_token_lock_key",
    "get_active_boot_id",
    "is_ip_prohibited",
    "is_safe_test_target",
    "normalize_hostname",
    "parse_proc_stat",
    "parse_proc_stat_content",
    "safe_delete_workspace",
    "scan_active_pgid_descendants",
    "split_advisory_lock_key",
    "verify_evidence_integrity",
    "write_cleanup_failure_record",
    "write_quarantine_record",
]
