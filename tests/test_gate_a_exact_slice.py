"""Exact Gate-A slice: analytic identities, fixtures, and claim boundaries."""

from __future__ import annotations

import math
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
    ValidatedLaplacian,
    blaschke_factor,
    blaschke_product_cheb_coeffs,
    cayley_map,
    center_width_from_root,
    dense_adjoint_tight_synthesis,
    dense_apply_tight_analysis,
    dense_chebyshev_operator,
    dense_exact_blaschke_operator,
    dense_exact_blaschke_symbol,
    dense_tight_analysis_matrix,
    mapped_zero_pole,
    normalized_laplacian,
    parameterize_center_width_roots,
    parameterize_roots,
    tight_split_responses,
    validate_external_laplacian,
)


SCALAR_TOL = 5e-12
EXACT_TOL = 1e-10
SPARSE_TOL = 1e-8
DEPTHS = (1, 2, 4, 8, 16)


def _undirected_edges(
    num_nodes: int,
    pairs: list[tuple[int, int, float]],
) -> tuple[torch.Tensor, torch.Tensor]:
    directed: list[tuple[int, int]] = []
    weights: list[float] = []
    for source, target, weight in pairs:
        directed.extend([(source, target), (target, source)])
        weights.extend([weight, weight])
    edge_index = torch.tensor(directed, dtype=torch.long).t().contiguous()
    edge_weight = torch.tensor(weights, dtype=torch.float64)
    return edge_index, edge_weight


def _path_fixture(num_nodes: int = 6) -> tuple[torch.Tensor, torch.Tensor]:
    return _undirected_edges(
        num_nodes,
        [(node, node + 1, 1.0) for node in range(num_nodes - 1)],
    )


def _cycle_fixture(num_nodes: int = 7) -> tuple[torch.Tensor, torch.Tensor]:
    return _undirected_edges(
        num_nodes,
        [(node, (node + 1) % num_nodes, 1.0) for node in range(num_nodes)],
    )


def _complete_fixture(num_nodes: int = 5) -> tuple[torch.Tensor, torch.Tensor]:
    pairs = [
        (source, target, 1.0)
        for source in range(num_nodes)
        for target in range(source + 1, num_nodes)
    ]
    return _undirected_edges(num_nodes, pairs)


def _disconnected_fixture() -> tuple[torch.Tensor, torch.Tensor]:
    return _undirected_edges(6, [(0, 1, 1.0), (1, 2, 1.0), (3, 4, 1.0)])


def _weighted_fixture() -> tuple[torch.Tensor, torch.Tensor]:
    return _undirected_edges(
        6,
        [(0, 1, 0.4), (1, 2, 1.7), (2, 3, 0.8), (3, 4, 2.1), (1, 4, 0.6)],
    )


FIXTURES = {
    "path": (6, _path_fixture),
    "cycle": (7, _cycle_fixture),
    "complete": (5, _complete_fixture),
    "disconnected": (6, _disconnected_fixture),
    "weighted": (6, _weighted_fixture),
}


def _laplacian(
    fixture: str,
) -> tuple[torch.Tensor, ValidatedLaplacian, torch.Tensor, torch.Tensor]:
    num_nodes, builder = FIXTURES[fixture]
    edge_index, edge_weight = builder()
    token = normalized_laplacian(edge_index, edge_weight, num_nodes)
    return token.to_dense(), token, edge_index, edge_weight


def _root_sets(depth: int) -> list[torch.Tensor]:
    roots = [
        torch.tensor([0.25 + 0.15j], dtype=torch.complex128),
        torch.tensor([-0.30 + 0.10j, 0.12 - 0.18j], dtype=torch.complex128),
        torch.tensor([0.42 - 0.14j], dtype=torch.complex128),
        torch.tensor([-0.18 - 0.22j, 0.08 + 0.27j], dtype=torch.complex128),
    ]
    return [roots[index % len(roots)] for index in range(depth)]


def _operators(laplacian: torch.Tensor, depth: int) -> list[torch.Tensor]:
    return [
        dense_exact_blaschke_operator(laplacian, roots)
        for roots in _root_sets(depth)
    ]


def _node_coefficient_rows(
    components: tuple[torch.Tensor, ...],
) -> torch.Tensor:
    return torch.cat(components, dim=-1)


