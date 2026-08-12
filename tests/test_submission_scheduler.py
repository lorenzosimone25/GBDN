from __future__ import annotations

import json
from dataclasses import replace
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
    sha256_file,
    write_failure_record,
)
from gbdn.heterophily_evaluator import AuthoritativeSplit, PREDICTION_FORMAT
from gbdn.submission_scheduler import (
    _capture_input_hashes,
    _record_failure,
    _semantic_evaluation,
    _validate_execution_identity,
    run_confirmatory_scheduler,
)
import numpy as np


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
            authoritative_dataset_root=tmp_path,
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
            authoritative_dataset_root=tmp_path,
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
            authoritative_dataset_root=tmp_path,
        )


def test_scheduler_continues_failures_and_preserves_records(tmp_path):
    script = (
        "import argparse\n"
        "p=argparse.ArgumentParser(); p.add_argument('--repository-root'); "
        "p.add_argument('--run-plan'); p.add_argument('--authoritative-dataset-root'); "
        "p.add_argument('--job-index', type=int); "
        "p.add_argument('--run-id'); a=p.parse_args()\n"
        "raise SystemExit(3 if a.job_index == 0 else 0)\n"
    )
    run_plan, confirmatory, registry, worker = _fixture(tmp_path, script)
    jobs = (_job(0), _job(1))
    with (
        patch("gbdn.submission_scheduler.validate_gate_a_acceptance"),
        patch("gbdn.submission_scheduler.validate_run_plan", return_value=SimpleNamespace(jobs=jobs)),
        patch("gbdn.submission_scheduler._validate_execution_identity"),
    ):
        summary = run_confirmatory_scheduler(
            repository_root=tmp_path,
            run_plan_path=run_plan,
            confirmatory_plan_path=confirmatory,
            baseline_registry_path=registry,
            worker_path=worker,
            authoritative_dataset_root=tmp_path,
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
        patch("gbdn.submission_scheduler._validate_execution_identity"),
    ):
        summary = run_confirmatory_scheduler(
            repository_root=tmp_path,
            run_plan_path=run_plan,
            confirmatory_plan_path=confirmatory,
            baseline_registry_path=registry,
            worker_path=worker,
            authoritative_dataset_root=tmp_path,
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
            authoritative_dataset_root=tmp_path,
            continue_on_error=1,
        )
    with pytest.raises(ArtifactValidationError, match="timeout"):
        run_confirmatory_scheduler(
            repository_root=tmp_path,
            run_plan_path=run_plan,
            confirmatory_plan_path=confirmatory,
            baseline_registry_path=registry,
            worker_path=worker,
            authoritative_dataset_root=tmp_path,
            timeout_seconds=0,
        )


def _prediction_and_result(root: Path, job: RunConfigRecord, *, metric: float) -> Path:
    bundle = root / "bundle"
    bundle.mkdir()
    prediction = bundle / "predictions.npz"
    indices = np.asarray([4, 9, 12], dtype=np.int64)
    logits = np.zeros((3, 18), dtype=np.float32)
    logits[0, 1], logits[1, 0], logits[2, 2] = 3, 2, 4
    np.savez_compressed(
        prediction,
        dataset=np.asarray("Roman-empire"),
        format=np.asarray(PREDICTION_FORMAT),
        indices=indices,
        logits=logits,
        run_id=np.asarray(job.identity.run_id),
        split_id=np.asarray(0, dtype=np.int64),
    )
    from gbdn.artifacts import PredictionArtifactManifest, RunResultRecord

    manifest = PredictionArtifactManifest(
        job.identity.run_id,
        "predictions.npz",
        sha256_file(prediction),
        prediction.stat().st_size,
        PREDICTION_FORMAT,
    )
    result = RunResultRecord.create(
        identity=job.identity,
        predictions=manifest,
        result_payload={"metrics": {"primary": {"name": "accuracy", "value": metric}}},
        source=job.source,
        environment=job.environment,
        created_at_utc="2026-08-12T12:00:00Z",
    )
    (bundle / "result.json").write_text(json.dumps(result.to_dict()), encoding="utf-8")
    return bundle


def test_semantically_wrong_metric_cannot_receive_attestation(tmp_path):
    job = _job(0)
    bundle = _prediction_and_result(tmp_path, job, metric=1.0)
    authority = AuthoritativeSplit(
        np.asarray([4, 9, 12], dtype=np.int64),
        np.asarray([1, 1, 2], dtype=np.int64),
        job.identity.dataset_sha256,
        "1" * 64,
        "2" * 64,
    )
    with (
        patch("gbdn.submission_scheduler.load_authoritative_split", return_value=authority),
        pytest.raises(ArtifactValidationError, match="disagrees"),
    ):
        _semantic_evaluation(job, bundle, tmp_path, tmp_path)
    assert not (tmp_path / "results_submission" / "evaluations").exists()


