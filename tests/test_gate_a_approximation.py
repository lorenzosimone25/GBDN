"""Gate-A tests for finite realization, expressivity, stability, and cost."""

from __future__ import annotations

import cmath
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
    blaschke_product_cheb_coeffs,
    dense_adjoint_tight_synthesis,
    dense_apply_tight_analysis,
    dct_synthesis,
    dense_chebyshev_operator,
    dense_exact_blaschke_operator,
    dense_tight_analysis_matrix,
    evaluate_chebyshev,
    mapped_zero_pole,
    normalized_laplacian,
)
from gbdn.diagnostics import (  # noqa: E402
    approximation_configuration_diagnostic,
    conservative_ellipse_supremum_bound,
    chebyshev_interpolation_error_bound,
    fixed_root_perturbation_constant,
    frozen_scalar_cayleynet_comparator,
    multilevel_frame_bound,
    product_sum_evaluation_matrix,
    reduced_blaschke_pole_diagnostic,
    target_pole_ellipse_parameter,
    target_pole_diagnostics,
)


EXACT_TOL = 1e-10
SPARSE_TOL = 1e-8


def _independent_blaschke_symbol(
    eigenvalues: torch.Tensor,
    roots: torch.Tensor,
) -> torch.Tensor:
    """Direct scalar target evaluation independent of production helpers."""

    one = torch.ones_like(eigenvalues)
    zeta = torch.complex(eigenvalues, -one) / torch.complex(eigenvalues, one)
    result = torch.ones_like(zeta)
    for root in roots:
        result = result * (zeta - root) / (1.0 - torch.conj(root) * zeta)
    return result


def _independent_chebyshev_values(
    coefficients: torch.Tensor,
    eigenvalues: torch.Tensor,
) -> torch.Tensor:
    """Evaluate a Chebyshev series without the production scalar recurrence."""

    shifted = eigenvalues.to(coefficients.real.dtype) - 1.0
    previous2 = torch.ones_like(shifted)
    result = coefficients[0] * previous2
    if coefficients.numel() == 1:
        return result
    previous = shifted
    result = result + coefficients[1] * previous
    for index in range(2, coefficients.numel()):
        current = 2.0 * shifted * previous - previous2
        result = result + coefficients[index] * current
        previous2, previous = previous, current
    return result


def _manual_mapped_zero(root: complex) -> complex:
    return 1j * (1.0 + root) / (1.0 - root)


def _manual_ellipse_parameter(point: complex) -> float:
    radical = cmath.sqrt(point * point - 1.0)
    return max(abs(point + radical), abs(point - radical))


def _manual_distance_to_interval(point: complex) -> float:
    clipped_real = min(2.0, max(0.0, point.real))
    return abs(point - clipped_real)


def _manual_conservative_m_bound(roots: torch.Tensor, rho: float) -> float:
    semimajor = 0.5 * (rho + 1.0 / rho)
    bound = 1.0
    for root_tensor in roots:
        zero = _manual_mapped_zero(complex(root_tensor.item()))
        pole = zero.conjugate()
        bound *= (abs(zero - 1.0) + semimajor) / (
            abs(pole - 1.0) - semimajor
        )
    return bound


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


def _complete_laplacian(n: int = 5) -> torch.Tensor:
    pairs = [
        (source, target)
        for source in range(n)
        for target in range(n)
        if source != target
    ]
    edge_index = torch.tensor(pairs, dtype=torch.long).t().contiguous()
    edge_weight = torch.ones(edge_index.shape[1], dtype=torch.float64)
    return normalized_laplacian(edge_index, edge_weight, n).to_dense()


def _weighted_laplacian() -> torch.Tensor:
    pairs = [
        (0, 1, 0.4),
        (1, 2, 1.7),
        (2, 3, 0.8),
        (3, 4, 2.1),
        (1, 4, 0.6),
    ]
    directed = []
    weights = []
    for source, target, weight in pairs:
        directed.extend(((source, target), (target, source)))
        weights.extend((weight, weight))
    edge_index = torch.tensor(directed, dtype=torch.long).t().contiguous()
    edge_weight = torch.tensor(weights, dtype=torch.float64)
    return normalized_laplacian(edge_index, edge_weight, 6).to_dense()