def test_ga01_root_admissibility_center_width_inverse_and_gradients():
    """GA-01: radial/c-w roots stay admissible and c-w inverse is exact."""

    radial_parameters = torch.tensor(
        [[-1000.0, -80.0], [0.0, math.pi / 3.0], [1000.0, 90.0]],
        dtype=torch.float64,
    )
    radial_roots = parameterize_roots(radial_parameters, r_max=0.95)
    assert torch.isfinite(radial_roots).all()
    assert torch.all(radial_roots.abs() < 0.95)
    assert torch.all(radial_roots.abs() < 1.0)
    with pytest.raises(ValueError, match="r_max"):
        parameterize_roots(radial_parameters, r_max=1.0)
    with pytest.raises(ValueError, match="finite"):
        parameterize_roots(
            torch.tensor([[float("inf"), 0.0]], dtype=torch.float64)
        )

    parameters = torch.tensor(
        [[-40.0, -40.0], [0.0, 0.0], [40.0, 40.0], [1.2, -0.7]],
        dtype=torch.float64,
        requires_grad=True,
    )
    roots = parameterize_center_width_roots(
        parameters,
        gamma_min=0.05,
        gamma_max=1.5,
    )
    center, width = center_width_from_root(roots)
    expected_center = 2.0 * torch.sigmoid(parameters[:, 0])
    expected_width = 0.05 + 1.45 * torch.sigmoid(parameters[:, 1])
    assert torch.all(roots.abs() < 1.0)
    assert torch.allclose(center, expected_center, atol=SCALAR_TOL, rtol=0)
    assert torch.allclose(width, expected_width, atol=SCALAR_TOL, rtol=0)
    assert torch.all((center >= -SCALAR_TOL) & (center <= 2.0 + SCALAR_TOL))
    assert torch.all((width >= 0.05 - SCALAR_TOL) & (width <= 1.5 + SCALAR_TOL))
    loss = roots.real.sum() + roots.imag.sum()
    loss.backward()
    assert parameters.grad is not None
    assert torch.isfinite(parameters.grad).all()


@pytest.mark.parametrize(
    "root",
    [
        torch.tensor(0.35 + 0.20j, dtype=torch.complex128),
        torch.tensor(0.949999 - 1e-4j, dtype=torch.complex128),
    ],
)
def test_ga02_scalar_modulus_phase_zero_pole_and_lorentzian(root):
    """GA-02: scalar all-pass geometry satisfies every analytic identity."""

    eigenvalues = torch.linspace(-4.0, 4.0, 2001, dtype=torch.float64)
    symbol = dense_exact_blaschke_symbol(eigenvalues, root.reshape(1))
    assert float((symbol.abs() - 1.0).abs().max().item()) < SCALAR_TOL

    zero, pole = mapped_zero_pole(root)
    assert torch.abs(blaschke_factor(root, root)).item() < SCALAR_TOL
    assert torch.abs(pole - torch.conj(zero)).item() < SCALAR_TOL
    recovered = (zero - 1j) / (zero + 1j)
    assert torch.abs(recovered - root).item() < SCALAR_TOL
    zero_image = (zero - 1j) / (zero + 1j)
    pole_image = (pole - 1j) / (pole + 1j)
    assert torch.abs(zero_image - root).item() < SCALAR_TOL
    assert torch.abs(1.0 - torch.conj(root) * pole_image).item() < SCALAR_TOL

    probe = torch.linspace(-3.0, 3.0, 801, dtype=torch.float64)
    analytic = tight_split_responses(probe, root.reshape(1))["phase_derivative"]
    lorentzian = 2.0 * zero.imag / (
        (probe - zero.real).square() + zero.imag.square()
    )
    assert torch.all(analytic > 0)
    assert torch.allclose(analytic, lorentzian, atol=SCALAR_TOL, rtol=SCALAR_TOL)
    step = 1e-6
    plus = dense_exact_blaschke_symbol(probe + step, root.reshape(1))
    minus = dense_exact_blaschke_symbol(probe - step, root.reshape(1))
    finite_difference = torch.angle(plus / minus) / (2.0 * step)
    assert torch.allclose(analytic, finite_difference, atol=2e-6, rtol=2e-6)


