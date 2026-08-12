from __future__ import annotations

import hashlib
import importlib.metadata
import inspect
from pathlib import Path

import pytest
import torch
from torch import nn
from torch_geometric.nn import ChebConv

from gbdn.baselines.chebnet import ChebNet
from gbdn.baselines.chebnet_oracle import (
    dense_scaled_symmetric_laplacian,
    dense_two_layer_chebnet,
)
from gbdn.heterophily_contract import DATASET_REGISTRY


PYG_VERSION = "2.8.0"
PYG_CHEB_CONV_SHA256 = (
    "e6c9039a7511906934a9860ac1e7deea4923fd94a88af52093f510cfdb221c85"
)
PYG_LICENSE_SHA256 = (
    "89cfb6edc309735916a0c1189dccf761add4af6062ddb34b5a26f60d3efadfea"
)


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


def _graph_with_isolated_vertex() -> tuple[torch.Tensor, torch.Tensor]:
    edge_index, edge_weight, _ = _reciprocal_weighted_graph()
    return edge_index, edge_weight


def _fill_deterministic_parameters(model: nn.Module) -> None:
    with torch.no_grad():
        for index, parameter in enumerate(model.parameters()):
            values = torch.arange(parameter.numel(), dtype=parameter.dtype).reshape(
                parameter.shape
            )
            parameter.copy_(0.015 * (values + 1.0) + 0.025 * index)
        # Keep the hidden response away from the ReLU nondifferentiability.
        model.conv1.bias.add_(1.5)


class _UpstreamFunctionalChebNet(nn.Module):
    """Direct composition of fresh upstream operators, independent of wrapper."""

    def __init__(self, in_channels: int, hidden: int, out_channels: int, K: int):
        super().__init__()
        self.conv1 = ChebConv(in_channels, hidden, K, normalization="sym")
        self.conv2 = ChebConv(hidden, out_channels, K, normalization="sym")

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_weight: torch.Tensor,
    ) -> torch.Tensor:
        lambda_max = x.new_tensor(2.0)
        hidden = self.conv1(
            x, edge_index, edge_weight, lambda_max=lambda_max
        ).relu()
        return self.conv2(
            hidden, edge_index, edge_weight, lambda_max=lambda_max
        )


def _loss(output: torch.Tensor) -> torch.Tensor:
    probe = torch.linspace(
        -0.6, 0.9, output.numel(), dtype=output.dtype, device=output.device
    ).reshape_as(output)
    return (output * probe).sum() + 0.17 * output.square().sum()


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


def test_wrapper_matches_fresh_upstream_functional_model_and_gradients():
    edge_index, edge_weight = _graph_with_isolated_vertex()
    adapter = ChebNet(2, 4, 3, K=4, dropout=0.0).to(dtype=torch.float64).eval()
    reference = _UpstreamFunctionalChebNet(2, 4, 3, K=4).to(
        dtype=torch.float64
    ).eval()
    _fill_deterministic_parameters(adapter)
    reference.load_state_dict(adapter.state_dict())

    values = torch.tensor(
        [
            [0.2, -0.1],
            [0.5, 0.7],
            [-0.4, 0.3],
            [0.9, -0.2],
            [0.6, 0.4],  # isolated vertex
        ],
        dtype=torch.float64,
    )
    adapter_x = values.clone().requires_grad_()
    reference_x = values.clone().requires_grad_()
    adapter_output = adapter(adapter_x, edge_index, edge_weight)
    reference_output = reference(reference_x, edge_index, edge_weight)
    torch.testing.assert_close(adapter_output, reference_output, rtol=0.0, atol=0.0)

    adapter_gradients = torch.autograd.grad(
        _loss(adapter_output), (adapter_x, *adapter.parameters())
    )
    reference_gradients = torch.autograd.grad(
        _loss(reference_output), (reference_x, *reference.parameters())
    )
    assert len(adapter_gradients) == len(reference_gradients)
    for observed, expected in zip(adapter_gradients, reference_gradients):
        torch.testing.assert_close(observed, expected, rtol=0.0, atol=0.0)