def test_evaluation_attestation_contains_hashes_not_authority_values(tmp_path):
    job = _job(0)
    bundle = _prediction_and_result(tmp_path, job, metric=2 / 3)
    authority = AuthoritativeSplit(
        np.asarray([4, 9, 12], dtype=np.int64),
        np.asarray([1, 1, 2], dtype=np.int64),
        job.identity.dataset_sha256,
        "1" * 64,
        "2" * 64,
    )
    with patch("gbdn.submission_scheduler.load_authoritative_split", return_value=authority):
        _semantic_evaluation(job, bundle, tmp_path, tmp_path)
        _semantic_evaluation(job, bundle, tmp_path, tmp_path)
    path = next((tmp_path / "results_submission" / "evaluations").rglob("evaluation.json"))
    value = json.loads(path.read_text(encoding="utf-8"))
    assert value["indices_sha256"] == "1" * 64 and value["labels_sha256"] == "2" * 64
    assert "indices" not in value and "labels" not in value


def test_semantic_evaluation_rejects_prediction_manifest_drift_with_same_metric(tmp_path):
    job = _job(0)
    bundle = _prediction_and_result(tmp_path, job, metric=2 / 3)
    prediction = bundle / "predictions.npz"
    with np.load(prediction, allow_pickle=False) as stored:
        values = {name: np.asarray(stored[name]) for name in stored.files}
    values["logits"] = values["logits"].copy()
    values["logits"][0, 5] = 0.25
    np.savez_compressed(prediction, **values)
    authority = AuthoritativeSplit(
        np.asarray([4, 9, 12], dtype=np.int64),
        np.asarray([1, 1, 2], dtype=np.int64),
        job.identity.dataset_sha256,
        "1" * 64,
        "2" * 64,
    )
    with (
        patch("gbdn.submission_scheduler.load_authoritative_split", return_value=authority),
        pytest.raises(ArtifactValidationError, match="immutable result manifest"),
    ):
        _semantic_evaluation(job, bundle, tmp_path, tmp_path)


def test_semantic_evaluation_scores_the_manifest_bound_snapshot_under_aba(tmp_path):
    job = _job(0)
    bundle = _prediction_and_result(tmp_path, job, metric=2 / 3)
    prediction = bundle / "predictions.npz"
    manifest_bytes = prediction.read_bytes()
    authority = AuthoritativeSplit(
        np.asarray([4, 9, 12], dtype=np.int64),
        np.asarray([1, 1, 2], dtype=np.int64),
        job.identity.dataset_sha256,
        "1" * 64,
        "2" * 64,
    )
    observed = {}

    def score_snapshot(payload, **kwargs):
        observed["payload"] = payload
        prediction.write_bytes(b"replacement that cannot affect captured bytes")
        from gbdn.heterophily_evaluator import evaluate_prediction_bytes

        return evaluate_prediction_bytes(payload, **kwargs)

    with (
        patch("gbdn.submission_scheduler.load_authoritative_split", return_value=authority),
        patch("gbdn.submission_scheduler.evaluate_prediction_bytes", side_effect=score_snapshot),
    ):
        _semantic_evaluation(job, bundle, tmp_path, tmp_path)
    assert observed["payload"] == manifest_bytes
    assert prediction.read_bytes() != manifest_bytes


def test_skip_path_invokes_semantic_evaluation_and_blocks_on_failure(tmp_path):
    run_plan, confirmatory, registry, worker = _fixture(tmp_path, "raise SystemExit(0)\n")
    job = _job(0)
    complete = SimpleNamespace(state=__import__("gbdn.artifacts", fromlist=["ResumeState"]).ResumeState.MATCHING_COMPLETE, path=tmp_path / "bundle")
    with (
        patch("gbdn.submission_scheduler.validate_gate_a_acceptance"),
        patch("gbdn.submission_scheduler.validate_run_plan", return_value=SimpleNamespace(jobs=(job,))),
        patch("gbdn.submission_scheduler._validate_execution_identity"),
        patch("gbdn.submission_scheduler.classify_resume", return_value=complete),
        patch("gbdn.submission_scheduler._semantic_evaluation", side_effect=ArtifactValidationError("wrong predictions")) as evaluate,
        patch("gbdn.submission_scheduler.subprocess.run") as launch,
    ):
        summary = run_confirmatory_scheduler(
            repository_root=tmp_path, run_plan_path=run_plan,
            confirmatory_plan_path=confirmatory, baseline_registry_path=registry,
            worker_path=worker, authoritative_dataset_root=tmp_path,
        )
    assert summary.blocked == 1 and summary.skipped == 0
    evaluate.assert_called_once()
    launch.assert_not_called()


