"""Synthetic graph signals for unwinding experiments."""

import math

import networkx as nx
import numpy as np
import torch
from scipy.spatial import KDTree
from torch_geometric.utils import from_networkx, get_laplacian, to_dense_adj


def grid_graph_data(grid_size: int = 20, idx_low: int = 3, idx_high: int | None = None):
    """Build grid graph with low+high eigenmode mixture."""
    G = nx.grid_2d_graph(grid_size, grid_size)
    data = from_networkx(G)
    N = data.num_nodes
    if idx_high is None:
        idx_high = N - 5

    L_idx, L_wt = get_laplacian(data.edge_index, normalization="sym", num_nodes=N)
    L = to_dense_adj(L_idx, edge_attr=L_wt, max_num_nodes=N).squeeze(0)
    evals, evecs = torch.linalg.eigh(L)

    sig_low = evecs[:, idx_low] * 5.0
    sig_high = evecs[:, idx_high] * 2.5
    sig_mix = sig_low + sig_high

    return {
        "data": data,
        "G": G,
        "grid_size": grid_size,
        "evals": evals,
        "evecs": evecs,
        "sig_low": sig_low,
        "sig_high": sig_high,
        "sig_mix": sig_mix,
        "idx_low": idx_low,
        "idx_high": idx_high,
    }


def sphere_graph_data(n_nodes: int = 400, k_nn: int = 8, idx_low: int = 5, idx_high: int = 150):
    """Fibonacci sphere kNN graph with eigenmode mixture."""

    import math
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
    edge_index = torch.tensor(edges, dtype=torch.long).t()

    L_idx, L_wt = get_laplacian(edge_index, normalization="sym", num_nodes=n_nodes)
    L = to_dense_adj(L_idx, edge_attr=L_wt, max_num_nodes=n_nodes).squeeze(0)
    evals, evecs = torch.linalg.eigh(L)

    sig_low = evecs[:, idx_low] * 5.0
    sig_high = evecs[:, idx_high] * 3.0
    sig_mix = sig_low + sig_high

    class Data:
        pass

    data = Data()
    data.edge_index = edge_index
    data.num_nodes = n_nodes

    return {
        "data": data,
        "points": points_np,
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
