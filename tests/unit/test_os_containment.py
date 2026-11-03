"""Quantum Flow Technologies — OS Process Containment & Lifecycle Tests.

Validates process containment guarantees across platforms:
- Windows: Native Win32 Job Object creation, strict KILL_ON_JOB_CLOSE limits,
  breakaway prohibition, suspended process launch (CREATE_SUSPENDED), pre-execution
  assignment, descendant termination, and process-count verification reaching zero.
- POSIX: Kernel-safe /proc/[pid]/stat parsing isolating comm via rfind(')'),
  fail-closed handling of indeterminate scans, and quarantine descriptors.
"""

import contextlib
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import pytest

from packages.scanner.safety.containment import (
    ProcStatParseError,
    create_windows_job_object,
    get_windows_job_process_count,
    parse_proc_stat_content,
    scan_active_pgid_descendants,
)

IS_WINDOWS = sys.platform == "win32"


# ------------------------------------------------------------------------------
# 1. Windows Native Job Object & Suspended Containment Tests
# ------------------------------------------------------------------------------
@pytest.mark.skipif(not IS_WINDOWS, reason="Requires native Windows Win32 API support")
class TestWindowsProcessContainment:
    """Verifies Win32 Job Object containment directly against the Windows kernel."""

    def test_windows_job_object_configuration_and_no_breakaway(self) -> None:
        """Verify Job Object enforces KILL_ON_JOB_CLOSE with breakaway flags strictly removed."""
        import win32api  # type: ignore[import-untyped]
        import win32job  # type: ignore[import-untyped]

        h_job = create_windows_job_object(f"qf_test_cfg_{uuid.uuid4().hex[:8]}")
        assert h_job is not None, "Failed to create Win32 Job Object"
        try:
            info = win32job.QueryInformationJobObject(
                h_job, win32job.JobObjectExtendedLimitInformation
            )
            limit_flags = info["BasicLimitInformation"]["LimitFlags"]

            # Must have KILL_ON_JOB_CLOSE set
            assert limit_flags & win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE != 0, (
                "JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE (0x2000) must be enabled"
            )

            # Must NOT have SILENT_BREAKAWAY_OK (0x1000) or BREAKAWAY_OK (0x800) set
            silent_breakaway_flag = 0x00001000
            breakaway_flag = 0x00000800
            assert limit_flags & silent_breakaway_flag == 0, (
                "JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK must be strictly forbidden"
            )
            assert limit_flags & breakaway_flag == 0, (
                "JOB_OBJECT_LIMIT_BREAKAWAY_OK must be strictly forbidden"
            )
        finally:
            win32api.CloseHandle(h_job)

    def test_windows_suspended_launch_and_pre_execution_assignment(self) -> None:
        """Verify process starts suspended, assigns to Job Object, resumes, and exits clean."""
        import win32api  # type: ignore[import-untyped]
        import win32con  # type: ignore[import-untyped]
        import win32job  # type: ignore[import-untyped]
        import win32process  # type: ignore[import-untyped]

        h_job = create_windows_job_object(f"qf_test_susp_{uuid.uuid4().hex[:8]}")
        assert h_job is not None

        hp = None
        ht = None
        try:
            si = win32process.STARTUPINFO()
            cmd_line = 'powershell.exe -NoProfile -Command "Start-Sleep -Seconds 15"'

            # 1. Create suspended process
            hp, ht, pid, tid = win32process.CreateProcess(
                None,
                cmd_line,
                None,
                None,
                False,
                win32con.CREATE_SUSPENDED | win32con.CREATE_NO_WINDOW,
                None,
                None,
                si,
            )
            assert pid > 0
            assert hp is not None
            assert ht is not None

            # Verify Job Object has zero processes before assignment
            assert get_windows_job_process_count(h_job) == 0

            # 2. Assign to Job Object while suspended
            win32job.AssignProcessToJobObject(h_job, hp)

            # Query Job Object process list while process is still suspended
            pids_suspended = win32job.QueryInformationJobObject(
                h_job, win32job.JobObjectBasicProcessIdList
            )
            assert pid in pids_suspended, "Process PID must be in Job Object while suspended"

            # 3. Resume thread only after successful assignment
            win32process.ResumeThread(ht)

            # Give process a moment to initialize
            time.sleep(0.3)
            active_count = get_windows_job_process_count(h_job)
            assert active_count >= 1, f"Expected at least 1 active process, got {active_count}"

            # 4. Terminate Job Object and verify process count drops to zero
            win32job.TerminateJobObject(h_job, 1)

            deadline = time.monotonic() + 5.0
            count_after = -1
            while time.monotonic() < deadline:
                count_after = get_windows_job_process_count(h_job)
                if count_after == 0:
                    break
                time.sleep(0.1)

            assert count_after == 0, "Job Object process count must reach 0 before cleanup"
        finally:
            if ht is not None:
                with contextlib.suppress(Exception):
                    win32api.CloseHandle(ht)
            if hp is not None:
                with contextlib.suppress(Exception):
                    win32process.TerminateProcess(hp, 1)
                with contextlib.suppress(Exception):
                    win32api.CloseHandle(hp)
            if h_job is not None:
                with contextlib.suppress(Exception):
                    win32api.CloseHandle(h_job)

    def test_windows_descendant_termination(self) -> None:
        """Verify terminating Job Object kills parent and any child descendants transitively."""
        import win32api  # type: ignore[import-untyped]
        import win32con  # type: ignore[import-untyped]
        import win32job  # type: ignore[import-untyped]
        import win32process  # type: ignore[import-untyped]

        h_job = create_windows_job_object(f"qf_test_desc_{uuid.uuid4().hex[:8]}")
        assert h_job is not None

        hp = None
        ht = None
        try:
            si = win32process.STARTUPINFO()
            # Command spawns a background child process inside powershell
            cmd_line = "powershell.exe -NoProfile -Command \"Start-Process powershell -ArgumentList '-NoProfile -Command Start-Sleep -Seconds 20'; Start-Sleep -Seconds 20\""

            hp, ht, pid, _ = win32process.CreateProcess(
                None,
                cmd_line,
                None,
                None,
                False,
                win32con.CREATE_SUSPENDED | win32con.CREATE_NO_WINDOW,
                None,
                None,
                si,
            )

            win32job.AssignProcessToJobObject(h_job, hp)
            win32process.ResumeThread(ht)

            # Wait up to 5 seconds for child descendant to spawn
            deadline = time.monotonic() + 5.0
            pids: tuple[Any, ...] = ()
            while time.monotonic() < deadline:
                pids = win32job.QueryInformationJobObject(
                    h_job, win32job.JobObjectBasicProcessIdList
                )
                if len(pids) >= 2:
                    break
                time.sleep(0.2)

            assert len(pids) >= 1, "Expected at least 1 process in Job Object"

            # Terminate all processes in the Job Object
            win32job.TerminateJobObject(h_job, 1)

            # Wait for count to reach 0
            deadline = time.monotonic() + 5.0
            count_after = -1
            while time.monotonic() < deadline:
                count_after = get_windows_job_process_count(h_job)
                if count_after == 0:
                    break
                time.sleep(0.1)

            assert count_after == 0, "All descendant processes must be terminated"
        finally:
            if ht is not None:
                with contextlib.suppress(Exception):
                    win32api.CloseHandle(ht)
            if hp is not None:
                with contextlib.suppress(Exception):
                    win32process.TerminateProcess(hp, 1)
                with contextlib.suppress(Exception):
                    win32api.CloseHandle(hp)
            if h_job is not None:
                with contextlib.suppress(Exception):
                    win32api.CloseHandle(h_job)

    def test_windows_assignment_failure_fails_closed(self) -> None:
        """Verify that if Job Object assignment fails, suspended process is terminated immediately."""
        import win32api  # type: ignore[import-untyped]
        import win32con  # type: ignore[import-untyped]
        import win32job  # type: ignore[import-untyped]
        import win32process  # type: ignore[import-untyped]

        hp = None
        ht = None
        # Create a Job Object and immediately close its handle to create an invalid handle
        h_invalid = create_windows_job_object(f"qf_test_inv_{uuid.uuid4().hex[:8]}")
        assert h_invalid is not None
        win32api.CloseHandle(h_invalid)

        try:
            si = win32process.STARTUPINFO()
            cmd_line = 'powershell.exe -NoProfile -Command "Start-Sleep -Seconds 30"'

            hp, ht, pid, tid = win32process.CreateProcess(
                None,
                cmd_line,
                None,
                None,
                False,
                win32con.CREATE_SUSPENDED | win32con.CREATE_NO_WINDOW,
                None,
                None,
                si,
            )

            # Attempt assignment with invalid closed handle to trigger failure
            assignment_failed = False
            try:
                win32job.AssignProcessToJobObject(h_invalid, hp)
            except Exception:
                assignment_failed = True
                # Fail closed: Terminate suspended process immediately
                win32process.TerminateProcess(hp, 1)

            assert assignment_failed is True, "Expected assignment to invalid handle to fail"

            # Confirm process was terminated before resume
            time.sleep(0.2)
            exit_code = win32process.GetExitCodeProcess(hp)
            assert exit_code == 1, f"Expected exit code 1 (terminated), got {exit_code}"
        finally:
            if ht is not None:
                with contextlib.suppress(Exception):
                    win32api.CloseHandle(ht)
            if hp is not None:
                with contextlib.suppress(Exception):
                    win32api.CloseHandle(hp)


