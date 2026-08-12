from __future__ import annotations

import json
from pathlib import Path

import pytest

from gbdn.artifacts import ArtifactValidationError, sha256_file
from gbdn.baseline_contract import (
    LOCAL_SEARCH,
    PARITY_EVIDENCE_SCHEMA,
    PLAN_SCHEMA,
    REGISTRY_SCHEMA,
    SEARCH_SPACE_SCHEMA,
    SELECTION_EVIDENCE_SCHEMA,
    validate_baseline_registry,
    validate_confirmatory_plan,
    validate_plan_registry_binding,
)
from gbdn.heterophily_contract import DATASET_REGISTRY, OFFICIAL_SPLITS, TRAINING_SEEDS


BASELINE = "ChebNet"


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")), encoding="utf-8")


def _dataset_bindings() -> dict[str, dict[str, str]]:
    return {
        name: {"selection_metric": spec.selection_metric, "task_type": spec.task_type}
        for name, spec in DATASET_REGISTRY.items()
    }


def _search_space() -> dict:
    return {
        "method": BASELINE,
        "parameters": {
            "model.K": {"role": "TUNED", "values": [2, 4]},
            "model.dropout": {"role": "FIXED", "values": [0.0]},
        },
        "schema_version": SEARCH_SPACE_SCHEMA,
        "status": "FROZEN_PRESPECIFIED",
    }


def _files(root: Path) -> dict[str, str]:
    paths = {
        "license": "licenses/chebnet.txt",
        "wrapper": "src/baselines/chebnet.py",
        "provenance": "docs/baselines/chebnet.md",
        "oracle": "tests/oracles/chebnet.py",
        "search": "configs/search/chebnet.json",
        "parity": "results_submission/reports/chebnet_operator_parity.json",
        "final": "configs/frozen/chebnet.json",
        "selection": "results_submission/reports/chebnet_selection.json",
        "test": "tests/test_chebnet.py",
    }
    for key in ("license", "wrapper", "provenance", "oracle", "test"):
        target = root / paths[key]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"{key}\n", encoding="utf-8")
    _write(root / paths["search"], _search_space())
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
            "baseline": BASELINE,
            "checks": checks,
            "implementation_kind": "UPSTREAM_CODE",
            "independent_oracle_sha256": sha256_file(root / paths["oracle"]),
            "scope": "OPERATOR_COMPOSITION",
            "schema_version": PARITY_EVIDENCE_SCHEMA,
            "source_commit": "1" * 40,
            "status": "PASS",
            "test_command": "python -m pytest -q tests/test_chebnet.py",
            "test_path": paths["test"],
            "test_result": "7 passed",
            "test_sha256": sha256_file(root / paths["test"]),
            "wrapper_sha256": sha256_file(root / paths["wrapper"]),
        },
    )
    return paths


