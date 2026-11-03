"""Quantum Flow Technologies — Autonomous Background Worker Daemon.

Independent execution plane worker daemon that claims and executes durable
PostgreSQL-backed discovery jobs using SELECT FOR UPDATE SKIP LOCKED, actively
renews leases via background heartbeats, recovers zombie jobs, runs database-authoritative
5-state garbage collection with descriptor-relative deletion, handles cleanup failure
escalation, and provides operator recovery CLI commands.
"""

import argparse
import asyncio
import json
import logging
import os
import re
import signal
import socket
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from packages.scanner.safety.containment import (
    derive_job_scratch_lock_key,
    derive_tenant_upload_slot_key,
    get_active_boot_id,
    safe_delete_workspace,
    scan_active_pgid_descendants,
    write_cleanup_failure_record,
)
from services.api.app.core.config import settings
from services.api.app.db.models.assessment import Assessment
from services.api.app.db.models.discovery_job import DiscoveryJob, JobStatus
from services.api.app.db.session import close_async_engine, get_sessionmaker
from services.api.app.services.assessment_service import AssessmentService
from services.api.app.services.job_service import JobService

logger = logging.getLogger("quantumflow.worker")


class AutonomousWorker:
    """Autonomous background execution daemon for durable assessment jobs."""

    def __init__(
        self,
        worker_id: str | None = None,
        session_maker: async_sessionmaker[AsyncSession] | None = None,
        poll_interval_seconds: float = 1.0,
        lease_seconds: int = 60,
        heartbeat_interval_seconds: float = 20.0,
        zombie_check_interval_seconds: float = 60.0,
        gc_interval_seconds: float = 3600.0,
        shutdown_event: asyncio.Event | None = None,
    ) -> None:
        self.worker_id = worker_id or (
            f"worker-{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"
        )
        self.session_maker = session_maker or get_sessionmaker()
        self.poll_interval = poll_interval_seconds
        self.lease_seconds = lease_seconds
        self.heartbeat_interval = heartbeat_interval_seconds
        self.zombie_check_interval = zombie_check_interval_seconds
        self.gc_interval_seconds = gc_interval_seconds
        self.shutdown_event = shutdown_event or asyncio.Event()
        self._last_zombie_check: float = 0.0
        self._last_gc_check: float = 0.0
        self._is_running = False

    async def _renew_heartbeat(self, job_id: uuid.UUID, stop_event: asyncio.Event) -> None:
        """Asynchronous background task to renew lease while collector executes."""
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=self.heartbeat_interval)
                break
            except TimeoutError:
                try:
                    async with self.session_maker() as hb_session:
                        renewed = await JobService.renew_lease(
                            db=hb_session,
                            job_id=job_id,
                            worker_id=self.worker_id,
                            lease_seconds=self.lease_seconds,
                        )
                        if renewed:
                            logger.debug(
                                "Worker %s renewed lease for job %s (+%ds)",
                                self.worker_id,
                                job_id,
                                self.lease_seconds,
                            )
                        else:
                            logger.warning(
                                "Worker %s failed to renew lease for job %s (not found or not running)",
                                self.worker_id,
                                job_id,
                            )
                except Exception as exc:
                    logger.warning("Error renewing lease for job %s: %s", job_id, exc)

    async def process_job(self, job_id: uuid.UUID) -> None:
        """Execute a single claimed job with an active heartbeat lease renewal task."""
        stop_event = asyncio.Event()
        hb_task = asyncio.create_task(self._renew_heartbeat(job_id, stop_event))
        try:
            async with self.session_maker() as db:
                await AssessmentService.execute_discovery_job(
                    db=db,
                    job_id=job_id,
                    worker_id=self.worker_id,
                )
        except Exception as exc:
            logger.exception("Unexpected error processing job %s: %s", job_id, exc)
        finally:
            stop_event.set()
            await hb_task

    async def check_zombies(self) -> int:
        """Identify and recover dead worker leases."""
        now = time.monotonic()
        if now - self._last_zombie_check >= self.zombie_check_interval:
            self._last_zombie_check = now
            try:
                async with self.session_maker() as db:
                    recovered = await JobService.recover_zombies(db)
                    if recovered > 0:
                        logger.warning(
                            "Worker %s recovered %d zombie jobs with expired leases",
                            self.worker_id,
                            recovered,
                        )
                    return recovered
            except Exception as exc:
                logger.error("Error during zombie recovery check: %s", exc)
        return 0

    # ==========================================================================
    # 5-State Garbage Collection Daemon & Startup Reconciliation
    # ==========================================================================
    async def reconcile_startup(self) -> None:
        """Startup reconciliation compensating for unclean terminations or sudden power loss."""
        staging_dir = Path(settings.staging_dir)
        failures_dir = staging_dir / ".cleanup_failures"

        # 1. Scan .cleanup_failures and unlink *.tmp files older than 10 minutes
        if failures_dir.exists():
            now_ts = time.time()
            for tmp_file in failures_dir.glob("*.tmp"):
                try:
                    if now_ts - tmp_file.stat().st_mtime > 600:
                        tmp_file.unlink(missing_ok=True)
                        logger.info("Startup reconciliation: unlinked stale tmp file %s", tmp_file)
                except Exception as exc:
                    logger.warning("Startup reconciliation note on %s: %s", tmp_file, exc)

        logger.info("Worker %s completed startup reconciliation", self.worker_id)

    async def check_staging_gc(self, db: AsyncSession) -> dict[str, int]:
        """5-State database-authoritative Staging Garbage Collection sweep."""
        stats = {"purged": 0, "preserved": 0, "alerts": 0}
        staging_dir = Path(settings.staging_dir)
        if not staging_dir.exists():
            return stats

        now_utc = datetime.now(UTC)

        for tenant_dir in staging_dir.iterdir():
            if not tenant_dir.is_dir() or tenant_dir.name.startswith("."):
                continue

            tenant_id = tenant_dir.name

            for token_dir in tenant_dir.iterdir():
                if not token_dir.is_dir() or token_dir.name.startswith("."):
                    continue

                token = token_dir.name
                meta_path = token_dir / "metadata.json"
                res_path = token_dir / "reservation.json"

                if meta_path.exists():
                    try:
                        with open(meta_path, encoding="utf-8") as f:
                            metadata = json.load(f)
                    except Exception as exc:
                        logger.warning(
                            "UNVERIFIABLE_STAGING_ENTRY: Corrupt metadata in %s: %s",
                            token_dir,
                            exc,
                        )
                        stats["preserved"] += 1
                        stats["alerts"] += 1
                        continue

                    # Verify canonical tenant consistency
                    meta_tenant = metadata.get("tenant_id")
                    if not meta_tenant or meta_tenant != tenant_id:
                        logger.error(
                            "AMBIGUOUS_TOKEN_OWNERSHIP: Directory tenant '%s' != metadata tenant '%s' in %s",
                            tenant_id,
                            meta_tenant,
                            token_dir,
                        )
                        stats["preserved"] += 1
                        stats["alerts"] += 1
                        continue

                    assessment_id_str = metadata.get("assessment_id")
                    if assessment_id_str:
                        # State 2: Bound Assessment Staged Upload
                        try:
                            ass_id = uuid.UUID(assessment_id_str)
                            ass = await db.scalar(select(Assessment).where(Assessment.id == ass_id))
                        except Exception:
                            ass = None

                        if ass is None:
                            logger.warning(
                                "AMBIGUOUS_TOKEN_OWNERSHIP: Assessment %s referenced by token %s not found in DB",
                                assessment_id_str,
                                token,
                            )
                            stats["preserved"] += 1
                            stats["alerts"] += 1
                            continue

                        ass_tenant = (ass.target_snapshot or {}).get("tenant_id")
                        if ass_tenant != tenant_id:
                            logger.critical(
                                "CRITICAL_CROSS_TENANT_INTEGRITY_VIOLATION: Assessment %s tenant '%s' != staging tenant '%s'",
                                ass.id,
                                ass_tenant,
                                tenant_id,
                            )
                            stats["preserved"] += 1
                            stats["alerts"] += 1
                            continue

                        # Terminal check
                        if ass.is_terminal():
                            logger.info(
                                "GC State 2: Purging staged upload for terminal assessment %s (%s)",
                                ass.id,
                                ass.status,
                            )
                            if safe_delete_workspace(token_dir):
                                stats["purged"] += 1
                            else:
                                stats["preserved"] += 1
                        else:
                            # Active assessment: preserve
                            stats["preserved"] += 1
                    else:
                        # State 1: Unbound Staged Upload (Check 4h expiration)
                        uploaded_at_str = metadata.get("uploaded_at")
                        try:
                            uploaded_at = datetime.fromisoformat(uploaded_at_str)
                            if uploaded_at.tzinfo is None:
                                uploaded_at = uploaded_at.replace(tzinfo=UTC)
                        except Exception:
                            uploaded_at = now_utc

                        if now_utc - uploaded_at > timedelta(hours=4):
                            logger.info(
                                "GC State 1: Purging expired unbound staged upload %s (>4h)",
                                token_dir,
                            )
                            if safe_delete_workspace(token_dir):
                                stats["purged"] += 1
                            else:
                                stats["preserved"] += 1
                        else:
                            stats["preserved"] += 1

                elif res_path.exists():
                    # Unfinalized upload: Upload-Slot Guard Protocol
                    try:
                        with open(res_path, encoding="utf-8") as f:
                            res_data = json.load(f)
                        res_tenant = res_data.get("tenant_id", tenant_id)
                        res_slot = int(res_data.get("slot", 0))
                        reserved_at_str = res_data.get("reserved_at")
                        reserved_at = datetime.fromisoformat(reserved_at_str)
                        if reserved_at.tzinfo is None:
                            reserved_at = reserved_at.replace(tzinfo=UTC)
                    except Exception:
                        res_tenant = tenant_id
                        res_slot = 0
                        reserved_at = now_utc

                    # Probe slot advisory lock
                    bind = db.bind or getattr(db, "sync_session", db).bind
                    dialect_name = bind.dialect.name if bind else ""
                    slot_held = False
                    if "postgres" in dialect_name:
                        slot_key = derive_tenant_upload_slot_key(res_tenant, res_slot)
                        probe_locked = await db.scalar(
                            text("SELECT pg_try_advisory_xact_lock(:slot_key)"),
                            {"slot_key": slot_key},
                        )
                        if not probe_locked:
                            # Slot lock is actively held by an API upload worker!
                            slot_held = True

                    if slot_held:
                        logger.info(
                            "GC Slot Guard: Preserving active in-flight upload in %s (slot lock actively held)",
                            token_dir,
                        )
                        stats["preserved"] += 1
                    else:
                        # Lock not held: check if abandoned (>300s)
                        if (now_utc - reserved_at).total_seconds() > 300:
                            logger.info(
                                "GC Slot Guard: Purging abandoned unfinalized upload in %s (>300s, lock unheld)",
                                token_dir,
                            )
                            if safe_delete_workspace(token_dir):
                                stats["purged"] += 1
                            else:
                                stats["preserved"] += 1
                        else:
                            stats["preserved"] += 1
                else:
                    # Staging directory without metadata or reservation: check age
                    try:
                        st = token_dir.stat()
                        if now_utc.timestamp() - st.st_mtime > 3600:
                            if safe_delete_workspace(token_dir):
                                stats["purged"] += 1
                            else:
                                stats["preserved"] += 1
                        else:
                            stats["preserved"] += 1
                    except Exception:
                        stats["preserved"] += 1

        return stats

    async def check_scratch_gc(self, db: AsyncSession) -> dict[str, int]:
        """Lease-aware scratch workspace Garbage Collection sweep."""
        stats = {"purged": 0, "preserved": 0, "orphans": 0}
        scratch_dir = Path(settings.scratch_dir)
        if not scratch_dir.exists():
            return stats

        now_utc = datetime.now(UTC)

        for workspace in scratch_dir.iterdir():
            if not workspace.is_dir() or workspace.name.startswith("."):
                continue

            match = re.match(
                r"^job_([0-9a-fA-F-]{36})_[0-9a-fA-F]{12}$",
                workspace.name,
            )
            if not match:
                continue

            job_id_str = match.group(1)
            try:
                job_id = uuid.UUID(job_id_str)
            except ValueError:
                continue

            # 1. Database Job Existence Check
            job = await db.scalar(select(DiscoveryJob).where(DiscoveryJob.id == job_id))
            if job is None:
                # Missing DB record: GC must NOT delete the workspace!
                logger.critical(
                    "CRITICAL_ORPHAN_SCRATCH_DIR: Scratch workspace %s references non-existent job_id %s. Preserving workspace for operator security audit.",
                    workspace,
                    job_id,
                )
                stats["orphans"] += 1
                stats["preserved"] += 1
                continue

            # 2. Active Lease Check
            job_lease = job.lease_expires_at
            if job_lease and job_lease.tzinfo is None:
                job_lease = job_lease.replace(tzinfo=UTC)

            if job.status == JobStatus.RUNNING.value and job_lease and now_utc < job_lease:
                # Active worker heartbeating: preserve immediately
                stats["preserved"] += 1
                continue

            # 3. Atomic Mutual Exclusion Advisory Lock Check
            bind = db.bind or getattr(db, "sync_session", db).bind
            dialect_name = bind.dialect.name if bind else ""
            lock_acquired = True
            if "postgres" in dialect_name:
                job_key = derive_job_scratch_lock_key(job_id)
                lock_acquired = await db.scalar(
                    text("SELECT pg_try_advisory_xact_lock(:job_key)"),
                    {"job_key": job_key},
                )

            if not lock_acquired:
                # Worker actively holds scratch advisory lock! Defer deletion.
                logger.debug(
                    "GC Scratch: Worker holds advisory lock for %s; deferring deletion",
                    workspace,
                )
                stats["preserved"] += 1
                continue

            # Lock acquired: verify terminal status or lease expiration (>120s past expiry)
            is_expired_lease = job_lease is not None and (now_utc - job_lease) > timedelta(
                seconds=120
            )
            is_terminal = job.status in (
                JobStatus.COMPLETED.value,
                JobStatus.FAILED.value,
                JobStatus.CANCELLED.value,
            )

            if is_terminal or is_expired_lease:
                logger.info(
                    "GC Scratch: Purging abandoned scratch workspace %s (status=%s, expired_lease=%s)",
                    workspace,
                    job.status,
                    is_expired_lease,
                )
                if safe_delete_workspace(workspace):
                    stats["purged"] += 1
                else:
                    write_cleanup_failure_record(
                        workspace_dir=workspace,
                        job_id=job_id,
                        staging_dir=settings.staging_dir,
                        tenant_id=None,
                        assessment_id=str(job.assessment_id) if job.assessment_id else None,
                        error="GC safe_delete_workspace failed",
                        db=db,
                    )
                    stats["preserved"] += 1
            else:
                stats["preserved"] += 1

        return stats

    async def check_cleanup_failures_gc(self, db: AsyncSession) -> dict[str, int]:
        """Process and retry persistent cleanup failure and quarantine records."""
        stats = {"retried": 0, "escalated": 0, "quarantine_resolved": 0}
        failures_dir = Path(settings.staging_dir) / ".cleanup_failures"
        if not failures_dir.exists():
            return stats

        for rec_file in failures_dir.glob("*.json"):
            if rec_file.name.endswith(".tmp"):
                continue

            try:
                with open(rec_file, encoding="utf-8") as f:
                    record = json.load(f)
            except Exception as exc:
                logger.warning("Error reading failure record %s: %s", rec_file, exc)
                continue

            # A. Quarantine Record Handling
            if rec_file.name.endswith(".quarantine.json"):
                workspace_path = Path(record.get("workspace_path", ""))
                proc_ident = record.get("process_identity", {})

                # Whole-Group Verification
                safe_to_reclaim = False
                posix_boot_id = proc_ident.get("posix_boot_id")
                if posix_boot_id:
                    current_boot_id = get_active_boot_id()
                    if current_boot_id and current_boot_id != posix_boot_id:
                        # Reboot occurred: all processes dead!
                        safe_to_reclaim = True
                    else:
                        target_pgid = proc_ident.get("posix_pgid")
                        if target_pgid:
                            matching_pids, is_conclusive = scan_active_pgid_descendants(target_pgid)
                            if is_conclusive and len(matching_pids) == 0:
                                safe_to_reclaim = True

                if safe_to_reclaim and safe_delete_workspace(workspace_path):
                    rec_file.unlink(missing_ok=True)
                    stats["quarantine_resolved"] += 1
                    logger.info("GC Quarantine: Reclaimed verified dead quarantine %s", rec_file)
                continue

            # B. Standard Cleanup Failure Record Handling
            workspace_path = Path(record.get("workspace_path", ""))
            attempts = record.get("attempts", 1)

            if attempts >= 5:
                # Escalation threshold reached
                if record.get("status") != "escalated_manual_intervention_required":
                    record["status"] = "escalated_manual_intervention_required"
                    tmp_r = failures_dir / f"{rec_file.name}.{uuid.uuid4().hex[:8]}.tmp"
                    with open(tmp_r, "w", encoding="utf-8") as f:
                        json.dump(record, f, indent=2)
                    os.replace(tmp_r, rec_file)
                    logger.critical(
                        "CRITICAL_SCRATCH_DIR_LEAK: Workspace %s has failed %d consecutive cleanup attempts (Last error: %s). Retries halted. Preserving for operator inspection.",
                        workspace_path,
                        attempts,
                        record.get("last_error"),
                    )
                stats["escalated"] += 1
                continue

            # Attempt deletion retry
            if workspace_path.exists():
                success = safe_delete_workspace(workspace_path)
                if success:
                    rec_file.unlink(missing_ok=True)
                    stats["retried"] += 1
                    logger.info("GC Cleanup Retry: Successfully cleaned up %s", workspace_path)
                else:
                    record["attempts"] = attempts + 1
                    record["last_failed_at"] = datetime.now(UTC).isoformat()
                    tmp_r = failures_dir / f"{rec_file.name}.{uuid.uuid4().hex[:8]}.tmp"
                    with open(tmp_r, "w", encoding="utf-8") as f:
                        json.dump(record, f, indent=2)
                    os.replace(tmp_r, rec_file)
            else:
                # Workspace directory already removed
                rec_file.unlink(missing_ok=True)
                stats["retried"] += 1

        return stats

    async def check_gc(self) -> dict[str, Any]:
        """Execute comprehensive periodic Garbage Collection sweep across all layers."""
        now = time.monotonic()
        if now - self._last_gc_check < self.gc_interval_seconds:
            return {}

        self._last_gc_check = now
        logger.info("Worker %s starting comprehensive Garbage Collection cycle", self.worker_id)
        results: dict[str, Any] = {}
        try:
            async with self.session_maker() as db:
                results["staging"] = await self.check_staging_gc(db)
                results["scratch"] = await self.check_scratch_gc(db)
                results["failures"] = await self.check_cleanup_failures_gc(db)
            logger.info("Worker %s completed Garbage Collection cycle: %s", self.worker_id, results)
        except Exception as exc:
            logger.exception("Error during Garbage Collection cycle: %s", exc)
        return results

    async def run_tick(self) -> bool:
        """Run a single polling and job execution cycle.

        Returns True if a job was claimed and processed, False otherwise.
        """
        # 1. Periodic zombie detection and recovery
        await self.check_zombies()

        # 2. Periodic comprehensive Garbage Collection sweep
        await self.check_gc()

        # 3. Claim next available queued job using SELECT FOR UPDATE SKIP LOCKED
        claimed_job_id: uuid.UUID | None = None
        try:
            async with self.session_maker() as db:
                job = await JobService.claim_next_job(
                    db=db,
                    worker_id=self.worker_id,
                    lease_seconds=self.lease_seconds,
                )
                if job:
                    claimed_job_id = job.id
        except Exception as exc:
            logger.error("Error claiming job from queue: %s", exc)
            return False

        if not claimed_job_id:
            return False

        # 4. Execute claimed job with background heartbeat
        logger.info("Worker %s claimed job %s; starting execution", self.worker_id, claimed_job_id)
        await self.process_job(claimed_job_id)
        return True

    async def run(self, max_iterations: int | None = None) -> None:
        """Start the autonomous worker polling loop until shutdown signal."""
        self._is_running = True
        logger.info(
            "Quantum Flow Worker %s started polling (interval=%.1fs, lease=%ds)",
            self.worker_id,
            self.poll_interval,
            self.lease_seconds,
        )

        # Run startup reconciliation before commencing loop
        await self.reconcile_startup()

        iterations = 0
        try:
            while not self.shutdown_event.is_set():
                if max_iterations is not None and iterations >= max_iterations:
                    break

                job_processed = await self.run_tick()
                iterations += 1

                if not job_processed and not self.shutdown_event.is_set():
                    try:
                        await asyncio.wait_for(
                            self.shutdown_event.wait(),
                            timeout=self.poll_interval,
                        )
                        break
                    except TimeoutError:
                        continue
        finally:
            self._is_running = False
            logger.info("Worker %s stopped cleanly", self.worker_id)


