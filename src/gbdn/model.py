"""Canonical model variants for the GBDN revision."""

from __future__ import annotations

from dataclasses import dataclass
import warnings

import torch
import torch.nn as nn

from gbdn.core import ValidatedLaplacian
from gbdn.layers import (
    ChebyshevBasis,
    GraphBlaschkeLayerMultiRoot,
    GraphBlaschkeLayerRelaxed,
    GraphBlaschkeLayerStrict,
    GraphBlaschkeLayerTight,
)
from gbdn.spectral import Convention


@dataclass
class TightAnalysisOutput:
    """Residual-first complete multilevel representation from Tight GBDN.

    The public order is frozen as ``(r_0, ..., r_{D-1}, h_D)``. The fields and
    construction order follow the same convention so no implicit permutation
    is needed by readouts, diagnostics, or artifact serializers.
    """

    bands: list[torch.Tensor]
    final_carry: torch.Tensor
    roots: list[torch.Tensor]

    def __post_init__(self) -> None:
        if len(self.bands) != len(self.roots):
            raise ValueError("bands and roots must have the same depth")

    @property
    def components(self) -> tuple[torch.Tensor, ...]:
        """Return ``(r_0, ..., r_{D-1}, h_D)`` exactly."""

        return (*self.bands, self.final_carry)

    @property
    def component_names(self) -> tuple[str, ...]:
        """Return stable semantic names aligned with :attr:`components`."""

        return (*[f"r_{index}" for index in range(len(self.bands))], "h_D")

    def concatenate(self, dim: int = -1) -> torch.Tensor:
        """Concatenate coefficients in the canonical residual-first order."""

        return torch.cat(self.components, dim=dim)

    def additive_reconstruction(self) -> torch.Tensor:
        """Recover the analyzed lift by telescoping shared complementary splits."""

        reconstructed = self.final_carry
        for band in reversed(self.bands):
            reconstructed = band + reconstructed
        return reconstructed

    def coefficient_energy(self) -> torch.Tensor:
        return sum(component.abs().square().sum() for component in self.components)


def _complex_lift(linear: nn.Linear, x: torch.Tensor) -> torch.Tensor:
    lifted = linear(x)
    split = lifted.shape[1] // 2
    return torch.complex(lifted[:, :split], lifted[:, split:])


class GBDNStrict(nn.Module):
    """Deprecated legacy model whose residual-sum readout telescopes.

    It remains available only for checkpoint compatibility and must not be used
    for revised-paper figures, theorem tests, or benchmark claims.
    """

    def __init__(
        self,
        in_channels: int,
        hidden_channels: int,
        out_channels: int,
        num_layers: int = 3,
        K: int = 5,
        num_roots: int = 1,
        *,
        convention: Convention = "forward",
    ):
        super().__init__()
        warnings.warn(
            "GBDNStrict is deprecated because its readout telescopes. "
            "Use GBDNTight or GBDNProductSum.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.num_roots = num_roots
        self.lifting = nn.Linear(in_channels, hidden_channels * 2)
        self.cheb_computer = ChebyshevBasis(K)
        if num_roots <= 1:
            layer_cls = GraphBlaschkeLayerStrict
            layer_kw = {"convention": convention}
        else:
            layer_cls = GraphBlaschkeLayerMultiRoot
            layer_kw = {"num_roots": num_roots, "convention": convention}
        self.layers = nn.ModuleList(
            [layer_cls(K, **layer_kw) for _ in range(num_layers)]
        )
        self.readout = nn.Linear(hidden_channels * 2, out_channels)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_weight: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, list]:
        h = _complex_lift(self.lifting, x)
        roots = []
        feature_sum = 0
        for layer in self.layers:
            basis = self.cheb_computer(h, edge_index, edge_weight=edge_weight)
            h, feature, alpha = layer(h, basis)
            feature_sum = feature_sum + feature
            roots.append(alpha)
        final = h + feature_sum
        output = self.readout(torch.cat([final.real, final.imag], dim=-1))
        return output, roots


