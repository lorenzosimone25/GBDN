"""Task-specific metrics and split-first confirmatory statistics.

The functions in this module operate on in-memory arrays or already verified
scalar run records.  They do not load datasets, inspect checkpoints, select
hyperparameters, access test masks, or write paper artifacts.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, replace
from typing import Final, Iterable, Mapping, Sequence

import numpy as np

from gbdn.heterophily_contract import (
    DATASET_REGISTRY,
    OFFICIAL_SPLITS,
    TRAINING_SEEDS,
    ProtocolContractError,
    resolve_dataset,
)


PRIMARY_SPLIT_COUNT: Final[int] = 10
PRIMARY_SEED_COUNT: Final[int] = 3
T_975_DF9: Final[float] = 2.2621571628540993


class StatisticalContractError(ValueError):
    """Raised when records or an analysis request violate the frozen design."""


def multiclass_accuracy(logits: np.ndarray, labels: np.ndarray) -> float:
    """Return accuracy from finite two-dimensional logits and integer labels."""

    scores = np.asarray(logits)
    target = np.asarray(labels)
    if scores.ndim != 2 or scores.shape[0] == 0 or scores.shape[1] < 2:
        raise StatisticalContractError("multiclass logits must have shape [N,C] with C>=2")
    if target.shape != (scores.shape[0],) or target.dtype.kind not in "iu":
        raise StatisticalContractError("multiclass labels must be an integer vector of length N")
    if not np.all(np.isfinite(scores)):
        raise StatisticalContractError("multiclass logits must be finite")
    if np.any(target < 0) or np.any(target >= scores.shape[1]):
        raise StatisticalContractError("multiclass labels lie outside the logit columns")
    return float(np.mean(np.argmax(scores, axis=1) == target))


def binary_roc_auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Return tie-aware binary ROC-AUC from continuous positive-class scores.

    This independent implementation uses the probabilistic definition:
    ``P(score_pos > score_neg) + 0.5 P(score_pos == score_neg)``.  It never
    thresholds predictions and does not call a multiclass/macro-AUROC path.
    """

    value = np.asarray(scores)
    target = np.asarray(labels)
    if value.ndim != 1 or value.size == 0 or target.shape != value.shape:
        raise StatisticalContractError("binary scores and labels must be nonempty vectors")
    if not np.issubdtype(value.dtype, np.floating) or not np.all(np.isfinite(value)):
        raise StatisticalContractError("binary scores must be finite floating values")
    if target.dtype.kind not in "biu" or not np.all(np.isin(target, (0, 1))):
        raise StatisticalContractError("binary labels must contain only 0 and 1")
    positive_count = int(np.count_nonzero(target == 1))
    negative_count = int(np.count_nonzero(target == 0))
    if positive_count == 0 or negative_count == 0:
        raise StatisticalContractError("binary ROC-AUC requires both label classes")
    # Mann--Whitney U with average ranks is exactly the probabilistic AUC
    # definition above, including half-credit for ties, without constructing
    # the O(n_positive * n_negative) pairwise comparison matrix.
    order = np.argsort(value, kind="mergesort")
    sorted_scores = value[order]
    ranks = np.empty(value.size, dtype=np.float64)
    start = 0
    while start < value.size:
        stop = start + 1
        while stop < value.size and sorted_scores[stop] == sorted_scores[start]:
            stop += 1
        ranks[order[start:stop]] = 0.5 * ((start + 1) + stop)
        start = stop
    positive_rank_sum = float(np.sum(ranks[target == 1]))
    mann_whitney = positive_rank_sum - positive_count * (positive_count + 1) / 2.0
    return float(mann_whitney / (positive_count * negative_count))


def recompute_primary_metric(
    dataset: str,
    predictions: np.ndarray,
    labels: np.ndarray,
) -> tuple[str, float]:
    """Dispatch only to the official primary metric for one dataset."""

    spec = resolve_dataset(dataset)
    if spec.test_metric == "accuracy":
        scores = np.asarray(predictions)
        if scores.ndim != 2 or scores.shape[1] != spec.output_logits:
            raise StatisticalContractError(
                f"{spec.canonical_name} requires {spec.output_logits} logit columns"
            )
        return spec.test_metric, multiclass_accuracy(scores, labels)
    scores = np.asarray(predictions)
    if scores.ndim != 1:
        raise StatisticalContractError(
            f"{spec.canonical_name} requires one-dimensional positive-class scores"
        )
    return spec.test_metric, binary_roc_auc(scores, labels)