def setup_signal_handlers(shutdown_event: asyncio.Event) -> None:
    """Attach OS signals for graceful termination across platforms."""
    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, shutdown_event.set)
            except NotImplementedError:
                # Windows ProactorEventLoop does not support add_signal_handler
                signal.signal(sig, lambda s, f: shutdown_event.set())
    except Exception as exc:
        logger.debug("Signal handler registration note: %s", exc)


# ==============================================================================
# Operator Recovery CLI Commands
# ==============================================================================
def list_cleanup_failures() -> None:
    """List persistent cleanup failures across containers."""
    failures_dir = Path(settings.staging_dir) / ".cleanup_failures"
    if not failures_dir.exists():
        print(f"No cleanup failures directory found at {failures_dir}")
        return

    records = list(failures_dir.glob("*.json"))
    if not records:
        print("Zero cleanup failures recorded. Storage is clean.")
        return

    print(f"\nFound {len(records)} cleanup failure / quarantine record(s):")
    print("-" * 80)
    for r_file in sorted(records):
        try:
            with open(r_file, encoding="utf-8") as f:
                rec = json.load(f)
            ws = rec.get("workspace_basename") or rec.get("workspace_path")
            st = rec.get("status", "unknown")
            att = rec.get("attempts", 0)
            err = rec.get("last_error") or rec.get("reason", "N/A")
            print(f"File:     {r_file.name}")
            print(f"Workspace:{ws}")
            print(f"Status:   {st} (Attempts: {att})")
            print(f"Error:    {err}")
            print("-" * 80)
        except Exception as exc:
            print(f"Error reading {r_file.name}: {exc}")