def test_ga02_multiroot_phase_additivity_and_root_permutation():
    """GA-02: phases add and factor/root ordering does not change the product."""

    eigenvalues = torch.linspace(-2.5, 3.0, 401, dtype=torch.float64)
    roots = torch.tensor(
        [0.2 + 0.1j, -0.35 + 0.2j, 0.15 - 0.25j],
        dtype=torch.complex128,
    )
    response = tight_split_responses(eigenvalues, roots)
    derivative_sum = sum(
        tight_split_responses(eigenvalues, root.reshape(1))["phase_derivative"]
        for root in roots
    )
    permuted = dense_exact_blaschke_symbol(eigenvalues, roots[[2, 0, 1]])
    assert torch.allclose(
        response["phase_derivative"], derivative_sum, atol=SCALAR_TOL, rtol=0
    )
    assert torch.allclose(response["symbol"], permuted, atol=SCALAR_TOL, rtol=0)


@pytest.mark.parametrize("domain", ["grid", "path-spectrum", "cycle-spectrum"])
def test_ga05_pointwise_multilevel_partition(domain):
    """GA-05: effective residual-first atoms partition energy pointwise."""

    if domain == "grid":
        eigenvalues = torch.linspace(-5.0, 5.0, 4001, dtype=torch.float64)
    else:
        fixture = "path" if domain == "path-spectrum" else "cycle"
        eigenvalues = torch.linalg.eigvalsh(_laplacian(fixture)[0])
    carry = torch.ones_like(eigenvalues, dtype=torch.complex128)
    atoms: list[torch.Tensor] = []
    for roots in _root_sets(16):
        symbol = dense_exact_blaschke_symbol(eigenvalues, roots)
        atoms.append(0.5 * (1.0 - symbol) * carry)
        carry = 0.5 * (1.0 + symbol) * carry
    partition = sum(atom.abs().square() for atom in atoms) + carry.abs().square()
    assert float((partition - 1.0).abs().max().item()) < SCALAR_TOL


@pytest.mark.parametrize("fixture", FIXTURES)
@pytest.mark.parametrize("depth", DEPTHS)
def test_ga06_ga07_full_block_isometry_and_conditioning(fixture, depth):
    """GA-06/07: full residual-first block is an isometry at all fixtures/depths."""

    laplacian = _laplacian(fixture)[0]
    analysis = dense_tight_analysis_matrix(_operators(laplacian, depth))
    identity = torch.eye(laplacian.shape[0], dtype=torch.complex128)
    defect = torch.linalg.matrix_norm(analysis.mH @ analysis - identity, ord=2)
    singular_values = torch.linalg.svdvals(analysis)
    assert float(defect.item()) < EXACT_TOL
    assert float((singular_values - 1.0).abs().max().item()) < EXACT_TOL
    condition = singular_values.max() / singular_values.min()
    assert abs(float(condition.item()) - 1.0) < EXACT_TOL

    generator = torch.Generator().manual_seed(6000 + depth)
    signal = torch.randn(
        laplacian.shape[0], 3, dtype=torch.complex128, generator=generator
    )
    components = dense_apply_tight_analysis(signal, _operators(laplacian, depth))
    coefficient_energy = sum(value.abs().square().sum() for value in components)
    relative = (coefficient_energy - signal.abs().square().sum()).abs()
    relative = relative / signal.abs().square().sum()
    assert float(relative.item()) < EXACT_TOL


@pytest.mark.parametrize("fixture", FIXTURES)
@pytest.mark.parametrize("depth", DEPTHS)
def test_ga09_exact_adjoint_synthesis(fixture, depth):
    """GA-09: independent adjoint synthesis equals A* and reconstructs exactly."""

    laplacian = _laplacian(fixture)[0]
    operators = _operators(laplacian, depth)
    generator = torch.Generator().manual_seed(9000 + depth)
    signal = torch.randn(
        laplacian.shape[0], 2, dtype=torch.complex128, generator=generator
    )
    components = dense_apply_tight_analysis(signal, operators)
    reconstructed = dense_adjoint_tight_synthesis(components, operators)
    analysis = dense_tight_analysis_matrix(operators)
    stacked = torch.cat(components, dim=0)
    assert torch.allclose(reconstructed, analysis.mH @ stacked, atol=1e-12, rtol=1e-12)
    relative = (reconstructed - signal).norm() / signal.norm()
    assert float(relative.item()) < EXACT_TOL


