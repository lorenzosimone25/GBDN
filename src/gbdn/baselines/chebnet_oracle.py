"""Independent dense oracle for the licensed PyG ChebNet adapter.

The implementation intentionally does not import PyTorch Geometric.  It builds
the symmetric normalized operator directly and evaluates the Chebyshev
recurrence with dense matrix multiplication.  This keeps parity tests
structurally independent from ``ChebConv`` message passing.
"""

from __future__ import annotations

from collections.abc import Sequence

import torch


def dense_scaled_symmetric_laplacian(
    edge_index: torch.Tensor,
    edge_weight: torch.Tensor,
    *,
    num_nodes: int,
) -> torch.Tensor:
    """Return ``2 L_sym / 2 - I`` for one reciprocal weighted graph.

    Under the adapter's fixed ``lambda_max=2`` convention, this is
    ``-D^{-1/2} A D^{-1/2}``.  Isolated vertices therefore have zero rows and
    columns, matching the scaled PyG operator.  Reciprocal symmetry is checked
    explicitly because it is part of the official graph-input contract.
    """

    if type(num_nodes) is not int or num_nodes <= 0:
        raise ValueError("num_nodes must be a positive integer")
    if (
        edge_index.ndim != 2
        or edge_index.shape[0] != 2
        or edge_index.dtype != torch.long
    ):
        raise ValueError("edge_index must have shape [2, E] and torch.long dtype")
    if edge_weight.ndim != 1 or edge_weight.numel() != edge_index.shape[1]:
        raise ValueError("edge_weight must contain one scalar per edge")
    if not edge_weight.is_floating_point() or not torch.isfinite(edge_weight).all():
        raise ValueError("edge_weight must be finite floating point")
    if edge_weight.numel() and torch.any(edge_weight < 0):
        raise ValueError("edge_weight must be nonnegative")
    if edge_index.device != edge_weight.device:
        raise ValueError("edge_index and edge_weight must share a device")
    if edge_index.numel() and (
        int(edge_index.min()) < 0 or int(edge_index.max()) >= num_nodes
    ):
        raise ValueError("edge_index contains a vertex outside num_nodes")

    adjacency = edge_weight.new_zeros((num_nodes, num_nodes))
    if edge_weight.numel():
        source, target = edge_index
        adjacency.index_put_((target, source), edge_weight, accumulate=True)
    if not torch.allclose(adjacency, adjacency.mT, rtol=0.0, atol=0.0):
        raise ValueError("the ChebNet oracle requires an exactly reciprocal graph")

    degree = adjacency.sum(dim=1)
    inverse_sqrt = torch.zeros_like(degree)
    nonisolated = degree > 0
    inverse_sqrt[nonisolated] = degree[nonisolated].rsqrt()
    return -(inverse_sqrt[:, None] * adjacency * inverse_sqrt[None, :])


def dense_chebyshev_convolution(
    x: torch.Tensor,
    scaled_laplacian: torch.Tensor,
    weights: Sequence[torch.Tensor],
    bias: torch.Tensor,
) -> torch.Tensor:
    """Evaluate one ChebConv layer with independent dense recurrence."""

    if x.ndim != 2:
        raise ValueError("x must be a node-by-feature matrix")
    if scaled_laplacian.shape != (x.shape[0], x.shape[0]):
        raise ValueError("scaled_laplacian shape is incompatible with x")
    if not weights:
        raise ValueError("at least one Chebyshev weight is required")
    output_channels = weights[0].shape[0]
    if bias.shape != (output_channels,):
        raise ValueError("bias shape differs from the Chebyshev output width")
    if any(weight.shape != (output_channels, x.shape[1]) for weight in weights):
        raise ValueError("Chebyshev weights must share [out_channels, in_channels]")

    terms = [x]
    if len(weights) > 1:
        terms.append(scaled_laplacian @ x)
    for _ in range(2, len(weights)):
        terms.append(2.0 * scaled_laplacian @ terms[-1] - terms[-2])
    return sum(term @ weight.mT for term, weight in zip(terms, weights)) + bias


def dense_two_layer_chebnet(
    x: torch.Tensor,
    scaled_laplacian: torch.Tensor,
    *,
    first_weights: Sequence[torch.Tensor],
    first_bias: torch.Tensor,
    second_weights: Sequence[torch.Tensor],
    second_bias: torch.Tensor,
) -> torch.Tensor:
    """Evaluate the adapter architecture with deterministic dropout disabled."""

    hidden = dense_chebyshev_convolution(
        x, scaled_laplacian, first_weights, first_bias
    ).relu()
    return dense_chebyshev_convolution(
        hidden, scaled_laplacian, second_weights, second_bias
    )


__all__ = [
    "dense_chebyshev_convolution",
    "dense_scaled_symmetric_laplacian",
    "dense_two_layer_chebnet",
]