def retry_cleanup_failures() -> None:
    """Retry cleanup for all recorded failure workspaces."""
    failures_dir = Path(settings.staging_dir) / ".cleanup_failures"
    if not failures_dir.exists():
        print("No cleanup failures recorded.")
        return

    records = list(failures_dir.glob("*.json"))
    print(f"Retrying cleanup for {len(records)} record(s)...")
    cleaned = 0
    for r_file in records:
        try:
            with open(r_file, encoding="utf-8") as f:
                rec = json.load(f)
            ws_path = Path(rec.get("workspace_path", ""))
            if ws_path.exists():
                if safe_delete_workspace(ws_path):
                    r_file.unlink(missing_ok=True)
                    cleaned += 1
                    print(f"SUCCESS: Cleaned {ws_path}")
                else:
                    print(f"FAILED: Could not clean {ws_path}")
            else:
                r_file.unlink(missing_ok=True)
                cleaned += 1
                print(f"REMOVED: Stale record {r_file.name} (workspace already absent)")
        except Exception as exc:
            print(f"ERROR: {r_file.name}: {exc}")

    print(f"Done. Cleaned {cleaned}/{len(records)} workspaces.")


def force_purge_failure(workspace_basename: str) -> None:
    """Force purge an abandoned workspace and unlink its failure descriptor."""
    failures_dir = Path(settings.staging_dir) / ".cleanup_failures"
    scratch_dir = Path(settings.scratch_dir)

    target_ws = scratch_dir / workspace_basename
    print(f"Attempting force purge of workspace: {target_ws}")

    if target_ws.exists():
        if safe_delete_workspace(target_ws):
            print("SUCCESS: Workspace safely deleted.")
        else:
            print("WARNING: safe_delete_workspace returned False, attempting direct unlink...")
            import shutil

            shutil.rmtree(target_ws, ignore_errors=True)
            print("Purged via fallback.")
    else:
        print(f"Workspace directory {target_ws} does not exist on disk.")

    # Unlink any matching descriptor
    for pattern in (
        f"{workspace_basename}.json",
        f"{workspace_basename}.failure.json",
        f"{workspace_basename}.quarantine.json",
    ):
        desc = failures_dir / pattern
        if desc.exists():
            desc.unlink(missing_ok=True)
            print(f"Unlinked descriptor: {desc}")


