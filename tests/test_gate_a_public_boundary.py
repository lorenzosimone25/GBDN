"""GA-00 public spectral boundary and frozen adversarial regressions."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gbdn import (  # noqa: E402
    blaschke_cayley_exact,
    blaschke_cayley_symbol,
    blaschke_product_cheb_coeffs,
    exact_blaschke_operator_from_eigendecomposition,
    mapped_zero_pole,
    tight_split_responses,
    validate_exact_blaschke_eigendecomposition,
)


def _valid_inputs(
    dtype: torch.dtype = torch.float64,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    complex_dtype = torch.complex128 if dtype == torch.float64 else torch.complex64
    eigenvalues = torch.tensor([0.0, 0.75, 2.0], dtype=dtype)
    eigenvectors = torch.eye(3, dtype=dtype)
    roots = torch.tensor([0.2 + 0.1j, -0.15 + 0.25j], dtype=complex_dtype)
    return eigenvalues, eigenvectors, roots


@pytest.mark.parametrize("real_dtype", (torch.float32, torch.float64))
@pytest.mark.parametrize("convention", ("forward", "inverse"))
def test_ga00_public_exact_operator_validates_and_preserves_precision(
    real_dtype,
    convention,
):
    """GA-00: valid public exact inputs retain dtype/device and convention."""

    eigenvalues, eigenvectors, roots = _valid_inputs(real_dtype)
    operator = blaschke_cayley_exact(
        eigenvalues,
        eigenvectors,
        roots,
        convention=convention,
    )
    expected_dtype = (
        torch.complex128 if real_dtype == torch.float64 else torch.complex64
    )
    assert operator.dtype == expected_dtype
    assert operator.device == eigenvalues.device
    identity = torch.eye(3, dtype=expected_dtype)
    tolerance = 2e-6 if real_dtype == torch.float32 else 1e-12
    assert float(torch.linalg.matrix_norm(operator.mH @ operator - identity, ord=2)) < tolerance

    forward = blaschke_cayley_exact(eigenvalues, eigenvectors, roots)
    if convention == "forward":
        assert torch.equal(operator, forward)
    else:
        assert torch.allclose(operator, forward.mH, atol=tolerance, rtol=0.0)


def test_ga00_public_exact_rejects_frozen_nonorthogonal_counterexample():
    """GA-00: the former exact API's 4.83269 unitarity defect is rejected."""

    eigenvalues = torch.tensor([0.0, 1.0], dtype=torch.float64)
    eigenvectors = torch.tensor(
        [[1.0, 1.0], [0.0, 1.0]],
        dtype=torch.float64,
    )
    roots = torch.tensor([0.2 + 0.1j], dtype=torch.complex128)

    # Freeze the independent pre-repair construction to ensure this is a
    # substantive counterexample rather than a malformed-input smoke test.
    one = torch.ones_like(eigenvalues)
    zeta = torch.complex(eigenvalues, -one) / torch.complex(eigenvalues, one)
    symbol = (zeta - roots[0]) / (1.0 - roots[0].conj() * zeta)
    vectors = eigenvectors.to(torch.complex128)
    unchecked = (vectors * symbol.unsqueeze(0)) @ vectors.mH
    identity = torch.eye(2, dtype=torch.complex128)
    defect = float(torch.linalg.matrix_norm(unchecked.mH @ unchecked - identity, ord=2))
    assert defect == pytest.approx(4.83269046506849, abs=1e-14)

    with pytest.raises(ValueError, match="not orthonormal"):
        blaschke_cayley_exact(eigenvalues, eigenvectors, roots)


@pytest.mark.parametrize(
    "exact_boundary",
    (
        blaschke_cayley_exact,
        exact_blaschke_operator_from_eigendecomposition,
        validate_exact_blaschke_eigendecomposition,
    ),
)
def test_ga00_public_exact_boundaries_cannot_relax_orthogonality(
    exact_boundary,
):
    """GA-00: no public exact alias accepts a caller relaxation knob."""

    eigenvalues = torch.tensor([0.0, 1.0], dtype=torch.float64)
    eigenvectors = torch.tensor(
        [[1.0, 1.0], [0.0, 1.0]],
        dtype=torch.float64,
    )
    roots = torch.tensor([0.2 + 0.1j], dtype=torch.complex128)

    with pytest.raises(TypeError, match="orthogonality_atol"):
        exact_boundary(
            eigenvalues,
            eigenvectors,
            roots,
            orthogonality_atol=10.0,
        )
    with pytest.raises(ValueError, match="not orthonormal"):
        exact_boundary(eigenvalues, eigenvectors, roots)


