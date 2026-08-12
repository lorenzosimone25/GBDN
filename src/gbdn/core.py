"""Validated graph inputs for the canonical GBDN implementation.

The mathematical core is deliberately strict: an adjacency passed directly
to it must already be finite, nonnegative, loop-free, and symmetric. Directed
data must first pass through :func:`preprocess_reciprocal_mean`, whose policy
and semantic input/output hashes are returned with the resulting operator.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from typing import Any

import torch


DEFAULT_SYMMETRY_ATOL = 1e-14
NORMALIZED_LAPLACIAN_INTERVAL = (0.0, 2.0)


@dataclass(frozen=True)
class GraphPreprocessRecord:
    """Serializable provenance for the directed-to-undirected conversion."""

    policy: str
    policy_version: int
    num_nodes: int
    input_directed_edge_count: int
    input_coalesced_edge_count: int
    duplicate_directed_edge_count: int
    removed_self_loop_count: int
    removed_self_loop_weight: float
    isolated_vertex_count: int
    input_sha256: str
    output_sha256: str
    formula: str = "A_sym=(A+A^T)/2"
    duplicate_policy: str = "sum-before-symmetrization"
    self_loop_policy: str = "remove"
    missing_reverse_edge_weight: float = 0.0
    isolated_laplacian_diagonal: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-compatible policy metadata."""

        return asdict(self)


_VALIDATED_LAPLACIAN_TOKEN = object()


class ValidatedLaplacian:
    """Auditable token proving that a Laplacian passed canonical validation.

    Instances are issued only by canonical builders or by the one-time
    :func:`validate_external_laplacian` check. The wrapped tensor is cloned at
    issuance and its mutation version is checked on every unwrap, so it cannot
    be changed in place and silently reused.
    """

    __slots__ = (
        "_tensor",
        "_tensor_version",
        "source",
        "validation_method",
        "sha256",
    )

    def __init__(
        self,
        tensor: torch.Tensor,
        *,
        source: str,
        validation_method: str,
        sha256: str,
        _token: object,
    ) -> None:
        if _token is not _VALIDATED_LAPLACIAN_TOKEN:
            raise TypeError(
                "ValidatedLaplacian cannot be constructed directly; use a "
                "canonical graph builder or validate_external_laplacian"
            )
        self._tensor = tensor
        self._tensor_version = tensor._version
        self.source = source
        self.validation_method = validation_method
        self.sha256 = sha256

    @property
    def tensor(self) -> torch.Tensor:
        """Return the validated tensor after detecting in-place mutation."""

        if self._tensor._version != self._tensor_version:
            raise RuntimeError(
                "validated Laplacian was modified in place; validate a fresh operator"
            )
        return self._tensor

    @property
    def shape(self) -> torch.Size:
        return self.tensor.shape

    @property
    def layout(self) -> torch.layout:
        return self.tensor.layout

    @property
    def dtype(self) -> torch.dtype:
        return self.tensor.dtype

    @property
    def device(self) -> torch.device:
        return self.tensor.device

    def to_dense(self) -> torch.Tensor:
        """Materialize a dense copy for small-graph diagnostics."""

        tensor = self.tensor
        return tensor.to_dense() if tensor.layout == torch.sparse_coo else tensor.clone()


@dataclass(frozen=True)
class PreprocessedGraph:
    """Reciprocal-mean adjacency, normalized Laplacian, and provenance."""

    adjacency: torch.Tensor
    laplacian: ValidatedLaplacian
    record: GraphPreprocessRecord


def _validate_num_nodes(num_nodes: int | None, edge_index: torch.Tensor) -> int:
    if num_nodes is None:
        if edge_index.shape[1] == 0:
            raise ValueError("num_nodes is required when edge_index is empty")
        num_nodes = int(edge_index.max().item()) + 1
    if isinstance(num_nodes, bool) or not isinstance(num_nodes, int) or num_nodes <= 0:
        raise ValueError(f"num_nodes must be a positive integer, got {num_nodes!r}")
    return num_nodes


