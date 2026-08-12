"""Fail-closed protocol contract for the five Platonov heterophily datasets.

This module contains metadata and validation only.  It never downloads or
loads a dataset, constructs a model, trains a checkpoint, or evaluates a test
split.  The distributed NPZ files remain the authoritative data objects; this
contract states what an acquisition/verification layer must prove before a
claim-bearing runner may consume them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Final, Literal, Mapping, Sequence


OFFICIAL_SOURCE_URL: Final[str] = (
    "https://github.com/yandex-research/heterophilous-graphs"
)
OFFICIAL_SOURCE_COMMIT: Final[str] = (
    "a431395582e929d88271309716bea4fe24ce6318"
)
OFFICIAL_SPLITS: Final[tuple[int, ...]] = tuple(range(10))
TRAINING_SEEDS: Final[tuple[int, ...]] = (0, 1, 2)
LOCAL_METHOD_CONFIG_PATHS: Final[dict[str, str]] = {
    "TightGBDN": "configs/submission/frozen/methods/TightGBDN.json",
    "ProductSumGBDN": "configs/submission/frozen/methods/ProductSumGBDN.json",
    "GBDNPlus": "configs/submission/frozen/methods/GBDNPlus.json",
}
UNRESOLVED: Final[str] = "UNRESOLVED_BLOCKER"

TaskType = Literal["multiclass", "binary"]
LossId = Literal["cross_entropy", "binary_cross_entropy_with_logits"]
MetricId = Literal["accuracy", "binary_roc_auc"]
_SHA256 = re.compile(r"[0-9a-f]{64}")
_GIT_BLOB = re.compile(r"[0-9a-f]{40}")
_ARRAY_NAMES: Final[frozenset[str]] = frozenset(
    {
        "node_features",
        "node_labels",
        "edges",
        "train_masks",
        "val_masks",
        "test_masks",
    }
)


class ProtocolContractError(ValueError):
    """Raised when metadata or execution intent violates the official contract."""


def _require_sha256(value: str, field: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ProtocolContractError(f"{field} must be 64 lowercase hex characters")
    return value


def _require_nonnegative(value: int, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ProtocolContractError(f"{field} must be a nonnegative integer")
    return value


@dataclass(frozen=True)
class DatasetTaskSpec:
    canonical_name: str
    aliases: tuple[str, ...]
    npz_path: str
    node_count: int
    stored_undirected_edges: int
    feature_count: int
    class_count: int
    task_type: TaskType
    output_logits: int
    loss_id: LossId
    selection_metric: MetricId
    test_metric: MetricId
    source_url: str = OFFICIAL_SOURCE_URL
    source_commit: str = OFFICIAL_SOURCE_COMMIT
    official_splits: tuple[int, ...] = OFFICIAL_SPLITS
    training_seeds: tuple[int, ...] = TRAINING_SEEDS
    npz_size_bytes: int = 0
    git_blob_sha1: str = UNRESOLVED
    npz_sha256: str = UNRESOLVED
    redistribution_terms: str = UNRESOLVED

    def __post_init__(self) -> None:
        if not self.canonical_name or self.canonical_name != self.canonical_name.strip():
            raise ProtocolContractError("canonical_name must be nonempty and trimmed")
        if not self.npz_path.startswith("data/") or not self.npz_path.endswith(".npz"):
            raise ProtocolContractError("npz_path must be an official data/*.npz path")
        for field, value in (
            ("node_count", self.node_count),
            ("stored_undirected_edges", self.stored_undirected_edges),
            ("feature_count", self.feature_count),
            ("class_count", self.class_count),
            ("output_logits", self.output_logits),
        ):
            if _require_nonnegative(value, field) == 0:
                raise ProtocolContractError(f"{field} must be positive")
        if self.official_splits != OFFICIAL_SPLITS:
            raise ProtocolContractError("official splits must be the supplied rows 0..9")
        if self.training_seeds != TRAINING_SEEDS:
            raise ProtocolContractError("training seeds must be the frozen set [0,1,2]")
        if self.source_url != OFFICIAL_SOURCE_URL or self.source_commit != OFFICIAL_SOURCE_COMMIT:
            raise ProtocolContractError("dataset source URL/commit differs from frozen source")
        if self.npz_size_bytes <= 0:
            raise ProtocolContractError("npz_size_bytes must be positive")
        if not isinstance(self.git_blob_sha1, str) or _GIT_BLOB.fullmatch(self.git_blob_sha1) is None:
            raise ProtocolContractError("git_blob_sha1 must be the pinned 40-hex Git blob ID")
        _require_sha256(self.npz_sha256, "npz_sha256")
        if self.task_type == "multiclass":
            expected = (self.class_count, "cross_entropy", "accuracy")
        elif self.task_type == "binary":
            expected = (1, "binary_cross_entropy_with_logits", "binary_roc_auc")
        else:
            raise ProtocolContractError(f"unsupported task_type: {self.task_type!r}")
        observed = (self.output_logits, self.loss_id, self.selection_metric)
        if observed != expected or self.test_metric != expected[2]:
            raise ProtocolContractError(
                "head/loss/selection/test metric does not match official task type"
            )

    @property
    def ready_for_acquisition(self) -> bool:
        return self.redistribution_terms != UNRESOLVED

    @property
    def blockers(self) -> tuple[str, ...]:
        blockers: list[str] = []
        if self.redistribution_terms == UNRESOLVED:
            blockers.append("dataset-specific redistribution terms are unresolved")
        return tuple(blockers)


def _spec(
    name: str,
    aliases: tuple[str, ...],
    npz: str,
    nodes: int,
    edges: int,
    features: int,
    classes: int,
    task: TaskType,
    npz_size_bytes: int,
    git_blob_sha1: str,
    npz_sha256: str,
) -> DatasetTaskSpec:
    multiclass = task == "multiclass"
    return DatasetTaskSpec(
        canonical_name=name,
        aliases=aliases,
        npz_path=npz,
        node_count=nodes,
        stored_undirected_edges=edges,
        feature_count=features,
        class_count=classes,
        task_type=task,
        output_logits=classes if multiclass else 1,
        loss_id="cross_entropy" if multiclass else "binary_cross_entropy_with_logits",
        selection_metric="accuracy" if multiclass else "binary_roc_auc",
        test_metric="accuracy" if multiclass else "binary_roc_auc",
        npz_size_bytes=npz_size_bytes,
        git_blob_sha1=git_blob_sha1,
        npz_sha256=npz_sha256,
    )


_SPECS: Final[tuple[DatasetTaskSpec, ...]] = (
    _spec("Roman-empire", ("roman-empire", "roman_empire"), "data/roman_empire.npz", 22662, 32927, 300, 18, "multiclass", 20401489, "1f9bae5e95b28e529015269e98acb237b65d8d3b", "a58ba741d123bf892fe5c872138d07463d75a2e9012360b8dd78ac2d4766d428"),
    _spec("Amazon-ratings", ("amazon-ratings", "amazon_ratings"), "data/amazon_ratings.npz", 24492, 93050, 300, 5, "multiclass", 27744018, "29647a8b0ff0ef856d73d683a8c3595bd5efbd38", "4c3a3e3b9d9f6cba0fede4625a00aad8c5721c1a36ed771367f446763241c7dd"),
    _spec("Minesweeper", ("minesweeper",), "data/minesweeper.npz", 10000, 39402, 7, 2, "binary", 135045, "cc2387032c65b92a5c520c473db1527cbb329d32", "e664c8dacf1e8ac466c2c09ed4b237bd2c5541f47a6eae9c6092cb87f16412b3"),
    _spec("Tolokers", ("tolokers",), "data/tolokers.npz", 11758, 519000, 10, 2, "binary", 1329769, "b8375a91a8f3c9e32c84fed7c151bbaf6ea6f0c7", "dacf3ac94cec53d03cd2adb5255c08b33dee1656c33ca8164a464bd9450a1667"),
    _spec("Questions", ("questions",), "data/questions.npz", 48921, 153540, 301, 2, "binary", 47369919, "4c7cb65057dbc9771af00fdfdee64a41b3875079", "757ebd772bab1475c4dd951ca9e364400c6db161656cff9d21780ee874cf3074"),
)

DATASET_REGISTRY: Final[Mapping[str, DatasetTaskSpec]] = MappingProxyType(
    {spec.canonical_name: spec for spec in _SPECS}
)
_ALIASES: Final[Mapping[str, str]] = MappingProxyType(
    {
        alias.casefold(): spec.canonical_name
        for spec in _SPECS
        for alias in (spec.canonical_name, *spec.aliases)
    }
)


def resolve_dataset(name: str) -> DatasetTaskSpec:
    """Resolve one frozen canonical name/alias without fuzzy matching."""

    if not isinstance(name, str) or not name or name != name.strip():
        raise ProtocolContractError("dataset name must be a nonempty trimmed string")
    canonical = _ALIASES.get(name.casefold())
    if canonical is None:
        raise ProtocolContractError(f"dataset is outside the official registry: {name!r}")
    return DATASET_REGISTRY[canonical]


def validate_task_dispatch(
    dataset: str,
    *,
    output_logits: int,
    loss_id: str,
    selection_metric: str,
    test_metric: str,
) -> DatasetTaskSpec:
    """Reject a head/loss/metric dispatch that differs from the official task."""

    spec = resolve_dataset(dataset)
    observed = (output_logits, loss_id, selection_metric, test_metric)
    expected = (
        spec.output_logits,
        spec.loss_id,
        spec.selection_metric,
        spec.test_metric,
    )
    if observed != expected:
        raise ProtocolContractError(
            f"task dispatch mismatch for {spec.canonical_name}: expected {expected}, got {observed}"
        )
    return spec


@dataclass(frozen=True)
class ArrayIdentity:
    name: str
    sha256: str
    dtype: str
    shape: tuple[int, ...]
    byte_order: Literal["little", "big", "not-applicable"]
    canonical_serialization: str

    def __post_init__(self) -> None:
        if self.name not in _ARRAY_NAMES:
            raise ProtocolContractError(f"unexpected NPZ array: {self.name!r}")
        _require_sha256(self.sha256, f"{self.name}.sha256")
        if not self.dtype or self.dtype != self.dtype.strip():
            raise ProtocolContractError(f"{self.name}.dtype must be nonempty and trimmed")
        if not self.shape or any(type(size) is not int or size <= 0 for size in self.shape):
            raise ProtocolContractError(f"{self.name}.shape must contain positive integers")
        if self.byte_order not in {"little", "big", "not-applicable"}:
            raise ProtocolContractError(f"{self.name}.byte_order is invalid")
        if (
            not isinstance(self.canonical_serialization, str)
            or not self.canonical_serialization
            or self.canonical_serialization != self.canonical_serialization.strip()
        ):
            raise ProtocolContractError(
                f"{self.name}.canonical_serialization must be nonempty and trimmed"
            )


@dataclass(frozen=True)
class SplitIdentity:
    split_id: int
    train_index_sha256: str
    validation_index_sha256: str
    test_index_sha256: str
    train_count: int
    validation_count: int
    test_count: int
    train_class_counts: tuple[int, ...]
    validation_class_counts: tuple[int, ...]
    test_class_counts: tuple[int, ...]
    pairwise_disjoint: bool
    covers_all_nodes: bool

    def __post_init__(self) -> None:
        if self.split_id not in OFFICIAL_SPLITS:
            raise ProtocolContractError("split_id must identify an official row 0..9")
        for field in ("train_index_sha256", "validation_index_sha256", "test_index_sha256"):
            _require_sha256(getattr(self, field), field)
        for field in ("train_count", "validation_count", "test_count"):
            _require_nonnegative(getattr(self, field), field)
        for field in (
            "train_class_counts",
            "validation_class_counts",
            "test_class_counts",
        ):
            counts = getattr(self, field)
            if not counts or any(type(count) is not int or count < 0 for count in counts):
                raise ProtocolContractError(f"{field} must contain nonnegative integers")
        if type(self.pairwise_disjoint) is not bool or type(self.covers_all_nodes) is not bool:
            raise ProtocolContractError("split invariant flags must be booleans")


@dataclass(frozen=True)
class GraphIdentity:
    node_count: int
    stored_undirected_edges: int
    expanded_directed_edges: int
    feature_count: int
    class_count: int
    self_loop_count: int
    duplicate_directed_edge_count: int
    connected_component_count: int
    bidirection_expansion_count: int
    raw_edge_sha256: str
    expanded_edge_sha256: str

    def __post_init__(self) -> None:
        for field in (
            "node_count",
            "stored_undirected_edges",
            "expanded_directed_edges",
            "feature_count",
            "class_count",
            "self_loop_count",
            "duplicate_directed_edge_count",
            "connected_component_count",
            "bidirection_expansion_count",
        ):
            _require_nonnegative(getattr(self, field), field)
        _require_sha256(self.raw_edge_sha256, "raw_edge_sha256")
        _require_sha256(self.expanded_edge_sha256, "expanded_edge_sha256")


@dataclass(frozen=True)
class DatasetIdentityCandidate:
    dataset: str
    source_commit: str
    npz_path: str
    npz_size_bytes: int
    npz_sha256: str
    redistribution_terms_record: str
    arrays: tuple[ArrayIdentity, ...]
    graph: GraphIdentity
    splits: tuple[SplitIdentity, ...]


def validate_dataset_identity(candidate: DatasetIdentityCandidate) -> DatasetTaskSpec:
    """Validate already-observed metadata without opening the underlying NPZ."""

    spec = resolve_dataset(candidate.dataset)
    if candidate.source_commit != spec.source_commit or candidate.npz_path != spec.npz_path:
        raise ProtocolContractError("dataset source commit or NPZ path is not the frozen source")
    if _require_nonnegative(candidate.npz_size_bytes, "npz_size_bytes") == 0:
        raise ProtocolContractError("npz_size_bytes must be positive")
    _require_sha256(candidate.npz_sha256, "npz_sha256")
    if (
        candidate.npz_size_bytes != spec.npz_size_bytes
        or candidate.npz_sha256 != spec.npz_sha256
    ):
        raise ProtocolContractError("dataset NPZ byte identity differs from the pinned registry")
    if candidate.redistribution_terms_record in {"", UNRESOLVED}:
        raise ProtocolContractError("dataset-specific redistribution terms are unresolved")

    names = [array.name for array in candidate.arrays]
    if len(names) != len(set(names)) or set(names) != _ARRAY_NAMES:
        raise ProtocolContractError("candidate must identify each required NPZ array exactly once")
    arrays = {array.name: array for array in candidate.arrays}
    array_hashes = [array.sha256 for array in candidate.arrays]
    if len(set(array_hashes)) != len(array_hashes):
        raise ProtocolContractError("distinct NPZ arrays must have distinct SHA-256 identities")
    if arrays["node_features"].shape != (spec.node_count, spec.feature_count):
        raise ProtocolContractError("node_features shape differs from official registry")
    if arrays["node_labels"].shape not in {(spec.node_count,), (spec.node_count, 1)}:
        raise ProtocolContractError("node_labels shape differs from official registry")
    if arrays["edges"].shape != (spec.stored_undirected_edges, 2):
        raise ProtocolContractError("raw edge shape differs from official registry")
    for name in ("train_masks", "val_masks", "test_masks"):
        if arrays[name].shape != (len(OFFICIAL_SPLITS), spec.node_count):
            raise ProtocolContractError(f"{name} must contain the ten supplied mask rows")

    graph = candidate.graph
    expected_graph = (
        spec.node_count,
        spec.stored_undirected_edges,
        2 * spec.stored_undirected_edges,
        spec.feature_count,
        spec.class_count,
        0,
        0,
        1,
        1,
    )
    observed_graph = (
        graph.node_count,
        graph.stored_undirected_edges,
        graph.expanded_directed_edges,
        graph.feature_count,
        graph.class_count,
        graph.self_loop_count,
        graph.duplicate_directed_edge_count,
        graph.connected_component_count,
        graph.bidirection_expansion_count,
    )
    if observed_graph != expected_graph:
        raise ProtocolContractError(
            f"graph invariants differ from official contract: expected {expected_graph}, got {observed_graph}"
        )
    if graph.raw_edge_sha256 == graph.expanded_edge_sha256:
        raise ProtocolContractError("raw and expanded graph identities must be distinct")

    if len(candidate.splits) != len(OFFICIAL_SPLITS):
        raise ProtocolContractError("candidate must contain exactly ten official splits")
    if tuple(split.split_id for split in candidate.splits) != OFFICIAL_SPLITS:
        raise ProtocolContractError("split identities must be the ordered official rows 0..9")
    all_split_hashes = [
        digest
        for split in candidate.splits
        for digest in (
            split.train_index_sha256,
            split.validation_index_sha256,
            split.test_index_sha256,
        )
    ]
    if len(set(all_split_hashes)) != len(all_split_hashes):
        raise ProtocolContractError("official split index identities must be globally distinct")
    for split in candidate.splits:
        if not split.pairwise_disjoint or not split.covers_all_nodes:
            raise ProtocolContractError(f"split {split.split_id} fails partition invariants")
        if split.train_count + split.validation_count + split.test_count != spec.node_count:
            raise ProtocolContractError(f"split {split.split_id} does not cover every node exactly once")
        for field, expected in (
            ("train_class_counts", split.train_count),
            ("validation_class_counts", split.validation_count),
            ("test_class_counts", split.test_count),
        ):
            counts = getattr(split, field)
            if len(counts) != spec.class_count or sum(counts) != expected:
                raise ProtocolContractError(
                    f"split {split.split_id} {field} does not match class/count contract"
                )
        split_hashes = {
            split.train_index_sha256,
            split.validation_index_sha256,
            split.test_index_sha256,
        }
        if len(split_hashes) != 3:
            raise ProtocolContractError(
                f"split {split.split_id} train/validation/test index identities are not distinct"
            )
    return spec


@dataclass(frozen=True)
class TrainingSelectionView:
    """Only identities that a training/checkpoint-selection process may receive."""

    dataset: str
    split_id: int
    train_index_sha256: str
    validation_index_sha256: str
    selection_metric: MetricId

    def __post_init__(self) -> None:
        spec = resolve_dataset(self.dataset)
        if self.split_id not in OFFICIAL_SPLITS:
            raise ProtocolContractError("training view split is not an official row")
        _require_sha256(self.train_index_sha256, "train_index_sha256")
        _require_sha256(self.validation_index_sha256, "validation_index_sha256")
        if self.selection_metric != spec.selection_metric:
            raise ProtocolContractError("training view uses the wrong validation metric")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "TrainingSelectionView":
        expected = {
            "dataset",
            "split_id",
            "train_index_sha256",
            "validation_index_sha256",
            "selection_metric",
        }
        if set(value) != expected:
            extra = sorted(set(value) - expected)
            missing = sorted(expected - set(value))
            raise ProtocolContractError(
                f"training selection keys mismatch; missing={missing}, extra={extra}"
            )
        return cls(**value)


def frozen_plan_jobs(
    methods: Sequence[str],
    *,
    splits: Sequence[int] = OFFICIAL_SPLITS,
    seeds: Sequence[int] = TRAINING_SEEDS,
) -> tuple[tuple[str, str, int, int], ...]:
    """Enumerate the exact dataset/method/split/seed product or fail closed."""

    if tuple(splits) != OFFICIAL_SPLITS:
        raise ProtocolContractError("confirmatory plan must use all official splits 0..9")
    if tuple(seeds) != TRAINING_SEEDS:
        raise ProtocolContractError("confirmatory plan must use frozen seeds [0,1,2]")
    if not methods or any(not isinstance(method, str) or not method.strip() for method in methods):
        raise ProtocolContractError("methods must be nonempty trimmed identifiers")
    if len(set(methods)) != len(methods):
        raise ProtocolContractError("methods must be unique")
    return tuple(
        (dataset, method, split, seed)
        for dataset in DATASET_REGISTRY
        for method in methods
        for split in OFFICIAL_SPLITS
        for seed in TRAINING_SEEDS
    )


__all__ = [
    "ArrayIdentity",
    "DATASET_REGISTRY",
    "DatasetIdentityCandidate",
    "DatasetTaskSpec",
    "GraphIdentity",
    "OFFICIAL_SOURCE_COMMIT",
    "OFFICIAL_SOURCE_URL",
    "OFFICIAL_SPLITS",
    "LOCAL_METHOD_CONFIG_PATHS",
    "ProtocolContractError",
    "SplitIdentity",
    "TRAINING_SEEDS",
    "TrainingSelectionView",
    "UNRESOLVED",
    "frozen_plan_jobs",
    "resolve_dataset",
    "validate_dataset_identity",
    "validate_task_dispatch",
]
