"""Licensed PyG ChebNet adapter with explicit resource accounting.

This is the Chebyshev network family of Defferrard et al. (2016), implemented
with :class:`torch_geometric.nn.ChebConv`.  It is deliberately named ChebNet,
not ChebNetII: the latter uses a different interpolation parameterization.
Nothing in this module constitutes baseline admission or parity evidence.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn
from torch_geometric.nn import ChebConv


@dataclass(frozen=True)
class ChebNetResourceCount:
    """Auditable trainable-parameter and feature-matrix SpMV counts."""

    trainable_parameters: int
    feature_matrix_spmvs_per_forward: int
    convention: str = (
        "one ChebConv propagation of a node-feature matrix counts as one SpMV; "
        "dense channel mixing and elementwise operations do not"
    )


class ChebNet(nn.Module):
    """Two-layer node-classification ChebNet using a fixed normalized scale.

    ``lambda_max=2`` is passed explicitly for the symmetric normalized
    Laplacian, so PyG applies the recurrence to ``L - I``.  Input graphs must
    already follow the official reciprocal-edge construction; graph-policy
    validation belongs to the dataset adapter, not this model.
    """

    def __init__(
        self,
        in_channels: int,
        hidden_channels: int,
        out_channels: int,
        *,
        K: int,
        dropout: float,
    ) -> None:
        super().__init__()
        for name, value in (
            ("in_channels", in_channels),
            ("hidden_channels", hidden_channels),
            ("out_channels", out_channels),
            ("K", K),
        ):
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if type(dropout) not in (int, float) or not 0.0 <= float(dropout) < 1.0:
            raise ValueError("dropout must be in [0,1)")
        self.K = K
        self.dropout = float(dropout)
        self.conv1 = ChebConv(in_channels, hidden_channels, K, normalization="sym")
        self.conv2 = ChebConv(hidden_channels, out_channels, K, normalization="sym")

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_weight: torch.Tensor | None = None,
    ) -> torch.Tensor:
        lambda_max = x.new_tensor(2.0)
        x = self.conv1(x, edge_index, edge_weight, lambda_max=lambda_max)
        x = torch.relu(x)
        x = nn.functional.dropout(x, p=self.dropout, training=self.training)
        return self.conv2(x, edge_index, edge_weight, lambda_max=lambda_max)

    def resource_count(self) -> ChebNetResourceCount:
        """Return counts from the instantiated module and PyG recurrence."""

        parameters = sum(parameter.numel() for parameter in self.parameters())
        return ChebNetResourceCount(
            trainable_parameters=parameters,
            feature_matrix_spmvs_per_forward=2 * (self.K - 1),
        )
