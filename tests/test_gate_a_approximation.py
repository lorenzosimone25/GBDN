"""Gate-A tests for finite realization, expressivity, stability, and cost."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gbdn import (  # noqa: E402
    ChebyshevBasis,
    GBDNTight,
    TightAnalysisOutput,
    blaschke_cayley_symbol,
    blaschke_product_cheb_coeffs,
    dct_synthesis,
    dense_chebyshev_operator,
    dense_exact_blaschke_operator,
    dense_tight_analysis_matrix,
    evaluate_chebyshev,
    mapped_zero_pole,
    normalized_laplacian,
)
from gbdn.diagnostics import (  # noqa: E402
    chebyshev_interpolation_error_bound,
    fixed_root_perturbation_constant,
    multilevel_frame_bound,
    product_sum_evaluation_matrix,
    target_pole_diagnostics,
)


EXACT_TOL = 1e-10
SPARSE_TOL = 1e-8


def _path_edges(
    n: int,
    weights: torch.Tensor | None = None,
) -> tuple[torch.Tensor, torch.Tensor]:
    source = torch.arange(n - 1, dtype=torch.long)
    target = source + 1
    edge_index = torch.stack(
        [torch.cat([source, target]), torch.cat([target, source])]
    )
    if weights is None:
        directed_weights = torch.ones(edge_index.shape[1], dtype=torch.float64)
    else:
        directed_weights = torch.cat([weights, weights]).to(torch.float64)
    return edge_index, directed_weights


def _path_laplacian(n: int, weights: torch.Tensor | None = None) -> torch.Tensor:
    edge_index, edge_weight = _path_edges(n, weights)
    return normalized_laplacian(edge_index, edge_weight, n).to_dense()


def _operator_error(actual: torch.Tensor, expected: torch.Tensor) -> float:
    numerator = torch.linalg.matrix_norm(actual - expected, ord=2)
    denominator = torch.linalg.matrix_norm(expected, ord=2).clamp_min(1e-30)
    return float((numerator / denominator).item())


def test_ga18_first_kind_coefficients_nodes_and_dense_recurrence():
    """GA-18: node interpolation, c0 convention, and recurrence agree."""

    degree = 12
    nodes = torch.cos(
        torch.pi
        * (torch.arange(degree + 1, dtype=torch.float64) + 0.5)
        / (degree + 1)
    ) + 1.0
    generator = torch.Generator().manual_seed(1800)
    expected_coefficients = torch.randn(
        degree + 1,
        dtype=torch.complex128,
        generator=generator,
    )
    samples = evaluate_chebyshev(expected_coefficients, nodes)
    recovered_coefficients = dct_synthesis(samples, degree)
    assert torch.allclose(
        recovered_coefficients,
        expected_coefficients,
        atol=EXACT_TOL,
        rtol=EXACT_TOL,
    )
    assert torch.allclose(
        evaluate_chebyshev(recovered_coefficients, nodes),
        samples,
        atol=EXACT_TOL,
        rtol=EXACT_TOL,
    )

    laplacian = _path_laplacian(7)
    dense = dense_chebyshev_operator(laplacian, recovered_coefficients)
    eigenvalues, eigenvectors = torch.linalg.eigh(laplacian)
    spectral = (
        eigenvectors.to(torch.complex128)
        * evaluate_chebyshev(recovered_coefficients, eigenvalues).unsqueeze(0)
    ) @ eigenvectors.to(torch.complex128).mH
    assert _operator_error(dense, spectral) < SPARSE_TOL


@pytest.mark.parametrize("degree", [4, 8, 16, 32])
def test_ga20_exact_graph_error_matches_spectral_max_and_analytic_bound(degree):
    """GA-20: true operator error and interval error obey the analytic bound."""

    roots = torch.tensor([0.2 + 0.1j], dtype=torch.complex128)
    laplacian = _path_laplacian(9)
    eigenvalues, _ = torch.linalg.eigh(laplacian)
    exact = dense_exact_blaschke_operator(laplacian, roots)
    coefficients = blaschke_product_cheb_coeffs(
        roots, degree, torch.device("cpu"), convention="forward"
    )
    approximate = dense_chebyshev_operator(laplacian, coefficients)
    operator_error = float(torch.linalg.matrix_norm(exact - approximate, ord=2).item())
    spectral_error = float(
        (
            blaschke_cayley_symbol(eigenvalues, roots)
            - evaluate_chebyshev(coefficients, eigenvalues)
        )
        .abs()
        .max()
        .item()
    )
    assert abs(operator_error - spectral_error) < EXACT_TOL

    interval = torch.linspace(0.0, 2.0, 20001, dtype=torch.float64)
    interval_error = float(
        (
            blaschke_cayley_symbol(interval, roots)
            - evaluate_chebyshev(coefficients, interval)
        )
        .abs()
        .max()
        .item()
    )
    bound = chebyshev_interpolation_error_bound(roots, degree, rho=1.5)
    assert spectral_error <= interval_error + 1e-12
    assert interval_error <= bound + 1e-10 * max(1.0, bound)


def test_ga21_one_level_frame_spectrum_obeys_true_operator_error_bound():
    """GA-21: measured frame spectrum lies inside its epsilon envelope."""

    roots = torch.tensor([0.35 + 0.15j], dtype=torch.complex128)
    degree = 8
    laplacian = _path_laplacian(8)
    exact = dense_exact_blaschke_operator(laplacian, roots)
    coefficients = blaschke_product_cheb_coeffs(
        roots, degree, torch.device("cpu"), convention="forward"
    )
    approximate = dense_chebyshev_operator(laplacian, coefficients)
    epsilon = float(torch.linalg.matrix_norm(approximate - exact, ord=2).item())
    identity = torch.eye(laplacian.shape[0], dtype=torch.complex128)
    minus = 0.5 * (identity - approximate)
    plus = 0.5 * (identity + approximate)
    frame = minus.mH @ minus + plus.mH @ plus
    eigenvalues = torch.linalg.eigvalsh(frame)
    defect = float(torch.linalg.matrix_norm(frame - identity, ord=2).item())
    predicted = epsilon + 0.5 * epsilon * epsilon
    slack = 1e-10 * max(1.0, predicted)
    assert defect <= predicted + slack
    assert float(eigenvalues.min().item()) >= 1.0 - predicted - slack
    assert float(eigenvalues.max().item()) <= 1.0 + predicted + slack


@pytest.mark.parametrize("depth", [1, 2, 4, 8, 16])
def test_ga22_multilevel_frame_defect_obeys_heterogeneous_delta(depth):
    """GA-22: observed multilevel defect is bounded at every required depth."""

    laplacian = _path_laplacian(6)
    root_bank = [
        torch.tensor([0.2 + 0.1j], dtype=torch.complex128),
        torch.tensor([-0.15 + 0.08j, 0.1 - 0.12j], dtype=torch.complex128),
        torch.tensor([0.3 - 0.05j], dtype=torch.complex128),
    ]
    degrees = [8, 12, 16]
    exact_operators: list[torch.Tensor] = []
    approximate_operators: list[torch.Tensor] = []
    errors: list[float] = []
    for level in range(depth):
        roots = root_bank[level % len(root_bank)]
        degree = degrees[level % len(degrees)]
        exact = dense_exact_blaschke_operator(laplacian, roots)
        coefficients = blaschke_product_cheb_coeffs(
            roots, degree, torch.device("cpu"), convention="forward"
        )
        approximate = dense_chebyshev_operator(laplacian, coefficients)
        exact_operators.append(exact)
        approximate_operators.append(approximate)
        errors.append(float(torch.linalg.matrix_norm(approximate - exact, ord=2).item()))

    del exact_operators
    analysis = dense_tight_analysis_matrix(approximate_operators)
    identity = torch.eye(laplacian.shape[0], dtype=torch.complex128)
    frame = analysis.mH @ analysis
    observed = float(torch.linalg.matrix_norm(frame - identity, ord=2).item())
    diagnostic = multilevel_frame_bound(errors)
    slack = 1e-10 * max(1.0, diagnostic.delta)
    assert observed <= diagnostic.delta + slack
    frame_eigenvalues = torch.linalg.eigvalsh(frame)
    assert float(frame_eigenvalues.max().item()) <= 1.0 + diagnostic.delta + slack
    if diagnostic.positive_lower_bound:
        assert float(frame_eigenvalues.min().item()) >= 1.0 - diagnostic.delta - slack
    adjoint_reconstruction_error = torch.linalg.matrix_norm(frame - identity, ord=2)
    assert float(adjoint_reconstruction_error.item()) <= diagnostic.delta + slack


def test_ga24_target_pole_diagnostics_emit_all_descriptive_quantities():
    """GA-24: radius, angle, pole geometry, margin, and ellipse are emitted."""

    roots = torch.tensor(
        [0.2 + 0.1j, -0.3 + 0.15j, 0.1 - 0.25j],
        dtype=torch.complex128,
    )
    rows = target_pole_diagnostics(roots)
    assert len(rows) == len(roots)
    required = {
        "root_radius",
        "root_angle",
        "mapped_zero_real",
        "mapped_zero_imag",
        "mapped_pole_real",
        "mapped_pole_imag",
        "pole_margin_to_interval",
        "bernstein_parameter",
    }
    for row in rows:
        assert set(row) == required
        assert all(torch.isfinite(torch.tensor(value)) for value in row.values())
        assert row["root_radius"] < 1.0
        assert row["mapped_zero_imag"] > 0.0
        assert row["mapped_pole_imag"] < 0.0
        assert row["pole_margin_to_interval"] > 0.0
        assert row["bernstein_parameter"] > 1.0


def test_ga25_product_sum_nonzero_roots_interpolate_with_reported_conditioning():
    """GA-25: nonzero admissible factors give a full-rank, stable witness."""

    eigenvalues = torch.tensor([0.0, 0.2, 0.7, 1.4, 2.0], dtype=torch.float64)
    angles = torch.tensor([0.1, 0.7, 1.3, 2.0], dtype=torch.float64)
    roots = torch.polar(torch.full_like(angles, 1e-3), angles).to(torch.complex128)
    matrix = product_sum_evaluation_matrix(eigenvalues, roots)
    singular_values = torch.linalg.svdvals(matrix)
    condition = float((singular_values.max() / singular_values.min()).item())
    assert torch.linalg.matrix_rank(matrix).item() == len(eigenvalues)
    assert condition <= 1e8

    target = torch.tensor(
        [0.3 + 0.1j, -0.2 + 0.4j, 1.1 - 0.3j, 0.0 + 0.2j, -0.7 - 0.1j],
        dtype=torch.complex128,
    )
    coefficients = torch.linalg.solve(matrix, target)
    relative = (matrix @ coefficients - target).norm() / target.norm()
    assert float(relative.item()) < EXACT_TOL


def test_ga26_scalar_multiplier_cannot_fit_orientations_in_repeated_eigenspace():
    """GA-26: one repeated-eigenvalue scalar cannot realize +1 and -1."""

    design = torch.ones((2, 1), dtype=torch.complex128)
    incompatible_target = torch.tensor([1.0, -1.0], dtype=torch.complex128)
    solution = torch.linalg.lstsq(design, incompatible_target).solution
    residual = (design @ solution - incompatible_target).norm()
    assert float(residual.item()) > 1.0
    assert torch.allclose(solution, torch.zeros_like(solution), atol=EXACT_TOL, rtol=0)


def test_ga27_off_axis_target_pole_is_outside_scalar_cayleynet_locus():
    """GA-27: an uncancelled exact GBDN pole lies off the CayleyNet axis."""

    root = torch.tensor([0.2 + 0.1j], dtype=torch.complex128)
    zero, pole = mapped_zero_pole(root)
    pole_value = complex(pole.item())
    zero_value = complex(zero.item())
    assert abs(pole_value.real) > 1e-6
    assert pole_value.imag < 0.0
    assert abs(pole_value - zero_value) > 1e-6
    # Published scalar finite-order CayleyNet responses have uncancelled poles
    # only at +/- i/h for h>0. This is a pole-locus witness, not a grid fit.
    assert pole_value.real != 0.0


@pytest.mark.parametrize("scale", [1e-4, 1e-3, 1e-2])
@pytest.mark.parametrize(
    "roots",
    [
        torch.tensor([0.2 + 0.1j], dtype=torch.complex128),
        torch.tensor([0.4 + 0.2j, -0.15 + 0.08j], dtype=torch.complex128),
    ],
)
def test_ga28_fixed_root_operator_perturbation_obeys_resolvent_bound(scale, roots):
    """GA-28: aligned Laplacian perturbations satisfy the explicit constant."""

    n = 8
    base_weights = torch.linspace(0.8, 1.4, n - 1, dtype=torch.float64)
    direction = torch.linspace(-0.4, 0.4, n - 1, dtype=torch.float64)
    perturbed_weights = base_weights + scale * direction
    laplacian = _path_laplacian(n, base_weights)
    perturbed = _path_laplacian(n, perturbed_weights)
    operator = dense_exact_blaschke_operator(laplacian, roots)
    perturbed_operator = dense_exact_blaschke_operator(perturbed, roots)
    eta_l = float(torch.linalg.matrix_norm(laplacian - perturbed, ord=2).item())
    eta_g = float(
        torch.linalg.matrix_norm(operator - perturbed_operator, ord=2).item()
    )
    bound = fixed_root_perturbation_constant(roots) * eta_l
    assert eta_g <= bound + 1e-10 * max(1.0, bound)


def test_ga29_polynomial_is_hop_local_while_exact_target_is_generally_dense():
    """GA-29: finite polynomial support and exact rational density are separate."""

    n = 14
    degree = 3
    laplacian = _path_laplacian(n)
    coefficients = torch.tensor(
        [0.4 + 0.1j, -0.2 + 0.3j, 0.1 - 0.05j, 0.03 + 0.02j],
        dtype=torch.complex128,
    )
    polynomial = dense_chebyshev_operator(laplacian, coefficients)
    indices = torch.arange(n)
    distance = (indices[:, None] - indices[None, :]).abs()
    assert float(polynomial[distance > degree].abs().max().item()) <= 1e-12

    exact = dense_exact_blaschke_operator(
        laplacian,
        torch.tensor([0.25 + 0.2j], dtype=torch.complex128),
    )
    assert float(exact[distance > degree].abs().max().item()) > 1e-8


def test_ga30_canonical_recurrence_uses_depth_times_degree_spmvs(monkeypatch):
    """GA-30: the current full per-level recurrence performs exactly D*K SpMVs."""

    n = 7
    depth = 4
    degree = 5
    edge_index, edge_weight = _path_edges(n)
    laplacian = normalized_laplacian(edge_index, edge_weight, n)
    model = GBDNTight(
        in_channels=2,
        hidden_channels=3,
        out_channels=2,
        num_layers=depth,
        K=degree,
    )
    generator = torch.Generator().manual_seed(3000)
    signal = torch.randn(n, 3, dtype=torch.complex64, generator=generator)
    calls = 0
    original = torch.sparse.mm

    def counted_mm(matrix, features):
        nonlocal calls
        calls += 1
        return original(matrix, features)

    monkeypatch.setattr(torch.sparse, "mm", counted_mm)
    analysis = model.analyze_complex(
        signal,
        edge_index,
        edge_weight=edge_weight.float(),
        laplacian=laplacian.float(),
    )
    assert calls == depth * degree
    assert isinstance(analysis, TightAnalysisOutput)
    assert analysis.component_names == (*[f"r_{i}" for i in range(depth)], "h_D")
    assert len(analysis.components) == depth + 1