@pytest.mark.parametrize(
    ("eigenvalues", "match"),
    (
        (torch.tensor([-0.1, 1.0], dtype=torch.float64), r"\[0, 2\]"),
        (torch.tensor([0.0, 2.1], dtype=torch.float64), r"\[0, 2\]"),
        (torch.tensor([0.0, float("nan")], dtype=torch.float64), "finite"),
        (torch.tensor([0.0, float("inf")], dtype=torch.float64), "finite"),
    ),
)
def test_ga00_public_exact_rejects_invalid_normalized_spectrum(eigenvalues, match):
    """GA-00: exact operator spectra must be finite and lie in [0,2]."""

    eigenvectors = torch.eye(2, dtype=torch.float64)
    roots = torch.tensor([0.2 + 0.1j], dtype=torch.complex128)
    with pytest.raises(ValueError, match=match):
        blaschke_cayley_exact(eigenvalues, eigenvectors, roots)


@pytest.mark.parametrize(
    ("roots", "exception", "match"),
    (
        (torch.tensor([1.2 + 0.0j], dtype=torch.complex128), ValueError, "unit disk"),
        (torch.tensor([1.0 + 0.0j], dtype=torch.complex128), ValueError, "unit disk"),
        (torch.tensor([complex(float("nan"), 0.0)], dtype=torch.complex128), ValueError, "finite"),
        (torch.tensor([complex(0.0, float("inf"))], dtype=torch.complex128), ValueError, "finite"),
        (torch.tensor([0.2], dtype=torch.float64), TypeError, "complex"),
        (torch.tensor([0.2 + 0.1j], dtype=torch.complex64), TypeError, "precision"),
    ),
)
def test_ga00_public_exact_rejects_invalid_roots(roots, exception, match):
    """GA-00: exact operator roots are complex, finite, nonempty, and admissible."""

    eigenvalues = torch.tensor([0.0, 1.0], dtype=torch.float64)
    eigenvectors = torch.eye(2, dtype=torch.float64)
    with pytest.raises(exception, match=match):
        blaschke_cayley_exact(eigenvalues, eigenvectors, roots)


@pytest.mark.parametrize(
    ("eigenvalues", "eigenvectors", "exception", "match"),
    (
        (
            torch.tensor([[0.0, 1.0]], dtype=torch.float64),
            torch.eye(2, dtype=torch.float64),
            ValueError,
            "one-dimensional",
        ),
        (
            torch.tensor([0.0, 1.0], dtype=torch.float64),
            torch.ones((2, 1), dtype=torch.float64),
            ValueError,
            "square basis",
        ),
        (
            torch.tensor([0, 1], dtype=torch.int64),
            torch.eye(2, dtype=torch.float64),
            TypeError,
            "real floating",
        ),
        (
            torch.tensor([0.0, 1.0], dtype=torch.float64),
            torch.eye(2, dtype=torch.int64),
            TypeError,
            "eigenvector dtype",
        ),
        (
            torch.tensor([0.0, 1.0], dtype=torch.float64),
            torch.tensor([[1.0, 0.0], [0.0, float("nan")]], dtype=torch.float64),
            ValueError,
            "finite",
        ),
    ),
)
def test_ga00_public_exact_rejects_shape_dtype_and_finiteness_errors(
    eigenvalues,
    eigenvectors,
    exception,
    match,
):
    """GA-00: malformed eigensystem shape, dtype, and values fail closed."""

    roots = torch.tensor([0.2 + 0.1j], dtype=torch.complex128)
    with pytest.raises(exception, match=match):
        blaschke_cayley_exact(eigenvalues, eigenvectors, roots)


def test_ga00_public_exact_rejects_device_mismatch_before_tensor_evaluation():
    """GA-00: public exact inputs cannot cross devices implicitly."""

    eigenvalues = torch.tensor([0.0, 1.0], dtype=torch.float64)
    eigenvectors = torch.eye(2, dtype=torch.float64)
    roots = torch.empty(1, dtype=torch.complex128, device="meta")
    with pytest.raises(ValueError, match="same device"):
        blaschke_cayley_exact(eigenvalues, eigenvectors, roots)


