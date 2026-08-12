from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

import numpy as np
import pytest
import torch

from gbdn.artifacts import ArtifactValidationError, canonical_json_bytes, sha256_file
from gbdn.heterophily_evaluator import PREDICTION_FORMAT, evaluate_prediction_archive
from gbdn.heterophily_worker import (
    CHECKPOINT_SCHEMA,
    EVALUATION_RECORD_SCHEMA,
    EVALUATION_SNAPSHOT_FORMAT,
    SELECTION_SNAPSHOT_FORMAT,
    TRAINING_RECORD_SCHEMA,
    _load_config_snapshot,
    _official_metric,
    _validate_graph_arrays,
    run_evaluation_stage,
    run_training_stage,
)


def _config() -> dict[str, object]:
    return {
        "dataset": "Minesweeper",
        "method": "TightGBDN",
        "model": {
            "K": 1,
            "convention": "forward",
            "hidden_channels": 2,
            "num_layers": 1,
            "num_roots": 1,
            "r_max": 0.8,
        },
        "optimizer": {
            "amsgrad": False,
            "betas": [0.9, 0.999],
            "eps": 1e-8,
            "learning_rate": 0.01,
            "name": "Adam",
            "weight_decay": 0.0,
        },
        "source_path": "configs/submission/frozen/methods/TightGBDN.json",
        "source_sha256": "a" * 64,
        "training": {
            "checkpoint_tie_breaker": "earliest",
            "deterministic_algorithms": True,
            "gradient_clip_norm": 1.0,
            "max_epochs": 3,
            "min_delta": 0.0,
            "patience": 2,
            "precision": "float32",
            "selection_source": "validation_only",
        },
    }


def _cycle_edges(nodes: int) -> np.ndarray:
    undirected = np.asarray([(index, (index + 1) % nodes) for index in range(nodes)], dtype=np.int64)
    return np.concatenate((undirected, undirected[:, ::-1]), axis=0).T


def _npz(path: Path, **values: np.ndarray) -> None:
    stream = io.BytesIO()
    np.savez_compressed(stream, **values)
    path.write_bytes(stream.getvalue())


def _selection(path: Path) -> None:
    rng = np.random.default_rng(7)
    features = rng.normal(size=(12, 7)).astype(np.float32)
    _npz(
        path,
        dataset=np.asarray("Minesweeper"),
        edge_index=_cycle_edges(12),
        features=features,
        format=np.asarray(SELECTION_SNAPSHOT_FORMAT),
        split_id=np.asarray(0, dtype=np.int64),
        train_indices=np.asarray([0, 1, 2, 3, 4, 5], dtype=np.int64),
        train_labels=np.asarray([0, 1, 0, 1, 0, 1], dtype=np.int64),
        validation_indices=np.asarray([6, 7, 8, 9], dtype=np.int64),
        validation_labels=np.asarray([0, 1, 0, 1], dtype=np.int64),
    )


def _evaluation(path: Path, *, labels: np.ndarray | None = None) -> None:
    rng = np.random.default_rng(7)
    features = rng.normal(size=(12, 7)).astype(np.float32)
    _npz(
        path,
        dataset=np.asarray("Minesweeper"),
        edge_index=_cycle_edges(12),
        features=features,
        format=np.asarray(EVALUATION_SNAPSHOT_FORMAT),
        split_id=np.asarray(0, dtype=np.int64),
        test_indices=np.asarray([10, 11], dtype=np.int64),
        test_labels=np.asarray([0, 1] if labels is None else labels, dtype=np.int64),
    )


def test_worker_script_delays_torch_import_until_after_environment_check():
    source = (Path(__file__).parents[1] / "scripts" / "run_heterophily_job.py").read_text(
        encoding="utf-8"
    )
    assert "\nimport torch" not in source and "\nfrom torch" not in source
    assert source.index("_require_isolated_environment()") < source.index(
        "from gbdn.heterophily_worker import execute_planned_job"
    )