def test_source_or_environment_drift_before_launch_blocks(tmp_path):
    run_plan, confirmatory, registry, worker = _fixture(tmp_path, "raise SystemExit(0)\n")
    with (
        patch("gbdn.submission_scheduler.validate_gate_a_acceptance"),
        patch("gbdn.submission_scheduler.validate_run_plan", return_value=SimpleNamespace(jobs=(_job(0),))),
        patch("gbdn.submission_scheduler._validate_execution_identity", side_effect=ArtifactValidationError("source drift")),
        patch("gbdn.submission_scheduler.subprocess.run") as launch,
    ):
        summary = run_confirmatory_scheduler(
            repository_root=tmp_path, run_plan_path=run_plan,
            confirmatory_plan_path=confirmatory, baseline_registry_path=registry,
            worker_path=worker, authoritative_dataset_root=tmp_path,
        )
    assert summary.blocked == 1
    launch.assert_not_called()


def test_execution_identity_recaptures_source_environment_and_input_hashes(tmp_path):
    run_plan, confirmatory, registry, worker = _fixture(tmp_path, "raise SystemExit(0)\n")
    job = _job(0)
    paths = {
        "run_plan_path": run_plan,
        "confirmatory_plan_path": confirmatory,
        "baseline_registry_path": registry,
        "worker": worker,
    }
    frozen = _capture_input_hashes(tmp_path.resolve(), **paths)
    acceptance = SimpleNamespace(reviewed_source_metadata=job.source)
    with (
        patch("gbdn.submission_scheduler.validate_operations_acceptance", return_value=acceptance) as source,
        patch("gbdn.submission_scheduler.capture_environment_metadata", return_value=job.environment) as environment,
    ):
        _validate_execution_identity(job, tmp_path.resolve(), frozen, **paths)
    source.assert_called_once_with(tmp_path.resolve())
    environment.assert_called_once()

    wrong_acceptance = SimpleNamespace(
        reviewed_source_metadata=replace(job.source, repository_commit="f" * 40)
    )
    with patch(
        "gbdn.submission_scheduler.validate_operations_acceptance",
        return_value=wrong_acceptance,
    ):
        with pytest.raises(ArtifactValidationError, match="reviewed executable source"):
            _validate_execution_identity(job, tmp_path.resolve(), frozen, **paths)

    worker.write_text("raise SystemExit(7)\n", encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="changed"):
        _validate_execution_identity(job, tmp_path.resolve(), frozen, **paths)


def test_zero_exit_wrong_bundle_and_post_child_identity_drift_fail(tmp_path):
    run_plan, confirmatory, registry, worker = _fixture(tmp_path, "raise SystemExit(0)\n")
    job = _job(0)
    complete = SimpleNamespace(
        state=__import__("gbdn.artifacts", fromlist=["ResumeState"]).ResumeState.MATCHING_COMPLETE,
        path=tmp_path / "bundle",
    )
    process = SimpleNamespace(returncode=0, stdout="", stderr="")
    with (
        patch("gbdn.submission_scheduler.validate_gate_a_acceptance"),
        patch("gbdn.submission_scheduler.validate_run_plan", return_value=SimpleNamespace(jobs=(job,))),
        patch("gbdn.submission_scheduler._validate_execution_identity") as identity_check,
        patch("gbdn.submission_scheduler.classify_resume", side_effect=[None, complete]),
        patch("gbdn.submission_scheduler.subprocess.run", return_value=process),
        patch("gbdn.submission_scheduler._semantic_evaluation", side_effect=ArtifactValidationError("wrong predictions")) as evaluate,
    ):
        summary = run_confirmatory_scheduler(
            repository_root=tmp_path, run_plan_path=run_plan,
            confirmatory_plan_path=confirmatory, baseline_registry_path=registry,
            worker_path=worker, authoritative_dataset_root=tmp_path,
        )
    assert summary.failed == 1 and summary.completed == 0
    assert identity_check.call_count == 2
    evaluate.assert_called_once()

    drift_root = tmp_path / "drift"
    run_plan, confirmatory, registry, worker = _fixture(drift_root, "raise SystemExit(0)\n")
    with (
        patch("gbdn.submission_scheduler.validate_gate_a_acceptance"),
        patch("gbdn.submission_scheduler.validate_run_plan", return_value=SimpleNamespace(jobs=(job,))),
        patch("gbdn.submission_scheduler._validate_execution_identity", side_effect=[None, ArtifactValidationError("environment drift")]),
        patch("gbdn.submission_scheduler.classify_resume", return_value=None),
        patch("gbdn.submission_scheduler.subprocess.run", return_value=process),
        patch("gbdn.submission_scheduler._semantic_evaluation") as evaluate,
    ):
        summary = run_confirmatory_scheduler(
            repository_root=drift_root, run_plan_path=run_plan,
            confirmatory_plan_path=confirmatory, baseline_registry_path=registry,
            worker_path=worker, authoritative_dataset_root=drift_root,
        )
    assert summary.failed == 1 and summary.completed == 0
    evaluate.assert_not_called()