@dataclass(frozen=True)
class VerifiedRunMetric:
    method: str
    dataset: str
    split: int
    seed: int
    metric_name: str
    value: float
    independently_verified: bool
    frozen_config: bool
    test_used_for_selection: bool

    def __post_init__(self) -> None:
        if not self.method or self.method != self.method.strip():
            raise StatisticalContractError("method must be a nonempty trimmed identifier")
        spec = resolve_dataset(self.dataset)
        object.__setattr__(self, "dataset", spec.canonical_name)
        if self.split not in OFFICIAL_SPLITS or self.seed not in TRAINING_SEEDS:
            raise StatisticalContractError("run split/seed is outside the frozen confirmatory grid")
        if self.metric_name != spec.test_metric:
            raise StatisticalContractError("run metric is not the dataset's official primary metric")
        if not isinstance(self.value, (int, float)) or not math.isfinite(float(self.value)):
            raise StatisticalContractError("run metric value must be finite")
        if not 0.0 <= float(self.value) <= 1.0:
            raise StatisticalContractError("run metric value must lie in [0,1]")
        for field in ("independently_verified", "frozen_config", "test_used_for_selection"):
            if type(getattr(self, field)) is not bool:
                raise StatisticalContractError(f"{field} must be boolean")


@dataclass(frozen=True)
class SplitMetric:
    method: str
    dataset: str
    split: int
    metric_name: str
    seed_mean: float
    seed_standard_deviation: float
    seeds: tuple[int, ...]


def aggregate_seed_within_split(
    records: Iterable[VerifiedRunMetric],
    *,
    methods: Sequence[str],
    datasets: Sequence[str] = tuple(DATASET_REGISTRY),
) -> tuple[SplitMetric, ...]:
    """Require the complete grid and average seeds before any split inference."""

    if not methods or len(set(methods)) != len(methods):
        raise StatisticalContractError("methods must be a nonempty unique sequence")
    canonical_datasets = tuple(resolve_dataset(name).canonical_name for name in datasets)
    if len(set(canonical_datasets)) != len(canonical_datasets):
        raise StatisticalContractError("datasets must be unique")
    indexed: dict[tuple[str, str, int, int], VerifiedRunMetric] = {}
    for record in records:
        key = (record.method, record.dataset, record.split, record.seed)
        if key in indexed:
            raise StatisticalContractError(f"duplicate run identity: {key}")
        if record.method not in methods or record.dataset not in canonical_datasets:
            raise StatisticalContractError(f"record is outside the frozen analysis scope: {key}")
        if not record.independently_verified:
            raise StatisticalContractError(f"run lacks independent metric verification: {key}")
        if not record.frozen_config:
            raise StatisticalContractError(f"run configuration is not frozen: {key}")
        if record.test_used_for_selection:
            raise StatisticalContractError(f"test metric was exposed during selection: {key}")
        indexed[key] = record

    output: list[SplitMetric] = []
    missing: list[tuple[str, str, int, int]] = []
    for dataset in canonical_datasets:
        metric = resolve_dataset(dataset).test_metric
        for method in methods:
            for split in OFFICIAL_SPLITS:
                values: list[float] = []
                for seed in TRAINING_SEEDS:
                    key = (method, dataset, split, seed)
                    record = indexed.get(key)
                    if record is None:
                        missing.append(key)
                    else:
                        values.append(float(record.value))
                if len(values) == len(TRAINING_SEEDS):
                    output.append(
                        SplitMetric(
                            method=method,
                            dataset=dataset,
                            split=split,
                            metric_name=metric,
                            seed_mean=float(np.mean(values)),
                            seed_standard_deviation=float(np.std(values, ddof=1)),
                            seeds=TRAINING_SEEDS,
                        )
                    )
    if missing:
        preview = ", ".join(map(str, missing[:5]))
        raise StatisticalContractError(
            f"confirmatory grid is incomplete; missing {len(missing)} runs: {preview}"
        )
    expected = len(methods) * len(canonical_datasets) * len(OFFICIAL_SPLITS)
    if len(output) != expected or len(indexed) != expected * len(TRAINING_SEEDS):
        raise StatisticalContractError("confirmatory run or split cardinality is inconsistent")
    return tuple(output)


@dataclass(frozen=True)
class SplitSummary:
    method: str
    dataset: str
    metric_name: str
    mean: float
    standard_deviation: float
    ci95_lower: float
    ci95_upper: float
    split_count: int
    ci_procedure: str = "two-sided Student-t interval over 10 official split means (df=9)"


def summarize_splits(split_metrics: Iterable[SplitMetric]) -> tuple[SplitSummary, ...]:
    """Compute the predeclared Student-t interval over ten split means."""

    groups: dict[tuple[str, str, str], list[SplitMetric]] = {}
    for record in split_metrics:
        groups.setdefault((record.method, record.dataset, record.metric_name), []).append(record)
    summaries: list[SplitSummary] = []
    for (method, dataset, metric), records in sorted(groups.items()):
        ordered = sorted(records, key=lambda record: record.split)
        if tuple(record.split for record in ordered) != OFFICIAL_SPLITS:
            raise StatisticalContractError(
                f"split summary for {(method, dataset)} must contain official rows 0..9 exactly once"
            )
        values = np.asarray([record.seed_mean for record in ordered], dtype=np.float64)
        mean = float(np.mean(values))
        standard_deviation = float(np.std(values, ddof=1))
        half_width = T_975_DF9 * standard_deviation / math.sqrt(PRIMARY_SPLIT_COUNT)
        summaries.append(
            SplitSummary(
                method,
                dataset,
                metric,
                mean,
                standard_deviation,
                mean - half_width,
                mean + half_width,
                PRIMARY_SPLIT_COUNT,
            )
        )
    return tuple(summaries)


