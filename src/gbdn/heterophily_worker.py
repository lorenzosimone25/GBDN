"""Canonical, leakage-isolated worker for official heterophily jobs.

The public worker process validates one immutable run-plan entry, prepares two
disjoint temporary views of the pinned NPZ, and launches fresh subprocesses for
validation-only checkpoint selection and post-freeze test evaluation.  The
selection subprocess never receives test indices or test labels.  The final
prediction archive is intentionally compatible with
``gbdn.heterophily_evaluator`` so the scheduler can recompute the metric from
authoritative labels using an independent implementation.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import random
import subprocess
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Mapping

import numpy as np
import torch
from torch import nn

from gbdn.artifacts import (
    ArtifactValidationError,
    AtomicRunBundle,
    PredictionArtifactManifest,
    RunConfigRecord,
    RunResultRecord,
    canonical_json_bytes,
    capture_environment_metadata,
    sha256_file,
)
from gbdn.baseline_contract import VerifiedBaseline
from gbdn.heterophily_contract import DATASET_REGISTRY, OFFICIAL_SPLITS, resolve_dataset
from gbdn.heterophily_evaluator import PREDICTION_FORMAT
from gbdn.heterophily_training import official_training_loss
from gbdn.model import GBDNProductSum, GBDNRelaxed, GBDNTight
from gbdn.operations_acceptance import validate_operations_acceptance
from gbdn.run_plan import ValidatedRunPlan, validate_run_plan


WORKER_RESULT_SCHEMA: Final[str] = "gbdn-official-heterophily-worker-result-v1"
METHOD_CONFIG_SCHEMA: Final[str] = "gbdn-heterophily-method-config-v1"
CHECKPOINT_SCHEMA: Final[str] = "gbdn-heterophily-checkpoint-v1"
SELECTION_SNAPSHOT_FORMAT: Final[str] = "gbdn-heterophily-selection-snapshot-v1"
EVALUATION_SNAPSHOT_FORMAT: Final[str] = "gbdn-heterophily-evaluation-snapshot-v1"
TRAINING_RECORD_SCHEMA: Final[str] = "gbdn-heterophily-training-record-v1"
EVALUATION_RECORD_SCHEMA: Final[str] = "gbdn-heterophily-evaluation-record-v1"

_MAX_JSON_BYTES: Final[int] = 16 * 1024 * 1024
_MAX_SNAPSHOT_BYTES: Final[int] = 1024 * 1024 * 1024
_MAX_EPOCHS: Final[int] = 100_000
_LOCAL_METHOD_CONFIGS: Final[Mapping[str, str]] = {
    "TightGBDN": "configs/submission/frozen/methods/TightGBDN.json",
    "ProductSumGBDN": "configs/submission/frozen/methods/ProductSumGBDN.json",
    "GBDNPlus": "configs/submission/frozen/methods/GBDNPlus.json",
}
_SUPPORTED_METHODS: Final[frozenset[str]] = frozenset(
    {*_LOCAL_METHOD_CONFIGS, "ChebNet"}
)


def _reject_constant(value: str) -> None:
    raise ArtifactValidationError(f"non-standard JSON constant: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ArtifactValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: str | Path, *, label: str) -> Mapping[str, Any]:
    target = Path(path)
    if (
        target.is_symlink()
        or not target.is_file()
        or target.stat().st_size > _MAX_JSON_BYTES
    ):
        raise ArtifactValidationError(f"{label} must be a bounded regular file")
    try:
        value = json.loads(
            target.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError(f"{label} must be valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ArtifactValidationError(f"{label} root must be an object")
    return value


def _load_json_bytes(payload: bytes, *, label: str) -> Mapping[str, Any]:
    if not payload or len(payload) > _MAX_JSON_BYTES:
        raise ArtifactValidationError(f"{label} must be bounded nonempty bytes")
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError(f"{label} must be valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ArtifactValidationError(f"{label} root must be an object")
    if canonical_json_bytes(value) != payload:
        raise ArtifactValidationError(f"{label} must use canonical JSON encoding")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ArtifactValidationError(f"{label} keys do not match the frozen schema")


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise ArtifactValidationError(f"{label} must be a positive integer")
    return value


def _finite_number(value: Any, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise ArtifactValidationError(f"{label} must be finite")
    return float(value)


def _regular_repository_file(root: Path, relative: str, label: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise ArtifactValidationError(f"{label} path is invalid")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ArtifactValidationError(f"{label} must be repository-relative")
    lexical = root / candidate
    if lexical.is_symlink() or not lexical.is_file():
        raise ArtifactValidationError(f"{label} must be a regular repository file")
    resolved = lexical.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ArtifactValidationError(f"{label} escapes repository root")
    return resolved


@dataclass(frozen=True)
class FrozenMethodConfig:
    method: str
    dataset: str
    model: Mapping[str, Any]
    optimizer: Mapping[str, Any]
    training: Mapping[str, Any]
    source_path: str
    source_sha256: str


def _validate_optimizer(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ArtifactValidationError("optimizer configuration must be an object")
    _exact_keys(
        value,
        {"amsgrad", "betas", "eps", "learning_rate", "name", "weight_decay"},
        "optimizer configuration",
    )
    if value["name"] not in {"Adam", "AdamW"}:
        raise ArtifactValidationError("only explicitly configured Adam/AdamW are supported")
    betas = value["betas"]
    if (
        not isinstance(betas, list)
        or len(betas) != 2
        or any(not 0.0 <= _finite_number(item, "optimizer beta") < 1.0 for item in betas)
    ):
        raise ArtifactValidationError("optimizer betas must be two finite values in [0,1)")
    if _finite_number(value["learning_rate"], "learning_rate") <= 0:
        raise ArtifactValidationError("learning_rate must be positive")
    if _finite_number(value["weight_decay"], "weight_decay") < 0:
        raise ArtifactValidationError("weight_decay must be nonnegative")
    if _finite_number(value["eps"], "optimizer eps") <= 0:
        raise ArtifactValidationError("optimizer eps must be positive")
    if type(value["amsgrad"]) is not bool:
        raise ArtifactValidationError("optimizer amsgrad must be boolean")
    return value


def _validate_training(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ArtifactValidationError("training configuration must be an object")
    _exact_keys(
        value,
        {
            "checkpoint_tie_breaker",
            "deterministic_algorithms",
            "gradient_clip_norm",
            "max_epochs",
            "min_delta",
            "patience",
            "precision",
            "selection_source",
        },
        "training configuration",
    )
    epochs = _positive_int(value["max_epochs"], "max_epochs")
    if epochs > _MAX_EPOCHS:
        raise ArtifactValidationError("max_epochs exceeds the worker safety bound")
    patience = _positive_int(value["patience"], "patience")
    if patience > epochs:
        raise ArtifactValidationError("patience cannot exceed max_epochs")
    if _finite_number(value["min_delta"], "min_delta") < 0:
        raise ArtifactValidationError("min_delta must be nonnegative")
    clip = value["gradient_clip_norm"]
    if clip is not None and _finite_number(clip, "gradient_clip_norm") <= 0:
        raise ArtifactValidationError("gradient_clip_norm must be null or positive")
    required = {
        "checkpoint_tie_breaker": "earliest",
        "deterministic_algorithms": True,
        "precision": "float32",
        "selection_source": "validation_only",
    }
    for key, expected in required.items():
        if value[key] != expected:
            raise ArtifactValidationError(f"training {key} must be {expected!r}")
    return value


def _validate_model(method: str, value: Any) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ArtifactValidationError("model configuration must be an object")
    if method in {"TightGBDN", "ProductSumGBDN"}:
        expected = {"K", "convention", "hidden_channels", "num_layers", "num_roots", "r_max"}
    elif method == "GBDNPlus":
        expected = {"K", "convention", "dropout", "hidden_channels", "num_layers", "r_max"}
    elif method == "ChebNet":
        expected = {"K", "dropout", "hidden_channels"}
    else:
        raise ArtifactValidationError(f"method has no canonical worker adapter: {method}")
    _exact_keys(value, expected, f"{method} model configuration")
    for field in expected & {"K", "hidden_channels", "num_layers", "num_roots"}:
        _positive_int(value[field], f"model {field}")
    for field in expected & {"dropout"}:
        number = _finite_number(value[field], f"model {field}")
        if not 0.0 <= number < 1.0:
            raise ArtifactValidationError(f"model {field} must lie in [0,1)")
    if "r_max" in expected and not 0.0 < _finite_number(value["r_max"], "model r_max") < 1.0:
        raise ArtifactValidationError("model r_max must lie strictly in (0,1)")
    if "convention" in expected and value["convention"] not in {"forward", "inverse"}:
        raise ArtifactValidationError("model convention must be forward or inverse")
    return value


def load_frozen_method_config(
    repository_root: str | Path,
    *,
    job: RunConfigRecord,
    baselines: tuple[VerifiedBaseline, ...],
) -> FrozenMethodConfig:
    """Load one source-bound method/dataset configuration without defaults."""

    root = Path(repository_root).resolve(strict=True)
    method = job.identity.model_name
    dataset = resolve_dataset(job.identity.dataset_name).canonical_name
    baseline_records = {item.name: item for item in baselines}
    if method in baseline_records:
        relative = baseline_records[method].reference_config_path
        expected_sha256 = baseline_records[method].reference_config_sha256
    else:
        relative = _LOCAL_METHOD_CONFIGS.get(method, "")
        expected_sha256 = ""
    if not relative:
        raise ArtifactValidationError(f"method has no frozen executable configuration: {method}")
    path = _regular_repository_file(root, relative, "method configuration")
    observed_sha256 = sha256_file(path)
    if expected_sha256 and observed_sha256 != expected_sha256:
        raise ArtifactValidationError("baseline method configuration differs from registry")
    data = _load_json(path, label="method configuration")
    _exact_keys(data, {"datasets", "method", "schema_version"}, "method configuration")
    if data["schema_version"] != METHOD_CONFIG_SCHEMA or data["method"] != method:
        raise ArtifactValidationError("method configuration identity is invalid")
    datasets = data["datasets"]
    if not isinstance(datasets, dict) or set(datasets) != set(DATASET_REGISTRY):
        raise ArtifactValidationError("method configuration must freeze all five datasets")
    selected = datasets[dataset]
    if not isinstance(selected, dict):
        raise ArtifactValidationError("dataset method configuration must be an object")
    _exact_keys(selected, {"model", "optimizer", "training"}, "dataset method configuration")
    return FrozenMethodConfig(
        method,
        dataset,
        _validate_model(method, selected["model"]),
        _validate_optimizer(selected["optimizer"]),
        _validate_training(selected["training"]),
        relative,
        observed_sha256,
    )
def _build_model(config: FrozenMethodConfig) -> nn.Module:
    spec = resolve_dataset(config.dataset)
    values = dict(config.model)
    if config.method == "TightGBDN":
        return GBDNTight(spec.feature_count, values.pop("hidden_channels"), spec.output_logits, **values)
    if config.method == "ProductSumGBDN":
        return GBDNProductSum(spec.feature_count, values.pop("hidden_channels"), spec.output_logits, **values)
    if config.method == "GBDNPlus":
        return GBDNRelaxed(spec.feature_count, values.pop("hidden_channels"), spec.output_logits, **values)
    if config.method == "ChebNet":
        from gbdn.baselines.chebnet import ChebNet

        return ChebNet.for_official_dataset(
            config.dataset,
            in_channels=spec.feature_count,
            **values,
        )
    raise ArtifactValidationError(f"method has no canonical model builder: {config.method}")


def _optimizer(model: nn.Module, config: Mapping[str, Any]) -> torch.optim.Optimizer:
    optimizer_class = torch.optim.AdamW if config["name"] == "AdamW" else torch.optim.Adam
    return optimizer_class(
        model.parameters(),
        lr=float(config["learning_rate"]),
        betas=(float(config["betas"][0]), float(config["betas"][1])),
        eps=float(config["eps"]),
        weight_decay=float(config["weight_decay"]),
        amsgrad=config["amsgrad"],
    )


def _seed_everything(seed: int) -> None:
    if type(seed) is not int or seed < 0:
        raise ArtifactValidationError("training seed must be a nonnegative integer")
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True


def _forward_logits(model: nn.Module, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
    output = model(x, edge_index)
    logits = output[0] if isinstance(output, tuple) else output
    if not isinstance(logits, torch.Tensor):
        raise ArtifactValidationError("model did not return tensor logits")
    return logits


def _binary_auc(scores: np.ndarray, labels: np.ndarray) -> float:
    if scores.ndim != 1 or labels.shape != scores.shape:
        raise ArtifactValidationError("binary validation arrays are misaligned")
    positives = int(np.count_nonzero(labels == 1))
    negatives = int(np.count_nonzero(labels == 0))
    if positives == 0 or negatives == 0:
        raise ArtifactValidationError("binary validation metric requires both classes")
    order = np.argsort(scores, kind="mergesort")
    sorted_scores = scores[order]
    ranks = np.empty(scores.size, dtype=np.float64)
    start = 0
    while start < scores.size:
        stop = start + 1
        while stop < scores.size and sorted_scores[stop] == sorted_scores[start]:
            stop += 1
        ranks[order[start:stop]] = 0.5 * ((start + 1) + stop)
        start = stop
    rank_sum = float(np.sum(ranks[labels == 1]))
    return (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def _official_metric(dataset: str, logits: torch.Tensor, labels: torch.Tensor) -> tuple[str, float]:
    spec = resolve_dataset(dataset)
    scores = logits.detach().to(device="cpu", dtype=torch.float64).numpy()
    targets = labels.detach().to(device="cpu", dtype=torch.int64).numpy()
    if not np.all(np.isfinite(scores)):
        raise ArtifactValidationError("validation/evaluation logits must be finite")
    if spec.selection_metric == "accuracy":
        if scores.shape != (targets.size, spec.output_logits):
            raise ArtifactValidationError("multiclass validation head has the wrong shape")
        if np.any(targets < 0) or np.any(targets >= spec.class_count):
            raise ArtifactValidationError("multiclass labels fall outside the official classes")
        return "accuracy", float(np.mean(np.argmax(scores, axis=1) == targets))
    if scores.shape == (targets.size, 1):
        scores = scores[:, 0]
    if scores.shape != (targets.size,):
        raise ArtifactValidationError("binary validation head must emit one logit")
    if not np.all(np.isin(targets, (0, 1))):
        raise ArtifactValidationError("binary labels must be exactly zero or one")
    return "binary_roc_auc", float(_binary_auc(scores, targets))


def _roots(model: nn.Module) -> list[list[dict[str, float]]]:
    layers = getattr(model, "layers", getattr(model, "factors", ()))
    result: list[list[dict[str, float]]] = []
    for layer in layers:
        getter = getattr(layer, "get_roots", None)
        if getter is None:
            continue
        values = getter().detach().to(device="cpu")
        result.append(
            [
                {"imag": float(value.imag), "real": float(value.real)}
                for value in values.reshape(-1)
            ]
        )
    return result


def _resource_count(model: nn.Module, config: FrozenMethodConfig) -> dict[str, Any]:
    parameters = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    if config.method == "ChebNet":
        count = model.resource_count()  # type: ignore[attr-defined]
        if count.trainable_parameters != parameters:
            raise ArtifactValidationError("ChebNet parameter accounting disagrees with module")
        spmvs = count.feature_matrix_spmvs_per_forward
        convention = count.convention
    elif config.method in {"TightGBDN", "ProductSumGBDN"}:
        spmvs = int(config.model["K"]) * int(config.model["num_layers"])
        convention = "one sparse Laplacian-feature multiplication per Chebyshev recurrence step"
    elif config.method == "GBDNPlus":
        spmvs = int(config.model["K"])
        convention = "one shared Chebyshev basis; dense channel/root operations excluded"
    else:  # pragma: no cover - guarded by configuration validation
        raise ArtifactValidationError("unsupported resource-count method")
    return {
        "feature_matrix_spmvs_per_forward": spmvs,
        "spmv_convention": convention,
        "trainable_parameters": parameters,
    }


def _npz_bytes(**arrays: np.ndarray) -> bytes:
    stream = io.BytesIO()
    np.savez_compressed(stream, **arrays)
    return stream.getvalue()


def _safe_npz(path: Path, expected_members: set[str], *, label: str) -> Mapping[str, np.ndarray]:
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_size <= 0
        or path.stat().st_size > _MAX_SNAPSHOT_BYTES
    ):
        raise ArtifactValidationError(f"{label} must be a regular file")
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            raw_names = [item.filename for item in members]
            names = [name.removesuffix(".npy") for name in raw_names]
            if (
                set(names) != expected_members
                or len(names) != len(expected_members)
                or any(
                    item.is_dir()
                    or not item.filename.endswith(".npy")
                    or item.file_size > _MAX_SNAPSHOT_BYTES
                    for item in members
                )
            ):
                raise ArtifactValidationError(f"{label} members do not match schema")
        with np.load(path, allow_pickle=False) as stored:
            return {name: np.asarray(stored[name]) for name in expected_members}
    except ArtifactValidationError:
        raise
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        raise ArtifactValidationError(f"{label} is invalid") from exc


def _validate_graph_arrays(
    *,
    features: np.ndarray,
    labels: np.ndarray,
    edges: np.ndarray,
    masks: tuple[np.ndarray, np.ndarray, np.ndarray],
    dataset: str,
) -> None:
    spec = resolve_dataset(dataset)
    if features.shape != (spec.node_count, spec.feature_count) or features.dtype not in (
        np.dtype("float32"),
        np.dtype("float64"),
    ):
        raise ArtifactValidationError("official node_features shape/dtype is invalid")
    if not np.all(np.isfinite(features)):
        raise ArtifactValidationError("official node_features contain nonfinite values")
    if labels.dtype != np.int64 or labels.shape != (spec.node_count,):
        raise ArtifactValidationError("official node_labels shape/dtype is invalid")
    if np.any(labels < 0) or np.any(labels >= spec.class_count):
        raise ArtifactValidationError("official labels fall outside the task classes")
    if edges.dtype != np.int64 or edges.shape != (spec.stored_undirected_edges, 2):
        raise ArtifactValidationError("official stored edges shape/dtype is invalid")
    if np.any(edges < 0) or np.any(edges >= spec.node_count) or np.any(edges[:, 0] == edges[:, 1]):
        raise ArtifactValidationError("official stored edges contain invalid endpoints/self-loops")
    canonical_edges = np.sort(edges, axis=1)
    if np.unique(canonical_edges, axis=0).shape[0] != edges.shape[0]:
        raise ArtifactValidationError("official stored edges contain duplicate undirected pairs")
    for mask in masks:
        if mask.dtype != np.bool_ or mask.shape != (len(OFFICIAL_SPLITS), spec.node_count):
            raise ArtifactValidationError("official masks differ from the ten-row contract")
    train_masks, validation_masks, test_masks = masks
    for split in OFFICIAL_SPLITS:
        assigned = (
            train_masks[split].astype(np.uint8)
            + validation_masks[split].astype(np.uint8)
            + test_masks[split].astype(np.uint8)
        )
        if not np.all(assigned == 1):
            raise ArtifactValidationError(f"official split {split} is not an exact partition")
    parent = np.arange(spec.node_count, dtype=np.int64)

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = int(parent[node])
        return node

    for left, right in edges:
        a, b = find(int(left)), find(int(right))
        if a != b:
            parent[b] = a
    if len({find(node) for node in range(spec.node_count)}) != 1:
        raise ArtifactValidationError("official graph is not connected")


def prepare_official_snapshots(
    authoritative_dataset_root: str | Path,
    *,
    dataset: str,
    split: int,
    selection_path: str | Path,
    evaluation_path: str | Path,
) -> None:
    """Create disjoint temporary views from one checksum-pinned NPZ."""

    spec = resolve_dataset(dataset)
    if type(split) is not int or split not in OFFICIAL_SPLITS:
        raise ArtifactValidationError("worker split is outside official rows 0..9")
    dataset_root = Path(authoritative_dataset_root).resolve(strict=True)
    archive = dataset_root / Path(spec.npz_path).name
    if archive.is_symlink() or not archive.is_file():
        raise ArtifactValidationError("official NPZ must be a regular file in the authoritative root")
    resolved_archive = archive.resolve(strict=True)
    if not resolved_archive.is_relative_to(dataset_root):
        raise ArtifactValidationError("official NPZ escapes the authoritative dataset root")
    if archive.is_symlink() or not archive.is_file():
        raise ArtifactValidationError("pinned official NPZ is absent")
    if archive.stat().st_size != spec.npz_size_bytes or sha256_file(archive) != spec.npz_sha256:
        raise ArtifactValidationError("official NPZ differs from its pinned byte identity")
    try:
        with np.load(archive, allow_pickle=False) as stored:
            required = {"node_features", "node_labels", "edges", "train_masks", "val_masks", "test_masks"}
            if set(stored.files) != required:
                raise ArtifactValidationError("official NPZ members do not match the frozen contract")
            features = np.asarray(stored["node_features"])
            labels = np.asarray(stored["node_labels"]).reshape(-1)
            edges = np.asarray(stored["edges"])
            train_masks = np.asarray(stored["train_masks"])
            validation_masks = np.asarray(stored["val_masks"])
            test_masks = np.asarray(stored["test_masks"])
    except ArtifactValidationError:
        raise
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        raise ArtifactValidationError("official NPZ cannot be decoded safely") from exc
    _validate_graph_arrays(
        features=features,
        labels=labels,
        edges=edges,
        masks=(train_masks, validation_masks, test_masks),
        dataset=dataset,
    )
    reciprocal = np.concatenate((edges, edges[:, ::-1]), axis=0).T
    train_indices = np.flatnonzero(train_masks[split]).astype(np.int64, copy=False)
    validation_indices = np.flatnonzero(validation_masks[split]).astype(np.int64, copy=False)
    test_indices = np.flatnonzero(test_masks[split]).astype(np.int64, copy=False)
    selection_payload = _npz_bytes(
        dataset=np.asarray(spec.canonical_name),
        edge_index=np.ascontiguousarray(reciprocal, dtype=np.int64),
        features=np.ascontiguousarray(features, dtype=np.float32),
        format=np.asarray(SELECTION_SNAPSHOT_FORMAT),
        split_id=np.asarray(split, dtype=np.int64),
        train_indices=train_indices,
        train_labels=np.ascontiguousarray(labels[train_indices], dtype=np.int64),
        validation_indices=validation_indices,
        validation_labels=np.ascontiguousarray(labels[validation_indices], dtype=np.int64),
    )
    evaluation_payload = _npz_bytes(
        dataset=np.asarray(spec.canonical_name),
        edge_index=np.ascontiguousarray(reciprocal, dtype=np.int64),
        features=np.ascontiguousarray(features, dtype=np.float32),
        format=np.asarray(EVALUATION_SNAPSHOT_FORMAT),
        split_id=np.asarray(split, dtype=np.int64),
        test_indices=test_indices,
        test_labels=np.ascontiguousarray(labels[test_indices], dtype=np.int64),
    )
    Path(selection_path).write_bytes(selection_payload)
    Path(evaluation_path).write_bytes(evaluation_payload)


def _load_config_snapshot(path: Path) -> FrozenMethodConfig:
    data = _load_json(path, label="internal method configuration")
    _exact_keys(
        data,
        {"dataset", "method", "model", "optimizer", "source_path", "source_sha256", "training"},
        "internal method configuration",
    )
    method = data["method"]
    dataset = resolve_dataset(data["dataset"]).canonical_name
    if method not in _SUPPORTED_METHODS:
        raise ArtifactValidationError("internal method is unsupported")
    source_sha256 = data["source_sha256"]
    if (
        not isinstance(source_sha256, str)
        or len(source_sha256) != 64
        or any(character not in "0123456789abcdef" for character in source_sha256)
    ):
        raise ArtifactValidationError("internal method configuration hash is invalid")
    source_path = data["source_path"]
    if (
        not isinstance(source_path, str)
        or not source_path
        or source_path != source_path.strip()
        or "\\" in source_path
        or ":" in source_path
        or Path(source_path).is_absolute()
        or ".." in Path(source_path).parts
    ):
        raise ArtifactValidationError("internal method configuration path is invalid")
    return FrozenMethodConfig(
        method,
        dataset,
        _validate_model(method, data["model"]),
        _validate_optimizer(data["optimizer"]),
        _validate_training(data["training"]),
        source_path,
        source_sha256,
    )


def _tensor_inputs(values: Mapping[str, np.ndarray], device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
    features = values["features"]
    edge_index = values["edge_index"]
    if features.dtype != np.float32 or features.ndim != 2 or not np.all(np.isfinite(features)):
        raise ArtifactValidationError("snapshot features must be finite float32 [N,F]")
    if edge_index.dtype != np.int64 or edge_index.shape[0] != 2:
        raise ArtifactValidationError("snapshot edge_index must be int64 [2,E]")
    return (
        torch.from_numpy(np.ascontiguousarray(features)).to(device=device),
        torch.from_numpy(np.ascontiguousarray(edge_index)).to(device=device),
    )


def run_training_stage(
    *,
    selection_path: str | Path,
    config_path: str | Path,
    checkpoint_path: str | Path,
    record_path: str | Path,
    seed: int,
    device_name: str,
    expected_selection_sha256: str | None = None,
    expected_config_sha256: str | None = None,
) -> None:
    """Select a checkpoint using train/validation data only."""

    if expected_selection_sha256 is not None and sha256_file(selection_path) != expected_selection_sha256:
        raise ArtifactValidationError("selection snapshot differs from frozen bytes")
    if expected_config_sha256 is not None and sha256_file(config_path) != expected_config_sha256:
        raise ArtifactValidationError("method-config snapshot differs from frozen bytes")
    config = _load_config_snapshot(Path(config_path))
    members = {
        "dataset", "edge_index", "features", "format", "split_id", "train_indices",
        "train_labels", "validation_indices", "validation_labels",
    }
    data = _safe_npz(Path(selection_path), members, label="selection snapshot")
    if str(data["format"].item()) != SELECTION_SNAPSHOT_FORMAT:
        raise ArtifactValidationError("selection snapshot format is invalid")
    if str(data["dataset"].item()) != config.dataset:
        raise ArtifactValidationError("selection snapshot dataset differs from configuration")
    device = torch.device(device_name)
    _seed_everything(seed)
    if device.type == "cuda":
        if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
            raise ArtifactValidationError("training stage requires exactly one visible CUDA device")
        torch.cuda.reset_peak_memory_stats(device)
    x, edge_index = _tensor_inputs(data, device)
    train_index = torch.from_numpy(np.ascontiguousarray(data["train_indices"])).to(device=device)
    validation_index = torch.from_numpy(np.ascontiguousarray(data["validation_indices"])).to(device=device)
    train_labels = torch.from_numpy(np.ascontiguousarray(data["train_labels"])).to(device=device)
    validation_labels = torch.from_numpy(np.ascontiguousarray(data["validation_labels"])).to(device=device)
    if train_index.dtype != torch.long or validation_index.dtype != torch.long:
        raise ArtifactValidationError("selection indices must be int64")
    if train_labels.dtype != torch.long or train_labels.shape != train_index.shape:
        raise ArtifactValidationError("training labels must align with training indices")
    if validation_labels.dtype != torch.long or validation_labels.shape != validation_index.shape:
        raise ArtifactValidationError("validation labels must align with validation indices")
    if train_index.numel() == 0 or validation_index.numel() == 0:
        raise ArtifactValidationError("training and validation partitions must be nonempty")
    if torch.any(train_index < 0) or torch.any(validation_index < 0) or torch.any(train_index >= x.shape[0]) or torch.any(validation_index >= x.shape[0]):
        raise ArtifactValidationError("selection indices are outside the node range")
    if torch.isin(train_index, validation_index).any():
        raise ArtifactValidationError("training and validation indices overlap")
    if torch.unique(train_index).numel() != train_index.numel() or torch.unique(validation_index).numel() != validation_index.numel():
        raise ArtifactValidationError("selection indices must be unique within each partition")

    model = _build_model(config).to(device=device, dtype=torch.float32)
    parameter_names_before = tuple(name for name, _ in model.named_parameters())
    optimizer = _optimizer(model, config.optimizer)
    if tuple(name for name, _ in model.named_parameters()) != parameter_names_before:
        raise ArtifactValidationError("model created parameters after optimizer construction")
    max_epochs = int(config.training["max_epochs"])
    patience = int(config.training["patience"])
    min_delta = float(config.training["min_delta"])
    clip = config.training["gradient_clip_norm"]
    best_metric = -math.inf
    best_epoch = 0
    best_state: dict[str, torch.Tensor] | None = None
    epochs_without_improvement = 0
    history: list[dict[str, Any]] = []
    started = time.perf_counter()
    for epoch in range(1, max_epochs + 1):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        logits = _forward_logits(model, x, edge_index)
        loss = official_training_loss(config.dataset, logits[train_index], train_labels)
        if not torch.isfinite(loss):
            raise ArtifactValidationError("training loss became nonfinite")
        loss.backward()
        if clip is not None:
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), float(clip), error_if_nonfinite=True)
            gradient_norm = float(norm.detach().cpu())
        else:
            squares = []
            for parameter in model.parameters():
                if parameter.grad is not None:
                    if not torch.isfinite(parameter.grad).all():
                        raise ArtifactValidationError("training gradient became nonfinite")
                    squares.append(parameter.grad.detach().square().sum())
            gradient_norm = float(torch.sqrt(sum(squares)).cpu()) if squares else 0.0
        optimizer.step()
        model.eval()
        with torch.no_grad():
            validation_logits = _forward_logits(model, x, edge_index)[validation_index]
            metric_name, metric_value = _official_metric(
                config.dataset, validation_logits, validation_labels
            )
        history.append(
            {
                "epoch": epoch,
                "gradient_norm": gradient_norm,
                "train_loss": float(loss.detach().cpu()),
                "validation_metric": {"name": metric_name, "value": metric_value},
            }
        )
        previous_best = best_metric
        if best_state is None or metric_value > best_metric:
            best_metric = metric_value
            best_epoch = epoch
            best_state = {
                name: value.detach().to(device="cpu").clone()
                for name, value in model.state_dict().items()
            }
        if previous_best == -math.inf or metric_value > previous_best + min_delta:
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= patience:
                break
    if best_state is None:
        raise ArtifactValidationError("validation-only selection produced no checkpoint")
    model.load_state_dict(best_state, strict=True)
    elapsed = time.perf_counter() - started
    peak_memory = int(torch.cuda.max_memory_allocated(device)) if device.type == "cuda" else 0
    checkpoint = {
        "config_sha256": config.source_sha256,
        "dataset": config.dataset,
        "method": config.method,
        "schema_version": CHECKPOINT_SCHEMA,
        "seed": seed,
        "selected_epoch": best_epoch,
        "state_dict": best_state,
    }
    checkpoint_target = Path(checkpoint_path)
    if checkpoint_target.exists() or checkpoint_target.is_symlink():
        raise FileExistsError(checkpoint_target)
    torch.save(checkpoint, checkpoint_target)
    record = {
        "checkpoint_sha256": sha256_file(checkpoint_target),
        "history": history,
        "peak_memory_bytes": peak_memory,
        "resources": _resource_count(model, config),
        "roots": _roots(model),
        "runtime_seconds": elapsed,
        "schema_version": TRAINING_RECORD_SCHEMA,
        "selected_epoch": best_epoch,
        "selection": {
            "checkpoint_tie_breaker": "earliest",
            "metric": resolve_dataset(config.dataset).selection_metric,
            "source": "validation_only",
            "test_used_for_selection": False,
        },
        "validation_metric": {"name": resolve_dataset(config.dataset).selection_metric, "value": best_metric},
    }
    Path(record_path).write_bytes(canonical_json_bytes(record))


def run_evaluation_stage(
    *,
    evaluation_path: str | Path,
    config_path: str | Path,
    checkpoint_path: str | Path,
    prediction_path: str | Path,
    record_path: str | Path,
    expected_checkpoint_sha256: str,
    run_id: str,
    device_name: str,
    expected_evaluation_sha256: str | None = None,
    expected_config_sha256: str | None = None,
) -> None:
    """Evaluate one immutable selected checkpoint; never perform selection."""

    if (
        not isinstance(run_id, str)
        or len(run_id) != 64
        or any(character not in "0123456789abcdef" for character in run_id)
    ):
        raise ArtifactValidationError("evaluation run ID must be 64 lowercase hex characters")
    if expected_evaluation_sha256 is not None and sha256_file(evaluation_path) != expected_evaluation_sha256:
        raise ArtifactValidationError("evaluation snapshot differs from frozen bytes")
    if expected_config_sha256 is not None and sha256_file(config_path) != expected_config_sha256:
        raise ArtifactValidationError("method-config snapshot differs from frozen bytes")
    config = _load_config_snapshot(Path(config_path))
    if sha256_file(checkpoint_path) != expected_checkpoint_sha256:
        raise ArtifactValidationError("evaluation checkpoint differs from frozen bytes")
    members = {"dataset", "edge_index", "features", "format", "split_id", "test_indices", "test_labels"}
    data = _safe_npz(Path(evaluation_path), members, label="evaluation snapshot")
    if str(data["format"].item()) != EVALUATION_SNAPSHOT_FORMAT:
        raise ArtifactValidationError("evaluation snapshot format is invalid")
    if str(data["dataset"].item()) != config.dataset:
        raise ArtifactValidationError("evaluation snapshot dataset differs from configuration")
    split_value = data["split_id"]
    if split_value.ndim != 0 or split_value.dtype.kind not in {"i", "u"}:
        raise ArtifactValidationError("evaluation split must be one integer scalar")
    split = split_value.item()
    if type(split) is not int or split not in OFFICIAL_SPLITS:
        raise ArtifactValidationError("evaluation split is outside official rows 0..9")
    device = torch.device(device_name)
    if device.type == "cuda" and (not torch.cuda.is_available() or torch.cuda.device_count() != 1):
        raise ArtifactValidationError("evaluation stage requires exactly one visible CUDA device")
    x, edge_index = _tensor_inputs(data, device)
    test_index = torch.from_numpy(np.ascontiguousarray(data["test_indices"])).to(device=device)
    test_labels = torch.from_numpy(np.ascontiguousarray(data["test_labels"])).to(device=device)
    if test_index.dtype != torch.long or test_labels.dtype != torch.long or test_labels.shape != test_index.shape:
        raise ArtifactValidationError("test indices/labels must be aligned int64 vectors")
    if (
        test_index.numel() == 0
        or torch.any(test_index < 0)
        or torch.any(test_index >= x.shape[0])
        or torch.unique(test_index).numel() != test_index.numel()
    ):
        raise ArtifactValidationError("test indices must be nonempty, unique, and in range")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    if (
        not isinstance(checkpoint, dict)
        or checkpoint.get("schema_version") != CHECKPOINT_SCHEMA
        or checkpoint.get("method") != config.method
        or checkpoint.get("dataset") != config.dataset
        or checkpoint.get("config_sha256") != config.source_sha256
    ):
        raise ArtifactValidationError("checkpoint identity differs from evaluation configuration")
    model = _build_model(config).to(device=device, dtype=torch.float32)
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    model.eval()
    started = time.perf_counter()
    with torch.no_grad():
        logits = _forward_logits(model, x, edge_index)[test_index]
    metric_name, metric_value = _official_metric(config.dataset, logits, test_labels)
    elapsed = time.perf_counter() - started
    values = logits.detach().to(device="cpu", dtype=torch.float32).numpy()
    if resolve_dataset(config.dataset).task_type == "binary":
        values = values.reshape(-1)
    prediction_payload = _npz_bytes(
        dataset=np.asarray(config.dataset),
        format=np.asarray(PREDICTION_FORMAT),
        indices=np.ascontiguousarray(data["test_indices"], dtype=np.int64),
        logits=np.ascontiguousarray(values, dtype=np.float32),
        run_id=np.asarray(run_id),
        split_id=np.asarray(split, dtype=np.int64),
    )
    target = Path(prediction_path)
    if target.exists() or target.is_symlink():
        raise FileExistsError(target)
    target.write_bytes(prediction_payload)
    record = {
        "checkpoint_sha256": expected_checkpoint_sha256,
        "example_count": int(test_index.numel()),
        "metric": {"name": metric_name, "value": metric_value},
        "prediction_sha256": sha256_file(target),
        "runtime_seconds": elapsed,
        "schema_version": EVALUATION_RECORD_SCHEMA,
    }
    Path(record_path).write_bytes(canonical_json_bytes(record))


def _load_planned_job(
    root: Path, run_plan_path: Path, job_index: int, run_id: str
) -> tuple[ValidatedRunPlan, RunConfigRecord, Path, Path, tuple[VerifiedBaseline, ...]]:
    confirmatory = _regular_repository_file(
        root, "configs/submission/frozen/confirmatory_plan.json", "confirmatory plan"
    )
    registry = _regular_repository_file(
        root, "results_submission/baseline_registry.json", "baseline registry"
    )
    plan = validate_run_plan(
        run_plan_path,
        confirmatory_plan_path=confirmatory,
        baseline_registry_path=registry,
        repository_root=root,
    )
    if type(job_index) is not int or job_index < 0 or job_index >= len(plan.jobs):
        raise ArtifactValidationError("worker job index is outside the validated plan")
    job = plan.jobs[job_index]
    if run_id != job.identity.run_id:
        raise ArtifactValidationError("worker run ID differs from the indexed job")
    # Re-validate the registry to retain the typed records needed for adapter
    # configuration binding without broadening the public run-plan contract.
    from gbdn.baseline_contract import validate_plan_registry_binding

    _, baseline_records = validate_plan_registry_binding(
        confirmatory, registry, repository_root=root
    )
    return plan, job, confirmatory, registry, baseline_records


def _validate_runtime_identity(root: Path, job: RunConfigRecord) -> None:
    accepted = validate_operations_acceptance(root)
    if accepted.reviewed_source_metadata != job.source:
        raise ArtifactValidationError("worker reviewed source differs from frozen job source")
    lock = root / job.environment.dependency_lock_path
    observed_environment = capture_environment_metadata(lock, repository_root=root)
    if observed_environment != job.environment:
        raise ArtifactValidationError("worker environment differs from frozen job environment")


def _config_snapshot(config: FrozenMethodConfig) -> dict[str, Any]:
    return {
        "dataset": config.dataset,
        "method": config.method,
        "model": dict(config.model),
        "optimizer": dict(config.optimizer),
        "source_path": config.source_path,
        "source_sha256": config.source_sha256,
        "training": dict(config.training),
    }


def _run_internal(arguments: list[str]) -> None:
    process = subprocess.run(arguments, check=False, capture_output=True, text=True)
    if process.returncode != 0:
        stderr = process.stderr[-16_384:]
        raise ArtifactValidationError(
            f"isolated worker stage exited with {process.returncode}: {stderr}"
        )


def execute_planned_job(
    *, repository_root: str | Path, run_plan_path: str | Path,
    authoritative_dataset_root: str | Path, job_index: int, run_id: str
) -> Path:
    """Execute exactly one validated job and atomically publish its bundle."""

    root = Path(repository_root).resolve(strict=True)
    dataset_root = Path(authoritative_dataset_root).resolve(strict=True)
    run_plan_target = Path(run_plan_path).resolve(strict=True)
    if run_plan_target.is_symlink() or not run_plan_target.is_file() or not run_plan_target.is_relative_to(root):
        raise ArtifactValidationError("worker run plan must be a regular repository file")
    plan, job, confirmatory, registry, baselines = _load_planned_job(
        root, run_plan_target, job_index, run_id
    )
    _validate_runtime_identity(root, job)
    config = load_frozen_method_config(root, job=job, baselines=baselines)
    if config.method != job.identity.model_name or config.dataset != job.identity.dataset_name:
        raise ArtifactValidationError("method configuration differs from run identity")
    if job.identity.dataset_sha256 != resolve_dataset(config.dataset).npz_sha256:
        raise ArtifactValidationError("run identity is not bound to the pinned official NPZ")
    if job.identity.precision_mode != "deterministic-fp32":
        raise ArtifactValidationError("canonical heterophily worker requires deterministic-fp32")

    with tempfile.TemporaryDirectory(prefix=f"gbdn-{run_id[:12]}-") as temporary:
        work = Path(temporary)
        selection = work / "selection.npz"
        evaluation = work / "evaluation.npz"
        config_snapshot = work / "method-config.json"
        checkpoint = work / "checkpoint.pt"
        training_record = work / "training.json"
        prediction = work / "predictions.npz"
        evaluation_record = work / "evaluation.json"
        prepare_official_snapshots(
            dataset_root,
            dataset=config.dataset,
            split=job.identity.split_id,
            selection_path=selection,
            evaluation_path=evaluation,
        )
        config_snapshot.write_bytes(canonical_json_bytes(_config_snapshot(config)))
        selection_sha256 = sha256_file(selection)
        evaluation_sha256 = sha256_file(evaluation)
        config_snapshot_sha256 = sha256_file(config_snapshot)
        input_hashes = {
            "confirmatory": sha256_file(confirmatory),
            "method_config": config.source_sha256,
            "registry": sha256_file(registry),
            "run_plan": sha256_file(run_plan_target),
            "worker_module": sha256_file(Path(__file__)),
            "worker_script": sha256_file(root / "scripts" / "run_heterophily_job.py"),
        }
        base = [sys.executable, "-m", "gbdn.heterophily_worker"]
        _run_internal(
            base
            + [
                "train",
                "--selection", str(selection),
                "--config", str(config_snapshot),
                "--checkpoint", str(checkpoint),
                "--record", str(training_record),
                "--seed", str(job.identity.seed),
                "--device", "cuda",
                "--selection-sha256", selection_sha256,
                "--config-sha256", config_snapshot_sha256,
            ]
        )
        checkpoint_bytes = checkpoint.read_bytes()
        checkpoint_sha256 = sha256_file(checkpoint)
        _run_internal(
            base
            + [
                "evaluate",
                "--evaluation", str(evaluation),
                "--config", str(config_snapshot),
                "--checkpoint", str(checkpoint),
                "--prediction", str(prediction),
                "--record", str(evaluation_record),
                "--checkpoint-sha256", checkpoint_sha256,
                "--run-id", run_id,
                "--device", "cuda",
                "--evaluation-sha256", evaluation_sha256,
                "--config-sha256", config_snapshot_sha256,
            ]
        )
        if checkpoint.read_bytes() != checkpoint_bytes:
            raise ArtifactValidationError("checkpoint changed after evaluation")
        training_bytes = training_record.read_bytes()
        evaluation_bytes = evaluation_record.read_bytes()
        prediction_bytes = prediction.read_bytes()
        training = _load_json_bytes(training_bytes, label="training record")
        evaluation_result = _load_json_bytes(evaluation_bytes, label="evaluation record")
        if training.get("schema_version") != TRAINING_RECORD_SCHEMA:
            raise ArtifactValidationError("training record schema is invalid")
        if evaluation_result.get("schema_version") != EVALUATION_RECORD_SCHEMA:
            raise ArtifactValidationError("evaluation record schema is invalid")
        if training.get("checkpoint_sha256") != checkpoint_sha256:
            raise ArtifactValidationError("training record is not bound to the selected checkpoint")
        if evaluation_result.get("checkpoint_sha256") != checkpoint_sha256:
            raise ArtifactValidationError("evaluation record is not bound to the selected checkpoint")
        if evaluation_result.get("prediction_sha256") != sha256_file(prediction):
            raise ArtifactValidationError("evaluation record is not bound to prediction bytes")
        _validate_runtime_identity(root, job)
        observed_input_hashes = {
            "confirmatory": sha256_file(confirmatory),
            "method_config": sha256_file(root / config.source_path),
            "registry": sha256_file(registry),
            "run_plan": sha256_file(run_plan_target),
            "worker_module": sha256_file(Path(__file__)),
            "worker_script": sha256_file(root / "scripts" / "run_heterophily_job.py"),
        }
        if observed_input_hashes != input_hashes:
            raise ArtifactValidationError("worker input changed during execution")

        writer = AtomicRunBundle(job, repository_root=root)
        prediction_file = writer.write_bytes("predictions.npz", prediction_bytes)
        writer.write_bytes("checkpoint.pt", checkpoint_bytes)
        writer.write_bytes("training.json", training_bytes)
        prediction_manifest = PredictionArtifactManifest.from_file_manifest(
            run_id, prediction_file, format=PREDICTION_FORMAT
        )
        frozen = json.loads(job.frozen_config_json)
        result_payload = {
            "binding": {
                "baseline_registry_sha256": sha256_file(registry),
                "confirmatory_plan_sha256": sha256_file(confirmatory),
                "dataset_sha256": job.identity.dataset_sha256,
                "method_config_path": config.source_path,
                "method_config_sha256": config.source_sha256,
                "run_plan_sha256": sha256_file(run_plan_target),
                "worker_source_sha256": sha256_file(Path(__file__)),
            },
            "checkpoint": {
                "path": "checkpoint.pt",
                "sha256": checkpoint_sha256,
            },
            "frozen_job": frozen,
            "metrics": {
                "primary": evaluation_result["metric"],
                "validation": training["validation_metric"],
            },
            "resources": training["resources"],
            "roots": training["roots"],
            "runtime_seconds": {
                "evaluation": evaluation_result["runtime_seconds"],
                "training": training["runtime_seconds"],
            },
            "schema_version": WORKER_RESULT_SCHEMA,
            "selected_epoch": training["selected_epoch"],
            "selection": training["selection"],
        }
        result = RunResultRecord.create(
            identity=job.identity,
            predictions=prediction_manifest,
            result_payload=result_payload,
            source=job.source,
            environment=job.environment,
        )
        return writer.commit(result)


def _internal_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Internal isolated heterophily stages")
    subparsers = parser.add_subparsers(dest="stage", required=True)
    train = subparsers.add_parser("train")
    train.add_argument("--selection", required=True)
    train.add_argument("--config", required=True)
    train.add_argument("--checkpoint", required=True)
    train.add_argument("--record", required=True)
    train.add_argument("--seed", required=True, type=int)
    train.add_argument("--device", required=True, choices=("cpu", "cuda"))
    train.add_argument("--selection-sha256")
    train.add_argument("--config-sha256")
    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("--evaluation", required=True)
    evaluate.add_argument("--config", required=True)
    evaluate.add_argument("--checkpoint", required=True)
    evaluate.add_argument("--prediction", required=True)
    evaluate.add_argument("--record", required=True)
    evaluate.add_argument("--checkpoint-sha256", required=True)
    evaluate.add_argument("--run-id", required=True)
    evaluate.add_argument("--device", required=True, choices=("cpu", "cuda"))
    evaluate.add_argument("--evaluation-sha256")
    evaluate.add_argument("--config-sha256")
    return parser


def _internal_main(argv: list[str] | None = None) -> int:
    arguments = _internal_parser().parse_args(argv)
    if arguments.stage == "train":
        run_training_stage(
            selection_path=arguments.selection,
            config_path=arguments.config,
            checkpoint_path=arguments.checkpoint,
            record_path=arguments.record,
            seed=arguments.seed,
            device_name=arguments.device,
            expected_selection_sha256=arguments.selection_sha256,
            expected_config_sha256=arguments.config_sha256,
        )
    else:
        run_evaluation_stage(
            evaluation_path=arguments.evaluation,
            config_path=arguments.config,
            checkpoint_path=arguments.checkpoint,
            prediction_path=arguments.prediction,
            record_path=arguments.record,
            expected_checkpoint_sha256=arguments.checkpoint_sha256,
            run_id=arguments.run_id,
            device_name=arguments.device,
            expected_evaluation_sha256=arguments.evaluation_sha256,
            expected_config_sha256=arguments.config_sha256,
        )
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through subprocess contract
    raise SystemExit(_internal_main())


__all__ = [
    "CHECKPOINT_SCHEMA",
    "EVALUATION_RECORD_SCHEMA",
    "EVALUATION_SNAPSHOT_FORMAT",
    "FrozenMethodConfig",
    "METHOD_CONFIG_SCHEMA",
    "SELECTION_SNAPSHOT_FORMAT",
    "TRAINING_RECORD_SCHEMA",
    "WORKER_RESULT_SCHEMA",
    "execute_planned_job",
    "load_frozen_method_config",
    "prepare_official_snapshots",
    "run_evaluation_stage",
    "run_training_stage",
]
