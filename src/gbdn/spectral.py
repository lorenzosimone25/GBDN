"""Blaschke--Cayley spectral operators under the canonical forward convention.

The revision uses

    phi(lambda) = (lambda - i) / (lambda + i)
    T_A = B_A(phi(L)).

Inverse factors remain available only through an explicit ``convention``
argument.  Exact helpers preserve double precision so theorem tests can use
strict numerical tolerances.
"""

from __future__ import annotations

import math
from typing import Literal, Sequence

import torch

Convention = Literal["forward", "inverse"]
_REAL_TO_COMPLEX_DTYPE = {
    torch.float32: torch.complex64,
    torch.float64: torch.complex128,
}


def _check_convention(convention: Convention) -> Convention:
    if convention not in {"forward", "inverse"}:
        raise ValueError(
            f"convention must be 'forward' or 'inverse', got {convention!r}"
        )
    return convention


def _apply_convention(values: torch.Tensor, convention: Convention) -> torch.Tensor:
    _check_convention(convention)
    return torch.conj(values) if convention == "inverse" else values


def _validate_degree(K: int) -> int:
    if isinstance(K, bool) or not isinstance(K, int) or K < 0:
        raise ValueError(f"K must be a nonnegative integer, got {K!r}")
    return K


def _validate_real_values(
    values: torch.Tensor,
    *,
    name: str,
    normalized_laplacian_spectrum: bool = False,
) -> torch.Tensor:
    if not isinstance(values, torch.Tensor):
        raise TypeError(f"{name} must be a torch.Tensor")
    if values.is_complex() or not values.is_floating_point():
        raise TypeError(f"{name} must use a real floating dtype")
    if values.dtype not in _REAL_TO_COMPLEX_DTYPE:
        raise TypeError(f"{name} must use float32 or float64")
    if values.numel() == 0:
        raise ValueError(f"{name} must be nonempty")
    if not torch.isfinite(values).all():
        raise ValueError(f"{name} must be finite")
    if normalized_laplacian_spectrum:
        tolerance = max(1e-12, 32.0 * torch.finfo(values.dtype).eps)
        lower = float(values.min().item())
        upper = float(values.max().item())
        if lower < -tolerance or upper > 2.0 + tolerance:
            raise ValueError(
                f"{name} must lie in [0, 2], got [{lower}, {upper}]"
            )
    return values


def _validate_admissible_roots(
    roots: torch.Tensor,
    *,
    reference: torch.Tensor | None = None,
    name: str = "roots",
    allow_empty: bool = True,
) -> torch.Tensor:
    if not isinstance(roots, torch.Tensor):
        raise TypeError(f"{name} must be a torch.Tensor")
    if not roots.is_complex():
        raise TypeError(f"{name} must use a complex dtype")
    roots = roots.reshape(-1)
    if roots.numel() == 0 and not allow_empty:
        raise ValueError(f"{name} must be nonempty")
    if roots.dtype not in {torch.complex64, torch.complex128}:
        raise TypeError(f"{name} must use complex64 or complex128")
    if reference is not None:
        expected_dtype = _REAL_TO_COMPLEX_DTYPE[reference.dtype]
        if roots.dtype != expected_dtype:
            raise TypeError(
                f"{name} dtype must match spectral precision: expected "
                f"{expected_dtype}, got {roots.dtype}"
            )
        if roots.device != reference.device:
            raise ValueError(f"{name} and spectral values must share a device")
    if not torch.isfinite(roots).all():
        raise ValueError(f"{name} must be finite")
    if torch.any(roots.abs() >= 1.0):
        singular_name = name[:-1] if name.endswith("s") else name
        raise ValueError(
            f"every {singular_name} must lie strictly inside the unit disk"
        )
    return roots


def chebyshev_nodes(
    K: int,
    device: torch.device,
    dtype: torch.dtype = torch.float32,
) -> torch.Tensor:
    """Return Chebyshev nodes on ``[-1, 1]`` mapped to ``[0, 2]``."""
    _validate_degree(K)
    if not isinstance(device, torch.device):
        raise TypeError("device must be a torch.device")
    if dtype not in _REAL_TO_COMPLEX_DTYPE:
        raise TypeError("Chebyshev nodes require float32 or float64")
    k_indices = torch.arange(K + 1, device=device, dtype=dtype)
    nodes = torch.cos(math.pi * (k_indices + 0.5) / (K + 1))
    return nodes + 1.0