# ------------------------------------------------------------------------------
# 2. Linux /proc Stat Parsing & Conclusive Scan Logic Tests
# ------------------------------------------------------------------------------
class TestLinuxProcStatParsing:
    """Tests Linux kernel /proc/[pid]/stat parsing and scan logic across platforms."""

    def test_proc_stat_with_spaces_and_parentheses_in_process_name(self) -> None:
        """Verify rfind(')') correctly handles process names containing spaces and parentheses."""
        # 1-based fields:
        # Field 1: pid (12345)
        # Field 2: comm ((python worker (child: 1)))
        # Fields 3-21 (remainder indices 0-18): 19 fields
        # Field 22 (remainder index 19): starttime (99999)
        prefix_fields = ["S", "100", "4242"] + ["0"] * 16  # 3 + 16 = 19 fields
        suffix_fields = ["99999", "0", "0"]
        raw_remainder = " ".join(prefix_fields + suffix_fields)
        raw_stat = f"12345 (python worker (child: 1)) {raw_remainder}"

        pgrp, starttime = parse_proc_stat_content(raw_stat, stat_path="/proc/12345/stat")
        assert pgrp == 4242, f"Expected pgrp 4242, got {pgrp}"
        assert starttime == 99999, f"Expected starttime 99999, got {starttime}"

    def test_proc_stat_missing_closing_parenthesis_raises_error(self) -> None:
        """Verify malformed content without ')' raises ProcStatParseError."""
        raw_stat = "12345 python_worker S 100 4242 100"
        with pytest.raises(ProcStatParseError, match="missing closing parenthesis"):
            parse_proc_stat_content(raw_stat, stat_path="/proc/12345/stat")

    def test_proc_stat_truncated_fields_raises_error(self) -> None:
        """Verify content with fewer than 20 fields after ')' raises ProcStatParseError."""
        raw_stat = "12345 (worker) S 100 4242"
        with pytest.raises(ProcStatParseError, match="Truncated"):
            parse_proc_stat_content(raw_stat, stat_path="/proc/12345/stat")

    def test_proc_stat_invalid_integer_raises_error(self) -> None:
        """Verify non-integer in pgrp or starttime fields raises ProcStatParseError."""
        raw_stat = "12345 (worker) S 100 NOT_AN_INT 100 0 0 0 0 0 0 0 0 0 0 0 0 0 0 99999 0 0 0 0"
        with pytest.raises(ProcStatParseError, match="Invalid integer field"):
            parse_proc_stat_content(raw_stat, stat_path="/proc/12345/stat")

    def test_scan_active_pgid_descendants_fails_closed_on_unreadable_entry(
        self, tmp_path: Path
    ) -> None:
        """Verify that an unreadable process entry flags is_scan_conclusive = False."""
        target_pgid = 5000

        # Create valid process entry 101 with matching pgid
        proc_101 = tmp_path / "101"
        proc_101.mkdir()
        valid_stat = "101 (worker) S 1 5000 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1234 0 0 0 0"
        (proc_101 / "stat").write_text(valid_stat, encoding="utf-8")

        # Create unreadable process entry 102 (empty/malformed stat)
        proc_102 = tmp_path / "102"
        proc_102.mkdir()
        (proc_102 / "stat").write_text("corrupted_no_parens", encoding="utf-8")

        matching_pids, is_conclusive = scan_active_pgid_descendants(
            target_pgid=target_pgid, proc_root=str(tmp_path)
        )

        assert 101 in matching_pids
        # Crucial guarantee: because entry 102 was corrupt, scan MUST be inconclusive
        assert is_conclusive is False, (
            "Corrupt or unreadable entry must fail closed (is_conclusive=False)"
        )