def _registry(root: Path, *, finalized: bool = False, trial_budget: int = 10) -> dict:
    paths = _files(root)
    final = None
    status = "IMPLEMENTATION_VERIFIED"
    if finalized:
        _write(
            root / paths["final"],
            {
                "datasets": {
                    name: {"model": {}, "optimizer": {}, "training": {}}
                    for name in DATASET_REGISTRY
                },
                "method": BASELINE,
                "schema_version": "gbdn-heterophily-method-config-v1",
            },
        )
        _write(
            root / paths["selection"],
            {
                "baseline": BASELINE,
                "configuration_kind": LOCAL_SEARCH,
                "final_config_sha256": sha256_file(root / paths["final"]),
                "schema_version": SELECTION_EVIDENCE_SCHEMA,
                "search_space_sha256": sha256_file(root / paths["search"]),
                "selection_partition": "validation",
                "status": "PASS",
                "test_used_for_selection": False,
                "trial_budget_per_dataset": trial_budget,
            },
        )
        final = {
            "path": paths["final"],
            "selection_evidence_path": paths["selection"],
            "selection_evidence_sha256": sha256_file(root / paths["selection"]),
            "sha256": sha256_file(root / paths["final"]),
        }
        status = "CONFIRMATORY_READY"
    record = {
        "configuration": {
            "budget_binding": "CONFIRMATORY_PLAN_EQUAL_TRIAL_BUDGET",
            "final_configuration": final,
            "kind": LOCAL_SEARCH,
            "search_space_path": paths["search"],
            "search_space_sha256": sha256_file(root / paths["search"]),
            "selection": {
                "dataset_bindings": _dataset_bindings(),
                "partition": "validation",
                "test_used_for_selection": False,
            },
        },
        "implementation": {
            "equation_locator": "Eq. (5)",
            "independent_oracle_path": paths["oracle"],
            "independent_oracle_sha256": sha256_file(root / paths["oracle"]),
            "kind": "UPSTREAM_CODE",
            "paper_url": "https://papers.example.org/chebnet",
            "provenance_path": paths["provenance"],
            "provenance_sha256": sha256_file(root / paths["provenance"]),
            "source_commit": "1" * 40,
            "source_repository_url": "https://example.org/chebnet",
            "upstream_code_used": True,
        },
        "license": {
            "notice_path": paths["license"],
            "notice_sha256": sha256_file(root / paths["license"]),
            "spdx": "MIT",
        },
        "name": BASELINE,
        "operator_parity": {
            "evidence_path": paths["parity"],
            "evidence_sha256": sha256_file(root / paths["parity"]),
            "scope": "OPERATOR_COMPOSITION",
            "status": "PASS",
        },
        "protocols": ["heterophily"],
        "status": status,
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
    return {"baselines": [record], "schema_version": REGISTRY_SCHEMA}


def _plan(registry_hash: str, *, budget: int = 10) -> dict:
    return {
        "baseline_registry_sha256": registry_hash,
        "datasets": list(DATASET_REGISTRY),
        "methods": ["TightGBDN", BASELINE],
        "official_splits": list(OFFICIAL_SPLITS),
        "primary_baselines": [BASELINE],
        "practical_tie_thresholds": {name: 0.005 for name in DATASET_REGISTRY},
        "schema_version": PLAN_SCHEMA,
        "selection": {
            "equal_validation_trial_budget": True,
            "freeze_before_test": True,
            "test_process_isolated": True,
            "test_used_for_selection": False,
        },
        "training_seeds": list(TRAINING_SEEDS),
        "trial_budget_per_method_dataset": budget,
    }


def test_implementation_verified_candidate_passes_screening_but_not_confirmatory(tmp_path):
    path = tmp_path / "registry.json"
    _write(path, _registry(tmp_path))
    records = validate_baseline_registry(
        path,
        repository_root=tmp_path,
        required_methods=(BASELINE,),
        admission="screening",
    )
    assert records[0].admission_status == "IMPLEMENTATION_VERIFIED"
    assert records[0].operator_parity_scope == "OPERATOR_COMPOSITION"
    assert records[0].configuration_provenance == LOCAL_SEARCH
    assert records[0].final_config_path is None
    with pytest.raises(ArtifactValidationError, match="not confirmatory-ready"):
        validate_baseline_registry(
            path, repository_root=tmp_path, required_methods=(BASELINE,)
        )


def test_finalized_validation_only_config_and_equal_budget_admit_confirmatory(tmp_path):
    registry_path = tmp_path / "registry.json"
    _write(registry_path, _registry(tmp_path, finalized=True, trial_budget=10))
    plan_path = tmp_path / "plan.json"
    _write(plan_path, _plan(sha256_file(registry_path), budget=10))
    plan, records = validate_plan_registry_binding(
        plan_path, registry_path, repository_root=tmp_path
    )
    assert plan.trial_budget_per_method_dataset == 10
    assert records[0].reference_config_path == "configs/frozen/chebnet.json"


def test_plan_rejects_final_config_selected_with_different_trial_budget(tmp_path):
    registry_path = tmp_path / "registry.json"
    _write(registry_path, _registry(tmp_path, finalized=True, trial_budget=9))
    plan_path = tmp_path / "plan.json"
    _write(plan_path, _plan(sha256_file(registry_path), budget=10))
    with pytest.raises(ArtifactValidationError, match="selection provenance"):
        validate_plan_registry_binding(plan_path, registry_path, repository_root=tmp_path)


@pytest.mark.parametrize(
    ("mutation", "match"),
    (
        (lambda r: r["implementation"].update(source_commit="abc"), "full 40-hex"),
        (lambda r: r["operator_parity"].update(scope="FULL_MODEL_ACCURACY"), "operator-composition"),
        (lambda r: r["verification"].update(spmv_count=False), "resource/task"),
        (lambda r: r["configuration"]["selection"].update(test_used_for_selection=True), "validation-only"),
        (lambda r: r["configuration"].update(kind="UPSTREAM_REFERENCE_CONFIG"), "upstream configuration"),
    ),
)
def test_registry_rejects_identity_parity_resource_and_configuration_laundering(
    tmp_path, mutation, match
):
    registry = _registry(tmp_path)
    mutation(registry["baselines"][0])
    path = tmp_path / "registry.json"
    _write(path, registry)
    with pytest.raises(ArtifactValidationError, match=match):
        validate_baseline_registry(
            path,
            repository_root=tmp_path,
            required_methods=(BASELINE,),
            admission="screening",
        )


def test_operator_evidence_and_search_space_are_independently_hash_bound(tmp_path):
    registry = _registry(tmp_path)
    path = tmp_path / "registry.json"
    parity = tmp_path / registry["baselines"][0]["operator_parity"]["evidence_path"]
    parity.write_text("tampered\n", encoding="utf-8")
    _write(path, registry)
    with pytest.raises(ArtifactValidationError, match="operator parity evidence hash"):
        validate_baseline_registry(
            path, repository_root=tmp_path, required_methods=(BASELINE,), admission="screening"
        )

    registry = _registry(tmp_path / "search")
    root = tmp_path / "search"
    search = root / registry["baselines"][0]["configuration"]["search_space_path"]
    data = json.loads(search.read_text(encoding="utf-8"))
    data["parameters"]["model.K"] = {"role": "FIXED", "values": [2, 4]}
    _write(search, data)
    registry["baselines"][0]["configuration"]["search_space_sha256"] = sha256_file(search)
    _write(root / "registry.json", registry)
    with pytest.raises(ArtifactValidationError, match="values/role"):
        validate_baseline_registry(
            root / "registry.json",
            repository_root=root,
            required_methods=(BASELINE,),
            admission="screening",
        )


def test_registry_v2_cannot_silently_migrate(tmp_path):
    path = tmp_path / "registry.json"
    _write(path, {"baselines": [], "schema_version": "gbdn-baseline-registry-v2"})
    with pytest.raises(ArtifactValidationError, match="schema"):
        validate_baseline_registry(
            path, repository_root=tmp_path, required_methods=(), admission="screening"
        )


def test_repository_chebnet_candidate_is_truthful_and_screening_only():
    root = Path(__file__).parents[1]
    registry = root / "results_submission" / "baseline_registry.json"
    records = validate_baseline_registry(
        registry,
        repository_root=root,
        required_methods=(BASELINE,),
        admission="screening",
    )
    assert records[0].source_commit == "726310a486eae37a89cd6359072b82bbbbb71579"
    assert records[0].configuration_provenance == LOCAL_SEARCH
    with pytest.raises(ArtifactValidationError, match="not confirmatory-ready"):
        validate_baseline_registry(
            registry, repository_root=root, required_methods=(BASELINE,)
        )


@pytest.mark.parametrize(
    ("mutation", "match"),
    (
        (lambda plan: plan.update(training_seeds=[0]), "10x3"),
        (lambda plan: plan.update(official_splits=list(range(9))), "10x3"),
        (lambda plan: plan["selection"].update(test_used_for_selection=True), "selection"),
        (lambda plan: plan.update(trial_budget_per_method_dataset=0), "budget"),
        (lambda plan: plan["practical_tie_thresholds"].pop("Questions"), "threshold"),
        (lambda plan: plan.update(primary_baselines=[]), "primary baselines"),
    ),
)
def test_plan_rejects_incomplete_grid_leakage_and_unfair_budget(tmp_path, mutation, match):
    plan = _plan("a" * 64)
    mutation(plan)
    path = tmp_path / "plan.json"
    _write(path, plan)
    with pytest.raises(ArtifactValidationError, match=match):
        validate_confirmatory_plan(path)