def cayley_map(lambdas: torch.Tensor) -> torch.Tensor:
    """Map finite real values to the unit circle.

    This scalar analytic map intentionally accepts values outside ``[0, 2]``;
    normalized-Laplacian range validation belongs to operator constructors.
    """
    lambdas = _validate_real_values(lambdas, name="lambdas")
    one = torch.ones_like(lambdas)
    return torch.complex(lambdas, -one) / torch.complex(lambdas, one)


def blaschke_factor(zeta: torch.Tensor, alpha: torch.Tensor) -> torch.Tensor:
    """Evaluate one low-level analytic factor after domain validation.

    This helper does not construct a graph operator. ``zeta`` may be any
    finite complex evaluation tensor, while ``alpha`` must be one admissible
    disk root. Use :func:`blaschke_cayley_exact` for a validated graph
    spectral operator.
    """
    if not isinstance(zeta, torch.Tensor) or not zeta.is_complex():
        raise TypeError("zeta must be a complex torch.Tensor")
    if zeta.numel() == 0 or not torch.isfinite(zeta).all():
        raise ValueError("zeta must be nonempty and finite")
    roots = _validate_admissible_roots(
        alpha,
        name="alpha",
        allow_empty=False,
    )
    if roots.numel() != 1:
        raise ValueError("alpha must contain exactly one root")
    root = roots[0]
    if root.dtype != zeta.dtype:
        raise TypeError("alpha and zeta must have the same complex dtype")
    if root.device != zeta.device:
        raise ValueError("alpha and zeta must be on the same device")
    result = (zeta - root) / (1.0 - torch.conj(root) * zeta)
    if not torch.isfinite(result).all():
        raise ValueError("Blaschke factor is singular or nonfinite at zeta")
    return result


def blaschke_product(zeta: torch.Tensor, alphas: torch.Tensor) -> torch.Tensor:
    """Evaluate a low-level finite product for validated disk roots.

    This is an analytic scalar/tensor evaluator, not an eigendecomposition or
    graph-operator validation boundary.
    """
    if not isinstance(zeta, torch.Tensor) or not zeta.is_complex():
        raise TypeError("zeta must be a complex torch.Tensor")
    if zeta.numel() == 0 or not torch.isfinite(zeta).all():
        raise ValueError("zeta must be nonempty and finite")
    alphas = _validate_admissible_roots(alphas)
    if alphas.dtype != zeta.dtype:
        raise TypeError("roots and zeta must have the same complex dtype")
    if alphas.device != zeta.device:
        raise ValueError("roots and zeta must be on the same device")
    out = torch.ones_like(zeta)
    for alpha in alphas:
        out = out * blaschke_factor(zeta, alpha)
    return out


def parameterize_roots(
    root_params: torch.Tensor,
    r_max: float = 0.95,
) -> torch.Tensor:
    """Map ``[..., (radial_logit, angle)]`` parameters into the open disk.

    The returned roots satisfy ``|alpha| < r_max`` for every finite radial
    logit.  This replaces independent Cartesian ``tanh`` constraints, which do
    not constrain the complex modulus.
    """
    if root_params.shape[-1] != 2:
        raise ValueError(
            "root_params must have final dimension 2: (radial_logit, angle)"
        )
    if not root_params.is_floating_point():
        raise TypeError("root_params must use a floating dtype")
    if not torch.isfinite(root_params).all():
        raise ValueError("root_params must be finite")
    if not 0.0 < r_max < 1.0:
        raise ValueError(f"r_max must lie in (0, 1), got {r_max}")
    # Leave a few ulps of margin so Cartesian reconstruction by ``torch.polar``
    # cannot round the complex modulus above the declared radius bound.
    margin = 1.0 - 8.0 * torch.finfo(root_params.dtype).eps
    radius = (r_max * margin) * torch.sigmoid(root_params[..., 0])
    angle = root_params[..., 1]
    return torch.polar(radius, angle)


