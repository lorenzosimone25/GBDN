"""Historical diagnostic subset; this file cannot establish Gate-A acceptance.

The mandatory scientific gate is the complete theorem-to-test suite and its
machine-readable reporter. These compact checks remain only as fast regression
diagnostics for early implementation behavior.
"""

from __future__ import annotations

import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gbdn import (  # noqa: E402
    ChebyshevBasis,
    GBDNTight,
    blaschke_cayley_exact,
    blaschke_cayley_symbol,
    blaschke_product_cheb_coeffs,
    cayley_map,
    mapped_zero_pole,
    multilevel_tight_analysis,
    multilevel_tight_synthesis,
    normalized_laplacian,
    parameterize_roots,
    tight_split_responses,
)

EXACT_TOL = 1e-10
SPARSE_TOL = 1e-8


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


def _spectrum(edge_index: torch.Tensor, edge_weight: torch.Tensor, n: int):
    laplacian = normalized_laplacian(
        edge_index,
        edge_weight,
        n,
        device=torch.device("cpu"),
    )
    return torch.linalg.eigh(laplacian.to_dense())


def _relative_error(actual: torch.Tensor, expected: torch.Tensor) -> float:
    return ((actual - expected).norm() / expected.norm().clamp_min(1e-30)).item()


def test_radial_root_constraint_under_extreme_parameters():
    torch.manual_seed(0)
    params = 100.0 * torch.randn(4096, 2, dtype=torch.float64)
    roots = parameterize_roots(params, r_max=0.95)
    assert torch.all(roots.abs() <= 0.95)
    assert torch.all(roots.abs() < 1.0)
    assert torch.isfinite(roots).all()


def test_forward_phase_derivative_sign_and_value():
    lambdas = torch.linspace(0.05, 1.95, 25, dtype=torch.float64)
    roots = torch.tensor([0.35 + 0.2j, -0.2 + 0.1j], dtype=torch.complex128)
    response = tight_split_responses(lambdas, roots, convention="forward")
    epsilon = 1e-6
    plus = blaschke_cayley_symbol(lambdas + epsilon, roots)
    minus = blaschke_cayley_symbol(lambdas - epsilon, roots)
    finite_difference = torch.angle(plus / minus) / (2.0 * epsilon)
    assert torch.all(response["phase_derivative"] > 0)
    assert torch.allclose(
        response["phase_derivative"],
        finite_difference,
        atol=2e-8,
        rtol=2e-8,
    )


def test_mapped_zero_and_pole_are_conjugates_and_off_real_axis():
    roots = torch.tensor([0.3 + 0.2j, -0.4 + 0.1j], dtype=torch.complex128)
    zeros, poles = mapped_zero_pole(roots)
    assert torch.allclose(poles, torch.conj(zeros), atol=EXACT_TOL, rtol=0)
    assert torch.all(zeros.imag > 0)
    assert torch.all(poles.imag < 0)


def test_exact_unitarity_and_one_level_tightness():
    edge_index, edge_weight = _path_edges(24)
    evals, evecs = _spectrum(edge_index, edge_weight, 24)
    roots = torch.tensor([0.4 + 0.2j, -0.3 + 0.25j], dtype=torch.complex128)
    operator = blaschke_cayley_exact(evals, evecs, roots)
    identity = torch.eye(24, dtype=torch.complex128)
    unitary_error = (operator.mH @ operator - identity).norm().item()
    assert unitary_error < EXACT_TOL

    torch.manual_seed(1)
    h = torch.randn(24, 3, dtype=torch.complex128)
    transformed = operator @ h
    p_plus = 0.5 * (h + transformed)
    p_minus = 0.5 * (h - transformed)
    relative_energy_error = abs(
        (p_plus.abs().square().sum() + p_minus.abs().square().sum()).item()
        - h.abs().square().sum().item()
    ) / h.abs().square().sum().item()
    assert relative_energy_error < EXACT_TOL


def test_multilevel_isometry_and_adjoint_perfect_reconstruction():
    edge_index, edge_weight = _path_edges(28)
    evals, evecs = _spectrum(edge_index, edge_weight, 28)
    root_sets = [
        torch.tensor([0.25 + 0.15j], dtype=torch.complex128),
        torch.tensor([-0.35 + 0.2j, 0.1 - 0.25j], dtype=torch.complex128),
        torch.tensor([0.45 - 0.1j], dtype=torch.complex128),
    ] * 6
    operators = [
        blaschke_cayley_exact(evals, evecs, roots) for roots in root_sets[:16]
    ]
    torch.manual_seed(2)
    h = torch.randn(28, 4, dtype=torch.complex128)
    bands, carry = multilevel_tight_analysis(h, operators)
    coefficient_energy = carry.abs().square().sum() + sum(
        band.abs().square().sum() for band in bands
    )
    energy_error = abs((coefficient_energy - h.abs().square().sum()).item())
    energy_error /= h.abs().square().sum().item()
    assert energy_error < EXACT_TOL

    reconstructed = multilevel_tight_synthesis(bands, carry, operators)
    assert _relative_error(reconstructed, h) < EXACT_TOL


