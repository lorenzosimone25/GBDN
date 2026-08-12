"""Resumable H100 sweeps extending the preserved legacy reproduction.

Raw runs are immutable and live outside the four frozen legacy result trees.
Heterophily intentionally retains the legacy AUROC protocol while varying the
official split column.  Peptides uses its task-specific official metric.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.datasets import HeterophilousGraphDataset, LRGBDataset
from torch_geometric.loader import DataLoader
from torch_geometric.nn import ChebConv, GATConv, GINEConv, global_mean_pool
from torch_geometric.transforms import NormalizeFeatures

from legacy_reproduction import (
    HETERO_DATASETS,
    HETERO_MODELS,
    MODEL_FACTORIES,
    RelaxedGBDN,
    _optimizer,
    compute_multiclass_auroc,
    environment_manifest,
    seed_everything,
    verify_h100,
)


PEPTIDE_DATASETS = ("Peptides-func", "Peptides-struct")
EXTENDED_LRGB_MODELS = ("GCN", "GINE", "GAT", "ChebNet_K10", "GBDN+")
DEFAULT_SPLITS = (0, 1, 2)
DEFAULT_SEED = 25
ATOM_FEATURE_CARDINALITIES = (119, 4, 12, 12, 10, 6, 6, 2, 2)
BOND_FEATURE_CARDINALITIES = (5, 6, 2)
PEPTIDE_CONFIG = {
    "num_graph_layers": 2,
    "hidden_dim": 256,
    "dropout": 0.5,
    "batch_size": 128,
    "epochs": 100,
    "lr": 0.001,
    "seed": DEFAULT_SEED,
}
SCHEMA_RAW = "gbdn-extended-legacy-raw-v1"
SCHEMA_SUMMARY = "gbdn-extended-legacy-summary-v1"


def heterophily_raw_path(root: Path, dataset: str, model: str, split: int, seed: int) -> Path:
    return Path(root) / dataset / model / f"split-{split:02d}_seed-{seed}.json"


def heterophily_summary_path(root: Path, dataset: str, model: str) -> Path:
    return Path(root) / dataset / f"{model}.json"


def peptide_raw_path(root: Path, dataset: str, model: str, seed: int) -> Path:
    return Path(root) / dataset / model / f"seed-{seed}.json"


def peptide_summary_path(root: Path, dataset: str, model: str) -> Path:
    return Path(root) / dataset / f"{model}.json"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str | None:
    result = subprocess.run(
        ["git", "-C", str(Path(__file__).resolve().parents[1]), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _provenance(config: dict[str, Any], gpu: dict[str, Any]) -> dict[str, Any]:
    repository = Path(__file__).resolve().parents[1]
    source_files = (
        Path(__file__),
        Path(__file__).with_name("legacy_reproduction.py"),
        repository / "scripts" / "reproduce_legacy.py",
        repository / "notebooks" / "reproduce_legacy.ipynb",
    )
    source = {str(path.relative_to(path.parents[1])).replace("\\", "/"): _sha256_file(path) for path in source_files}
    env = environment_manifest(gpu)
    identity = _sha256_bytes(_canonical_bytes({"config": config, "source": source, "environment": env}))
    return {
        "identity": identity,
        "git_commit": _git_commit(),
        "source_sha256": source,
        "environment": env,
        "host": platform.node(),
    }


def _write_immutable_json(path: Path, payload: dict[str, Any], rerun: bool = False) -> bool:
    """Write atomically; return False when an identical completed run resumes."""
    path = Path(path)
    payload = dict(payload)
    payload.pop("artifact_sha256", None)
    payload["artifact_sha256"] = _sha256_bytes(_canonical_bytes(payload))
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        same = existing.get("provenance", {}).get("identity") == payload.get("provenance", {}).get("identity")
        if same and not rerun:
            if existing.get("artifact_sha256") != _sha256_bytes(_canonical_bytes({key: value for key, value in existing.items() if key != "artifact_sha256"})):
                raise ValueError(f"completed artifact failed its content hash: {path}")
            return False
        if not rerun:
            raise FileExistsError(f"refusing to overwrite conflicting artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    data = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False).encode("utf-8")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if rerun:
            os.replace(temporary, path)
        else:
            try:
                os.link(temporary, path)
            except FileExistsError:
                raise FileExistsError(f"concurrent writer completed first: {path}")
            finally:
                temporary.unlink(missing_ok=True)
    finally:
        temporary.unlink(missing_ok=True)
    return True


def _selected_masks(data: Any, split: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    masks = []
    for name in ("train_mask", "val_mask", "test_mask"):
        value = getattr(data, name)
        if value.ndim > 1:
            if split < 0 or split >= value.shape[1]:
                raise ValueError(f"official split {split} is outside {name} columns")
            value = value[:, split]
        elif split != 0:
            raise ValueError(f"dataset exposes only one {name} column")
        masks.append(value.bool())
    return tuple(masks)  # type: ignore[return-value]


def run_heterophily_split(
    dataset_name: str,
    model_name: str,
    output_root: Path,
    data_root: Path,
    *,
    split: int,
    seed: int = DEFAULT_SEED,
    epochs: int = 1000,
    rerun: bool = False,
) -> Path:
    if dataset_name not in HETERO_DATASETS or model_name not in HETERO_MODELS:
        raise ValueError(f"unsupported pair: {dataset_name}/{model_name}")
    path = heterophily_raw_path(output_root, dataset_name, model_name, split, seed)
    config = {
        "dataset": dataset_name,
        "model": model_name,
        "split": int(split),
        "seed": int(seed),
        "hidden_dim": 64,
        "lr": 0.01,
        "epochs": int(epochs),
        "K": 10 if model_name == "ChebNetII" else (5 if model_name in {"GBDN+", "ChebNet"} else None),
        "protocol": "legacy_auroc_validation_selection",
    }
    gpu = verify_h100()
    provenance = _provenance(config, gpu)
    if path.exists() and not rerun:
        old = json.loads(path.read_text(encoding="utf-8"))
        if old.get("provenance", {}).get("identity") == provenance["identity"]:
            validate_raw_artifact(path)
            return path
        raise FileExistsError(f"conflicting completed run: {path}")
    seed_everything(seed)
    dataset = HeterophilousGraphDataset(
        root=str(Path(data_root) / dataset_name), name=dataset_name, transform=NormalizeFeatures()
    )
    data = dataset[0].to("cuda:0")
    train_mask, val_mask, test_mask = _selected_masks(data, split)
    model = MODEL_FACTORIES[model_name](dataset.num_features, 64, dataset.num_classes).to("cuda:0")
    optimizer = _optimizer(model_name, model)
    best_val = -math.inf
    selected: dict[str, Any] | None = None
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        raw = model(data.x, data.edge_index)
        logits = raw[0] if isinstance(raw, tuple) else raw
        F.cross_entropy(logits[train_mask], data.y[train_mask]).backward()
        optimizer.step()
        model.eval()
        with torch.no_grad():
            raw = model(data.x, data.edge_index)
            logits = raw[0] if isinstance(raw, tuple) else raw
            probabilities = F.softmax(logits, dim=1)
            val_probs, val_labels = probabilities[val_mask], data.y[val_mask]
            val_score = compute_multiclass_auroc(val_labels, val_probs, dataset.num_classes)
            if val_score > best_val:
                best_val = val_score
                test_probs, test_labels = probabilities[test_mask], data.y[test_mask]
                selected = {
                    "selected_epoch": epoch + 1,
                    "val_predictions": val_probs.cpu().tolist(),
                    "val_labels": val_labels.cpu().tolist(),
                    "test_predictions": test_probs.cpu().tolist(),
                    "test_labels": test_labels.cpu().tolist(),
                    "metrics": {
                        "val_auroc": float(val_score),
                        "test_auroc": float(compute_multiclass_auroc(test_labels, test_probs, dataset.num_classes)),
                        "test_acc": float((test_probs.argmax(1) == test_labels).float().mean().item()),
                    },
                }
    if selected is None:
        raise RuntimeError("no heterophily checkpoint was selected")
    payload = {
        "schema_version": SCHEMA_RAW,
        "artifact_type": "raw_run",
        "task": "heterophily_node_classification",
        "dataset": dataset_name,
        "model": model_name,
        "split": int(split),
        "seed": int(seed),
        "config": config,
        **selected,
        "runtime_seconds": time.perf_counter() - started,
        "peak_cuda_memory_bytes": int(torch.cuda.max_memory_allocated()),
        "provenance": provenance,
    }
    _write_immutable_json(path, payload, rerun=rerun)
    return path


class CategoricalFeatureEncoder(nn.Module):
    def __init__(self, cardinalities: Iterable[int], hidden_dim: int):
        super().__init__()
        self.cardinalities = tuple(int(v) for v in cardinalities)
        self.embeddings = nn.ModuleList([nn.Embedding(size, hidden_dim) for size in self.cardinalities])
        self.reset_parameters()

    def reset_parameters(self) -> None:
        for embedding in self.embeddings:
            nn.init.xavier_uniform_(embedding.weight)

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        if features.ndim != 2 or features.shape[1] != len(self.embeddings):
            raise ValueError(f"expected categorical features [N,{len(self.embeddings)}]")
        features = features.long()
        outputs = []
        for column, (embedding, cardinality) in enumerate(zip(self.embeddings, self.cardinalities)):
            values = features[:, column]
            if values.numel() and (int(values.min()) < 0 or int(values.max()) >= cardinality):
                raise ValueError(f"categorical column {column} is out of range")
            outputs.append(embedding(values))
        return torch.stack(outputs, dim=0).sum(dim=0)


class BondGCNLayer(nn.Module):
    def __init__(self, hidden_dim: int):
        super().__init__()
        self.neighbor = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.root = nn.Linear(hidden_dim, hidden_dim)
        self.edge = nn.Linear(hidden_dim, hidden_dim, bias=False)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor, edge_attr: torch.Tensor) -> torch.Tensor:
        source, target = edge_index
        degree = x.new_zeros(x.shape[0]).index_add_(0, target, x.new_ones(target.numel())).clamp_min_(1)
        norm = degree[source].rsqrt() * degree[target].rsqrt()
        messages = (self.neighbor(x[source]) + self.edge(edge_attr)) * norm[:, None]
        return self.root(x) + x.new_zeros(x.shape).index_add_(0, target, messages)


class PeptideGraphModel(nn.Module):
    """Two-layer, bond-aware graph model with official categorical encoders."""

    def __init__(self, model_name: str, out_dim: int, hidden_dim: int = 256, dropout: float = 0.5):
        super().__init__()
        if model_name not in EXTENDED_LRGB_MODELS:
            raise ValueError(f"unsupported Peptides model: {model_name}")
        self.model_name = model_name
        self.dropout = float(dropout)
        self.atom_encoder = CategoricalFeatureEncoder(ATOM_FEATURE_CARDINALITIES, hidden_dim)
        self.bond_encoder = CategoricalFeatureEncoder(BOND_FEATURE_CARDINALITIES, hidden_dim)
        if model_name == "GCN":
            self.layers = nn.ModuleList([BondGCNLayer(hidden_dim) for _ in range(2)])
        elif model_name == "GINE":
            self.layers = nn.ModuleList([
                GINEConv(nn.Sequential(nn.Linear(hidden_dim, hidden_dim), nn.ReLU(), nn.Linear(hidden_dim, hidden_dim)))
                for _ in range(2)
            ])
        elif model_name == "GAT":
            self.layers = nn.ModuleList([
                GATConv(hidden_dim, hidden_dim // 4, heads=4, concat=True, edge_dim=hidden_dim)
                for _ in range(2)
            ])
        elif model_name == "ChebNet_K10":
            self.layers = nn.ModuleList([ChebConv(hidden_dim, hidden_dim, K=10) for _ in range(2)])
            self.edge_gates = nn.ModuleList([nn.Linear(hidden_dim, 1) for _ in range(2)])
        else:
            self.layers = nn.ModuleList([
                RelaxedGBDN(hidden_dim, hidden_dim, hidden_dim, num_layers=2, K=10, dropout=dropout)
            ])
            self.edge_gates = nn.ModuleList([nn.Linear(hidden_dim, 1)])
        self.norms = nn.ModuleList([nn.LayerNorm(hidden_dim) for _ in self.layers])
        self.output = nn.Linear(hidden_dim, out_dim)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor, edge_attr: torch.Tensor, batch: torch.Tensor) -> torch.Tensor:
        x = self.atom_encoder(x)
        edge = self.bond_encoder(edge_attr)
        for index, (layer, norm) in enumerate(zip(self.layers, self.norms)):
            if self.model_name in {"GCN", "GINE", "GAT"}:
                updated = layer(x, edge_index, edge)
            elif self.model_name == "ChebNet_K10":
                weights = F.softplus(self.edge_gates[index](edge).squeeze(-1))
                updated = layer(x, edge_index, edge_weight=weights, lambda_max=2.0)
            else:
                layer.cheb_computer.L_cache = None
                weights = F.softplus(self.edge_gates[index](edge).squeeze(-1))
                # RelaxedGBDN itself is topology-aware; incident bond messages make
                # its inputs bond-aware while a weighted basis is used below when supported.
                incident = x.new_zeros(x.shape).index_add_(0, edge_index[1], edge * weights[:, None])
                counts = x.new_zeros(x.shape[0]).index_add_(0, edge_index[1], x.new_ones(edge_index.shape[1])).clamp_min_(1)
                updated, _ = layer(x + incident / counts[:, None], edge_index, weights)
            x = norm(x + F.dropout(F.relu(updated), p=self.dropout, training=self.training))
        return self.output(global_mean_pool(x, batch))


def peptide_task(dataset: str) -> dict[str, Any]:
    if dataset == "Peptides-func":
        return {"out_dim": 10, "metric": "ap", "direction": "maximize", "loss": "bce_with_logits"}
    if dataset == "Peptides-struct":
        return {"out_dim": 11, "metric": "mae", "direction": "minimize", "loss": "l1"}
    raise ValueError(f"unsupported Peptides dataset: {dataset}")


def macro_average_precision(targets: np.ndarray, predictions: np.ndarray) -> float:
    from sklearn.metrics import average_precision_score

    return float(average_precision_score(np.asarray(targets), np.asarray(predictions), average="macro"))


def mean_absolute_error(targets: np.ndarray, predictions: np.ndarray) -> float:
    return float(np.mean(np.abs(np.asarray(targets, dtype=float) - np.asarray(predictions, dtype=float))))


def checkpoint_improved(candidate: float, incumbent: float | None, direction: str) -> bool:
    if not math.isfinite(candidate):
        return False
    return incumbent is None or (candidate > incumbent if direction == "maximize" else candidate < incumbent)


def _peptide_evaluate(model: nn.Module, loader: DataLoader, task: dict[str, Any]) -> tuple[float, list, list]:
    model.eval()
    targets, predictions = [], []
    with torch.no_grad():
        for data in loader:
            data = data.to("cuda:0")
            output = model(data.x, data.edge_index, data.edge_attr, data.batch)
            targets.append(data.y.float().cpu())
            predictions.append((torch.sigmoid(output) if task["metric"] == "ap" else output).cpu())
    target = torch.cat(targets).numpy()
    prediction = torch.cat(predictions).numpy()
    metric = macro_average_precision(target, prediction) if task["metric"] == "ap" else mean_absolute_error(target, prediction)
    return metric, prediction.tolist(), target.tolist()


def run_peptide(
    dataset_name: str,
    model_name: str,
    output_root: Path,
    data_root: Path,
    *,
    seed: int = DEFAULT_SEED,
    epochs: int = 100,
    batch_size: int = 128,
    rerun: bool = False,
    max_train_batches: int | None = None,
) -> Path:
    task = peptide_task(dataset_name)
    if model_name not in EXTENDED_LRGB_MODELS:
        raise ValueError(f"unsupported Peptides model: {model_name}")
    path = peptide_raw_path(output_root, dataset_name, model_name, seed)
    config = {
        "dataset": dataset_name,
        "model": model_name,
        **PEPTIDE_CONFIG,
        "epochs": int(epochs),
        "batch_size": int(batch_size),
        "seed": int(seed),
        "task": task,
        "max_train_batches": max_train_batches,
        "pooling": "global_mean",
        "atom_cardinalities": ATOM_FEATURE_CARDINALITIES,
        "bond_cardinalities": BOND_FEATURE_CARDINALITIES,
    }
    gpu = verify_h100()
    provenance = _provenance(config, gpu)
    if path.exists() and not rerun:
        old = json.loads(path.read_text(encoding="utf-8"))
        if old.get("provenance", {}).get("identity") == provenance["identity"]:
            validate_raw_artifact(path)
            return path
        raise FileExistsError(f"conflicting completed run: {path}")
    seed_everything(seed)
    datasets = {
        split: LRGBDataset(root=str(Path(data_root) / dataset_name), name=dataset_name, split=split)
        for split in ("train", "val", "test")
    }
    loaders = {
        split: DataLoader(
            value,
            batch_size=batch_size if split == "train" else batch_size * 2,
            shuffle=split == "train",
            num_workers=2,
            pin_memory=True,
        )
        for split, value in datasets.items()
    }
    model = PeptideGraphModel(model_name, task["out_dim"], PEPTIDE_CONFIG["hidden_dim"], PEPTIDE_CONFIG["dropout"]).to("cuda:0")
    optimizer = torch.optim.Adam(model.parameters(), lr=PEPTIDE_CONFIG["lr"], weight_decay=1e-5)
    best: float | None = None
    selected: dict[str, Any] | None = None
    best_state: dict[str, torch.Tensor] | None = None
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    for epoch in range(epochs):
        model.train()
        for batch_index, data in enumerate(loaders["train"]):
            if max_train_batches is not None and batch_index >= max_train_batches:
                break
            data = data.to("cuda:0")
            optimizer.zero_grad(set_to_none=True)
            output = model(data.x, data.edge_index, data.edge_attr, data.batch)
            loss = F.binary_cross_entropy_with_logits(output, data.y.float()) if task["loss"] == "bce_with_logits" else F.l1_loss(output, data.y.float())
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
        val_metric, val_predictions, val_targets = _peptide_evaluate(model, loaders["val"], task)
        if checkpoint_improved(val_metric, best, task["direction"]):
            best = val_metric
            selected = {
                "selected_epoch": epoch + 1,
                "val_predictions": val_predictions,
                "val_targets": val_targets,
                "metrics": {f"val_{task['metric']}": val_metric},
            }
            best_state = {name: value.detach().cpu().clone() for name, value in model.state_dict().items()}
    if selected is None or best_state is None:
        raise RuntimeError("no Peptides checkpoint was selected")
    model.load_state_dict(best_state)
    test_metric, test_predictions, test_targets = _peptide_evaluate(model, loaders["test"], task)
    selected["test_predictions"] = test_predictions
    selected["test_targets"] = test_targets
    selected["metrics"][f"test_{task['metric']}"] = test_metric
    payload = {
        "schema_version": SCHEMA_RAW,
        "artifact_type": "raw_run",
        "task": f"peptides_{task['metric']}",
        "dataset": dataset_name,
        "model": model_name,
        "official_partition": True,
        "seed": int(seed),
        "config": config,
        **selected,
        "runtime_seconds": time.perf_counter() - started,
        "peak_cuda_memory_bytes": int(torch.cuda.max_memory_allocated()),
        "provenance": provenance,
    }
    _write_immutable_json(path, payload, rerun=rerun)
    return path


def recompute_raw_metrics(record: dict[str, Any]) -> dict[str, float]:
    task = record.get("task")
    if task == "heterophily_node_classification":
        val_predictions = torch.tensor(record["val_predictions"], dtype=torch.float64)
        val_labels = torch.tensor(record["val_labels"], dtype=torch.long)
        test_predictions = torch.tensor(record["test_predictions"], dtype=torch.float64)
        test_labels = torch.tensor(record["test_labels"], dtype=torch.long)
        classes = test_predictions.shape[1]
        for name, probabilities, labels in (
            ("val", val_predictions, val_labels), ("test", test_predictions, test_labels)
        ):
            if probabilities.ndim != 2 or labels.ndim != 1 or probabilities.shape[0] != labels.shape[0]:
                raise ValueError(f"invalid heterophily {name} prediction/label shapes")
            if not torch.isfinite(probabilities).all() or not torch.allclose(
                probabilities.sum(dim=1), torch.ones(probabilities.shape[0], dtype=probabilities.dtype), atol=1e-5
            ):
                raise ValueError(f"invalid heterophily {name} probabilities")
        return {
            "val_auroc": float(compute_multiclass_auroc(val_labels, val_predictions, classes)),
            "test_auroc": float(compute_multiclass_auroc(test_labels, test_predictions, classes)),
            "test_acc": float((test_predictions.argmax(1) == test_labels).double().mean().item()),
        }
    if task == "peptides_ap":
        if np.asarray(record["val_targets"]).shape != np.asarray(record["val_predictions"]).shape or np.asarray(record["test_targets"]).shape != np.asarray(record["test_predictions"]).shape:
            raise ValueError("Peptides-func target/prediction shape mismatch")
        return {
            "val_ap": macro_average_precision(np.asarray(record["val_targets"]), np.asarray(record["val_predictions"])),
            "test_ap": macro_average_precision(np.asarray(record["test_targets"]), np.asarray(record["test_predictions"])),
        }
    if task == "peptides_mae":
        if np.asarray(record["val_targets"]).shape != np.asarray(record["val_predictions"]).shape or np.asarray(record["test_targets"]).shape != np.asarray(record["test_predictions"]).shape:
            raise ValueError("Peptides-struct target/prediction shape mismatch")
        return {
            "val_mae": mean_absolute_error(np.asarray(record["val_targets"]), np.asarray(record["val_predictions"])),
            "test_mae": mean_absolute_error(np.asarray(record["test_targets"]), np.asarray(record["test_predictions"])),
        }
    raise ValueError(f"unknown raw task: {task!r}")


def validate_raw_artifact(path: Path, tolerance: float = 1e-8) -> dict[str, Any]:
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record.get("schema_version") != SCHEMA_RAW or record.get("artifact_type") != "raw_run":
        raise ValueError(f"invalid raw artifact schema: {path}")
    stored_hash = record.get("artifact_sha256")
    computed_hash = _sha256_bytes(_canonical_bytes({key: value for key, value in record.items() if key != "artifact_sha256"}))
    if stored_hash != computed_hash:
        raise ValueError(f"artifact content hash mismatch: {path}")
    recomputed = recompute_raw_metrics(record)
    if set(recomputed) != set(record.get("metrics", {})):
        raise ValueError(f"metric key mismatch: {path}")
    for name, value in recomputed.items():
        stored = float(record["metrics"][name])
        if not math.isfinite(stored) or abs(stored - value) > tolerance:
            raise ValueError(f"metric mismatch in {path}: {name} stored={stored} recomputed={value}")
    if int(record.get("selected_epoch", 0)) < 1:
        raise ValueError(f"invalid selected epoch: {path}")
    provenance = record.get("provenance", {})
    if not provenance.get("identity"):
        raise ValueError(f"missing provenance identity: {path}")
    if record.get("config") is not None:
        required = {"git_commit", "source_sha256", "environment", "host"}
        if not required.issubset(provenance):
            raise ValueError(f"incomplete source/environment provenance: {path}")
        expected_identity = _sha256_bytes(_canonical_bytes({
            "config": record["config"],
            "source": provenance["source_sha256"],
            "environment": provenance["environment"],
        }))
        if provenance["identity"] != expected_identity:
            raise ValueError(f"provenance identity mismatch: {path}")
    return record


def _aggregate(paths: list[Path], summary_path: Path, *, rerun: bool = False) -> Path:
    records = [validate_raw_artifact(path) for path in paths]
    if not records:
        raise ValueError("cannot aggregate zero runs")
    metric_names = tuple(records[0]["metrics"])
    if any(tuple(record["metrics"]) != metric_names for record in records):
        raise ValueError("raw metric sets differ")
    metrics = {}
    for name in metric_names:
        values = np.asarray([record["metrics"][name] for record in records], dtype=float)
        metrics[name] = {
            "mean": float(values.mean()),
            "std": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
        }
    root = summary_path.parents[1]
    raw_refs = [
        {"path": path.relative_to(root).as_posix(), "sha256": _sha256_file(path), "identity": record["provenance"]["identity"]}
        for path, record in zip(paths, records)
    ]
    payload = {
        "schema_version": SCHEMA_SUMMARY,
        "artifact_type": "aggregate_summary",
        "dataset": records[0]["dataset"],
        "model": records[0]["model"],
        "run_count": len(records),
        "metrics": metrics,
        "raw_runs": raw_refs,
        "splits": [record["split"] for record in records if "split" in record],
        "seeds": sorted({record["seed"] for record in records}),
    }
    for name, aggregate in metrics.items():
        payload[name] = aggregate["mean"]
        payload[f"{name}_std"] = aggregate["std"]
    payload["provenance"] = {"identity": _sha256_bytes(_canonical_bytes(payload))}
    _write_immutable_json(summary_path, payload, rerun=rerun)
    return summary_path


def aggregate_heterophily(output_root: Path, splits: Iterable[int] = DEFAULT_SPLITS, seed: int = DEFAULT_SEED, *, datasets: Iterable[str] = HETERO_DATASETS, models: Iterable[str] = HETERO_MODELS, rerun: bool = False) -> list[Path]:
    split_list = tuple(int(value) for value in splits)
    summaries = []
    for dataset in datasets:
        for model in models:
            paths = [heterophily_raw_path(output_root, dataset, model, split, seed) for split in split_list]
            missing = [str(path) for path in paths if not path.is_file()]
            if missing:
                raise FileNotFoundError(f"missing raw heterophily runs: {missing}")
            summaries.append(_aggregate(paths, heterophily_summary_path(output_root, dataset, model), rerun=rerun))
    return summaries


def aggregate_peptides(output_root: Path, seed: int = DEFAULT_SEED, *, datasets: Iterable[str] = PEPTIDE_DATASETS, models: Iterable[str] = EXTENDED_LRGB_MODELS, rerun: bool = False) -> list[Path]:
    summaries = []
    for dataset in datasets:
        for model in models:
            path = peptide_raw_path(output_root, dataset, model, seed)
            if not path.is_file():
                raise FileNotFoundError(f"missing raw Peptides run: {path}")
            summaries.append(_aggregate([path], peptide_summary_path(output_root, dataset, model), rerun=rerun))
    return summaries


def expected_counts(splits: Iterable[int] = DEFAULT_SPLITS) -> dict[str, int]:
    count = len(tuple(splits))
    return {
        "heterophily_raw": len(HETERO_DATASETS) * len(HETERO_MODELS) * count,
        "peptides_raw": len(PEPTIDE_DATASETS) * len(EXTENDED_LRGB_MODELS),
        "heterophily_summaries": len(HETERO_DATASETS) * len(HETERO_MODELS),
        "peptides_summaries": len(PEPTIDE_DATASETS) * len(EXTENDED_LRGB_MODELS),
    }


def prepare_extended_datasets(
    data_root: Path,
    heterophily_datasets: Iterable[str] = HETERO_DATASETS,
    peptide_datasets: Iterable[str] = PEPTIDE_DATASETS,
) -> None:
    """Download/process each shared dataset once before parallel workers start."""
    for dataset in heterophily_datasets:
        if dataset not in HETERO_DATASETS:
            raise ValueError(f"unsupported heterophily dataset: {dataset}")
        HeterophilousGraphDataset(root=str(Path(data_root) / dataset), name=dataset)
    for dataset in peptide_datasets:
        peptide_task(dataset)
        for split in ("train", "val", "test"):
            LRGBDataset(root=str(Path(data_root) / dataset), name=dataset, split=split)


def verify_extended_results(hetero_root: Path, peptide_root: Path, splits: Iterable[int] = DEFAULT_SPLITS, seed: int = DEFAULT_SEED) -> list[str]:
    problems: list[str] = []
    split_list = tuple(int(value) for value in splits)
    expected: list[tuple[Path, Path]] = []
    expected_metadata: dict[Path, dict[str, Any]] = {}
    for dataset in HETERO_DATASETS:
        for model in HETERO_MODELS:
            summary = heterophily_summary_path(hetero_root, dataset, model)
            for split in split_list:
                raw = heterophily_raw_path(hetero_root, dataset, model, split, seed)
                expected.append((raw, summary))
                expected_metadata[raw.resolve()] = {"dataset": dataset, "model": model, "split": split, "seed": seed}
    for dataset in PEPTIDE_DATASETS:
        for model in EXTENDED_LRGB_MODELS:
            raw = peptide_raw_path(peptide_root, dataset, model, seed)
            expected.append((raw, peptide_summary_path(peptide_root, dataset, model)))
            expected_metadata[raw.resolve()] = {"dataset": dataset, "model": model, "seed": seed}
    for raw, _ in expected:
        if not raw.is_file():
            problems.append(f"missing raw artifact: {raw}")
            continue
        try:
            record = validate_raw_artifact(raw)
            for key, expected_value in expected_metadata[raw.resolve()].items():
                if record.get(key) != expected_value:
                    raise ValueError(f"{key} mismatch: expected {expected_value!r}, got {record.get(key)!r}")
        except Exception as error:
            problems.append(f"invalid raw artifact {raw}: {error}")
    expected_raw = {item[0].resolve() for item in expected}
    observed_raw = {
        *[path.resolve() for path in Path(hetero_root).glob("*/*/split-*_seed-*.json")],
        *[path.resolve() for path in Path(peptide_root).glob("*/*/seed-*.json")],
    }
    for unexpected in sorted(observed_raw - expected_raw):
        problems.append(f"unexpected/conflicting raw artifact: {unexpected}")
    expected_summaries = {item[1].resolve() for item in expected}
    observed_summaries = {
        *[path.resolve() for path in Path(hetero_root).glob("*/*.json")],
        *[path.resolve() for path in Path(peptide_root).glob("*/*.json")],
    }
    for unexpected in sorted(observed_summaries - expected_summaries):
        problems.append(f"unexpected/conflicting summary: {unexpected}")
    expected_by_summary: dict[Path, set[Path]] = {}
    for raw, summary in expected:
        expected_by_summary.setdefault(summary.resolve(), set()).add(raw.resolve())
    for summary in sorted({item[1] for item in expected}):
        if not summary.is_file():
            problems.append(f"missing summary: {summary}")
            continue
        try:
            record = json.loads(summary.read_text(encoding="utf-8"))
            if record.get("schema_version") != SCHEMA_SUMMARY:
                raise ValueError("wrong summary schema")
            stored_hash = record.get("artifact_sha256")
            computed_hash = _sha256_bytes(_canonical_bytes({key: value for key, value in record.items() if key != "artifact_sha256"}))
            if stored_hash != computed_hash:
                raise ValueError("summary content hash mismatch")
            root = summary.parents[1]
            refs = record.get("raw_runs", [])
            expected_run_count = len(split_list) if record["dataset"] in HETERO_DATASETS else 1
            if record.get("run_count") != expected_run_count or len(refs) != expected_run_count:
                raise ValueError("wrong summary run count")
            raw_paths = [root / ref["path"] for ref in refs]
            if {path.resolve() for path in raw_paths} != expected_by_summary[summary.resolve()]:
                raise ValueError("summary raw references do not match the expected run set")
            for path, ref in zip(raw_paths, refs):
                if not path.is_file() or _sha256_file(path) != ref["sha256"]:
                    raise ValueError(f"raw reference mismatch: {path}")
            records = [validate_raw_artifact(path) for path in raw_paths]
            for metric, aggregate in record["metrics"].items():
                values = np.asarray([item["metrics"][metric] for item in records])
                mean = float(values.mean())
                std = float(values.std(ddof=1)) if len(values) > 1 else 0.0
                if abs(mean - aggregate["mean"]) > 1e-8 or abs(std - aggregate["std"]) > 1e-8:
                    raise ValueError(f"aggregate mismatch: {metric}")
        except Exception as error:
            problems.append(f"invalid summary {summary}: {error}")
    return problems


def generate_extended_report(hetero_root: Path, peptide_root: Path, output_path: Path) -> Path:
    problems = verify_extended_results(hetero_root, peptide_root)
    if problems:
        raise RuntimeError("cannot report incomplete results:\n" + "\n".join(problems))
    def table(headers: list[str], rows: list[list[str]]) -> str:
        return "\n".join(["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|", *["| " + " | ".join(row) + " |" for row in rows]])
    hetero_rows = []
    for dataset in HETERO_DATASETS:
        for model in HETERO_MODELS:
            item = json.loads(heterophily_summary_path(hetero_root, dataset, model).read_text())
            hetero_rows.append([dataset, model, f"{item['metrics']['test_auroc']['mean']:.4f} ± {item['metrics']['test_auroc']['std']:.4f}", f"{item['metrics']['test_acc']['mean']:.4f} ± {item['metrics']['test_acc']['std']:.4f}", str(item["run_count"])])
    peptide_rows = []
    for dataset in PEPTIDE_DATASETS:
        metric = "test_ap" if dataset.endswith("func") else "test_mae"
        for model in EXTENDED_LRGB_MODELS:
            item = json.loads(peptide_summary_path(peptide_root, dataset, model).read_text())
            peptide_rows.append([dataset, model, metric, f"{item['metrics'][metric]['mean']:.4f}", str(item["run_count"])])
    counts = expected_counts()
    report = f"""# H100 Multi-Split and Extended Peptides Results\n\nRaw runs: **{counts['heterophily_raw'] + counts['peptides_raw']}**. Aggregate summaries: **{counts['heterophily_summaries'] + counts['peptides_summaries']}**.\n\n## Heterophily (official splits 0, 1, 2; seed 25)\n\n{table(['Dataset','Model','Test AUROC','Test accuracy','Runs'], hetero_rows)}\n\n## Peptides (official partition; seed 25)\n\n{table(['Dataset','Model','Metric','Test value','Runs'], peptide_rows)}\n\nAll displayed metrics were recomputed from the predictions and labels/targets in the referenced immutable raw artifacts before this report was written.\n"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(report, encoding="utf-8")
    os.replace(temporary, output_path)
    return output_path