@pytest.mark.parametrize("convention", ("Forward", "backward", "", None))
def test_ga00_public_exact_rejects_invalid_convention(convention):
    """GA-00: only the frozen forward and inverse conventions are accepted."""

    eigenvalues, eigenvectors, roots = _valid_inputs()
    with pytest.raises(ValueError, match="convention"):
        blaschke_cayley_exact(
            eigenvalues,
            eigenvectors,
            roots,
            convention=convention,
        )


@pytest.mark.parametrize(
    "invalid_lambdas",
    (
        torch.tensor([0, 1]),
        torch.tensor([0.0 + 0.0j], dtype=torch.complex128),
        torch.tensor([float("nan")], dtype=torch.float64),
        torch.tensor([], dtype=torch.float64),
    ),
)
def test_ga00_claim_bearing_scalar_helpers_reject_invalid_spectral_values(
    invalid_lambdas,
):
    """GA-00: symbols and split responses require finite real spectral values."""

    roots = torch.tensor([0.2 + 0.1j], dtype=torch.complex128)
    for function in (blaschke_cayley_symbol, tight_split_responses):
        with pytest.raises((TypeError, ValueError)):
            function(invalid_lambdas, roots)


@pytest.mark.parametrize(
    "invalid_roots",
    (
        torch.tensor([1.2 + 0.0j], dtype=torch.complex128),
        torch.tensor([complex(float("nan"), 0.0)], dtype=torch.complex128),
        torch.tensor([0.2], dtype=torch.float64),
    ),
)
def test_ga00_claim_bearing_helpers_reject_invalid_roots(invalid_roots):
    """GA-00: symbol, split, geometry, and Chebyshev APIs share root policy."""

    eigenvalues = torch.tensor([0.0, 1.0], dtype=torch.float64)
    for function in (
        lambda: blaschke_cayley_symbol(eigenvalues, invalid_roots),
        lambda: tight_split_responses(eigenvalues, invalid_roots),
        lambda: mapped_zero_pole(invalid_roots),
        lambda: blaschke_product_cheb_coeffs(
            invalid_roots,
            4,
            torch.device("cpu"),
        ),
    ):
        with pytest.raises((TypeError, ValueError)):
            function()


def test_ga00_scalar_symbol_retains_full_real_line_scope_for_ga05():
    """GA-00/05: scalar symbol supports finite real values beyond graph spectra."""

    lambdas = torch.tensor([-4.0, 0.0, 2.0, 7.0], dtype=torch.float64)
    roots = torch.tensor([0.2 + 0.1j], dtype=torch.complex128)
    symbol = blaschke_cayley_symbol(lambdas, roots)
    assert torch.allclose(symbol.abs(), torch.ones_like(lambdas), atol=1e-12, rtol=0.0)


def test_ga00_empty_blaschke_product_is_the_exact_identity():
    """GA-00: an empty root sequence retains the mathematical q0=1 identity."""

    eigenvalues = torch.tensor([0.0, 0.7, 2.0], dtype=torch.float64)
    eigenvectors = torch.eye(3, dtype=torch.float64)
    roots = torch.empty(0, dtype=torch.complex128)
    symbol = blaschke_cayley_symbol(eigenvalues, roots)
    operator = blaschke_cayley_exact(eigenvalues, eigenvectors, roots)
    coefficients = blaschke_product_cheb_coeffs(
        roots,
        4,
        torch.device("cpu"),
    )
    responses = tight_split_responses(eigenvalues, roots)

    assert torch.equal(symbol, torch.ones_like(symbol))
    assert torch.equal(operator, torch.eye(3, dtype=torch.complex128))
    assert torch.allclose(
        coefficients,
        torch.tensor([1.0, 0.0, 0.0, 0.0, 0.0], dtype=torch.complex128),
        atol=1e-15,
        rtol=0.0,
    )
    assert torch.equal(responses["p_plus"], torch.ones_like(symbol))
    assert torch.equal(responses["p_minus"], torch.zeros_like(symbol))
    zeros, poles = mapped_zero_pole(roots)
    assert zeros.numel() == poles.numel() == 0
