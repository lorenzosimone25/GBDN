"""Spectral peeling utilities."""

from typing import List, Tuple

import torch

from gbdn.layers import ChebyshevBasis
from gbdn.spectral import (
    alpha_from_eigenvalue,
    blaschke_cheb_coeffs,
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


def oracle_coeffs_for_mode(
    evals: torch.Tensor,
    idx_target: int,
    K: int,
    device: torch.device,
    scale: float = 0.9,
) -> torch.Tensor:
    """Inverse Blaschke coeffs with root at Cayley image of target eigenvalue."""
    alpha = alpha_from_eigenvalue(evals[idx_target], scale=scale)
    return blaschke_cheb_coeffs(alpha.real, alpha.imag, K, device).conj()


def peel_sequence(
    h0: torch.Tensor,
    edge_index,
    layer_specs: List[torch.Tensor],
    K: int,
) -> dict:
    """
    Apply a sequence of spectral filters (coeffs per layer).

    layer_specs: list of complex coeff tensors [K+1]
  Returns dict with h, residuals, unwound per step.
    """
    basis_module = ChebyshevBasis(K)
    h = h0
    residuals = []
    unwound = []
    hs = [h0]

    for coeffs in layer_specs:
        basis = basis_module(h, edge_index)
        h_u, r = peel_layer(h, basis, coeffs)
        residuals.append(r)
        unwound.append(h_u)
        h = h_u
        hs.append(h)

    return {"hs": hs, "residuals": residuals, "unwound": unwound}


def tight_peel_sequence(
    h0: torch.Tensor,
    edge_index,
    layer_specs: List[torch.Tensor],
    K: int,
) -> dict:
    """Tight two-channel peeling sequence.

    Carries h_plus forward and stores each h_minus residual. Returns dict with
    carried states ``hs``, peeled ``residuals``, and per-step energy components
    for verifying ||h^(ell)||^2 = ||h^(ell+1)||^2 + ||r^(ell)||^2.
    """
    basis_module = ChebyshevBasis(K)
    h = h0
    residuals = []
    hs = [h0]
    energy = []

    for coeffs in layer_specs:
        basis = basis_module(h, edge_index)
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


def strict_forward_states(model, x, edge_index) -> dict:
    """Run GBDNStrict and capture per-layer hidden states and residuals."""
    x_lift = model.lifting(x)
    h = torch.complex(
        x_lift[:, : x_lift.shape[1] // 2],
        x_lift[:, x_lift.shape[1] // 2 :],
    )
    hs = [h]
    residuals = []
    alphas = []

    for layer in model.layers:
        basis = model.cheb_computer(h, edge_index)
        h, r, alpha = layer(h, basis)
        residuals.append(r)
        alphas.append(alpha)
        hs.append(h)

    return {"hs": hs, "residuals": residuals, "alphas": alphas, "final": h}
