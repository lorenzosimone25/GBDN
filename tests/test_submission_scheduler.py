from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from gbdn.artifacts import (
    NA_ID,
    SCHEMA_VERSION,
    ArtifactValidationError,
    EnvironmentMetadata,
    FailureRecord,
    RunConfigRecord,
    RunIdentity,
    RunMode,
    SourceMetadata,
    canonical_json_sha256,
    load_failure_record,
    write_failure_record,
)
from gbdn.submission_scheduler import run_confirmatory_scheduler


def _job(index: int) -> RunConfigRecord:
    source = SourceMetadata("a" * 40, "b" * 40, "c" * 64, False, None, False)
    environment = EnvironmentMetadata(
        "3.11.0",
        "CPython",
        "Linux",
        "x86_64",
        "/usr/bin/python",
        "requirements.lock",
        "d" * 64,
        "0",
        ":4096:8",
        "0",
    )
    frozen = {"job": index}
    identity = RunIdentity(
        SCHEMA_VERSION,
        "heterophily_confirm",
        "Roman-empire",
        "e" * 64,
        f"Method-{index}",
        "frozen-confirmatory",
        index,
        0,
        0,
        canonical_json_sha256(frozen),
        source.source_sha256,
        environment.dependency_lock_sha256,
        NA_ID,
        "deterministic-fp32",
    )
    return RunConfigRecord.create(
        identity=identity,
        frozen_config=frozen,
        source=source,
        environment=environment,
        run_mode=RunMode.FULL,
        created_at_utc="2026-08-12T12:00:00Z",
    )


def _fixture(root: Path, worker_source: str) -> tuple[Path, Path, Path, Path]:
    worker = root / "scripts" / "run_heterophily_job.py"
    worker.parent.mkdir(parents=True)
    worker.write_text(worker_source, encoding="utf-8")
    paths = tuple(root / name for name in ("run_plan.json", "confirmatory.json", "registry.json"))
    for path in paths:
        path.write_text("{}", encoding="utf-8")
    return (*paths, worker)


def test_scheduler_refuses_without_independent_acceptance(tmp_path):
    run_plan, confirmatory, registry, worker = _fixture(tmp_path, "raise SystemExit(0)\n")
    with pytest.raises(ArtifactValidationError, match="acceptance token is absent"):
        run_confirmatory_scheduler(
            repository_root=tmp_path,
            run_plan_path=run_plan,
            confirmatory_plan_path=confirmatory,
            baseline_registry_path=registry,
            worker_path=worker,
        )


def test_scheduler_rejects_noncanonical_worker_before_launch(tmp_path):
    run_plan, confirmatory, registry, _ = _fixture(tmp_path, "raise SystemExit(0)\n")
    other = tmp_path / "other.py"
    other.write_text("raise SystemExit(0)\n", encoding="utf-8")
    with (
        patch("gbdn.submission_scheduler.validate_gate_a_acceptance"),
        patch("gbdn.submission_scheduler.validate_run_plan", return_value=SimpleNamespace(jobs=(_job(0),))),
        pytest.raises(ArtifactValidationError, match="canonical"),
    ):
        run_confirmatory_scheduler(
            repository_root=tmp_path,
            run_plan_path=run_plan,
            confirmatory_plan_path=confirmatory,
            baseline_registry_path=registry,
            worker_path=other,
        )


def test_scheduler_rejects_symlinked_worker_when_supported(tmp_path):
    run_plan, confirmatory, registry, canonical = _fixture(tmp_path, "raise SystemExit(0)\n")
    target = tmp_path / "target.py"
    target.write_text("raise SystemExit(0)\n", encoding="utf-8")
    canonical.unlink()
    try:
        canonical.symlink_to(target)
    except OSError:
        pytest.skip("file symlink creation is unavailable")
    with (
        patch("gbdn.submission_scheduler.validate_gate_a_acceptance"),
        patch("gbdn.submission_scheduler.validate_run_plan", return_value=SimpleNamespace(jobs=(_job(0),))),
        pytest.raises(ArtifactValidationError, match="canonical"),
    ):
        run_confirmatory_scheduler(
            repository_root=tmp_path,
            run_plan_path=run_plan,
            confirmatory_plan_path=confirmatory,
            baseline_registry_path=registry,
            worker_path=canonical,
        )


