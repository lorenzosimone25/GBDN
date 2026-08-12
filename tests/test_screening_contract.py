from __future__ import annotations

import json
from pathlib import Path

import pytest

from gbdn.artifacts import ArtifactValidationError, canonical_json_bytes
from gbdn.heterophily_contract import DATASET_REGISTRY, resolve_dataset
from gbdn.screening_contract import (
    OBSERVATION_SCHEMA,
    SAMPLING_POLICY,
    build_screening_schedule,
    enumerate_candidates,
    load_search_space,
    select_validation_winners,
    validate_screening_manifest,
)


DATASETS = tuple(DATASET_REGISTRY)
UNITS = ("split=0/seed=0", "split=1/seed=0")


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _space(method: str = "ChebNet") -> dict[str, object]:
    return {
        "method": method,
        "parameters": {
            "model.K": {"role": "TUNED", "values": [2, 4]},
            "model.dropout": {"role": "FIXED", "values": [0.0]},
            "model.hidden_channels": {"role": "FIXED", "values": [32]},
            "optimizer.amsgrad": {"role": "FIXED", "values": [False]},
            "optimizer.betas": {"role": "FIXED", "values": [[0.9, 0.999]]},
            "optimizer.eps": {"role": "FIXED", "values": [1e-8]},
            "optimizer.learning_rate": {"role": "TUNED", "values": [0.001, 0.01]},
            "optimizer.name": {"role": "FIXED", "values": ["Adam"]},
            "optimizer.weight_decay": {"role": "FIXED", "values": [0.0]},
            "training.checkpoint_tie_breaker": {"role": "FIXED", "values": ["earliest"]},
            "training.deterministic_algorithms": {"role": "FIXED", "values": [True]},
            "training.gradient_clip_norm": {"role": "FIXED", "values": [None]},
            "training.max_epochs": {"role": "FIXED", "values": [10]},
            "training.min_delta": {"role": "FIXED", "values": [0.0]},
            "training.patience": {"role": "FIXED", "values": [5]},
            "training.precision": {"role": "FIXED", "values": ["float32"]},
            "training.selection_source": {"role": "FIXED", "values": ["validation_only"]},
        },
        "schema_version": "gbdn-baseline-search-space-v1",
        "status": "FROZEN_PRESPECIFIED",
    }


def _loaded(tmp_path: Path, method: str = "ChebNet"):
    relative = f"configs/search/{method}.json"
    path = tmp_path / relative
    _write(path, _space(method))
    return load_search_space(path, source_path=relative)


def _observations(schedule, *, tied: bool = False) -> list[dict[str, object]]:
    values: list[dict[str, object]] = []
    for trial in schedule.trials:
        score = 0.5 if tied else 0.4 + 0.1 * trial.trial_id
        values.append(
            {
                "candidate_sha256": trial.candidate.candidate_sha256,
                "dataset": trial.dataset,
                "evaluation_unit_ids": list(UNITS),
                "method": trial.method,
                "schema_version": OBSERVATION_SCHEMA,
                "selection_partition": "validation",
                "test_used_for_selection": False,
                "trial_id": trial.trial_id,
                "validation_metric": resolve_dataset(trial.dataset).selection_metric,
                "validation_values": [score, score],
            }
        )
    return values


def test_repository_chebnet_space_enumerates_all_exact_candidates():
    root = Path(__file__).resolve().parents[1]
    path = root / "configs/submission/search_spaces/ChebNet.json"
    space = load_search_space(
        path,
        source_path="configs/submission/search_spaces/ChebNet.json",
    )
    candidates = enumerate_candidates(space)
    assert space.method == "ChebNet"
    assert space.candidate_count == 243
    assert len(candidates) == len({item.candidate_sha256 for item in candidates}) == 243
    assert all(set(candidate.configuration) == {"model", "optimizer", "training"} for candidate in candidates)


def test_schedule_is_deterministic_equal_budget_and_seed_bound(tmp_path):
    first = _loaded(tmp_path, "ChebNet")
    second = _loaded(tmp_path, "TightGBDN")
    schedule = build_screening_schedule(
        [second, first],
        datasets=DATASETS,
        validation_unit_ids=UNITS,
        screening_seed=20260812,
        trial_budget_per_method_dataset=3,
    )
    repeated = build_screening_schedule(
        [first, second],
        datasets=DATASETS,
        validation_unit_ids=UNITS,
        screening_seed=20260812,
        trial_budget_per_method_dataset=3,
    )
    changed = build_screening_schedule(
        [first, second],
        datasets=DATASETS,
        validation_unit_ids=UNITS,
        screening_seed=20260813,
        trial_budget_per_method_dataset=3,
    )
    assert schedule.payload() == repeated.payload()
    assert schedule.sha256 == repeated.sha256
    assert schedule.sha256 != changed.sha256
    assert schedule.payload()["policy"]["candidate_sampling"] == SAMPLING_POLICY
    assert len(schedule.trials) == 2 * len(DATASETS) * 3
    for method in ("ChebNet", "TightGBDN"):
        for dataset in DATASETS:
            selected = [trial for trial in schedule.trials if trial.method == method and trial.dataset == dataset]
            assert [trial.trial_id for trial in selected] == [0, 1, 2]
            assert len({trial.candidate.candidate_sha256 for trial in selected}) == 3


