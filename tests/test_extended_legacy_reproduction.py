from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import torch
from torch_geometric.data import Batch, Data


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import extended_legacy_reproduction as extended  # noqa: E402

SPEC = importlib.util.spec_from_file_location("extended_legacy_cli", ROOT / "scripts" / "reproduce_legacy.py")
assert SPEC and SPEC.loader
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


def _hetero_record(split: int, seed: int, identity: str) -> dict:
    labels = [0, 1, 0, 1]
    predictions = [[0.9, 0.1], [0.2, 0.8], [0.8, 0.2], [0.1, 0.9]]
    record = {
        "schema_version": extended.SCHEMA_RAW,
        "artifact_type": "raw_run",
        "task": "heterophily_node_classification",
        "dataset": "Minesweeper",
        "model": "MLP",
        "split": split,
        "seed": seed,
        "selected_epoch": 2,
        "val_predictions": predictions,
        "val_labels": labels,
        "test_predictions": predictions,
        "test_labels": labels,
        "metrics": {},
        "provenance": {"identity": identity},
    }
    record["metrics"] = extended.recompute_raw_metrics(record)
    return record


def test_expected_counts_paths_and_cli_defaults():
    assert extended.expected_counts((0, 1, 2)) == {
        "heterophily_raw": 180,
        "peptides_raw": 10,
        "heterophily_summaries": 60,
        "peptides_summaries": 10,
    }
    assert str(extended.heterophily_raw_path(Path("r"), "Questions", "GAT", 2, 25)).replace("\\", "/") == "r/Questions/GAT/split-02_seed-25.json"
    assert str(extended.peptide_raw_path(Path("r"), "Peptides-struct", "GINE", 25)).replace("\\", "/") == "r/Peptides-struct/GINE/seed-25.json"
    args = cli.build_parser().parse_args(["run-all", "--splits", "0", "1", "2", "--seed", "25", "--workers", "auto"])
    assert args.splits == [0, 1, 2]
    assert args.seed == 25
    assert len(args.heterophily_models) == 12
    assert len(args.peptides_models) == 5


def test_raw_artifact_no_overwrite_resume_and_aggregate(tmp_path):
    paths = []
    for split in (0, 1, 2):
        path = extended.heterophily_raw_path(tmp_path, "Minesweeper", "MLP", split, 25)
        payload = _hetero_record(split, 25, f"id-{split}")
        assert extended._write_immutable_json(path, payload)
        assert not extended._write_immutable_json(path, payload)
        changed = {**payload, "provenance": {"identity": "different"}}
        with pytest.raises(FileExistsError):
            extended._write_immutable_json(path, changed)
        paths.append(path)

    tampered = json.loads(paths[0].read_text())
    tampered["selected_epoch"] = 99
    paths[0].write_text(json.dumps(tampered))
    with pytest.raises(ValueError, match="content hash"):
        extended.validate_raw_artifact(paths[0])
    extended._write_immutable_json(paths[0], _hetero_record(0, 25, "id-0"), rerun=True)

    summary = extended._aggregate(paths, extended.heterophily_summary_path(tmp_path, "Minesweeper", "MLP"))
    value = json.loads(summary.read_text())
    assert value["run_count"] == 3
    assert value["metrics"]["test_acc"]["mean"] == pytest.approx(1.0)
    assert value["metrics"]["test_acc"]["std"] == pytest.approx(0.0)
    assert [item["path"] for item in value["raw_runs"]] == [
        "Minesweeper/MLP/split-00_seed-25.json",
        "Minesweeper/MLP/split-01_seed-25.json",
        "Minesweeper/MLP/split-02_seed-25.json",
    ]


def test_metric_examples_and_checkpoint_direction():
    targets = np.asarray([[1, 0], [0, 1], [1, 0], [0, 1]])
    perfect = np.asarray([[0.9, 0.1], [0.1, 0.8], [0.8, 0.2], [0.2, 0.9]])
    assert extended.macro_average_precision(targets, perfect) == pytest.approx(1.0)
    assert extended.mean_absolute_error(np.asarray([[0.0, 2.0]]), np.asarray([[1.0, 0.0]])) == pytest.approx(1.5)
    assert extended.checkpoint_improved(0.6, 0.5, "maximize")
    assert not extended.checkpoint_improved(0.4, 0.5, "maximize")
    assert extended.checkpoint_improved(0.4, 0.5, "minimize")
    assert not extended.checkpoint_improved(0.6, 0.5, "minimize")