def test_energy_separation_and_complex_recovery_inequalities():
    torch.manual_seed(3)
    coefficients = torch.randn(12, dtype=torch.complex128)
    target = torch.arange(3, 7)
    complement = torch.tensor([0, 1, 2, 7, 8, 9, 10, 11])
    delta = 0.08
    eta = 0.05

    magnitude_response = torch.zeros(12, dtype=torch.complex128)
    magnitude_response[target] = (1.0 - delta) * torch.exp(
        1j * torch.linspace(0.2, 1.1, len(target), dtype=torch.float64)
    )
    magnitude_response[complement] = eta
    residual = magnitude_response * coefficients
    assert residual[target].norm() + 1e-14 >= (1.0 - delta) * coefficients[target].norm()
    assert residual[complement].norm() <= eta * coefficients[complement].norm() + 1e-14

    recovery_response = torch.zeros(12, dtype=torch.complex128)
    recovery_response[target] = 1.0 + delta * torch.exp(
        1j * torch.linspace(0.0, 1.0, len(target), dtype=torch.float64)
    )
    recovery_response[complement] = eta
    recovered = recovery_response * coefficients
    truth = torch.zeros_like(coefficients)
    truth[target] = coefficients[target]
    bound = (
        delta**2 * coefficients[target].abs().square().sum()
        + eta**2 * coefficients[complement].abs().square().sum()
    )
    assert (recovered - truth).abs().square().sum() <= bound + 1e-14


def test_diagnostic_sparse_response_and_single_signal_energy_ratio():
    """Diagnostic only: this is not the mandatory full-operator frame test."""
    n = 20
    edge_index, edge_weight = _path_edges(n)
    evals, evecs = _spectrum(edge_index, edge_weight, n)
    roots = torch.tensor([0.2 + 0.1j], dtype=torch.complex128)
    exact = blaschke_cayley_exact(evals, evecs, roots)
    coeffs = blaschke_product_cheb_coeffs(
        roots,
        128,
        torch.device("cpu"),
        convention="forward",
    )
    torch.manual_seed(4)
    h = torch.randn(n, 2, dtype=torch.complex128)
    basis = ChebyshevBasis(128)(
        h,
        edge_index,
        edge_weight=edge_weight,
        num_nodes=n,
    )
    approximate = torch.sum(coeffs.view(-1, 1, 1) * basis, dim=0)
    operator_error = _relative_error(approximate, exact @ h)
    assert operator_error < SPARSE_TOL

    epsilon = operator_error
    p_plus = 0.5 * (h + approximate)
    p_minus = 0.5 * (h - approximate)
    ratio = (
        p_plus.abs().square().sum() + p_minus.abs().square().sum()
    ) / h.abs().square().sum()
    lower = 0.5 * (1.0 + (1.0 - epsilon) ** 2)
    upper = 0.5 * (1.0 + (1.0 + epsilon) ** 2)
    assert lower - 1e-12 <= ratio <= upper + 1e-12


def test_equal_sized_graphs_do_not_share_stale_laplacians():
    n = 12
    path_edges, path_weights = _path_edges(n)
    cycle_edges, cycle_weights = _cycle_edges(n)
    torch.manual_seed(5)
    x = torch.randn(n, 2, dtype=torch.complex128)
    basis_module = ChebyshevBasis(3)
    path_basis = basis_module(x, path_edges, edge_weight=path_weights)
    cycle_basis = basis_module(x, cycle_edges, edge_weight=cycle_weights)
    fresh_cycle_basis = ChebyshevBasis(3)(x, cycle_edges, edge_weight=cycle_weights)
    assert not torch.allclose(path_basis, cycle_basis)
    assert torch.allclose(cycle_basis, fresh_cycle_basis, atol=EXACT_TOL, rtol=0)


def test_tight_model_analysis_interface_and_depth_dependence():
    n = 14
    edge_index, edge_weight = _path_edges(n)
    torch.manual_seed(6)
    model = GBDNTight(3, 4, 2, num_layers=3, K=16, num_roots=2)
    x = torch.randn(n, 3)
    analysis = model.analyze(x, edge_index, edge_weight=edge_weight.float())
    assert len(analysis.bands) == 3
    assert len(analysis.roots) == 3
    assert all(torch.all(roots.abs() < 1.0) for roots in analysis.roots)
    assert not torch.allclose(analysis.bands[0], analysis.bands[1])
    output, roots = model(x, edge_index, edge_weight=edge_weight.float())
    assert output.shape == (n, 2)
    assert len(roots) == 3


def test_zero_root_product_sum_is_vandermonde_full_rank():
    eigenvalues = torch.tensor([0.0, 0.2, 0.7, 1.4, 2.0], dtype=torch.float64)
    points = cayley_map(eigenvalues)
    vandermonde = torch.stack(
        [points**degree for degree in range(len(points))], dim=1
    )
    assert torch.linalg.matrix_rank(vandermonde).item() == len(points)


if __name__ == "__main__":
    tests = [
        value
        for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        test()
        print(f"{test.__name__}: PASS")
    print(
        f"Diagnostic subset passed: {len(tests)} checks. "
        "This does not establish Gate A; run scripts/report_gate_a.py and "
        "obtain independent review."
    )