def test_method_config_is_closed_and_has_no_optimizer_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_bytes(canonical_json_bytes(_config()))
    loaded = _load_config_snapshot(path)
    assert loaded.optimizer["name"] == "Adam"
    broken = _config()
    del broken["optimizer"]["eps"]  # type: ignore[index]
    path.write_bytes(canonical_json_bytes(broken))
    with pytest.raises(ArtifactValidationError, match="keys"):
        _load_config_snapshot(path)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ('{"dataset":"Minesweeper","dataset":"Questions"}', "duplicate"),
        ('{"value":NaN}', "non-standard"),
    ],
)
def test_method_config_rejects_ambiguous_json(tmp_path, payload, message):
    path = tmp_path / "config.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match=message):
        _load_config_snapshot(path)


def test_task_specific_metric_dispatch_uses_accuracy_and_one_logit_auc():
    name, value = _official_metric(
        "Roman-empire",
        torch.tensor([[3.0] + [0.0] * 17, [0.0, 4.0] + [0.0] * 16]),
        torch.tensor([0, 1]),
    )
    assert name == "accuracy" and value == 1.0
    name, value = _official_metric(
        "Minesweeper", torch.tensor([-2.0, 0.5, 0.5, 3.0]), torch.tensor([0, 0, 1, 1])
    )
    assert name == "binary_roc_auc" and value == pytest.approx(0.875)


def test_training_snapshot_has_no_test_identifiers_or_labels(tmp_path):
    path = tmp_path / "selection.npz"
    _selection(path)
    with zipfile.ZipFile(path) as archive:
        names = {item.filename.removesuffix(".npy") for item in archive.infolist()}
    assert not any("test" in name for name in names)
    assert names == {
        "dataset",
        "edge_index",
        "features",
        "format",
        "split_id",
        "train_indices",
        "train_labels",
        "validation_indices",
        "validation_labels",
    }


def test_cpu_training_and_isolated_evaluation_emit_recomputable_predictions(tmp_path):
    config = tmp_path / "config.json"
    selection = tmp_path / "selection.npz"
    evaluation = tmp_path / "evaluation.npz"
    checkpoint = tmp_path / "checkpoint.pt"
    training_record = tmp_path / "training.json"
    prediction = tmp_path / "predictions.npz"
    evaluation_record = tmp_path / "evaluation.json"
    config.write_bytes(canonical_json_bytes(_config()))
    _selection(selection)
    _evaluation(evaluation)

    run_training_stage(
        selection_path=selection,
        config_path=config,
        checkpoint_path=checkpoint,
        record_path=training_record,
        seed=0,
        device_name="cpu",
    )
    checkpoint_hash = sha256_file(checkpoint)
    training = json.loads(training_record.read_text(encoding="utf-8"))
    assert training["schema_version"] == TRAINING_RECORD_SCHEMA
    assert training["selection"] == {
        "checkpoint_tie_breaker": "earliest",
        "metric": "binary_roc_auc",
        "source": "validation_only",
        "test_used_for_selection": False,
    }
    assert 1 <= training["selected_epoch"] <= 3
    assert all("test" not in json.dumps(item).lower() for item in training["history"])
    saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
    assert saved["schema_version"] == CHECKPOINT_SCHEMA

    run_evaluation_stage(
        evaluation_path=evaluation,
        config_path=config,
        checkpoint_path=checkpoint,
        prediction_path=prediction,
        record_path=evaluation_record,
        expected_checkpoint_sha256=checkpoint_hash,
        run_id="b" * 64,
        device_name="cpu",
    )
    evaluated = json.loads(evaluation_record.read_text(encoding="utf-8"))
    assert evaluated["schema_version"] == EVALUATION_RECORD_SCHEMA
    assert evaluated["metric"]["name"] == "binary_roc_auc"
    independently = evaluate_prediction_archive(
        prediction,
        expected_run_id="b" * 64,
        expected_dataset="Minesweeper",
        expected_split=0,
        expected_test_indices=np.asarray([10, 11], dtype=np.int64),
        authoritative_test_labels=np.asarray([0, 1], dtype=np.int64),
    )
    assert independently.metric_name == evaluated["metric"]["name"]
    assert independently.value == evaluated["metric"]["value"]