def exact_sign_flip_pvalue(differences: Sequence[float]) -> float:
    """Return the exact two-sided paired sign-flip p-value for ten splits."""

    values = np.asarray(differences, dtype=np.float64)
    if values.shape != (PRIMARY_SPLIT_COUNT,) or not np.all(np.isfinite(values)):
        raise StatisticalContractError("paired sign-flip test requires ten finite differences")
    observed = abs(float(np.mean(values)))
    tolerance = 32.0 * np.finfo(np.float64).eps * max(1.0, observed, float(np.max(np.abs(values))))
    extreme = 0
    total = 1 << PRIMARY_SPLIT_COUNT
    for signs in itertools.product((-1.0, 1.0), repeat=PRIMARY_SPLIT_COUNT):
        statistic = abs(float(np.mean(values * np.asarray(signs))))
        extreme += statistic + tolerance >= observed
    return float(extreme / total)


@dataclass(frozen=True)
class PairedComparison:
    dataset: str
    method_a: str
    method_b: str
    metric_name: str
    mean_difference: float
    ci95_lower: float
    ci95_upper: float
    standardized_effect: float | None
    raw_p_value: float
    adjusted_p_value: float | None
    wins: int
    ties: int
    losses: int
    tie_threshold: float
    split_count: int = PRIMARY_SPLIT_COUNT
    test_procedure: str = "exact two-sided paired sign-flip over official split means"


def paired_comparison(
    split_metrics: Iterable[SplitMetric],
    *,
    dataset: str,
    method_a: str,
    method_b: str,
    tie_threshold: float,
) -> PairedComparison:
    """Compare two methods on the same ten official split means."""

    if not isinstance(tie_threshold, (int, float)) or not math.isfinite(float(tie_threshold)) or tie_threshold < 0:
        raise StatisticalContractError("tie_threshold must be finite and nonnegative")
    canonical = resolve_dataset(dataset).canonical_name
    selected = [
        record
        for record in split_metrics
        if record.dataset == canonical and record.method in {method_a, method_b}
    ]
    by_key = {(record.method, record.split): record for record in selected}
    differences: list[float] = []
    for split in OFFICIAL_SPLITS:
        left = by_key.get((method_a, split))
        right = by_key.get((method_b, split))
        if left is None or right is None:
            raise StatisticalContractError("paired comparison is missing a shared official split")
        if left.metric_name != right.metric_name:
            raise StatisticalContractError("paired methods use different metrics")
        differences.append(left.seed_mean - right.seed_mean)
    values = np.asarray(differences, dtype=np.float64)
    mean = float(np.mean(values))
    standard_deviation = float(np.std(values, ddof=1))
    half_width = T_975_DF9 * standard_deviation / math.sqrt(PRIMARY_SPLIT_COUNT)
    standardized = None if standard_deviation == 0.0 else mean / standard_deviation
    threshold = float(tie_threshold)
    wins = int(np.count_nonzero(values > threshold))
    losses = int(np.count_nonzero(values < -threshold))
    ties = PRIMARY_SPLIT_COUNT - wins - losses
    metric = resolve_dataset(canonical).test_metric
    return PairedComparison(
        canonical,
        method_a,
        method_b,
        metric,
        mean,
        mean - half_width,
        mean + half_width,
        standardized,
        exact_sign_flip_pvalue(values),
        None,
        wins,
        ties,
        losses,
        threshold,
    )


def holm_adjust(comparisons: Sequence[PairedComparison]) -> tuple[PairedComparison, ...]:
    """Apply Holm's step-down correction to one predeclared comparison family."""

    if not comparisons:
        raise StatisticalContractError("Holm family must be nonempty")
    for comparison in comparisons:
        if not 0.0 <= comparison.raw_p_value <= 1.0:
            raise StatisticalContractError("raw p-values must lie in [0,1]")
        if comparison.adjusted_p_value is not None:
            raise StatisticalContractError("Holm input must contain unadjusted comparisons")
    order = sorted(range(len(comparisons)), key=lambda index: comparisons[index].raw_p_value)
    adjusted = [0.0] * len(comparisons)
    running = 0.0
    family_size = len(comparisons)
    for rank, index in enumerate(order):
        candidate = min(1.0, (family_size - rank) * comparisons[index].raw_p_value)
        running = max(running, candidate)
        adjusted[index] = running
    return tuple(
        replace(comparison, adjusted_p_value=adjusted[index])
        for index, comparison in enumerate(comparisons)
    )


__all__ = [
    "PairedComparison",
    "SplitMetric",
    "SplitSummary",
    "StatisticalContractError",
    "VerifiedRunMetric",
    "aggregate_seed_within_split",
    "binary_roc_auc",
    "exact_sign_flip_pvalue",
    "holm_adjust",
    "multiclass_accuracy",
    "paired_comparison",
    "recompute_primary_metric",
    "summarize_splits",
]
