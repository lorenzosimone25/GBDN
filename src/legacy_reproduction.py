"""Faithful reproduction of the legacy JSON benchmark artifacts.

The implementation follows cells 23 and 28 of notebooks/BlanshkeGraphs.ipynb.
It is intentionally separate from the revised gbdn package and benchmark runner.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import subprocess
import time
import traceback
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch_geometric
from torch.nn import LayerNorm, Linear, Parameter, ReLU
from torch_geometric.datasets import HeterophilousGraphDataset, LRGBDataset
from torch_geometric.loader import DataLoader
from torch_geometric.nn import (
    AntiSymmetricConv,
    ChebConv,
    FAConv,
    GATConv,
    MixHopConv,
    SAGEConv,
    SGConv,
    global_mean_pool,
)
from torch_geometric.transforms import NormalizeFeatures
from torch_geometric.utils import get_laplacian


ROOT = Path(__file__).resolve().parents[1]
HETERO_DATASETS = (
    "Roman-empire",
    "Amazon-ratings",
    "Minesweeper",
    "Tolokers",
    "Questions",
)
HETERO_MODELS = (
    "GBDN+",
    "ChebNet",
    "ChebNetII",
    "H2GCN",
    "FAGCN",
    "MLP",
    "MixHop",
    "GAT",
    "GraphSAGE",
    "ADGN",
    "ResNet",
    "ResNet+SGC",
)
LRGB_MODELS = ("ChebNet_K10", "GBDN+")

HETERO_CONFIG = {"hidden_dim": 64, "lr": 0.01, "epochs": 1000, "seed": 25, "split_id": 0}
LRGB_CONFIG = {"batch_size": 128, "hidden_dim": 256, "lr": 0.001, "epochs": 100, "seed": 25}


def configure_faithful_math() -> None:
    """Keep the legacy computation in strict FP32 on Ampere/Hopper GPUs."""
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False


def seed_everything(seed: int = 25) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    configure_faithful_math()
    os.environ["PYTHONHASHSEED"] = str(seed)


def _nvidia_smi(*args: str) -> str:
    result = subprocess.run(
        ["nvidia-smi", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def verify_h100() -> dict[str, Any]:
    """Fail unless exactly one explicitly selected H100 is visible to PyTorch."""
    configure_faithful_math()
    listing = _nvidia_smi("-L")
    gpu_lines = [line for line in listing.splitlines() if line.strip().startswith("GPU ")]
    if not gpu_lines:
        raise RuntimeError("nvidia-smi reported no GPUs")

    visible = os.environ.get("CUDA_VISIBLE_DEVICES")
    selected = [value.strip() for value in (visible or "").split(",") if value.strip()]
    if len(selected) != 1 or not selected[0].isdigit():
        raise RuntimeError(
            "CUDA_VISIBLE_DEVICES must contain exactly one physical GPU index; "
            f"got {visible!r}. Launch through scripts/run_h100.sh."
        )
    expected = selected[0]
    if int(expected) >= len(gpu_lines):
        raise RuntimeError(f"selected physical GPU {expected} does not exist")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable after selecting the last physical GPU")
    if torch.cuda.device_count() != 1:
        raise RuntimeError(f"expected exactly one visible CUDA device, got {torch.cuda.device_count()}")

    query = _nvidia_smi(
        "--query-gpu=index,name,driver_version,memory.total",
        "--format=csv,noheader,nounits",
    )
    physical = query.splitlines()[int(expected)].split(", ")
    logical_name = torch.cuda.get_device_name(0)
    if len(physical) >= 2 and logical_name != physical[1]:
        raise RuntimeError(
            f"cuda:0 maps to {logical_name!r}, not selected physical GPU {physical[1]!r}"
        )
    if "H100" not in logical_name.upper():
        raise RuntimeError(f"selected GPU is not an H100: {logical_name!r}")
    return {
        "physical_index": int(expected),
        "logical_device": "cuda:0",
        "name": logical_name,
        "cuda_visible_devices": visible,
        "nvidia_smi_L": listing,
        "nvidia_smi_query": query,
        "torch_cuda": torch.version.cuda,
    }


def verify_last_gpu() -> dict[str, Any]:
    """Backward-compatible alias for the old public helper name."""
    return verify_h100()


def environment_manifest(gpu: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "torch_geometric": torch_geometric.__version__,
        "numpy": np.__version__,
        "precision": {
            "default_dtype": str(torch.get_default_dtype()),
            "float32_matmul_precision": torch.get_float32_matmul_precision(),
            "cuda_matmul_tf32": bool(torch.backends.cuda.matmul.allow_tf32),
            "cudnn_tf32": bool(torch.backends.cudnn.allow_tf32),
        },
    }
    if gpu is not None:
        manifest["gpu"] = gpu
    return manifest


class ResNetBlock(nn.Module):
    def __init__(self, channels: int, dropout: float):
        super().__init__()
        self.lin1 = Linear(channels, channels)
        self.lin2 = Linear(channels, channels)
        self.norm = LayerNorm(channels)
        self.act = ReLU()
        self.dropout = dropout

    def forward(self, x):
        residual = x
        x = self.lin1(F.dropout(self.act(self.norm(x)), p=self.dropout, training=self.training))
        x = self.lin2(F.dropout(self.act(self.norm(x)), p=self.dropout, training=self.training))
        return x + residual


class BaselineResNet(nn.Module):
    def __init__(self, in_c, hidden_c, out_c, num_blocks=2, dropout=0.5):
        super().__init__()
        self.lin_in = Linear(in_c, hidden_c)
        self.blocks = nn.ModuleList([ResNetBlock(hidden_c, dropout) for _ in range(num_blocks)])
        self.lin_out = Linear(hidden_c, out_c)
        self.dropout = dropout

    def forward(self, x, edge_index=None):
        x = self.lin_in(x)
        for block in self.blocks:
            x = block(x)
        return self.lin_out(F.dropout(x, p=self.dropout, training=self.training))


class BaselineResNetSGC(nn.Module):
    def __init__(self, in_c, hidden_c, out_c, K=2, num_blocks=2, dropout=0.5):
        super().__init__()
        self.sgc = SGConv(in_c, in_c, K=K, cached=True, bias=False)
        self.lin_in = Linear(in_c, hidden_c)
        self.blocks = nn.ModuleList([ResNetBlock(hidden_c, dropout) for _ in range(num_blocks)])
        self.lin_out = Linear(hidden_c, out_c)
        self.dropout = dropout

    def forward(self, x, edge_index):
        x = self.lin_in(self.sgc(x, edge_index))
        for block in self.blocks:
            x = block(x)
        return self.lin_out(F.dropout(x, p=self.dropout, training=self.training))


class BaselineGraphSAGE(nn.Module):
    def __init__(self, in_c, hidden_c, out_c, dropout=0.5, aggr="mean"):
        super().__init__()
        self.conv1 = SAGEConv(in_c, hidden_c, aggr=aggr)
        self.conv2 = SAGEConv(hidden_c, out_c, aggr=aggr)
        self.dropout = dropout

    def forward(self, x, edge_index):
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = F.relu(self.conv1(x, edge_index))
        return self.conv2(F.dropout(x, p=self.dropout, training=self.training), edge_index)


class BaselineH2GCN(nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels):
        super().__init__()
        self.dense1 = Linear(in_channels, hidden_channels)
        self.dense2 = Linear(hidden_channels, out_channels)
        self.dropout = 0.5

    def forward(self, x, edge_index):
        x = F.relu(self.dense1(F.dropout(x, self.dropout, training=self.training)))
        row, col = edge_index
        degree = torch.bincount(row, minlength=x.size(0)).float()
        degree_inv_sqrt = degree.pow(-0.5)
        degree_inv_sqrt[degree_inv_sqrt == float("inf")] = 0
        norm = degree_inv_sqrt[row] * degree_inv_sqrt[col]
        adjacency = torch.sparse_coo_tensor(edge_index, norm, (x.size(0), x.size(0)))
        x1 = torch.sparse.mm(adjacency, x)
        x2 = torch.sparse.mm(adjacency, x1)
        x_cat = torch.cat([x, x1, x2], dim=1)
        # This late creation is retained because it is how the legacy artifact was produced.
        if not hasattr(self, "final_project"):
            self.final_project = Linear(self.dense1.out_features * 3, self.dense2.out_features).to(x.device)
        return self.final_project(F.dropout(x_cat, self.dropout, training=self.training))


class BaselineMLP(nn.Module):
    def __init__(self, in_c, hidden_c, out_c):
        super().__init__()
        self.lin1 = Linear(in_c, hidden_c)
        self.lin2 = Linear(hidden_c, out_c)

    def forward(self, x, edge_index=None):
        return self.lin2(F.dropout(self.lin1(x), p=0.6, training=self.training))


class BaselineMixHop(nn.Module):
    def __init__(self, in_c, hidden_c, out_c):
        super().__init__()
        self.conv1 = MixHopConv(in_c, hidden_c, powers=[0, 1, 2])
        self.conv2 = MixHopConv(hidden_c * 3, out_c, powers=[0, 1, 2])

    def forward(self, x, edge_index):
        x = F.relu(self.conv1(x, edge_index))
        return self.conv2(F.dropout(x, p=0.5, training=self.training), edge_index)


class BaselineADGN(nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels, num_iters=2, epsilon=0.1, gamma=0.1):
        super().__init__()
        self.lin1 = Linear(in_channels, hidden_channels)
        self.conv = AntiSymmetricConv(
            in_channels=hidden_channels,
            phi=None,
            num_iters=num_iters,
            epsilon=epsilon,
            gamma=gamma,
            act="tanh",
        )
        self.lin2 = Linear(hidden_channels, out_channels)

    def forward(self, x, edge_index):
        x = F.relu(self.lin1(F.dropout(x, p=0.5, training=self.training)))
        x = self.conv(F.dropout(x, p=0.5, training=self.training), edge_index)
        return self.lin2(x)


class BaselineGAT(nn.Module):
    def __init__(self, in_c, hidden_c, out_c, heads=8):
        super().__init__()
        self.conv1 = GATConv(in_c, hidden_c, heads=heads, dropout=0.6)
        self.conv2 = GATConv(hidden_c * heads, out_c, heads=1, concat=False, dropout=0.6)

    def forward(self, x, edge_index):
        x = F.dropout(x, p=0.6, training=self.training)
        x = F.elu(self.conv1(x, edge_index))
        return self.conv2(F.dropout(x, p=0.6, training=self.training), edge_index)


class BaselineFAGCN(nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels, layers=2, dropout=0.5):
        super().__init__()
        self.layers = nn.ModuleList()
        self.dropout = dropout
        self.lin1 = Linear(in_channels, hidden_channels)
        self.lin2 = Linear(hidden_channels, out_channels)
        self.prop = FAConv(hidden_channels, dropout=dropout)
        self.num_prop_layers = layers

    def forward(self, x, edge_index):
        x = F.relu(self.lin1(F.dropout(x, p=self.dropout, training=self.training)))
        x = F.dropout(x, p=self.dropout, training=self.training)
        x0 = x
        for _ in range(self.num_prop_layers):
            x = self.prop(x, x0, edge_index)
        return self.lin2(x)


class ChebyshevBasis(nn.Module):
    def __init__(self, K):
        super().__init__()
        self.K = K
        self.L_cache = None

    def forward(self, x, edge_index, edge_weight=None, num_nodes=None):
        num_nodes = x.size(0) if num_nodes is None else num_nodes
        if self.L_cache is None or self.L_cache.size(0) != num_nodes:
            indices, values = get_laplacian(
                edge_index, edge_weight, normalization="sym", num_nodes=num_nodes
            )
            self.L_cache = torch.sparse_coo_tensor(indices, values, (num_nodes, num_nodes)).to(x.device)
        laplacian = self.L_cache.to(x.dtype) if x.dtype != self.L_cache.dtype else self.L_cache
        bases = [x, torch.sparse.mm(laplacian, x) - x]
        for _ in range(2, self.K + 1):
            term = torch.sparse.mm(laplacian, bases[-1]) - bases[-1]
            bases.append(2 * term - bases[-2])
        return torch.stack(bases, dim=0)


class RelaxedGraphBlaschkeLayer(nn.Module):
    def __init__(self, K=5, hidden_dim=64):
        super().__init__()
        self.K = K
        self.alpha_param = Parameter(torch.tensor([0.0, 0.0]))
        self.cheb_correction = Parameter(torch.randn(K + 1, 1, 1) * 0.01)

    def get_blaschke_coeffs(self, alpha_real, alpha_imag, device):
        k = torch.arange(self.K + 1, device=device).float()
        nodes = torch.cos(np.pi * (k + 0.5) / (self.K + 1))
        lambdas = nodes + 1.0
        cayley = torch.complex(lambdas, -torch.ones_like(lambdas)) / torch.complex(
            lambdas, torch.ones_like(lambdas)
        )
        alpha = torch.complex(alpha_real, alpha_imag).unsqueeze(-1)
        samples = (cayley - alpha) / (1.0 - torch.conj(alpha) * cayley)
        return torch.stack(
            [
                2.0
                / (self.K + 1)
                * torch.sum(samples * torch.cos(j * np.pi * (k + 0.5) / (self.K + 1)), dim=-1)
                for j in range(self.K + 1)
            ],
            dim=0,
        )

    def forward(self, h_complex, cheb_basis):
        alpha = torch.tanh(self.alpha_param) * 0.95
        coeffs = self.get_blaschke_coeffs(alpha[0], alpha[1], h_complex.device)
        weights = torch.conj(coeffs).view(-1, 1, 1) + self.cheb_correction
        return torch.sum(weights * cheb_basis, dim=0)


class RelaxedGBDN(nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels, num_layers=3, K=5, dropout=0.5):
        super().__init__()
        self.lifting = Linear(in_channels, hidden_channels * 2)
        self.cheb_computer = ChebyshevBasis(K)
        self.layers = nn.ModuleList(
            [RelaxedGraphBlaschkeLayer(K, hidden_channels) for _ in range(num_layers)]
        )
        self.skip_weight = Parameter(torch.tensor(0.5))
        self.readout = nn.Sequential(
            Linear(hidden_channels * 2, hidden_channels),
            nn.ReLU(),
            nn.Dropout(p=dropout),
            Linear(hidden_channels, out_channels),
        )

    def forward(self, x, edge_index):
        x_lift = self.lifting(x)
        half = x_lift.shape[1] // 2
        h = torch.complex(x_lift[:, :half], x_lift[:, half:])
        basis = self.cheb_computer(h, edge_index)
        h_accum = sum((layer(h, basis) for layer in self.layers), start=torch.zeros_like(h))
        final = (1 - self.skip_weight) * h + self.skip_weight * h_accum
        return self.readout(torch.cat([final.real, final.imag], dim=-1)), []


class BaselineChebNet(nn.Module):
    def __init__(self, in_c, hidden_c, out_c, K=3):
        super().__init__()
        self.conv1 = ChebConv(in_c, hidden_c, K=K)
        self.conv2 = ChebConv(hidden_c, out_c, K=K)

    def forward(self, x, edge_index):
        x = F.relu(self.conv1(x, edge_index))
        return self.conv2(F.dropout(x, p=0.5, training=self.training), edge_index)


class ChebNetII(nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels, K=10, dropout=0.5, heads=8):
        super().__init__()
        self.K = K
        self.dropout = dropout
        self.heads = heads
        self.lin1 = Linear(in_channels, hidden_channels)
        self.lin2 = Linear(hidden_channels, hidden_channels)
        self.temp_weight = Parameter(torch.empty(heads, K + 1))
        self.lin_final = Linear(hidden_channels * heads, out_channels)
        self.reset_parameters()

    def reset_parameters(self):
        self.lin1.reset_parameters()
        self.lin2.reset_parameters()
        self.lin_final.reset_parameters()
        nn.init.zeros_(self.temp_weight)
        with torch.no_grad():
            self.temp_weight[:, 0] = 1.0

    def get_cheb_coeffs(self):
        n = self.K + 1
        k = torch.arange(n, device=self.temp_weight.device, dtype=torch.float32).reshape(1, -1)
        j = torch.arange(n, device=self.temp_weight.device, dtype=torch.float32).reshape(1, -1)
        dct = torch.cos(np.pi * k.T * (j + 0.5) / n)
        coeffs = (2.0 / n) * self.temp_weight @ dct.T
        coeffs[:, 0] *= 0.5
        return coeffs

    def forward(self, x, edge_index):
        x = F.relu(self.lin1(F.dropout(x, p=self.dropout, training=self.training)))
        x = self.lin2(F.dropout(x, p=self.dropout, training=self.training))
        if not hasattr(self, "L_indices"):
            self.L_indices, self.L_values = get_laplacian(
                edge_index, normalization="sym", num_nodes=x.size(0)
            )
        laplacian = torch.sparse_coo_tensor(
            self.L_indices, self.L_values, (x.size(0), x.size(0))
        )
        coeffs = self.get_cheb_coeffs()
        outputs = [coeffs[h, 0] * x for h in range(self.heads)]
        if self.K > 0:
            previous2 = x
            previous = torch.sparse.mm(laplacian, x) - x
            for h in range(self.heads):
                outputs[h] += coeffs[h, 1] * previous
            for order in range(2, self.K + 1):
                current = 2 * (torch.sparse.mm(laplacian, previous) - previous) - previous2
                for h in range(self.heads):
                    outputs[h] += coeffs[h, order] * current
                previous2, previous = previous, current
        return self.lin_final(torch.cat(outputs, dim=1))


MODEL_FACTORIES: dict[str, Callable[[int, int, int], nn.Module]] = {
    "GBDN+": lambda i, h, o: RelaxedGBDN(i, h, o, num_layers=2, K=5, dropout=0.5),
    "ChebNet": lambda i, h, o: BaselineChebNet(i, h, o, K=5),
    "ChebNetII": lambda i, h, o: ChebNetII(i, h, o, K=10, heads=8, dropout=0.5),
    "H2GCN": BaselineH2GCN,
    "FAGCN": BaselineFAGCN,
    "MLP": BaselineMLP,
    "MixHop": BaselineMixHop,
    "GAT": BaselineGAT,
    "GraphSAGE": BaselineGraphSAGE,
    "ADGN": lambda i, h, o: BaselineADGN(i, h, o, num_iters=2, epsilon=0.1, gamma=0.1),
    "ResNet": BaselineResNet,
    "ResNet+SGC": lambda i, h, o: BaselineResNetSGC(i, h, o, K=5),
}


def compute_multiclass_auroc(y_true, y_probs, num_classes):
    """Exact legacy one-vs-rest trapezoidal AUROC implementation."""
    y_true = y_true.detach().cpu()
    y_probs = y_probs.detach().cpu()
    aucs = []
    for class_id in range(num_classes):
        y_class = (y_true == class_id).float()
        if y_class.sum() == 0:
            continue
        indices = torch.sort(y_probs[:, class_id], descending=True).indices
        sorted_y = y_class[indices]
        tps = torch.cumsum(sorted_y, dim=0)
        fps = torch.cumsum(1 - sorted_y, dim=0)
        tpr = torch.cat([torch.tensor([0.0]), tps / tps[-1]])
        fpr = torch.cat([torch.tensor([0.0]), fps / fps[-1]])
        aucs.append(torch.trapz(tpr, fpr).item())
    return sum(aucs) / len(aucs) if aucs else 0.5


def _optimizer(name: str, model: nn.Module):
    if name == "ChebNetII":
        return torch.optim.Adam(
            [
                {"params": model.temp_weight, "lr": 0.01},
                {
                    "params": [p for n, p in model.named_parameters() if "temp_weight" not in n],
                    "lr": 0.01,
                    "weight_decay": 5e-4,
                },
            ]
        )
    return torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=5e-4)


def _source_hash() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _identity(config: dict[str, Any], manifest: dict[str, Any]) -> str:
    payload = json.dumps(
        {"config": config, "source": _source_hash(), "environment": manifest},
        sort_keys=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def _write_json(path: Path, payload: dict[str, Any], rerun: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not rerun:
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("reproduction", {}).get("identity") == payload["reproduction"]["identity"]:
            return
        raise FileExistsError(f"{path} exists with a different run identity; pass --rerun")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(path)


def _hetero_run_config(dataset_name: str, model_name: str, epochs: int | None = None):
    return {
        "dataset": dataset_name,
        "model": model_name,
        **HETERO_CONFIG,
        "epochs": epochs or HETERO_CONFIG["epochs"],
        "K": 10 if model_name == "ChebNetII" else 5,
    }


def _artifact_matches(path: Path, config: dict[str, Any], manifest: dict[str, Any]) -> bool:
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return payload.get("reproduction", {}).get("identity") == _identity(config, manifest)


def _capture_rng_state() -> dict[str, Any]:
    return {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch": torch.get_rng_state(),
        "cuda": torch.cuda.get_rng_state_all(),
    }


def _restore_rng_state(state: dict[str, Any]) -> None:
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(state["torch"])
    torch.cuda.set_rng_state_all(state["cuda"])


def _write_rng_checkpoint(path: Path, identity: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save({"identity": identity, "rng": _capture_rng_state()}, temporary)
    temporary.replace(path)


def _load_rng_checkpoint(path: Path, identity: str) -> bool:
    if not path.exists():
        return False
    try:
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    except (OSError, RuntimeError, ValueError, EOFError, TypeError):
        return False
    if checkpoint.get("identity") != identity:
        return False
    _restore_rng_state(checkpoint["rng"])
    return True


def _with_provenance(
    payload: dict[str, Any],
    config: dict[str, Any],
    manifest: dict[str, Any],
    duration: float,
    peak_memory: int,
) -> dict[str, Any]:
    payload["reproduction"] = {
        "identity": _identity(config, manifest),
        "source": "notebooks/BlanshkeGraphs.ipynb cells 23 and 28",
        "source_sha256": _source_hash(),
        "config": config,
        "environment": manifest,
        "duration_seconds": duration,
        "peak_cuda_memory_bytes": peak_memory,
    }
    return payload


def run_heterophily(
    dataset_name: str,
    model_name: str,
    output_root: Path,
    data_root: Path,
    rerun: bool = False,
    epochs: int | None = None,
    reseed: bool = True,
    on_epoch: Callable[..., Any] | None = None,
) -> Path:
    if dataset_name not in HETERO_DATASETS or model_name not in HETERO_MODELS:
        raise ValueError(f"unsupported pair: {dataset_name}/{model_name}")
    gpu = verify_last_gpu()
    manifest = environment_manifest(gpu)
    config = _hetero_run_config(dataset_name, model_name, epochs)
    if reseed:
        seed_everything(config["seed"])
    dataset = HeterophilousGraphDataset(
        root=str(data_root / dataset_name),
        name=dataset_name,
        transform=NormalizeFeatures(),
    )
    data = dataset[0].to("cuda:0")
    model = MODEL_FACTORIES[model_name](
        dataset.num_features, config["hidden_dim"], dataset.num_classes
    ).to("cuda:0")
    optimizer = _optimizer(model_name, model)
    split = config["split_id"]
    train_mask = data.train_mask[:, split] if data.train_mask.dim() > 1 else data.train_mask
    val_mask = data.val_mask[:, split] if data.val_mask.dim() > 1 else data.val_mask
    test_mask = data.test_mask[:, split] if data.test_mask.dim() > 1 else data.test_mask
    best_val = 0.0
    final = {"val_auroc": 0.0, "test_auroc": 0.0, "test_acc": 0.0, "test_probs": [], "test_labels": []}
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    total_epochs = config["epochs"]
    for epoch in range(total_epochs):
        model.train()
        optimizer.zero_grad()
        raw = model(data.x, data.edge_index)
        output = raw[0] if isinstance(raw, tuple) else raw
        F.cross_entropy(output[train_mask], data.y[train_mask]).backward()
        optimizer.step()
        model.eval()
        with torch.no_grad():
            raw = model(data.x, data.edge_index)
            output = raw[0] if isinstance(raw, tuple) else raw
            probabilities = F.softmax(output, dim=1)
            val = compute_multiclass_auroc(
                data.y[val_mask], probabilities[val_mask], dataset.num_classes
            )
            if val > best_val:
                best_val = val
                test_probs = probabilities[test_mask]
                test_labels = data.y[test_mask]
                final = {
                    "val_auroc": val,
                    "test_auroc": compute_multiclass_auroc(
                        test_labels, test_probs, dataset.num_classes
                    ),
                    "test_acc": (
                        (test_probs.argmax(dim=1) == test_labels).sum().item()
                        / test_labels.size(0)
                    ),
                    "test_probs": test_probs.cpu().tolist(),
                    "test_labels": test_labels.cpu().tolist(),
                }
        if on_epoch is not None:
            on_epoch(
                epoch,
                total_epochs,
                best_val=best_val,
                test_auroc=final["test_auroc"],
                test_acc=final["test_acc"],
            )
    payload = {
        "dataset": dataset_name,
        "model": model_name,
        "hidden_dim": config["hidden_dim"],
        "lr": config["lr"],
        "epochs": config["epochs"],
        "K": config["K"],
        **final,
    }
    payload = _with_provenance(
        payload,
        config,
        manifest,
        time.perf_counter() - started,
        torch.cuda.max_memory_allocated(),
    )
    path = output_root / dataset_name / f"{model_name}.json"
    _write_json(path, payload, rerun)
    return path


def run_model(
    model_name: str,
    output_root: Path,
    data_root: Path,
    state_root: Path,
    rerun: bool = False,
    epochs: int | None = None,
    on_epoch: Callable[..., Any] | None = None,
    on_dataset: Callable[..., Any] | None = None,
    on_dataset_done: Callable[..., Any] | None = None,
) -> list[Path]:
    """Run one model over datasets in legacy order with exact resumable RNG state."""
    if model_name not in HETERO_MODELS:
        raise ValueError(f"unsupported model: {model_name}")
    gpu = verify_h100()
    manifest = environment_manifest(gpu)
    seed_everything(HETERO_CONFIG["seed"])
    completed: list[Path] = []
    failures = output_root.parent / "reproduction_failures"
    for dataset_name in HETERO_DATASETS:
        config = _hetero_run_config(dataset_name, model_name, epochs)
        identity = _identity(config, manifest)
        output_path = output_root / dataset_name / f"{model_name}.json"
        checkpoint_path = state_root / model_name / f"{dataset_name}.pt"
        skipped = (
            not rerun
            and _artifact_matches(output_path, config, manifest)
            and _load_rng_checkpoint(checkpoint_path, identity)
        )
        if on_dataset is not None:
            on_dataset(dataset_name, skipped=skipped, epochs=config["epochs"])
        if skipped:
            completed.append(output_path)
            if on_dataset_done is not None:
                on_dataset_done(dataset_name, skipped=True)
            continue
        try:
            run_kwargs = {
                "rerun": rerun,
                "epochs": epochs,
                "reseed": False,
            }
            if on_epoch is not None:
                run_kwargs["on_epoch"] = on_epoch
            path = run_heterophily(
                dataset_name,
                model_name,
                output_root,
                data_root,
                **run_kwargs,
            )
            _write_rng_checkpoint(checkpoint_path, identity)
            completed.append(path)
            if on_dataset_done is not None:
                on_dataset_done(dataset_name, skipped=False)
        except Exception as error:
            _record_failure(
                failures / dataset_name / f"{model_name}.json",
                dataset_name,
                model_name,
                error,
            )
            break
    return completed


class ComputeLaplacian:
    def __call__(self, data):
        edge_index, edge_weight = get_laplacian(
            data.edge_index, edge_weight=None, normalization="sym", num_nodes=data.num_nodes
        )
        data.edge_index = edge_index
        data.edge_weight = edge_weight.float()
        return data


class GraphLevelWrapper(nn.Module):
    def __init__(self, base_model, hidden_dim, out_dim):
        super().__init__()
        self.base_model = base_model
        self.lin_out = Linear(hidden_dim, out_dim)

    def forward(self, x, edge_index, edge_weight=None, batch=None):
        try:
            node_output = self.base_model(x, edge_index, edge_weight)
        except TypeError:
            node_output = self.base_model(x, edge_index)
        if isinstance(node_output, tuple):
            node_output = node_output[0]
        return self.lin_out(global_mean_pool(node_output, batch))


def _lrgb_model(name, in_dim, hidden_dim, out_dim):
    if name == "ChebNet_K10":
        base = BaselineChebNet(in_dim, hidden_dim, hidden_dim, K=10)
    elif name == "GBDN+":
        base = RelaxedGBDN(in_dim, hidden_dim, hidden_dim, num_layers=2, K=10)
    else:
        raise ValueError(f"unsupported LRGB model: {name}")
    return GraphLevelWrapper(base, hidden_dim, out_dim)


def _lrgb_evaluate(model, loader):
    from sklearn.metrics import average_precision_score

    model.eval()
    true, scores = [], []
    with torch.no_grad():
        for data in loader:
            data = data.to("cuda:0")
            if hasattr(model.base_model, "cheb_computer"):
                model.base_model.cheb_computer.L_cache = None
            output = model(data.x.float(), data.edge_index, data.edge_weight, data.batch)
            true.append(data.y.cpu())
            scores.append(torch.sigmoid(output).cpu())
    y_true = torch.cat(true).numpy()
    y_scores = torch.cat(scores).numpy()
    return 0.0 if np.isnan(y_scores).any() else float(
        average_precision_score(y_true, y_scores, average="weighted")
    )


def _lrgb_optimizer(name, model, learning_rate):
    if name == "GBDN+":
        return torch.optim.Adam(
            [
                {
                    "params": [p for n, p in model.named_parameters() if "cheb_correction" in n],
                    "lr": learning_rate * 10,
                },
                {
                    "params": [p for n, p in model.named_parameters() if "alpha_param" in n],
                    "lr": learning_rate * 10,
                },
                {
                    "params": [
                        p
                        for n, p in model.named_parameters()
                        if "cheb" not in n and "alpha" not in n
                    ],
                    "lr": learning_rate,
                },
            ],
            weight_decay=1e-7,
        )
    return torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=1e-5)


def _train_lrgb(
    model,
    optimizer,
    loaders,
    epochs,
    on_epoch: Callable[..., Any] | None = None,
    on_batch: Callable[..., Any] | None = None,
):
    best_val = final_test = 0.0
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    train_loader = loaders["train"]
    n_batches = len(train_loader)
    for epoch in range(epochs):
        model.train()
        for batch_idx, data in enumerate(train_loader):
            data = data.to("cuda:0")
            optimizer.zero_grad()
            if hasattr(model.base_model, "cheb_computer"):
                model.base_model.cheb_computer.L_cache = None
            output = model(data.x.float(), data.edge_index, data.edge_weight, data.batch)
            F.binary_cross_entropy_with_logits(output, data.y.float()).backward()
            optimizer.step()
            if on_batch is not None:
                on_batch(batch_idx, n_batches, epoch, epochs)
        val = _lrgb_evaluate(model, loaders["val"])
        if val > best_val:
            best_val = val
            final_test = _lrgb_evaluate(model, loaders["test"])
        if on_epoch is not None:
            on_epoch(epoch, epochs, best_val=best_val, test_ap=final_test)
    return best_val, final_test, time.perf_counter() - started, torch.cuda.max_memory_allocated()


def run_lrgb(
    model_name: str,
    output_root: Path,
    data_root: Path,
    rerun: bool = False,
    epochs: int | None = None,
    on_epoch: Callable[..., Any] | None = None,
    on_batch: Callable[..., Any] | None = None,
    on_model: Callable[..., Any] | None = None,
    on_model_done: Callable[..., Any] | None = None,
) -> Path:
    gpu = verify_last_gpu()
    manifest = environment_manifest(gpu)
    config = {
        "dataset": "Peptides-func",
        "model": model_name,
        **LRGB_CONFIG,
        "epochs": epochs or LRGB_CONFIG["epochs"],
    }
    expected_paths = {
        name: output_root / f"{name}.json" for name in LRGB_MODELS
    }
    if not rerun and all(
        _artifact_matches(path, {**config, "model": name}, manifest)
        for name, path in expected_paths.items()
    ):
        if on_model is not None:
            for name in LRGB_MODELS:
                on_model(name, skipped=True, epochs=config["epochs"])
                if on_model_done is not None:
                    on_model_done(name, skipped=True)
        return expected_paths[model_name]
    seed_everything(config["seed"])
    datasets = {
        split: LRGBDataset(
            root=str(data_root / "Peptides-func"),
            name="Peptides-func",
            split=split,
            pre_transform=ComputeLaplacian(),
        )
        for split in ("train", "val", "test")
    }
    loaders = {
        "train": DataLoader(
            datasets["train"],
            batch_size=config["batch_size"],
            shuffle=True,
            num_workers=2,
            pin_memory=True,
        ),
        "val": DataLoader(
            datasets["val"],
            batch_size=config["batch_size"] * 2,
            shuffle=False,
            num_workers=2,
            pin_memory=True,
        ),
        "test": DataLoader(
            datasets["test"],
            batch_size=config["batch_size"] * 2,
            shuffle=False,
            num_workers=2,
            pin_memory=True,
        ),
    }
    # Cell 28 instantiated both models before training and then trained ChebNet
    # first. Retaining that order is necessary for GBDN+ initialization and
    # DataLoader RNG parity.
    models = {
        name: _lrgb_model(name, datasets["train"].num_features, config["hidden_dim"], 10).to(
            "cuda:0"
        )
        for name in LRGB_MODELS
    }
    selected_path = None
    for current_name, model in models.items():
        current_config = {**config, "model": current_name}
        if on_model is not None:
            on_model(current_name, skipped=False, epochs=config["epochs"])
        optimizer = _lrgb_optimizer(current_name, model, config["lr"])
        train_kwargs = {}
        if on_epoch is not None:
            train_kwargs["on_epoch"] = on_epoch
        if on_batch is not None:
            train_kwargs["on_batch"] = on_batch
        best_val, final_test, duration, peak_memory = _train_lrgb(
            model,
            optimizer,
            loaders,
            config["epochs"],
            **train_kwargs,
        )
        payload = {
            "dataset": "Peptides-func",
            "model": current_name,
            "test_ap": final_test,
            "best_val_ap": best_val,
            "config": {
                "epochs": config["epochs"],
                "batch_size": config["batch_size"],
                "hidden_dim": config["hidden_dim"],
            },
        }
        payload = _with_provenance(
            payload, current_config, manifest, duration, peak_memory
        )
        path = output_root / f"{current_name}.json"
        _write_json(path, payload, rerun)
        if on_model_done is not None:
            on_model_done(current_name, skipped=False)
        if current_name == model_name:
            selected_path = path
            break
    if selected_path is None:
        raise ValueError(f"unsupported LRGB model: {model_name}")
    return selected_path


def run_all(
    output_root: Path,
    lrgb_output_root: Path,
    data_root: Path,
    rerun: bool = False,
) -> list[Path]:
    completed = []
    failures = output_root.parent / "reproduction_failures"
    for model in HETERO_MODELS:
        completed.extend(
            run_model(
                model,
                output_root,
                data_root,
                output_root.parent / "reproduction_state",
                rerun,
            )
        )
    try:
        run_lrgb("GBDN+", lrgb_output_root, data_root, rerun)
        completed.extend(lrgb_output_root / f"{model}.json" for model in LRGB_MODELS)
    except Exception as error:
        for model in LRGB_MODELS:
            path = lrgb_output_root / f"{model}.json"
            if not path.exists():
                _record_failure(
                    failures / "Peptides-func" / f"{model}.json",
                    "Peptides-func",
                    model,
                    error,
                )
    return completed


def _record_failure(path: Path, dataset: str, model: str, error: Exception) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            {
                "dataset": dataset,
                "model": model,
                "error": f"{type(error).__name__}: {error}",
                "traceback": traceback.format_exc(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    temporary.replace(path)


def _load_jsons(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    records = {}
    if not root.exists():
        return records
    for path in root.rglob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if "dataset" in data and "model" in data:
            records[(data["dataset"], data["model"])] = data
    return records


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _metric_table(
    originals: dict,
    reproduced: dict,
    metric: str,
    datasets: tuple[str, ...] = HETERO_DATASETS,
) -> str:
    rows = []
    for model in HETERO_MODELS:
        cells = [model]
        for dataset in datasets:
            old = originals.get((dataset, model), {}).get(metric)
            new = reproduced.get((dataset, model), {}).get(metric)
            if old is None or new is None:
                cells.append("—")
            else:
                cells.append(f"{new:.4f} ({old:.4f}; Δ {new - old:+.4f})")
        rows.append(cells)
    return _markdown_table(["Model", *datasets], rows)


def validate_heterophily_record(record: dict[str, Any], tolerance: float = 1e-6) -> list[str]:
    problems = []
    if not record.get("test_probs") or not record.get("test_labels"):
        return ["missing test predictions or labels"]
    probs = torch.tensor(record["test_probs"])
    labels = torch.tensor(record["test_labels"])
    accuracy = float((probs.argmax(dim=1) == labels).float().mean().item())
    auroc = compute_multiclass_auroc(labels, probs, probs.shape[1])
    if abs(accuracy - record["test_acc"]) > tolerance:
        problems.append(f"test_acc mismatch: recomputed {accuracy}")
    if abs(auroc - record["test_auroc"]) > tolerance:
        problems.append(f"test_auroc mismatch: recomputed {auroc}")
    return problems


def verify_reproduction(
    original_root: Path,
    reproduced_root: Path,
    original_lrgb_root: Path,
    reproduced_lrgb_root: Path,
    drift_tolerance: float = 0.02,
) -> list[str]:
    """Return acceptance failures for the complete 62-artifact reproduction."""
    problems: list[str] = []
    originals = _load_jsons(original_root)
    reproduced = _load_jsons(reproduced_root)
    original_lrgb = _load_jsons(original_lrgb_root)
    reproduced_lrgb = _load_jsons(reproduced_lrgb_root)
    provenance_keys = {
        "identity",
        "source",
        "source_sha256",
        "config",
        "environment",
        "duration_seconds",
        "peak_cuda_memory_bytes",
    }

    for dataset in HETERO_DATASETS:
        for model in HETERO_MODELS:
            key = (dataset, model)
            label = f"{dataset}/{model}"
            record = reproduced.get(key)
            original = originals.get(key)
            if record is None:
                problems.append(f"missing heterophily artifact: {label}")
                continue
            if original is None:
                problems.append(f"missing reference artifact: {label}")
                continue
            for issue in validate_heterophily_record(record):
                problems.append(f"invalid {label}: {issue}")
            reproduction = record.get("reproduction", {})
            missing = sorted(provenance_keys - reproduction.keys())
            if missing:
                problems.append(f"missing provenance in {label}: {', '.join(missing)}")
            for metric in ("test_acc", "test_auroc"):
                drift = abs(float(record[metric]) - float(original[metric]))
                if drift > drift_tolerance:
                    problems.append(
                        f"metric drift in {label}/{metric}: {drift:.6f} > {drift_tolerance:.6f}"
                    )

    for model in LRGB_MODELS:
        key = ("Peptides-func", model)
        label = f"Peptides-func/{model}"
        record = reproduced_lrgb.get(key)
        original = original_lrgb.get(key)
        if record is None:
            problems.append(f"missing LRGB artifact: {label}")
            continue
        if original is None:
            problems.append(f"missing LRGB reference artifact: {label}")
            continue
        reproduction = record.get("reproduction", {})
        missing = sorted(provenance_keys - reproduction.keys())
        if missing:
            problems.append(f"missing provenance in {label}: {', '.join(missing)}")
        for metric in ("best_val_ap", "test_ap"):
            drift = abs(float(record[metric]) - float(original[metric]))
            if drift > drift_tolerance:
                problems.append(
                    f"metric drift in {label}/{metric}: {drift:.6f} > {drift_tolerance:.6f}"
                )

    if not (reproduced_root / "run_manifest.json").exists():
        problems.append("missing results_repro/run_manifest.json")
    return problems


def generate_report(
    original_root: Path,
    reproduced_root: Path,
    original_lrgb_root: Path,
    reproduced_lrgb_root: Path,
    output_path: Path,
) -> Path:
    originals = _load_jsons(original_root)
    reproduced = _load_jsons(reproduced_root)
    original_lrgb = _load_jsons(original_lrgb_root)
    reproduced_lrgb = _load_jsons(reproduced_lrgb_root)
    failures = _load_jsons(reproduced_root.parent / "reproduction_failures")
    expected = {(dataset, model) for dataset in HETERO_DATASETS for model in HETERO_MODELS}
    validation = {
        key: validate_heterophily_record(record)
        for key, record in reproduced.items()
        if key in expected
    }
    status_rows = []
    for dataset, model in sorted(expected):
        if (dataset, model) not in reproduced:
            failure = failures.get((dataset, model), {}).get("error")
            status = f"failed: {failure}" if failure else "missing"
        elif validation.get((dataset, model)):
            status = "invalid: " + "; ".join(validation[(dataset, model)])
        else:
            old = originals.get((dataset, model), {})
            new = reproduced[(dataset, model)]
            drift = max(
                abs(new[metric] - old[metric])
                for metric in ("test_acc", "test_auroc")
                if metric in new and metric in old
            )
            status = "complete" if drift <= 0.02 else f"complete; drift {drift:.4f}"
        status_rows.append([dataset, model, status])

    lrgb_rows = []
    for model in LRGB_MODELS:
        old = original_lrgb.get(("Peptides-func", model))
        new = reproduced_lrgb.get(("Peptides-func", model))
        if old and new:
            lrgb_rows.append(
                [
                    model,
                    f"{old['best_val_ap']:.4f}",
                    f"{new['best_val_ap']:.4f}",
                    f"{new['best_val_ap'] - old['best_val_ap']:+.4f}",
                    f"{old['test_ap']:.4f}",
                    f"{new['test_ap']:.4f}",
                    f"{new['test_ap'] - old['test_ap']:+.4f}",
                ]
            )
        else:
            lrgb_rows.append([model, "—", "—", "—", "—", "—", "—"])

    manifests = [
        value.get("reproduction", {}).get("environment")
        for value in [*reproduced.values(), *reproduced_lrgb.values()]
        if value.get("reproduction", {}).get("environment")
    ]
    environment = json.dumps(manifests[0], indent=2) if manifests else "No reproduction run completed."
    performance_rows = []
    for (dataset, model), record in sorted({**reproduced, **reproduced_lrgb}.items()):
        provenance = record.get("reproduction", {})
        seconds = provenance.get("duration_seconds")
        memory = provenance.get("peak_cuda_memory_bytes")
        performance_rows.append(
            [
                dataset,
                model,
                f"{seconds:.1f}" if isinstance(seconds, (int, float)) else "—",
                f"{memory / 2**20:.1f}" if isinstance(memory, (int, float)) else "—",
            ]
        )
    report = f"""# Legacy Result Reproduction Report