def test_evaluation_rejects_checkpoint_byte_drift(tmp_path):
    config = tmp_path / "config.json"
    selection = tmp_path / "selection.npz"
    evaluation = tmp_path / "evaluation.npz"
    checkpoint = tmp_path / "checkpoint.pt"
    config.write_bytes(canonical_json_bytes(_config()))
    _selection(selection)
    _evaluation(evaluation)
    run_training_stage(
        selection_path=selection,
        config_path=config,
        checkpoint_path=checkpoint,
        record_path=tmp_path / "training.json",
        seed=0,
        device_name="cpu",
    )
    expected = sha256_file(checkpoint)
    checkpoint.write_bytes(checkpoint.read_bytes() + b"tamper")
    with pytest.raises(ArtifactValidationError, match="frozen bytes"):
        run_evaluation_stage(
            evaluation_path=evaluation,
            config_path=config,
            checkpoint_path=checkpoint,
            prediction_path=tmp_path / "predictions.npz",
            record_path=tmp_path / "evaluation.json",
            expected_checkpoint_sha256=expected,
            run_id="b" * 64,
            device_name="cpu",
        )


def test_graph_validation_rejects_duplicate_pair_partition_leak_and_disconnection():
    spec = SimpleNamespace(
        node_count=4,
        feature_count=2,
        class_count=2,
        stored_undirected_edges=3,
    )
    features = np.zeros((4, 2), dtype=np.float32)
    labels = np.asarray([0, 1, 0, 1], dtype=np.int64)
    masks = np.zeros((10, 4), dtype=np.bool_)
    masks[:, :2] = True
    validation = np.zeros_like(masks)
    validation[:, 2] = True
    test = np.zeros_like(masks)
    test[:, 3] = True
    with patch("gbdn.heterophily_worker.resolve_dataset", return_value=spec):
        _validate_graph_arrays(
            features=features,
            labels=labels,
            edges=np.asarray([[0, 1], [1, 2], [2, 3]], dtype=np.int64),
            masks=(masks, validation, test),
            dataset="synthetic",
        )
        with pytest.raises(ArtifactValidationError, match="duplicate"):
            _validate_graph_arrays(
                features=features,
                labels=labels,
                edges=np.asarray([[0, 1], [1, 0], [2, 3]], dtype=np.int64),
                masks=(masks, validation, test),
                dataset="synthetic",
            )
        leaking = validation.copy()
        leaking[:, 0] = True
        with pytest.raises(ArtifactValidationError, match="partition"):
            _validate_graph_arrays(
                features=features,
                labels=labels,
                edges=np.asarray([[0, 1], [1, 2], [2, 3]], dtype=np.int64),
                masks=(masks, leaking, test),
                dataset="synthetic",
            )
        with pytest.raises(ArtifactValidationError, match="connected"):
            _validate_graph_arrays(
                features=features,
                labels=labels,
                edges=np.asarray([[0, 1], [1, 2], [0, 2]], dtype=np.int64),
                masks=(masks, validation, test),
                dataset="synthetic",
            )


def test_evaluation_snapshot_does_not_contain_training_or_validation_partitions(tmp_path):
    path = tmp_path / "evaluation.npz"
    _evaluation(path)
    with zipfile.ZipFile(path) as archive:
        names = {item.filename.removesuffix(".npy") for item in archive.infolist()}
    assert not any("train" in name or "validation" in name for name in names)
    assert PREDICTION_FORMAT not in names