def _prepare_edges(
    edge_index: torch.Tensor,
    edge_weight: torch.Tensor | None,
    num_nodes: int | None,
    *,
    device: torch.device | None = None,
) -> tuple[torch.Tensor, torch.Tensor, int]:
    if edge_index.ndim != 2 or edge_index.shape[0] != 2:
        raise ValueError(
            f"edge_index must have shape [2, E], got {tuple(edge_index.shape)}"
        )
    integer_dtypes = {
        torch.uint8,
        torch.int8,
        torch.int16,
        torch.int32,
        torch.int64,
    }
    if edge_index.dtype not in integer_dtypes:
        raise TypeError(f"edge_index must use an integer dtype, got {edge_index.dtype}")
    num_nodes = _validate_num_nodes(num_nodes, edge_index)
    if device is None:
        device = edge_index.device
    indices = edge_index.to(device=device, dtype=torch.long)
    if indices.numel() > 0:
        if int(indices.min().item()) < 0 or int(indices.max().item()) >= num_nodes:
            raise ValueError("edge_index contains a vertex outside [0, num_nodes)")

    edge_count = indices.shape[1]
    if edge_weight is None:
        weights = torch.ones(
            edge_count,
            dtype=torch.get_default_dtype(),
            device=device,
        )
    else:
        if edge_weight.ndim != 1 or edge_weight.shape[0] != edge_count:
            raise ValueError(
                "edge_weight must be one-dimensional with one value per edge"
            )
        if edge_weight.is_complex():
            raise TypeError("graph adjacency weights must be real")
        weights = edge_weight.to(device=device)
        if not weights.is_floating_point():
            weights = weights.to(torch.get_default_dtype())

    if not torch.isfinite(weights).all():
        raise ValueError("graph adjacency weights must be finite")
    if torch.any(weights < 0):
        raise ValueError("graph adjacency weights must be nonnegative")
    return indices, weights, num_nodes


def _coalesced_adjacency(
    edge_index: torch.Tensor,
    edge_weight: torch.Tensor,
    num_nodes: int,
) -> torch.Tensor:
    adjacency = torch.sparse_coo_tensor(
        edge_index,
        edge_weight,
        (num_nodes, num_nodes),
        device=edge_weight.device,
        dtype=edge_weight.dtype,
        check_invariants=True,
    ).coalesce()
    values = adjacency.values()
    nonzero = values != 0
    if bool(nonzero.all()):
        return adjacency
    return torch.sparse_coo_tensor(
        adjacency.indices()[:, nonzero],
        values[nonzero],
        adjacency.shape,
        device=values.device,
        dtype=values.dtype,
        check_invariants=True,
    ).coalesce()


def _sparse_transpose(adjacency: torch.Tensor) -> torch.Tensor:
    return torch.sparse_coo_tensor(
        adjacency.indices().flip(0),
        adjacency.values(),
        adjacency.shape,
        device=adjacency.device,
        dtype=adjacency.dtype,
        check_invariants=True,
    ).coalesce()


def _symmetry_residual(adjacency: torch.Tensor) -> float:
    transpose = _sparse_transpose(adjacency)
    if not torch.equal(adjacency.indices(), transpose.indices()):
        return float("inf")
    if adjacency._nnz() == 0:
        return 0.0
    return float((adjacency.values() - transpose.values()).abs().max().item())


