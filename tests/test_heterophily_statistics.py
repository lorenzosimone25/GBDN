"""Synthetic-only tests for official metrics and split-first statistics."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from gbdn.heterophily_contract import OFFICIAL_SPLITS, TRAINING_SEEDS
from gbdn.heterophily_statistics import (
    PairedComparison,
    StatisticalContractError,
    VerifiedRunMetric,
    aggregate_seed_within_split,
    binary_roc_auc,
    exact_sign_flip_pvalue,
    holm_adjust,
    multiclass_accuracy,
    paired_comparison,
    recompute_primary_metric,
    summarize_splits,
)


def _records(methods=("GBDN", "Baseline"), datasets=("Roman-empire",)):
    records = []
    for dataset in datasets:
        metric = "accuracy" if dataset in {"Roman-empire", "Amazon-ratings"} else "binary_roc_auc"
        for method_index, method in enumerate(methods):
            for split in OFFICIAL_SPLITS:
                for seed in TRAINING_SEEDS:
                    records.append(
                        VerifiedRunMetric(
                            method,
                            dataset,
                            split,
                            seed,
                            metric,
                            0.55 + 0.01 * method_index + 0.001 * split + 0.0001 * seed,
                            True,
                            True,
                            False,
                        )
                    )
    return records


def test_official_metric_dispatch_accuracy_and_tie_safe_binary_auc():
    logits = np.asarray([[2.0, 1.0], [0.0, 3.0], [4.0, 2.0]])
    labels = np.asarray([0, 1, 1], dtype=np.int64)
    assert multiclass_accuracy(logits, labels) == pytest.approx(2 / 3)
    assert recompute_primary_metric("Roman-empire", np.pad(logits, ((0, 0), (0, 16))), labels)[0] == "accuracy"

    scores = np.asarray([0.9, 0.5, 0.5, 0.1], dtype=np.float64)
    binary_labels = np.asarray([1, 1, 0, 0], dtype=np.int64)
    # Four pos/neg pairs: wins 3, tie 1 -> (3 + .5) / 4.
    assert binary_roc_auc(scores, binary_labels) == pytest.approx(0.875)
    name, value = recompute_primary_metric("Questions", scores, binary_labels)
    assert name == "binary_roc_auc" and value == pytest.approx(0.875)


def test_metrics_reject_thresholds_wrong_shapes_nonfinite_and_single_class():
    with pytest.raises(StatisticalContractError, match="one-dimensional"):
        recompute_primary_metric("Minesweeper", np.ones((3, 2)), np.asarray([0, 1, 0]))
    with pytest.raises(StatisticalContractError, match="both label classes"):
        binary_roc_auc(np.asarray([0.1, 0.2]), np.asarray([1, 1]))
    with pytest.raises(StatisticalContractError, match="finite"):
        binary_roc_auc(np.asarray([0.1, np.nan]), np.asarray([0, 1]))
    with pytest.raises(StatisticalContractError, match="18 logit columns"):
        recompute_primary_metric("Roman-empire", np.ones((2, 2)), np.asarray([0, 1]))


def test_seed_aggregation_is_complete_split_first_and_deterministic():
    aggregated = aggregate_seed_within_split(_records(), methods=("GBDN", "Baseline"), datasets=("Roman-empire",))
    assert len(aggregated) == 20
    first = aggregated[0]
    assert first.seeds == (0, 1, 2)
    assert first.seed_mean == pytest.approx(0.5501)
    summaries = summarize_splits(aggregated)
    assert len(summaries) == 2
    assert all(summary.split_count == 10 for summary in summaries)
    assert all(summary.ci95_lower < summary.mean < summary.ci95_upper for summary in summaries)


@pytest.mark.parametrize(
    ("mutation", "match"),
    (
        (lambda row: replace(row, independently_verified=False), "independent"),
        (lambda row: replace(row, frozen_config=False), "not frozen"),
        (lambda row: replace(row, test_used_for_selection=True), "exposed"),
    ),
)
def test_aggregation_rejects_unverified_unfrozen_and_test_exposed_runs(mutation, match):
    records = _records()
    records[0] = mutation(records[0])
    with pytest.raises(StatisticalContractError, match=match):
        aggregate_seed_within_split(records, methods=("GBDN", "Baseline"), datasets=("Roman-empire",))


def test_aggregation_rejects_missing_duplicate_wrong_metric_and_seed():
    records = _records()
    with pytest.raises(StatisticalContractError, match="incomplete"):
        aggregate_seed_within_split(records[:-1], methods=("GBDN", "Baseline"), datasets=("Roman-empire",))
    with pytest.raises(StatisticalContractError, match="duplicate"):
        aggregate_seed_within_split(records + [records[0]], methods=("GBDN", "Baseline"), datasets=("Roman-empire",))
    with pytest.raises(StatisticalContractError, match="official primary"):
        replace(records[0], metric_name="binary_roc_auc")
    with pytest.raises(StatisticalContractError, match="frozen confirmatory"):
        replace(records[0], seed=25)


def test_paired_comparison_uses_shared_splits_effect_wtl_and_exact_sign_flip():
    records = [
        replace(row, value=row.value + 0.0001 * row.split)
        if row.method == "Baseline"
        else row
        for row in _records()
    ]
    split_metrics = aggregate_seed_within_split(records, methods=("GBDN", "Baseline"), datasets=("Roman-empire",))
    comparison = paired_comparison(
        split_metrics,
        dataset="Roman-empire",
        method_a="Baseline",
        method_b="GBDN",
        tie_threshold=0.005,
    )
    assert comparison.mean_difference == pytest.approx(0.01045)
    assert (comparison.wins, comparison.ties, comparison.losses) == (10, 0, 0)
    assert comparison.standardized_effect is not None
    assert comparison.raw_p_value == pytest.approx(2 / 1024)
    assert exact_sign_flip_pvalue([1.0] * 10) == pytest.approx(2 / 1024)


def test_zero_difference_effect_is_undefined_and_all_ties():
    metrics = aggregate_seed_within_split(_records(methods=("A", "B")), methods=("A", "B"), datasets=("Roman-empire",))
    # Make B identical to A at the already aggregated level.
    aligned = tuple(
        replace(row, seed_mean=row.seed_mean - 0.01) if row.method == "B" else row
        for row in metrics
    )
    comparison = paired_comparison(aligned, dataset="Roman-empire", method_a="A", method_b="B", tie_threshold=0.0)
    assert comparison.mean_difference == pytest.approx(0.0)
    assert comparison.standardized_effect is None
    assert (comparison.wins, comparison.ties, comparison.losses) == (0, 10, 0)
    assert comparison.raw_p_value == 1.0


def test_holm_adjustment_is_monotone_and_preserves_input_order():
    base = PairedComparison("Roman-empire", "A", "B", "accuracy", 0.0, 0.0, 0.0, None, 0.04, None, 0, 10, 0, 0.0)
    family = (
        replace(base, method_b="B1", raw_p_value=0.04),
        replace(base, method_b="B2", raw_p_value=0.01),
        replace(base, method_b="B3", raw_p_value=0.03),
    )
    adjusted = holm_adjust(family)
    assert tuple(item.method_b for item in adjusted) == ("B1", "B2", "B3")
    assert [item.adjusted_p_value for item in adjusted] == pytest.approx([0.06, 0.03, 0.06])


def test_paired_analysis_rejects_missing_splits_and_invalid_tie_threshold():
    metrics = aggregate_seed_within_split(_records(), methods=("GBDN", "Baseline"), datasets=("Roman-empire",))
    with pytest.raises(StatisticalContractError, match="missing"):
        paired_comparison(metrics[:-1], dataset="Roman-empire", method_a="GBDN", method_b="Baseline", tie_threshold=0.0)
    with pytest.raises(StatisticalContractError, match="tie_threshold"):
        paired_comparison(metrics, dataset="Roman-empire", method_a="GBDN", method_b="Baseline", tie_threshold=float("nan"))