def _synthetic_batch() -> Batch:
    graphs = []
    for nodes in (3, 4):
        source = torch.arange(nodes, dtype=torch.long)
        target = torch.roll(source, -1)
        edge_index = torch.cat([torch.stack([source, target]), torch.stack([target, source])], dim=1)
        x = torch.zeros((nodes, 9), dtype=torch.long)
        x[:, 0] = torch.arange(nodes) % 10
        x[:, 2] = 1
        x[:, 3] = 4
        x[:, 6] = 1
        edge_attr = torch.zeros((edge_index.shape[1], 3), dtype=torch.long)
        edge_attr[:, 0] = torch.arange(edge_index.shape[1]) % 4
        graphs.append(Data(x=x, edge_index=edge_index, edge_attr=edge_attr))
    return Batch.from_data_list(graphs)


@pytest.mark.parametrize("model_name", extended.EXTENDED_LRGB_MODELS)
def test_all_peptide_models_encode_bonds_and_have_correct_shapes(model_name):
    batch = _synthetic_batch()
    model = extended.PeptideGraphModel(model_name, out_dim=10, hidden_dim=32, dropout=0.5)
    output = model(batch.x, batch.edge_index, batch.edge_attr, batch.batch)
    assert output.shape == (2, 10)
    output.sum().backward()
    assert all(parameter.grad is not None for parameter in model.parameters() if parameter.requires_grad)


def test_categorical_encoder_rejects_wrong_shape_and_range():
    encoder = extended.CategoricalFeatureEncoder((3, 2), 8)
    assert encoder(torch.tensor([[0, 1], [2, 0]])).shape == (2, 8)
    with pytest.raises(ValueError):
        encoder(torch.tensor([[3, 0]]))
    with pytest.raises(ValueError):
        encoder(torch.tensor([0, 1]))


def test_split_validation_and_failure_isolation(tmp_path, monkeypatch):
    assert cli._validate_splits([0, 1, 2]) == (0, 1, 2)
    with pytest.raises(ValueError):
        cli._validate_splits([0, 0])
    with pytest.raises(ValueError):
        cli._validate_splits([10])

    calls = []
    monkeypatch.setattr(cli, "verify_h100", lambda: {"name": "H100"})
    monkeypatch.setattr(cli, "environment_manifest", lambda gpu=None: {"gpu": gpu})
    monkeypatch.setattr(cli, "_resolve_workers", lambda value, job_count=22: 2)
    monkeypatch.setattr(cli, "prepare_extended_datasets", lambda *args: None)
    monkeypatch.setattr(cli, "aggregate_heterophily", lambda *a, **k: pytest.fail("must not aggregate failed sweep"))
    monkeypatch.setattr(cli, "aggregate_peptides", lambda *a, **k: pytest.fail("must not aggregate failed sweep"))

    def fake_run(command, log_path):
        model = command[command.index("--model") + 1]
        calls.append(model)
        return int(model == "GAT")

    monkeypatch.setattr(cli, "_run_logged", fake_run)
    args = cli.build_parser().parse_args([
        "run-all", "--output-root", str(tmp_path / "h"), "--lrgb-output-root", str(tmp_path / "p"),
        "--heterophily-datasets", "Minesweeper", "--heterophily-models", "MLP", "GAT",
        "--peptides-datasets", "Peptides-func", "--peptides-models", "GCN", "--workers", "2",
    ])
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    assert cli._run_all(args) == 1
    assert set(calls) == {"MLP", "GAT", "GCN"}
    manifest = json.loads((tmp_path / "h" / "run_manifest.json").read_text())
    assert manifest["status"] == "failed"
    assert manifest["expected_total_raw"] == 7


def test_notebook_all_code_cells_parse():
    notebook = json.loads((ROOT / "notebooks" / "reproduce_legacy.ipynb").read_text(encoding="utf-8"))
    assert notebook["nbformat"] == 4
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    assert len(code_cells) >= 6
    for index, cell in enumerate(code_cells):
        compile("".join(cell["source"]), f"notebook-cell-{index}", "exec")


def test_dataset_preparation_is_sequential_and_complete(tmp_path, monkeypatch):
    observed = []

    class FakeHetero:
        def __init__(self, root, name):
            observed.append(("hetero", name, None))

    class FakeLRGB:
        def __init__(self, root, name, split):
            observed.append(("peptide", name, split))

    monkeypatch.setattr(extended, "HeterophilousGraphDataset", FakeHetero)
    monkeypatch.setattr(extended, "LRGBDataset", FakeLRGB)
    extended.prepare_extended_datasets(tmp_path, ["Minesweeper"], ["Peptides-struct"])
    assert observed == [
        ("hetero", "Minesweeper", None),
        ("peptide", "Peptides-struct", "train"),
        ("peptide", "Peptides-struct", "val"),
        ("peptide", "Peptides-struct", "test"),
    ]
