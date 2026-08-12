"""Sparse Chebyshev realization of the revised GBDN filter families."""

from __future__ import annotations

import warnings

import torch
import torch.nn as nn
from torch_geometric.utils import get_laplacian

from gbdn.spectral import (
    Convention,
    blaschke_product_cheb_coeffs,
    parameterize_roots,
)


def initial_root_parameters(num_roots: int) -> torch.Tensor:
    """Initialize small positive radii and zero angles."""
    params = torch.zeros(num_roots, 2)
    params[:, 0] = -2.0
    return params


def normalized_laplacian(
    edge_index: torch.Tensor,
    edge_weight: torch.Tensor | None = None,
    num_nodes: int | None = None,
    *,
    device: torch.device | None = None,
) -> torch.Tensor:
    """Build a coalesced symmetric normalized Laplacian."""
    if num_nodes is None:
        num_nodes = int(edge_index.max().item()) + 1
    lap_index, lap_weight = get_laplacian(
        edge_index,
        edge_weight,
        normalization="sym",
        num_nodes=num_nodes,
    )
    if device is None:
        device = edge_index.device
    return torch.sparse_coo_tensor(
        lap_index.to(device),
        lap_weight.to(device),
        (num_nodes, num_nodes),
        device=device,
    ).coalesce()


class ChebyshevBasis(nn.Module):
    """Compute ``T_k(L-I)x`` without unsafe implicit graph caching.

    Callers may pass a precomputed normalized ``laplacian`` for a fixed graph.
    When it is omitted, the Laplacian is rebuilt from the supplied edges.  This
    makes equal-sized different graphs safe by construction.
    """

    def __init__(self, K: int):
        super().__init__()
        if K < 0:
            raise ValueError(f"K must be nonnegative, got {K}")
        self.K = K

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_weight: torch.Tensor | None = None,
        num_nodes: int | None = None,
        laplacian: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if num_nodes is None:
            num_nodes = x.size(0)
        if laplacian is None:
            laplacian = normalized_laplacian(
                edge_index,
                edge_weight,
                num_nodes,
                device=x.device,
            )
        if laplacian.shape != (num_nodes, num_nodes):
            raise ValueError(
                f"laplacian shape {tuple(laplacian.shape)} does not match "
                f"({num_nodes}, {num_nodes})"
            )
        laplacian = laplacian.to(device=x.device, dtype=x.dtype)

        bases = [x]
        if self.K == 0:
            return torch.stack(bases, dim=0)

        lap_x = torch.sparse.mm(laplacian, x)
        bases.append(lap_x - x)
        for _ in range(2, self.K + 1):
            previous, previous2 = bases[-1], bases[-2]
            shifted = torch.sparse.mm(laplacian, previous) - previous
            bases.append(2.0 * shifted - previous2)
        return torch.stack(bases, dim=0)


class _RootParameterizedLayer(nn.Module):
    def __init__(
        self,
        K: int,
        num_roots: int,
        *,
        r_max: float = 0.95,
        convention: Convention = "forward",
    ):
        super().__init__()
        self.K = K
        self.num_roots = num_roots
        self.r_max = r_max
        self.convention = convention
        self.root_params = nn.Parameter(initial_root_parameters(num_roots))

    def get_roots(self) -> torch.Tensor:
        return parameterize_roots(self.root_params, r_max=self.r_max)

    def get_alphas(self) -> torch.Tensor:
        """Compatibility name for existing visualization code."""
        return self.get_roots()

    def get_coeffs(self, device: torch.device) -> torch.Tensor:
        return blaschke_product_cheb_coeffs(
            self.get_roots().to(device),
            self.K,
            device,
            convention=self.convention,
        )

    def apply_operator(
        self,
        cheb_basis: torch.Tensor,
        *,
        adjoint: bool = False,
    ) -> torch.Tensor:
        coeffs = self.get_coeffs(cheb_basis.device)
        if adjoint:
            coeffs = torch.conj(coeffs)
        weights = coeffs.to(cheb_basis.dtype).view(-1, 1, 1)
        return torch.sum(weights * cheb_basis, dim=0)