def test_ga11_weighted_parseval_for_spectral_weights_and_repeated_eigenspace():
    """GA-11: complete exact analysis preserves every tested spectral energy."""

    laplacian = _laplacian("complete")[0]
    eigenvalues, eigenvectors = torch.linalg.eigh(laplacian)
    operators = _operators(laplacian, 8)
    generator = torch.Generator().manual_seed(1100)
    signal = torch.randn(5, 3, dtype=torch.complex128, generator=generator)
    components = dense_apply_tight_analysis(signal, operators)
    identity = torch.eye(5, dtype=torch.complex128)
    repeated_projector = eigenvectors[:, 1:].to(torch.complex128) @ eigenvectors[:, 1:].mT.to(
        torch.complex128
    )
    spectral_power = (
        eigenvectors.to(torch.complex128)
        * eigenvalues.pow(0.5).to(torch.complex128).unsqueeze(0)
    ) @ eigenvectors.mT.to(torch.complex128)
    weights = [
        identity,
        laplacian.to(torch.complex128),
        laplacian.to(torch.complex128) @ laplacian.to(torch.complex128),
        spectral_power,
        repeated_projector,
    ]
    for weight in weights:
        input_energy = torch.einsum("nc,nm,mc->", signal.conj(), weight, signal).real
        output_energy = sum(
            torch.einsum("nc,nm,mc->", value.conj(), weight, value).real
            for value in components
        )
        relative = (output_energy - input_energy).abs() / input_energy.abs().clamp_min(1e-30)
        assert float(relative.item()) < EXACT_TOL


def test_ga12_noncommuting_node_projector_breaks_weighted_parseval():
    """GA-12: a node projector is outside the commuting spectral theorem."""

    edge_index, edge_weight = _path_fixture(2)
    laplacian = normalized_laplacian(edge_index, edge_weight, 2).to_dense()
    operators = _operators(laplacian, 1)
    signal = torch.tensor(
        [[1.0 + 0.2j], [-0.4 + 0.7j]],
        dtype=torch.complex128,
    )
    components = dense_apply_tight_analysis(signal, operators)
    projector = torch.zeros((2, 2), dtype=torch.complex128)
    projector[0, 0] = 1.0
    complex_laplacian = laplacian.to(torch.complex128)
    commutator = projector @ complex_laplacian - complex_laplacian @ projector
    assert float(torch.linalg.matrix_norm(commutator, ord=2).item()) > 1e-6
    input_energy = torch.einsum("nc,nm,mc->", signal.conj(), projector, signal).real
    output_energy = sum(
        torch.einsum("nc,nm,mc->", value.conj(), projector, value).real
        for value in components
    )
    assert float((output_energy - input_energy).abs().item()) > 1e-6


