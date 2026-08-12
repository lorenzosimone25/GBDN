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

from gbdn.spectral import blaschke_cayley_symbol, mapped_zero_pole


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


def multilevel_frame_bound(errors: Sequence[float]) -> FrameBoundDiagnostic:
    """Compute the frozen heterogeneous ``Delta_D`` recurrence.

    Every input must be a finite, nonnegative, true operator-norm error.
    """

    checked: list[float] = []
    defects: list[float] = []
    amplifications: list[float] = []
    prefix = 1.0
    delta = 0.0
    for raw_error in errors:
        error = float(raw_error)
        if not math.isfinite(error) or error < 0.0:
            raise ValueError("operator errors must be finite and nonnegative")
        defect = error + 0.5 * error * error
        amplification = (1.0 + 0.5 * error) ** 2
        delta += defect * prefix
        prefix *= amplification
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
    radical = cmath.sqrt(value * value - 1.0)
    return max(abs(value + radical), abs(value - radical))


def target_pole_ellipse_parameter(roots: torch.Tensor) -> float:
    """Return the nearest reduced target-pole ellipse parameter on ``[0,2]``."""

    if roots.numel() == 0:
        raise ValueError("at least one root is required")
    zeros, poles = mapped_zero_pole(roots.reshape(-1))
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

    rho = float(rho)
    if not math.isfinite(rho) or rho <= 1.0:
        raise ValueError("rho must be finite and greater than one")
    if roots.numel() == 0:
        raise ValueError("at least one root is required")
    zeros, poles = mapped_zero_pole(roots.reshape(-1))
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
    return float(bound)


def chebyshev_interpolation_error_bound(
    roots: torch.Tensor,
    degree: int,
    rho: float,
) -> float:
    """Return a certified first-kind Chebyshev interpolation error bound."""

    if isinstance(degree, bool) or not isinstance(degree, int) or degree < 0:
        raise ValueError("degree must be a nonnegative integer")
    if rho >= target_pole_ellipse_parameter(roots):
        raise ValueError("rho must lie strictly inside every target-pole ellipse")
    supremum = conservative_ellipse_supremum_bound(roots, rho)
    return 4.0 * supremum * rho ** (-degree) / (rho - 1.0)


def distance_to_interval(point: complex, lower: float, upper: float) -> float:
    """Euclidean distance from a complex point to a closed real interval."""

    value = complex(point)
    if value.real < lower:
        real_distance = lower - value.real
    elif value.real > upper:
        real_distance = value.real - upper
    else:
        real_distance = 0.0
    return math.hypot(real_distance, value.imag)


def fixed_root_perturbation_constant(roots: torch.Tensor) -> float:
    """Return the product telescoping constant for spectra in ``[0,2]``."""

    if roots.numel() == 0:
        raise ValueError("at least one root is required")
    zeros, poles = mapped_zero_pole(roots.reshape(-1))
    constant = 0.0
    for zero, pole in zip(zeros, poles, strict=True):
        zero_value = complex(zero.item())
        pole_value = complex(pole.item())
        margin = distance_to_interval(pole_value, 0.0, 2.0)
        if margin <= 0.0:
            raise ValueError("target pole must have positive distance from [0,2]")
        constant += abs(pole_value - zero_value) / (margin * margin)
    return float(constant)


def product_sum_evaluation_matrix(
    eigenvalues: torch.Tensor,
    roots: torch.Tensor,
) -> torch.Tensor:
    """Evaluate ``(1,q_1,...,q_D)`` for one nonzero root per factor."""

    if eigenvalues.ndim != 1 or not eigenvalues.is_floating_point():
        raise TypeError("eigenvalues must be a one-dimensional real tensor")
    if roots.ndim != 1 or not roots.is_complex():
        raise TypeError("roots must be a one-dimensional complex tensor")
    if torch.any(roots.abs() <= 0.0) or torch.any(roots.abs() >= 1.0):
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

    zeros, poles = mapped_zero_pole(roots.reshape(-1))
    rows: list[dict[str, float]] = []
    for root, zero, pole in zip(roots.reshape(-1), zeros, poles, strict=True):
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