class GraphBlaschkeLayerStrict(_RootParameterizedLayer):
    """Deprecated unscaled legacy difference layer.

    This class remains importable for old checkpoints, but it must not be used
    as evidence for the revised paper.
    """

    def __init__(
        self,
        K: int = 5,
        *,
        r_max: float = 0.95,
        convention: Convention = "forward",
    ):
        warnings.warn(
            "GraphBlaschkeLayerStrict is deprecated; use "
            "GraphBlaschkeLayerTight for reconstructing analysis.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(K, 1, r_max=r_max, convention=convention)

    def forward(
        self,
        h_complex: torch.Tensor,
        cheb_basis: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, tuple[float, float]]:
        transformed = self.apply_operator(cheb_basis)
        residual = h_complex - transformed
        alpha = self.get_roots()[0]
        return transformed, residual, (alpha.real.item(), alpha.imag.item())


class GraphBlaschkeLayerMultiRoot(_RootParameterizedLayer):
    """Deprecated unscaled multi-root legacy difference layer."""

    def __init__(
        self,
        K: int = 5,
        num_roots: int = 3,
        *,
        r_max: float = 0.95,
        convention: Convention = "forward",
    ):
        warnings.warn(
            "GraphBlaschkeLayerMultiRoot is deprecated; use "
            "GraphBlaschkeLayerTight for reconstructing analysis.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(K, num_roots, r_max=r_max, convention=convention)

    def forward(
        self,
        h_complex: torch.Tensor,
        cheb_basis: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, list[tuple[float, float]]]:
        transformed = self.apply_operator(cheb_basis)
        residual = h_complex - transformed
        roots = self.get_roots()
        root_tuples = [(a.real.item(), a.imag.item()) for a in roots]
        return transformed, residual, root_tuples


class GraphBlaschkeLayerTight(_RootParameterizedLayer):
    """Complementary Blaschke--Cayley analysis layer."""

    def __init__(
        self,
        K: int = 5,
        num_roots: int = 1,
        *,
        r_max: float = 0.95,
        convention: Convention = "forward",
    ):
        super().__init__(
            K,
            num_roots,
            r_max=r_max,
            convention=convention,
        )

    def forward(
        self,
        h_complex: torch.Tensor,
        cheb_basis: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        transformed = self.apply_operator(cheb_basis)
        carry = 0.5 * (h_complex + transformed)
        band = 0.5 * (h_complex - transformed)
        return carry, band, self.get_roots()

    def synthesize_from_adjoint_basis(
        self,
        carry: torch.Tensor,
        band: torch.Tensor,
        adjoint_basis: torch.Tensor,
    ) -> torch.Tensor:
        """Apply ``P+* carry + P-* band`` from a basis of ``carry-band``."""
        adjoint_term = self.apply_operator(adjoint_basis, adjoint=True)
        return 0.5 * (carry + band) + 0.5 * adjoint_term


class GraphBlaschkeLayerRelaxed(_RootParameterizedLayer):
    """One branch of the parallel empirical GBDN+ filter mixture."""

    def __init__(
        self,
        K: int = 5,
        *,
        r_max: float = 0.95,
        convention: Convention = "forward",
    ):
        super().__init__(K, 1, r_max=r_max, convention=convention)
        self.cheb_correction = nn.Parameter(torch.randn(K + 1, 1, 1) * 0.01)

    def forward(
        self,
        h_complex: torch.Tensor,
        cheb_basis: torch.Tensor,
    ) -> tuple[torch.Tensor, tuple[float, float]]:
        coeffs = self.get_coeffs(h_complex.device).view(-1, 1, 1)
        weights = coeffs.to(cheb_basis.dtype) + self.cheb_correction.to(
            cheb_basis.dtype
        )
        filtered = torch.sum(weights * cheb_basis, dim=0)
        alpha = self.get_roots()[0]
        return filtered, (alpha.real.item(), alpha.imag.item())
