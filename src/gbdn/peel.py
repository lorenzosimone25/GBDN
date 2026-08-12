"""Validated spectral-peeling diagnostics outside the canonical model API.

These helpers remain for mechanism diagnostics, but they may consume only a
``ValidatedLaplacian``.  They are not definitions of Tight GBDN.  The former
angular-anchor helper named ``oracle_coeffs_for_mode`` is explicitly
quarantined because its name and localization semantics were scientifically
unsafe.
"""

from typing import List, Tuple
import warnings

import torch

from gbdn.core import ValidatedLaplacian
from gbdn.layers import ChebyshevBasis
from gbdn.spectral import (
    Convention,
    blaschke_product_cheb_coeffs,
)


def apply_spectral_filter(h: torch.Tensor, cheb_basis: torch.Tensor, coeffs: torch.Tensor) -> torch.Tensor:
    """Apply sum_k c_k T_k(L) h."""
    weights = coeffs.view(-1, 1, 1)
    return torch.sum(weights * cheb_basis, dim=0)


def peel_layer(
    h: torch.Tensor,
    cheb_basis: torch.Tensor,
    coeffs: torch.Tensor,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Strict peel: h_unwound = filter(h), residual = h - h_unwound."""
    h_unwound = apply_spectral_filter(h, cheb_basis, coeffs)
    return h_unwound, h - h_unwound


def tight_peel_layer(
    h: torch.Tensor,
    cheb_basis: torch.Tensor,
    coeffs: torch.Tensor,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Tight split: h_plus = 0.5(h + T_A h) carried, h_minus = 0.5(h - T_A h) peeled."""
    t_h = apply_spectral_filter(h, cheb_basis, coeffs)
    return 0.5 * (h + t_h), 0.5 * (h - t_h)


def center_width_coeffs_for_mode(
    evals: torch.Tensor,
    idx_target: int,
    K: int,
    device: torch.device,
    width: float = 0.25,
    *,
    convention: Convention = "forward",
) -> torch.Tensor:
    """Return coefficients whose exact mapped zero has the declared center/width."""

    if evals.ndim != 1 or not evals.is_floating_point() or evals.is_complex():
        raise TypeError("evals must be a one-dimensional real floating tensor")
    if evals.numel() == 0 or not torch.isfinite(evals).all():
        raise ValueError("evals must be nonempty and finite")
    if torch.any(evals < 0.0) or torch.any(evals > 2.0):
        raise ValueError("normalized-Laplacian eigenvalues must lie in [0, 2]")
    if not isinstance(idx_target, int) or isinstance(idx_target, bool):
        raise TypeError("idx_target must be an integer")
    if not 0 <= idx_target < evals.numel():
        raise IndexError("idx_target is outside the eigenvalue vector")
    width = float(width)
    if not torch.isfinite(torch.tensor(width)) or width <= 0.0:
        raise ValueError("width must be finite and positive")
    center = evals[idx_target].to(device=device)
    width_tensor = torch.as_tensor(width, dtype=center.dtype, device=device)
    mapped_zero = torch.complex(center, width_tensor)
    imaginary_unit = torch.complex(
        torch.zeros_like(center), torch.ones_like(center)
    )
    root = ((mapped_zero - imaginary_unit) / (mapped_zero + imaginary_unit)).reshape(1)
    return blaschke_product_cheb_coeffs(
        root,
        K,
        device,
        convention=convention,
    )


def oracle_coeffs_for_mode(*args, **kwargs) -> torch.Tensor:
    """Quarantined pre-contract angular-anchor helper.

    Use :func:`center_width_coeffs_for_mode`, whose center and half-width are
    exact mapped-zero quantities and whose conjugation convention is explicit.
    """

    del args, kwargs
    raise RuntimeError(
        "oracle_coeffs_for_mode is quarantined: its scaled-Cayley angular "
        "anchor was not an exact spectral center. Use "
        "center_width_coeffs_for_mode with an explicit convention."
    )


def _basis_from_validated_laplacian(
    h: torch.Tensor,
    laplacian: ValidatedLaplacian,
    K: int,
) -> torch.Tensor:
    if not isinstance(laplacian, ValidatedLaplacian):
        raise TypeError(
            "peeling diagnostics require a ValidatedLaplacian token; route "
            "directed inputs through preprocess_reciprocal_mean first"
        )
    empty_edges = torch.empty((2, 0), dtype=torch.long, device=h.device)
    return ChebyshevBasis(K)(
        h,
        empty_edges,
        num_nodes=h.shape[0],
        laplacian=laplacian,
    )


def peel_sequence(
    h0: torch.Tensor,
    laplacian: ValidatedLaplacian,
    layer_specs: List[torch.Tensor],
    K: int,
) -> dict:
    """
    Apply a sequence of spectral filters (coeffs per layer).

    layer_specs: list of complex coeff tensors [K+1]
  Returns dict with h, residuals, unwound per step.
    """
    h = h0
    residuals = []
    unwound = []
    hs = [h0]

    for coeffs in layer_specs:
        basis = _basis_from_validated_laplacian(h, laplacian, K)
        h_u, r = peel_layer(h, basis, coeffs)
        residuals.append(r)
        unwound.append(h_u)
        h = h_u
        hs.append(h)

    return {"hs": hs, "residuals": residuals, "unwound": unwound}


def tight_peel_sequence(
    h0: torch.Tensor,
    laplacian: ValidatedLaplacian,
    layer_specs: List[torch.Tensor],
    K: int,
) -> dict:
    """Tight two-channel peeling sequence.

    Carries h_plus forward and stores each h_minus residual. Returns dict with
    carried states ``hs``, peeled ``residuals``, and per-step energy components
    for verifying ||h^(ell)||^2 = ||h^(ell+1)||^2 + ||r^(ell)||^2.
    """
    h = h0
    residuals = []
    hs = [h0]
    energy = []

    for coeffs in layer_specs:
        basis = _basis_from_validated_laplacian(h, laplacian, K)
        h_plus, h_minus = tight_peel_layer(h, basis, coeffs)
        energy.append(
            (
                (h.abs() ** 2).sum().item(),
                (h_plus.abs() ** 2).sum().item(),
                (h_minus.abs() ** 2).sum().item(),
            )
        )
        residuals.append(h_minus)
        h = h_plus
        hs.append(h)

    return {"hs": hs, "residuals": residuals, "energy": energy}


def strict_forward_states(
    model,
    x: torch.Tensor,
    laplacian: ValidatedLaplacian,
) -> dict:
    """Run deprecated GBDNStrict diagnostics with a validated operator token."""

    warnings.warn(
        "strict_forward_states is a legacy-model diagnostic and cannot define "
        "the canonical revised method",
        DeprecationWarning,
        stacklevel=2,
    )
    x_lift = model.lifting(x)
    h = torch.complex(
        x_lift[:, : x_lift.shape[1] // 2],
        x_lift[:, x_lift.shape[1] // 2 :],
    )
    hs = [h]
    residuals = []
    alphas = []

    for layer in model.layers:
        basis = _basis_from_validated_laplacian(
            h,
            laplacian,
            model.cheb_computer.K,
        )
        h, r, alpha = layer(h, basis)
        residuals.append(r)
        alphas.append(alpha)
        hs.append(h)

    return {"hs": hs, "residuals": residuals, "alphas": alphas, "final": h}
