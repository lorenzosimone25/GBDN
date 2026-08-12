"""Pure, provenance-preserving renderers for confirmatory result artifacts.

This module does not discover runs or write files.  Callers must first
independently evaluate immutable prediction archives and construct the complete
frozen run grid.  The returned bytes can then be reviewed before an atomic
publication layer writes them to ``paper/generated``.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
import io
import json
import math
import re
from typing import Iterable, Mapping, Sequence

from gbdn.artifacts import canonical_json_bytes
from gbdn.heterophily_contract import OFFICIAL_SPLITS, TRAINING_SEEDS, resolve_dataset
from gbdn.heterophily_statistics import (
    PairedComparison,
    StatisticalContractError,
    VerifiedRunMetric,
    aggregate_seed_within_split,
    holm_adjust,
    paired_comparison,
    summarize_splits,
)


RESULT_RENDER_SCHEMA = "gbdn-confirmatory-render-v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class ProvenancedRunMetric:
    method: str
    dataset: str
    split: int
    seed: int
    metric_name: str
    value: float
    run_id: str
    prediction_sha256: str
    frozen_config_sha256: str
    independently_verified: bool = True
    frozen_config: bool = True
    test_used_for_selection: bool = False

    def verified_metric(self) -> VerifiedRunMetric:
        for name in ("run_id", "prediction_sha256", "frozen_config_sha256"):
            if not _SHA256.fullmatch(getattr(self, name)):
                raise StatisticalContractError(f"{name} must be lowercase SHA-256")
        return VerifiedRunMetric(
            self.method,
            self.dataset,
            self.split,
            self.seed,
            self.metric_name,
            self.value,
            self.independently_verified,
            self.frozen_config,
            self.test_used_for_selection,
        )


@dataclass(frozen=True)
class RenderedConfirmatoryArtifacts:
    split_level_metrics_csv: bytes
    summary_metrics_csv: bytes
    paired_tests_csv: bytes
    latex_table: bytes
    provenance_json: bytes


def _csv_bytes(header: Sequence[str], rows: Iterable[Sequence[object]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _latex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    return "".join(replacements.get(character, character) for character in value)


def render_confirmatory_artifacts(
    records: Iterable[ProvenancedRunMetric],
    *,
    methods: Sequence[str],
    datasets: Sequence[str],
    primary_method: str,
    tie_thresholds: Mapping[str, float],
) -> RenderedConfirmatoryArtifacts:
    """Validate the complete grid and render deterministic, unranked outputs."""

    if primary_method not in methods:
        raise StatisticalContractError("primary_method must be in the frozen method sequence")
    canonical_datasets = tuple(resolve_dataset(dataset).canonical_name for dataset in datasets)
    if set(tie_thresholds) != set(canonical_datasets):
        raise StatisticalContractError("tie thresholds must cover the frozen datasets exactly")
    materialized = tuple(records)
    verified: list[VerifiedRunMetric] = []
    run_ids: set[str] = set()
    provenance_by_cell: dict[tuple[str, str], list[ProvenancedRunMetric]] = {}
    config_by_cell: dict[tuple[str, str], str] = {}
    for record in materialized:
        metric = record.verified_metric()
        if record.run_id in run_ids:
            raise StatisticalContractError("duplicate provenance run_id")
        run_ids.add(record.run_id)
        key = (metric.method, metric.dataset)
        previous_config = config_by_cell.setdefault(key, record.frozen_config_sha256)
        if previous_config != record.frozen_config_sha256:
            raise StatisticalContractError("method--dataset cell uses multiple frozen configurations")
        provenance_by_cell.setdefault(key, []).append(record)
        verified.append(metric)

    split_metrics = aggregate_seed_within_split(
        verified, methods=methods, datasets=canonical_datasets
    )
    summaries = summarize_splits(split_metrics)
    summary_index = {(row.method, row.dataset): row for row in summaries}

    comparisons: list[PairedComparison] = []
    for dataset in canonical_datasets:
        for comparator in methods:
            if comparator != primary_method:
                comparisons.append(
                    paired_comparison(
                        split_metrics,
                        dataset=dataset,
                        method_a=primary_method,
                        method_b=comparator,
                        tie_threshold=float(tie_thresholds[dataset]),
                    )
                )
    adjusted = holm_adjust(comparisons) if comparisons else tuple()

    split_csv = _csv_bytes(
        ("method", "dataset", "split", "metric", "seed_mean", "seed_sd", "seeds"),
        (
            (
                row.method,
                row.dataset,
                row.split,
                row.metric_name,
                f"{row.seed_mean:.17g}",
                f"{row.seed_standard_deviation:.17g}",
                ";".join(map(str, row.seeds)),
            )
            for row in split_metrics
        ),
    )
    summary_csv = _csv_bytes(
        ("method", "dataset", "metric", "mean", "split_sd", "ci95_lower", "ci95_upper", "splits", "ci_procedure"),
        (
            (
                row.method,
                row.dataset,
                row.metric_name,
                f"{row.mean:.17g}",
                f"{row.standard_deviation:.17g}",
                f"{row.ci95_lower:.17g}",
                f"{row.ci95_upper:.17g}",
                row.split_count,
                row.ci_procedure,
            )
            for row in summaries
        ),
    )
    paired_csv = _csv_bytes(
        ("dataset", "method_a", "method_b", "metric", "mean_difference", "ci95_lower", "ci95_upper", "standardized_effect", "raw_p", "holm_p", "wins", "ties", "losses", "tie_threshold", "splits", "test_procedure"),
        (
            (
                row.dataset,
                row.method_a,
                row.method_b,
                row.metric_name,
                f"{row.mean_difference:.17g}",
                f"{row.ci95_lower:.17g}",
                f"{row.ci95_upper:.17g}",
                "NA" if row.standardized_effect is None else f"{row.standardized_effect:.17g}",
                f"{row.raw_p_value:.17g}",
                f"{row.adjusted_p_value:.17g}",
                row.wins,
                row.ties,
                row.losses,
                f"{row.tie_threshold:.17g}",
                row.split_count,
                row.test_procedure,
            )
            for row in adjusted
        ),
    )

    columns = "l" + "c" * len(canonical_datasets)
    lines = [
        "% Generated from immutable confirmatory artifacts; do not edit.",
        r"\begin{tabular}{" + columns + "}",
        r"\toprule",
        "Method & " + " & ".join(_latex_escape(name) for name in canonical_datasets) + r" \\",
        r"\midrule",
    ]
    for method in methods:
        cells = []
        for dataset in canonical_datasets:
            summary = summary_index[(method, dataset)]
            cells.append(
                f"{summary.mean:.4f} "
                f"[{summary.ci95_lower:.4f}, {summary.ci95_upper:.4f}]"
            )
        lines.append(_latex_escape(method) + " & " + " & ".join(cells) + r" \\")
    lines.extend((r"\bottomrule", r"\end{tabular}", ""))

    cells = []
    for method in methods:
        for dataset in canonical_datasets:
            rows = sorted(provenance_by_cell[(method, dataset)], key=lambda row: (row.split, row.seed))
            if tuple((row.split, row.seed) for row in rows) != tuple(
                (split, seed) for split in OFFICIAL_SPLITS for seed in TRAINING_SEEDS
            ):
                raise StatisticalContractError("provenance rows are not the complete ordered 10x3 grid")
            cells.append(
                {
                    "dataset": dataset,
                    "frozen_config_sha256": rows[0].frozen_config_sha256,
                    "method": method,
                    "prediction_sha256": [row.prediction_sha256 for row in rows],
                    "run_ids": [row.run_id for row in rows],
                }
            )
    provenance = {
        "cells": cells,
        "datasets": list(canonical_datasets),
        "methods": list(methods),
        "paired_comparisons": [asdict(row) for row in adjusted],
        "primary_method": primary_method,
        "schema_version": RESULT_RENDER_SCHEMA,
        "tie_thresholds": {dataset: float(tie_thresholds[dataset]) for dataset in canonical_datasets},
    }
    return RenderedConfirmatoryArtifacts(
        split_csv,
        summary_csv,
        paired_csv,
        "\n".join(lines).encode("utf-8"),
        canonical_json_bytes(provenance),
    )


__all__ = [
    "ProvenancedRunMetric",
    "RESULT_RENDER_SCHEMA",
    "RenderedConfirmatoryArtifacts",
    "render_confirmatory_artifacts",
]
