"""Deterministic fixture-matrix completion for the Gate-A contract.

This module supplements the focused theorem tests.  It deliberately keeps the
graph and root registries explicit so a report can audit coverage rather than
infer it from a passing test count.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gbdn import (  # noqa: E402
    ChebyshevBasis,
    blaschke_product_cheb_coeffs,
    dense_adjoint_tight_synthesis,
    dense_apply_tight_analysis,
    dense_chebyshev_operator,
    dense_exact_blaschke_operator,
    dense_exact_blaschke_symbol,
    dense_tight_analysis_matrix,
    normalized_laplacian,
)


SCALAR_TOL = 5e-12
EXACT_TOL = 1e-10
SPARSE_TOL = 1e-8
DEPTHS = (1, 2, 4, 8, 16)


def _undirected_edges(
    pairs: list[tuple[int, int, float]],
) -> tuple[torch.Tensor, torch.Tensor]:
    directed: list[tuple[int, int]] = []
    weights: list[float] = []
    for source, target, weight in pairs:
        directed.extend(((source, target), (target, source)))
        weights.extend((weight, weight))
    edge_index = torch.tensor(directed, dtype=torch.long).t().contiguous()
    edge_weight = torch.tensor(weights, dtype=torch.float64)
    return edge_index, edge_weight


def _path(num_nodes: int) -> tuple[torch.Tensor, torch.Tensor]:
    return _undirected_edges(
        [(node, node + 1, 1.0) for node in range(num_nodes - 1)]
    )


def _cycle(num_nodes: int) -> tuple[torch.Tensor, torch.Tensor]:
    return _undirected_edges(
        [(node, (node + 1) % num_nodes, 1.0) for node in range(num_nodes)]
    )


def _grid(rows: int = 2, columns: int = 4) -> tuple[torch.Tensor, torch.Tensor]:
    pairs: list[tuple[int, int, float]] = []
    for row in range(rows):
        for column in range(columns):
            node = row * columns + column
            if column + 1 < columns:
                pairs.append((node, node + 1, 1.0))
            if row + 1 < rows:
                pairs.append((node, node + columns, 1.0))
    return _undirected_edges(pairs)


def _star(num_nodes: int = 7) -> tuple[torch.Tensor, torch.Tensor]:
    return _undirected_edges([(0, node, 1.0) for node in range(1, num_nodes)])


def _complete(num_nodes: int = 5) -> tuple[torch.Tensor, torch.Tensor]:
    return _undirected_edges(
        [
            (source, target, 1.0)
            for source in range(num_nodes)
            for target in range(source + 1, num_nodes)
        ]
    )


def _disconnected() -> tuple[torch.Tensor, torch.Tensor]:
    # P3 union C3 plus one isolated vertex.
    return _undirected_edges(
        [
            (0, 1, 1.0),
            (1, 2, 1.0),
            (3, 4, 1.0),
            (4, 5, 1.0),
            (5, 3, 1.0),
        ]
    )


def _random_weighted() -> tuple[torch.Tensor, torch.Tensor]:
    # Frozen seed-1701 witness, stored explicitly to avoid RNG/version drift.
    return _undirected_edges(
        [
            (0, 1, 0.31),
            (0, 3, 1.47),
            (0, 6, 0.82),
            (1, 2, 1.13),
            (1, 5, 0.56),
            (2, 4, 1.91),
            (2, 7, 0.44),
            (3, 4, 0.73),
            (3, 7, 1.28),
            (4, 5, 1.62),
            (5, 6, 0.95),
            (6, 7, 1.36),
        ]
    )


GraphBuilder = Callable[[], tuple[torch.Tensor, torch.Tensor]]
GRAPH_FIXTURES: dict[str, tuple[int, GraphBuilder]] = {
    "path_5": (5, lambda: _path(5)),
    "path_8": (8, lambda: _path(8)),
    "cycle_even_6": (6, lambda: _cycle(6)),
    "cycle_odd_7": (7, lambda: _cycle(7)),
    "grid_2x4": (8, _grid),
    "star_7": (7, _star),
    "complete_5": (5, _complete),
    "disconnected_7": (7, _disconnected),
    "random_weighted_seed_1701": (8, _random_weighted),
}

ROOT_FIXTURES: dict[str, torch.Tensor] = {
    "real_interior": torch.tensor([0.35 + 0.0j], dtype=torch.complex128),
    "generic_complex": torch.tensor([0.22 + 0.17j], dtype=torch.complex128),
    "multi_root": torch.tensor(
        [0.18 + 0.11j, -0.27 + 0.08j, 0.09 - 0.21j],
        dtype=torch.complex128,
    ),
    "conjugate_pair": torch.tensor(
        [0.28 + 0.19j, 0.28 - 0.19j], dtype=torch.complex128
    ),
    "near_radius_cap": torch.tensor([0.949999 - 1e-4j], dtype=torch.complex128),
}


def _graph(name: str):
    num_nodes, builder = GRAPH_FIXTURES[name]
    edge_index, edge_weight = builder()
    token = normalized_laplacian(edge_index, edge_weight, num_nodes)
    return token.to_dense(), token, edge_index, edge_weight


def _root_bank(depth: int) -> list[torch.Tensor]:
    roots = list(ROOT_FIXTURES.values())
    return [roots[index % len(roots)] for index in range(depth)]


def _operators(laplacian: torch.Tensor, depth: int) -> list[torch.Tensor]:
    return [
        dense_exact_blaschke_operator(laplacian, roots)
        for roots in _root_bank(depth)
    ]


def test_ga00_asymmetric_directed_knn_input_is_rejected():
    """GA-00: a deterministic directed 1-NN-style graph triggers core rejection."""

    # Each vertex chooses one neighbor, but the resulting directed relation is
    # not reciprocal (for example, 2 -> 1 has no matching 1 -> 2 edge).
    edge_index = torch.tensor(
        [[0, 1, 2, 3, 4], [1, 0, 1, 2, 3]], dtype=torch.long
    )
    edge_weight = torch.ones(5, dtype=torch.float64)
    with pytest.raises(ValueError, match="symmetric"):
        normalized_laplacian(edge_index, edge_weight, num_nodes=5)


@pytest.mark.parametrize("root_name", ROOT_FIXTURES)
def test_ga02_declared_root_fixture_unit_modulus(root_name):
    """GA-02: every declared deterministic root family is an exact all-pass."""

    eigenvalues = torch.linspace(-5.0, 5.0, 5001, dtype=torch.float64)
    symbol = dense_exact_blaschke_symbol(eigenvalues, ROOT_FIXTURES[root_name])
    assert float((symbol.abs() - 1.0).abs().max().item()) < SCALAR_TOL


@pytest.mark.parametrize("fixture", GRAPH_FIXTURES)
@pytest.mark.parametrize("root_name", ROOT_FIXTURES)
def test_ga03_ga04_full_graph_fixture_matrix(fixture, root_name):
    """GA-03/04: exact factor and complementary split pass every graph fixture."""

    laplacian = _graph(fixture)[0]
    roots = ROOT_FIXTURES[root_name]
    operator = dense_exact_blaschke_operator(laplacian, roots)
    identity = torch.eye(laplacian.shape[0], dtype=torch.complex128)
    left = operator.mH @ operator
    right = operator @ operator.mH
    assert float(torch.linalg.matrix_norm(left - identity, ord=2).item()) < EXACT_TOL
    assert float(torch.linalg.matrix_norm(right - identity, ord=2).item()) < EXACT_TOL

    residual = 0.5 * (identity - operator)
    carry = 0.5 * (identity + operator)
    frame = residual.mH @ residual + carry.mH @ carry
    assert float(torch.linalg.matrix_norm(frame - identity, ord=2).item()) < EXACT_TOL

    generator = torch.Generator().manual_seed(3040 + laplacian.shape[0])
    for feature_count in (1, 3):
        signal = torch.randn(
            laplacian.shape[0],
            feature_count,
            dtype=torch.complex128,
            generator=generator,
        )
        split_energy = (residual @ signal).abs().square().sum()
        split_energy = split_energy + (carry @ signal).abs().square().sum()
        relative = (split_energy - signal.abs().square().sum()).abs()
        relative = relative / signal.abs().square().sum()
        assert float(relative.item()) < EXACT_TOL


@pytest.mark.parametrize("fixture", GRAPH_FIXTURES)
def test_ga05_partition_on_every_fixture_spectrum(fixture):
    """GA-05: the multilevel partition holds at every fixture eigenvalue."""

    eigenvalues = torch.linalg.eigvalsh(_graph(fixture)[0])
    carry = torch.ones_like(eigenvalues, dtype=torch.complex128)
    residuals: list[torch.Tensor] = []
    for roots in _root_bank(16):
        symbol = dense_exact_blaschke_symbol(eigenvalues, roots)
        residuals.append(0.5 * (1.0 - symbol) * carry)
        carry = 0.5 * (1.0 + symbol) * carry
    partition = sum(value.abs().square() for value in residuals)
    partition = partition + carry.abs().square()
    assert float((partition - 1.0).abs().max().item()) < SCALAR_TOL


@pytest.mark.parametrize("fixture", GRAPH_FIXTURES)
@pytest.mark.parametrize("root_name", ROOT_FIXTURES)
@pytest.mark.parametrize("depth", DEPTHS)
def test_ga06_ga07_ga09_full_graph_depth_root_matrix(fixture, root_name, depth):
    """GA-06/07/09: exercise every graph, depth, and declared root family."""

    laplacian = _graph(fixture)[0]
    roots = ROOT_FIXTURES[root_name]
    operators = [
        dense_exact_blaschke_operator(laplacian, roots) for _ in range(depth)
    ]
    analysis = dense_tight_analysis_matrix(operators)
    identity = torch.eye(laplacian.shape[0], dtype=torch.complex128)
    defect = torch.linalg.matrix_norm(analysis.mH @ analysis - identity, ord=2)
    singular_values = torch.linalg.svdvals(analysis)
    assert float(defect.item()) < EXACT_TOL
    assert float((singular_values - 1.0).abs().max().item()) < EXACT_TOL
    assert abs(float((singular_values.max() / singular_values.min()).item()) - 1.0) < EXACT_TOL

    generator = torch.Generator().manual_seed(67090 + 100 * depth + laplacian.shape[0])
    signal = torch.randn(
        laplacian.shape[0], 2, dtype=torch.complex128, generator=generator
    )
    components = dense_apply_tight_analysis(signal, operators)
    reconstructed = dense_adjoint_tight_synthesis(components, operators)
    stacked = torch.cat(components, dim=0)
    assert torch.allclose(reconstructed, analysis.mH @ stacked, atol=1e-12, rtol=1e-12)
    relative = (reconstructed - signal).norm() / signal.norm()
    assert float(relative.item()) < EXACT_TOL


@pytest.mark.parametrize(
    ("fixture", "degree", "root_name"),
    [
        ("grid_2x4", 16, "conjugate_pair"),
        ("star_7", 32, "generic_complex"),
        ("random_weighted_seed_1701", 64, "multi_root"),
    ],
)
def test_ga19_sparse_dense_operator_extended_degree_matrix(
    fixture,
    degree,
    root_name,
):
    """GA-19: extend full-operator agreement through the high-order case."""

    laplacian, token, edge_index, edge_weight = _graph(fixture)
    roots = ROOT_FIXTURES[root_name]
    coefficients = blaschke_product_cheb_coeffs(
        roots, degree, torch.device("cpu"), convention="forward"
    )
    num_nodes = laplacian.shape[0]
    identity = torch.eye(num_nodes, dtype=coefficients.dtype)
    basis = ChebyshevBasis(degree)(
        identity,
        edge_index,
        edge_weight=edge_weight,
        num_nodes=num_nodes,
        laplacian=token,
    )
    sparse_operator = torch.sum(coefficients.view(-1, 1, 1) * basis, dim=0)
    dense_operator = dense_chebyshev_operator(laplacian, coefficients)
    numerator = torch.linalg.matrix_norm(sparse_operator - dense_operator, ord=2)
    denominator = torch.linalg.matrix_norm(dense_operator, ord=2).clamp_min(1e-30)
    assert float((numerator / denominator).item()) < SPARSE_TOL


def test_ga17_fixture_hashes_are_deterministic_and_noncolliding():
    """GA-17: the declared graph matrix has stable, graph-specific identities."""

    first = {name: _graph(name)[1].sha256 for name in GRAPH_FIXTURES}
    second = {name: _graph(name)[1].sha256 for name in GRAPH_FIXTURES}
    assert first == second
    assert len(set(first.values())) == len(first)
