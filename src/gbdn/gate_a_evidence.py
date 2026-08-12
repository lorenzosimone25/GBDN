"""Deterministic, read-only numeric evidence for the Gate-A contract.

The pytest suite remains the executable regression surface.  This module is a
second, explicit evidence path: it recomputes the theorem observables in
memory, serializes the quantities that determined each verdict, and never
writes an artifact.  The coverage report links every collected pytest node to
one of the row records produced here.

An ``N/A`` value is allowed only with a nonempty, row-specific rationale.  In
particular, a passing pytest status is never converted into a fabricated zero
residual.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import copy
import hashlib
import math
import re
from typing import Any, Final
from unittest.mock import patch

import torch

from gbdn.core import preprocess_reciprocal_mean
from gbdn.diagnostics import (
    approximation_configuration_diagnostic,
    fixed_root_perturbation_constant,
    frozen_scalar_cayleynet_comparator,
    multilevel_frame_bound,
    product_sum_evaluation_matrix,
    reduced_blaschke_pole_diagnostic,
    target_pole_ellipse_parameter,
)
from gbdn.layers import ChebyshevBasis, normalized_laplacian
from gbdn.model import GBDNProductSum, GBDNRelaxed, GBDNTight, TightAnalysisOutput
from gbdn.oracle import (
    adjoint_tight_synthesis,
    apply_tight_analysis,
    dense_chebyshev_operator,
    exact_blaschke_operator,
    exact_blaschke_operator_from_eigendecomposition,
    exact_blaschke_symbol,
    tight_analysis_matrix,
)
from gbdn.spectral import (
    blaschke_product_cheb_coeffs,
    cayley_map,
    center_width_from_root,
    dct_synthesis,
    evaluate_chebyshev,
    mapped_zero_pole,
    parameterize_center_width_roots,
    parameterize_roots,
    tight_split_responses,
)
from gbdn.synthetic import sphere_graph_data


EVIDENCE_SCHEMA: Final[str] = "gbdn-gate-a-evidence-v1"
REQUIRED_IDS: Final[tuple[str, ...]] = tuple(
    f"GA-{index:02d}" for index in range(36)
)
SCALAR_TOL: Final[float] = 5e-12
EXACT_TOL: Final[float] = 1e-10
SPARSE_TOL: Final[float] = 1e-8
ZERO_TOL: Final[float] = 1e-12
SLACK: Final[float] = 1e-10
SHA256_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")


def evidence_value(value: Any) -> dict[str, Any]:
    """Wrap a JSON value so absence cannot be confused with numeric zero."""

    return {"status": "VALUE", "value": value}


def evidence_na(rationale: str) -> dict[str, str]:
    """Return a typed not-applicable value with a mandatory rationale."""

    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("N/A evidence requires a nonempty rationale")
    return {"status": "N/A", "rationale": rationale.strip()}


def _metric(
    name: str,
    *,
    observed: Any,
    absolute_residual: float | dict[str, Any],
    relative_residual: float | dict[str, Any],
    predicted_bound: Any | dict[str, Any],
    comparison: dict[str, Any],
    tolerance: float | dict[str, Any],
) -> dict[str, Any]:
    def wrapped(value: Any | dict[str, Any]) -> dict[str, Any]:
        if isinstance(value, dict) and value.get("status") in {"VALUE", "N/A"}:
            return value
        return evidence_value(value)

    return {
        "name": name,
        "observed_quantity": wrapped(observed),
        "absolute_residual": wrapped(absolute_residual),
        "relative_residual": wrapped(relative_residual),
        "predicted_bound": wrapped(predicted_bound),
        "observed_vs_bound": comparison,
        "tolerance": wrapped(tolerance),
    }


def _error_metric(
    name: str,
    error: float,
    bound: float,
    *,
    relative_error: float | None = None,
) -> dict[str, Any]:
    error = float(error)
    bound = float(bound)
    relative = (
        evidence_na(
            f"{name} has no contract-defined nonzero normalization; "
            "the absolute residual is authoritative"
        )
        if relative_error is None
        else float(relative_error)
    )
    return _metric(
        name,
        observed=error,
        absolute_residual=error,
        relative_residual=relative,
        predicted_bound=bound,
        comparison=evidence_value(
            {"operator": "<=", "decision": error <= bound}
        ),
        tolerance=bound,
    )


def _upper_bound_metric(
    name: str,
    observed: float,
    bound: float,
    *,
    scale: float | None = None,
) -> dict[str, Any]:
    observed = float(observed)
    bound = float(bound)
    violation = max(0.0, observed - bound)
    denominator = max(abs(bound if scale is None else scale), 1e-30)
    return _metric(
        name,
        observed=observed,
        absolute_residual=violation,
        relative_residual=violation / denominator,
        predicted_bound=bound,
        comparison=evidence_value(
            {"operator": "<=", "decision": observed <= bound}
        ),
        tolerance=bound,
    )


def _lower_bound_metric(
    name: str,
    observed: float,
    lower_bound: float,
) -> dict[str, Any]:
    observed = float(observed)
    lower_bound = float(lower_bound)
    violation = max(0.0, lower_bound - observed)
    return _metric(
        name,
        observed=observed,
        absolute_residual=violation,
        relative_residual=violation / max(abs(lower_bound), 1e-30),
        predicted_bound=lower_bound,
        comparison=evidence_value(
            {"operator": ">=", "decision": observed >= lower_bound}
        ),
        tolerance=lower_bound,
    )


def _descriptive_metric(
    name: str,
    observed: Any,
    rationale: str,
) -> dict[str, Any]:
    not_applicable = evidence_na(rationale)
    return _metric(
        name,
        observed=observed,
        absolute_residual=not_applicable,
        relative_residual=not_applicable,
        predicted_bound=not_applicable,
        comparison=not_applicable,
        tolerance=not_applicable,
    )


def _undirected_edges(
    pairs: list[tuple[int, int, float]],
) -> tuple[torch.Tensor, torch.Tensor]:
    directed: list[tuple[int, int]] = []
    weights: list[float] = []
    for source, target, weight in pairs:
        directed.extend(((source, target), (target, source)))
        weights.extend((weight, weight))
    return (
        torch.tensor(directed, dtype=torch.long).t().contiguous(),
        torch.tensor(weights, dtype=torch.float64),
    )


def _semantic_edge_hash(
    edge_index: torch.Tensor,
    edge_weight: torch.Tensor,
    num_nodes: int,
) -> str:
    """Hash an edge-list input independently of column order."""

    digest = hashlib.sha256()
    digest.update(f"num_nodes={int(num_nodes)}\n".encode("ascii"))
    rows = sorted(
        (
            int(source),
            int(target),
            float(weight).hex(),
        )
        for source, target, weight in zip(
            edge_index[0].detach().cpu().tolist(),
            edge_index[1].detach().cpu().tolist(),
            edge_weight.detach().cpu().tolist(),
            strict=True,
        )
    )
    for source, target, weight in rows:
        digest.update(f"{source}:{target}:{weight}\n".encode("ascii"))
    return digest.hexdigest()


def _path(num_nodes: int) -> tuple[torch.Tensor, torch.Tensor]:
    return _undirected_edges(
        [(node, node + 1, 1.0) for node in range(num_nodes - 1)]
    )


def _cycle(num_nodes: int) -> tuple[torch.Tensor, torch.Tensor]:
    return _undirected_edges(
        [(node, (node + 1) % num_nodes, 1.0) for node in range(num_nodes)]
    )


def _complete(num_nodes: int) -> tuple[torch.Tensor, torch.Tensor]:
    return _undirected_edges(
        [
            (source, target, 1.0)
            for source in range(num_nodes)
            for target in range(source + 1, num_nodes)
        ]
    )


def _grid() -> tuple[torch.Tensor, torch.Tensor]:
    pairs: list[tuple[int, int, float]] = []
    for row in range(2):
        for column in range(4):
            node = row * 4 + column
            if column < 3:
                pairs.append((node, node + 1, 1.0))
            if row == 0:
                pairs.append((node, node + 4, 1.0))
    return _undirected_edges(pairs)


def _star() -> tuple[torch.Tensor, torch.Tensor]:
    return _undirected_edges([(0, node, 1.0) for node in range(1, 7)])


def _disconnected_six() -> tuple[torch.Tensor, torch.Tensor]:
    return _undirected_edges(
        [(0, 1, 1.0), (1, 2, 1.0), (3, 4, 1.0)]
    )


def _disconnected_seven() -> tuple[torch.Tensor, torch.Tensor]:
    return _undirected_edges(
        [
            (0, 1, 1.0),
            (1, 2, 1.0),
            (3, 4, 1.0),
            (4, 5, 1.0),
            (5, 3, 1.0),
        ]
    )


def _weighted_six() -> tuple[torch.Tensor, torch.Tensor]:
    return _undirected_edges(
        [
            (0, 1, 0.4),
            (1, 2, 1.7),
            (2, 3, 0.8),
            (3, 4, 2.1),
            (1, 4, 0.6),
        ]
    )


def _random_weighted() -> tuple[torch.Tensor, torch.Tensor]:
    return _undirected_edges(
        [
            (0, 1, 0.31),
            (0, 3, 1.47),
            (0, 6, 0.82),
            (1, 2, 1.13),
            (1, 5, 0.56),
            (2, 4, 1.91),
            (2, 7, 0.44),
            (3, 4, 0.73),
            (3, 7, 1.28),
            (4, 5, 1.62),
            (5, 6, 0.95),
            (6, 7, 1.36),
        ]
    )


@dataclass(frozen=True)
class EvidenceGraph:
    name: str
    num_nodes: int
    edge_index: torch.Tensor
    edge_weight: torch.Tensor
    laplacian_token: Any

    @property
    def laplacian(self) -> torch.Tensor:
        return self.laplacian_token.to_dense()

    def provenance(self) -> dict[str, Any]:
        return {
            "fixture": self.name,
            "num_nodes": self.num_nodes,
            "semantic_sha256": self.laplacian_token.sha256,
            "source": self.laplacian_token.source,
        }


def _make_graph(
    name: str,
    num_nodes: int,
    builder: Any,
) -> EvidenceGraph:
    edge_index, edge_weight = builder()
    token = normalized_laplacian(edge_index, edge_weight, num_nodes)
    return EvidenceGraph(name, num_nodes, edge_index, edge_weight, token)


@lru_cache(maxsize=1)
def _graph_registry() -> dict[str, EvidenceGraph]:
    specifications = {
        "path_2": (2, lambda: _path(2)),
        "path_5": (5, lambda: _path(5)),
        "path_6": (6, lambda: _path(6)),
        "path_8": (8, lambda: _path(8)),
        "path_9": (9, lambda: _path(9)),
        "path_10": (10, lambda: _path(10)),
        "path_14": (14, lambda: _path(14)),
        "path_20": (20, lambda: _path(20)),
        "cycle_even_6": (6, lambda: _cycle(6)),
        "cycle_odd_7": (7, lambda: _cycle(7)),
        "cycle_odd_9": (9, lambda: _cycle(9)),
        "cycle_even_10": (10, lambda: _cycle(10)),
        "grid_2x4": (8, _grid),
        "star_7": (7, _star),
        "complete_5": (5, lambda: _complete(5)),
        "complete_6": (6, lambda: _complete(6)),
        "disconnected_6": (6, _disconnected_six),
        "disconnected_7": (7, _disconnected_seven),
        "weighted_6": (6, _weighted_six),
        "random_weighted_seed_1701": (8, _random_weighted),
    }
    return {
        name: _make_graph(name, num_nodes, builder)
        for name, (num_nodes, builder) in specifications.items()
    }


@lru_cache(maxsize=1)
def _root_registry() -> dict[str, torch.Tensor]:
    return {
        "real_interior": torch.tensor(
            [0.35 + 0.0j], dtype=torch.complex128
        ),
        "generic_complex": torch.tensor(
            [0.22 + 0.17j], dtype=torch.complex128
        ),
        "multi_root": torch.tensor(
            [0.18 + 0.11j, -0.27 + 0.08j, 0.09 - 0.21j],
            dtype=torch.complex128,
        ),
        "conjugate_pair": torch.tensor(
            [0.28 + 0.19j, 0.28 - 0.19j], dtype=torch.complex128
        ),
        "near_radius_cap": torch.tensor(
            [0.949999 - 1e-4j], dtype=torch.complex128
        ),
    }


def _graph_context(names: tuple[str, ...] | None, rationale: str = "") -> dict[str, Any]:
    if names is None:
        return evidence_na(rationale)
    registry = _graph_registry()
    return evidence_value([registry[name].provenance() for name in names])


def _serialized_roots(roots: torch.Tensor) -> list[dict[str, float]]:
    return [
        {"real": float(root.real.item()), "imag": float(root.imag.item())}
        for root in roots.reshape(-1)
    ]


def _root_context(names: tuple[str, ...] | None, rationale: str = "") -> dict[str, Any]:
    if names is None:
        return evidence_na(rationale)
    registry = _root_registry()
    return evidence_value(
        [
            {
                "fixture": name,
                "parameterization": "fixed-explicit-complex",
                "values": _serialized_roots(registry[name]),
            }
            for name in names
        ]
    )


def _row(
    gate_id: str,
    *,
    evaluator: str,
    realization_tags: tuple[str, ...],
    graphs: dict[str, Any],
    roots: dict[str, Any],
    dtype: str,
    device: str,
    configuration: dict[str, Any],
    metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "evaluator": evaluator,
        "realization_tags": list(realization_tags),
        "graph_semantic_hashes": graphs,
        "root_fixtures_and_values": roots,
        "dtype": evidence_value(dtype),
        "device": evidence_value(device),
        "configuration": evidence_value(configuration),
        "metrics": metrics,
    }


def _relative_operator_error(actual: torch.Tensor, expected: torch.Tensor) -> float:
    numerator = torch.linalg.matrix_norm(actual - expected, ord=2)
    denominator = torch.linalg.matrix_norm(expected, ord=2).clamp_min(1e-30)
    return float((numerator / denominator).item())


def _apply_sparse_polynomial(
    graph: EvidenceGraph,
    coefficients: torch.Tensor,
) -> torch.Tensor:
    identity = torch.eye(graph.num_nodes, dtype=coefficients.dtype)
    basis = ChebyshevBasis(coefficients.numel() - 1)(
        identity,
        graph.edge_index,
        edge_weight=graph.edge_weight,
        num_nodes=graph.num_nodes,
        laplacian=graph.laplacian_token,
    )
    return torch.sum(coefficients.view(-1, 1, 1) * basis, dim=0)


def _operators(
    graph: EvidenceGraph,
    roots: torch.Tensor,
    depth: int,
) -> list[torch.Tensor]:
    return [exact_blaschke_operator(graph.laplacian, roots) for _ in range(depth)]


def _evaluate_ga00() -> dict[str, Any]:
    directed = torch.tensor(
        [[0, 1, 2, 3, 4], [1, 0, 1, 2, 3]], dtype=torch.long
    )
    weights = torch.ones(5, dtype=torch.float64)
    rejected = False
    try:
        normalized_laplacian(directed, weights, 5)
    except ValueError:
        rejected = True

    preprocess_edges = torch.tensor(
        [[0, 0, 1, 1, 0, 3], [1, 1, 0, 2, 0, 3]], dtype=torch.long
    )
    preprocess_weights = torch.tensor(
        [1.0, 3.0, 2.0, 4.0, 0.5, 1.0], dtype=torch.float64
    )
    preprocessed = preprocess_reciprocal_mean(
        preprocess_edges, preprocess_weights, 5
    )
    laplacian = preprocessed.laplacian.to_dense()
    eigenvalues = torch.linalg.eigvalsh(laplacian)
    symmetry_error = float(
        torch.linalg.matrix_norm(laplacian - laplacian.mH, ord=2).item()
    )
    interval_violation = max(
        0.0,
        -float(eigenvalues.min().item()),
        float(eigenvalues.max().item()) - 2.0,
    )
    policy_mismatch_count = int(
        preprocessed.record.policy != "reciprocal-mean"
        or preprocessed.record.formula != "A_sym=(A+A^T)/2"
        or preprocessed.record.isolated_laplacian_diagonal != 1.0
    )
    sphere = sphere_graph_data(
        n_nodes=24,
        k_nn=3,
        idx_low=2,
        idx_high=15,
    )
    sphere_laplacian = sphere["laplacian"].to_dense()
    sphere_symmetry_error = float(
        torch.linalg.matrix_norm(
            sphere_laplacian - sphere_laplacian.mH,
            ord=2,
        ).item()
    )
    sphere_eigensystem_residual = float(
        (
            torch.linalg.matrix_norm(
                sphere_laplacian @ sphere["evecs"]
                - sphere["evecs"] * sphere["evals"].unsqueeze(0),
                ord="fro",
            )
            / torch.linalg.matrix_norm(
                sphere_laplacian,
                ord="fro",
            ).clamp_min(1e-30)
        ).item()
    )
    sphere_record = sphere["graph_preprocess_record"]
    sphere_policy_mismatch_count = int(
        sphere_record["policy"] != "reciprocal-mean"
        or sphere_record["formula"] != "A_sym=(A+A^T)/2"
    )
    graphs = evidence_value(
        [
            {
                "fixture": "directed-knn-rejection-input",
                "semantic_sha256": _semantic_edge_hash(directed, weights, 5),
                "semantic_role": "ordered-directed-input",
            },
            {
                "fixture": "reciprocal-mean-policy-input",
                "semantic_sha256": preprocessed.record.input_sha256,
                "semantic_role": "recorded-directed-input",
            },
            {
                "fixture": "reciprocal-mean-output",
                "semantic_sha256": preprocessed.record.output_sha256,
                "semantic_role": "recorded-symmetric-adjacency-output",
            },
            {
                "fixture": "reciprocal-mean-laplacian",
                "semantic_sha256": preprocessed.laplacian.sha256,
                "semantic_role": "validated-normalized-laplacian",
            },
            {
                "fixture": "sphere-directed-knn-preprocessed-output",
                "semantic_sha256": sphere_record["output_sha256"],
                "semantic_role": "recorded-symmetric-adjacency-output",
            },
            {
                "fixture": "sphere-validated-laplacian",
                "semantic_sha256": sphere["laplacian"].sha256,
                "semantic_role": "validated-normalized-laplacian",
            },
        ]
    )
    return _row(
        "GA-00",
        evaluator="evaluate_graph_contract",
        realization_tags=("exact",),
        graphs=graphs,
        roots=evidence_na("GA-00 validates graph inputs and has no filter root"),
        dtype="torch.float64",
        device="cpu",
        configuration={
            "policy": preprocessed.record.to_dict(),
            "sphere_policy": sphere_record,
            "peel_contract": "ValidatedLaplacian-required; angular-oracle-quarantined",
        },
        metrics=[
            _upper_bound_metric(
                "directed_input_rejection_failure_count", int(not rejected), 0.0
            ),
            _error_metric("laplacian_self_adjoint_residual", symmetry_error, 1e-14),
            _upper_bound_metric("laplacian_spectral_interval_violation", interval_violation, 1e-12),
            _upper_bound_metric("policy_metadata_mismatch_count", policy_mismatch_count, 0.0),
            _error_metric(
                "sphere_laplacian_self_adjoint_residual",
                sphere_symmetry_error,
                1e-14,
            ),
            _error_metric(
                "sphere_eigensystem_relative_residual",
                sphere_eigensystem_residual,
                EXACT_TOL,
                relative_error=sphere_eigensystem_residual,
            ),
            _upper_bound_metric(
                "sphere_policy_metadata_mismatch_count",
                sphere_policy_mismatch_count,
                0.0,
            ),
        ],
    )


def _evaluate_ga01() -> dict[str, Any]:
    radial_parameters = torch.tensor(
        [[-1000.0, -80.0], [0.0, math.pi / 3.0], [1000.0, 90.0]],
        dtype=torch.float64,
    )
    radial = parameterize_roots(radial_parameters, r_max=0.95)
    center_parameters = torch.tensor(
        [[-40.0, -40.0], [0.0, 0.0], [40.0, 40.0], [1.2, -0.7]],
        dtype=torch.float64,
        requires_grad=True,
    )
    centered = parameterize_center_width_roots(
        center_parameters, gamma_min=0.05, gamma_max=1.5
    )
    center, width = center_width_from_root(centered)
    expected_center = 2.0 * torch.sigmoid(center_parameters[:, 0])
    expected_width = 0.05 + 1.45 * torch.sigmoid(center_parameters[:, 1])
    inverse_error = float(
        torch.maximum(
            (center - expected_center).abs().max(),
            (width - expected_width).abs().max(),
        ).item()
    )
    (centered.real.sum() + centered.imag.sum()).backward()
    nonfinite_gradient_count = int(
        (~torch.isfinite(center_parameters.grad)).sum().item()
    )
    cap_violation = max(0.0, float(radial.abs().max().item()) - 0.95)
    roots = evidence_value(
        [
            {
                "fixture": "radial-polar-extremes",
                "parameterization": "rho_max*sigmoid(s)*exp(i*theta)",
                "values": _serialized_roots(radial),
            },
            {
                "fixture": "exact-center-width-extremes",
                "parameterization": "inverse-cayley(mu+i*gamma)",
                "values": _serialized_roots(centered),
            },
        ]
    )
    return _row(
        "GA-01",
        evaluator="evaluate_root_admissibility",
        realization_tags=("exact",),
        graphs=evidence_na("GA-01 is a scalar root-parameterization contract"),
        roots=roots,
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={"r_max": 0.95, "gamma_min": 0.05, "gamma_max": 1.5},
        metrics=[
            _upper_bound_metric("radial_cap_violation", cap_violation, 0.0),
            _error_metric("center_width_inverse_residual", inverse_error, SCALAR_TOL),
            _upper_bound_metric("nonfinite_gradient_count", nonfinite_gradient_count, 0.0),
        ],
    )


def _evaluate_ga02() -> dict[str, Any]:
    roots = _root_registry()
    scalar_grid = torch.linspace(-5.0, 5.0, 5001, dtype=torch.float64)
    modulus_error = 0.0
    for root in roots.values():
        symbol = exact_blaschke_symbol(scalar_grid, root)
        modulus_error = max(
            modulus_error, float((symbol.abs() - 1.0).abs().max().item())
        )
    root = roots["generic_complex"]
    zero, pole = mapped_zero_pole(root)
    pole_error = float((pole - torch.conj(zero)).abs().max().item())
    recovered = (zero - 1j) / (zero + 1j)
    inverse_error = float((recovered - root).abs().max().item())
    probe = torch.linspace(-3.0, 3.0, 801, dtype=torch.float64)
    analytic = tight_split_responses(probe, root)["phase_derivative"]
    lorentzian = 2.0 * zero.imag / (
        (probe - zero.real).square() + zero.imag.square()
    )
    lorentzian_error = float((analytic - lorentzian).abs().max().item())
    step = 1e-6
    plus = exact_blaschke_symbol(probe + step, root)
    minus = exact_blaschke_symbol(probe - step, root)
    finite_difference = torch.angle(plus / minus) / (2.0 * step)
    phase_error = float((analytic - finite_difference).abs().max().item())
    return _row(
        "GA-02",
        evaluator="evaluate_scalar_allpass_geometry",
        realization_tags=("exact",),
        graphs=evidence_na("GA-02 is evaluated on a scalar real-frequency grid"),
        roots=_root_context(tuple(roots)),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={"scalar_grid_points": 5001, "finite_difference_step": step},
        metrics=[
            _error_metric("maximum_unit_modulus_residual", modulus_error, SCALAR_TOL),
            _error_metric("mapped_zero_pole_conjugacy_residual", pole_error, SCALAR_TOL),
            _error_metric("mapped_zero_inverse_residual", inverse_error, SCALAR_TOL),
            _error_metric("lorentzian_derivative_residual", lorentzian_error, SCALAR_TOL),
            _error_metric("phase_finite_difference_residual", phase_error, 2e-6),
            _lower_bound_metric(
                "minimum_forward_phase_derivative",
                float(analytic.min().item()),
                0.0,
            ),
        ],
    )


def _evaluate_ga03_ga04() -> tuple[dict[str, Any], dict[str, Any]]:
    graph_names = (
        "path_5",
        "path_8",
        "cycle_even_6",
        "cycle_odd_7",
        "grid_2x4",
        "star_7",
        "complete_5",
        "disconnected_7",
        "random_weighted_seed_1701",
    )
    root_names = tuple(_root_registry())
    max_left = max_right = max_frame = max_energy = 0.0
    generator = torch.Generator().manual_seed(3040)
    for graph_name in graph_names:
        graph = _graph_registry()[graph_name]
        identity = torch.eye(graph.num_nodes, dtype=torch.complex128)
        for root_name in root_names:
            operator = exact_blaschke_operator(
                graph.laplacian, _root_registry()[root_name]
            )
            max_left = max(
                max_left,
                float(
                    torch.linalg.matrix_norm(
                        operator.mH @ operator - identity, ord=2
                    ).item()
                ),
            )
            max_right = max(
                max_right,
                float(
                    torch.linalg.matrix_norm(
                        operator @ operator.mH - identity, ord=2
                    ).item()
                ),
            )
            residual = 0.5 * (identity - operator)
            carry = 0.5 * (identity + operator)
            frame = residual.mH @ residual + carry.mH @ carry
            max_frame = max(
                max_frame,
                float(torch.linalg.matrix_norm(frame - identity, ord=2).item()),
            )
            signal = torch.randn(
                graph.num_nodes,
                3,
                dtype=torch.complex128,
                generator=generator,
            )
            split_energy = (residual @ signal).abs().square().sum()
            split_energy += (carry @ signal).abs().square().sum()
            energy_error = (split_energy - signal.abs().square().sum()).abs()
            energy_error /= signal.abs().square().sum()
            max_energy = max(max_energy, float(energy_error.item()))
    shared = {
        "graphs": _graph_context(graph_names),
        "roots": _root_context(root_names),
        "dtype": "torch.float64/torch.complex128",
        "device": "cpu",
        "configuration": {
            "graph_count": len(graph_names),
            "root_fixture_count": len(root_names),
            "feature_dimensions": [3],
        },
    }
    ga03 = _row(
        "GA-03",
        evaluator="evaluate_exact_unitarity_fixture_matrix",
        realization_tags=("exact",),
        metrics=[
            _error_metric("maximum_left_unitarity_residual", max_left, EXACT_TOL),
            _error_metric("maximum_right_unitarity_residual", max_right, EXACT_TOL),
        ],
        **shared,
    )
    ga04 = _row(
        "GA-04",
        evaluator="evaluate_one_level_split_fixture_matrix",
        realization_tags=("exact",),
        metrics=[
            _error_metric("maximum_frame_operator_residual", max_frame, EXACT_TOL),
            _error_metric(
                "maximum_channel_energy_relative_residual",
                max_energy,
                EXACT_TOL,
                relative_error=max_energy,
            ),
        ],
        **shared,
    )
    return ga03, ga04


def _evaluate_ga05() -> dict[str, Any]:
    graph_names = (
        "path_5",
        "path_8",
        "cycle_even_6",
        "cycle_odd_7",
        "grid_2x4",
        "star_7",
        "complete_5",
        "disconnected_7",
        "random_weighted_seed_1701",
    )
    roots = list(_root_registry().values())
    max_error = 0.0
    spectra = [
        torch.linspace(-5.0, 5.0, 4001, dtype=torch.float64),
        *[
            torch.linalg.eigvalsh(_graph_registry()[name].laplacian)
            for name in graph_names
        ],
    ]
    for eigenvalues in spectra:
        carry = torch.ones_like(eigenvalues, dtype=torch.complex128)
        residuals: list[torch.Tensor] = []
        for level in range(16):
            symbol = exact_blaschke_symbol(
                eigenvalues, roots[level % len(roots)]
            )
            residuals.append(0.5 * (1.0 - symbol) * carry)
            carry = 0.5 * (1.0 + symbol) * carry
        partition = sum(value.abs().square() for value in residuals)
        partition += carry.abs().square()
        max_error = max(
            max_error, float((partition - 1.0).abs().max().item())
        )
    return _row(
        "GA-05",
        evaluator="evaluate_pointwise_multilevel_partition",
        realization_tags=("exact",),
        graphs=_graph_context(graph_names),
        roots=_root_context(tuple(_root_registry())),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={"depth": 16, "real_grid_points": 4001},
        metrics=[
            _error_metric("maximum_partition_residual", max_error, SCALAR_TOL)
        ],
    )


@lru_cache(maxsize=1)
def _evaluate_ga06_ga07_ga09() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    graph_names = (
        "path_5",
        "path_8",
        "cycle_even_6",
        "cycle_odd_7",
        "grid_2x4",
        "star_7",
        "complete_5",
        "disconnected_7",
        "random_weighted_seed_1701",
    )
    root_names = tuple(_root_registry())
    depths = (1, 2, 4, 8, 16)
    max_frame = max_energy = max_singular = max_condition = max_reconstruction = 0.0
    generator = torch.Generator().manual_seed(670900)
    for graph_name in graph_names:
        graph = _graph_registry()[graph_name]
        identity = torch.eye(graph.num_nodes, dtype=torch.complex128)
        for root_name in root_names:
            roots = _root_registry()[root_name]
            for depth in depths:
                operators = _operators(graph, roots, depth)
                analysis = tight_analysis_matrix(operators)
                frame_error = float(
                    torch.linalg.matrix_norm(
                        analysis.mH @ analysis - identity, ord=2
                    ).item()
                )
                singular_values = torch.linalg.svdvals(analysis)
                singular_error = float(
                    (singular_values - 1.0).abs().max().item()
                )
                condition_error = abs(
                    float(
                        (singular_values.max() / singular_values.min()).item()
                    )
                    - 1.0
                )
                signal = torch.randn(
                    graph.num_nodes,
                    2,
                    dtype=torch.complex128,
                    generator=generator,
                )
                components = apply_tight_analysis(signal, operators)
                coefficient_energy = sum(
                    component.abs().square().sum() for component in components
                )
                energy_error = (
                    coefficient_energy - signal.abs().square().sum()
                ).abs() / signal.abs().square().sum()
                reconstructed = adjoint_tight_synthesis(components, operators)
                reconstruction = float(
                    ((reconstructed - signal).norm() / signal.norm()).item()
                )
                max_frame = max(max_frame, frame_error)
                max_energy = max(max_energy, float(energy_error.item()))
                max_singular = max(max_singular, singular_error)
                max_condition = max(max_condition, condition_error)
                max_reconstruction = max(max_reconstruction, reconstruction)
    shared = {
        "graphs": _graph_context(graph_names),
        "roots": _root_context(root_names),
        "dtype": "torch.float64/torch.complex128",
        "device": "cpu",
        "configuration": {
            "depths": list(depths),
            "graph_count": len(graph_names),
            "root_fixture_count": len(root_names),
        },
    }
    ga06 = _row(
        "GA-06",
        evaluator="evaluate_multilevel_isometry_matrix",
        realization_tags=("exact",),
        metrics=[
            _error_metric("maximum_frame_operator_residual", max_frame, EXACT_TOL),
            _error_metric(
                "maximum_energy_relative_residual",
                max_energy,
                EXACT_TOL,
                relative_error=max_energy,
            ),
        ],
        **shared,
    )
    ga07 = _row(
        "GA-07",
        evaluator="evaluate_multilevel_conditioning_matrix",
        realization_tags=("exact",),
        metrics=[
            _error_metric("maximum_singular_value_residual", max_singular, EXACT_TOL),
            _error_metric("maximum_condition_number_residual", max_condition, EXACT_TOL),
        ],
        **shared,
    )
    ga09 = _row(
        "GA-09",
        evaluator="evaluate_exact_adjoint_synthesis_matrix",
        realization_tags=("exact",),
        metrics=[
            _error_metric(
                "maximum_reconstruction_relative_residual",
                max_reconstruction,
                EXACT_TOL,
                relative_error=max_reconstruction,
            )
        ],
        **shared,
    )
    return ga06, ga07, ga09


def _evaluate_ga08() -> dict[str, Any]:
    graph = _graph_registry()["path_8"]
    identity = torch.eye(graph.num_nodes, dtype=torch.complex128)
    root = _root_registry()["generic_complex"]
    exact = exact_blaschke_operator(graph.laplacian, root)
    approximate = dense_chebyshev_operator(
        graph.laplacian,
        torch.tensor(
            [0.7 + 0.1j, -0.25 + 0.2j, 0.05 - 0.1j],
            dtype=torch.complex128,
        ),
    )
    nonunitary = torch.diag(
        torch.linspace(0.2, 1.4, graph.num_nodes, dtype=torch.float64)
    ).to(torch.complex128)
    generator = torch.Generator().manual_seed(800)
    signal = torch.randn(
        graph.num_nodes, 3, dtype=torch.complex128, generator=generator
    )
    components = apply_tight_analysis(signal, [exact, approximate, nonunitary])
    additive = sum(components[:-1], start=torch.zeros_like(signal)) + components[-1]
    multilevel_error = float(((additive - signal).norm() / signal.norm()).item())
    one_level = apply_tight_analysis(signal, [nonunitary])
    one_level_error = float(
        ((one_level[0] + one_level[1] - signal).norm() / signal.norm()).item()
    )
    nonunitarity = float(
        torch.linalg.matrix_norm(nonunitary.mH @ nonunitary - identity, ord=2).item()
    )
    return _row(
        "GA-08",
        evaluator="evaluate_additive_reconstruction",
        realization_tags=("exact", "chebyshev-K"),
        graphs=_graph_context(("path_8",)),
        roots=_root_context(("generic_complex",)),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={"depth": 3, "includes_deliberately_nonunitary_factor": True},
        metrics=[
            _error_metric(
                "one_level_additive_relative_residual",
                one_level_error,
                ZERO_TOL,
                relative_error=one_level_error,
            ),
            _error_metric(
                "multilevel_additive_relative_residual",
                multilevel_error,
                ZERO_TOL,
                relative_error=multilevel_error,
            ),
            _lower_bound_metric("nonunitarity_witness", nonunitarity, 1e-3),
        ],
    )


def _evaluate_ga10() -> dict[str, Any]:
    graph = _graph_registry()["weighted_6"]
    model = GBDNTight(
        in_channels=2,
        hidden_channels=2,
        out_channels=2,
        num_layers=2,
        K=4,
        num_roots=1,
    ).double()
    model.eval()
    with torch.no_grad():
        model.lifting.weight.copy_(
            torch.tensor(
                [
                    [0.2, -0.1],
                    [0.4, 0.3],
                    [-0.25, 0.5],
                    [0.15, -0.35],
                ],
                dtype=torch.float64,
            )
        )
        model.lifting.bias.copy_(
            torch.tensor([0.1, -0.2, 0.3, -0.4], dtype=torch.float64)
        )
        for layer_index, layer in enumerate(model.layers):
            layer.root_params.copy_(
                torch.tensor(
                    [[-0.8 + 0.3 * layer_index, 0.25 + 0.6 * layer_index]],
                    dtype=torch.float64,
                )
            )
        model.readout.weight.copy_(
            torch.arange(1, 25, dtype=torch.float64).reshape(2, 12) / 17.0
        )
        model.readout.bias.copy_(torch.tensor([0.2, -0.3], dtype=torch.float64))

    signal = torch.tensor(
        [
            [0.3, -0.7],
            [1.2, 0.4],
            [-0.5, 0.8],
            [0.9, -1.1],
            [0.2, 0.6],
            [-0.8, -0.1],
        ],
        dtype=torch.float64,
    )
    lifted_real = (
        signal @ model.lifting.weight.detach().mT + model.lifting.bias.detach()
    )
    lifted = torch.complex(lifted_real[:, :2], lifted_real[:, 2:])
    output = model.analyze_complex(
        lifted,
        graph.edge_index,
        graph.edge_weight,
        laplacian=graph.laplacian_token,
    )
    public_logits, forward_roots = model(
        signal,
        graph.edge_index,
        graph.edge_weight,
    )

    # Construct each production polynomial operator independently as a dense
    # Chebyshev recurrence, then perform the residual-first split in the dense
    # oracle. This does not read the public output fields to define expected
    # coefficient values.
    operators: list[torch.Tensor] = []
    for roots in output.roots:
        coefficients = blaschke_product_cheb_coeffs(
            roots,
            4,
            torch.device("cpu"),
        )
        operators.append(
            dense_chebyshev_operator(graph.laplacian, coefficients)
        )
    expected_components = apply_tight_analysis(lifted, operators)
    expected = torch.cat(expected_components, dim=-1)
    expected_features = torch.cat([expected.real, expected.imag], dim=-1)
    expected_logits = (
        expected_features @ model.readout.weight.detach().mT
        + model.readout.bias.detach()
    )
    component_errors = [
        float(
            (
                (observed - expected_component).norm()
                / expected_component.norm().clamp_min(1e-30)
            ).item()
        )
        for observed, expected_component in zip(
            output.components,
            expected_components,
            strict=True,
        )
    ]
    wrong = torch.cat((expected_components[-1], *expected_components[:-1]), dim=-1)
    wrong_features = torch.cat([wrong.real, wrong.imag], dim=-1)
    wrong_logits = (
        wrong_features @ model.readout.weight.detach().mT
        + model.readout.bias.detach()
    )
    readout_error = float(
        (
            (public_logits - expected_logits).norm()
            / expected_logits.norm().clamp_min(1e-30)
        ).item()
    )
    wrong_order_separation = float(
        ((output.concatenate() - wrong).norm() / expected.norm()).item()
    )
    wrong_readout_separation = float(
        ((expected_logits - wrong_logits).norm() / expected_logits.norm()).item()
    )
    root_error = max(
        float((left - right).abs().max().item())
        for left, right in zip(output.roots, forward_roots, strict=True)
    )
    public_synthesis = model.synthesize(
        output,
        graph.edge_index,
        graph.edge_weight,
        laplacian=graph.laplacian_token,
    )
    independent_synthesis = adjoint_tight_synthesis(
        expected_components,
        operators,
    )
    synthesis_error = float(
        (
            (public_synthesis - independent_synthesis).norm()
            / independent_synthesis.norm().clamp_min(1e-30)
        ).item()
    )
    return _row(
        "GA-10",
        evaluator="evaluate_public_coefficient_order",
        realization_tags=("exact", "chebyshev-K"),
        graphs=_graph_context(("weighted_6",)),
        roots=evidence_value(
            [
                {
                    "fixture": f"public_model_layer_{index}",
                    "parameterization": "finite-radial-logit-angle",
                    "values": _serialized_roots(roots),
                }
                for index, roots in enumerate(output.roots)
            ]
        ),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={
            "public_model": "GBDNTight",
            "depth": 2,
            "degree": 4,
            "expected_order": ["r_0", "r_1", "h_D"],
            "independent_assembly": (
                "dense Chebyshev operators plus independent residual-first oracle"
            ),
            "negative_control_order": ["h_D", "r_0", "r_1"],
        },
        metrics=[
            _error_metric(
                "maximum_public_component_relative_residual",
                max(component_errors),
                SPARSE_TOL,
                relative_error=max(component_errors),
            ),
            _error_metric(
                "residual_first_tuple_relative_residual",
                float(
                    (
                        (output.concatenate() - expected).norm()
                        / expected.norm().clamp_min(1e-30)
                    ).item()
                ),
                SPARSE_TOL,
                relative_error=float(
                    (
                        (output.concatenate() - expected).norm()
                        / expected.norm().clamp_min(1e-30)
                    ).item()
                ),
            ),
            _error_metric(
                "public_forward_readout_relative_residual",
                readout_error,
                EXACT_TOL,
                relative_error=readout_error,
            ),
            _error_metric("public_forward_root_residual", root_error, 0.0),
            _error_metric(
                "public_synthesis_vs_dense_adjoint_relative_residual",
                synthesis_error,
                SPARSE_TOL,
                relative_error=synthesis_error,
            ),
            _lower_bound_metric(
                "wrong_order_coefficient_relative_separation",
                wrong_order_separation,
                1e-3,
            ),
            _lower_bound_metric(
                "wrong_order_readout_relative_separation",
                wrong_readout_separation,
                1e-3,
            ),
        ],
    )


def _evaluate_ga11() -> dict[str, Any]:
    graph = _graph_registry()["complete_5"]
    roots = _root_registry()["multi_root"]
    eigenvalues, eigenvectors = torch.linalg.eigh(graph.laplacian)
    operators = _operators(graph, roots, 8)
    generator = torch.Generator().manual_seed(1100)
    signal = torch.randn(
        graph.num_nodes, 3, dtype=torch.complex128, generator=generator
    )
    components = apply_tight_analysis(signal, operators)
    complex_vectors = eigenvectors.to(torch.complex128)
    repeated_projector = complex_vectors[:, 1:] @ complex_vectors[:, 1:].mH
    spectral_power = (
        complex_vectors
        * eigenvalues.clamp_min(0.0).sqrt().to(torch.complex128).unsqueeze(0)
    ) @ complex_vectors.mH
    complex_laplacian = graph.laplacian.to(torch.complex128)
    weights = {
        "I": torch.eye(graph.num_nodes, dtype=torch.complex128),
        "L": complex_laplacian,
        "L2": complex_laplacian @ complex_laplacian,
        "L_half": spectral_power,
        "repeated_eigenspace_projector": repeated_projector,
    }
    residuals: dict[str, float] = {}
    for name, weight in weights.items():
        input_energy = torch.einsum(
            "nc,nm,mc->", signal.conj(), weight, signal
        ).real
        output_energy = sum(
            torch.einsum("nc,nm,mc->", value.conj(), weight, value).real
            for value in components
        )
        residuals[name] = float(
            (
                (output_energy - input_energy).abs()
                / input_energy.abs().clamp_min(1e-30)
            ).item()
        )
    maximum = max(residuals.values())
    return _row(
        "GA-11",
        evaluator="evaluate_weighted_spectral_parseval",
        realization_tags=("exact",),
        graphs=_graph_context(("complete_5",)),
        roots=_root_context(("multi_root",)),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={"depth": 8, "weights": list(weights)},
        metrics=[
            _metric(
                "weighted_energy_relative_residuals",
                observed=residuals,
                absolute_residual=maximum,
                relative_residual=maximum,
                predicted_bound=EXACT_TOL,
                comparison=evidence_value(
                    {"operator": "<=", "decision": maximum <= EXACT_TOL}
                ),
                tolerance=EXACT_TOL,
            )
        ],
    )


def _evaluate_ga12() -> dict[str, Any]:
    graph = _graph_registry()["path_2"]
    roots = _root_registry()["generic_complex"]
    operator = exact_blaschke_operator(graph.laplacian, roots)
    signal = torch.tensor(
        [[1.0 + 0.2j], [-0.4 + 0.7j]], dtype=torch.complex128
    )
    components = apply_tight_analysis(signal, [operator])
    projector = torch.zeros((2, 2), dtype=torch.complex128)
    projector[0, 0] = 1.0
    complex_laplacian = graph.laplacian.to(torch.complex128)
    commutator = projector @ complex_laplacian - complex_laplacian @ projector
    commutator_norm = float(torch.linalg.matrix_norm(commutator, ord=2).item())
    input_energy = torch.einsum(
        "nc,nm,mc->", signal.conj(), projector, signal
    ).real
    output_energy = sum(
        torch.einsum("nc,nm,mc->", value.conj(), projector, value).real
        for value in components
    )
    mismatch = float((output_energy - input_energy).abs().item())
    return _row(
        "GA-12",
        evaluator="evaluate_noncommuting_node_projector_counterexample",
        realization_tags=("exact",),
        graphs=_graph_context(("path_2",)),
        roots=_root_context(("generic_complex",)),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={"projected_node": 0, "depth": 1},
        metrics=[
            _lower_bound_metric("projector_laplacian_commutator_norm", commutator_norm, 1e-6),
            _lower_bound_metric("node_projector_energy_mismatch", mismatch, 1e-6),
        ],
    )


def _evaluate_ga13() -> dict[str, Any]:
    graph = _graph_registry()["complete_5"]
    generator = torch.Generator().manual_seed(1300)
    coefficients = torch.randn(
        5, 3, dtype=torch.complex128, generator=generator
    )
    target = torch.tensor([1, 2, 3, 4])
    complement = torch.tensor([0])
    delta, eta = 0.08, 0.05
    response = torch.zeros(5, dtype=torch.complex128)
    response[target] = (1.0 - delta / 2.0) * torch.exp(
        torch.tensor(0.4j, dtype=torch.complex128)
    )
    response[complement] = (eta / 2.0) * torch.exp(
        torch.tensor(-0.7j, dtype=torch.complex128)
    )
    selected = response.unsqueeze(1) * coefficients
    target_ratio = float(
        (selected[target].norm() / coefficients[target].norm()).item()
    )
    complement_ratio = float(
        (
            selected[complement].norm()
            / coefficients[complement].norm().clamp_min(1e-30)
        ).item()
    )
    return _row(
        "GA-13",
        evaluator="evaluate_whole_eigenspace_energy_selection",
        realization_tags=("exact",),
        graphs=_graph_context(("complete_5",)),
        roots=evidence_na(
            "GA-13 tests a prescribed multiplier envelope, not a fitted Blaschke root"
        ),
        dtype="torch.complex128",
        device="cpu",
        configuration={"delta": delta, "eta": eta, "feature_dimensions": 3},
        metrics=[
            _lower_bound_metric("target_eigenspace_norm_ratio", target_ratio, 1.0 - delta),
            _upper_bound_metric("complement_eigenspace_norm_ratio", complement_ratio, eta),
        ],
    )


def _evaluate_ga14() -> dict[str, Any]:
    graph = _graph_registry()["weighted_6"]
    roots = _root_registry()["multi_root"][:2]
    degree = 8
    eigenvalues, eigenvectors = torch.linalg.eigh(graph.laplacian)
    exact_factor = exact_blaschke_operator(graph.laplacian, roots)
    coefficients_k = blaschke_product_cheb_coeffs(
        roots,
        degree,
        torch.device("cpu"),
    )
    approximate_factor = dense_chebyshev_operator(
        graph.laplacian,
        coefficients_k,
    )
    identity = torch.eye(graph.num_nodes, dtype=torch.complex128)
    q_exact = 0.5 * (identity - exact_factor)
    q_approximate = 0.5 * (identity - approximate_factor)
    q_symbol = 0.5 * (
        1.0 - exact_blaschke_symbol(eigenvalues, roots)
    )
    target_mask = torch.zeros(graph.num_nodes, dtype=torch.bool)
    target_mask[1::2] = True
    complement_mask = ~target_mask
    projector = (
        eigenvectors[:, target_mask] @ eigenvectors[:, target_mask].mT
    ).to(torch.complex128)
    generator = torch.Generator().manual_seed(1400)
    signal = torch.randn(
        graph.num_nodes, 3, dtype=torch.complex128, generator=generator
    )
    target_signal = projector @ signal
    spectral_coefficients = eigenvectors.to(torch.complex128).mH @ signal
    exact_error_squared = (q_exact @ signal - target_signal).abs().square().sum()
    decomposed = (
        (
            (q_symbol[target_mask] - 1.0).unsqueeze(1)
            * spectral_coefficients[target_mask]
        ).abs().square().sum()
        + (
            q_symbol[complement_mask].unsqueeze(1)
            * spectral_coefficients[complement_mask]
        ).abs().square().sum()
    )
    identity_error = float((exact_error_squared - decomposed).abs().item())
    epsilon_k = float(
        torch.linalg.matrix_norm(
            approximate_factor - exact_factor,
            ord=2,
        ).item()
    )
    induced_channel_error = float(
        torch.linalg.matrix_norm(q_approximate - q_exact, ord=2).item()
    )
    half_epsilon_residual = abs(induced_channel_error - 0.5 * epsilon_k)
    delta = float((q_symbol[target_mask] - 1.0).abs().max().item())
    eta = float(q_symbol[complement_mask].abs().max().item())
    spectral_exact_bound = float(
        (
            delta**2 * target_signal.norm().square()
            + eta**2 * (signal - target_signal).norm().square()
        ).sqrt().item()
    )
    theorem_perturbation_term = 0.5 * epsilon_k * float(signal.norm().item())
    triangle_bound = spectral_exact_bound + theorem_perturbation_term
    finite_error = float(
        (q_approximate @ signal - target_signal).norm().item()
    )
    actual_channel_perturbation = float(
        ((q_approximate - q_exact) @ signal).norm().item()
    )
    return _row(
        "GA-14",
        evaluator="evaluate_complex_recovery_decomposition",
        realization_tags=("exact", "chebyshev-K"),
        graphs=_graph_context(("weighted_6",)),
        roots=evidence_value(
            [
                {
                    "fixture": "multi-root-first-two",
                    "parameterization": "fixed-admissible",
                    "values": _serialized_roots(roots),
                }
            ]
        ),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={
            "spectral_points": graph.num_nodes,
            "feature_dimensions": 3,
            "degree": degree,
            "channel_relation": "q=(1-t)/2",
            "epsilon_k_operator_norm": epsilon_k,
            "epsilon_k_over_two": 0.5 * epsilon_k,
            "exact_recovery_norm": float(exact_error_squared.sqrt().item()),
            "delta": delta,
            "eta": eta,
            "spectral_exact_bound": spectral_exact_bound,
            "approximation_term_epsilon_over_two_times_signal_norm": (
                theorem_perturbation_term
            ),
            "finite_factor_kind": "actual-first-kind-chebyshev-interpolant",
        },
        metrics=[
            _error_metric("exact_error_decomposition_residual", identity_error, ZERO_TOL),
            _error_metric(
                "induced_channel_epsilon_over_two_residual",
                half_epsilon_residual,
                ZERO_TOL,
            ),
            _upper_bound_metric(
                "actual_channel_perturbation_norm",
                actual_channel_perturbation,
                theorem_perturbation_term,
            ),
            _upper_bound_metric("finite_recovery_error", finite_error, triangle_bound),
        ],
    )


def _evaluate_ga15() -> dict[str, Any]:
    graph = _graph_registry()["weighted_6"]
    permutation = torch.tensor([4, 1, 5, 0, 3, 2])
    permutation_matrix = torch.eye(graph.num_nodes, dtype=torch.float64)[permutation]
    inverse_permutation = torch.empty_like(permutation)
    inverse_permutation[permutation] = torch.arange(graph.num_nodes)
    permuted_edges = inverse_permutation[graph.edge_index]
    permuted_token = normalized_laplacian(
        permuted_edges, graph.edge_weight, graph.num_nodes
    )
    permuted_laplacian = permuted_token.to_dense()
    generator = torch.Generator().manual_seed(1500)
    signal = torch.randn(
        graph.num_nodes, 2, dtype=torch.complex128, generator=generator
    )
    complex_permutation = permutation_matrix.to(torch.complex128)
    permuted_signal = complex_permutation @ signal
    root_names = tuple(list(_root_registry())[:4])
    exact_operators = [
        exact_blaschke_operator(graph.laplacian, _root_registry()[name])
        for name in root_names
    ]
    exact_permuted = [
        exact_blaschke_operator(permuted_laplacian, _root_registry()[name])
        for name in root_names
    ]
    exact_error = 0.0
    for original, permuted in zip(
        apply_tight_analysis(signal, exact_operators),
        apply_tight_analysis(permuted_signal, exact_permuted),
        strict=True,
    ):
        expected = complex_permutation @ original
        exact_error = max(
            exact_error,
            float(((permuted - expected).norm() / expected.norm()).item()),
        )

    polynomial: list[torch.Tensor] = []
    polynomial_permuted: list[torch.Tensor] = []
    for name in root_names:
        coefficients = blaschke_product_cheb_coeffs(
            _root_registry()[name], 12, torch.device("cpu")
        )
        polynomial.append(_apply_sparse_polynomial(graph, coefficients))
        permuted_graph = EvidenceGraph(
            "weighted_6_permuted",
            graph.num_nodes,
            permuted_edges,
            graph.edge_weight,
            permuted_token,
        )
        polynomial_permuted.append(
            _apply_sparse_polynomial(permuted_graph, coefficients)
        )
    polynomial_error = 0.0
    for original, permuted in zip(
        apply_tight_analysis(signal, polynomial),
        apply_tight_analysis(permuted_signal, polynomial_permuted),
        strict=True,
    ):
        expected = complex_permutation @ original
        polynomial_error = max(
            polynomial_error,
            float(((permuted - expected).norm() / expected.norm()).item()),
        )
    graph_context = evidence_value(
        [
            graph.provenance(),
            {
                "fixture": "weighted_6_permuted",
                "num_nodes": graph.num_nodes,
                "semantic_sha256": permuted_token.sha256,
                "source": permuted_token.source,
            },
        ]
    )
    return _row(
        "GA-15",
        evaluator="evaluate_permutation_equivariance",
        realization_tags=("exact", "chebyshev-K"),
        graphs=graph_context,
        roots=_root_context(root_names),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={"depth": 4, "degree": 12, "permutation": permutation.tolist()},
        metrics=[
            _error_metric(
                "exact_coefficient_equivariance_relative_residual",
                exact_error,
                EXACT_TOL,
                relative_error=exact_error,
            ),
            _error_metric(
                "polynomial_coefficient_equivariance_relative_residual",
                polynomial_error,
                SPARSE_TOL,
                relative_error=polynomial_error,
            ),
        ],
    )


def _evaluate_ga16() -> dict[str, Any]:
    graph = _graph_registry()["complete_6"]
    roots = _root_registry()["multi_root"]
    eigenvalues, eigenvectors = torch.linalg.eigh(graph.laplacian)
    generator = torch.Generator().manual_seed(1616)
    rotation_block, _ = torch.linalg.qr(
        torch.randn(5, 5, dtype=torch.float64, generator=generator)
    )
    rotation = torch.eye(6, dtype=torch.float64)
    rotation[1:, 1:] = rotation_block
    rotated_vectors = eigenvectors @ rotation
    canonical = exact_blaschke_operator_from_eigendecomposition(
        eigenvalues, eigenvectors, roots
    )
    rotated = exact_blaschke_operator_from_eigendecomposition(
        eigenvalues, rotated_vectors, roots
    )
    operator_error = _relative_operator_error(rotated, canonical)
    symbol = exact_blaschke_symbol(eigenvalues, roots)
    scalar_error = float((symbol[1:] - symbol[1]).abs().max().item())
    return _row(
        "GA-16",
        evaluator="evaluate_repeated_eigenspace_invariance",
        realization_tags=("exact",),
        graphs=_graph_context(("complete_6",)),
        roots=_root_context(("multi_root",)),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={"repeated_eigenspace_dimension": 5},
        metrics=[
            _error_metric(
                "basis_rotation_operator_relative_residual",
                operator_error,
                EXACT_TOL,
                relative_error=operator_error,
            ),
            _error_metric("repeated_eigenspace_scalar_multiplier_residual", scalar_error, EXACT_TOL),
        ],
    )


def _evaluate_ga17() -> dict[str, Any]:
    path_graph = _graph_registry()["path_10"]
    cycle_graph = _graph_registry()["cycle_even_10"]
    coefficients = torch.tensor(
        [0.2 + 0.1j, -0.35 + 0.05j, 0.1 - 0.2j, 0.04 + 0.03j],
        dtype=torch.complex128,
    )
    path_operator = _apply_sparse_polynomial(path_graph, coefficients)
    cycle_operator = _apply_sparse_polynomial(cycle_graph, coefficients)
    rebuilt_cycle = dense_chebyshev_operator(
        cycle_graph.laplacian, coefficients
    )
    distinct_norm = float(
        torch.linalg.matrix_norm(path_operator - cycle_operator, ord=2).item()
    )
    rebuild_error = _relative_operator_error(cycle_operator, rebuilt_cycle)
    collision_count = int(path_graph.laplacian_token.sha256 == cycle_graph.laplacian_token.sha256)
    return _row(
        "GA-17",
        evaluator="evaluate_graph_identity_cache_safety",
        realization_tags=("chebyshev-K",),
        graphs=_graph_context(("path_10", "cycle_even_10")),
        roots=evidence_na(
            "GA-17 uses an explicit polynomial coefficient vector to isolate graph identity"
        ),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={"degree": 3, "num_nodes": 10},
        metrics=[
            _upper_bound_metric("semantic_hash_collision_count", collision_count, 0.0),
            _lower_bound_metric("distinct_graph_operator_distance", distinct_norm, 1e-6),
            _error_metric(
                "cycle_rebuild_operator_relative_residual",
                rebuild_error,
                EXACT_TOL,
                relative_error=rebuild_error,
            ),
        ],
    )


def _evaluate_ga18() -> dict[str, Any]:
    degree = 12
    nodes = torch.cos(
        torch.pi
        * (torch.arange(degree + 1, dtype=torch.float64) + 0.5)
        / (degree + 1)
    ) + 1.0
    generator = torch.Generator().manual_seed(1800)
    expected_coefficients = torch.randn(
        degree + 1, dtype=torch.complex128, generator=generator
    )
    samples = evaluate_chebyshev(expected_coefficients, nodes)
    recovered = dct_synthesis(samples, degree)
    coefficient_error = float((recovered - expected_coefficients).abs().max().item())
    node_error = float(
        (evaluate_chebyshev(recovered, nodes) - samples).abs().max().item()
    )
    graph = _graph_registry()["path_8"]
    dense = dense_chebyshev_operator(graph.laplacian, recovered)
    eigenvalues, eigenvectors = torch.linalg.eigh(graph.laplacian)
    spectral = (
        eigenvectors.to(torch.complex128)
        * evaluate_chebyshev(recovered, eigenvalues).unsqueeze(0)
    ) @ eigenvectors.to(torch.complex128).mH
    operator_error = _relative_operator_error(dense, spectral)
    return _row(
        "GA-18",
        evaluator="evaluate_chebyshev_coefficient_convention",
        realization_tags=("chebyshev-K",),
        graphs=_graph_context(("path_8",)),
        roots=evidence_na(
            "GA-18 uses arbitrary Chebyshev coefficients to isolate coefficient convention"
        ),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={"degree": degree, "node_convention": "first-kind"},
        metrics=[
            _error_metric("coefficient_recovery_max_residual", coefficient_error, EXACT_TOL),
            _error_metric("node_interpolation_max_residual", node_error, EXACT_TOL),
            _error_metric(
                "dense_recurrence_operator_relative_residual",
                operator_error,
                SPARSE_TOL,
                relative_error=operator_error,
            ),
        ],
    )


def _evaluate_ga19() -> dict[str, Any]:
    cases = (
        ("path_8", 4, "generic_complex"),
        ("cycle_odd_9", 8, "multi_root"),
        ("grid_2x4", 16, "conjugate_pair"),
        ("star_7", 32, "generic_complex"),
        ("random_weighted_seed_1701", 128, "multi_root"),
    )
    residuals: list[dict[str, Any]] = []
    maximum = 0.0
    for graph_name, degree, root_name in cases:
        graph = _graph_registry()[graph_name]
        coefficients = blaschke_product_cheb_coeffs(
            _root_registry()[root_name], degree, torch.device("cpu")
        )
        sparse = _apply_sparse_polynomial(graph, coefficients)
        dense = dense_chebyshev_operator(graph.laplacian, coefficients)
        error = _relative_operator_error(sparse, dense)
        maximum = max(maximum, error)
        residuals.append(
            {
                "fixture": graph_name,
                "degree": degree,
                "root_fixture": root_name,
                "relative_operator_residual": error,
            }
        )
    return _row(
        "GA-19",
        evaluator="evaluate_sparse_dense_polynomial_full_operator",
        realization_tags=("chebyshev-K",),
        graphs=_graph_context(tuple(case[0] for case in cases)),
        roots=_root_context(tuple(dict.fromkeys(case[2] for case in cases))),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={"cases": residuals},
        metrics=[
            _metric(
                "full_operator_relative_residuals",
                observed=residuals,
                absolute_residual=maximum,
                relative_residual=maximum,
                predicted_bound=SPARSE_TOL,
                comparison=evidence_value(
                    {"operator": "<=", "decision": maximum <= SPARSE_TOL}
                ),
                tolerance=SPARSE_TOL,
            )
        ],
    )


def _evaluate_ga20() -> dict[str, Any]:
    graph = _graph_registry()["path_9"]
    eigenvalues = torch.linalg.eigvalsh(graph.laplacian)
    cases = (
        ("generic_complex", 1.5),
        ("multi_root", 1.2),
        ("near_radius_cap", 1.02),
    )
    rows: list[dict[str, Any]] = []
    maximum_operator_spectral_mismatch = 0.0
    maximum_bound_violation = 0.0
    maximum_graph_interval_violation = 0.0
    maximum_relative_bound_violation = 0.0
    for root_name, rho in cases:
        roots = _root_registry()[root_name]
        for degree in (4, 8, 16, 32):
            exact = exact_blaschke_operator(graph.laplacian, roots)
            coefficients = blaschke_product_cheb_coeffs(
                roots, degree, torch.device("cpu")
            )
            approximate = dense_chebyshev_operator(graph.laplacian, coefficients)
            operator_error = float(
                torch.linalg.matrix_norm(exact - approximate, ord=2).item()
            )
            diagnostic = approximation_configuration_diagnostic(
                roots, degree, rho, eigenvalues, interval_grid_size=20_001
            )
            mismatch = abs(
                operator_error - diagnostic.graph_spectral_max_error
            )
            bound_slack = SLACK * max(
                1.0, diagnostic.certified_interpolation_error_bound
            )
            bound_violation = max(
                0.0,
                diagnostic.interval_grid_max_error
                - diagnostic.certified_interpolation_error_bound
                - bound_slack,
            )
            graph_interval_violation = max(
                0.0,
                diagnostic.graph_spectral_max_error
                - diagnostic.interval_grid_max_error
                - ZERO_TOL,
            )
            maximum_operator_spectral_mismatch = max(
                maximum_operator_spectral_mismatch, mismatch
            )
            maximum_bound_violation = max(
                maximum_bound_violation, bound_violation
            )
            maximum_graph_interval_violation = max(
                maximum_graph_interval_violation, graph_interval_violation
            )
            maximum_relative_bound_violation = max(
                maximum_relative_bound_violation,
                bound_violation
                / max(diagnostic.certified_interpolation_error_bound, 1e-30),
            )
            rows.append(
                {
                    "root_fixture": root_name,
                    "degree": degree,
                    "rho": rho,
                    "operator_error": operator_error,
                    "graph_spectral_max_error": diagnostic.graph_spectral_max_error,
                    "interval_grid_max_error": diagnostic.interval_grid_max_error,
                    "certified_bound": diagnostic.certified_interpolation_error_bound,
                }
            )
    return _row(
        "GA-20",
        evaluator="evaluate_exact_approximation_error_and_certificate",
        realization_tags=("exact", "chebyshev-K"),
        graphs=_graph_context(("path_9",)),
        roots=_root_context(tuple(case[0] for case in cases)),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={"cases": rows, "interval_grid_points": 20_001},
        metrics=[
            _error_metric(
                "operator_vs_graph_spectral_error_residual",
                maximum_operator_spectral_mismatch,
                EXACT_TOL,
            ),
            _metric(
                "interval_error_certificate_decisions",
                observed=rows,
                absolute_residual=maximum_bound_violation,
                relative_residual=maximum_relative_bound_violation,
                predicted_bound=[row["certified_bound"] for row in rows],
                comparison=evidence_value(
                    {"operator": "<=", "decision": maximum_bound_violation == 0.0}
                ),
                tolerance=SLACK,
            ),
            _upper_bound_metric(
                "graph_spectral_vs_interval_grid_violation",
                maximum_graph_interval_violation,
                0.0,
            ),
        ],
    )


def _evaluate_ga21() -> dict[str, Any]:
    roots = _root_registry()["generic_complex"]
    graph_names = ("path_8", "complete_5", "weighted_6")
    rows: list[dict[str, Any]] = []
    max_defect_violation = max_lower_violation = max_upper_violation = 0.0
    for graph_name in graph_names:
        graph = _graph_registry()[graph_name]
        for degree in (8, 16):
            exact = exact_blaschke_operator(graph.laplacian, roots)
            coefficients = blaschke_product_cheb_coeffs(
                roots, degree, torch.device("cpu")
            )
            approximate = dense_chebyshev_operator(graph.laplacian, coefficients)
            epsilon = float(
                torch.linalg.matrix_norm(approximate - exact, ord=2).item()
            )
            identity = torch.eye(graph.num_nodes, dtype=torch.complex128)
            residual = 0.5 * (identity - approximate)
            carry = 0.5 * (identity + approximate)
            frame = residual.mH @ residual + carry.mH @ carry
            frame_eigenvalues = torch.linalg.eigvalsh(frame)
            defect = float(
                torch.linalg.matrix_norm(frame - identity, ord=2).item()
            )
            predicted = epsilon + 0.5 * epsilon * epsilon
            slack = SLACK * max(1.0, predicted)
            defect_violation = max(0.0, defect - predicted - slack)
            lower_violation = max(
                0.0,
                1.0
                - predicted
                - slack
                - float(frame_eigenvalues.min().item()),
            )
            upper_violation = max(
                0.0,
                float(frame_eigenvalues.max().item())
                - (1.0 + predicted + slack),
            )
            max_defect_violation = max(max_defect_violation, defect_violation)
            max_lower_violation = max(max_lower_violation, lower_violation)
            max_upper_violation = max(max_upper_violation, upper_violation)
            rows.append(
                {
                    "graph_fixture": graph_name,
                    "degree": degree,
                    "epsilon_operator_norm": epsilon,
                    "predicted_frame_defect_bound": predicted,
                    "observed_frame_defect": defect,
                    "minimum_frame_eigenvalue": float(
                        frame_eigenvalues.min().item()
                    ),
                    "maximum_frame_eigenvalue": float(
                        frame_eigenvalues.max().item()
                    ),
                }
            )
    return _row(
        "GA-21",
        evaluator="evaluate_one_level_finite_frame_bound",
        realization_tags=("exact", "chebyshev-K"),
        graphs=_graph_context(graph_names),
        roots=_root_context(("generic_complex",)),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={
            "degrees": [8, 16],
            "cases": rows,
            "repeated_spectrum_fixture": "complete_5",
            "nonuniform_weighted_fixture": "weighted_6",
        },
        metrics=[
            _upper_bound_metric(
                "maximum_frame_defect_bound_violation",
                max_defect_violation,
                0.0,
            ),
            _upper_bound_metric(
                "maximum_lower_frame_eigenvalue_violation",
                max_lower_violation,
                0.0,
            ),
            _upper_bound_metric(
                "maximum_upper_frame_eigenvalue_violation",
                max_upper_violation,
                0.0,
            ),
        ],
    )


def _evaluate_ga22() -> dict[str, Any]:
    graph_names = ("path_8", "complete_5", "weighted_6")
    root_names = ("generic_complex", "multi_root", "real_interior")
    degrees = (8, 12, 16)
    rows: list[dict[str, Any]] = []
    maximum_frame_violation = maximum_synthesis_violation = 0.0
    maximum_additive_error = maximum_singular_frame_residual = 0.0
    for graph_index, graph_name in enumerate(graph_names):
        graph = _graph_registry()[graph_name]
        for depth in (1, 2, 4, 8, 16):
            approximate_operators: list[torch.Tensor] = []
            errors: list[float] = []
            for level in range(depth):
                roots = _root_registry()[root_names[level % len(root_names)]]
                degree = degrees[level % len(degrees)]
                exact = exact_blaschke_operator(graph.laplacian, roots)
                coefficients = blaschke_product_cheb_coeffs(
                    roots, degree, torch.device("cpu")
                )
                approximate = dense_chebyshev_operator(graph.laplacian, coefficients)
                approximate_operators.append(approximate)
                errors.append(
                    float(
                        torch.linalg.matrix_norm(
                            approximate - exact, ord=2
                        ).item()
                    )
                )
            analysis = tight_analysis_matrix(approximate_operators)
            identity = torch.eye(graph.num_nodes, dtype=torch.complex128)
            frame = analysis.mH @ analysis
            observed = float(
                torch.linalg.matrix_norm(frame - identity, ord=2).item()
            )
            diagnostic = multilevel_frame_bound(errors)
            slack = SLACK * max(1.0, diagnostic.delta)
            generator = torch.Generator().manual_seed(
                2200 + 100 * graph_index + depth
            )
            signal = torch.randn(
                graph.num_nodes,
                3,
                dtype=torch.complex128,
                generator=generator,
            )
            components = apply_tight_analysis(signal, approximate_operators)
            additive = sum(
                components[:-1], start=torch.zeros_like(signal)
            ) + components[-1]
            additive_error = float(
                ((additive - signal).norm() / signal.norm()).item()
            )
            synthesized = adjoint_tight_synthesis(
                components, approximate_operators
            )
            synthesis_error = float(
                ((synthesized - signal).norm() / signal.norm()).item()
            )
            singular_values = torch.linalg.svdvals(analysis)
            frame_eigenvalues = torch.linalg.eigvalsh(frame)
            singular_frame_residual = float(
                (
                    singular_values.square().sort().values
                    - frame_eigenvalues.sort().values
                ).abs().max().item()
            )
            maximum_frame_violation = max(
                maximum_frame_violation,
                max(0.0, observed - diagnostic.delta - slack),
            )
            maximum_synthesis_violation = max(
                maximum_synthesis_violation,
                max(0.0, synthesis_error - diagnostic.delta - slack),
            )
            maximum_additive_error = max(maximum_additive_error, additive_error)
            maximum_singular_frame_residual = max(
                maximum_singular_frame_residual, singular_frame_residual
            )
            rows.append(
                {
                    "graph_fixture": graph_name,
                    "depth": depth,
                    "per_level_errors": errors,
                    "predicted_delta": diagnostic.delta,
                    "observed_frame_defect": observed,
                    "additive_reconstruction_error": additive_error,
                    "adjoint_synthesis_error": synthesis_error,
                    "positive_lower_bound": diagnostic.positive_lower_bound,
                }
            )
    return _row(
        "GA-22",
        evaluator="evaluate_multilevel_finite_frame_bound",
        realization_tags=("exact", "chebyshev-K"),
        graphs=_graph_context(graph_names),
        roots=_root_context(root_names),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={
            "degrees": list(degrees),
            "cases": rows,
            "repeated_spectrum_fixture": "complete_5",
            "nonuniform_weighted_fixture": "weighted_6",
        },
        metrics=[
            _metric(
                "multilevel_frame_bound_decisions",
                observed=rows,
                absolute_residual=maximum_frame_violation,
                relative_residual=maximum_frame_violation,
                predicted_bound=[row["predicted_delta"] for row in rows],
                comparison=evidence_value(
                    {"operator": "<=", "decision": maximum_frame_violation == 0.0}
                ),
                tolerance=SLACK,
            ),
            _upper_bound_metric("maximum_additive_reconstruction_residual", maximum_additive_error, ZERO_TOL),
            _upper_bound_metric("maximum_adjoint_synthesis_bound_violation", maximum_synthesis_violation, 0.0),
            _error_metric("singular_values_vs_frame_spectrum_residual", maximum_singular_frame_residual, EXACT_TOL),
        ],
    )


def _evaluate_ga23() -> dict[str, Any]:
    mu, gamma = 1.0, 0.25
    gamma_min, gamma_max = 0.05, 1.0
    probability = (gamma - gamma_min) / (gamma_max - gamma_min)
    parameters = torch.tensor(
        [[0.0, math.log(probability / (1.0 - probability))]],
        dtype=torch.float64,
    )
    root = parameterize_center_width_roots(
        parameters, gamma_min=gamma_min, gamma_max=gamma_max
    )
    zero, pole = mapped_zero_pole(root)
    probes = torch.tensor([mu - gamma, mu, mu + gamma], dtype=torch.float64)
    derivative = tight_split_responses(probes, root)["phase_derivative"]
    expected = torch.tensor(
        [1.0 / gamma, 2.0 / gamma, 1.0 / gamma], dtype=torch.float64
    )
    phase_error = float((derivative - expected).abs().max().item())
    pole_error = abs(complex(pole.item()) - complex(mu, -gamma))
    anchor_root = 0.5 * cayley_map(torch.tensor([1.0], dtype=torch.float64))
    anchor_zero, _ = mapped_zero_pole(anchor_root)
    anchor_error = abs(float(anchor_zero.real.item()) - 0.8)
    pole_limited_rho_star = target_pole_ellipse_parameter(root)
    admissible_rho = 0.5 * (1.0 + pole_limited_rho_star)
    return _row(
        "GA-23",
        evaluator="evaluate_exact_center_width_and_angular_boundary",
        realization_tags=("exact",),
        graphs=evidence_na("GA-23 is a scalar root-localization identity"),
        roots=evidence_value(
            [
                {
                    "fixture": "exact_center_width",
                    "parameterization": "inverse-cayley(mu+i*gamma)",
                    "values": _serialized_roots(root),
                },
                {
                    "fixture": "angular_anchor_counterexample",
                    "parameterization": "rho*cayley(mu)",
                    "values": _serialized_roots(anchor_root),
                },
            ]
        ),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={
            "mu": mu,
            "gamma": gamma,
            "angular_anchor_mu": 1.0,
            "angular_anchor_rho": 0.5,
            "admissible_rho": admissible_rho,
            "pole_limited_rho_star": pole_limited_rho_star,
        },
        metrics=[
            _error_metric("center_and_hwhm_phase_residual", phase_error, SCALAR_TOL),
            _error_metric("mapped_pole_residual", pole_error, SCALAR_TOL),
            _error_metric("angular_anchor_center_0p8_residual", anchor_error, SCALAR_TOL),
            _lower_bound_metric(
                "pole_ellipse_margin_over_admissible_rho",
                pole_limited_rho_star - admissible_rho,
                0.0,
            ),
        ],
    )


def _evaluate_ga24() -> dict[str, Any]:
    graph = _graph_registry()["path_9"]
    roots = _root_registry()["multi_root"]
    eigenvalues = torch.linalg.eigvalsh(graph.laplacian)
    diagnostic = approximation_configuration_diagnostic(
        roots, 12, 1.2, eigenvalues, interval_grid_size=4097
    )
    violation = max(
        0.0,
        diagnostic.interval_grid_max_error
        - diagnostic.certified_interpolation_error_bound
        - SLACK * max(1.0, diagnostic.certified_interpolation_error_bound),
    )
    configuration = diagnostic.to_dict()
    configuration["target_root_pole_geometry"] = list(
        diagnostic.target_root_pole_geometry
    )
    return _row(
        "GA-24",
        evaluator="evaluate_joined_root_approximation_diagnostic",
        realization_tags=("exact", "chebyshev-K"),
        graphs=_graph_context(("path_9",)),
        roots=_root_context(("multi_root",)),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration=configuration,
        metrics=[
            _upper_bound_metric("certified_interval_error_violation", violation, 0.0),
            _descriptive_metric(
                "exact_target_root_pole_geometry",
                list(diagnostic.target_root_pole_geometry),
                "GA-24 exact-target geometry is descriptive; the finite polynomial "
                "has no literal finite poles and no monotonic ordering is an "
                "acceptance premise",
            ),
        ],
    )


def _evaluate_ga25() -> dict[str, Any]:
    eigenvalues = torch.tensor(
        [0.0, 0.2, 0.7, 1.4, 2.0], dtype=torch.float64
    )
    angles = torch.tensor([0.1, 0.7, 1.3, 2.0], dtype=torch.float64)
    roots = torch.polar(torch.full_like(angles, 1e-3), angles).to(
        torch.complex128
    )
    radial_logit = math.log(1e-3 / (0.95 - 1e-3))
    raw_parameters = torch.stack(
        [torch.full_like(angles, radial_logit), angles], dim=-1
    )
    reachable_roots = parameterize_roots(raw_parameters, r_max=0.95)
    reachability_error = float((reachable_roots - roots).abs().max().item())
    matrix = product_sum_evaluation_matrix(eigenvalues, roots)
    singular_values = torch.linalg.svdvals(matrix)
    rank = int(torch.linalg.matrix_rank(matrix).item())
    condition = float((singular_values.max() / singular_values.min()).item())
    target = torch.tensor(
        [0.3 + 0.1j, -0.2 + 0.4j, 1.1 - 0.3j, 0.2j, -0.7 - 0.1j],
        dtype=torch.complex128,
    )
    coefficients = torch.linalg.solve(matrix, target)
    residual = float(((matrix @ coefficients - target).norm() / target.norm()).item())

    # The existence theorem has no uniform conditioning guarantee.  A second
    # distinct but clustered spectrum records that boundary rather than
    # allowing the stable positive witness to hide it.
    ill_eigenvalues = torch.arange(5, dtype=torch.float64) * 1e-3
    ill_matrix = product_sum_evaluation_matrix(ill_eigenvalues, roots)
    ill_singular_values = torch.linalg.svdvals(ill_matrix)
    ill_rank = int(torch.linalg.matrix_rank(ill_matrix).item())
    ill_condition = float(
        (ill_singular_values.max() / ill_singular_values.min()).item()
    )
    ill_coefficients = torch.linalg.lstsq(ill_matrix, target).solution
    ill_residual = float(
        ((ill_matrix @ ill_coefficients - target).norm() / target.norm()).item()
    )
    return _row(
        "GA-25",
        evaluator="evaluate_product_sum_interpolation",
        realization_tags=("exact",),
        graphs=evidence_na("GA-25 uses a prescribed finite spectrum, not a graph fixture"),
        roots=evidence_value(
            [
                {
                    "fixture": "nonzero-small-radius",
                    "parameterization": "fixed-polar",
                    "values": _serialized_roots(roots),
                }
            ]
        ),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={
            "spectral_points": 5,
            "factor_count": 4,
            "stable_distinct_spectrum": eigenvalues.tolist(),
            "stable_singular_values": singular_values.tolist(),
            "ill_conditioned_distinct_spectrum": ill_eigenvalues.tolist(),
            "ill_conditioned_singular_values": ill_singular_values.tolist(),
            "ill_conditioned_numeric_rank": ill_rank,
            "ill_conditioned_interpolation_relative_residual": ill_residual,
            "finite_raw_parameters": raw_parameters.tolist(),
        },
        metrics=[
            _error_metric(
                "finite_raw_parameter_root_residual",
                reachability_error,
                SCALAR_TOL,
            ),
            _upper_bound_metric("rank_deficiency", 5 - rank, 0.0),
            _upper_bound_metric(
                "stable_evaluation_matrix_condition_number", condition, 1e8
            ),
            _error_metric(
                "interpolation_relative_residual",
                residual,
                EXACT_TOL,
                relative_error=residual,
            ),
            _lower_bound_metric(
                "ill_conditioned_evaluation_matrix_condition_number",
                ill_condition,
                1e10,
            ),
            _descriptive_metric(
                "ill_conditioned_interpolation_relative_residual",
                ill_residual,
                "GA-25 requires disclosure of ill-conditioned behavior; no "
                "small-residual acceptance premise is valid for this boundary fixture",
            ),
        ],
    )


def _evaluate_ga26() -> dict[str, Any]:
    design = torch.ones((2, 1), dtype=torch.complex128)
    target = torch.tensor([1.0, -1.0], dtype=torch.complex128)
    solution = torch.linalg.lstsq(design, target).solution
    residual = float((design @ solution - target).norm().item())
    return _row(
        "GA-26",
        evaluator="evaluate_repeated_eigenvalue_scalar_limitation",
        realization_tags=("exact",),
        graphs=evidence_na("GA-26 is a synthetic repeated-eigenvalue counterexample"),
        roots=evidence_na("GA-26 concerns every scalar spectral multiplier, independent of roots"),
        dtype="torch.complex128",
        device="cpu",
        configuration={"repeated_eigenspace_dimension": 2, "targets": [1.0, -1.0]},
        metrics=[
            _lower_bound_metric("least_squares_incompatibility_residual", residual, 1.0)
        ],
    )


def _evaluate_ga27() -> dict[str, Any]:
    roots = _root_registry()["generic_complex"]
    comparator = frozen_scalar_cayleynet_comparator(
        0.3,
        torch.tensor(
            [0.7 + 0.2j, -0.4 + 0.3j, 0.15 - 0.25j],
            dtype=torch.complex128,
        ),
        1.7,
    )
    gbdn = reduced_blaschke_pole_diagnostic(roots)
    comparator_poles = comparator["reduced_pole_multiset"]
    gbdn_poles = gbdn["reduced_pole_multiset"]
    comparator_axis_residual = max(
        abs(float(entry["pole"]["real"])) for entry in comparator_poles
    )
    minimum_separation = min(
        abs(
            complex(gbdn_entry["pole"]["real"], gbdn_entry["pole"]["imag"])
            - complex(
                comparator_entry["pole"]["real"],
                comparator_entry["pole"]["imag"],
            )
        )
        for gbdn_entry in gbdn_poles
        for comparator_entry in comparator_poles
    )
    off_axis = min(abs(float(entry["pole"]["real"])) for entry in gbdn_poles)
    lower_half_margin = min(-float(entry["pole"]["imag"]) for entry in gbdn_poles)
    cancellation_count = int(gbdn["cancelled_pair_count"])

    return _row(
        "GA-27",
        evaluator="evaluate_reduced_pole_locus_witness",
        realization_tags=("exact",),
        graphs=evidence_na("GA-27 is a scalar continuum pole-locus witness"),
        roots=_root_context(("generic_complex",)),
        dtype="torch.complex128",
        device="cpu",
        configuration={
            "frozen_comparator": comparator,
            "exact_gbdn_reduction": gbdn,
            "comparison_scope": (
                "exact scalar finite-order response, equality on a real interval "
                "with an accumulation point, after rational cancellation"
            ),
            "excluded_conclusions": [
                "finite-spectrum separation",
                "approximation superiority",
                "optimization superiority",
                "SpMV efficiency",
            ],
        },
        metrics=[
            _upper_bound_metric(
                "derived_cayleynet_reduced_pole_axis_residual",
                comparator_axis_residual,
                0.0,
            ),
            _upper_bound_metric(
                "gbdn_cancelled_zero_pole_pair_count",
                cancellation_count,
                0.0,
            ),
            _lower_bound_metric(
                "reduced_pole_distance_to_cayley_imaginary_axis_locus",
                off_axis,
                1e-6,
            ),
            _lower_bound_metric(
                "minimum_reduced_pole_multiset_separation",
                minimum_separation,
                1e-6,
            ),
            _lower_bound_metric("lower_half_plane_margin", lower_half_margin, 0.0),
        ],
    )


def _evaluate_ga28() -> dict[str, Any]:
    base_weights = torch.linspace(0.8, 1.4, 7, dtype=torch.float64)
    direction = torch.linspace(-0.4, 0.4, 7, dtype=torch.float64)
    rows: list[dict[str, Any]] = []
    max_violation = max_ratio = 0.0
    for root_name in ("generic_complex", "multi_root"):
        roots = _root_registry()[root_name]
        constant = fixed_root_perturbation_constant(roots)
        for scale in (1e-4, 1e-3, 1e-2):
            base_edges, base_directed_weights = _path(8)
            del base_directed_weights
            base_weight = base_weights.repeat_interleave(2)
            perturbed_weight = (
                base_weights + scale * direction
            ).repeat_interleave(2)
            base_token = normalized_laplacian(base_edges, base_weight, 8)
            perturbed_token = normalized_laplacian(
                base_edges, perturbed_weight, 8
            )
            laplacian = base_token.to_dense()
            perturbed = perturbed_token.to_dense()
            eta_l = float(
                torch.linalg.matrix_norm(laplacian - perturbed, ord=2).item()
            )
            eta_g = float(
                torch.linalg.matrix_norm(
                    exact_blaschke_operator(laplacian, roots)
                    - exact_blaschke_operator(perturbed, roots),
                    ord=2,
                ).item()
            )
            bound = constant * eta_l
            slack = SLACK * max(1.0, bound)
            violation = max(0.0, eta_g - bound - slack)
            ratio = eta_g / max(bound, 1e-30)
            max_violation = max(max_violation, violation)
            max_ratio = max(max_ratio, ratio)
            rows.append(
                {
                    "root_fixture": root_name,
                    "scale": scale,
                    "laplacian_perturbation_norm": eta_l,
                    "filter_perturbation_norm": eta_g,
                    "perturbation_constant": constant,
                    "predicted_bound": bound,
                    "observed_to_bound_ratio": ratio,
                    "base_semantic_sha256": base_token.sha256,
                    "perturbed_semantic_sha256": perturbed_token.sha256,
                }
            )
    graph_entries: dict[str, dict[str, Any]] = {}
    for row in rows:
        base_digest = row["base_semantic_sha256"]
        graph_entries.setdefault(
            base_digest,
            {
                "fixture": "weighted_path_8_base",
                "semantic_sha256": base_digest,
                "semantic_role": "base-normalized-laplacian",
            },
        )
        perturbed_digest = row["perturbed_semantic_sha256"]
        graph_entries.setdefault(
            perturbed_digest,
            {
                "fixture": f"weighted_path_8_scale_{row['scale']}",
                "semantic_sha256": perturbed_digest,
                "semantic_role": "perturbed-normalized-laplacian",
            },
        )
    graph_context = evidence_value(list(graph_entries.values()))
    return _row(
        "GA-28",
        evaluator="evaluate_fixed_root_graph_operator_perturbation",
        realization_tags=("exact",),
        graphs=graph_context,
        roots=_root_context(("generic_complex", "multi_root")),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={"cases": rows},
        metrics=[
            _upper_bound_metric("maximum_resolvent_bound_violation", max_violation, 0.0),
            _descriptive_metric(
                "maximum_observed_to_bound_ratio",
                max_ratio,
                "The theorem requires a ratio at most one with slack; the ratio is diagnostic, not a target value",
            ),
        ],
    )


def _evaluate_ga29() -> dict[str, Any]:
    graph = _graph_registry()["path_14"]
    degree = 3
    coefficients = torch.tensor(
        [0.4 + 0.1j, -0.2 + 0.3j, 0.1 - 0.05j, 0.03 + 0.02j],
        dtype=torch.complex128,
    )
    polynomial = dense_chebyshev_operator(graph.laplacian, coefficients)
    indices = torch.arange(graph.num_nodes)
    distance = (indices[:, None] - indices[None, :]).abs()
    off_hop = float(polynomial[distance > degree].abs().max().item())
    roots = _root_registry()["generic_complex"]
    exact = exact_blaschke_operator(graph.laplacian, roots)
    exact_nonlocal = float(exact[distance > degree].abs().max().item())
    return _row(
        "GA-29",
        evaluator="evaluate_polynomial_locality_and_exact_boundary",
        realization_tags=("exact", "chebyshev-K"),
        graphs=_graph_context(("path_14",)),
        roots=_root_context(("generic_complex",)),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={"degree": degree},
        metrics=[
            _upper_bound_metric("maximum_polynomial_entry_beyond_k_hops", off_hop, ZERO_TOL),
            _lower_bound_metric("exact_target_non_k_hop_witness", exact_nonlocal, 1e-8),
        ],
    )


def _evaluate_ga30() -> dict[str, Any]:
    graph = _graph_registry()["path_8"]
    cases: list[dict[str, Any]] = []
    maximum_count_error = maximum_storage_error = 0.0
    recorded_roots: list[dict[str, Any]] = []
    for depth, degree in ((1, 0), (1, 3), (2, 4), (4, 5)):
        torch.manual_seed(3000 + 10 * depth + degree)
        hidden_channels = 3
        model = GBDNTight(
            in_channels=2,
            hidden_channels=hidden_channels,
            out_channels=2,
            num_layers=depth,
            K=degree,
        )
        generator = torch.Generator().manual_seed(3000)
        signal = torch.randn(
            graph.num_nodes,
            hidden_channels,
            dtype=torch.complex64,
            generator=generator,
        )
        calls = 0
        original = torch.sparse.mm

        def counted_mm(matrix: torch.Tensor, features: torch.Tensor) -> torch.Tensor:
            nonlocal calls
            calls += 1
            return original(matrix, features)

        with patch.object(torch.sparse, "mm", counted_mm):
            analysis = model.analyze_complex(
                signal,
                graph.edge_index,
                edge_weight=graph.edge_weight.float(),
                laplacian=graph.laplacian_token,
            )
        expected_calls = depth * degree
        observed_storage = sum(
            component.numel() * component.element_size()
            for component in analysis.components
        )
        expected_storage = (
            (depth + 1)
            * graph.num_nodes
            * hidden_channels
            * signal.element_size()
        )
        count_error = abs(calls - expected_calls)
        storage_error = abs(observed_storage - expected_storage)
        maximum_count_error = max(maximum_count_error, float(count_error))
        maximum_storage_error = max(maximum_storage_error, float(storage_error))
        recorded_roots.extend(
            {
                "fixture": f"model_depth_{depth}_degree_{degree}_level_{level}",
                "parameterization": "learned-radial-polar-initial-state",
                "values": _serialized_roots(roots),
            }
            for level, roots in enumerate(analysis.roots)
        )
        cases.append(
            {
                "depth": depth,
                "degree": degree,
                "observed_spmv_count": calls,
                "predicted_spmv_count": expected_calls,
                "observed_coefficient_storage_bytes": observed_storage,
                "predicted_coefficient_storage_bytes": expected_storage,
                "component_order": list(analysis.component_names),
            }
        )
    return _row(
        "GA-30",
        evaluator="evaluate_sparse_operation_and_storage_count",
        realization_tags=("chebyshev-K",),
        graphs=_graph_context(("path_8",)),
        roots=evidence_value(recorded_roots),
        dtype="torch.float32/torch.complex64",
        device="cpu",
        configuration={
            "cases": cases,
            "spmv_counting_convention": "one torch.sparse.mm on a complex feature matrix",
        },
        metrics=[
            _upper_bound_metric("maximum_spmv_count_error", maximum_count_error, 0.0),
            _upper_bound_metric("maximum_coefficient_storage_byte_error", maximum_storage_error, 0.0),
        ],
    )


def _evaluate_ga31() -> dict[str, Any]:
    graph = _graph_registry()["weighted_6"]
    root_names = (
        "generic_complex",
        "multi_root",
        "real_interior",
        "conjugate_pair",
    )
    depth = 4
    exact_operators = [
        exact_blaschke_operator(graph.laplacian, _root_registry()[name])
        for name in root_names
    ]
    approximate_operators = []
    for name in root_names:
        coefficients = blaschke_product_cheb_coeffs(
            _root_registry()[name], 8, torch.device("cpu")
        )
        approximate_operators.append(
            dense_chebyshev_operator(graph.laplacian, coefficients)
        )
    generator = torch.Generator().manual_seed(3100)
    signal = torch.randn(
        graph.num_nodes, 3, dtype=torch.complex128, generator=generator
    )
    maximum_violation = 0.0
    minimum_ratio = float("inf")
    for operators in (exact_operators, approximate_operators):
        rows = torch.cat(apply_tight_analysis(signal, operators), dim=-1)
        for source in range(graph.num_nodes):
            for target in range(source + 1, graph.num_nodes):
                input_distance = (signal[source] - signal[target]).norm()
                lower = input_distance / math.sqrt(depth + 1)
                observed = (rows[source] - rows[target]).norm()
                maximum_violation = max(
                    maximum_violation,
                    float(torch.clamp(lower - observed - SLACK, min=0.0).item()),
                )
                if float(lower.item()) > 0.0:
                    minimum_ratio = min(
                        minimum_ratio,
                        float((observed / lower).item()),
                    )
    return _row(
        "GA-31",
        evaluator="evaluate_nodewise_coefficient_lower_bound",
        realization_tags=("exact", "chebyshev-K"),
        graphs=_graph_context(("weighted_6",)),
        roots=_root_context(root_names),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={"depth": depth, "degree": 8, "all_unordered_node_pairs": True},
        metrics=[
            _upper_bound_metric("maximum_lower_bound_violation", maximum_violation, 0.0),
            _lower_bound_metric("minimum_observed_to_required_ratio", minimum_ratio, 1.0),
        ],
    )


def _evaluate_ga32() -> dict[str, Any]:
    graph = _graph_registry()["cycle_odd_7"]
    roots = torch.tensor([0.5 + 0.0j], dtype=torch.complex128)
    zero_mode = torch.ones(graph.num_nodes, 2, dtype=torch.complex128)
    operator = exact_blaschke_operator(graph.laplacian, roots)
    residual, carry = apply_tight_analysis(zero_mode, [operator])
    carry_ratio = float((carry.norm() / zero_mode.norm()).item())
    residual_error = float(((residual - zero_mode).norm() / zero_mode.norm()).item())
    return _row(
        "GA-32",
        evaluator="evaluate_carried_state_annihilation_counterexample",
        realization_tags=("exact",),
        graphs=_graph_context(("cycle_odd_7",)),
        roots=evidence_value(
            [
                {
                    "fixture": "real-interior-zero-mode-witness",
                    "parameterization": "fixed-explicit-complex",
                    "values": _serialized_roots(roots),
                }
            ]
        ),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={"depth": 1, "feature_dimensions": 2},
        metrics=[
            _upper_bound_metric("carried_state_relative_norm", carry_ratio, EXACT_TOL),
            _error_metric(
                "residual_equals_input_relative_residual",
                residual_error,
                EXACT_TOL,
                relative_error=residual_error,
            ),
        ],
    )


def _evaluate_ga33() -> dict[str, Any]:
    graph = _graph_registry()["path_6"]
    roots = _root_registry()["multi_root"]
    analysis = tight_analysis_matrix(_operators(graph, roots, 8))
    column_norms = analysis.abs().square().sum(dim=0).sqrt()
    error = float((column_norms - 1.0).abs().max().item())
    return _row(
        "GA-33",
        evaluator="evaluate_global_jacobian_column_isometry",
        realization_tags=("exact",),
        graphs=_graph_context(("path_6",)),
        roots=_root_context(("multi_root",)),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={"depth": 8},
        metrics=[
            _error_metric("maximum_jacobian_column_norm_residual", error, EXACT_TOL)
        ],
    )


def _evaluate_ga34() -> dict[str, Any]:
    disconnected = _graph_registry()["disconnected_6"]
    roots = _root_registry()["real_interior"]
    disconnected_analysis = tight_analysis_matrix(
        _operators(disconnected, roots, 4)
    )
    source = 0
    target = 4
    target_rows = [
        level * disconnected.num_nodes + target for level in range(5)
    ]
    disconnected_global_error = abs(
        float(disconnected_analysis[:, source].norm().item()) - 1.0
    )
    disconnected_target = float(
        disconnected_analysis[target_rows, source].norm().item()
    )

    path_long = _graph_registry()["path_20"]
    endpoint_root = torch.tensor([0.8 + 0.0j], dtype=torch.complex128)
    endpoint_analysis = tight_analysis_matrix(
        [exact_blaschke_operator(path_long.laplacian, endpoint_root)]
    )
    endpoint_global_error = abs(
        float(endpoint_analysis[:, 0].norm().item()) - 1.0
    )
    endpoint_target = float(endpoint_analysis[[19, 39], 0].norm().item())

    path_short = _graph_registry()["path_8"]
    coefficients = torch.tensor(
        [0.2 + 0.1j, 0.3 - 0.2j], dtype=torch.complex128
    )
    polynomial = dense_chebyshev_operator(path_short.laplacian, coefficients)
    beyond_reach = float(polynomial[7, 0].abs().item())
    return _row(
        "GA-34",
        evaluator="evaluate_target_sensitivity_boundaries",
        realization_tags=("exact", "chebyshev-K"),
        graphs=_graph_context(("disconnected_6", "path_20", "path_8")),
        roots=evidence_value(
            [
                {
                    "fixture": "real-interior-disconnected",
                    "parameterization": "fixed-explicit-complex",
                    "values": _serialized_roots(roots),
                },
                {
                    "fixture": "real-interior-connected-endpoint",
                    "parameterization": "fixed-explicit-complex",
                    "values": _serialized_roots(endpoint_root),
                },
            ]
        ),
        dtype="torch.float64/torch.complex128",
        device="cpu",
        configuration={
            "disconnected_depth": 4,
            "connected_endpoint_depth": 1,
            "polynomial_degree": 1,
        },
        metrics=[
            _error_metric("disconnected_global_column_norm_residual", disconnected_global_error, EXACT_TOL),
            _upper_bound_metric("disconnected_target_block_norm", disconnected_target, ZERO_TOL),
            _error_metric("connected_global_column_norm_residual", endpoint_global_error, EXACT_TOL),
            _upper_bound_metric("connected_endpoint_target_block_norm", endpoint_target, ZERO_TOL),
            _upper_bound_metric("polynomial_beyond_reach_block_norm", beyond_reach, ZERO_TOL),
        ],
    )


def _evaluate_ga35() -> dict[str, Any]:
    graph = _graph_registry()["path_6"]
    model_classes = (GBDNTight, GBDNProductSum, GBDNRelaxed)
    rows: list[dict[str, Any]] = []
    maximum_parameter_identity_mismatch = 0
    maximum_optimizer_membership_mismatch = 0
    for index, model_class in enumerate(model_classes):
        torch.manual_seed(3500 + index)
        model = model_class(
            in_channels=3,
            hidden_channels=4,
            out_channels=2,
            num_layers=2,
            K=3,
        )
        before = {
            name: id(parameter) for name, parameter in model.named_parameters()
        }
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        optimizer_ids = {
            id(parameter)
            for group in optimizer.param_groups
            for parameter in group["params"]
        }
        generator = torch.Generator().manual_seed(3550 + index)
        features = torch.randn(
            graph.num_nodes, 3, generator=generator
        )
        predictions, _ = model(
            features,
            graph.edge_index,
            edge_weight=graph.edge_weight.float(),
        )
        predictions.square().mean().backward()
        after = {
            name: id(parameter) for name, parameter in model.named_parameters()
        }
        identity_mismatch = len(
            set(before.items()).symmetric_difference(set(after.items()))
        )
        optimizer_mismatch = len(
            optimizer_ids.symmetric_difference(set(after.values()))
        )
        maximum_parameter_identity_mismatch = max(
            maximum_parameter_identity_mismatch, identity_mismatch
        )
        maximum_optimizer_membership_mismatch = max(
            maximum_optimizer_membership_mismatch, optimizer_mismatch
        )
        rows.append(
            {
                "model": model_class.__name__,
                "parameter_count": len(after),
                "parameter_identity_mismatch_count": identity_mismatch,
                "optimizer_membership_mismatch_count": optimizer_mismatch,
            }
        )
    return _row(
        "GA-35",
        evaluator="evaluate_trainable_parameter_lifecycle",
        realization_tags=("chebyshev-K",),
        graphs=_graph_context(("path_6",)),
        roots=evidence_na(
            "GA-35 concerns parameter registration identity; realized root values are not its premise or conclusion"
        ),
        dtype="torch.float32",
        device="cpu",
        configuration={"models": rows, "optimizer": "Adam"},
        metrics=[
            _upper_bound_metric(
                "maximum_parameter_identity_mismatch_count",
                maximum_parameter_identity_mismatch,
                0.0,
            ),
            _upper_bound_metric(
                "maximum_optimizer_membership_mismatch_count",
                maximum_optimizer_membership_mismatch,
                0.0,
            ),
        ],
    )


def _compute_evidence_catalog() -> dict[str, Any]:
    ga03, ga04 = _evaluate_ga03_ga04()
    ga06, ga07, ga09 = _evaluate_ga06_ga07_ga09()
    rows = {
        "GA-00": _evaluate_ga00(),
        "GA-01": _evaluate_ga01(),
        "GA-02": _evaluate_ga02(),
        "GA-03": ga03,
        "GA-04": ga04,
        "GA-05": _evaluate_ga05(),
        "GA-06": ga06,
        "GA-07": ga07,
        "GA-08": _evaluate_ga08(),
        "GA-09": ga09,
        "GA-10": _evaluate_ga10(),
        "GA-11": _evaluate_ga11(),
        "GA-12": _evaluate_ga12(),
        "GA-13": _evaluate_ga13(),
        "GA-14": _evaluate_ga14(),
        "GA-15": _evaluate_ga15(),
        "GA-16": _evaluate_ga16(),
        "GA-17": _evaluate_ga17(),
        "GA-18": _evaluate_ga18(),
        "GA-19": _evaluate_ga19(),
        "GA-20": _evaluate_ga20(),
        "GA-21": _evaluate_ga21(),
        "GA-22": _evaluate_ga22(),
        "GA-23": _evaluate_ga23(),
        "GA-24": _evaluate_ga24(),
        "GA-25": _evaluate_ga25(),
        "GA-26": _evaluate_ga26(),
        "GA-27": _evaluate_ga27(),
        "GA-28": _evaluate_ga28(),
        "GA-29": _evaluate_ga29(),
        "GA-30": _evaluate_ga30(),
        "GA-31": _evaluate_ga31(),
        "GA-32": _evaluate_ga32(),
        "GA-33": _evaluate_ga33(),
        "GA-34": _evaluate_ga34(),
        "GA-35": _evaluate_ga35(),
    }
    return {"schema": EVIDENCE_SCHEMA, "rows": rows}


@lru_cache(maxsize=1)
def _cached_evidence_catalog() -> dict[str, Any]:
    # Model initialization in GA-30/35 uses PyTorch's global generator. Fork
    # and restore it so this read-only diagnostic cannot perturb a caller's RNG
    # stream while still pinning a deterministic initialization state.
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(1701)
        return _compute_evidence_catalog()


def evaluate_gate_a_evidence() -> dict[str, Any]:
    """Recompute and return a mutation-isolated in-memory evidence catalog."""

    return copy.deepcopy(_cached_evidence_catalog())


def _validate_json_value(value: Any, path: str, errors: list[str]) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            errors.append(f"{path}: numeric value must be finite")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]", errors)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                errors.append(f"{path}: mapping keys must be strings")
            _validate_json_value(item, f"{path}.{key}", errors)
        return
    errors.append(f"{path}: unsupported JSON value type {type(value).__name__}")


def _validate_typed_value(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path}: expected typed evidence object")
        return
    status = value.get("status")
    if status == "VALUE":
        if "value" not in value:
            errors.append(f"{path}: VALUE evidence is missing value")
        else:
            _validate_json_value(value["value"], f"{path}.value", errors)
    elif status == "N/A":
        rationale = value.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            errors.append(f"{path}: N/A evidence requires a rationale")
    else:
        errors.append(f"{path}: status must be VALUE or N/A")


def validate_evidence_catalog(catalog: Any) -> list[str]:
    """Return deterministic schema/provenance errors for an evidence catalog."""

    errors: list[str] = []
    if not isinstance(catalog, dict):
        return ["catalog: expected mapping"]
    if catalog.get("schema") != EVIDENCE_SCHEMA:
        errors.append("catalog.schema: unexpected evidence schema")
    rows = catalog.get("rows")
    if not isinstance(rows, dict):
        errors.append("catalog.rows: expected mapping")
        return errors
    missing = [gate_id for gate_id in REQUIRED_IDS if gate_id not in rows]
    extra = sorted(set(rows) - set(REQUIRED_IDS))
    if missing:
        errors.append(f"catalog.rows: missing rows {', '.join(missing)}")
    if extra:
        errors.append(f"catalog.rows: unexpected rows {', '.join(extra)}")
    typed_fields = (
        "graph_semantic_hashes",
        "root_fixtures_and_values",
        "dtype",
        "device",
        "configuration",
    )
    metric_fields = (
        "observed_quantity",
        "absolute_residual",
        "relative_residual",
        "predicted_bound",
        "observed_vs_bound",
        "tolerance",
    )
    for gate_id in REQUIRED_IDS:
        row = rows.get(gate_id)
        path = f"catalog.rows.{gate_id}"
        if not isinstance(row, dict):
            if row is not None:
                errors.append(f"{path}: expected mapping")
            continue
        if row.get("gate_id") != gate_id:
            errors.append(f"{path}.gate_id: row identity mismatch")
        if not isinstance(row.get("evaluator"), str) or not row["evaluator"]:
            errors.append(f"{path}.evaluator: missing evaluator identity")
        tags = row.get("realization_tags")
        if not isinstance(tags, list) or not tags or not all(
            tag in {"exact", "chebyshev-K"} for tag in tags
        ):
            errors.append(f"{path}.realization_tags: invalid realization tags")
        for field_name in typed_fields:
            _validate_typed_value(
                row.get(field_name), f"{path}.{field_name}", errors
            )
        graph_context = row.get("graph_semantic_hashes", {})
        if graph_context.get("status") == "VALUE":
            graph_rows = graph_context.get("value")
            if not isinstance(graph_rows, list) or not graph_rows:
                errors.append(f"{path}.graph_semantic_hashes: empty graph list")
            else:
                for index, graph_row in enumerate(graph_rows):
                    digest = graph_row.get("semantic_sha256") if isinstance(graph_row, dict) else None
                    if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
                        errors.append(
                            f"{path}.graph_semantic_hashes.value[{index}]: invalid sha256"
                        )
        root_context = row.get("root_fixtures_and_values", {})
        if root_context.get("status") == "VALUE":
            root_rows = root_context.get("value")
            if not isinstance(root_rows, list) or not root_rows:
                errors.append(f"{path}.root_fixtures_and_values: empty root list")
            else:
                for index, root_row in enumerate(root_rows):
                    if not isinstance(root_row, dict):
                        errors.append(
                            f"{path}.root_fixtures_and_values.value[{index}]: expected mapping"
                        )
                        continue
                    values = root_row.get("values")
                    if not isinstance(values, list) or not values:
                        errors.append(
                            f"{path}.root_fixtures_and_values.value[{index}]: missing root values"
                        )
        metrics = row.get("metrics")
        if not isinstance(metrics, list) or not metrics:
            errors.append(f"{path}.metrics: at least one metric is required")
            continue
        names: set[str] = set()
        for index, metric in enumerate(metrics):
            metric_path = f"{path}.metrics[{index}]"
            if not isinstance(metric, dict):
                errors.append(f"{metric_path}: expected mapping")
                continue
            name = metric.get("name")
            if not isinstance(name, str) or not name:
                errors.append(f"{metric_path}.name: missing metric name")
            elif name in names:
                errors.append(f"{metric_path}.name: duplicate metric name {name}")
            else:
                names.add(name)
            for field_name in metric_fields:
                _validate_typed_value(
                    metric.get(field_name),
                    f"{metric_path}.{field_name}",
                    errors,
                )
            comparison = metric.get("observed_vs_bound", {})
            if comparison.get("status") == "VALUE":
                decision = comparison.get("value")
                if (
                    not isinstance(decision, dict)
                    or decision.get("operator") not in {"<=", ">=", "=="}
                    or not isinstance(decision.get("decision"), bool)
                ):
                    errors.append(
                        f"{metric_path}.observed_vs_bound: VALUE must contain "
                        "a supported operator and Boolean decision"
                    )
                else:
                    observed = metric.get("observed_quantity", {})
                    bound = metric.get("predicted_bound", {})
                    observed_value = observed.get("value")
                    bound_value = bound.get("value")
                    if (
                        observed.get("status") == "VALUE"
                        and bound.get("status") == "VALUE"
                        and isinstance(observed_value, (int, float))
                        and not isinstance(observed_value, bool)
                        and isinstance(bound_value, (int, float))
                        and not isinstance(bound_value, bool)
                    ):
                        operator = decision["operator"]
                        expected = {
                            "<=": observed_value <= bound_value,
                            ">=": observed_value >= bound_value,
                            "==": observed_value == bound_value,
                        }[operator]
                        if decision["decision"] is not expected:
                            errors.append(
                                f"{metric_path}.observed_vs_bound: recorded "
                                "decision disagrees with scalar values"
                            )
    return errors


def evidence_decision_failures(catalog: dict[str, Any]) -> list[str]:
    """Return row/metric identifiers whose recorded comparison is false."""

    failures: list[str] = []
    rows = catalog.get("rows", {})
    for gate_id in REQUIRED_IDS:
        for metric in rows.get(gate_id, {}).get("metrics", []):
            comparison = metric.get("observed_vs_bound", {})
            if comparison.get("status") != "VALUE":
                continue
            value = comparison.get("value")
            if isinstance(value, dict) and value.get("decision") is False:
                failures.append(f"{gate_id}:{metric.get('name', 'unnamed')}")
    return failures


def evidence_field_counts(catalog: dict[str, Any]) -> dict[str, int]:
    """Count typed VALUE/N/A fields under rows using a frozen definition."""

    counts = {"VALUE": 0, "N/A": 0, "TOTAL": 0}
    row_fields = (
        "graph_semantic_hashes",
        "root_fixtures_and_values",
        "dtype",
        "device",
        "configuration",
    )
    metric_fields = (
        "observed_quantity",
        "absolute_residual",
        "relative_residual",
        "predicted_bound",
        "observed_vs_bound",
        "tolerance",
    )
    for row in catalog.get("rows", {}).values():
        fields = [row.get(field_name) for field_name in row_fields]
        for metric in row.get("metrics", []):
            fields.extend(metric.get(field_name) for field_name in metric_fields)
        for value in fields:
            status = value.get("status") if isinstance(value, dict) else None
            if status in {"VALUE", "N/A"}:
                counts[status] += 1
            counts["TOTAL"] += 1
    return counts
