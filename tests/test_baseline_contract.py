from __future__ import annotations

import json
from pathlib import Path

import pytest

from gbdn.artifacts import ArtifactValidationError, sha256_file
from gbdn.baseline_contract import (
    PARITY_EVIDENCE_SCHEMA,
    PLAN_SCHEMA,
    REGISTRY_SCHEMA,
    validate_baseline_registry,
    validate_confirmatory_plan,
    validate_plan_registry_binding,
)
from gbdn.heterophily_contract import DATASET_REGISTRY, OFFICIAL_SPLITS, TRAINING_SEEDS


BASELINES = ("CayleyNet", "ChebNetII", "WaveGC")


def _files(root: Path) -> None:
    for name in BASELINES:
        slug = name.lower()
        for relative in (
            f"licenses/{slug}.txt",
            f"src/baselines/{slug}.py",
            f"configs/baselines/{slug}.json",
            f"docs/baselines/{slug}_provenance.md",
            f"tests/oracles/{slug}_oracle.py",
            f"results_submission/reports/{slug}_parity.json",
        ):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{name}\n", encoding="utf-8")


def _registry(root: Path, *, status: str = "VERIFIED") -> dict:
    _files(root)
    records = []
    for index, name in enumerate(BASELINES):
        slug = name.lower()
        evidence_path = root / f"results_submission/reports/{slug}_parity.json"
        _write(
            evidence_path,
            {
                "baseline": name,
                "dataset": "upstream-fixture",
                "expected": 0.8,
                "implementation_kind": "UPSTREAM_CODE",
                "independent_oracle_sha256": sha256_file(
                    root / f"tests/oracles/{slug}_oracle.py"
                ),
                "metric": "accuracy",
                "observed": 0.8 + index * 0.001,
                "reference_config_sha256": sha256_file(
                    root / f"configs/baselines/{slug}.json"
                ),
                "schema_version": PARITY_EVIDENCE_SCHEMA,
                "source_commit": f"{index + 1:040x}",
                "status": "PASS",
                "tolerance": 0.01,
                "wrapper_sha256": sha256_file(root / f"src/baselines/{slug}.py"),
            },
        )
        records.append(
            {
                "implementation": {
                    "equation_locator": "Eq. (3), p. 4",
                    "independent_oracle_path": f"tests/oracles/{slug}_oracle.py",
                    "independent_oracle_sha256": sha256_file(
                        root / f"tests/oracles/{slug}_oracle.py"
                    ),
                    "kind": "UPSTREAM_CODE",
                    "paper_url": f"https://papers.example.org/{slug}",
                    "provenance_path": f"docs/baselines/{slug}_provenance.md",
                    "provenance_sha256": sha256_file(
                        root / f"docs/baselines/{slug}_provenance.md"
                    ),
                    "source_commit": f"{index + 1:040x}",
                    "source_repository_url": f"https://example.org/{slug}",
                    "upstream_code_used": True,
                },
                "license": {
                    "notice_path": f"licenses/{slug}.txt",
                    "notice_sha256": sha256_file(root / f"licenses/{slug}.txt"),
                    "spdx": "MIT",
                },
                "name": name,
                "parity": {
                    "dataset": "upstream-fixture",
                    "evidence_path": f"results_submission/reports/{slug}_parity.json",
                    "evidence_sha256": sha256_file(
                        root / f"results_submission/reports/{slug}_parity.json"
                    ),
                    "expected": 0.8,
                    "metric": "accuracy",
                    "observed": 0.8 + index * 0.001,
                    "status": "PASS",
                    "tolerance": 0.01,
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
                    "path": f"src/baselines/{slug}.py",
                    "reference_config_path": f"configs/baselines/{slug}.json",
                    "reference_config_sha256": sha256_file(
                        root / f"configs/baselines/{slug}.json"
                    ),
                    "source_sha256": sha256_file(root / f"src/baselines/{slug}.py"),
                },
            }
        )
    return {"baselines": records, "schema_version": REGISTRY_SCHEMA}


def _plan(registry_hash: str) -> dict:
    return {
        "baseline_registry_sha256": registry_hash,
        "datasets": list(DATASET_REGISTRY),
        "methods": ["TightGBDN", *BASELINES],
        "official_splits": list(OFFICIAL_SPLITS),
        "primary_baselines": list(BASELINES),
        "practical_tie_thresholds": {name: 0.005 for name in DATASET_REGISTRY},
        "schema_version": PLAN_SCHEMA,
        "selection": {
            "equal_validation_trial_budget": True,
            "freeze_before_test": True,
            "test_process_isolated": True,
            "test_used_for_selection": False,
        },
        "training_seeds": list(TRAINING_SEEDS),
        "trial_budget_per_method_dataset": 20,
    }


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def test_verified_registry_and_equal_budget_plan_bind_by_hash(tmp_path):
    registry_path = tmp_path / "baseline_registry.json"
    _write(registry_path, _registry(tmp_path))
    plan_path = tmp_path / "confirmatory_plan.json"
    _write(plan_path, _plan(sha256_file(registry_path)))
    plan, baselines = validate_plan_registry_binding(
        plan_path, registry_path, repository_root=tmp_path
    )
    assert plan.primary_baselines == BASELINES
    assert plan.trial_budget_per_method_dataset == 20
    assert tuple(item.name for item in baselines) == BASELINES


def test_blocked_or_missing_baseline_cannot_enter_primary_scope(tmp_path):
    path = tmp_path / "registry.json"
    _write(path, _registry(tmp_path, status="BLOCKED"))
    with pytest.raises(ArtifactValidationError, match="not VERIFIED"):
        validate_baseline_registry(path, repository_root=tmp_path, required_methods=BASELINES)

    _write(path, _registry(tmp_path))
    with pytest.raises(ArtifactValidationError, match="scope mismatch"):
        validate_baseline_registry(
            path,
            repository_root=tmp_path,
            required_methods=(*BASELINES, "UniFilter"),
        )


