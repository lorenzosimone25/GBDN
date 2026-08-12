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
from gbdn.baseline_contract import (
    LOCAL_SEARCH,
    PARITY_EVIDENCE_SCHEMA,
    PLAN_SCHEMA,
    REGISTRY_SCHEMA,
    SEARCH_SPACE_SCHEMA,
    SELECTION_EVIDENCE_SCHEMA,
)
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
        paths = {
            "license": f"licenses/{slug}.txt",
            "wrapper": f"src/baselines/{slug}.py",
            "final": f"configs/baselines/{slug}.json",
            "provenance": f"docs/baselines/{slug}_provenance.md",
            "oracle": f"tests/oracles/{slug}_oracle.py",
            "parity": f"tests/fixtures/baselines/{slug}_parity.json",
            "search": f"configs/search/{slug}.json",
            "selection": f"tests/fixtures/baselines/{slug}_selection.json",
            "test": f"tests/test_{slug}.py",
        }
        for relative in (
            paths["license"],
            paths["wrapper"],
            paths["provenance"],
            paths["oracle"],
            paths["test"],
        ):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{method}:{relative}\n", encoding="utf-8")
        _write(
            root / paths["final"],
            {
                "datasets": {
                    dataset: {"model": {}, "optimizer": {}, "training": {}}
                    for dataset in DATASET_REGISTRY
                },
                "method": method,
                "schema_version": "gbdn-heterophily-method-config-v1",
            },
        )
        _write(
            root / paths["search"],
            {
                "method": method,
                "parameters": {"model.K": {"role": "TUNED", "values": [2, 4]}},
                "schema_version": SEARCH_SPACE_SCHEMA,
                "status": "FROZEN_PRESPECIFIED",
            },
        )
        checks = {
            name: {"evidence": f"tests::{name}", "status": "PASS"}
            for name in (
                "independent_dense_operator_forward",
                "independent_dense_operator_gradients",
                "official_task_head_dispatch",
                "parameter_count",
                "spmv_count",
                "upstream_composition_forward",
                "upstream_composition_gradients",
            )
        }
        _write(
            root / paths["parity"],
            {
                "baseline": method,
                "checks": checks,
                "implementation_kind": "UPSTREAM_CODE",
                "independent_oracle_sha256": sha256_file(root / paths["oracle"]),
                "scope": "OPERATOR_COMPOSITION",
                "schema_version": PARITY_EVIDENCE_SCHEMA,
                "source_commit": f"{index + 1:040x}",
                "status": "PASS",
                "test_command": f"python -m pytest -q {paths['test']}",
                "test_path": paths["test"],
                "test_result": "7 passed",
                "test_sha256": sha256_file(root / paths["test"]),
                "wrapper_sha256": sha256_file(root / paths["wrapper"]),
            },
        )
        _write(
            root / paths["selection"],
            {
                "baseline": method,
                "configuration_kind": LOCAL_SEARCH,
                "final_config_sha256": sha256_file(root / paths["final"]),
                "schema_version": SELECTION_EVIDENCE_SCHEMA,
                "search_space_sha256": sha256_file(root / paths["search"]),
                "selection_partition": "validation",
                "status": "PASS",
                "test_used_for_selection": False,
                "trial_budget_per_dataset": 10,
            },
        )
        records.append(
            {
                "configuration": {
                    "budget_binding": "CONFIRMATORY_PLAN_EQUAL_TRIAL_BUDGET",
                    "final_configuration": {
                        "path": paths["final"],
                        "selection_evidence_path": paths["selection"],
                        "selection_evidence_sha256": sha256_file(root / paths["selection"]),
                        "sha256": sha256_file(root / paths["final"]),
                    },
                    "kind": LOCAL_SEARCH,
                    "search_space_path": paths["search"],
                    "search_space_sha256": sha256_file(root / paths["search"]),
                    "selection": {
                        "dataset_bindings": {
                            dataset: {
                                "selection_metric": spec.selection_metric,
                                "task_type": spec.task_type,
                            }
                            for dataset, spec in DATASET_REGISTRY.items()
                        },
                        "partition": "validation",
                        "test_used_for_selection": False,
                    },
                },
                "implementation": {
                    "equation_locator": "Eq. (3), p. 4",
                    "independent_oracle_path": paths["oracle"],
                    "independent_oracle_sha256": sha256_file(root / paths["oracle"]),
                    "kind": "UPSTREAM_CODE",
                    "paper_url": f"https://papers.example.org/{slug}",
                    "provenance_path": paths["provenance"],
                    "provenance_sha256": sha256_file(root / paths["provenance"]),
                    "source_commit": f"{index + 1:040x}",
                    "source_repository_url": f"https://example.org/{slug}",
                    "upstream_code_used": True,
                },
                "license": {
                    "notice_path": paths["license"],
                    "notice_sha256": sha256_file(root / paths["license"]),
                    "spdx": "MIT",
                },
                "name": method,
                "operator_parity": {
                    "evidence_path": paths["parity"],
                    "evidence_sha256": sha256_file(root / paths["parity"]),
                    "scope": "OPERATOR_COMPOSITION",
                    "status": "PASS",
                },
                "protocols": ["heterophily"],
                "status": "CONFIRMATORY_READY",
                "verification": {
                    "independent_operator_oracle": True,
                    "official_task_contract": True,
                    "parameter_count": True,
                    "spmv_count": True,
                },
                "wrapper": {
                    "path": paths["wrapper"],
                    "source_sha256": sha256_file(root / paths["wrapper"]),
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
    with pytest.raises(ArtifactValidationError, match="source commit"):
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
