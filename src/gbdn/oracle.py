"""Independent dense oracle for small-graph theorem and operator tests.

This module intentionally does not import :mod:`gbdn.layers` or reuse its
Chebyshev recurrence. Exact scalar symbols and dense polynomial recurrences are
implemented directly so sparse-layer convention errors cannot validate
themselves.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

import torch

from gbdn.core import validate_self_adjoint_operator


Convention = Literal["forward", "inverse"]


def _complex_dtype(real_dtype: torch.dtype) -> torch.dtype:
    if real_dtype == torch.float64:
        return torch.complex128
    if real_dtype == torch.float32:
        return torch.complex64
    raise TypeError(f"unsupported real dtype for spectral oracle: {real_dtype}")


def _validate_convention(convention: Convention) -> None:
    if convention not in {"forward", "inverse"}:
        raise ValueError(
            f"convention must be 'forward' or 'inverse', got {convention!r}"
        )


def _validate_roots(roots: torch.Tensor) -> torch.Tensor:
    if not roots.is_complex():
        raise TypeError("roots must use a complex dtype")
    roots = roots.reshape(-1)
    if not torch.isfinite(roots).all():
        raise ValueError("roots must be finite")
    if torch.any(roots.abs() >= 1.0):
        raise ValueError("every root must lie strictly inside the unit disk")
    return roots


def exact_blaschke_symbol(
    eigenvalues: torch.Tensor,
    roots: torch.Tensor,
    *,
    convention: Convention = "forward",
) -> torch.Tensor:
    """Evaluate the canonical exact symbol without sparse-layer utilities."""

    _validate_convention(convention)
    if eigenvalues.is_complex() or not eigenvalues.is_floating_point():
        raise TypeError("eigenvalues must use a real floating dtype")
    if not torch.isfinite(eigenvalues).all():
        raise ValueError("eigenvalues must be finite")
    complex_dtype = _complex_dtype(eigenvalues.dtype)
    eigenvalues = eigenvalues.to(dtype=eigenvalues.dtype)
    one = torch.ones_like(eigenvalues)
    zeta = torch.complex(eigenvalues, -one) / torch.complex(eigenvalues, one)
    roots = _validate_roots(roots).to(device=zeta.device, dtype=complex_dtype)
    symbol = torch.ones_like(zeta)
    for root in roots:
        symbol = symbol * (zeta - root) / (1.0 - torch.conj(root) * zeta)
    return torch.conj(symbol) if convention == "inverse" else symbol


def exact_blaschke_operator_from_eigendecomposition(
    eigenvalues: torch.Tensor,
    eigenvectors: torch.Tensor,
    roots: torch.Tensor,
    *,
    convention: Convention = "forward",
    orthogonality_atol: float = 1e-10,
) -> torch.Tensor:
    """Construct ``U diag(g(lambda)) U*`` from an explicit eigendecomposition."""

    if eigenvalues.ndim != 1:
        raise ValueError("eigenvalues must be one-dimensional")
    if eigenvectors.ndim != 2 or eigenvectors.shape != (
        eigenvalues.numel(),
        eigenvalues.numel(),
    ):
        raise ValueError("eigenvectors must be a square basis matching eigenvalues")
    if not torch.isfinite(eigenvectors).all():
        raise ValueError("eigenvectors must be finite")
    lower = float(eigenvalues.min().item())
    upper = float(eigenvalues.max().item())
    if lower < -1e-12 or upper > 2.0 + 1e-12:
        raise ValueError(
            f"normalized-Laplacian eigenvalues must lie in [0, 2], got [{lower}, {upper}]"
        )
    symbol = exact_blaschke_symbol(
        eigenvalues,
        roots,
        convention=convention,
    )
    vectors = eigenvectors.to(device=symbol.device, dtype=symbol.dtype)
    identity = torch.eye(vectors.shape[0], dtype=vectors.dtype, device=vectors.device)
    residual = torch.linalg.matrix_norm(vectors.mH @ vectors - identity, ord=2)
    if float(residual.item()) > orthogonality_atol:
        raise ValueError(f"eigenvectors are not orthonormal (residual={residual.item()})")
    return (vectors * symbol.unsqueeze(0)) @ vectors.mH


def exact_blaschke_operator(
    laplacian: torch.Tensor,
    roots: torch.Tensor,
    *,
    convention: Convention = "forward",
) -> torch.Tensor:
    """Diagonalize a validated dense Laplacian and construct its exact factor."""

    if laplacian.layout != torch.strided:
        raise TypeError("the dense oracle requires a dense Laplacian")
    validate_self_adjoint_operator(laplacian)
    eigenvalues, eigenvectors = torch.linalg.eigh(laplacian)
    return exact_blaschke_operator_from_eigendecomposition(
        eigenvalues,
        eigenvectors,
        roots,
        convention=convention,
    )


def dense_chebyshev_operator(
    laplacian: torch.Tensor,
    coefficients: torch.Tensor,
) -> torch.Tensor:
    """Evaluate ``sum_k c_k T_k(L-I)`` by an independent dense recurrence."""

    if laplacian.layout != torch.strided:
        raise TypeError("the dense polynomial oracle requires a dense Laplacian")
    validate_self_adjoint_operator(laplacian)
    if coefficients.ndim != 1 or coefficients.numel() == 0:
        raise ValueError("coefficients must be a nonempty one-dimensional tensor")
    if not torch.isfinite(coefficients).all():
        raise ValueError("coefficients must be finite")

    dtype = coefficients.dtype
    matrix = laplacian.to(device=coefficients.device, dtype=dtype)
    identity = torch.eye(matrix.shape[0], device=matrix.device, dtype=dtype)
    shifted = matrix - identity
    previous2 = identity
    result = coefficients[0] * previous2
    if coefficients.numel() == 1:
        return result
    previous = shifted
    result = result + coefficients[1] * previous
    for degree in range(2, coefficients.numel()):
        current = 2.0 * shifted @ previous - previous2
        result = result + coefficients[degree] * current
        previous2, previous = previous, current
    return result


def tight_analysis_matrix(operators: Sequence[torch.Tensor]) -> torch.Tensor:
    """Assemble the residual-first complete block analysis matrix explicitly."""

    if not operators:
        raise ValueError("at least one operator is required")
    first = operators[0]
    if first.ndim != 2 or first.shape[0] != first.shape[1]:
        raise ValueError("operators must be square matrices")
    num_nodes = first.shape[0]
    dtype = first.dtype
    device = first.device
    identity = torch.eye(num_nodes, dtype=dtype, device=device)
    carry_operator = identity
    residual_operators: list[torch.Tensor] = []
    for operator in operators:
        if operator.shape != first.shape:
            raise ValueError("all operators must have the same square shape")
        operator = operator.to(device=device, dtype=dtype)
        minus = 0.5 * (identity - operator)
        plus = 0.5 * (identity + operator)
        residual_operators.append(minus @ carry_operator)
        carry_operator = plus @ carry_operator
    return torch.cat([*residual_operators, carry_operator], dim=0)


def apply_tight_analysis(
    signal: torch.Tensor,
    operators: Sequence[torch.Tensor],
) -> tuple[torch.Tensor, ...]:
    """Apply a sequence of shared complementary splits, residuals first."""

    carry = signal
    residuals: list[torch.Tensor] = []
    for operator in operators:
        transformed = operator @ carry
        residuals.append(0.5 * (carry - transformed))
        carry = 0.5 * (carry + transformed)
    return (*residuals, carry)
