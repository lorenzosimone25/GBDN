"""Sequential, fail-closed scheduler around validated confirmatory plans."""

from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from gbdn.artifacts import (
    ArtifactFileManifest,
    ArtifactValidationError,
    FailureRecord,
    ResumeState,
    RunResultRecord,
    canonical_json_bytes,
    canonical_json_sha256,
    capture_environment_metadata,
    capture_source_metadata,
    classify_resume,
    sha256_file,
    utc_now_iso,
    write_failure_record,
)
from gbdn.gate_acceptance import validate_gate_a_acceptance
from gbdn.heterophily_evaluator import (
    evaluation_attestation,
    evaluate_prediction_archive,
    load_authoritative_split,
)
from gbdn.provenance import CANONICAL_RESULT_DIR, canonical_output_path, write_new_canonical_artifact
from gbdn.run_plan import validate_run_plan


_LOG_LIMIT = 64 * 1024
_METRIC_TOLERANCE = 1e-12
_SECRET = re.compile(
    r"(?i)(api[_-]?key|authorization|cookie|password|secret|token)(\s*[:=]\s*)([^\s,;]+)"
)


@dataclass(frozen=True)
class SchedulerSummary:
    total: int
    completed: int
    skipped: int
    failed: int
    blocked: int

    @property
    def success(self) -> bool:
        return self.failed == 0 and self.blocked == 0 and self.completed + self.skipped == self.total

    def to_dict(self) -> dict[str, int | bool]:
        return {
            "blocked": self.blocked,
            "completed": self.completed,
            "failed": self.failed,
            "skipped": self.skipped,
            "success": self.success,
            "total": self.total,
        }


def _regular_repository_file(root: Path, path: str | Path, label: str) -> Path:
    raw = Path(path)
    if not raw.is_absolute():
        raw = root / raw
    if raw.is_symlink() or not raw.is_file():
        raise ArtifactValidationError(f"{label} must be a regular repository file")
    resolved = raw.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ArtifactValidationError(f"{label} escapes the repository") from exc
    return resolved


def _capture_input_hashes(
    root: Path, *, run_plan_path: Path, confirmatory_plan_path: Path,
    baseline_registry_path: Path, worker: Path
) -> dict[str, str]:
    return {
        "baseline_registry": sha256_file(_regular_repository_file(root, baseline_registry_path, "baseline registry")),
        "confirmatory_plan": sha256_file(_regular_repository_file(root, confirmatory_plan_path, "confirmatory plan")),
        "run_plan": sha256_file(_regular_repository_file(root, run_plan_path, "run plan")),
        "worker": sha256_file(_regular_repository_file(root, worker, "scheduler worker")),
    }


def _validate_execution_identity(job, root: Path, frozen_hashes: dict[str, str], **paths: Path) -> None:
    if _capture_input_hashes(root, worker=paths["worker"], run_plan_path=paths["run_plan_path"],
                             confirmatory_plan_path=paths["confirmatory_plan_path"],
                             baseline_registry_path=paths["baseline_registry_path"]) != frozen_hashes:
        raise ArtifactValidationError("scheduler input or worker changed after plan validation")
    observed_source = capture_source_metadata(root, full_run=True)
    if observed_source != job.source:
        raise ArtifactValidationError("current source differs from the frozen job source")
    lock = root / job.environment.dependency_lock_path
    observed_environment = capture_environment_metadata(lock, repository_root=root)
    if observed_environment != job.environment:
        raise ArtifactValidationError("current interpreter/environment differs from the frozen job environment")


def _load_result(bundle: Path) -> RunResultRecord:
    target = bundle / "result.json"
    if target.is_symlink() or not target.is_file():
        raise ArtifactValidationError("completed bundle result is absent or unsafe")
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError("completed bundle result is invalid") from exc
    return RunResultRecord.from_dict(value)


def _reported_primary_metric(result: RunResultRecord) -> tuple[str, float]:
    payload = json.loads(result.result_payload_json)
    metrics = payload.get("metrics")
    primary = metrics.get("primary") if isinstance(metrics, dict) else None
    if not isinstance(primary, dict) or set(primary) != {"name", "value"}:
        raise ArtifactValidationError("result lacks the closed primary metric contract")
    name, value = primary["name"], primary["value"]
    if not isinstance(name, str) or type(value) not in (int, float):
        raise ArtifactValidationError("reported primary metric has invalid types")
    return name, float(value)