FINITE_FRAME_FIXTURES = {
    "path_8": lambda: _path_laplacian(8),
    "complete_5_repeated_spectrum": _complete_laplacian,
    "weighted_6": _weighted_laplacian,
}


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
@pytest.mark.parametrize(
    ("roots", "rho"),
    [
        (torch.tensor([0.2 + 0.1j], dtype=torch.complex128), 1.5),
        (
            torch.tensor(
                [0.2 + 0.1j, -0.15 + 0.08j],
                dtype=torch.complex128,
            ),
            1.2,
        ),
        (torch.tensor([-0.9 + 0.0j], dtype=torch.complex128), 1.02),
    ],
    ids=["generic", "multi-root", "near-cap"],
)
def test_ga20_exact_graph_error_matches_spectral_max_and_analytic_bound(
    degree,
    roots,
    rho,
):
    """GA-20: errors obey independently reconstructed analytic components.

    The certified bound is permitted to be loose and is not interpreted as an
    approximation-efficiency result.
    """

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
            _independent_blaschke_symbol(eigenvalues, roots)
            - _independent_chebyshev_values(coefficients, eigenvalues)
        ).abs().max().item()
    )
    assert abs(operator_error - spectral_error) < EXACT_TOL

    interval = torch.linspace(0.0, 2.0, 20001, dtype=torch.float64)
    interval_error = float(
        (
            _independent_blaschke_symbol(interval, roots)
            - _independent_chebyshev_values(coefficients, interval)
        ).abs().max().item()
    )
    manual_rho_star = min(
        _manual_ellipse_parameter(
            _manual_mapped_zero(complex(root.item())).conjugate() - 1.0
        )
        for root in roots
    )
    manual_m_bound = _manual_conservative_m_bound(roots, rho)
    manual_bound = 4.0 * manual_m_bound * rho ** (-degree) / (rho - 1.0)
    assert target_pole_ellipse_parameter(roots) == pytest.approx(
        manual_rho_star,
        rel=1e-13,
        abs=1e-13,
    )
    assert conservative_ellipse_supremum_bound(roots, rho) == pytest.approx(
        manual_m_bound,
        rel=1e-13,
        abs=1e-13,
    )
    bound = chebyshev_interpolation_error_bound(roots, degree, rho=rho)
    assert bound == pytest.approx(manual_bound, rel=1e-13, abs=1e-13)
    assert spectral_error <= interval_error + 1e-12
    assert interval_error <= bound + 1e-10 * max(1.0, bound)

    joined = approximation_configuration_diagnostic(
        roots,
        degree,
        rho,
        eigenvalues,
        interval_grid_size=20_001,
    )
    assert joined.realization_tag == "chebyshev-K"
    assert joined.graph_spectral_max_error == pytest.approx(
        spectral_error,
        rel=1e-11,
        abs=1e-13,
    )
    assert joined.interval_grid_max_error == pytest.approx(
        interval_error,
        rel=1e-11,
        abs=1e-13,
    )
    assert joined.pole_limited_rho_star == pytest.approx(manual_rho_star)
    assert joined.conservative_m_rho_upper_bound == pytest.approx(manual_m_bound)
    assert joined.certified_interpolation_error_bound == pytest.approx(manual_bound)


@pytest.mark.parametrize("fixture", FINITE_FRAME_FIXTURES)
@pytest.mark.parametrize("degree", [8, 16])
def test_ga21_one_level_frame_spectrum_obeys_true_operator_error_bound(
    fixture,
    degree,
    record_property,
):
    """GA-21: measured frame spectrum lies inside its epsilon envelope."""

    roots = torch.tensor([0.35 + 0.15j], dtype=torch.complex128)
    laplacian = FINITE_FRAME_FIXTURES[fixture]()
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
    record_property(
        "gate_a_metrics",
        {
            "gate_id": "GA-21",
            "fixture": fixture,
            "realization_tag": "exact+chebyshev-K",
            "roots": [[float(root.real), float(root.imag)] for root in roots],
            "degree": degree,
            "epsilon_operator_norm": epsilon,
            "observed_frame_defect": defect,
            "predicted_frame_defect_bound": predicted,
            "minimum_frame_eigenvalue": float(eigenvalues.min().item()),
            "maximum_frame_eigenvalue": float(eigenvalues.max().item()),
            "dtype": str(laplacian.dtype),
            "device": str(laplacian.device),
        },
    )


