import json
import sys
from pathlib import Path

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legacy_reproduction import (
    HETERO_DATASETS,
    HETERO_MODELS,
    LRGB_MODELS,
    compute_multiclass_auroc,
    generate_report,
    validate_heterophily_record,
)


def test_experiment_inventory_matches_legacy_artifacts():
    heterophily = list((ROOT / "results").glob("*/*.json"))
    lrgb = list((ROOT / "results_LRGB").glob("*.json"))
    assert len(HETERO_DATASETS) * len(HETERO_MODELS) == 60
    assert len(heterophily) == 60
    assert len(LRGB_MODELS) == len(lrgb) == 2


@pytest.mark.parametrize(
    "path",
    [
        ROOT / "results" / "Roman-empire" / "GBDN+.json",
        ROOT / "results" / "Minesweeper" / "ChebNet.json",
        ROOT / "results" / "Tolokers" / "MLP.json",
    ],
)
def test_saved_legacy_metrics_recompute_from_predictions(path):
    record = json.loads(path.read_text(encoding="utf-8"))
    # Some preserved notebook artifacts have small internal AUROC drift between
    # their stored scalar and stored probabilities (maximum observed: 0.0036).
    assert validate_heterophily_record(record, tolerance=0.005) == []


def test_legacy_auroc_known_binary_ranking():
    labels = torch.tensor([0, 0, 1, 1])
    probabilities = torch.tensor(
        [[0.9, 0.1], [0.8, 0.2], [0.2, 0.8], [0.1, 0.9]]
    )
    assert compute_multiclass_auroc(labels, probabilities, 2) == pytest.approx(1.0)


def test_report_is_generated_from_artifacts(tmp_path):
    output = tmp_path / "report.md"
    generate_report(
        ROOT / "results",
        tmp_path / "missing-results",
        ROOT / "results_LRGB",
        tmp_path / "missing-lrgb",
        output,
    )
    report = output.read_text(encoding="utf-8")
    assert "Completed heterophily artifacts: **0/60**" in report
    assert "Completed Peptides-func artifacts: **0/2**" in report