def _semantic_evaluation(job, bundle: Path, root: Path, dataset_root: Path) -> None:
    result = _load_result(bundle)
    authority = load_authoritative_split(
        dataset_root, dataset=job.identity.dataset_name, split=job.identity.split_id
    )
    if authority.dataset_sha256 != job.identity.dataset_sha256:
        raise ArtifactValidationError("job dataset identity differs from authoritative archive")
    prediction = bundle / result.predictions.path
    metric = evaluate_prediction_archive(
        prediction,
        expected_run_id=job.identity.run_id,
        expected_dataset=job.identity.dataset_name,
        expected_split=job.identity.split_id,
        expected_test_indices=authority.indices,
        authoritative_test_labels=authority.labels,
    )
    reported_name, reported_value = _reported_primary_metric(result)
    if reported_name != metric.metric_name or abs(reported_value - metric.value) > _METRIC_TOLERANCE:
        raise ArtifactValidationError("reported metric disagrees with authoritative recomputation")
    evaluator_hash = sha256_file(Path(__file__).with_name("heterophily_evaluator.py"))
    record = evaluation_attestation(metric, authority, evaluator_sha256=evaluator_hash)
    relative = Path(CANONICAL_RESULT_DIR) / "evaluations" / f"run={job.identity.run_id}" / "evaluation.json"
    target = canonical_output_path(relative, repository_root=root)
    payload = canonical_json_bytes(record)
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_file() or target.read_bytes() != payload:
            raise ArtifactValidationError("independent evaluation attestation is conflicting or corrupt")
    else:
        try:
            write_new_canonical_artifact(relative, payload, repository_root=root)
        except FileExistsError:
            if target.is_symlink() or not target.is_file() or target.read_bytes() != payload:
                raise ArtifactValidationError("concurrent evaluation attestation conflict")


def _bounded_redacted(value: str | bytes | None) -> bytes:
    if value is None:
        text = ""
    elif isinstance(value, bytes):
        text = value.decode("utf-8", errors="replace")
    else:
        text = value
    text = _SECRET.sub(r"\1\2[REDACTED]", text)
    payload = text.encode("utf-8", errors="replace")
    return payload[-_LOG_LIMIT:]


def _record_failure(root: Path, job, *, exception_type: str, message: str,
                    stdout: str | bytes | None, stderr: str | bytes | None) -> None:
    attempt = canonical_json_sha256(
        {"nonce": secrets.token_hex(16), "run_id": job.identity.run_id, "timestamp": utc_now_iso()}
    )
    base = Path(CANONICAL_RESULT_DIR) / "failures" / f"run={job.identity.run_id}" / f"attempt={attempt}"
    manifests = []
    for name, content in (
        ("stdout.txt", _bounded_redacted(stdout)),
        ("stderr.txt", _bounded_redacted(stderr)),
        ("traceback.txt", _bounded_redacted(message)),
    ):
        relative = base / name
        path = write_new_canonical_artifact(relative, content, repository_root=root)
        manifests.append(ArtifactFileManifest(relative.as_posix(), sha256_file(path), path.stat().st_size))
    record = FailureRecord(
        identity=job.identity,
        exception_type=exception_type,
        message=_bounded_redacted(message).decode("utf-8"),
        traceback_path=(base / "traceback.txt").as_posix(),
        partial_artifacts=(),
        source=job.source,
        environment=job.environment,
        created_at_utc=utc_now_iso(),
        evidence=tuple(manifests),
    )
    write_failure_record(record, repository_root=root)


