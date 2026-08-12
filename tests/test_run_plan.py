from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from gbdn.artifacts import (
    NA_ID,
    SCHEMA_VERSION,
    ArtifactValidationError,
    EnvironmentMetadata,
    RunConfigRecord,
    RunIdentity,
    RunMode,
    SourceMetadata,
    canonical_json_sha256,
    sha256_file,
)
from gbdn.baseline_contract import PLAN_SCHEMA, REGISTRY_SCHEMA
from gbdn.heterophily_contract import DATASET_REGISTRY, OFFICIAL_SPLITS, TRAINING_SEEDS
from gbdn.run_plan import RUN_PLAN_SCHEMA, inventory_run_plan, validate_run_plan


BASELINES = ("CayleyNet", "ChebNetII")


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def _inputs(root: Path) -> tuple[Path, Path, Path]:
    records = []
    for index, method in enumerate(BASELINES):
        slug = method.lower()
        paths = (
            f"licenses/{slug}.txt",
            f"src/baselines/{slug}.py",
            f"configs/baselines/{slug}.json",
        )
        for relative in paths:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{method}:{relative}\n", encoding="utf-8")
        records.append(
            {
                "license": {"notice_path": paths[0], "spdx": "MIT"},
                "name": method,
                "parity": {
                    "dataset": "upstream-fixture",
                    "expected": 0.8,
                    "metric": "accuracy",
                    "observed": 0.8,
                    "status": "PASS",
                    "tolerance": 0.001,
                },
                "protocols": ["heterophily"],
                "repository_url": f"https://example.org/{slug}",
                "status": "VERIFIED",
                "upstream_commit": f"{index + 1:040x}",
                "verification": {"parameter_count": True, "spmv_count": True},
                "wrapper": {
                    "local_patch_sha256": sha256_file(root / paths[1]),
                    "path": paths[1],
                    "upstream_config_path": paths[2],
                },
            }
        )
    registry_path = root / "baseline_registry.json"
    _write(registry_path, {"baselines": records, "schema_version": REGISTRY_SCHEMA})
    plan_path = root / "confirmatory_plan.json"
    _write(
        plan_path,
        {
            "baseline_registry_sha256": sha256_file(registry_path),
            "datasets": list(DATASET_REGISTRY),
            "methods": ["TightGBDN", *BASELINES],
            "official_splits": list(OFFICIAL_SPLITS),
            "primary_baselines": list(BASELINES),
            "practical_tie_thresholds": {dataset: 0.005 for dataset in DATASET_REGISTRY},
            "schema_version": PLAN_SCHEMA,
            "selection": {
                "equal_validation_trial_budget": True,
                "freeze_before_test": True,
                "test_process_isolated": True,
                "test_used_for_selection": False,
            },
            "training_seeds": list(TRAINING_SEEDS),
            "trial_budget_per_method_dataset": 10,
        },
    )
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
    baseline_commits = {method: f"{index + 1:040x}" for index, method in enumerate(BASELINES)}
    jobs = []
    for method in ("TightGBDN", *BASELINES):
        for dataset in DATASET_REGISTRY:
            for split in OFFICIAL_SPLITS:
                for seed in TRAINING_SEEDS:
                    frozen = {
                        "baseline_registry_sha256": sha256_file(registry_path),
                        "confirmatory_plan_sha256": sha256_file(plan_path),
                        "dataset": dataset,
                        "method": method,
                        "seed": seed,
                        "split": split,
                        "trial_budget": 10,
                    }
                    identity = RunIdentity(
                        SCHEMA_VERSION,
                        "heterophily_confirm",
                        dataset,
                        canonical_json_sha256({"dataset": dataset}),
                        method,
                        "frozen-confirmatory",
                        split,
                        seed,
                        0,
                        canonical_json_sha256(frozen),
                        source.source_sha256,
                        environment.dependency_lock_sha256,
                        baseline_commits.get(method, NA_ID),
                        "deterministic-fp32",
                    )
                    jobs.append(
                        RunConfigRecord.create(
                            identity=identity,
                            frozen_config=frozen,
                            source=source,
                            environment=environment,
                            run_mode=RunMode.FULL,
                            created_at_utc="2026-08-12T12:00:00Z",
                        ).to_dict()
                    )
    run_plan_path = root / "run_plan.json"
    _write(
        run_plan_path,
        {
            "baseline_registry_sha256": sha256_file(registry_path),
            "confirmatory_plan_sha256": sha256_file(plan_path),
            "jobs": jobs,
            "schema_version": RUN_PLAN_SCHEMA,
        },
    )
    return run_plan_path, plan_path, registry_path


def test_full_grid_validates_and_read_only_inventory_is_all_pending(tmp_path):
    run_plan, confirmatory, registry = _inputs(tmp_path)
    validated = validate_run_plan(
        run_plan,
        confirmatory_plan_path=confirmatory,
        baseline_registry_path=registry,
        repository_root=tmp_path,
    )
    assert len(validated.jobs) == 3 * 5 * 10 * 3
    inventory = inventory_run_plan(validated, repository_root=tmp_path)
    assert inventory.to_dict() == {
        "complete": 0,
        "conflict": 0,
        "corrupt": 0,
        "partial": 0,
        "pending": 450,
        "total": 450,
    }
    assert not (tmp_path / "results_submission").exists()


