"""Synthetic-only tests for provenance-preserving paper result rendering."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json

import pytest

from gbdn.heterophily_contract import OFFICIAL_SPLITS, TRAINING_SEEDS
from gbdn.heterophily_statistics import StatisticalContractError
from gbdn.paper_results import ProvenancedRunMetric, render_confirmatory_artifacts


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _records(methods=("TightGBDN", "Baseline"), datasets=("Roman-empire",)):
    rows = []
    for dataset in datasets:
        metric = "accuracy" if dataset in {"Roman-empire", "Amazon-ratings"} else "binary_roc_auc"
        for method_index, method in enumerate(methods):
            config = _sha(f"config:{method}:{dataset}")
            for split in OFFICIAL_SPLITS:
                for seed in TRAINING_SEEDS:
                    identity = f"{method}:{dataset}:{split}:{seed}"
                    rows.append(
                        ProvenancedRunMetric(
                            method,
                            dataset,
                            split,
                            seed,
                            metric,
                            0.6 + 0.01 * method_index + 0.001 * split + 0.0001 * seed,
                            _sha("run:" + identity),
                            _sha("prediction:" + identity),
                            config,
                        )
                    )
    return rows


def test_renderer_is_deterministic_unranked_and_provenance_complete():
    kwargs = dict(
        methods=("TightGBDN", "Baseline"),
        datasets=("Roman-empire",),
        primary_method="TightGBDN",
        tie_thresholds={"Roman-empire": 0.002},
    )
    first = render_confirmatory_artifacts(reversed(_records()), **kwargs)
    second = render_confirmatory_artifacts(_records(), **kwargs)
    assert first == second
    latex = first.latex_table.decode()
    assert "\\textbf" not in latex and "TightGBDN" in latex
    assert "[" in latex and "]" in latex
    provenance = json.loads(first.provenance_json)
    assert provenance["schema_version"] == "gbdn-confirmatory-render-v1"
    assert len(provenance["cells"]) == 2
    assert all(len(cell["run_ids"]) == 30 for cell in provenance["cells"])
    assert b"exact two-sided paired sign-flip" in first.paired_tests_csv


@pytest.mark.parametrize(
    ("mutation", "match"),
    (
        (lambda rows: rows[:-1], "incomplete"),
        (lambda rows: rows + [rows[0]], "duplicate provenance"),
        (lambda rows: [replace(rows[0], run_id="A" * 64), *rows[1:]], "lowercase SHA-256"),
        (lambda rows: [replace(rows[0], independently_verified=False), *rows[1:]], "independent"),
        (lambda rows: [replace(rows[0], test_used_for_selection=True), *rows[1:]], "exposed"),
        (lambda rows: [replace(rows[0], frozen_config_sha256=_sha("other")), *rows[1:]], "multiple frozen"),
    ),
)
def test_renderer_fails_closed_on_grid_provenance_and_leakage_defects(mutation, match):
    with pytest.raises(StatisticalContractError, match=match):
        render_confirmatory_artifacts(
            mutation(_records()),
            methods=("TightGBDN", "Baseline"),
            datasets=("Roman-empire",),
            primary_method="TightGBDN",
            tie_thresholds={"Roman-empire": 0.002},
        )


def test_renderer_requires_exact_threshold_family_and_primary_method():
    with pytest.raises(StatisticalContractError, match="thresholds"):
        render_confirmatory_artifacts(
            _records(),
            methods=("TightGBDN", "Baseline"),
            datasets=("Roman-empire",),
            primary_method="TightGBDN",
            tie_thresholds={},
        )
    with pytest.raises(StatisticalContractError, match="primary_method"):
        render_confirmatory_artifacts(
            _records(),
            methods=("TightGBDN", "Baseline"),
            datasets=("Roman-empire",),
            primary_method="Missing",
            tie_thresholds={"Roman-empire": 0.002},
        )