## Scope

This report compares the single-seed, single-split legacy artifacts against faithful reruns of cells 23 and 28 in `notebooks/BlanshkeGraphs.ipynb`. These results are not the newer multi-seed official protocol in `papers/revision/benchmark_protocol.md`.

Completed heterophily artifacts: **{len(expected & reproduced.keys())}/60**
Completed Peptides-func artifacts: **{sum(key in reproduced_lrgb for key in [('Peptides-func', model) for model in LRGB_MODELS])}/2**

## Environment and GPU isolation

```json
{environment}
```

Every training command fails closed unless `CUDA_VISIBLE_DEVICES` selects one physical H100 and PyTorch sees exactly one logical CUDA device.

## Protocol

- Heterophily: seed 25, official split column 0, normalized features, hidden size 64, 1,000 epochs, validation-AUROC selection.
- Peptides-func: seed 25, official splits, hidden size 256, batch size 128, 100 epochs, weighted average precision.
- Original `results/` and `results_LRGB/` artifacts remain unchanged.

## Heterophily test accuracy

Each cell is `reproduced (original; delta)`.

{_metric_table(originals, reproduced, 'test_acc')}

## Heterophily test AUROC

Each cell is `reproduced (original; delta)`.

{_metric_table(originals, reproduced, 'test_auroc')}

## Peptides-func average precision

{_markdown_table(['Model', 'Original val', 'Reproduced val', 'Delta val', 'Original test', 'Reproduced test', 'Delta test'], lrgb_rows)}

## Artifact status and metric validation

{_markdown_table(['Dataset', 'Model', 'Status'], status_rows)}

## Runtime and peak CUDA memory

{_markdown_table(['Dataset', 'Model', 'Seconds', 'Peak MiB'], performance_rows) if performance_rows else 'No completed runs.'}

## Reproducibility limitations

- GPU kernels, CUDA/PyTorch/PyG versions, and dependency changes can cause numerical drift.
- The legacy protocol evaluates only seed 25 and split column 0 for heterophily.
- The legacy checkpoint rule uses validation AUROC for all heterophily datasets.
- Preserved legacy JSONs have up to 0.0036 internal AUROC drift between their stored scalar and probabilities; reproduced artifacts are validated independently.
- Peptides-func artifacts do not contain predictions, so AP cannot be independently recomputed from the saved JSON alone.
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(report, encoding="utf-8")
    temporary.replace(output_path)
    return output_path