def test_failure_evidence_is_bounded_redacted_hash_bound_and_exclusive(tmp_path):
    job = _job(0)
    secret = "token=DO-NOT-STORE " + "x" * 100_000
    with patch("gbdn.submission_scheduler.secrets.token_hex", return_value="a" * 32):
        _record_failure(
            tmp_path, job, exception_type="RuntimeError", message=secret,
            stdout=secret, stderr="authorization: bearer-secret",
        )
        files = sorted((tmp_path / "results_submission" / "failures").rglob("*.txt"))
        assert len(files) == 3 and all(path.stat().st_size <= 64 * 1024 for path in files)
        assert all(b"DO-NOT-STORE" not in path.read_bytes() for path in files)
        record = load_failure_record(next((tmp_path / "results_submission" / "failures").rglob("failure=*.json")))
        assert len(record.evidence) == 3
        assert all(sha256_file(tmp_path / item.path) == item.sha256 for item in record.evidence)
        snapshots = {path: path.read_bytes() for path in files}
        with pytest.raises(FileExistsError):
            _record_failure(
                tmp_path, job, exception_type="RuntimeError", message=secret,
                stdout=secret, stderr="authorization: bearer-secret",
            )
    assert snapshots == {path: path.read_bytes() for path in files}

    files[0].write_bytes(b"tampered")
    decision = __import__("gbdn.artifacts", fromlist=["classify_resume"]).classify_resume(
        job.identity, repository_root=tmp_path
    )
    assert decision is not None and decision.state.value == "corrupt"


def test_partial_failure_evidence_is_not_retryable(tmp_path):
    job = _job(0)
    partial = (
        tmp_path
        / "results_submission"
        / "failures"
        / f"run={job.identity.run_id}"
        / "attempt=partial"
        / "stdout.txt"
    )
    partial.parent.mkdir(parents=True)
    partial.write_text("orphan", encoding="utf-8")
    decision = __import__("gbdn.artifacts", fromlist=["classify_resume"]).classify_resume(
        job.identity, repository_root=tmp_path
    )
    assert decision is not None and decision.state.value == "corrupt"
    assert decision.recoverable is False


def test_scheduler_requires_authoritative_dataset_root_argument(tmp_path):
    run_plan, confirmatory, registry, worker = _fixture(tmp_path, "raise SystemExit(0)\n")
    with pytest.raises(TypeError, match="authoritative_dataset_root"):
        run_confirmatory_scheduler(
            repository_root=tmp_path,
            run_plan_path=run_plan,
            confirmatory_plan_path=confirmatory,
            baseline_registry_path=registry,
            worker_path=worker,
        )


def test_scheduler_passes_authoritative_dataset_root_to_worker(tmp_path):
    run_plan, confirmatory, registry, worker = _fixture(tmp_path, "raise SystemExit(0)\n")
    job = _job(0)
    process = SimpleNamespace(returncode=1, stdout="", stderr="")
    with (
        patch("gbdn.submission_scheduler.validate_gate_a_acceptance"),
        patch("gbdn.submission_scheduler.validate_run_plan", return_value=SimpleNamespace(jobs=(job,))),
        patch("gbdn.submission_scheduler._validate_execution_identity"),
        patch("gbdn.submission_scheduler.subprocess.run", return_value=process) as launch,
    ):
        run_confirmatory_scheduler(
            repository_root=tmp_path,
            run_plan_path=run_plan,
            confirmatory_plan_path=confirmatory,
            baseline_registry_path=registry,
            worker_path=worker,
            authoritative_dataset_root=tmp_path,
            continue_on_error=False,
        )
    command = launch.call_args.args[0]
    offset = command.index("--authoritative-dataset-root")
    assert Path(command[offset + 1]) == tmp_path.resolve()
