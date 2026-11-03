"""Quantum Flow Technologies — Migration Safety & Legacy Data Compatibility Tests.

Verifies schema upgrade and downgrade safety with populated representative data from
Sprint 1 (targets, scans, observations) and Sprint 2 (CBOM assets, standalone risk assessments).
"""

import os
import socket
import uuid
from collections.abc import Generator
from urllib.parse import urlparse

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from services.api.app.core.config import settings
from services.api.app.db.models import (
    Assessment,
    AssessmentAsset,
    AssessmentObservation,
    AssessmentStatus,
    CryptographicAsset,
    DiscoveryJob,
    JobStatus,
    JobType,
    Observation,
    Recommendation,
    RiskAssessment,
    RiskFactor,
    Scan,
    ScanStatus,
    Target,
)

PG_URL = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql+psycopg2://quantumflow:quantumflow_secret_dev@localhost:5434/quantumflow_db",
)
os.environ["DATABASE_URL_SYNC"] = PG_URL
settings.database_url_sync = PG_URL


@pytest.fixture(scope="module")
def alembic_cfg() -> Config:
    """Alembic configuration fixture configured for the test PostgreSQL instance."""
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", PG_URL)
    return cfg


def _is_db_reachable(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 5432
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except Exception:
        return False


@pytest.fixture(scope="module", autouse=True)
def require_postgres() -> None:
    if not _is_db_reachable(PG_URL):
        pytest.skip("PostgreSQL 16 test database is not available on port 5434")


@pytest.fixture(scope="module")
def pg_engine() -> Generator[Engine, None, None]:
    """Module-level engine for migration verification."""
    engine = create_engine(PG_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


def test_migration_safety_with_populated_legacy_records(
    pg_engine: Engine, alembic_cfg: Config
) -> None:
    """Pre-populate Sprint 1 & 2 records, then verify downgrade and re-upgrade preserves all data."""
    # Ensure starting at head
    command.upgrade(alembic_cfg, "head")

    session = Session(pg_engine)
    unique_suffix = uuid.uuid4().hex[:8]

    target_id: uuid.UUID | None = None
    scan_id: uuid.UUID | None = None
    obs_id: uuid.UUID | None = None
    asset_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    risk_id: uuid.UUID | None = None

    try:
        # 1. Populate Sprint 1: Target
        target = Target(
            hostname=f"legacy-{unique_suffix}.example.com",
            display_name="Legacy Sprint 1 Target",
            status="ACTIVE",
            authorisation_status="VERIFIED",
            verification_token=f"tok_{unique_suffix}",
        )
        session.add(target)
        session.flush()
        target_id = target.id

        # 2. Populate Sprint 1: Scan
        scan = Scan(
            target_id=target.id,
            status=ScanStatus.COMPLETED.value,
            scan_type="tls_handshake",
            collector_version="v1.0.0",
        )
        session.add(scan)
        session.flush()
        scan_id = scan.id

        # 3. Populate Sprint 1: Observation
        obs = Observation(
            target_id=target.id,
            scan_id=scan.id,
            observation_type="tls_certificate",
            source="network_tls_probe",
            collector_version="v1.0.0",
            observed_value={"subject": f"CN=legacy-{unique_suffix}.example.com"},
            evidence_sha256=uuid.uuid4().hex * 2,
        )
        session.add(obs)
        session.flush()
        obs_id = obs.id

        # 4. Populate Sprint 2: CryptographicAsset
        asset = CryptographicAsset(
            target_id=target.id,
            asset_key=f"asset:legacy:rsa2048:{unique_suffix}",
            display_name="Legacy RSA-2048 Asset",
            asset_type="ASYMMETRIC_KEY",
            algorithm_name="RSA",
            algorithm_family="RSA",
            business_criticality="HIGH",
            cryptographic_purpose="SIGNATURE",
            parameters={"key_size": 2048},
            lifecycle_status="ACTIVE",
            classification="OBSERVED",
            confidence_score=1.0,
            correlation_version="v1.0.0",
        )
        session.add(asset)
        session.flush()
        asset_id = asset.id

        # 5. Populate Sprint 2: DiscoveryJob (standalone, assessment_id = None)
        job = DiscoveryJob(
            target_id=target.id,
            job_type=JobType.TLS_DISCOVERY.value,
            status=JobStatus.COMPLETED.value,
            assessment_id=None,
        )
        session.add(job)
        session.flush()
        job_id = job.id

        # 6. Populate Sprint 2: RiskAssessment (standalone, assessment_id = None)
        risk = RiskAssessment(
            asset_id=asset.id,
            assessment_id=None,
            assessment_number=1,
            status="provisional",
            score=750,
            risk_category="high",
            quantum_threat_type="shor_vulnerable",
            threat_summary="Vulnerable to Shor factoring",
            evidence_quality="high",
            assessment_input_hash=uuid.uuid4().hex * 2,
            engine_version="v1.0.0",
            methodology_version="QFT-RISK-v1.0",
            policy_snapshot={"weights": {"Q": 300}},
            limitations={},
        )
        session.add(risk)
        session.flush()
        risk_id = risk.id

        factor = RiskFactor(
            risk_assessment_id=risk.id,
            dimension="Q",
            factor_code="DIM_Q_SHOR_EXPOSURE",
            title="Shor Exposure",
            explanation="RSA-2048 can be factored in polynomial time",
            rating=5,
            weight=300,
            contribution=300,
        )
        session.add(factor)

        rec = Recommendation(
            risk_assessment_id=risk.id,
            asset_id=asset.id,
            title="Migrate to ML-DSA-65",
            description="Replace RSA digital signatures with ML-DSA-65",
            priority="high",
        )
        session.add(rec)
        session.commit()
        session.close()

        # 7. Execute Downgrade to 4a2d8e1f9b3c on populated database
        command.downgrade(alembic_cfg, "4a2d8e1f9b3c")

        # Verify all legacy records exist and remain valid after downgrade
        session = Session(pg_engine)
        down_target = session.get(Target, target_id)
        assert down_target is not None
        assert down_target.status == "ACTIVE"

        down_scan = session.get(Scan, scan_id)
        assert down_scan is not None
        assert down_scan.status == ScanStatus.COMPLETED.value

        down_obs = session.get(Observation, obs_id)
        assert down_obs is not None

        down_asset = session.get(CryptographicAsset, asset_id)
        assert down_asset is not None
        assert down_asset.asset_key == f"asset:legacy:rsa2048:{unique_suffix}"

        down_job = session.get(DiscoveryJob, job_id)
        assert down_job is not None
        assert down_job.assessment_id is None

        down_risk = session.get(RiskAssessment, risk_id)
        assert down_risk is not None
        assert down_risk.score == 750
        assert down_risk.assessment_id is None
        assert len(down_risk.factors) == 1
        assert len(down_risk.recommendations) == 1
        session.close()

        # 8. Re-upgrade to head (5b3e9f2a1c0d)
        command.upgrade(alembic_cfg, "head")

        # Verify all legacy records still exist and are unharmed
        session = Session(pg_engine)
        up_risk = session.get(RiskAssessment, risk_id)
        assert up_risk is not None
        assert up_risk.score == 750
        assert up_risk.assessment_id is None
        assert len(up_risk.factors) == 1
        assert len(up_risk.recommendations) == 1

        # 9. Verify that new Sprint 3 entities can now be created and reference legacy rows
        new_assessment = Assessment(
            title="Sprint 3 Integration Run",
            target_id=target_id,
            scope_hash=uuid.uuid4().hex,
            status=AssessmentStatus.RUNNING.value,
        )
        session.add(new_assessment)
        session.flush()

        aa = AssessmentAsset(
            assessment_id=new_assessment.id,
            asset_id=asset_id,
            classification="OBSERVED",
            asset_snapshot={"algorithm": "RSA"},
        )
        ao = AssessmentObservation(
            assessment_id=new_assessment.id,
            observation_id=obs_id,
        )
        session.add_all([aa, ao])
        session.commit()

        # Verify associations persisted
        retrieved_aa = session.get(AssessmentAsset, (new_assessment.id, asset_id))
        assert retrieved_aa is not None
        retrieved_ao = session.get(AssessmentObservation, (new_assessment.id, obs_id))
        assert retrieved_ao is not None

        # Clean up Sprint 3 test entities
        session.delete(aa)
        session.delete(ao)
        session.delete(new_assessment)
        session.commit()

    finally:
        # Clean up populated legacy test data
        session.close()
        session = Session(pg_engine)
        try:
            if risk_id:
                r = session.get(RiskAssessment, risk_id)
                if r:
                    session.delete(r)
            if job_id:
                j = session.get(DiscoveryJob, job_id)
                if j:
                    session.delete(j)
            if asset_id:
                a = session.get(CryptographicAsset, asset_id)
                if a:
                    session.delete(a)
            if obs_id:
                o = session.get(Observation, obs_id)
                if o:
                    session.delete(o)
            if scan_id:
                s = session.get(Scan, scan_id)
                if s:
                    session.delete(s)
            if target_id:
                t = session.get(Target, target_id)
                if t:
                    session.delete(t)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()