@pytest.mark.parametrize("fixture", FINITE_FRAME_FIXTURES)
@pytest.mark.parametrize("depth", [1, 2, 4, 8, 16])
def test_ga22_multilevel_frame_defect_obeys_heterogeneous_delta(
    fixture,
    depth,
    record_property,
):
    """GA-22: observed multilevel defect is bounded at every required depth."""

    laplacian = FINITE_FRAME_FIXTURES[fixture]()
    root_bank = [
        torch.tensor([0.2 + 0.1j], dtype=torch.complex128),
        torch.tensor([-0.15 + 0.08j, 0.1 - 0.12j], dtype=torch.complex128),
        torch.tensor([0.3 - 0.05j], dtype=torch.complex128),
    ]
    degrees = [8, 12, 16]
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
        approximate_operators.append(approximate)
        errors.append(float(torch.linalg.matrix_norm(approximate - exact, ord=2).item()))

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

    singular_values = torch.linalg.svdvals(analysis)
    assert torch.allclose(
        singular_values.square().sort().values,
        frame_eigenvalues.sort().values,
        atol=EXACT_TOL,
        rtol=EXACT_TOL,
    )

    generator = torch.Generator().manual_seed(2200 + depth)
    signal = torch.randn(
        laplacian.shape[0],
        3,
        dtype=torch.complex128,
        generator=generator,
    )
    components = dense_apply_tight_analysis(signal, approximate_operators)
    materialized_components = torch.cat(components, dim=0)
    assert torch.allclose(
        materialized_components,
        analysis @ signal,
        atol=EXACT_TOL,
        rtol=EXACT_TOL,
    )

    additive = sum(components[:-1], start=torch.zeros_like(signal)) + components[-1]
    additive_error = float((additive - signal).norm().div(signal.norm()).item())
    assert additive_error <= 1e-12

    synthesized = dense_adjoint_tight_synthesis(
        components,
        approximate_operators,
    )
    synthesis_error = float((synthesized - signal).norm().div(signal.norm()).item())
    assert synthesis_error <= diagnostic.delta + slack
    assert torch.allclose(
        synthesized,
        frame @ signal,
        atol=EXACT_TOL,
        rtol=EXACT_TOL,
    )

    record_property(
        "gate_a_metrics",
        {
            "gate_id": "GA-22",
            "fixture": fixture,
            "realization_tag": "exact+chebyshev-K",
            "depth": depth,
            "degrees": degrees,
            "per_level_epsilon_operator_norms": errors,
            "predicted_delta": diagnostic.delta,
            "observed_frame_defect": observed,
            "singular_values": [float(value.item()) for value in singular_values],
            "additive_reconstruction_error": additive_error,
            "adjoint_synthesis_error": synthesis_error,
            "dtype": str(laplacian.dtype),
            "device": str(laplacian.device),
        },
    )


def test_ga22_heterogeneous_formula_and_no_lower_bound_boundary():
    """GA-22: pin the recurrence formula and the strict Delta<1 condition."""

    errors = (0.1, 0.3, 0.7)
    defects = tuple(error + 0.5 * error * error for error in errors)
    amplifications = tuple((1.0 + 0.5 * error) ** 2 for error in errors)
    expected_delta = (
        defects[0]
        + defects[1] * amplifications[0]
        + defects[2] * amplifications[0] * amplifications[1]
    )
    diagnostic = multilevel_frame_bound(errors)
    assert diagnostic.one_level_defects == pytest.approx(defects)
    assert diagnostic.carry_amplifications == pytest.approx(amplifications)
    assert diagnostic.delta == pytest.approx(expected_delta)

    no_lower_bound = multilevel_frame_bound((0.8,))
    assert no_lower_bound.delta >= 1.0
    assert not no_lower_bound.positive_lower_bound
    assert no_lower_bound.to_dict()["positive_lower_bound"] is False