def _hash_sparse_matrix(matrix: torch.Tensor) -> str:
    matrix = matrix.coalesce()
    digest = hashlib.sha256()
    digest.update(str(tuple(matrix.shape)).encode("ascii"))
    digest.update(str(matrix.dtype).encode("ascii"))
    digest.update(matrix.indices().detach().cpu().contiguous().numpy().tobytes())
    digest.update(matrix.values().detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def _hash_operator(operator: torch.Tensor) -> str:
    if operator.layout == torch.sparse_coo:
        return _hash_sparse_matrix(operator)
    if operator.layout != torch.strided:
        raise TypeError("operator must be a dense or sparse COO tensor")
    digest = hashlib.sha256()
    digest.update(str(tuple(operator.shape)).encode("ascii"))
    digest.update(str(operator.dtype).encode("ascii"))
    digest.update(operator.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def _issue_validated_laplacian(
    operator: torch.Tensor,
    *,
    source: str,
    validation_method: str,
) -> ValidatedLaplacian:
    if operator.layout == torch.sparse_coo:
        frozen = operator.detach().clone().coalesce()
    elif operator.layout == torch.strided:
        frozen = operator.detach().clone()
    else:
        raise TypeError("operator must be a dense or sparse COO tensor")
    return ValidatedLaplacian(
        frozen,
        source=source,
        validation_method=validation_method,
        sha256=_hash_operator(frozen),
        _token=_VALIDATED_LAPLACIAN_TOKEN,
    )


def require_validated_laplacian(value: object) -> torch.Tensor:
    """Unwrap an issued Laplacian token or reject a raw external tensor."""

    if not isinstance(value, ValidatedLaplacian):
        raise TypeError(
            "caller-supplied laplacian must be a ValidatedLaplacian; call "
            "validate_external_laplacian once before repeated forwards"
        )
    return value.tensor


def validate_adjacency(
    edge_index: torch.Tensor,
    edge_weight: torch.Tensor | None = None,
    num_nodes: int | None = None,
    *,
    device: torch.device | None = None,
    symmetry_atol: float = DEFAULT_SYMMETRY_ATOL,
) -> torch.Tensor:
    """Return a coalesced adjacency or reject a noncanonical graph input.

    Duplicate directed entries are summed before validation. Direct core input
    may not contain self-loops; directed data and loop removal belong to the
    explicit preprocessing path.
    """

    indices, weights, num_nodes = _prepare_edges(
        edge_index,
        edge_weight,
        num_nodes,
        device=device,
    )
    if indices.shape[1] and torch.any(indices[0] == indices[1]):
        raise ValueError(
            "self-loops are not accepted by the core; use the recorded preprocessor"
        )
    adjacency = _coalesced_adjacency(indices, weights, num_nodes)
    residual = _symmetry_residual(adjacency)
    if not torch.isfinite(torch.tensor(residual)) or residual > symmetry_atol:
        raise ValueError(
            "adjacency must be symmetric; use preprocess_reciprocal_mean "
            f"for directed input (residual={residual})"
        )
    return adjacency


def normalized_laplacian_from_adjacency(adjacency: torch.Tensor) -> torch.Tensor:
    """Build the symmetric normalized Laplacian from validated adjacency.

    Every diagonal entry is one, including those of isolated vertices, as
    frozen by the scientific contract.
    """

    if adjacency.layout != torch.sparse_coo:
        raise TypeError("adjacency must be a sparse COO tensor")
    adjacency = adjacency.coalesce()
    if adjacency.ndim != 2 or adjacency.shape[0] != adjacency.shape[1]:
        raise ValueError("adjacency must be a square matrix")
    if not torch.isfinite(adjacency.values()).all():
        raise ValueError("adjacency values must be finite")
    if torch.any(adjacency.values() < 0):
        raise ValueError("adjacency values must be nonnegative")
    if adjacency._nnz() and torch.any(adjacency.indices()[0] == adjacency.indices()[1]):
        raise ValueError("validated adjacency must not contain self-loops")
    residual = _symmetry_residual(adjacency)
    if residual > DEFAULT_SYMMETRY_ATOL:
        raise ValueError(f"adjacency is not symmetric (residual={residual})")

    num_nodes = adjacency.shape[0]
    indices = adjacency.indices()
    values = adjacency.values()
    degree = torch.zeros(num_nodes, dtype=values.dtype, device=values.device)
    if adjacency._nnz():
        degree.index_add_(0, indices[0], values)
    inverse_sqrt = torch.zeros_like(degree)
    positive = degree > 0
    inverse_sqrt[positive] = degree[positive].rsqrt()
    normalized_values = values * inverse_sqrt[indices[0]] * inverse_sqrt[indices[1]]

    diagonal = torch.arange(num_nodes, device=indices.device, dtype=torch.long)
    laplacian_indices = torch.cat(
        [torch.stack([diagonal, diagonal]), indices],
        dim=1,
    )
    laplacian_values = torch.cat(
        [torch.ones(num_nodes, dtype=values.dtype, device=values.device), -normalized_values]
    )
    laplacian = torch.sparse_coo_tensor(
        laplacian_indices,
        laplacian_values,
        adjacency.shape,
        device=values.device,
        dtype=values.dtype,
        check_invariants=True,
    ).coalesce()
    validate_self_adjoint_operator(laplacian, spectral_bounds=None)
    return laplacian


def validated_normalized_laplacian(
    edge_index: torch.Tensor,
    edge_weight: torch.Tensor | None = None,
    num_nodes: int | None = None,
    *,
    device: torch.device | None = None,
) -> ValidatedLaplacian:
    """Validate an undirected graph and issue its normalized-Laplacian token."""

    adjacency = validate_adjacency(
        edge_index,
        edge_weight,
        num_nodes,
        device=device,
    )
    laplacian = normalized_laplacian_from_adjacency(adjacency)
    return _issue_validated_laplacian(
        laplacian,
        source="validated-undirected-adjacency",
        validation_method="normalized-laplacian-construction",
    )


def preprocess_reciprocal_mean(
    edge_index: torch.Tensor,
    edge_weight: torch.Tensor | None = None,
    num_nodes: int | None = None,
    *,
    device: torch.device | None = None,
) -> PreprocessedGraph:
    """Apply the recorded policy ``A_sym = (A + A.T) / 2``.

    Duplicate directed edges are summed first, missing reverse edges have zero
    weight, and input self-loops are removed and counted. Negative or nonfinite
    weights are rejected rather than repaired.
    """

    indices, weights, num_nodes = _prepare_edges(
        edge_index,
        edge_weight,
        num_nodes,
        device=device,
    )
    raw_edge_count = indices.shape[1]
    coalesced_input = _coalesced_adjacency(indices, weights, num_nodes)
    input_hash = _hash_sparse_matrix(coalesced_input)
    if raw_edge_count:
        directed_keys = indices[0] * num_nodes + indices[1]
        unique_directed_edge_count = int(torch.unique(directed_keys).numel())
    else:
        unique_directed_edge_count = 0
    duplicate_count = raw_edge_count - unique_directed_edge_count

    raw_self_loop_mask = indices[0] == indices[1]
    removed_self_loop_count = int(raw_self_loop_mask.sum().item())
    removed_self_loop_weight = float(weights[raw_self_loop_mask].sum().item())

    coalesced_indices = coalesced_input.indices()
    coalesced_values = coalesced_input.values()
    keep = coalesced_indices[0] != coalesced_indices[1]
    loop_free_indices = coalesced_indices[:, keep]
    loop_free_values = coalesced_values[keep]

    symmetric_indices = torch.cat(
        [loop_free_indices, loop_free_indices.flip(0)],
        dim=1,
    )
    symmetric_values = torch.cat(
        [0.5 * loop_free_values, 0.5 * loop_free_values],
        dim=0,
    )
    adjacency = _coalesced_adjacency(
        symmetric_indices,
        symmetric_values,
        num_nodes,
    )
    residual = _symmetry_residual(adjacency)
    if residual > DEFAULT_SYMMETRY_ATOL:
        raise RuntimeError(
            f"reciprocal-mean preprocessing produced residual {residual}"
        )
    laplacian_tensor = normalized_laplacian_from_adjacency(adjacency)
    laplacian = _issue_validated_laplacian(
        laplacian_tensor,
        source="reciprocal-mean-preprocessor-v1",
        validation_method="normalized-laplacian-construction",
    )

    degree = torch.zeros(
        num_nodes,
        dtype=adjacency.dtype,
        device=adjacency.device,
    )
    if adjacency._nnz():
        degree.index_add_(0, adjacency.indices()[0], adjacency.values())
    isolated_count = int((degree == 0).sum().item())
    record = GraphPreprocessRecord(
        policy="reciprocal-mean",
        policy_version=1,
        num_nodes=num_nodes,
        input_directed_edge_count=raw_edge_count,
        input_coalesced_edge_count=unique_directed_edge_count,
        duplicate_directed_edge_count=duplicate_count,
        removed_self_loop_count=removed_self_loop_count,
        removed_self_loop_weight=removed_self_loop_weight,
        isolated_vertex_count=isolated_count,
        input_sha256=input_hash,
        output_sha256=_hash_sparse_matrix(adjacency),
    )
    return PreprocessedGraph(adjacency=adjacency, laplacian=laplacian, record=record)


def validate_external_laplacian(operator: torch.Tensor) -> ValidatedLaplacian:
    """Perform the one-time full check required for caller-supplied operators.

    This path explicitly checks the spectrum in ``[0, 2]`` and clones the
    operator into a mutation-detecting token. Repeated forwards unwrap the
    token in constant time and do not repeat the eigendecomposition.
    """

    if operator.layout == torch.sparse_coo:
        candidate = operator.detach().clone().coalesce()
    elif operator.layout == torch.strided:
        candidate = operator.detach().clone()
    else:
        raise TypeError("operator must be a dense or sparse COO tensor")
    validate_self_adjoint_operator(candidate)
    return _issue_validated_laplacian(
        candidate,
        source="caller-supplied-operator",
        validation_method="explicit-self-adjoint-and-spectrum-check",
    )


def validate_self_adjoint_operator(
    operator: torch.Tensor,
    *,
    symmetry_atol: float = DEFAULT_SYMMETRY_ATOL,
    spectral_bounds: tuple[float, float] | None = NORMALIZED_LAPLACIAN_INTERVAL,
    spectral_atol: float = 1e-12,
) -> torch.Tensor:
    """Reject a nonfinite, nonsquare, non-self-adjoint graph operator.

    When ``spectral_bounds`` is provided, the full dense spectrum is checked.
    Canonical normalized-Laplacian construction may pass ``None`` because the
    bound follows from its validated nonnegative symmetric adjacency; dense
    theorem/oracle paths should retain the default explicit check.
    """

    if operator.ndim != 2 or operator.shape[0] != operator.shape[1]:
        raise ValueError(f"operator must be square, got shape {tuple(operator.shape)}")
    if operator.shape[0] == 0:
        raise ValueError("operator must be nonempty")

    if operator.layout == torch.sparse_coo:
        checked = operator.coalesce()
        if not torch.isfinite(checked.values()).all():
            raise ValueError("operator entries must be finite")
        transpose = torch.sparse_coo_tensor(
            checked.indices().flip(0),
            torch.conj(checked.values()),
            checked.shape,
            device=checked.device,
            dtype=checked.dtype,
            check_invariants=True,
        ).coalesce()
        if not torch.equal(checked.indices(), transpose.indices()):
            raise ValueError("operator must be self-adjoint")
        residual = (
            0.0
            if checked._nnz() == 0
            else float((checked.values() - transpose.values()).abs().max().item())
        )
        if residual > symmetry_atol:
            raise ValueError(f"operator must be self-adjoint (residual={residual})")
        dense = checked.to_dense() if spectral_bounds is not None else None
    elif operator.layout == torch.strided:
        checked = operator
        if not torch.isfinite(checked).all():
            raise ValueError("operator entries must be finite")
        residual = float((checked - checked.mH).abs().max().item())
        if residual > symmetry_atol:
            raise ValueError(f"operator must be self-adjoint (residual={residual})")
        dense = checked
    else:
        raise TypeError("operator must be a dense or sparse COO tensor")

    if spectral_bounds is not None:
        assert dense is not None
        lower, upper = spectral_bounds
        eigenvalues = torch.linalg.eigvalsh(dense)
        if not torch.isfinite(eigenvalues).all():
            raise ValueError("operator spectrum must be finite")
        observed_lower = float(eigenvalues.min().item())
        observed_upper = float(eigenvalues.max().item())
        if observed_lower < lower - spectral_atol or observed_upper > upper + spectral_atol:
            raise ValueError(
                "operator spectrum lies outside "
                f"[{lower}, {upper}]: [{observed_lower}, {observed_upper}]"
            )
    return operator