def parameterize_center_width_roots(
    center_width_params: torch.Tensor,
    *,
    gamma_min: float = 0.02,
    gamma_max: float = 2.0,
) -> torch.Tensor:
    """Map finite raw parameters to roots with exact center-width semantics.

    ``mu = 2 sigmoid(raw_mu)`` and
    ``gamma = gamma_min + (gamma_max-gamma_min) sigmoid(raw_gamma)`` define the
    mapped zero ``mu + i gamma``. The inverse Cayley map then yields a root
    strictly inside the unit disk for every finite parameter pair.
    """

    if center_width_params.shape[-1] != 2:
        raise ValueError(
            "center_width_params must have final dimension 2: "
            "(center_logit, width_logit)"
        )
    if not center_width_params.is_floating_point():
        raise TypeError("center_width_params must use a floating dtype")
    if not torch.isfinite(center_width_params).all():
        raise ValueError("center_width_params must be finite")
    if not 0.0 < gamma_min < gamma_max:
        raise ValueError(
            "gamma bounds must satisfy 0 < gamma_min < gamma_max, got "
            f"[{gamma_min}, {gamma_max}]"
        )
    center = 2.0 * torch.sigmoid(center_width_params[..., 0])
    width = gamma_min + (gamma_max - gamma_min) * torch.sigmoid(
        center_width_params[..., 1]
    )
    mapped_zero = torch.complex(center, width)
    imaginary_unit = torch.complex(torch.zeros_like(center), torch.ones_like(center))
    return (mapped_zero - imaginary_unit) / (mapped_zero + imaginary_unit)