def test_ga13_actual_blaschke_channel_separation_and_recovery_bounds():
    """GA-13: an actual q=(1-B(phi))/2 obeys both spectral bounds."""

    laplacian, token, _, _ = _laplacian("weighted")
    assert token.validation_method == "normalized-laplacian-construction"
    eigenvalues, eigenvectors = torch.linalg.eigh(laplacian)
    # The repeated lambda=1 eigenspace is kept wholly in S^c.
    assert float((eigenvalues[2] - eigenvalues[3]).abs().item()) < EXACT_TOL
    target_mask = torch.tensor([True, True, False, False, False, False])
    complement_mask = ~target_mask

    roots = torch.tensor(
        [-0.43133513652379385 - 0.4313351365237939j],
        dtype=torch.complex128,
    )
    assert float(roots.abs().max().item()) < 1.0
    one = torch.ones_like(eigenvalues)
    zeta = torch.complex(eigenvalues, -one) / torch.complex(eigenvalues, one)
    # Independent scalar construction: do not ask the production symbol to
    # certify the very channel premise under test.
    exact_symbol = torch.ones_like(zeta)
    for root in roots:
        exact_symbol *= (zeta - root) / (1.0 - root.conj() * zeta)
    q_symbol = 0.5 * (1.0 - exact_symbol)
    assert float((exact_symbol.abs() - 1.0).abs().max().item()) < 5e-12

    exact_factor = dense_exact_blaschke_operator(laplacian, roots)
    independent_factor = (
        eigenvectors.to(torch.complex128) * exact_symbol.unsqueeze(0)
    ) @ eigenvectors.to(torch.complex128).mH
    assert torch.allclose(exact_factor, independent_factor, atol=1e-12, rtol=0.0)

    generator = torch.Generator().manual_seed(1300)
    coefficients = torch.randn(
        6,
        3,
        dtype=torch.complex128,
        generator=generator,
    )
    assert float(coefficients[target_mask].norm().item()) > 1.0
    assert float(coefficients[complement_mask].norm().item()) > 1.0
    vectors = eigenvectors.to(torch.complex128)
    signal = vectors @ coefficients
    q_operator = 0.5 * (
        torch.eye(6, dtype=torch.complex128) - exact_factor
    )
    selected_signal = q_operator @ signal
    selected_coefficients = vectors.mH @ selected_signal
    expected_selected = q_symbol.unsqueeze(1) * coefficients
    assert torch.allclose(
        selected_coefficients,
        expected_selected,
        atol=1e-12,
        rtol=0.0,
    )

    magnitude_delta = float(
        (q_symbol[target_mask].abs() - 1.0).abs().max().item()
    )
    eta = float(q_symbol[complement_mask].abs().max().item())
    target_output_norm = selected_coefficients[target_mask].norm()
    complement_output_norm = selected_coefficients[complement_mask].norm()
    target_lower_bound = (
        (1.0 - magnitude_delta) * coefficients[target_mask].norm()
    )
    complement_upper_bound = eta * coefficients[complement_mask].norm()
    assert target_output_norm + 1e-12 >= target_lower_bound
    assert complement_output_norm <= complement_upper_bound + 1e-12
    assert float(
        target_output_norm / coefficients[target_mask].norm()
        - complement_output_norm / coefficients[complement_mask].norm()
    ) > 0.5

    target_signal = vectors[:, target_mask] @ coefficients[target_mask]
    complement_signal = vectors[:, complement_mask] @ coefficients[complement_mask]
    recovery_delta = float(
        (q_symbol[target_mask] - 1.0).abs().max().item()
    )
    recovery_error = (selected_signal - target_signal).norm()
    recovery_bound = torch.sqrt(
        recovery_delta**2 * target_signal.norm().square()
        + eta**2 * complement_signal.norm().square()
    )
    exact_squared_error = (
        (
            (q_symbol[target_mask] - 1.0).unsqueeze(1)
            * coefficients[target_mask]
        ).abs().square().sum()
        + (
            q_symbol[complement_mask].unsqueeze(1)
            * coefficients[complement_mask]
        ).abs().square().sum()
    )
    assert torch.allclose(
        recovery_error.square(),
        exact_squared_error,
        atol=1e-12,
        rtol=0.0,
    )
    assert recovery_error <= recovery_bound + 1e-12

    # Frozen negative control from the rejected row: these attractive-looking
    # prescribed values are not complementary channels of any all-pass factor.
    arbitrary_q = torch.zeros(5, dtype=torch.complex128)
    arbitrary_q[1:] = 0.96 * torch.exp(
        torch.tensor(0.4j, dtype=torch.complex128)
    )
    arbitrary_q[0] = 0.025 * torch.exp(
        torch.tensor(-0.7j, dtype=torch.complex128)
    )
    arbitrary_factor_defect = (torch.abs(1.0 - 2.0 * arbitrary_q) - 1.0).abs()
    assert arbitrary_factor_defect[1].item() == pytest.approx(
        0.07215940187498293,
        abs=1e-14,
    )
    assert arbitrary_factor_defect[0].item() == pytest.approx(
        0.037702862276130955,
        abs=1e-14,
    )