@pytest.mark.parametrize(
    ("mutation", "match"),
    (
        (lambda record: record["license"].update(spdx="NOASSERTION"), "license"),
        (lambda record: record["parity"].update(observed=0.95), "exceeds"),
        (lambda record: record["verification"].update(spmv_count=False), "resource"),
        (lambda record: record["protocols"].clear(), "protocols"),
        (lambda record: record["implementation"].update(source_commit="abc"), "full 40-hex"),
    ),
)
def test_registry_rejects_unresolved_provenance_parity_and_accounting(tmp_path, mutation, match):
    registry = _registry(tmp_path)
    mutation(registry["baselines"][0])
    path = tmp_path / "registry.json"
    _write(path, registry)
    with pytest.raises(ArtifactValidationError, match=match):
        validate_baseline_registry(path, repository_root=tmp_path, required_methods=BASELINES)


def test_registry_rejects_missing_evidence_and_duplicate_names(tmp_path):
    registry = _registry(tmp_path)
    (tmp_path / registry["baselines"][0]["wrapper"]["path"]).unlink()
    path = tmp_path / "registry.json"
    _write(path, registry)
    with pytest.raises(ArtifactValidationError, match="missing regular.*wrapper source"):
        validate_baseline_registry(path, repository_root=tmp_path, required_methods=BASELINES)


def test_clean_room_equation_implementation_is_explicit_and_admissible(tmp_path):
    registry = _registry(tmp_path)
    record = registry["baselines"][0]
    record["implementation"].update(
        kind="CLEAN_ROOM_EQUATIONS", upstream_code_used=False
    )
    evidence_path = tmp_path / record["parity"]["evidence_path"]
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["implementation_kind"] = "CLEAN_ROOM_EQUATIONS"
    _write(evidence_path, evidence)
    record["parity"]["evidence_sha256"] = sha256_file(evidence_path)
    path = tmp_path / "registry.json"
    _write(path, registry)
    validated = validate_baseline_registry(
        path, repository_root=tmp_path, required_methods=BASELINES
    )
    assert validated[0].implementation_kind == "CLEAN_ROOM_EQUATIONS"
    assert validated[0].upstream_code_used is False


def test_implementation_kind_cannot_launder_upstream_code(tmp_path):
    registry = _registry(tmp_path)
    registry["baselines"][0]["implementation"].update(
        kind="CLEAN_ROOM_EQUATIONS", upstream_code_used=True
    )
    path = tmp_path / "registry.json"
    _write(path, registry)
    with pytest.raises(ArtifactValidationError, match="contradicts"):
        validate_baseline_registry(path, repository_root=tmp_path, required_methods=BASELINES)


def test_registry_rejects_tampered_parity_evidence_and_oracle_absence(tmp_path):
    registry = _registry(tmp_path)
    record = registry["baselines"][0]
    evidence = tmp_path / record["parity"]["evidence_path"]
    evidence.write_text("tampered\n", encoding="utf-8")
    path = tmp_path / "registry.json"
    _write(path, registry)
    with pytest.raises(ArtifactValidationError, match="evidence hash"):
        validate_baseline_registry(path, repository_root=tmp_path, required_methods=BASELINES)

    registry = _registry(tmp_path)
    oracle = tmp_path / registry["baselines"][0]["implementation"]["independent_oracle_path"]
    oracle.unlink()
    _write(path, registry)
    with pytest.raises(ArtifactValidationError, match="missing regular.*independent oracle"):
        validate_baseline_registry(path, repository_root=tmp_path, required_methods=BASELINES)

    registry = _registry(tmp_path)
    provenance = tmp_path / registry["baselines"][0]["implementation"]["provenance_path"]
    provenance.write_text("drifted provenance\n", encoding="utf-8")
    _write(path, registry)
    with pytest.raises(ArtifactValidationError, match="provenance hash"):
        validate_baseline_registry(path, repository_root=tmp_path, required_methods=BASELINES)

    registry = _registry(tmp_path)
    record = registry["baselines"][0]
    evidence_path = tmp_path / record["parity"]["evidence_path"]
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["observed"] = 0.81
    _write(evidence_path, evidence)
    record["parity"]["evidence_sha256"] = sha256_file(evidence_path)
    _write(path, registry)
    with pytest.raises(ArtifactValidationError, match="registry- and implementation-bound"):
        validate_baseline_registry(path, repository_root=tmp_path, required_methods=BASELINES)

    registry = _registry(tmp_path)
    registry["baselines"][1]["name"] = registry["baselines"][0]["name"]
    _write(path, registry)
    with pytest.raises(ArtifactValidationError, match="duplicate"):
        validate_baseline_registry(path, repository_root=tmp_path, required_methods=BASELINES)


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
def test_plan_rejects_incomplete_grid_leakage_unfair_budget_and_unfrozen_analysis(tmp_path, mutation, match):
    plan = _plan("a" * 64)
    mutation(plan)
    path = tmp_path / "plan.json"
    _write(path, plan)
    with pytest.raises(ArtifactValidationError, match=match):
        validate_confirmatory_plan(path)


def test_plan_rejects_registry_drift(tmp_path):
    registry_path = tmp_path / "registry.json"
    _write(registry_path, _registry(tmp_path))
    plan_path = tmp_path / "plan.json"
    _write(plan_path, _plan("f" * 64))
    with pytest.raises(ArtifactValidationError, match="hash mismatch"):
        validate_plan_registry_binding(plan_path, registry_path, repository_root=tmp_path)