def center_width_from_root(alpha: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Recover the exact mapped-zero center and half-width from disk roots."""

    if not alpha.is_complex():
        raise TypeError("alpha must use a complex dtype")
    if not torch.isfinite(alpha).all():
        raise ValueError("alpha must be finite")
    if torch.any(alpha.abs() >= 1.0):
        raise ValueError("every root must lie strictly inside the unit disk")
    mapped_zero, _ = mapped_zero_pole(alpha)
    return mapped_zero.real, mapped_zero.imag


def constrain_alpha(
    root_params: torch.Tensor,
    scale: float = 0.95,
) -> torch.Tensor:
    """Deprecated compatibility alias for :func:`parameterize_roots`.

    Inputs now represent ``(radial_logit, angle)`` pairs rather than Cartesian
    coordinates.  New code should call :func:`parameterize_roots` explicitly.
    """
    return parameterize_roots(root_params, r_max=scale)


def mapped_zero_pole(alpha: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Return exact mapped zero/pole geometry for admissible disk roots."""
    if not isinstance(alpha, torch.Tensor):
        raise TypeError("alpha must be a torch.Tensor")
    original_shape = alpha.shape
    alpha = _validate_admissible_roots(alpha, name="alpha")
    one = torch.ones_like(alpha)
    imag = torch.complex(torch.zeros_like(alpha.real), torch.ones_like(alpha.real))
    zero = imag * (one + alpha) / (one - alpha)
    pole = torch.conj(zero)
    return zero.reshape(original_shape), pole.reshape(original_shape)


def dct_synthesis(f_nodes: torch.Tensor, K: int) -> torch.Tensor:
    """Map Chebyshev-node samples to interpolation coefficients."""
    _validate_degree(K)
    if not isinstance(f_nodes, torch.Tensor):
        raise TypeError("f_nodes must be a torch.Tensor")
    if f_nodes.ndim == 0:
        raise ValueError("f_nodes must have a node-sample dimension")
    if not (f_nodes.is_floating_point() or f_nodes.is_complex()):
        raise TypeError("f_nodes must use a floating or complex dtype")
    if f_nodes.shape[-1] != K + 1:
        raise ValueError("f_nodes must contain exactly K+1 node samples")
    if not torch.isfinite(f_nodes).all():
        raise ValueError("f_nodes must be finite")
    dtype = f_nodes.real.dtype
    device = f_nodes.device
    k_indices = torch.arange(K + 1, device=device, dtype=dtype)
    coeffs = []
    norm = 2.0 / (K + 1)
    for degree in range(K + 1):
        basis = torch.cos(
            degree * math.pi * (k_indices + 0.5) / (K + 1)
        )
        coeffs.append(norm * torch.sum(f_nodes * basis, dim=-1))
    coeffs[0] = coeffs[0] * 0.5
    return torch.stack(coeffs, dim=0)


def blaschke_product_cheb_coeffs(
    alphas: torch.Tensor,
    K: int,
    device: torch.device,
    convention: Convention = "forward",
) -> torch.Tensor:
    """Chebyshev coefficients for a finite Blaschke--Cayley product."""
    _validate_degree(K)
    _check_convention(convention)
    if not isinstance(device, torch.device):
        raise TypeError("device must be a torch.device")
    alphas = _validate_admissible_roots(alphas)
    real_dtype = alphas.real.dtype
    lambdas = chebyshev_nodes(K, device, dtype=real_dtype)
    nodes = cayley_map(lambdas)
    values = blaschke_product(nodes, alphas.to(device=device, dtype=nodes.dtype))
    values = _apply_convention(values, convention)
    return dct_synthesis(values, K)


def blaschke_cheb_coeffs(
    alpha_real: torch.Tensor,
    alpha_imag: torch.Tensor,
    K: int,
    device: torch.device,
    convention: Convention = "forward",
) -> torch.Tensor:
    """Chebyshev coefficients for one Blaschke--Cayley factor."""
    if not isinstance(alpha_real, torch.Tensor) or not isinstance(
        alpha_imag, torch.Tensor
    ):
        raise TypeError("alpha_real and alpha_imag must be torch.Tensor values")
    if alpha_real.shape != alpha_imag.shape:
        raise ValueError("alpha_real and alpha_imag must have the same shape")
    if (
        not alpha_real.is_floating_point()
        or not alpha_imag.is_floating_point()
        or alpha_real.dtype != alpha_imag.dtype
    ):
        raise TypeError("alpha_real and alpha_imag must share a real floating dtype")
    if alpha_real.device != alpha_imag.device:
        raise ValueError("alpha_real and alpha_imag must share a device")
    alpha = torch.complex(alpha_real, alpha_imag).reshape(-1)
    return blaschke_product_cheb_coeffs(alpha, K, device, convention=convention)


def evaluate_chebyshev(
    coeffs: torch.Tensor,
    evals: torch.Tensor,
) -> torch.Tensor:
    """Evaluate ``sum_k c_k T_k(lambda-1)`` on real eigenvalues."""
    if not isinstance(coeffs, torch.Tensor):
        raise TypeError("coeffs must be a torch.Tensor")
    if coeffs.ndim != 1 or coeffs.numel() == 0:
        raise ValueError("coeffs must be a nonempty one-dimensional tensor")
    if not (coeffs.is_floating_point() or coeffs.is_complex()):
        raise TypeError("coeffs must use a floating or complex dtype")
    if coeffs.real.dtype not in _REAL_TO_COMPLEX_DTYPE:
        raise TypeError("coeffs must use float32/complex64 or float64/complex128")
    if not torch.isfinite(coeffs).all():
        raise ValueError("coeffs must be finite")
    evals = _validate_real_values(evals, name="evals")
    if evals.dtype != coeffs.real.dtype:
        raise TypeError("evals and coeffs must use matching real precision")
    if evals.device != coeffs.device:
        raise ValueError("evals and coeffs must share a device")
    x = evals - 1.0
    degree = coeffs.shape[0] - 1
    t_prev2 = torch.ones_like(x)
    values = coeffs[0] * t_prev2
    if degree == 0:
        return values
    t_prev = x
    values = values + coeffs[1] * t_prev
    for k in range(2, degree + 1):
        t_next = 2.0 * x * t_prev - t_prev2
        values = values + coeffs[k] * t_next
        t_prev2, t_prev = t_prev, t_next
    return values


def spectral_response(
    evals: torch.Tensor,
    alpha_real: float,
    alpha_imag: float,
    K: int = 32,
    device: torch.device | None = None,
    convention: Convention = "forward",
) -> torch.Tensor:
    """Approximate the magnitude response of one factor on eigenvalues."""
    evals = _validate_real_values(evals, name="evals")
    if device is None:
        device = evals.device
    if not isinstance(device, torch.device):
        raise TypeError("device must be a torch.device")
    if device != evals.device:
        raise ValueError("device must match evals.device")
    dtype = evals.dtype if evals.is_floating_point() else torch.get_default_dtype()
    alpha_real_t = torch.tensor(alpha_real, device=device, dtype=dtype)
    alpha_imag_t = torch.tensor(alpha_imag, device=device, dtype=dtype)
    coeffs = blaschke_cheb_coeffs(
        alpha_real_t,
        alpha_imag_t,
        K,
        device,
        convention=convention,
    )
    return evaluate_chebyshev(coeffs, evals).abs()


def blaschke_cayley_symbol(
    lambdas: torch.Tensor,
    alphas: torch.Tensor,
    convention: Convention = "forward",
) -> torch.Tensor:
    """Evaluate the exact scalar symbol on finite real spectral values.

    Values outside ``[0, 2]`` are intentionally supported for analytic
    pointwise identities. This function does not certify that its inputs are
    an eigendecomposition; use :func:`blaschke_cayley_exact` for that public
    operator boundary.
    """
    lambdas = _validate_real_values(lambdas, name="lambdas")
    alphas = _validate_admissible_roots(
        alphas,
        reference=lambdas,
    )
    _check_convention(convention)
    zeta = cayley_map(lambdas)
    return _apply_convention(blaschke_product(zeta, alphas), convention)


def blaschke_cayley_exact(
    evals: torch.Tensor,
    evecs: torch.Tensor,
    alphas: torch.Tensor,
    convention: Convention = "forward",
) -> torch.Tensor:
    """Construct a validated exact normalized-Laplacian spectral operator.

    The public boundary rejects malformed, nonorthonormal, out-of-range, or
    precision/device-inconsistent spectral data before assembly. Validation is
    shared with the dense oracle, while scalar evaluation and matrix assembly
    remain separate production arithmetic.
    """
    from gbdn.oracle import validate_exact_blaschke_eigendecomposition

    validate_exact_blaschke_eigendecomposition(
        evals,
        evecs,
        alphas,
        convention=convention,
    )
    symbol = blaschke_cayley_symbol(evals, alphas, convention=convention)
    vectors = evecs.to(dtype=symbol.dtype)
    return (vectors * symbol.unsqueeze(0)) @ vectors.mH


def tight_split_responses(
    lambdas: torch.Tensor,
    alphas: torch.Tensor,
    convention: Convention = "forward",
) -> dict[str, torch.Tensor]:
    """Return phase, phase derivative, and complementary channel responses."""
    lambdas = _validate_real_values(lambdas, name="lambdas")
    alphas = _validate_admissible_roots(alphas, reference=lambdas)
    _check_convention(convention)
    symbol = blaschke_cayley_symbol(lambdas, alphas, convention=convention)
    phase = torch.angle(symbol)
    p_plus = 0.5 * (1.0 + symbol)
    p_minus = 0.5 * (1.0 - symbol)

    lam = lambdas.to(dtype=symbol.real.dtype)
    zeta = cayley_map(lam)
    theta_derivative = 2.0 / (1.0 + lam.square())
    phase_derivative = torch.zeros_like(lam)
    sign = 1.0 if convention == "forward" else -1.0
    eps = torch.finfo(lam.dtype).eps
    for alpha in alphas.to(device=zeta.device, dtype=zeta.dtype).reshape(-1):
        poisson = (1.0 - alpha.abs().square()) / ((zeta - alpha).abs().square() + eps)
        phase_derivative = phase_derivative + sign * poisson * theta_derivative

    return {
        "symbol": symbol,
        "phase": phase,
        "phase_derivative": phase_derivative,
        # Compatibility aliases for existing plotting code.
        "psi": phase,
        "dpsi": phase_derivative,
        "p_plus": p_plus,
        "p_minus": p_minus,
        "p_plus_sq": p_plus.abs().square(),
        "p_minus_sq": p_minus.abs().square(),
        "residual": p_minus.abs(),
    }


def multilevel_tight_analysis(
    h: torch.Tensor,
    operators: Sequence[torch.Tensor],
) -> tuple[list[torch.Tensor], torch.Tensor]:
    """Apply exact tight analysis for a sequence of square operators."""
    carry = h
    bands: list[torch.Tensor] = []
    for operator in operators:
        transformed = operator @ carry
        bands.append(0.5 * (carry - transformed))
        carry = 0.5 * (carry + transformed)
    return bands, carry


def multilevel_tight_synthesis(
    bands: Sequence[torch.Tensor],
    final_carry: torch.Tensor,
    operators: Sequence[torch.Tensor],
) -> torch.Tensor:
    """Reconstruct exact tight-analysis coefficients with adjoint synthesis."""
    if len(bands) != len(operators):
        raise ValueError("bands and operators must have the same length")
    carry = final_carry
    for band, operator in zip(reversed(bands), reversed(operators)):
        adjoint = operator.conj().transpose(-1, -2)
        carry = 0.5 * (carry + band) + 0.5 * (adjoint @ (carry - band))
    return carry


def alpha_from_eigenvalue(
    lam: torch.Tensor,
    scale: float = 0.9,
) -> torch.Tensor:
    """Place a root radially inside the Cayley image of an eigenvalue."""
    zeta = cayley_map(lam.reshape(1)).squeeze()
    return scale * zeta / zeta.abs().clamp_min(torch.finfo(zeta.real.dtype).eps)