def test_ga14_actual_blaschke_chebyshev_complex_recovery_bound(record_property):
    """GA-14: actual T/Ttilde bind recovery to epsilon_K/2 in operator norm."""

    laplacian, laplacian_token, _, _ = _laplacian("weighted")
    eigenvalues, eigenvectors = torch.linalg.eigh(laplacian)
    roots = torch.tensor([0.24 + 0.13j, -0.11 + 0.07j], dtype=torch.complex128)
    degree = 8
    exact_factor = dense_exact_blaschke_operator(laplacian, roots)
    chebyshev_coefficients = blaschke_product_cheb_coeffs(
        roots,
        degree,
        torch.device("cpu"),
        convention="forward",
    )
    approximate_factor = dense_chebyshev_operator(
        laplacian,
        chebyshev_coefficients,
    )
    epsilon_k = torch.linalg.matrix_norm(
        approximate_factor - exact_factor,
        ord=2,
    )
    identity = torch.eye(laplacian.shape[0], dtype=torch.complex128)
    q_exact = 0.5 * (identity - exact_factor)
    q_approximate = 0.5 * (identity - approximate_factor)

    q_symbol = 0.5 * (1.0 - dense_exact_blaschke_symbol(eigenvalues, roots))
    # Select a deterministic nontrivial subset; the bound is an identity/
    # inequality for any S and does not assume that this root realizes an ideal
    # packet.
    target_mask = torch.zeros(laplacian.shape[0], dtype=torch.bool)
    target_mask[1::2] = True
    complement_mask = ~target_mask
    projector = (
        eigenvectors[:, target_mask] @ eigenvectors[:, target_mask].mT
    ).to(torch.complex128)
    generator = torch.Generator().manual_seed(1400)
    signal = torch.randn(
        laplacian.shape[0],
        3,
        dtype=torch.complex128,
        generator=generator,
    )
    target_signal = projector @ signal
    coefficients = eigenvectors.to(torch.complex128).mH @ signal
    exact_error_squared = (q_exact @ signal - target_signal).abs().square().sum()
    decomposed = (
        (
            (q_symbol[target_mask] - 1.0).unsqueeze(1)
            * coefficients[target_mask]
        ).abs().square().sum()
        + (
            q_symbol[complement_mask].unsqueeze(1)
            * coefficients[complement_mask]
        ).abs().square().sum()
    )
    identity_residual = (exact_error_squared - decomposed).abs()
    assert float(identity_residual.item()) < 1e-12

    delta = float((q_symbol[target_mask] - 1.0).abs().max().item())
    eta = float(q_symbol[complement_mask].abs().max().item())
    spectral_exact_bound = (
        delta**2 * target_signal.norm().square()
        + eta**2 * (signal - target_signal).norm().square()
    ).sqrt()
    finite_error = (q_approximate @ signal - target_signal).norm()
    approximation_term = 0.5 * epsilon_k * signal.norm()
    total_bound = spectral_exact_bound + approximation_term
    assert finite_error <= total_bound + 1e-12

    induced_operator_error = torch.linalg.matrix_norm(
        q_approximate - q_exact,
        ord=2,
    )
    half_epsilon_residual = (induced_operator_error - 0.5 * epsilon_k).abs()
    assert float(half_epsilon_residual.item()) < 1e-12

    record_property(
        "gate_a_metrics",
        {
            "gate_id": "GA-14",
            "realization_tag": "exact+chebyshev-K",
            "graph_hash": laplacian_token.sha256,
            "roots": [[float(root.real), float(root.imag)] for root in roots],
            "degree": degree,
            "epsilon_k_operator_norm": float(epsilon_k.item()),
            "epsilon_k_over_two": float((0.5 * epsilon_k).item()),
            "exact_squared_identity_residual": float(identity_residual.item()),
            "finite_recovery_error": float(finite_error.item()),
            "predicted_total_bound": float(total_bound.item()),
            "dtype": str(signal.dtype),
            "device": str(signal.device),
        },
    )