def test_ga24_joined_configuration_diagnostic_is_complete_and_independent():
    """GA-24: join measured error, certified bounds, and root geometry."""

    roots = torch.tensor(
        [0.2 + 0.1j, -0.15 + 0.08j],
        dtype=torch.complex128,
    )
    degree = 12
    rho = 1.2
    eigenvalues = torch.linalg.eigvalsh(_path_laplacian(9))
    diagnostic = approximation_configuration_diagnostic(
        roots,
        degree,
        rho,
        eigenvalues,
        interval_grid_size=4097,
    )
    payload = diagnostic.to_dict()
    assert set(payload) == {
        "realization_tag",
        "degree",
        "chosen_rho",
        "pole_limited_rho_star",
        "conservative_m_rho_upper_bound",
        "certified_interpolation_error_bound",
        "interval_grid_max_error",
        "graph_spectral_max_error",
        "interval_grid_size",
        "graph_eigenvalue_count",
        "geometry_scope",
        "target_root_pole_geometry",
    }
    assert diagnostic.realization_tag == "chebyshev-K"
    assert diagnostic.degree == degree
    assert diagnostic.chosen_rho == rho
    assert diagnostic.interval_grid_size == 4097
    assert diagnostic.graph_eigenvalue_count == eigenvalues.numel()
    assert diagnostic.geometry_scope == "exact-target"

    coefficients = blaschke_product_cheb_coeffs(
        roots,
        degree,
        torch.device("cpu"),
        convention="forward",
    )
    expected_graph_error = float(
        (
            _independent_blaschke_symbol(eigenvalues, roots)
            - _independent_chebyshev_values(coefficients, eigenvalues)
        ).abs().max().item()
    )
    interval = torch.linspace(0.0, 2.0, 4097, dtype=torch.float64)
    expected_interval_error = float(
        (
            _independent_blaschke_symbol(interval, roots)
            - _independent_chebyshev_values(coefficients, interval)
        ).abs().max().item()
    )
    manual_rho_star = min(
        _manual_ellipse_parameter(
            _manual_mapped_zero(complex(root.item())).conjugate() - 1.0
        )
        for root in roots
    )
    manual_m_bound = _manual_conservative_m_bound(roots, rho)
    manual_error_bound = 4.0 * manual_m_bound * rho ** (-degree) / (rho - 1.0)
    assert diagnostic.graph_spectral_max_error == pytest.approx(
        expected_graph_error,
        rel=1e-11,
        abs=1e-13,
    )
    assert diagnostic.interval_grid_max_error == pytest.approx(
        expected_interval_error,
        rel=1e-11,
        abs=1e-13,
    )
    assert diagnostic.pole_limited_rho_star == pytest.approx(manual_rho_star)
    assert diagnostic.conservative_m_rho_upper_bound == pytest.approx(manual_m_bound)
    assert diagnostic.certified_interpolation_error_bound == pytest.approx(
        manual_error_bound
    )

    rows = diagnostic.target_root_pole_geometry
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
    for root, row in zip(roots, rows, strict=True):
        assert set(row) == required
        assert all(torch.isfinite(torch.tensor(value)) for value in row.values())
        root_value = complex(root.item())
        zero = _manual_mapped_zero(root_value)
        pole = zero.conjugate()
        assert row["root_radius"] == pytest.approx(abs(root_value))
        assert row["root_angle"] == pytest.approx(
            math.atan2(root_value.imag, root_value.real)
        )
        assert row["mapped_zero_real"] == pytest.approx(zero.real)
        assert row["mapped_zero_imag"] == pytest.approx(zero.imag)
        assert row["mapped_pole_real"] == pytest.approx(pole.real)
        assert row["mapped_pole_imag"] == pytest.approx(pole.imag)
        assert row["pole_margin_to_interval"] == pytest.approx(
            _manual_distance_to_interval(pole)
        )
        assert row["bernstein_parameter"] == pytest.approx(
            _manual_ellipse_parameter(pole - 1.0)
        )