async def async_main() -> None:
    """Async entrypoint for standalone worker daemon."""
    shutdown_event = asyncio.Event()
    setup_signal_handlers(shutdown_event)

    try:
        worker = AutonomousWorker(shutdown_event=shutdown_event)
        await worker.run()
    finally:
        await close_async_engine()


def main() -> None:
    """CLI process entrypoint with operator management flags."""
    parser = argparse.ArgumentParser(description="Quantum Flow Autonomous Worker Daemon")
    parser.add_argument(
        "--list-cleanup-failures",
        action="store_true",
        help="List persistent cleanup failure records",
    )
    parser.add_argument(
        "--retry-cleanup-failures",
        action="store_true",
        help="Retry cleanup for recorded failure workspaces",
    )
    parser.add_argument(
        "--force-purge-failure",
        type=str,
        metavar="WORKSPACE_BASENAME",
        help="Force purge an abandoned workspace and unlink its failure descriptor",
    )

    args = parser.parse_args()

    if args.list_cleanup_failures:
        list_cleanup_failures()
        return

    if args.retry_cleanup_failures:
        retry_cleanup_failures()
        return

    if args.force_purge_failure:
        force_purge_failure(args.force_purge_failure)
        return

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Starting Quantum Flow Autonomous Worker process...")
    try:
        asyncio.run(async_main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker process exited via interrupt signal")


if __name__ == "__main__":
    main()