class GBDNTight(nn.Module):
    """Primary reconstructing Blaschke--Cayley analysis architecture."""

    def __init__(
        self,
        in_channels: int,
        hidden_channels: int,
        out_channels: int,
        num_layers: int = 3,
        K: int = 5,
        num_roots: int = 1,
        *,
        r_max: float = 0.95,
        convention: Convention = "forward",
    ):
        super().__init__()
        self.num_layers = num_layers
        self.num_roots = num_roots
        self.convention = convention
        self.lifting = nn.Linear(in_channels, hidden_channels * 2)
        self.cheb_computer = ChebyshevBasis(K)
        self.layers = nn.ModuleList(
            [
                GraphBlaschkeLayerTight(
                    K,
                    num_roots=num_roots,
                    r_max=r_max,
                    convention=convention,
                )
                for _ in range(num_layers)
            ]
        )
        readout_in = hidden_channels * (num_layers + 1) * 2
        self.readout = nn.Linear(readout_in, out_channels)

    def analyze_complex(
        self,
        h: torch.Tensor,
        edge_index: torch.Tensor,
        edge_weight: torch.Tensor | None = None,
        laplacian: ValidatedLaplacian | None = None,
    ) -> TightAnalysisOutput:
        """Return every emitted band, the final carry, and learned roots."""
        bands: list[torch.Tensor] = []
        roots: list[torch.Tensor] = []
        carry = h
        for layer in self.layers:
            basis = self.cheb_computer(
                carry,
                edge_index,
                edge_weight=edge_weight,
                laplacian=laplacian,
            )
            carry, band, layer_roots = layer(carry, basis)
            bands.append(band)
            roots.append(layer_roots)
        return TightAnalysisOutput(
            bands=bands,
            final_carry=carry,
            roots=roots,
        )

    def analyze(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_weight: torch.Tensor | None = None,
        laplacian: ValidatedLaplacian | None = None,
    ) -> TightAnalysisOutput:
        return self.analyze_complex(
            _complex_lift(self.lifting, x),
            edge_index,
            edge_weight=edge_weight,
            laplacian=laplacian,
        )

    def synthesize(
        self,
        analysis: TightAnalysisOutput,
        edge_index: torch.Tensor,
        edge_weight: torch.Tensor | None = None,
        laplacian: ValidatedLaplacian | None = None,
    ) -> torch.Tensor:
        """Apply the adjoint synthesis recursion of the Chebyshev realization."""
        if len(analysis.bands) != len(self.layers):
            raise ValueError("analysis depth does not match this model")
        carry = analysis.final_carry
        for band, layer in zip(reversed(analysis.bands), reversed(self.layers)):
            difference = carry - band
            adjoint_basis = self.cheb_computer(
                difference,
                edge_index,
                edge_weight=edge_weight,
                laplacian=laplacian,
            )
            carry = layer.synthesize_from_adjoint_basis(
                carry,
                band,
                adjoint_basis,
            )
        return carry

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_weight: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, list[torch.Tensor]]:
        analysis = self.analyze(x, edge_index, edge_weight=edge_weight)
        coefficients = analysis.concatenate(dim=-1)
        features = torch.cat([coefficients.real, coefficients.imag], dim=-1)
        return self.readout(features), analysis.roots


class GBDNProductSum(nn.Module):
    """BDN-inspired learned sum of cumulative all-pass products."""

    def __init__(
        self,
        in_channels: int,
        hidden_channels: int,
        out_channels: int,
        num_layers: int = 3,
        K: int = 5,
        num_roots: int = 1,
        *,
        r_max: float = 0.95,
        convention: Convention = "forward",
    ):
        super().__init__()
        self.num_layers = num_layers
        self.lifting = nn.Linear(in_channels, hidden_channels * 2)
        self.cheb_computer = ChebyshevBasis(K)
        self.factors = nn.ModuleList(
            [
                GraphBlaschkeLayerTight(
                    K,
                    num_roots=num_roots,
                    r_max=r_max,
                    convention=convention,
                )
                for _ in range(num_layers)
            ]
        )
        self.coeffs = nn.Parameter(torch.zeros(num_layers + 1, 2))
        with torch.no_grad():
            self.coeffs[0, 0] = 1.0
        self.readout = nn.Linear(hidden_channels * 2, out_channels)

    def _apply_factor(
        self,
        factor: GraphBlaschkeLayerTight,
        h: torch.Tensor,
        edge_index: torch.Tensor,
        edge_weight: torch.Tensor | None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        basis = self.cheb_computer(h, edge_index, edge_weight=edge_weight)
        return factor.apply_operator(basis), factor.get_roots()

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_weight: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, list[torch.Tensor]]:
        h0 = _complex_lift(self.lifting, x)
        coeffs = torch.complex(self.coeffs[:, 0], self.coeffs[:, 1])
        accumulated = coeffs[0] * h0
        roots = []
        cumulative = h0
        for index, factor in enumerate(self.factors, start=1):
            cumulative, factor_roots = self._apply_factor(
                factor,
                cumulative,
                edge_index,
                edge_weight,
            )
            accumulated = accumulated + coeffs[index] * cumulative
            roots.append(factor_roots)
        features = torch.cat([accumulated.real, accumulated.imag], dim=-1)
        return self.readout(features), roots


class GBDNRelaxed(nn.Module):
    """GBDN+: a parallel empirical mixture without tightness guarantees."""

    def __init__(
        self,
        in_channels: int,
        hidden_channels: int,
        out_channels: int,
        num_layers: int = 3,
        K: int = 5,
        dropout: float = 0.5,
        *,
        r_max: float = 0.95,
        convention: Convention = "forward",
    ):
        super().__init__()
        self.dropout = dropout
        self.lifting = nn.Linear(in_channels, hidden_channels * 2)
        self.cheb_computer = ChebyshevBasis(K)
        self.layers = nn.ModuleList(
            [
                GraphBlaschkeLayerRelaxed(
                    K,
                    r_max=r_max,
                    convention=convention,
                )
                for _ in range(num_layers)
            ]
        )
        self.skip_weight = nn.Parameter(torch.tensor(0.5))
        self.readout = nn.Sequential(
            nn.Linear(hidden_channels * 2, hidden_channels),
            nn.ReLU(),
            nn.Dropout(p=dropout),
            nn.Linear(hidden_channels, out_channels),
        )

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_weight: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, list[tuple[float, float]]]:
        h = _complex_lift(self.lifting, x)
        basis = self.cheb_computer(h, edge_index, edge_weight=edge_weight)
        roots = []
        accumulated = 0
        for layer in self.layers:
            filtered, alpha = layer(h, basis)
            accumulated = accumulated + filtered
            roots.append(alpha)
        final = (1.0 - self.skip_weight) * h + self.skip_weight * accumulated
        features = torch.cat([final.real, final.imag], dim=-1)
        return self.readout(features), roots