def test_diagnostics_reject_empty_nonfinite_and_inadmissible_inputs():
    """Gate diagnostics fail loudly instead of emitting invalid records."""

    empty = torch.empty(0, dtype=torch.complex128)
    nonfinite = torch.tensor([complex(float("nan"), 0.0)], dtype=torch.complex128)
    inadmissible = torch.tensor([1.0 + 0.0j], dtype=torch.complex128)
    with pytest.raises(ValueError, match="at least one root"):
        target_pole_diagnostics(empty)
    with pytest.raises(TypeError, match="complex dtype"):
        target_pole_diagnostics(torch.tensor([0.2], dtype=torch.float64))
    with pytest.raises(ValueError, match="finite"):
        target_pole_ellipse_parameter(nonfinite)
    with pytest.raises(ValueError, match="unit disk"):
        conservative_ellipse_supremum_bound(inadmissible, 1.1)
    with pytest.raises(ValueError, match="unit disk"):
        fixed_root_perturbation_constant(inadmissible)

    valid = torch.tensor([0.2 + 0.1j], dtype=torch.complex128)
    with pytest.raises(ValueError, match="must not be empty"):
        approximation_configuration_diagnostic(
            valid,
            8,
            1.2,
            torch.empty(0, dtype=torch.float64),
        )
    with pytest.raises(ValueError, match=r"\[0, 2\]"):
        approximation_configuration_diagnostic(
            valid,
            8,
            1.2,
            torch.tensor([-0.1, 1.0], dtype=torch.float64),
        )


def test_frame_and_interpolation_diagnostics_reject_nonfinite_output():
    """Finite inputs may not silently produce overflowed theorem bounds."""

    with pytest.raises(ValueError, match="at least one operator error"):
        multilevel_frame_bound(())
    with pytest.raises(ValueError, match="finite and nonnegative"):
        multilevel_frame_bound((float("inf"),))
    with pytest.raises(ValueError, match="finite and nonnegative"):
        multilevel_frame_bound((-0.1,))
    with pytest.raises(OverflowError, match="overflow"):
        multilevel_frame_bound((1e308,))

    roots = torch.tensor([0.2 + 0.1j], dtype=torch.complex128)
    with pytest.raises(ValueError, match="nonnegative integer"):
        chebyshev_interpolation_error_bound(roots, True, 1.2)
    with pytest.raises(TypeError, match="real scalar"):
        chebyshev_interpolation_error_bound(roots, 8, "not-a-number")
    with pytest.raises(ValueError, match="greater than one"):
        chebyshev_interpolation_error_bound(roots, 8, 1.0)
    with pytest.raises(ValueError, match="strictly inside"):
        chebyshev_interpolation_error_bound(
            roots,
            8,
            target_pole_ellipse_parameter(roots),
        )


def test_ga25_product_sum_reports_stable_and_ill_conditioned_witnesses(
    record_property,
):
    """GA-25: report stable interpolation and the ill-conditioned boundary."""

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

    ill_eigenvalues = torch.arange(5, dtype=torch.float64) * 1e-3
    ill_matrix = product_sum_evaluation_matrix(ill_eigenvalues, roots)
    ill_singular_values = torch.linalg.svdvals(ill_matrix)
    ill_condition = float(
        (ill_singular_values.max() / ill_singular_values.min()).item()
    )
    assert ill_condition > 1e10
    record_property(
        "gate_a_metrics",
        {
            "gate_id": "GA-25",
            "realization_tag": "exact",
            "roots": [[float(root.real), float(root.imag)] for root in roots],
            "stable_spectrum": eigenvalues.tolist(),
            "stable_singular_values": singular_values.tolist(),
            "stable_numerical_rank": int(torch.linalg.matrix_rank(matrix).item()),
            "stable_condition_number": condition,
            "stable_interpolation_relative_residual": float(relative.item()),
            "ill_conditioned_spectrum": ill_eigenvalues.tolist(),
            "ill_conditioned_singular_values": ill_singular_values.tolist(),
            "ill_conditioned_numerical_rank": int(
                torch.linalg.matrix_rank(ill_matrix).item()
            ),
            "ill_conditioned_condition_number": ill_condition,
            "finite_k_claim": False,
            "dtype": str(matrix.dtype),
            "device": str(matrix.device),
        },
    )


