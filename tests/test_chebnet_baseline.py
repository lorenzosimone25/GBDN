from __future__ import annotations

import torch
import pytest

from gbdn.baselines.chebnet import ChebNet
from gbdn.heterophily_contract import DATASET_REGISTRY


def _reciprocal_weighted_graph() -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    adjacency = torch.tensor(
        [
            [0.0, 1.0, 0.0, 0.0],
            [1.0, 0.0, 2.0, 0.0],
            [0.0, 2.0, 0.0, 0.5],
            [0.0, 0.0, 0.5, 0.0],
        ],
        dtype=torch.float64,
    )
    row, col = adjacency.nonzero(as_tuple=True)
    edge_index = torch.stack((row, col))
    edge_weight = adjacency[row, col]
    degree = adjacency.sum(dim=1)
    inv_sqrt = degree.rsqrt()
    normalized_adjacency = inv_sqrt[:, None] * adjacency * inv_sqrt[None, :]
    scaled_laplacian = -normalized_adjacency  # 2 L / 2 - I = L - I.
    return edge_index, edge_weight, scaled_laplacian


def _dense_chebyshev_apply(
    scaled_laplacian: torch.Tensor,
    x: torch.Tensor,
    weights: tuple[torch.Tensor, ...],
    bias: torch.Tensor,
) -> torch.Tensor:
    terms = [x]
    if len(weights) > 1:
        terms.append(scaled_laplacian @ x)
    for _ in range(2, len(weights)):
        terms.append(2.0 * scaled_laplacian @ terms[-1] - terms[-2])
    return sum(term @ weight.T for term, weight in zip(terms, weights)) + bias


def test_pyg_chebnet_layer_matches_independent_dense_recurrence():
    edge_index, edge_weight, scaled_laplacian = _reciprocal_weighted_graph()
    model = ChebNet(2, 3, 2, K=4, dropout=0.0).to(dtype=torch.float64)
    x = torch.tensor(
        [[0.2, -0.1], [0.5, 0.7], [-0.4, 0.3], [0.9, -0.2]],
        dtype=torch.float64,
    )
    with torch.no_grad():
        for index, linear in enumerate(model.conv1.lins):
            linear.weight.copy_(
                torch.arange(6, dtype=torch.float64).reshape(3, 2) / 10 + index / 7
            )
        model.conv1.bias.copy_(torch.tensor([0.1, -0.2, 0.3], dtype=torch.float64))
    observed = model.conv1(
        x,
        edge_index,
        edge_weight,
        lambda_max=x.new_tensor(2.0),
    )
    expected = _dense_chebyshev_apply(
        scaled_laplacian,
        x,
        tuple(linear.weight for linear in model.conv1.lins),
        model.conv1.bias,
    )
    torch.testing.assert_close(observed, expected, rtol=1e-12, atol=1e-12)


def test_chebnet_resource_count_and_task_head_are_exact():
    model = ChebNet(7, 11, 1, K=5, dropout=0.25)
    expected_parameters = 5 * 7 * 11 + 11 + 5 * 11 * 1 + 1
    count = model.resource_count()
    assert count.trainable_parameters == expected_parameters
    assert count.trainable_parameters == sum(p.numel() for p in model.parameters())
    assert count.feature_matrix_spmvs_per_forward == 8
    assert model.conv2.out_channels == 1


def test_chebnet_rejects_ambiguous_or_invalid_configuration():
    for kwargs in (
        {"K": 0, "dropout": 0.0},
        {"K": 3, "dropout": -0.1},
        {"K": 3, "dropout": 1.0},
    ):
        try:
            ChebNet(2, 3, 2, **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"configuration should be rejected: {kwargs}")


@pytest.mark.parametrize("dataset", tuple(DATASET_REGISTRY))
def test_chebnet_official_factory_binds_feature_and_head_width(dataset):
    spec = DATASET_REGISTRY[dataset]
    model = ChebNet.for_official_dataset(
        dataset,
        in_channels=spec.feature_count,
        hidden_channels=8,
        K=3,
        dropout=0.0,
    )
    assert model.conv1.in_channels == spec.feature_count
    assert model.conv2.out_channels == spec.output_logits

    with pytest.raises(ValueError, match="input features"):
        ChebNet.for_official_dataset(
            dataset,
            in_channels=spec.feature_count + 1,
            hidden_channels=8,
            K=3,
            dropout=0.0,
        )


def test_chebnet_official_factory_rejects_nonregistry_dataset():
    with pytest.raises(ValueError, match="outside the official registry"):
        ChebNet.for_official_dataset(
            "Cora", in_channels=1433, hidden_channels=8, K=3, dropout=0.0
        )