def test_ga15_permutation_equivariance_exact_and_polynomial_full_coefficients():
    """GA-15: every exact and polynomial coefficient permutes with the graph."""

    laplacian, laplacian_token, edge_index, edge_weight = _laplacian("weighted")
    num_nodes = laplacian.shape[0]
    permutation = torch.tensor([4, 1, 5, 0, 3, 2])
    permutation_matrix = torch.eye(num_nodes, dtype=torch.float64)[permutation]
    permuted_laplacian = permutation_matrix @ laplacian @ permutation_matrix.mT
    inverse_permutation = torch.empty_like(permutation)
    inverse_permutation[permutation] = torch.arange(num_nodes)
    permuted_edge_index = inverse_permutation[edge_index]
    permuted_token = normalized_laplacian(
        permuted_edge_index,
        edge_weight,
        num_nodes,
    )
    assert torch.allclose(
        permuted_token.to_dense(), permuted_laplacian, atol=1e-12, rtol=0
    )
    generator = torch.Generator().manual_seed(1500)
    signal = torch.randn(num_nodes, 2, dtype=torch.complex128, generator=generator)
    permuted_signal = permutation_matrix.to(torch.complex128) @ signal
    roots = _root_sets(4)

    exact = _operators(laplacian, 4)
    exact_permuted = _operators(permuted_laplacian, 4)
    original_components = dense_apply_tight_analysis(signal, exact)
    permuted_components = dense_apply_tight_analysis(permuted_signal, exact_permuted)
    for original, permuted in zip(original_components, permuted_components):
        expected = permutation_matrix.to(torch.complex128) @ original
        relative = (permuted - expected).norm() / expected.norm().clamp_min(1e-30)
        assert float(relative.item()) < EXACT_TOL

    polynomial: list[torch.Tensor] = []
    polynomial_permuted: list[torch.Tensor] = []
    identity = torch.eye(num_nodes, dtype=torch.complex128)
    for layer_roots in roots:
        coefficients = blaschke_product_cheb_coeffs(
            layer_roots, 12, torch.device("cpu"), convention="forward"
        )
        basis = ChebyshevBasis(12)
        original_basis = basis(
            identity,
            edge_index,
            edge_weight=edge_weight,
            laplacian=laplacian_token,
        )
        permuted_basis = basis(
            identity,
            permuted_edge_index,
            edge_weight=edge_weight,
            laplacian=permuted_token,
        )
        polynomial.append(
            torch.sum(coefficients.view(-1, 1, 1) * original_basis, dim=0)
        )
        polynomial_permuted.append(
            torch.sum(coefficients.view(-1, 1, 1) * permuted_basis, dim=0)
        )
    original_components = dense_apply_tight_analysis(signal, polynomial)
    permuted_components = dense_apply_tight_analysis(permuted_signal, polynomial_permuted)
    for original, permuted in zip(original_components, permuted_components):
        expected = permutation_matrix.to(torch.complex128) @ original
        relative = (permuted - expected).norm() / expected.norm().clamp_min(1e-30)
        assert float(relative.item()) < SPARSE_TOL


def test_ga31_nodewise_lower_bound_exact_and_shared_approximate():
    """GA-31: additive left inverse yields the frozen node-pair lower bound."""

    laplacian = _laplacian("weighted")[0]
    depth = 4
    exact_operators = _operators(laplacian, depth)
    approximate_operators = []
    for roots in _root_sets(depth):
        coefficients = blaschke_product_cheb_coeffs(
            roots, 8, torch.device("cpu"), convention="forward"
        )
        approximate_operators.append(dense_chebyshev_operator(laplacian, coefficients))
    generator = torch.Generator().manual_seed(3100)
    signal = torch.randn(6, 3, dtype=torch.complex128, generator=generator)
    for operators in (exact_operators, approximate_operators):
        rows = _node_coefficient_rows(dense_apply_tight_analysis(signal, operators))
        for source in range(6):
            for target in range(source + 1, 6):
                lower = (signal[source] - signal[target]).norm() / math.sqrt(depth + 1)
                observed = (rows[source] - rows[target]).norm()
                assert observed + 1e-10 >= lower


def test_ga32_carried_state_annihilation_preserves_residual():
    """GA-32: tightness does not imply carried-state non-dissipation."""

    laplacian = _laplacian("cycle")[0]
    zero_mode = torch.ones(7, 2, dtype=torch.complex128)
    # phi(0)=-1 and B_alpha(-1)=-1 for every real interior alpha.
    root = torch.tensor([0.5 + 0.0j], dtype=torch.complex128)
    operator = dense_exact_blaschke_operator(laplacian, root)
    residual, carry = dense_apply_tight_analysis(zero_mode, [operator])
    assert float(carry.norm().item() / zero_mode.norm().item()) < EXACT_TOL
    relative_residual = (residual - zero_mode).norm() / zero_mode.norm()
    assert float(relative_residual.item()) < EXACT_TOL


def test_ga33_global_jacobian_columns_have_unit_norm():
    """GA-33: every complete exact-analysis Jacobian column has norm one."""

    laplacian = _laplacian("path")[0]
    analysis = dense_tight_analysis_matrix(_operators(laplacian, 8))
    column_norms = analysis.abs().square().sum(dim=0).sqrt()
    assert float((column_norms - 1.0).abs().max().item()) < EXACT_TOL