def test_ga26_scalar_multiplier_cannot_fit_orientations_in_repeated_eigenspace():
    """GA-26: one repeated-eigenvalue scalar cannot realize +1 and -1."""

    design = torch.ones((2, 1), dtype=torch.complex128)
    incompatible_target = torch.tensor([1.0, -1.0], dtype=torch.complex128)
    solution = torch.linalg.lstsq(design, incompatible_target).solution
    residual = (design @ solution - incompatible_target).norm()
    assert float(residual.item()) > 1.0
    assert torch.allclose(solution, torch.zeros_like(solution), atol=EXACT_TOL, rtol=0)


def test_ga27_frozen_cayleynet_and_gbdn_reduced_pole_multisets(record_property):
    """GA-27: exact reduced poles separate under the frozen continuum scope."""

    comparator = frozen_scalar_cayleynet_comparator(
        0.3,
        torch.tensor(
            [0.7 + 0.2j, -0.4 + 0.3j, 0.15 - 0.25j],
            dtype=torch.complex128,
        ),
        1.7,
    )
    assert comparator["declared_order"] == comparator["effective_order"] == 3
    comparator_poles = comparator["reduced_pole_multiset"]
    assert comparator_poles
    assert all(abs(entry["pole"]["real"]) <= 1e-12 for entry in comparator_poles)
    assert all(entry["multiplicity"] > 0 for entry in comparator_poles)

    root = torch.tensor([0.2 + 0.1j], dtype=torch.complex128)
    gbdn = reduced_blaschke_pole_diagnostic(root)
    assert gbdn["cancelled_pair_count"] == 0
    assert len(gbdn["reduced_pole_multiset"]) == 1
    gbdn_pole = gbdn["reduced_pole_multiset"][0]["pole"]
    assert abs(gbdn_pole["real"]) > 1e-6
    assert gbdn_pole["imag"] < 0.0
    distance_to_comparator = min(
        abs(
            complex(gbdn_pole["real"], gbdn_pole["imag"])
            - complex(entry["pole"]["real"], entry["pole"]["imag"])
        )
        for entry in comparator_poles
    )
    assert distance_to_comparator > 1e-6
    assert comparator["comparison_domain"] == gbdn["comparison_domain"]
    record_property(
        "gate_a_metrics",
        {
            "gate_id": "GA-27",
            "realization_tag": "exact",
            "comparison_domain": "continuum-with-accumulation-point",
            "comparator": comparator,
            "gbdn": gbdn,
            "minimum_reduced_pole_multiset_distance": distance_to_comparator,
            "finite_spectrum_claim": False,
            "approximation_or_efficiency_claim": False,
            "dtype": str(root.dtype),
            "device": str(root.device),
        },
    )


def test_ga27_reduced_pole_diagnostics_reject_invalid_comparator_inputs():
    """GA-27: the frozen rational comparator fails on undefined conventions."""

    coefficients = torch.tensor([0.5 + 0.2j], dtype=torch.complex128)
    with pytest.raises(ValueError, match="positive"):
        frozen_scalar_cayleynet_comparator(0.0, coefficients, 0.0)
    with pytest.raises(ValueError, match="positive effective order"):
        frozen_scalar_cayleynet_comparator(
            0.0,
            torch.zeros(2, dtype=torch.complex128),
            1.0,
        )
    with pytest.raises(ValueError, match="unit disk"):
        reduced_blaschke_pole_diagnostic(
            torch.tensor([1.0 + 0.0j], dtype=torch.complex128)
        )


