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


def _check_convention(convention: Convention) -> Convention:
    if convention not in {"forward", "inverse"}:
        raise ValueError(
            f"convention must be 'forward' or 'inverse', got {convention!r}"
        )
    return convention


def _apply_convention(values: torch.Tensor, convention: Convention) -> torch.Tensor:
    _check_convention(convention)
    return torch.conj(values) if convention == "inverse" else values


def chebyshev_nodes(
    K: int,
    device: torch.device,
    dtype: torch.dtype = torch.float32,
) -> torch.Tensor:
    """Return Chebyshev nodes on ``[-1, 1]`` mapped to ``[0, 2]``."""
    if K < 0:
        raise ValueError(f"K must be nonnegative, got {K}")
    k_indices = torch.arange(K + 1, device=device, dtype=dtype)
    nodes = torch.cos(math.pi * (k_indices + 0.5) / (K + 1))
    return nodes + 1.0


def cayley_map(lambdas: torch.Tensor) -> torch.Tensor:
    """Map real Laplacian eigenvalues to the unit circle."""
    if not lambdas.is_floating_point():
        lambdas = lambdas.to(torch.get_default_dtype())
    one = torch.ones_like(lambdas)
    return torch.complex(lambdas, -one) / torch.complex(lambdas, one)


def blaschke_factor(zeta: torch.Tensor, alpha: torch.Tensor) -> torch.Tensor:
    """Evaluate ``B_alpha(zeta)=(zeta-alpha)/(1-conj(alpha) zeta)``."""
    return (zeta - alpha) / (1.0 - torch.conj(alpha) * zeta)


def blaschke_product(zeta: torch.Tensor, alphas: torch.Tensor) -> torch.Tensor:
    """Evaluate a finite Blaschke product for roots strictly inside the disk."""
    out = torch.ones_like(zeta)
    for alpha in alphas.reshape(-1):
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
    if not 0.0 < r_max < 1.0:
        raise ValueError(f"r_max must lie in (0, 1), got {r_max}")
    # Leave a few ulps of margin so Cartesian reconstruction by ``torch.polar``
    # cannot round the complex modulus above the declared radius bound.
    margin = 1.0 - 8.0 * torch.finfo(root_params.dtype).eps
    radius = (r_max * margin) * torch.sigmoid(root_params[..., 0])
    angle = root_params[..., 1]
    return torch.polar(radius, angle)


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
    """Return the zero and pole of ``B_alpha(phi(lambda))`` in the lambda plane."""
    one = torch.ones_like(alpha)
    imag = torch.complex(torch.zeros_like(alpha.real), torch.ones_like(alpha.real))
    zero = imag * (one + alpha) / (one - alpha)
    pole = torch.conj(zero)
    return zero, pole


def dct_synthesis(f_nodes: torch.Tensor, K: int) -> torch.Tensor:
    """Map Chebyshev-node samples to interpolation coefficients."""
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
    alpha = torch.complex(alpha_real, alpha_imag).reshape(-1)
    return blaschke_product_cheb_coeffs(alpha, K, device, convention=convention)


def evaluate_chebyshev(
    coeffs: torch.Tensor,
    evals: torch.Tensor,
) -> torch.Tensor:
    """Evaluate ``sum_k c_k T_k(lambda-1)`` on real eigenvalues."""
    x = evals.to(dtype=coeffs.real.dtype, device=coeffs.device) - 1.0
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
    if device is None:
        device = evals.device
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
    """Evaluate the exact spectral symbol on real Laplacian eigenvalues."""
    zeta = cayley_map(lambdas)
    roots = alphas.to(device=zeta.device, dtype=zeta.dtype)
    return _apply_convention(blaschke_product(zeta, roots), convention)


def blaschke_cayley_exact(
    evals: torch.Tensor,
    evecs: torch.Tensor,
    alphas: torch.Tensor,
    convention: Convention = "forward",
) -> torch.Tensor:
    """Construct the exact dense operator ``U diag(B_A(phi(lambda))) U*``."""
    symbol = blaschke_cayley_symbol(evals, alphas, convention=convention)
    vectors = evecs.to(device=symbol.device, dtype=symbol.dtype)
    return (vectors * symbol.unsqueeze(0)) @ vectors.conj().transpose(-1, -2)


def tight_split_responses(
    lambdas: torch.Tensor,
    alphas: torch.Tensor,
    convention: Convention = "forward",
) -> dict[str, torch.Tensor]:
    """Return phase, phase derivative, and complementary channel responses."""
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