def test_run_plan_rejects_missing_and_duplicate_logical_jobs(tmp_path):
    run_plan, confirmatory, registry = _inputs(tmp_path)
    data = json.loads(run_plan.read_text(encoding="utf-8"))
    data["jobs"].pop()
    _write(run_plan, data)
    with pytest.raises(ArtifactValidationError, match="grid mismatch"):
        validate_run_plan(run_plan, confirmatory_plan_path=confirmatory, baseline_registry_path=registry, repository_root=tmp_path)

    run_plan, confirmatory, registry = _inputs(tmp_path / "duplicate")
    data = json.loads(run_plan.read_text(encoding="utf-8"))
    data["jobs"].append(data["jobs"][0])
    _write(run_plan, data)
    with pytest.raises(ArtifactValidationError, match="duplicate"):
        validate_run_plan(run_plan, confirmatory_plan_path=confirmatory, baseline_registry_path=registry, repository_root=tmp_path / "duplicate")


def test_run_plan_rejects_hash_drift_smoke_mode_and_mixed_source(tmp_path):
    run_plan, confirmatory, registry = _inputs(tmp_path)
    data = json.loads(run_plan.read_text(encoding="utf-8"))
    data["confirmatory_plan_sha256"] = "f" * 64
    _write(run_plan, data)
    with pytest.raises(ArtifactValidationError, match="confirmatory-plan hash"):
        validate_run_plan(run_plan, confirmatory_plan_path=confirmatory, baseline_registry_path=registry, repository_root=tmp_path)

    run_plan, confirmatory, registry = _inputs(tmp_path / "mode")
    data = json.loads(run_plan.read_text(encoding="utf-8"))
    data["jobs"][0]["run_mode"] = "smoke"
    _write(run_plan, data)
    with pytest.raises(ArtifactValidationError, match="full mode"):
        validate_run_plan(run_plan, confirmatory_plan_path=confirmatory, baseline_registry_path=registry, repository_root=tmp_path / "mode")

    run_plan, confirmatory, registry = _inputs(tmp_path / "source")
    data = json.loads(run_plan.read_text(encoding="utf-8"))
    changed_source = dict(data["jobs"][0]["source"])
    changed_source["repository_commit"] = "e" * 40
    changed_source["repository_tree"] = "f" * 40
    changed_source["source_sha256"] = canonical_json_sha256(
        {
            "dirty_fingerprint_sha256": "clean",
            "repository_commit": "e" * 40,
            "repository_tree": "f" * 40,
        }
    )
    data["jobs"][0]["source"] = changed_source
    data["jobs"][0]["identity"]["source_sha256"] = changed_source["source_sha256"]
    data["jobs"][0]["run_id"] = RunIdentity.from_dict(data["jobs"][0]["identity"]).run_id
    _write(run_plan, data)
    with pytest.raises(ArtifactValidationError, match="source/environment"):
        validate_run_plan(run_plan, confirmatory_plan_path=confirmatory, baseline_registry_path=registry, repository_root=tmp_path / "source")


def test_run_plan_rejects_unbound_baseline_config_and_gpu_environment(tmp_path):
    run_plan, confirmatory, registry = _inputs(tmp_path)
    data = json.loads(run_plan.read_text(encoding="utf-8"))
    baseline_job = next(job for job in data["jobs"] if job["identity"]["model"]["name"] == "CayleyNet")
    baseline_job["identity"]["baseline_upstream_commit"] = "f" * 40
    baseline_job["run_id"] = RunIdentity.from_dict(baseline_job["identity"]).run_id
    _write(run_plan, data)
    with pytest.raises(ArtifactValidationError, match="upstream commit"):
        validate_run_plan(run_plan, confirmatory_plan_path=confirmatory, baseline_registry_path=registry, repository_root=tmp_path)

    run_plan, confirmatory, registry = _inputs(tmp_path / "config")
    data = json.loads(run_plan.read_text(encoding="utf-8"))
    data["jobs"][0]["frozen_config"]["trial_budget"] = 9
    data["jobs"][0]["frozen_config_sha256"] = canonical_json_sha256(data["jobs"][0]["frozen_config"])
    data["jobs"][0]["identity"]["frozen_config_sha256"] = data["jobs"][0]["frozen_config_sha256"]
    data["jobs"][0]["run_id"] = RunIdentity.from_dict(data["jobs"][0]["identity"]).run_id
    _write(run_plan, data)
    with pytest.raises(ArtifactValidationError, match="plan/identity-bound"):
        validate_run_plan(run_plan, confirmatory_plan_path=confirmatory, baseline_registry_path=registry, repository_root=tmp_path / "config")

    run_plan, confirmatory, registry = _inputs(tmp_path / "gpu")
    data = json.loads(run_plan.read_text(encoding="utf-8"))
    for job in data["jobs"]:
        job["environment"]["cuda_visible_devices"] = "0,1"
    _write(run_plan, data)
    with pytest.raises(ArtifactValidationError, match="one deterministic GPU"):
        validate_run_plan(run_plan, confirmatory_plan_path=confirmatory, baseline_registry_path=registry, repository_root=tmp_path / "gpu")
