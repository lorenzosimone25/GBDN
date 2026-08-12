"""Immutable full-grid run-plan validation and read-only resume inventory."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from gbdn.artifacts import (
    NA_ID,
    ArtifactValidationError,
    ResumeState,
    RunConfigRecord,
    RunMode,
    classify_resume,
    sha256_file,
)
from gbdn.baseline_contract import ConfirmatoryPlan, validate_plan_registry_binding
from gbdn.heterophily_contract import (
    DATASET_REGISTRY,
    LOCAL_METHOD_CONFIG_PATHS,
    OFFICIAL_SPLITS,
    TRAINING_SEEDS,
)


RUN_PLAN_SCHEMA = "gbdn-run-plan-v1"
_MAX_PLAN_BYTES = 32 * 1024 * 1024


@dataclass(frozen=True)
class ValidatedRunPlan:
    confirmatory: ConfirmatoryPlan
    jobs: tuple[RunConfigRecord, ...]
    confirmatory_plan_sha256: str
    baseline_registry_sha256: str


@dataclass(frozen=True)
class RunPlanInventory:
    total: int
    pending: int
    complete: int
    partial: int
    corrupt: int
    conflict: int

    def to_dict(self) -> dict[str, int]:
        return {
            "complete": self.complete,
            "conflict": self.conflict,
            "corrupt": self.corrupt,
            "partial": self.partial,
            "pending": self.pending,
            "total": self.total,
        }


def _load(path: str | Path) -> Mapping[str, Any]:
    target = Path(path)
    if target.is_symlink() or not target.is_file() or target.stat().st_size > _MAX_PLAN_BYTES:
        raise ArtifactValidationError("run plan must be a bounded regular file")
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError("run plan must be valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ArtifactValidationError("run plan root must be an object")
    return value


def validate_run_plan(
    run_plan_path: str | Path,
    *,
    confirmatory_plan_path: str | Path,
    baseline_registry_path: str | Path,
    repository_root: str | Path,
) -> ValidatedRunPlan:
    """Require the exact method x dataset x split x seed confirmatory grid."""

    confirmatory, admitted_baselines = validate_plan_registry_binding(
        confirmatory_plan_path,
        baseline_registry_path,
        repository_root=repository_root,
    )
    data = _load(run_plan_path)
    if set(data) != {
        "baseline_registry_sha256",
        "confirmatory_plan_sha256",
        "jobs",
        "schema_version",
    }:
        raise ArtifactValidationError("run plan keys do not match the frozen schema")
    if data["schema_version"] != RUN_PLAN_SCHEMA:
        raise ArtifactValidationError("run plan schema is invalid")
    confirm_hash = sha256_file(confirmatory_plan_path)
    registry_hash = sha256_file(baseline_registry_path)
    if data["confirmatory_plan_sha256"] != confirm_hash:
        raise ArtifactValidationError("run plan confirmatory-plan hash mismatch")
    if data["baseline_registry_sha256"] != registry_hash:
        raise ArtifactValidationError("run plan baseline-registry hash mismatch")
    raw_jobs = data["jobs"]
    if not isinstance(raw_jobs, list):
        raise ArtifactValidationError("run plan jobs must be a list")
    jobs = tuple(RunConfigRecord.from_dict(value) for value in raw_jobs)
    expected = {
        (method, dataset, split, seed)
        for method in confirmatory.methods
        for dataset in DATASET_REGISTRY
        for split in OFFICIAL_SPLITS
        for seed in TRAINING_SEEDS
    }
    observed: set[tuple[str, str, int, int]] = set()
    run_ids: set[str] = set()
    source = None
    environment = None
    baseline_commits = {
        baseline.name: baseline.source_commit for baseline in admitted_baselines
    }
    baseline_configs = {
        baseline.name: (baseline.reference_config_path, baseline.reference_config_sha256)
        for baseline in admitted_baselines
    }
    for job in jobs:
        identity = job.identity
        if job.run_mode is not RunMode.FULL:
            raise ArtifactValidationError("confirmatory run-plan jobs must use full mode")
        if identity.experiment != "heterophily_confirm" or identity.model_variant != "frozen-confirmatory":
            raise ArtifactValidationError("run-plan job experiment/variant is invalid")
        if identity.trial_id != 0 or type(identity.split_id) is not int or type(identity.seed) is not int:
            raise ArtifactValidationError("confirmatory job split/seed/trial is invalid")
        key = (identity.model_name, identity.dataset_name, identity.split_id, identity.seed)
        if key in observed or identity.run_id in run_ids:
            raise ArtifactValidationError("duplicate logical job or run identity")
        observed.add(key)
        run_ids.add(identity.run_id)
        expected_upstream = baseline_commits.get(identity.model_name, NA_ID)
        if identity.baseline_upstream_commit != expected_upstream:
            raise ArtifactValidationError(
                "run-plan baseline implementation source commit is not registry-bound"
            )
        try:
            frozen = json.loads(job.frozen_config_json)
        except json.JSONDecodeError as exc:  # guarded by RunConfigRecord; defensive
            raise ArtifactValidationError("run-plan frozen config is invalid") from exc
        if identity.model_name in baseline_configs:
            method_config_path, method_config_sha256 = baseline_configs[identity.model_name]
        else:
            method_config_path = LOCAL_METHOD_CONFIG_PATHS.get(identity.model_name)
            if method_config_path is None:
                raise ArtifactValidationError("run-plan method has no frozen configuration path")
            config_target = Path(repository_root) / method_config_path
            if config_target.is_symlink() or not config_target.is_file():
                raise ArtifactValidationError("local method configuration is unavailable")
            method_config_sha256 = sha256_file(config_target)
        required_frozen = {
            "baseline_registry_sha256": registry_hash,
            "confirmatory_plan_sha256": confirm_hash,
            "dataset": identity.dataset_name,
            "method": identity.model_name,
            "method_config_path": method_config_path,
            "method_config_sha256": method_config_sha256,
            "seed": identity.seed,
            "split": identity.split_id,
            "trial_budget": confirmatory.trial_budget_per_method_dataset,
        }
        if frozen != required_frozen:
            raise ArtifactValidationError("run-plan frozen config is not plan/identity-bound")
        if job.source.dirty or job.source.dirty_override:
            raise ArtifactValidationError("confirmatory run-plan source must be clean")
        visible = job.environment.cuda_visible_devices
        if (
            not isinstance(visible, str)
            or not visible
            or "," in visible
            or visible == "-1"
            or job.environment.cublas_workspace_config != ":4096:8"
            or job.environment.pythonhashseed != "0"
        ):
            raise ArtifactValidationError("run-plan environment does not isolate one deterministic GPU")
        if source is None:
            source, environment = job.source, job.environment
        elif job.source != source or job.environment != environment:
            raise ArtifactValidationError("run-plan jobs do not share one source/environment")
    missing = sorted(expected - observed)
    extra = sorted(observed - expected)
    if missing or extra:
        raise ArtifactValidationError(
            f"run-plan grid mismatch; missing={len(missing)}, extra={len(extra)}"
        )
    return ValidatedRunPlan(confirmatory, jobs, confirm_hash, registry_hash)


def inventory_run_plan(
    plan: ValidatedRunPlan, *, repository_root: str | Path
) -> RunPlanInventory:
    """Classify immutable bundle state without writing or executing jobs."""

    counts = {"pending": 0, "complete": 0, "partial": 0, "corrupt": 0, "conflict": 0}
    for job in plan.jobs:
        decision = classify_resume(job.identity, repository_root=repository_root)
        if decision is None:
            counts["pending"] += 1
        elif decision.state is ResumeState.MATCHING_COMPLETE:
            counts["complete"] += 1
        else:
            counts[decision.state.value] += 1
    return RunPlanInventory(len(plan.jobs), **counts)


__all__ = [
    "RUN_PLAN_SCHEMA",
    "RunPlanInventory",
    "ValidatedRunPlan",
    "inventory_run_plan",
    "validate_run_plan",
]