@pytest.mark.parametrize("K", (1, 2, 4, 6))
def test_full_wrapper_matches_independent_dense_oracle_and_gradients(K):
    edge_index, edge_weight = _graph_with_isolated_vertex()
    model = ChebNet(2, 4, 3, K=K, dropout=0.0).to(dtype=torch.float64).eval()
    _fill_deterministic_parameters(model)
    values = torch.tensor(
        [
            [0.2, -0.1],
            [0.5, 0.7],
            [-0.4, 0.3],
            [0.9, -0.2],
            [0.6, 0.4],
        ],
        dtype=torch.float64,
    )
    sparse_x = values.clone().requires_grad_()
    dense_x = values.clone().requires_grad_()
    scaled_laplacian = dense_scaled_symmetric_laplacian(
        edge_index, edge_weight, num_nodes=values.shape[0]
    )

    named_parameters = tuple(model.named_parameters())
    dense_by_name = {
        name: parameter.detach().clone().requires_grad_()
        for name, parameter in named_parameters
    }
    dense_parameters = [dense_by_name[name] for name, _ in named_parameters]
    first_weights = [dense_by_name[f"conv1.lins.{index}.weight"] for index in range(K)]
    first_bias = dense_by_name["conv1.bias"]
    second_weights = [dense_by_name[f"conv2.lins.{index}.weight"] for index in range(K)]
    second_bias = dense_by_name["conv2.bias"]
    sparse_output = model(sparse_x, edge_index, edge_weight)
    dense_output = dense_two_layer_chebnet(
        dense_x,
        scaled_laplacian,
        first_weights=first_weights,
        first_bias=first_bias,
        second_weights=second_weights,
        second_bias=second_bias,
    )
    torch.testing.assert_close(sparse_output, dense_output, rtol=1e-11, atol=1e-11)

    sparse_gradients = torch.autograd.grad(
        _loss(sparse_output), (sparse_x, *model.parameters())
    )
    dense_gradients = torch.autograd.grad(
        _loss(dense_output), (dense_x, *dense_parameters)
    )
    for observed, expected in zip(sparse_gradients, dense_gradients):
        torch.testing.assert_close(observed, expected, rtol=1e-10, atol=1e-10)


def test_dense_oracle_rejects_nonreciprocal_graph_semantics():
    edge_index = torch.tensor([[0], [1]], dtype=torch.long)
    edge_weight = torch.tensor([1.0], dtype=torch.float64)
    with pytest.raises(ValueError, match="exactly reciprocal"):
        dense_scaled_symmetric_laplacian(edge_index, edge_weight, num_nodes=2)


def test_chebnet_resource_count_and_task_head_are_exact():
    model = ChebNet(7, 11, 1, K=5, dropout=0.25)
    expected_parameters = 5 * 7 * 11 + 11 + 5 * 11 * 1 + 1
    count = model.resource_count()
    assert count.trainable_parameters == expected_parameters
    assert count.trainable_parameters == sum(p.numel() for p in model.parameters())
    assert count.feature_matrix_spmvs_per_forward == 8
    assert model.conv2.out_channels == 1


@pytest.mark.parametrize("dataset", tuple(DATASET_REGISTRY))
@pytest.mark.parametrize("K", (1, 3, 5))
def test_resource_formula_for_every_official_head(dataset, K):
    spec = DATASET_REGISTRY[dataset]
    hidden = 11
    model = ChebNet.for_official_dataset(
        dataset,
        in_channels=spec.feature_count,
        hidden_channels=hidden,
        K=K,
        dropout=0.0,
    )
    expected_parameters = (
        K * spec.feature_count * hidden
        + hidden
        + K * hidden * spec.output_logits
        + spec.output_logits
    )
    count = model.resource_count()
    assert count.trainable_parameters == expected_parameters
    assert count.feature_matrix_spmvs_per_forward == 2 * (K - 1)
    assert len(model.conv1.lins) - 1 + len(model.conv2.lins) - 1 == 2 * (K - 1)


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


def test_installed_pyg_release_source_and_license_are_exactly_pinned():
    distribution = importlib.metadata.distribution("torch-geometric")
    assert distribution.version == PYG_VERSION
    assert distribution.metadata["License-Expression"] == "MIT"

    source_path = inspect.getsourcefile(ChebConv)
    assert source_path is not None
    with open(source_path, "rb") as handle:
        assert hashlib.sha256(handle.read()).hexdigest() == PYG_CHEB_CONV_SHA256

    license_files = [
        file
        for file in distribution.files or ()
        if str(file).replace("\\", "/").endswith(".dist-info/licenses/LICENSE")
    ]
    assert len(license_files) == 1
    license_path = distribution.locate_file(license_files[0])
    with open(license_path, "rb") as handle:
        assert hashlib.sha256(handle.read()).hexdigest() == PYG_LICENSE_SHA256


def test_preserved_license_matches_installed_wheel():
    distribution = importlib.metadata.distribution("torch-geometric")
    wheel_license = next(
        distribution.locate_file(file)
        for file in distribution.files or ()
        if str(file).replace("\\", "/").endswith(".dist-info/licenses/LICENSE")
    )
    repository_license = (
        Path(__file__).parents[1]
        / "licenses"
        / "third_party"
        / "pytorch_geometric_MIT.txt"
    )
    assert repository_license.read_bytes() == wheel_license.read_bytes()