def test_scheduler_continues_failures_and_preserves_records(tmp_path):
    script = (
        "import argparse\n"
        "p=argparse.ArgumentParser(); p.add_argument('--repository-root'); "
        "p.add_argument('--run-plan'); p.add_argument('--job-index', type=int); "
        "p.add_argument('--run-id'); a=p.parse_args()\n"
        "raise SystemExit(3 if a.job_index == 0 else 0)\n"
    )
    run_plan, confirmatory, registry, worker = _fixture(tmp_path, script)
    jobs = (_job(0), _job(1))
    with (
        patch("gbdn.submission_scheduler.validate_gate_a_acceptance"),
        patch("gbdn.submission_scheduler.validate_run_plan", return_value=SimpleNamespace(jobs=jobs)),
    ):
        summary = run_confirmatory_scheduler(
            repository_root=tmp_path,
            run_plan_path=run_plan,
            confirmatory_plan_path=confirmatory,
            baseline_registry_path=registry,
            worker_path=worker,
            continue_on_error=True,
            timeout_seconds=30,
        )
    assert summary.to_dict() == {
        "blocked": 0,
        "completed": 0,
        "failed": 2,
        "skipped": 0,
        "success": False,
        "total": 2,
    }
    failure_paths = sorted((tmp_path / "results_submission" / "failures").rglob("failure=*.json"))
    assert len(failure_paths) == 2
    records = [load_failure_record(path) for path in failure_paths]
    assert {record.exception_type for record in records} == {"SubprocessFailure", "WorkerContractError"}
    assert {record.identity.run_id for record in records} == {job.identity.run_id for job in jobs}


def test_prior_failure_blocks_by_default_and_retry_is_explicit(tmp_path):
    run_plan, confirmatory, registry, worker = _fixture(tmp_path, "raise SystemExit(4)\n")
    job = _job(0)
    write_failure_record(
        FailureRecord(
            job.identity,
            "PriorFailure",
            "preserved",
            NA_ID,
            (),
            job.source,
            job.environment,
            "2026-08-12T12:00:00Z",
        ),
        repository_root=tmp_path,
    )
    with (
        patch("gbdn.submission_scheduler.validate_gate_a_acceptance"),
        patch("gbdn.submission_scheduler.validate_run_plan", return_value=SimpleNamespace(jobs=(job,))),
    ):
        summary = run_confirmatory_scheduler(
            repository_root=tmp_path,
            run_plan_path=run_plan,
            confirmatory_plan_path=confirmatory,
            baseline_registry_path=registry,
            worker_path=worker,
        )
    assert summary.blocked == 1 and summary.failed == 0
    assert len(list((tmp_path / "results_submission" / "failures").rglob("failure=*.json"))) == 1


def test_scheduler_flags_and_timeout_fail_closed(tmp_path):
    run_plan, confirmatory, registry, worker = _fixture(tmp_path, "raise SystemExit(0)\n")
    with pytest.raises(ArtifactValidationError, match="booleans"):
        run_confirmatory_scheduler(
            repository_root=tmp_path,
            run_plan_path=run_plan,
            confirmatory_plan_path=confirmatory,
            baseline_registry_path=registry,
            worker_path=worker,
            continue_on_error=1,
        )
    with pytest.raises(ArtifactValidationError, match="timeout"):
        run_confirmatory_scheduler(
            repository_root=tmp_path,
            run_plan_path=run_plan,
            confirmatory_plan_path=confirmatory,
            baseline_registry_path=registry,
            worker_path=worker,
            timeout_seconds=0,
        )
