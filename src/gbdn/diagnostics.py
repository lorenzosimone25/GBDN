"""Theory-facing diagnostics for Gate A.

These helpers expose quantities that appear in the finite-realization and
perturbation theorems.  They do not run experiments and they do not turn a
partial test suite into Gate-A acceptance.
"""

from __future__ import annotations

import cmath
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass

import torch

from gbdn.spectral import (
    blaschke_cayley_symbol,
    blaschke_product_cheb_coeffs,
    evaluate_chebyshev,
    mapped_zero_pole,
)


@dataclass(frozen=True)
class FrameBoundDiagnostic:
    """Heterogeneous multilevel frame-defect upper bound."""

    errors: tuple[float, ...]
    one_level_defects: tuple[float, ...]
    carry_amplifications: tuple[float, ...]
    delta: float

    @property
    def positive_lower_bound(self) -> bool:
        return self.delta < 1.0

    def to_dict(self) -> dict[str, object]:
        return asdict(self) | {"positive_lower_bound": self.positive_lower_bound}


@dataclass(frozen=True)
class ApproximationConfigurationDiagnostic:
    """Joined GA-24 record for one finite target approximation.

    ``conservative_m_rho_upper_bound`` is an analytic upper bound on
    ``M_rho``, not the actual ellipse supremum. Likewise,
    ``certified_interpolation_error_bound`` is a certificate, not a claim that
    the finite realization is efficient or that the bound is tight.
    """

    realization_tag: str
    degree: int
    chosen_rho: float
    pole_limited_rho_star: float
    conservative_m_rho_upper_bound: float
    certified_interpolation_error_bound: float
    interval_grid_max_error: float
    graph_spectral_max_error: float
    interval_grid_size: int
    graph_eigenvalue_count: int
    geometry_scope: str
    target_root_pole_geometry: tuple[dict[str, float], ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _validated_roots(roots: torch.Tensor) -> torch.Tensor:
    """Return a flattened finite complex root tensor inside the open disk."""

    if not isinstance(roots, torch.Tensor):
        raise TypeError("roots must be a torch.Tensor")
    if not roots.is_complex():
        raise TypeError("roots must use a complex dtype")
    roots = roots.reshape(-1)
    if roots.numel() == 0:
        raise ValueError("at least one root is required")
    if not torch.isfinite(roots).all():
        raise ValueError("roots must be finite")
    if torch.any(roots.abs() >= 1.0):
        raise ValueError("roots must lie strictly inside the unit disk")
    return roots


def _validated_degree(degree: int) -> int:
    if isinstance(degree, bool) or not isinstance(degree, int) or degree < 0:
        raise ValueError("degree must be a nonnegative integer")
    return degree


def _validated_rho(rho: float) -> float:
    try:
        rho = float(rho)
    except (TypeError, ValueError) as error:
        raise TypeError("rho must be a real scalar") from error
    if not math.isfinite(rho) or rho <= 1.0:
        raise ValueError("rho must be finite and greater than one")
    return rho


def multilevel_frame_bound(errors: Sequence[float]) -> FrameBoundDiagnostic:
    """Compute the frozen heterogeneous ``Delta_D`` recurrence.

    Every input must be a finite, nonnegative, true operator-norm error.
    """

    if len(errors) == 0:
        raise ValueError("at least one operator error is required")

    checked: list[float] = []
    defects: list[float] = []
    amplifications: list[float] = []
    prefix = 1.0
    delta = 0.0
    for raw_error in errors:
        error = float(raw_error)
        if not math.isfinite(error) or error < 0.0:
            raise ValueError("operator errors must be finite and nonnegative")
        try:
            defect = error + 0.5 * error * error
            amplification = (1.0 + 0.5 * error) ** 2
        except OverflowError as overflow:
            raise OverflowError(
                "frame-bound terms overflowed finite precision"
            ) from overflow
        if not math.isfinite(defect) or not math.isfinite(amplification):
            raise OverflowError("frame-bound terms overflowed finite precision")
        delta += defect * prefix
        prefix *= amplification
        if not math.isfinite(delta) or not math.isfinite(prefix):
            raise OverflowError("frame-bound recurrence overflowed finite precision")
        checked.append(error)
        defects.append(defect)
        amplifications.append(amplification)
    return FrameBoundDiagnostic(
        errors=tuple(checked),
        one_level_defects=tuple(defects),
        carry_amplifications=tuple(amplifications),
        delta=delta,
    )


def bernstein_ellipse_parameter(point: complex) -> float:
    """Return the Bernstein-ellipse parameter through a point off ``[-1,1]``."""

    value = complex(point)
    if not math.isfinite(value.real) or not math.isfinite(value.imag):
        raise ValueError("point must be finite")
    if abs(value.imag) == 0.0 and -1.0 <= value.real <= 1.0:
        return 1.0
    try:
        radical = cmath.sqrt(value * value - 1.0)
        parameter = max(abs(value + radical), abs(value - radical))
    except OverflowError as error:
        raise OverflowError("Bernstein-ellipse calculation overflowed") from error
    if not math.isfinite(parameter):
        raise OverflowError("Bernstein-ellipse parameter is not finite")
    return parameter


def target_pole_ellipse_parameter(roots: torch.Tensor) -> float:
    """Return the nearest reduced target-pole ellipse parameter on ``[0,2]``."""

    roots = _validated_roots(roots)
    zeros, poles = mapped_zero_pole(roots)
    del zeros
    return min(
        bernstein_ellipse_parameter(complex(pole.item()) - 1.0)
        for pole in poles
    )


def conservative_ellipse_supremum_bound(
    roots: torch.Tensor,
    rho: float,
) -> float:
    """Upper-bound ``max |B_R(phi(lambda))|`` on a Bernstein ellipse.

    The ellipse is centered at one in the Laplacian variable.  It is contained
    in the disk of radius ``a=(rho+rho^-1)/2``.  Applying the triangle and
    reverse-triangle inequalities to each reduced factor gives a conservative,
    fully explicit bound.  The helper intentionally rejects ellipses for which
    this disk bound cannot certify a positive pole margin.
    """

    rho = _validated_rho(rho)
    roots = _validated_roots(roots)
    zeros, poles = mapped_zero_pole(roots)
    semimajor = 0.5 * (rho + 1.0 / rho)
    bound = 1.0
    for zero, pole in zip(zeros, poles, strict=True):
        numerator = abs(complex(zero.item()) - 1.0) + semimajor
        denominator = abs(complex(pole.item()) - 1.0) - semimajor
        if denominator <= 0.0:
            raise ValueError(
                "chosen ellipse is not certified by the conservative disk margin"
            )
        bound *= numerator / denominator
        if not math.isfinite(bound):
            raise OverflowError("conservative ellipse supremum bound overflowed")
    return float(bound)


def chebyshev_interpolation_error_bound(
    roots: torch.Tensor,
    degree: int,
    rho: float,
) -> float:
    """Return a certified first-kind Chebyshev interpolation error bound."""

    degree = _validated_degree(degree)
    roots = _validated_roots(roots)
    rho = _validated_rho(rho)
    if rho >= target_pole_ellipse_parameter(roots):
        raise ValueError("rho must lie strictly inside every target-pole ellipse")
    supremum = conservative_ellipse_supremum_bound(roots, rho)
    bound = 4.0 * supremum * rho ** (-degree) / (rho - 1.0)
    if not math.isfinite(bound) or bound <= 0.0:
        raise OverflowError("interpolation error bound is not representable")
    return float(bound)


def distance_to_interval(point: complex, lower: float, upper: float) -> float:
    """Euclidean distance from a complex point to a closed real interval."""

    value = complex(point)
    lower = float(lower)
    upper = float(upper)
    if not all(
        math.isfinite(item) for item in (value.real, value.imag, lower, upper)
    ):
        raise ValueError("point and interval endpoints must be finite")
    if lower > upper:
        raise ValueError("lower interval endpoint must not exceed upper endpoint")
    if value.real < lower:
        real_distance = lower - value.real
    elif value.real > upper:
        real_distance = value.real - upper
    else:
        real_distance = 0.0
    return math.hypot(real_distance, value.imag)


def fixed_root_perturbation_constant(roots: torch.Tensor) -> float:
    """Return the product telescoping constant for spectra in ``[0,2]``."""

    roots = _validated_roots(roots)
    zeros, poles = mapped_zero_pole(roots)
    constant = 0.0
    for zero, pole in zip(zeros, poles, strict=True):
        zero_value = complex(zero.item())
        pole_value = complex(pole.item())
        margin = distance_to_interval(pole_value, 0.0, 2.0)
        if margin <= 0.0:
            raise ValueError("target pole must have positive distance from [0,2]")
        constant += abs(pole_value - zero_value) / (margin * margin)
        if not math.isfinite(constant):
            raise OverflowError("perturbation constant overflowed finite precision")
    return float(constant)


def product_sum_evaluation_matrix(
    eigenvalues: torch.Tensor,
    roots: torch.Tensor,
) -> torch.Tensor:
    """Evaluate ``(1,q_1,...,q_D)`` for one nonzero root per factor."""

    if eigenvalues.ndim != 1 or not eigenvalues.is_floating_point():
        raise TypeError("eigenvalues must be a one-dimensional real tensor")
    if eigenvalues.numel() == 0 or not torch.isfinite(eigenvalues).all():
        raise ValueError("eigenvalues must be nonempty and finite")
    if roots.ndim != 1 or not roots.is_complex():
        raise TypeError("roots must be a one-dimensional complex tensor")
    roots = _validated_roots(roots)
    if torch.any(roots.abs() <= 0.0):
        raise ValueError("roots must be nonzero and strictly inside the unit disk")
    cumulative = torch.ones(
        eigenvalues.numel(),
        dtype=torch.complex128 if eigenvalues.dtype == torch.float64 else torch.complex64,
        device=eigenvalues.device,
    )
    columns = [cumulative]
    for root in roots:
        cumulative = cumulative * blaschke_cayley_symbol(
            eigenvalues,
            root.reshape(1),
        )
        columns.append(cumulative)
    return torch.stack(columns, dim=1)


def _complex_record(value: complex) -> dict[str, float]:
    return {"real": float(value.real), "imag": float(value.imag)}


def _polynomial_add(
    left: list[complex],
    right: list[complex],
) -> list[complex]:
    result = [0.0j] * max(len(left), len(right))
    for index, value in enumerate(left):
        result[index] += value
    for index, value in enumerate(right):
        result[index] += value
    return result


def _polynomial_multiply(
    left: list[complex],
    right: list[complex],
) -> list[complex]:
    result = [0.0j] * (len(left) + len(right) - 1)
    for left_index, left_value in enumerate(left):
        for right_index, right_value in enumerate(right):
            result[left_index + right_index] += left_value * right_value
    return result


def _polynomial_power(base: list[complex], exponent: int) -> list[complex]:
    result = [1.0 + 0.0j]
    for _ in range(exponent):
        result = _polynomial_multiply(result, base)
    return result


def _polynomial_evaluate(coefficients: list[complex], point: complex) -> complex:
    result = 0.0j
    for coefficient in reversed(coefficients):
        result = result * point + coefficient
    return result


def frozen_scalar_cayleynet_comparator(
    c0: float,
    coefficients: torch.Tensor,
    scale: float,
) -> dict[str, object]:
    """Reduce one frozen published scalar finite-order CayleyNet response.

    The frozen convention is

    ``c0 + sum_j [c_j q_h(z)^j + conj(c_j) q_h(z)^(-j)]`` with
    ``q_h(z)=(h z-i)/(h z+i)``.  ``h`` is learned in CayleyNet but shared by
    all powers of one scalar response.  This diagnostic evaluates no grid: it
    constructs the exact numerator/common denominator and records the reduced
    pole multiset.  Reduction is algebraic: the highest exactly nonzero
    coefficient fixes the pole order at both Cayley loci, so a caller cannot
    change the exact rational object through a numerical tolerance.
    """

    try:
        c0 = float(c0)
        scale = float(scale)
    except (TypeError, ValueError) as error:
        raise TypeError("c0 and scale must be real scalars") from error
    if not math.isfinite(c0):
        raise ValueError("c0 must be finite")
    if not math.isfinite(scale) or scale <= 0.0:
        raise ValueError("Cayley scale h must be finite and positive")
    if not isinstance(coefficients, torch.Tensor):
        raise TypeError("coefficients must be a torch.Tensor")
    if coefficients.ndim != 1 or coefficients.numel() == 0:
        raise ValueError("coefficients c_1,...,c_r must be a nonempty vector")
    if not coefficients.is_complex():
        raise TypeError("Cayley coefficients must use a complex dtype")
    if not torch.isfinite(coefficients).all():
        raise ValueError("Cayley coefficients must be finite")

    values = [complex(value.item()) for value in coefficients]
    effective_order = 0
    for index, value in enumerate(values, start=1):
        if value != 0.0j:
            effective_order = index
    if effective_order == 0:
        raise ValueError("the frozen comparator must have positive effective order")
    values = values[:effective_order]

    plus = [1.0j, complex(scale, 0.0)]  # h z + i
    minus = [-1.0j, complex(scale, 0.0)]  # h z - i
    order = effective_order
    denominator = _polynomial_multiply(
        _polynomial_power(plus, order),
        _polynomial_power(minus, order),
    )
    numerator = [c0 * value for value in denominator]
    for power, coefficient in enumerate(values, start=1):
        analytic = _polynomial_multiply(
            _polynomial_power(minus, order + power),
            _polynomial_power(plus, order - power),
        )
        conjugate = _polynomial_multiply(
            _polynomial_power(plus, order + power),
            _polynomial_power(minus, order - power),
        )
        numerator = _polynomial_add(
            numerator,
            [coefficient * value for value in analytic],
        )
        numerator = _polynomial_add(
            numerator,
            [coefficient.conjugate() * value for value in conjugate],
        )

    candidates = (-1.0j / scale, 1.0j / scale)
    reduced: list[dict[str, object]] = []
    unreduced: list[dict[str, object]] = []
    cancellations: list[dict[str, object]] = []
    numerator_values: list[dict[str, object]] = []
    for pole in candidates:
        unreduced.append({"pole": _complex_record(pole), "multiplicity": order})
        cancellations.append(
            {
                "pole": _complex_record(pole),
                "numerator_multiplicity": 0,
                "cancelled_multiplicity": 0,
            }
        )
        numerator_values.append(
            {
                "pole": _complex_record(pole),
                "value": _complex_record(_polynomial_evaluate(numerator, pole)),
            }
        )
        reduced.append({"pole": _complex_record(pole), "multiplicity": order})

    return {
        "schema": "gbdn-frozen-scalar-cayleynet-comparator-v2",
        "family": "CayleyNet",
        "response_kind": "published-real-scalar-rational-continuation",
        "formula": (
            "c0 + sum_{j=1}^r [c_j q_h(z)^j + conj(c_j) q_h(z)^(-j)]"
        ),
        "cayley_map": "q_h(z)=(h*z-i)/(h*z+i)",
        "coefficient_convention": "c0 real; c_j complex for j>=1",
        "scale_convention": "one learned shared h>0 per scalar response",
        "reduction_policy": (
            "algebraic-highest-exactly-nonzero-coefficient; no caller tolerance"
        ),
        "scale_h": scale,
        "declared_order": int(coefficients.numel()),
        "effective_order": order,
        "c0": c0,
        "coefficients_c1_to_cr": [_complex_record(value) for value in values],
        "numerator_coefficients_ascending": [
            _complex_record(value) for value in numerator
        ],
        "denominator_coefficients_ascending": [
            _complex_record(value) for value in denominator
        ],
        "unreduced_pole_multiset": unreduced,
        "numerator_at_unreduced_poles": numerator_values,
        "cancellations": cancellations,
        "reduced_pole_multiset": reduced,
        "realization_tag": "exact",
        "comparison_domain": "continuum-with-accumulation-point",
        "primary_source_binding": (
            "CayleyNets Eq. (3), convention frozen in "
            "reviews/novelty_primary_source_audit.md"
        ),
    }


def reduced_blaschke_pole_diagnostic(
    roots: torch.Tensor,
) -> dict[str, object]:
    """Return the algebraically reduced poles of an exact Blaschke product.

    For admissible roots, numerator zeros correspond to disk points while
    denominator poles correspond to reciprocal-conjugate points outside the
    disk.  The Cayley map is injective, hence no zero--pole pair can cancel.
    Repeated poles are grouped only when their represented roots are exactly
    equal; no caller-controlled numerical threshold changes the exact object.
    """

    roots = _validated_roots(roots)
    zeros_tensor, poles_tensor = mapped_zero_pole(roots)
    zeros = [complex(value.item()) for value in zeros_tensor]
    poles = [complex(value.item()) for value in poles_tensor]
    root_values = [complex(value.item()) for value in roots]

    def grouped_by_root() -> list[dict[str, object]]:
        groups: list[dict[str, object]] = []
        root_to_group: dict[complex, int] = {}
        for root, pole in zip(root_values, poles, strict=True):
            group_index = root_to_group.get(root)
            if group_index is None:
                root_to_group[root] = len(groups)
                groups.append({"pole": _complex_record(pole), "multiplicity": 1})
            else:
                groups[group_index]["multiplicity"] = (
                    int(groups[group_index]["multiplicity"]) + 1
                )
        return groups

    grouped_poles = grouped_by_root()
    return {
        "schema": "gbdn-exact-blaschke-reduced-poles-v2",
        "family": "exact-Blaschke-Cayley-product",
        "factor_count": int(roots.numel()),
        "root_multiset": [_complex_record(value) for value in root_values],
        "numerator_zero_multiset": [_complex_record(value) for value in zeros],
        "unreduced_pole_multiset": grouped_poles,
        "cancellations": [],
        "cancelled_pair_count": 0,
        "reduced_pole_multiset": [dict(entry) for entry in grouped_poles],
        "reduction_policy": (
            "algebraic-admissible-disk-zero-vs-reciprocal-conjugate-pole; "
            "no caller tolerance"
        ),
        "realization_tag": "exact",
        "comparison_domain": "continuum-with-accumulation-point",
    }


def target_pole_diagnostics(roots: torch.Tensor) -> list[dict[str, float]]:
    """Emit descriptive root, target-pole, and ellipse quantities for GA-24."""

    roots = _validated_roots(roots)
    zeros, poles = mapped_zero_pole(roots)
    rows: list[dict[str, float]] = []
    for root, zero, pole in zip(roots, zeros, poles, strict=True):
        root_value = complex(root.item())
        zero_value = complex(zero.item())
        pole_value = complex(pole.item())
        rows.append(
            {
                "root_radius": abs(root_value),
                "root_angle": math.atan2(root_value.imag, root_value.real),
                "mapped_zero_real": zero_value.real,
                "mapped_zero_imag": zero_value.imag,
                "mapped_pole_real": pole_value.real,
                "mapped_pole_imag": pole_value.imag,
                "pole_margin_to_interval": distance_to_interval(
                    pole_value, 0.0, 2.0
                ),
                "bernstein_parameter": bernstein_ellipse_parameter(
                    pole_value - 1.0
                ),
            }
        )
    return rows


def approximation_configuration_diagnostic(
    roots: torch.Tensor,
    degree: int,
    rho: float,
    graph_eigenvalues: torch.Tensor,
    *,
    interval_grid_size: int = 20_001,
) -> ApproximationConfigurationDiagnostic:
    """Join target geometry, certified bounds, and measured approximation error.

    The graph quantity is the maximum scalar error over the supplied spectrum.
    The interval quantity is a deterministic grid maximum and is not presented
    as the exact continuum supremum. Both use the degree-``K`` first-kind
    Chebyshev interpolant targeted by the sparse realization.
    """

    roots = _validated_roots(roots)
    degree = _validated_degree(degree)
    if not isinstance(graph_eigenvalues, torch.Tensor):
        raise TypeError("graph_eigenvalues must be a torch.Tensor")
    if (
        graph_eigenvalues.ndim != 1
        or not graph_eigenvalues.is_floating_point()
        or graph_eigenvalues.is_complex()
    ):
        raise TypeError("graph_eigenvalues must be a one-dimensional real tensor")
    if graph_eigenvalues.numel() == 0:
        raise ValueError("graph_eigenvalues must not be empty")
    if not torch.isfinite(graph_eigenvalues).all():
        raise ValueError("graph_eigenvalues must be finite")
    if torch.any(graph_eigenvalues < 0.0) or torch.any(graph_eigenvalues > 2.0):
        raise ValueError("graph_eigenvalues must lie in [0, 2]")
    if (
        isinstance(interval_grid_size, bool)
        or not isinstance(interval_grid_size, int)
        or interval_grid_size < 2
    ):
        raise ValueError("interval_grid_size must be an integer of at least two")

    rho = _validated_rho(rho)
    rho_star = target_pole_ellipse_parameter(roots)
    m_rho_upper_bound = conservative_ellipse_supremum_bound(roots, rho)
    certified_bound = chebyshev_interpolation_error_bound(roots, degree, rho)

    device = graph_eigenvalues.device
    coefficients = blaschke_product_cheb_coeffs(
        roots,
        degree,
        device,
        convention="forward",
    )
    graph_exact = blaschke_cayley_symbol(graph_eigenvalues, roots)
    graph_approximate = evaluate_chebyshev(coefficients, graph_eigenvalues)
    graph_error = float((graph_exact - graph_approximate).abs().max().item())

    interval = torch.linspace(
        0.0,
        2.0,
        interval_grid_size,
        dtype=graph_eigenvalues.dtype,
        device=device,
    )
    interval_exact = blaschke_cayley_symbol(interval, roots)
    interval_approximate = evaluate_chebyshev(coefficients, interval)
    interval_error = float(
        (interval_exact - interval_approximate).abs().max().item()
    )
    if not math.isfinite(graph_error) or not math.isfinite(interval_error):
        raise OverflowError("measured approximation error is not finite")

    return ApproximationConfigurationDiagnostic(
        realization_tag="chebyshev-K",
        degree=degree,
        chosen_rho=rho,
        pole_limited_rho_star=rho_star,
        conservative_m_rho_upper_bound=m_rho_upper_bound,
        certified_interpolation_error_bound=certified_bound,
        interval_grid_max_error=interval_error,
        graph_spectral_max_error=graph_error,
        interval_grid_size=interval_grid_size,
        graph_eigenvalue_count=graph_eigenvalues.numel(),
        geometry_scope="exact-target",
        target_root_pole_geometry=tuple(target_pole_diagnostics(roots)),
    )