@pytest.mark.parametrize("scale", [1e-4, 1e-3, 1e-2])
@pytest.mark.parametrize(
    "roots",
    [
        torch.tensor([0.2 + 0.1j], dtype=torch.complex128),
        torch.tensor([0.4 + 0.2j, -0.15 + 0.08j], dtype=torch.complex128),
    ],
)
def test_ga28_fixed_root_operator_perturbation_obeys_resolvent_bound(
    scale,
    roots,
    record_property,
):
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
    manual_constant = 0.0
    for root in roots:
        zero = _manual_mapped_zero(complex(root.item()))
        pole = zero.conjugate()
        margin = _manual_distance_to_interval(pole)
        manual_constant += abs(pole - zero) / (margin * margin)
    reported_constant = fixed_root_perturbation_constant(roots)
    assert reported_constant == pytest.approx(
        manual_constant,
        rel=1e-13,
        abs=1e-13,
    )
    bound = reported_constant * eta_l
    assert eta_g <= bound + 1e-10 * max(1.0, bound)
    record_property("laplacian_perturbation_norm", eta_l)
    record_property("filter_perturbation_norm", eta_g)
    record_property("perturbation_constant", reported_constant)
    record_property("observed_to_bound_ratio", eta_g / bound)


def test_ga29_polynomial_is_hop_local_while_exact_target_is_not_k_hop_localized():
    """GA-29: finite support does not transfer from polynomial to exact target."""

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
    # This witness proves failure of K-hop localization. It is deliberately not
    # promoted to a universal claim that every exact rational response is dense.
    assert float(exact[distance > degree].abs().max().item()) > 1e-8


@pytest.mark.parametrize(("depth", "degree"), [(1, 0), (1, 3), (2, 4), (4, 5)])
def test_ga30_canonical_recurrence_spmvs_and_coefficient_storage(
    monkeypatch,
    record_property,
    depth,
    degree,
):
    """GA-30: verify D*K SpMVs and residual-first coefficient storage.

    Counting convention: one ``torch.sparse.mm`` call applying the real graph
    Laplacian to a complex feature matrix counts as one complex-feature SpMV.
    We report coefficient-tensor storage only; parameters, recurrence
    temporaries, allocator overhead, and the downstream readout are excluded.
    """

    n = 7
    hidden_channels = 3
    edge_index, edge_weight = _path_edges(n)
    laplacian = normalized_laplacian(edge_index, edge_weight, n)
    model = GBDNTight(
        in_channels=2,
        hidden_channels=hidden_channels,
        out_channels=2,
        num_layers=depth,
        K=degree,
    )
    generator = torch.Generator().manual_seed(3000)
    signal = torch.randn(
        n,
        hidden_channels,
        dtype=torch.complex64,
        generator=generator,
    )
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
        laplacian=laplacian,
    )
    assert calls == depth * degree
    assert isinstance(analysis, TightAnalysisOutput)
    assert analysis.component_names == (*[f"r_{i}" for i in range(depth)], "h_D")
    assert len(analysis.components) == depth + 1
    expected_complex_values = (depth + 1) * n * hidden_channels
    observed_complex_values = sum(component.numel() for component in analysis.components)
    observed_storage_bytes = sum(
        component.numel() * component.element_size()
        for component in analysis.components
    )
    expected_storage_bytes = expected_complex_values * signal.element_size()
    assert observed_complex_values == expected_complex_values
    assert observed_storage_bytes == expected_storage_bytes
    assert all(component.dtype == signal.dtype for component in analysis.components)
    assert all(component.shape == signal.shape for component in analysis.components)

    record_property(
        "spmv_counting_convention",
        "one torch.sparse.mm on a complex feature matrix counts as one SpMV",
    )
    record_property("depth", depth)
    record_property("degree", degree)
    record_property("observed_spmv_count", calls)
    record_property("coefficient_complex_value_count", observed_complex_values)
    record_property("coefficient_storage_bytes", observed_storage_bytes)
