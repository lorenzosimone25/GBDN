"""Synthetic graph signals routed through the canonical graph contract."""

import networkx as nx
import numpy as np
import torch
from scipy.spatial import KDTree
from torch_geometric.utils import from_networkx

from gbdn.core import PreprocessedGraph, preprocess_reciprocal_mean


def _canonical_spectral_graph(
    edge_index: torch.Tensor,
    num_nodes: int,
    edge_weight: torch.Tensor | None = None,
) -> tuple[PreprocessedGraph, torch.Tensor, torch.Tensor]:
    """Preprocess possibly directed edges before any Hermitian eigensolver."""

    if edge_weight is None:
        edge_weight = torch.ones(edge_index.shape[1], dtype=torch.float64)
    processed = preprocess_reciprocal_mean(
        edge_index,
        edge_weight,
        num_nodes,
    )
    laplacian = processed.laplacian.to_dense()
    eigenvalues, eigenvectors = torch.linalg.eigh(laplacian)
    residual = torch.linalg.matrix_norm(
        laplacian.to(eigenvectors.dtype) @ eigenvectors
        - eigenvectors * eigenvalues.unsqueeze(0),
        ord="fro",
    ) / torch.linalg.matrix_norm(laplacian, ord="fro").clamp_min(1e-30)
    if float(residual.item()) > 1e-10:
        raise RuntimeError(
            "validated synthetic-graph eigendecomposition failed its residual check"
        )
    return processed, eigenvalues, eigenvectors


def _validate_mode_indices(
    num_nodes: int,
    idx_low: int,
    idx_high: int,
) -> None:
    if not 0 <= idx_low < num_nodes or not 0 <= idx_high < num_nodes:
        raise ValueError(
            f"mode indices must lie in [0, {num_nodes}), got {idx_low}, {idx_high}"
        )


def grid_graph_data(grid_size: int = 20, idx_low: int = 3, idx_high: int | None = None):
    """Build a recorded reciprocal-mean grid and low/high eigenmode mixture."""

    if isinstance(grid_size, bool) or not isinstance(grid_size, int) or grid_size < 2:
        raise ValueError("grid_size must be an integer of at least two")
    G = nx.grid_2d_graph(grid_size, grid_size)
    data = from_networkx(G)
    N = data.num_nodes
    if idx_high is None:
        idx_high = N - 5
    _validate_mode_indices(N, idx_low, idx_high)

    processed, evals, evecs = _canonical_spectral_graph(data.edge_index, N)
    data.edge_index = processed.adjacency.indices()
    data.edge_weight = processed.adjacency.values()

    sig_low = evecs[:, idx_low] * 5.0
    sig_high = evecs[:, idx_high] * 2.5
    sig_mix = sig_low + sig_high

    return {
        "data": data,
        "G": G,
        "grid_size": grid_size,
        "adjacency": processed.adjacency,
        "laplacian": processed.laplacian,
        "graph_preprocess_record": processed.record.to_dict(),
        "evals": evals,
        "evecs": evecs,
        "sig_low": sig_low,
        "sig_high": sig_high,
        "sig_mix": sig_mix,
        "idx_low": idx_low,
        "idx_high": idx_high,
    }


def sphere_graph_data(
    n_nodes: int = 400,
    k_nn: int = 8,
    idx_low: int = 5,
    idx_high: int = 150,
):
    """Build a reciprocal-mean Fibonacci-sphere kNN spectral fixture.

    The directed kNN relation is intentionally treated as raw input.  The
    returned ``data.edge_index`` and eigensystem belong to the recorded
    symmetric adjacency, never to the asymmetric relation.
    """

    import math

    if isinstance(n_nodes, bool) or not isinstance(n_nodes, int) or n_nodes < 3:
        raise ValueError("n_nodes must be an integer of at least three")
    if isinstance(k_nn, bool) or not isinstance(k_nn, int) or not 1 <= k_nn < n_nodes:
        raise ValueError("k_nn must be an integer in [1, n_nodes)")
    _validate_mode_indices(n_nodes, idx_low, idx_high)

    points = []
    phi = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(n_nodes):
        y = 1 - (i / float(n_nodes - 1)) * 2
        r = math.sqrt(max(0.0, 1 - y * y))
        theta = phi * i
        points.append([math.cos(theta) * r, y, math.sin(theta) * r])
    points_np = np.array(points)
    points = torch.tensor(points_np, dtype=torch.float32)

    tree = KDTree(points.numpy())
    _, ind = tree.query(points.numpy(), k=k_nn + 1)
    edges = []
    for i in range(n_nodes):
        for j in ind[i][1:]:
            edges.append([i, int(j)])
    directed_edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()

    processed, evals, evecs = _canonical_spectral_graph(
        directed_edge_index,
        n_nodes,
    )

    sig_low = evecs[:, idx_low] * 5.0
    sig_high = evecs[:, idx_high] * 3.0
    sig_mix = sig_low + sig_high

    class Data:
        pass

    data = Data()
    data.edge_index = processed.adjacency.indices()
    data.edge_weight = processed.adjacency.values()
    data.num_nodes = n_nodes

    return {
        "data": data,
        "points": points_np,
        "adjacency": processed.adjacency,
        "laplacian": processed.laplacian,
        "graph_preprocess_record": processed.record.to_dict(),
        "evals": evals,
        "evecs": evecs,
        "sig_low": sig_low,
        "sig_high": sig_high,
        "sig_mix": sig_mix,
        "idx_low": idx_low,
        "idx_high": idx_high,
    }


def complex_signal_from_real(sig: torch.Tensor, channels: int = 1) -> torch.Tensor:
    """Real graph signal -> complex [N, C] with zero imaginary part."""
    if sig.dim() == 1:
        sig = sig.unsqueeze(1)
    if channels > 1:
        sig = sig.repeat(1, channels)
    return torch.complex(sig.float(), torch.zeros_like(sig.float()))
