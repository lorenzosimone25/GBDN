"""CPU-only Stage-1 submission orchestration.

This module intentionally implements one diagnostic synthetic job.  It tests
the execution and artifact path without making a benchmark or Gate-A claim.
Expensive phases, official datasets, CUDA scheduling, aggregation, and paper
rendering remain unavailable until their scientific contracts are accepted.
"""

from __future__ import annotations

import io
import json
import math
import os
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Mapping

import numpy as np

from gbdn.artifacts import (
    NA_ID,
    SCHEMA_VERSION,
    ArtifactValidationError,
    AtomicRunBundle,
    PredictionArtifactManifest,
    ResumeDecision,
    ResumeState,
    RunConfigRecord,
    RunIdentity,
    RunMode,
    RunResultRecord,
    canonical_json_bytes,
    canonical_json_sha256,
    capture_environment_metadata,
    capture_source_metadata,
    classify_resume,
)


_PLAN_KEYS: Final[frozenset[str]] = frozenset(
    {
        "claim_status",
        "device",
        "jobs",
        "plan_name",
        "plan_version",
        "schema_version",
    }
)
_JOB_KEYS: Final[frozenset[str]] = frozenset(
    {"dataset", "experiment", "metric", "model", "seed", "split", "trial"}
)
_EXPECTED_JOB: Final[dict[str, Any]] = {
    "dataset": "synthetic-fixed-binary-v1",
    "experiment": "submission_cpu_smoke",
    "metric": "accuracy",
    "model": "fixed-threshold-oracle",
    "seed": 0,
    "split": 0,
    "trial": 0,
}
_PREDICTION_FORMAT: Final[str] = "synthetic_binary_logits_labels_v1"
_METRIC_TOLERANCE: Final[float] = 1e-12
_MAX_PREDICTION_ARCHIVE_BYTES: Final[int] = 1024 * 1024
_MAX_PREDICTION_MEMBER_BYTES: Final[int] = 64 * 1024
_GATE_A_ACCEPTANCE_PATH: Final[Path] = Path(
    "configs/submission/frozen/gate_a_acceptance.json"
)


@dataclass(frozen=True)
class SmokePlan:
    """The validated frozen plan and metadata for exactly one CPU job."""

    repository_root: Path
    config_path: Path
    frozen_config: Mapping[str, Any]
    config: RunConfigRecord

    @property
    def identity(self) -> RunIdentity:
        return self.config.identity

    def inventory(self) -> dict[str, Any]:
        decision = classify_smoke_resume(self)
        return {
            "claim_status": "diagnostic-only",
            "device": "cpu",
            "job_count": 1,
            "repository_root": str(self.repository_root),
            "run_id": self.identity.run_id,
            "run_mode": self.config.run_mode.value,
            "state": "pending" if decision is None else decision.state.value,
        }


@dataclass(frozen=True)
class SmokeExecution:
    """Outcome of a parent orchestration call."""

    run_id: str
    state: str
    bundle_path: Path
    metric: float
    worker_pid: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_path": str(self.bundle_path),
            "metric": self.metric,
            "run_id": self.run_id,
            "state": self.state,
            "worker_pid": self.worker_pid,
        }