def test_canonical_manifest_rebuilds_and_rejects_tampering(tmp_path):
    space = _loaded(tmp_path)
    schedule = build_screening_schedule(
        [space], datasets=DATASETS, validation_unit_ids=UNITS, screening_seed=7, trial_budget_per_method_dataset=2
    )
    manifest = tmp_path / "screening.json"
    _write(manifest, schedule.payload())
    accepted = validate_screening_manifest(manifest, repository_root=tmp_path)
    assert accepted.sha256 == schedule.sha256

    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["trials"][0]["rank_sha256"] = "0" * 64
    _write(manifest, data)
    with pytest.raises(ArtifactValidationError, match="deterministic reconstruction"):
        validate_screening_manifest(manifest, repository_root=tmp_path)

    _write(manifest, schedule.payload())
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["trials"][0]["trial_id"] = False
    _write(manifest, data)
    with pytest.raises(ArtifactValidationError, match="deterministic reconstruction"):
        validate_screening_manifest(manifest, repository_root=tmp_path)

    _write(manifest, schedule.payload())
    source = tmp_path / space.source_path
    changed = _space()
    changed["parameters"]["model.K"]["values"] = [2, 8]
    _write(source, changed)
    with pytest.raises(ArtifactValidationError, match="binding differs"):
        validate_screening_manifest(manifest, repository_root=tmp_path)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda value: value["parameters"].update({"model.bad.path": {"role": "TUNED", "values": [1, 2]}}), "section.field"),
        (lambda value: value["parameters"].update({"model.flag": {"role": "TUNED", "values": [False, 0]}}), None),
        (lambda value: value["parameters"]["model.K"].update(values=[2, 2]), "duplicate"),
        (lambda value: value["parameters"]["model.K"].update(values=[2]), "contradicts"),
    ],
)
def test_search_space_rejects_bad_paths_duplicates_and_roles(tmp_path, mutate, message):
    value = _space()
    mutate(value)
    path = tmp_path / "space.json"
    _write(path, value)
    if message is None:
        # Boolean false and integer zero are distinct JSON types and are retained.
        loaded = load_search_space(path, source_path="space.json")
        assert loaded.candidate_count == 8
    else:
        with pytest.raises(ArtifactValidationError, match=message):
            load_search_space(path, source_path="space.json")


def test_search_space_requires_canonical_json_and_safe_source_path(tmp_path):
    path = tmp_path / "space.json"
    path.write_text(json.dumps(_space(), indent=2), encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="canonical"):
        load_search_space(path, source_path="space.json")
    _write(path, _space())
    with pytest.raises(ArtifactValidationError, match="safe relative"):
        load_search_space(path, source_path="../space.json")


def test_schedule_rejects_bool_budget_partial_datasets_and_excess_budget(tmp_path):
    space = _loaded(tmp_path)
    with pytest.raises(ArtifactValidationError, match="positive exact integer"):
        build_screening_schedule([space], datasets=DATASETS, validation_unit_ids=UNITS, screening_seed=1, trial_budget_per_method_dataset=True)
    with pytest.raises(ArtifactValidationError, match="all five"):
        build_screening_schedule([space], datasets=DATASETS[:-1], validation_unit_ids=UNITS, screening_seed=1, trial_budget_per_method_dataset=1)
    with pytest.raises(ArtifactValidationError, match="exceeds"):
        build_screening_schedule([space], datasets=DATASETS, validation_unit_ids=UNITS, screening_seed=1, trial_budget_per_method_dataset=5)


def test_validation_selection_is_complete_metric_bound_and_hash_tiebroken(tmp_path):
    space = _loaded(tmp_path)
    schedule = build_screening_schedule(
        [space], datasets=DATASETS, validation_unit_ids=UNITS, screening_seed=11, trial_budget_per_method_dataset=2
    )
    observations = _observations(schedule)
    decisions = select_validation_winners(schedule, observations)
    assert len(decisions) == len(DATASETS)
    assert all(decision.trial_id == 1 for decision in decisions)
    assert all(decision.payload()["test_used_for_selection"] is False for decision in decisions)
    assert all(decision.screening_manifest_sha256 == schedule.sha256 for decision in decisions)
    assert all(len(decision.candidate_observations) == 2 for decision in decisions)

    tied = select_validation_winners(schedule, _observations(schedule, tied=True))
    for decision in tied:
        candidate_hashes = sorted(
            trial.candidate.candidate_sha256
            for trial in schedule.trials
            if trial.dataset == decision.dataset
        )
        assert decision.candidate_sha256 == candidate_hashes[0]


def test_validation_selection_fails_closed_on_test_field_units_and_missing_trial(tmp_path):
    space = _loaded(tmp_path)
    schedule = build_screening_schedule(
        [space], datasets=DATASETS, validation_unit_ids=UNITS, screening_seed=11, trial_budget_per_method_dataset=2
    )
    observations = _observations(schedule)
    observations[0]["test_metric"] = 0.99
    with pytest.raises(ArtifactValidationError, match="keys"):
        select_validation_winners(schedule, observations)

    observations = _observations(schedule)
    observations[1]["evaluation_unit_ids"] = ["split=9/seed=9", "split=1/seed=0"]
    with pytest.raises(ArtifactValidationError, match="manifest-frozen validation units"):
        select_validation_winners(schedule, observations)

    with pytest.raises(ArtifactValidationError, match="incomplete"):
        select_validation_winners(schedule, _observations(schedule)[:-1])


def test_validation_selection_rejects_wrong_metric_and_bool_score(tmp_path):
    space = _loaded(tmp_path)
    schedule = build_screening_schedule(
        [space], datasets=DATASETS, validation_unit_ids=UNITS, screening_seed=11, trial_budget_per_method_dataset=1
    )
    observations = _observations(schedule)
    observations[0]["validation_metric"] = "binary_roc_auc"
    with pytest.raises(ArtifactValidationError, match="official-metric"):
        select_validation_winners(schedule, observations)
    observations = _observations(schedule)
    observations[0]["validation_values"] = [True, 0.5]
    with pytest.raises(ArtifactValidationError, match="official-metric"):
        select_validation_winners(schedule, observations)
