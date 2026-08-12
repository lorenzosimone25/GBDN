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
    root_pole_geometry: tuple[dict[str, float], ...]

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
        root_pole_geometry=tuple(target_pole_diagnostics(roots)),
    )