def test_ga34_global_isometry_coexists_with_zero_target_sensitivity():
    """GA-34: disconnected topology gives exact zero target blocks."""

    laplacian = _laplacian("disconnected")[0]
    analysis = dense_tight_analysis_matrix(_operators(laplacian, 4))
    source = 0
    disconnected_target = 4
    num_nodes = laplacian.shape[0]
    target_rows = [level * num_nodes + disconnected_target for level in range(5)]
    global_column_norm = analysis[:, source].norm()
    target_block_norm = analysis[target_rows, source].norm()
    assert abs(float(global_column_norm.item()) - 1.0) < EXACT_TOL
    assert float(target_block_norm.item()) < 1e-12


def test_ga34_connected_endpoint_sensitivity_can_be_arbitrarily_small():
    """GA-34: connected endpoint sensitivity may vanish numerically despite isometry."""

    edge_index, edge_weight = _path_fixture(20)
    laplacian = normalized_laplacian(edge_index, edge_weight, 20).to_dense()
    root = torch.tensor([0.8 + 0.0j], dtype=torch.complex128)
    analysis = dense_tight_analysis_matrix(
        [dense_exact_blaschke_operator(laplacian, root)]
    )
    source = 0
    target_rows = [19, 39]
    assert abs(float(analysis[:, source].norm().item()) - 1.0) < EXACT_TOL
    assert float(analysis[target_rows, source].norm().item()) < 1e-12


def test_ga34_polynomial_beyond_reach_is_exactly_zero():
    """GA-34: degree-K polynomial sensitivity is zero beyond K hops."""

    edge_index, edge_weight = _path_fixture(8)
    token = normalized_laplacian(edge_index, edge_weight, 8)
    coefficient = torch.tensor([0.2 + 0.1j, 0.3 - 0.2j], dtype=torch.complex128)
    polynomial = dense_chebyshev_operator(token.to_dense(), coefficient)
    assert torch.abs(polynomial[7, 0]).item() < 1e-12


def test_external_laplacian_requires_validated_token_and_detects_mutation():
    """Raw external operators cannot bypass the one-time [0,2] audit."""

    edge_index, edge_weight = _path_fixture(6)
    canonical = normalized_laplacian(edge_index, edge_weight, 6)
    raw = canonical.to_dense()
    signal = torch.randn(6, 2, dtype=torch.complex128)
    basis = ChebyshevBasis(2)
    with pytest.raises(TypeError, match="ValidatedLaplacian"):
        basis(signal, edge_index, edge_weight=edge_weight, laplacian=raw)

    out_of_range = 1.1 * raw
    with pytest.raises(ValueError, match="outside"):
        validate_external_laplacian(out_of_range)
    asymmetric = raw.clone()
    asymmetric[0, 1] += 0.1
    with pytest.raises(ValueError, match="self-adjoint"):
        validate_external_laplacian(asymmetric)

    validated = validate_external_laplacian(raw)
    assert validated.source == "caller-supplied-operator"
    assert len(validated.sha256) == 64
    first = basis(signal, edge_index, edge_weight=edge_weight, laplacian=validated)
    second = basis(signal, edge_index, edge_weight=edge_weight, laplacian=validated)
    assert torch.equal(first, second)
    validated.tensor.add_(torch.eye(6, dtype=torch.float64))
    with pytest.raises(RuntimeError, match="modified in place"):
        basis(signal, edge_index, edge_weight=edge_weight, laplacian=validated)


def test_tight_model_accepts_validated_external_laplacian_only():
    """The public canonical model exposes the same auditable token boundary."""

    edge_index, edge_weight = _path_fixture(6)
    raw = normalized_laplacian(edge_index, edge_weight, 6).to_dense()
    validated = validate_external_laplacian(raw)
    model = GBDNTight(2, 3, 2, num_layers=2, K=3)
    signal = torch.randn(6, 2)
    with pytest.raises(TypeError, match="ValidatedLaplacian"):
        model.analyze(signal, edge_index, edge_weight, laplacian=raw)
    output = model.analyze(signal, edge_index, edge_weight, laplacian=validated)
    assert isinstance(output, TightAnalysisOutput)
