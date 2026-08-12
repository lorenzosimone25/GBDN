"""Focused Gate-A contracts for graph policy, oracle, and public ordering."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gbdn import (  # noqa: E402
    ChebyshevBasis,
    GBDNProductSum,
    GBDNRelaxed,
    GBDNTight,
    TightAnalysisOutput,
    blaschke_product_cheb_coeffs,
    dense_adjoint_tight_synthesis,
    dense_apply_tight_analysis,
    dense_chebyshev_operator,
    dense_exact_blaschke_operator,
    dense_exact_blaschke_symbol,
    dense_tight_analysis_matrix,
    exact_blaschke_operator_from_eigendecomposition,
    normalized_laplacian,
    preprocess_reciprocal_mean,
    validate_adjacency,
    validate_self_adjoint_operator,
)
from gbdn.peel import (  # noqa: E402
    center_width_coeffs_for_mode,
    oracle_coeffs_for_mode,
    tight_peel_sequence,
)
from gbdn.synthetic import sphere_graph_data  # noqa: E402


EXACT_OPERATOR_TOL = 1e-10
SPARSE_OPERATOR_TOL = 1e-8


def _path_edges(n: int) -> tuple[torch.Tensor, torch.Tensor]:
    source = torch.arange(n - 1, dtype=torch.long)
    target = source + 1
    edge_index = torch.stack(
        [torch.cat([source, target]), torch.cat([target, source])]
    )
    return edge_index, torch.ones(edge_index.shape[1], dtype=torch.float64)


def _cycle_edges(n: int) -> tuple[torch.Tensor, torch.Tensor]:
    source = torch.arange(n, dtype=torch.long)
    target = (source + 1) % n
    edge_index = torch.stack(
        [torch.cat([source, target]), torch.cat([target, source])]
    )
    return edge_index, torch.ones(edge_index.shape[1], dtype=torch.float64)


def _complete_edges(n: int) -> tuple[torch.Tensor, torch.Tensor]:
    pairs = [(source, target) for source in range(n) for target in range(n) if source != target]
    edge_index = torch.tensor(pairs, dtype=torch.long).t().contiguous()
    return edge_index, torch.ones(edge_index.shape[1], dtype=torch.float64)


def _relative_operator_error(actual: torch.Tensor, expected: torch.Tensor) -> float:
    numerator = torch.linalg.matrix_norm(actual - expected, ord=2)
    denominator = torch.linalg.matrix_norm(expected, ord=2).clamp_min(1e-30)
    return float((numerator / denominator).item())


def _materialize_sparse_polynomial(
    edge_index: torch.Tensor,
    edge_weight: torch.Tensor,
    num_nodes: int,
    coefficients: torch.Tensor,
    basis_module: ChebyshevBasis | None = None,
) -> tuple[torch.Tensor, torch.Tensor]:
    laplacian = normalized_laplacian(
        edge_index,
        edge_weight,
        num_nodes,
        device=torch.device("cpu"),
    )
    identity = torch.eye(num_nodes, dtype=coefficients.dtype)
    if basis_module is None:
        basis_module = ChebyshevBasis(coefficients.numel() - 1)
    basis = basis_module(
        identity,
        edge_index,
        edge_weight=edge_weight,
        num_nodes=num_nodes,
        laplacian=laplacian,
    )
    operator = torch.sum(coefficients.view(-1, 1, 1) * basis, dim=0)
    return operator, laplacian


@pytest.mark.parametrize(
    ("edge_index", "edge_weight", "match"),
    [
        (
            torch.tensor([[0], [1]], dtype=torch.long),
            torch.tensor([1.0], dtype=torch.float64),
            "symmetric",
        ),
        (
            torch.tensor([[0, 1], [1, 0]], dtype=torch.long),
            torch.tensor([1.0, -0.5], dtype=torch.float64),
            "nonnegative",
        ),
        (
            torch.tensor([[0, 1], [1, 0]], dtype=torch.long),
            torch.tensor([1.0, float("nan")], dtype=torch.float64),
            "finite",
        ),
        (
            torch.tensor([[0, 1], [1, 0]], dtype=torch.long),
            torch.tensor([1.0, float("inf")], dtype=torch.float64),
            "finite",
        ),
        (
            torch.tensor([[0], [0]], dtype=torch.long),
            torch.tensor([1.0], dtype=torch.float64),
            "self-loops",
        ),
    ],
)
def test_ga00_core_rejects_invalid_adjacencies(edge_index, edge_weight, match):
    """GA-00: direct core input rejects directed, negative, and nonfinite data."""

    with pytest.raises(ValueError, match=match):
        validate_adjacency(edge_index, edge_weight, num_nodes=2)
    if match in {"nonnegative", "finite"}:
        with pytest.raises(ValueError, match=match):
            preprocess_reciprocal_mean(edge_index, edge_weight, num_nodes=2)


def test_ga00_core_rejects_invalid_self_adjoint_operators():
    """GA-00: precomputed operators cannot bypass finite/self-adjoint checks."""

    asymmetric = torch.tensor([[1.0, -1.0], [0.0, 1.0]], dtype=torch.float64)
    with pytest.raises(ValueError, match="self-adjoint"):
        validate_self_adjoint_operator(asymmetric)
    nonfinite = torch.eye(2, dtype=torch.float64)
    nonfinite[0, 0] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        validate_self_adjoint_operator(nonfinite)


@pytest.mark.parametrize("tolerance", (10.0, float("nan"), float("inf"), -1.0))
def test_ga00_public_graph_validators_do_not_expose_relaxation_knobs(tolerance):
    """GA-00: canonical public validators use fixed contract tolerances."""

    directed_edges = torch.tensor([[0], [1]], dtype=torch.long)
    directed_weights = torch.ones(1, dtype=torch.float64)
    with pytest.raises(TypeError, match="symmetry_atol"):
        validate_adjacency(
            directed_edges,
            directed_weights,
            num_nodes=2,
            symmetry_atol=tolerance,
        )

    asymmetric = torch.tensor([[0.0, 1.0], [0.0, 0.0]], dtype=torch.float64)
    with pytest.raises(TypeError, match="symmetry_atol"):
        validate_self_adjoint_operator(asymmetric, symmetry_atol=tolerance)

    out_of_range = torch.diag(torch.tensor([-4.0, 7.0], dtype=torch.float64))
    with pytest.raises(TypeError, match="spectral_atol"):
        validate_self_adjoint_operator(out_of_range, spectral_atol=tolerance)


def test_ga00_public_graph_validator_cannot_disable_spectrum_check():
    """GA-00: canonical validation always enforces normalized spectrum."""

    out_of_range = torch.diag(torch.tensor([-4.0, 7.0], dtype=torch.float64))
    with pytest.raises(TypeError, match="spectral_bounds"):
        validate_self_adjoint_operator(out_of_range, spectral_bounds=None)
    with pytest.raises(ValueError, match="outside"):
        validate_self_adjoint_operator(out_of_range)


def test_ga00_reciprocal_mean_policy_is_recorded_and_deterministic():
    """GA-00: reciprocal mean obeys duplicate/loop/isolate/hash conventions."""

    edge_index = torch.tensor(
        [[0, 0, 1, 1, 0, 3], [1, 1, 0, 2, 0, 3]],
        dtype=torch.long,
    )
    edge_weight = torch.tensor([1.0, 3.0, 2.0, 4.0, 0.5, 1.0], dtype=torch.float64)
    result = preprocess_reciprocal_mean(edge_index, edge_weight, num_nodes=5)

    expected = torch.zeros((5, 5), dtype=torch.float64)
    expected[0, 1] = expected[1, 0] = 3.0
    expected[1, 2] = expected[2, 1] = 2.0
    assert torch.equal(result.adjacency.to_dense(), expected)

    record = result.record
    assert record.policy == "reciprocal-mean"
    assert record.policy_version == 1
    assert record.formula == "A_sym=(A+A^T)/2"
    assert record.duplicate_policy == "sum-before-symmetrization"
    assert record.duplicate_directed_edge_count == 1
    assert record.removed_self_loop_count == 2
    assert record.removed_self_loop_weight == pytest.approx(1.5)
    assert record.isolated_vertex_count == 2
    assert record.missing_reverse_edge_weight == 0.0
    assert len(record.input_sha256) == len(record.output_sha256) == 64
    json.dumps(record.to_dict())

    dense_laplacian = result.laplacian.to_dense()
    assert torch.linalg.matrix_norm(dense_laplacian - dense_laplacian.mH, ord=2) < 1e-14
    eigenvalues = torch.linalg.eigvalsh(dense_laplacian)
    assert float(eigenvalues.min().item()) >= -1e-12
    assert float(eigenvalues.max().item()) <= 2.0 + 1e-12
    assert dense_laplacian[3, 3].item() == 1.0
    assert dense_laplacian[4, 4].item() == 1.0

    permutation = torch.tensor([5, 2, 0, 4, 1, 3])
    repeated = preprocess_reciprocal_mean(
        edge_index[:, permutation],
        edge_weight[permutation],
        num_nodes=5,
    )
    assert repeated.record.input_sha256 == record.input_sha256
    assert repeated.record.output_sha256 == record.output_sha256
    assert torch.equal(repeated.adjacency.to_dense(), expected)


def test_ga00_sphere_helper_routes_directed_knn_through_recorded_preprocessor():
    """GA-00: the canonical sphere helper cannot feed an asymmetric eigensolver."""

    result = sphere_graph_data(
        n_nodes=24,
        k_nn=3,
        idx_low=2,
        idx_high=15,
    )
    record = result["graph_preprocess_record"]
    assert record["policy"] == "reciprocal-mean"
    assert record["formula"] == "A_sym=(A+A^T)/2"
    adjacency = result["adjacency"].to_dense()
    assert torch.equal(adjacency, adjacency.mT)
    laplacian = result["laplacian"].to_dense()
    assert torch.linalg.matrix_norm(laplacian - laplacian.mT, ord=2) < 1e-14
    residual = torch.linalg.matrix_norm(
        laplacian @ result["evecs"]
        - result["evecs"] * result["evals"].unsqueeze(0),
        ord="fro",
    ) / torch.linalg.matrix_norm(laplacian, ord="fro")
    assert float(residual.item()) < 1e-10
    assert torch.equal(result["data"].edge_index, result["adjacency"].indices())
    assert torch.equal(result["data"].edge_weight, result["adjacency"].values())


def test_ga00_peel_diagnostics_require_token_and_quarantine_angular_oracle():
    """GA-00: peeling diagnostics cannot bypass tokens or misname angular anchors."""

    edge_index, edge_weight = _path_edges(5)
    laplacian = normalized_laplacian(edge_index, edge_weight, 5)
    eigenvalues = torch.linalg.eigvalsh(laplacian.to_dense())
    coefficients = center_width_coeffs_for_mode(
        eigenvalues,
        2,
        4,
        torch.device("cpu"),
        width=0.3,
    )
    signal = torch.randn(
        5,
        2,
        dtype=torch.complex128,
        generator=torch.Generator().manual_seed(42),
    )
    output = tight_peel_sequence(signal, laplacian, [coefficients], 4)
    assert len(output["hs"]) == 2
    with pytest.raises(TypeError, match="ValidatedLaplacian"):
        tight_peel_sequence(signal, laplacian.to_dense(), [coefficients], 4)
    with pytest.raises(RuntimeError, match="quarantined"):
        oracle_coeffs_for_mode(
            eigenvalues,
            2,
            4,
            torch.device("cpu"),
        )


def test_ga03_ga04_dense_exact_unitarity_and_one_level_split():
    """GA-03/04: independent dense factor is two-sided unitary and tightly split."""

    num_nodes = 9
    edge_index, edge_weight = _path_edges(num_nodes)
    laplacian = normalized_laplacian(edge_index, edge_weight, num_nodes).to_dense()
    roots = torch.tensor([0.4 + 0.2j, -0.3 + 0.25j], dtype=torch.complex128)
    operator = dense_exact_blaschke_operator(laplacian, roots)
    identity = torch.eye(num_nodes, dtype=torch.complex128)

    left = torch.linalg.matrix_norm(operator.mH @ operator - identity, ord=2)
    right = torch.linalg.matrix_norm(operator @ operator.mH - identity, ord=2)
    assert float(left.item()) < EXACT_OPERATOR_TOL
    assert float(right.item()) < EXACT_OPERATOR_TOL

    minus = 0.5 * (identity - operator)
    plus = 0.5 * (identity + operator)
    split_error = torch.linalg.matrix_norm(
        minus.mH @ minus + plus.mH @ plus - identity,
        ord=2,
    )
    assert float(split_error.item()) < EXACT_OPERATOR_TOL

    generator = torch.Generator().manual_seed(3004)
    signal = torch.randn(num_nodes, 4, dtype=torch.complex128, generator=generator)
    channel_energy = (minus @ signal).abs().square().sum() + (plus @ signal).abs().square().sum()
    relative = (channel_energy - signal.abs().square().sum()).abs() / signal.abs().square().sum()
    assert float(relative.item()) < EXACT_OPERATOR_TOL


def test_ga08_additive_reconstruction_exact_approximate_and_nonunitary():
    """GA-08: shared half-channels telescope without requiring unitarity."""

    num_nodes = 7
    edge_index, edge_weight = _path_edges(num_nodes)
    laplacian = normalized_laplacian(edge_index, edge_weight, num_nodes).to_dense()
    exact = dense_exact_blaschke_operator(
        laplacian,
        torch.tensor([0.3 + 0.15j], dtype=torch.complex128),
    )
    approximate = dense_chebyshev_operator(
        laplacian,
        torch.tensor([0.7 + 0.1j, -0.25 + 0.2j, 0.05 - 0.1j], dtype=torch.complex128),
    )
    nonunitary = torch.diag(
        torch.linspace(0.2, 1.4, num_nodes, dtype=torch.float64)
    ).to(torch.complex128)
    operators = [exact, approximate, nonunitary]
    generator = torch.Generator().manual_seed(800)
    signal = torch.randn(num_nodes, 3, dtype=torch.complex128, generator=generator)
    components = dense_apply_tight_analysis(signal, operators)
    analysis_matrix = dense_tight_analysis_matrix(operators)
    assert torch.allclose(
        analysis_matrix @ signal,
        torch.cat(components, dim=0),
        atol=1e-12,
        rtol=1e-12,
    )
    output = TightAnalysisOutput(
        bands=list(components[:-1]),
        final_carry=components[-1],
        roots=[torch.empty(0, dtype=torch.complex128) for _ in operators],
    )

    relative = (output.additive_reconstruction() - signal).norm() / signal.norm()
    assert float(relative.item()) < 1e-12
    one_level = dense_apply_tight_analysis(signal, [nonunitary])
    assert torch.allclose(one_level[0] + one_level[1], signal, atol=1e-12, rtol=1e-12)


def test_ga10_public_tight_values_order_readout_and_synthesis_match_dense_oracle(
    record_property,
):
    """GA-10: public coefficients equal an independent residual-first assembly."""

    num_nodes, depth, degree, hidden = 6, 3, 5, 2
    edge_index, edge_weight = _path_edges(num_nodes)
    laplacian = normalized_laplacian(edge_index, edge_weight, num_nodes)
    model = GBDNTight(
        in_channels=2,
        hidden_channels=hidden,
        out_channels=2,
        num_layers=depth,
        K=degree,
        num_roots=1,
    ).double()
    model.eval()
    with torch.no_grad():
        model.lifting.weight.copy_(
            torch.tensor(
                [
                    [0.2, -0.1],
                    [0.4, 0.3],
                    [-0.25, 0.5],
                    [0.15, -0.35],
                ],
                dtype=torch.float64,
            )
        )
        model.lifting.bias.copy_(
            torch.tensor([0.1, -0.2, 0.3, -0.4], dtype=torch.float64)
        )
        for index, layer in enumerate(model.layers):
            layer.root_params.copy_(
                torch.tensor(
                    [[-0.9 + 0.25 * index, 0.2 + 0.55 * index]],
                    dtype=torch.float64,
                )
            )
        readout_width = hidden * (depth + 1) * 2
        model.readout.weight.copy_(
            torch.arange(
                1,
                2 * readout_width + 1,
                dtype=torch.float64,
            ).reshape(2, readout_width)
            / 23.0
        )
        model.readout.bias.copy_(torch.tensor([0.2, -0.3], dtype=torch.float64))

    x = torch.tensor(
        [
            [0.3, -0.7],
            [1.2, 0.4],
            [-0.5, 0.8],
            [0.9, -1.1],
            [0.2, 0.6],
            [-0.8, -0.1],
        ],
        dtype=torch.float64,
    )
    lifted_real = x @ model.lifting.weight.detach().mT + model.lifting.bias.detach()
    lifted = torch.complex(lifted_real[:, :hidden], lifted_real[:, hidden:])
    public = model.analyze_complex(
        lifted,
        edge_index,
        edge_weight=edge_weight,
        laplacian=laplacian,
    )

    operators = []
    for roots in public.roots:
        coefficients = blaschke_product_cheb_coeffs(
            roots,
            degree,
            torch.device("cpu"),
            convention="forward",
        )
        operators.append(
            dense_chebyshev_operator(laplacian.to_dense(), coefficients)
        )
    independent = dense_apply_tight_analysis(lifted, operators)
    assert public.component_names == ("r_0", "r_1", "r_2", "h_D")
    component_errors = []
    for observed, expected in zip(public.components, independent, strict=True):
        relative = (observed - expected).norm() / expected.norm().clamp_min(1e-30)
        component_errors.append(float(relative.item()))
        assert float(relative.item()) < SPARSE_OPERATOR_TOL

    independently_concatenated = torch.cat(independent, dim=-1)
    tuple_error = (
        (public.concatenate() - independently_concatenated).norm()
        / independently_concatenated.norm().clamp_min(1e-30)
    )
    assert float(tuple_error.item()) < SPARSE_OPERATOR_TOL
    carry_first = torch.cat((independent[-1], *independent[:-1]), dim=-1)
    permutation_separation = (
        (public.concatenate() - carry_first).norm()
        / independently_concatenated.norm().clamp_min(1e-30)
    )
    assert float(permutation_separation.item()) > 1e-3

    independent_features = torch.cat(
        [independently_concatenated.real, independently_concatenated.imag],
        dim=-1,
    )
    independent_logits = (
        independent_features @ model.readout.weight.detach().mT
        + model.readout.bias.detach()
    )
    public_logits, _ = model(x, edge_index, edge_weight=edge_weight)
    readout_error = (
        (public_logits - independent_logits).norm()
        / independent_logits.norm().clamp_min(1e-30)
    )
    assert float(readout_error.item()) < SPARSE_OPERATOR_TOL

    public_synthesis = model.synthesize(
        public,
        edge_index,
        edge_weight=edge_weight,
        laplacian=laplacian,
    )
    independent_synthesis = dense_adjoint_tight_synthesis(
        independent,
        operators,
    )
    synthesis_error = (
        (public_synthesis - independent_synthesis).norm()
        / independent_synthesis.norm().clamp_min(1e-30)
    )
    assert float(synthesis_error.item()) < SPARSE_OPERATOR_TOL

    record_property(
        "gate_a_metrics",
        json.dumps(
            {
                "gate_id": "GA-10",
                "realization_tag": "chebyshev-K",
                "graph_hash": laplacian.sha256,
                "roots": [
                    [
                        [
                            float(value.detach().real),
                            float(value.detach().imag),
                        ]
                        for value in roots
                    ]
                    for roots in public.roots
                ],
                "depth": depth,
                "degree": degree,
                "component_order": list(public.component_names),
                "maximum_component_relative_residual": max(component_errors),
                "tuple_relative_residual": float(tuple_error.item()),
                "permuted_tuple_relative_separation": float(
                    permutation_separation.item()
                ),
                "readout_relative_residual": float(readout_error.item()),
                "synthesis_relative_residual": float(synthesis_error.item()),
                "tolerance": SPARSE_OPERATOR_TOL,
                "dtype": str(lifted.dtype),
                "device": str(lifted.device),
            },
            sort_keys=True,
        ),
    )


def test_ga16_dense_oracle_is_invariant_to_repeated_eigenspace_basis():
    """GA-16: a complete-graph repeated eigenspace admits arbitrary basis rotation."""

    num_nodes = 6
    edge_index, edge_weight = _complete_edges(num_nodes)
    laplacian = normalized_laplacian(edge_index, edge_weight, num_nodes).to_dense()
    eigenvalues, eigenvectors = torch.linalg.eigh(laplacian)
    roots = torch.tensor([0.25 + 0.2j, -0.15 + 0.1j], dtype=torch.complex128)

    generator = torch.Generator().manual_seed(1616)
    rotation_block, _ = torch.linalg.qr(
        torch.randn(num_nodes - 1, num_nodes - 1, dtype=torch.float64, generator=generator)
    )
    rotation = torch.eye(num_nodes, dtype=torch.float64)
    rotation[1:, 1:] = rotation_block
    rotated_vectors = eigenvectors @ rotation

    canonical = exact_blaschke_operator_from_eigendecomposition(
        eigenvalues,
        eigenvectors,
        roots,
    )
    rotated = exact_blaschke_operator_from_eigendecomposition(
        eigenvalues,
        rotated_vectors,
        roots,
    )
    assert _relative_operator_error(rotated, canonical) < EXACT_OPERATOR_TOL

    symbol = dense_exact_blaschke_symbol(eigenvalues, roots)
    assert float((symbol[1:] - symbol[1]).abs().max().item()) < EXACT_OPERATOR_TOL


def test_ga17_equal_sized_graphs_do_not_share_operator_state():
    """GA-17: one basis module rebuilds distinct same-size graph operators safely."""

    num_nodes = 10
    path_edges, path_weights = _path_edges(num_nodes)
    cycle_edges, cycle_weights = _cycle_edges(num_nodes)
    coefficients = torch.tensor(
        [0.2 + 0.1j, -0.35 + 0.05j, 0.1 - 0.2j, 0.04 + 0.03j],
        dtype=torch.complex128,
    )
    shared_basis = ChebyshevBasis(coefficients.numel() - 1)
    path_operator, _ = _materialize_sparse_polynomial(
        path_edges,
        path_weights,
        num_nodes,
        coefficients,
        shared_basis,
    )
    cycle_operator, _ = _materialize_sparse_polynomial(
        cycle_edges,
        cycle_weights,
        num_nodes,
        coefficients,
        shared_basis,
    )
    rebuilt_cycle, _ = _materialize_sparse_polynomial(
        cycle_edges,
        cycle_weights,
        num_nodes,
        coefficients,
        ChebyshevBasis(coefficients.numel() - 1),
    )

    assert not torch.allclose(path_operator, cycle_operator)
    assert torch.allclose(cycle_operator, rebuilt_cycle, atol=1e-12, rtol=0)


@pytest.mark.parametrize(
    ("graph", "num_nodes", "degree", "roots"),
    [
        ("path", 8, 4, torch.tensor([0.2 + 0.1j], dtype=torch.complex128)),
        (
            "cycle",
            9,
            8,
            torch.tensor([0.2 + 0.1j, -0.35 + 0.2j], dtype=torch.complex128),
        ),
    ],
)
def test_ga19_sparse_polynomial_matches_independent_dense_full_operator(
    graph,
    num_nodes,
    degree,
    roots,
):
    """GA-19: compare full operators, never one sampled feature vector."""

    edge_index, edge_weight = (
        _path_edges(num_nodes) if graph == "path" else _cycle_edges(num_nodes)
    )
    coefficients = blaschke_product_cheb_coeffs(
        roots,
        degree,
        torch.device("cpu"),
        convention="forward",
    )
    sparse_operator, sparse_laplacian = _materialize_sparse_polynomial(
        edge_index,
        edge_weight,
        num_nodes,
        coefficients,
    )
    dense_operator = dense_chebyshev_operator(
        sparse_laplacian.to_dense(),
        coefficients,
    )
    assert _relative_operator_error(sparse_operator, dense_operator) < SPARSE_OPERATOR_TOL


@pytest.mark.parametrize("model_class", [GBDNTight, GBDNProductSum, GBDNRelaxed])
def test_ga35_optimizer_sees_every_parameter_before_first_forward(model_class):
    """GA-35: canonical variants create no trainable parameter lazily."""

    model = model_class(
        in_channels=3,
        hidden_channels=4,
        out_channels=2,
        num_layers=2,
        K=3,
    )
    before = {name: id(parameter) for name, parameter in model.named_parameters()}
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    optimizer_ids = {
        id(parameter)
        for group in optimizer.param_groups
        for parameter in group["params"]
    }
    assert optimizer_ids == set(before.values())

    edge_index, edge_weight = _path_edges(6)
    generator = torch.Generator().manual_seed(3500)
    features = torch.randn(6, 3, generator=generator)
    predictions, _ = model(features, edge_index, edge_weight=edge_weight.float())
    predictions.square().mean().backward()

    after = {name: id(parameter) for name, parameter in model.named_parameters()}
    assert after == before
    assert optimizer_ids == set(after.values())