def _require_exact_keys(value: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    observed = set(value)
    if observed != set(expected):
        raise ArtifactValidationError(
            f"{label} keys mismatch; missing={sorted(set(expected) - observed)}, "
            f"extra={sorted(observed - set(expected))}"
        )


def _load_frozen_plan(path: Path) -> Mapping[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ArtifactValidationError("smoke config must be a regular file")
    payload = path.read_bytes()
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise ArtifactValidationError(f"duplicate smoke config key: {key}")
            result[key] = item
        return result

    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError("smoke config must be valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ArtifactValidationError("smoke config must be a JSON object")
    _require_exact_keys(value, _PLAN_KEYS, "smoke plan")
    if value["schema_version"] != SCHEMA_VERSION:
        raise ArtifactValidationError("unsupported smoke plan schema_version")
    if value["plan_name"] != "gbdn-stage1-cpu-smoke" or value["plan_version"] != 1:
        raise ArtifactValidationError("unsupported smoke plan identity")
    if value["claim_status"] != "diagnostic-only":
        raise ArtifactValidationError("Stage-1 smoke must remain diagnostic-only")
    if value["device"] != "cpu":
        raise ArtifactValidationError("Stage-1 smoke only permits device='cpu'")
    jobs = value["jobs"]
    if not isinstance(jobs, list) or len(jobs) != 1 or not isinstance(jobs[0], dict):
        raise ArtifactValidationError("Stage-1 smoke plan must contain exactly one job")
    _require_exact_keys(jobs[0], _JOB_KEYS, "smoke job")
    if jobs[0] != _EXPECTED_JOB:
        raise ArtifactValidationError("Stage-1 smoke job differs from the frozen contract")
    return value


def _require_inside_repository(path: Path, repository_root: Path, label: str) -> Path:
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(repository_root)
    except ValueError as exc:
        raise ArtifactValidationError(f"{label} must be inside repository_root") from exc
    return resolved


def _require_gate_a_acceptance(repository_root: Path) -> None:
    """Fail closed until a reviewed, source-bound Gate-A token is installed.

    The token schema is intentionally not implemented in this Stage-1 slice:
    the independent reviewer and orchestrator must first freeze that contract.
    Merely creating a file at this location therefore cannot unlock execution.
    """

    token = repository_root / _GATE_A_ACCEPTANCE_PATH
    if not token.exists():
        raise ArtifactValidationError(
            "claim-bearing mode is blocked: independent Gate-A acceptance token is absent"
        )
    raise ArtifactValidationError(
        "claim-bearing mode is blocked: Gate-A acceptance-token schema is not yet frozen"
    )


def build_smoke_plan(
    *,
    repository_root: str | Path,
    config_path: str | Path,
    run_mode: str | RunMode = RunMode.SMOKE,
) -> SmokePlan:
    """Validate the frozen CPU plan and bind it to source and environment.

    Only ``RunMode.SMOKE`` may execute. Other modes fail closed behind the
    independently reviewed Gate-A acceptance contract.
    """

    root = Path(repository_root).resolve(strict=True)
    requested_config = Path(config_path)
    config = _require_inside_repository(
        requested_config if requested_config.is_absolute() else root / requested_config,
        root,
        "config_path",
    )
    lock = _require_inside_repository(root / "requirements.lock", root, "dependency lock")
    mode = RunMode(run_mode)
    frozen = _load_frozen_plan(config)
    source = capture_source_metadata(root, full_run=mode is not RunMode.SMOKE)
    if mode is not RunMode.SMOKE:
        _require_gate_a_acceptance(root)
    environment = capture_environment_metadata(lock, repository_root=root)
    if mode is RunMode.SMOKE and environment.cuda_visible_devices != "-1":
        raise ArtifactValidationError(
            "diagnostic smoke requires CUDA_VISIBLE_DEVICES=-1 before plan construction"
        )
    dataset_payload = canonical_json_bytes(
        {
            "labels": [0, 1, 1, 0, 1, 0],
            "logits": [-2.0, 3.0, -0.4, 0.2, 1.0, -1.0],
            "name": _EXPECTED_JOB["dataset"],
        }
    )
    identity = RunIdentity(
        schema_version=SCHEMA_VERSION,
        experiment=_EXPECTED_JOB["experiment"],
        dataset_name=_EXPECTED_JOB["dataset"],
        dataset_sha256=canonical_json_sha256(json.loads(dataset_payload)),
        model_name=_EXPECTED_JOB["model"],
        model_variant="diagnostic",
        split_id=_EXPECTED_JOB["split"],
        seed=_EXPECTED_JOB["seed"],
        trial_id=_EXPECTED_JOB["trial"],
        frozen_config_sha256=canonical_json_sha256(frozen),
        source_sha256=source.source_sha256,
        dependency_lock_sha256=environment.dependency_lock_sha256,
        baseline_upstream_commit=NA_ID,
        precision_mode="deterministic-fp64-cpu",
    )
    record = RunConfigRecord.create(
        identity=identity,
        frozen_config=frozen,
        source=source,
        environment=environment,
        run_mode=mode,
    )
    return SmokePlan(root, config, frozen, record)


def _synthetic_predictions() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    labels = np.asarray([0, 1, 1, 0, 1, 0], dtype=np.int64)
    logits = np.asarray([-2.0, 3.0, -0.4, 0.2, 1.0, -1.0], dtype=np.float64)
    indices = np.arange(labels.size, dtype=np.int64)
    return indices, labels, logits


def _reported_smoke_accuracy(labels: np.ndarray, logits: np.ndarray) -> float:
    """Compute the worker's reported metric without reading the artifact."""

    correct = sum(
        int((float(score) >= 0.0) == bool(int(label)))
        for label, score in zip(labels.tolist(), logits.tolist(), strict=True)
    )
    return float(correct / labels.size)


def _prediction_bytes(run_id: str) -> bytes:
    indices, labels, logits = _synthetic_predictions()
    stream = io.BytesIO()
    np.savez_compressed(
        stream,
        indices=indices,
        labels=labels,
        logits=logits,
        run_id=np.asarray(run_id),
        split_id=np.asarray(0, dtype=np.int64),
    )
    return stream.getvalue()


def recompute_smoke_accuracy(prediction_path: str | Path, *, expected_run_id: str) -> float:
    """Independently recompute accuracy solely from a saved prediction file."""

    path = Path(prediction_path)
    if path.is_symlink() or not path.is_file():
        raise ArtifactValidationError("prediction path must be a regular file")
    if path.stat().st_size > _MAX_PREDICTION_ARCHIVE_BYTES:
        raise ArtifactValidationError("prediction archive exceeds the smoke size limit")
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if (
                len(members) != 5
                or any(member.is_dir() for member in members)
                or any(
                    member.file_size > _MAX_PREDICTION_MEMBER_BYTES
                    for member in members
                )
            ):
                raise ArtifactValidationError(
                    "prediction archive has unsafe member cardinality or size"
                )
        with np.load(path, allow_pickle=False) as stored:
            if set(stored.files) != {"indices", "labels", "logits", "run_id", "split_id"}:
                raise ArtifactValidationError("prediction arrays do not match smoke schema")
            indices = np.asarray(stored["indices"])
            labels = np.asarray(stored["labels"])
            logits = np.asarray(stored["logits"])
            run_id = str(np.asarray(stored["run_id"]).item())
            split_id = int(np.asarray(stored["split_id"]).item())
    except ArtifactValidationError:
        raise
    except (OSError, ValueError, TypeError, zipfile.BadZipFile) as exc:
        raise ArtifactValidationError("invalid smoke prediction archive") from exc
    if run_id != expected_run_id:
        raise ArtifactValidationError("prediction archive belongs to another run")
    if split_id != 0:
        raise ArtifactValidationError("prediction archive has the wrong split")
    if labels.dtype != np.int64 or indices.dtype != np.int64 or logits.dtype != np.float64:
        raise ArtifactValidationError("prediction arrays have the wrong dtype")
    if labels.shape != (6,) or logits.shape != labels.shape or indices.shape != labels.shape:
        raise ArtifactValidationError("prediction arrays have the wrong shape")
    if not np.array_equal(indices, np.arange(labels.size, dtype=np.int64)):
        raise ArtifactValidationError("prediction indices are not canonical")
    if not np.all(np.isin(labels, (0, 1))) or not np.all(np.isfinite(logits)):
        raise ArtifactValidationError("prediction values are invalid")
    predictions = (logits >= 0.0).astype(np.int64)
    return float(np.count_nonzero(predictions == labels) / labels.size)


def _read_completed_result(
    plan: SmokePlan, bundle_path: Path
) -> tuple[RunResultRecord, float, int]:
    result_path = bundle_path / "result.json"
    try:
        result = RunResultRecord.from_dict(json.loads(result_path.read_text(encoding="utf-8")))
        if result.identity != plan.identity:
            raise ArtifactValidationError("completed smoke result identity differs from plan")
        if result.source != plan.config.source:
            raise ArtifactValidationError("completed smoke source metadata differs from plan")
        if result.environment != plan.config.environment:
            raise ArtifactValidationError(
                "completed smoke environment metadata differs from plan"
            )
        payload = json.loads(result.result_payload_json)
        if set(payload) != {"claim_status", "compute", "diagnostics", "metrics", "selection"}:
            raise ArtifactValidationError("completed smoke result has unexpected payload keys")
        if payload["claim_status"] != "diagnostic-only":
            raise ArtifactValidationError("completed smoke result is not diagnostic-only")
        if payload["selection"] != {"policy": "none", "test_used_for_selection": False}:
            raise ArtifactValidationError("completed smoke result has an invalid selection policy")
        if payload["diagnostics"] != {
            "independent_metric_tolerance": _METRIC_TOLERANCE
        }:
            raise ArtifactValidationError("completed smoke result has invalid diagnostics")
        if set(payload["metrics"]) != {"test"} or set(payload["metrics"]["test"]) != {
            "accuracy"
        }:
            raise ArtifactValidationError("completed smoke result has invalid metrics")
        compute = payload["compute"]
        if set(compute) != {
            "device",
            "duration_seconds",
            "peak_cuda_memory_bytes",
            "worker_pid",
        }:
            raise ArtifactValidationError("completed smoke result has invalid compute keys")
        if compute["device"] != "cpu" or compute["peak_cuda_memory_bytes"] != 0:
            raise ArtifactValidationError("completed smoke result is not CPU-only")
        duration = float(compute["duration_seconds"])
        recorded = float(payload["metrics"]["test"]["accuracy"])
        worker_pid = int(compute["worker_pid"])
        if not math.isfinite(duration) or duration < 0.0 or worker_pid <= 0:
            raise ArtifactValidationError("completed smoke compute values are invalid")
        if not math.isfinite(recorded) or not 0.0 <= recorded <= 1.0:
            raise ArtifactValidationError("completed smoke metric is invalid")
    except ArtifactValidationError:
        raise
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError("completed smoke result has an invalid payload") from exc
    recomputed = recompute_smoke_accuracy(
        bundle_path / result.predictions.path,
        expected_run_id=plan.identity.run_id,
    )
    if abs(recorded - recomputed) > _METRIC_TOLERANCE:
        raise ArtifactValidationError(
            f"saved accuracy drift: recorded={recorded}, recomputed={recomputed}"
        )
    return result, recomputed, worker_pid


def classify_smoke_resume(plan: SmokePlan) -> ResumeDecision | None:
    """Classify artifact state and require metric agreement before a skip."""

    decision = classify_resume(plan.identity, repository_root=plan.repository_root)
    if decision is None or decision.state is not ResumeState.MATCHING_COMPLETE:
        return decision
    try:
        _read_completed_result(plan, decision.path)
    except (ArtifactValidationError, OSError) as exc:
        return ResumeDecision(
            state=ResumeState.CORRUPT,
            path=decision.path,
            reason=f"independent smoke verification failed: {exc}",
        )
    return decision


def execute_smoke_job(plan: SmokePlan, *, expected_run_id: str) -> SmokeExecution:
    """Execute the one diagnostic job in the current worker process."""

    if expected_run_id != plan.identity.run_id:
        raise ArtifactValidationError("worker run_id differs from the frozen plan")
    decision = classify_smoke_resume(plan)
    if decision is not None:
        if decision.state is ResumeState.MATCHING_COMPLETE:
            _, metric, worker_pid = _read_completed_result(plan, decision.path)
            return SmokeExecution(
                plan.identity.run_id, "skipped", decision.path, metric, worker_pid
            )
        raise ArtifactValidationError(
            f"unsafe resume state {decision.state.value}: {decision.reason}"
        )

    started = time.perf_counter()
    bundle = AtomicRunBundle(plan.config, repository_root=plan.repository_root)
    _, labels, logits = _synthetic_predictions()
    reported_metric = _reported_smoke_accuracy(labels, logits)
    prediction_file = bundle.write_bytes(
        "predictions.npz", _prediction_bytes(plan.identity.run_id)
    )
    prediction = PredictionArtifactManifest.from_file_manifest(
        plan.identity.run_id,
        prediction_file,
        format=_PREDICTION_FORMAT,
    )
    independently_recomputed = recompute_smoke_accuracy(
        bundle.staging_path / prediction.path,
        expected_run_id=plan.identity.run_id,
    )
    if abs(reported_metric - independently_recomputed) > _METRIC_TOLERANCE:
        raise ArtifactValidationError(
            "worker metric disagrees with independent prediction recomputation"
        )
    result = RunResultRecord.create(
        identity=plan.identity,
        predictions=prediction,
        result_payload={
            "claim_status": "diagnostic-only",
            "compute": {
                "device": "cpu",
                "duration_seconds": float(time.perf_counter() - started),
                "peak_cuda_memory_bytes": 0,
                "worker_pid": os.getpid(),
            },
            "diagnostics": {"independent_metric_tolerance": _METRIC_TOLERANCE},
            "metrics": {"test": {"accuracy": reported_metric}},
            "selection": {"policy": "none", "test_used_for_selection": False},
        },
        source=plan.config.source,
        environment=plan.config.environment,
    )
    final = bundle.commit(result)
    _, verified_metric, worker_pid = _read_completed_result(plan, final)
    return SmokeExecution(plan.identity.run_id, "completed", final, verified_metric, worker_pid)


def run_smoke_subprocess(
    plan: SmokePlan,
    *,
    entry_point: str | Path,
    timeout_seconds: float = 60.0,
) -> SmokeExecution:
    """Run or safely resume the smoke job through one isolated subprocess."""

    decision = classify_smoke_resume(plan)
    if decision is not None:
        if decision.state is ResumeState.MATCHING_COMPLETE:
            _, metric, worker_pid = _read_completed_result(plan, decision.path)
            return SmokeExecution(
                plan.identity.run_id, "skipped", decision.path, metric, worker_pid
            )
        raise ArtifactValidationError(
            f"unsafe resume state {decision.state.value}: {decision.reason}"
        )
    command = [
        sys.executable,
        str(Path(entry_point).resolve(strict=True)),
        "run-job",
        "--repository-root",
        str(plan.repository_root),
        "--config",
        str(plan.config_path),
        "--run-id",
        plan.identity.run_id,
        "--mode",
        plan.config.run_mode.value,
    ]
    entry = Path(entry_point).resolve(strict=True)
    expected_entry = (plan.repository_root / "scripts" / "run_submission.py").resolve(
        strict=True
    )
    if entry != expected_entry or entry.is_symlink() or not entry.is_file():
        raise ArtifactValidationError(
            "smoke worker entry point must be the canonical repository script"
        )
    command[1] = str(entry)
    child_environment = os.environ.copy()
    child_environment["CUDA_VISIBLE_DEVICES"] = "-1"
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        env=child_environment,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "isolated smoke worker failed "
            f"(exit={completed.returncode}): {completed.stderr.strip()}"
        )
    decision = classify_smoke_resume(plan)
    if decision is None or decision.state is not ResumeState.MATCHING_COMPLETE:
        state = "missing" if decision is None else decision.state.value
        raise ArtifactValidationError(
            f"worker did not produce a verified complete bundle: {state}"
        )
    _, metric, worker_pid = _read_completed_result(plan, decision.path)
    return SmokeExecution(plan.identity.run_id, "completed", decision.path, metric, worker_pid)


def require_canonical_output_root(repository_root: str | Path, output_root: str | Path) -> Path:
    """Reject output roots other than the canonical results_submission tree."""

    root = Path(repository_root).resolve(strict=True)
    output = Path(output_root)
    resolved = (output if output.is_absolute() else root / output).resolve(strict=False)
    expected = (root / "results_submission").resolve(strict=False)
    try:
        expected.relative_to(root)
    except ValueError as exc:
        raise ArtifactValidationError(
            "repository_root/results_submission resolves outside the repository"
        ) from exc
    if resolved != expected:
        raise ArtifactValidationError("output_root must be repository_root/results_submission")
    return resolved


__all__ = [
    "SmokeExecution",
    "SmokePlan",
    "build_smoke_plan",
    "classify_smoke_resume",
    "execute_smoke_job",
    "recompute_smoke_accuracy",
    "require_canonical_output_root",
    "run_smoke_subprocess",
]