def run_confirmatory_scheduler(
    *, repository_root: str | Path, run_plan_path: str | Path,
    confirmatory_plan_path: str | Path, baseline_registry_path: str | Path,
    worker_path: str | Path, authoritative_dataset_root: str | Path,
    continue_on_error: bool = True, retry_recorded_failures: bool = False,
    timeout_seconds: float = 24 * 60 * 60,
) -> SchedulerSummary:
    """Run validated jobs sequentially; never delete, overwrite, or self-accept."""

    if type(continue_on_error) is not bool or type(retry_recorded_failures) is not bool:
        raise ArtifactValidationError("scheduler flags must be booleans")
    if not isinstance(timeout_seconds, (int, float)) or not 0 < float(timeout_seconds) <= 7 * 24 * 60 * 60:
        raise ArtifactValidationError("scheduler timeout must be positive and at most seven days")
    root = Path(repository_root).resolve(strict=True)
    dataset_root = Path(authoritative_dataset_root).resolve(strict=True)
    validate_gate_a_acceptance(root)
    plan = validate_run_plan(run_plan_path, confirmatory_plan_path=confirmatory_plan_path,
                             baseline_registry_path=baseline_registry_path, repository_root=root)
    requested_worker = Path(worker_path)
    worker = _regular_repository_file(root, requested_worker, "scheduler worker")
    expected_worker = root / "scripts" / "run_heterophily_job.py"
    if expected_worker.is_symlink() or not expected_worker.is_file() or worker != expected_worker.resolve(strict=True):
        raise ArtifactValidationError("scheduler worker must be the canonical repository script")
    paths = {
        "worker": worker,
        "run_plan_path": Path(run_plan_path).resolve(strict=True),
        "confirmatory_plan_path": Path(confirmatory_plan_path).resolve(strict=True),
        "baseline_registry_path": Path(baseline_registry_path).resolve(strict=True),
    }
    frozen_hashes = _capture_input_hashes(root, **paths)

    completed = skipped = failed = blocked = 0
    for index, job in enumerate(plan.jobs):
        try:
            _validate_execution_identity(job, root, frozen_hashes, **paths)
            decision = classify_resume(job.identity, repository_root=root)
            if decision is not None and decision.state is ResumeState.MATCHING_COMPLETE:
                _semantic_evaluation(job, decision.path, root, dataset_root)
                skipped += 1
                continue
            if decision is not None and not (
                retry_recorded_failures and decision.state is ResumeState.PARTIAL and decision.recoverable
            ):
                blocked += 1
                if not continue_on_error:
                    break
                continue
        except (ArtifactValidationError, OSError):
            blocked += 1
            if not continue_on_error:
                break
            continue

        child_environment = os.environ.copy()
        child_environment["CUDA_VISIBLE_DEVICES"] = str(job.environment.cuda_visible_devices)
        child_environment["CUBLAS_WORKSPACE_CONFIG"] = str(job.environment.cublas_workspace_config)
        child_environment["PYTHONHASHSEED"] = str(job.environment.pythonhashseed)
        command = [sys.executable, str(worker), "--repository-root", str(root), "--run-plan",
                   str(paths["run_plan_path"]), "--job-index", str(index), "--run-id", job.identity.run_id]
        exception_type, message, stdout, stderr = "SubprocessFailure", "", "", ""
        try:
            process = subprocess.run(command, check=False, capture_output=True, text=True,
                                     timeout=float(timeout_seconds), env=child_environment)
            stdout, stderr = process.stdout, process.stderr
            if process.returncode != 0:
                message = f"worker exited with status {process.returncode}"
            else:
                _validate_execution_identity(job, root, frozen_hashes, **paths)
                postcondition = classify_resume(job.identity, repository_root=root)
                if postcondition is None or postcondition.state is not ResumeState.MATCHING_COMPLETE:
                    exception_type = "WorkerContractError"
                    observed = "missing" if postcondition is None else postcondition.state.value
                    message = f"worker exited zero without a matching complete bundle: {observed}"
                else:
                    _semantic_evaluation(job, postcondition.path, root, dataset_root)
                    completed += 1
                    continue
        except subprocess.TimeoutExpired as exc:
            exception_type, message, stdout, stderr = (
                "WorkerTimeout", f"worker exceeded timeout_seconds={float(timeout_seconds)}", exc.stdout, exc.stderr
            )
        except (ArtifactValidationError, OSError) as exc:
            exception_type, message = "WorkerContractError", str(exc)
        try:
            _record_failure(root, job, exception_type=exception_type, message=message,
                            stdout=stdout, stderr=stderr)
        except (ArtifactValidationError, FileExistsError, OSError):
            blocked += 1
            if not continue_on_error:
                break
            continue
        failed += 1
        if not continue_on_error:
            break
    return SchedulerSummary(len(plan.jobs), completed, skipped, failed, blocked)


__all__ = ["SchedulerSummary", "run_confirmatory_scheduler"]
