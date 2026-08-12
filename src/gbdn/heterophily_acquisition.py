"""Pinned local acquisition and identity verification for Platonov-five data.

Raw archives are fetched only from the frozen upstream commit and remain in
the ignored ``data/`` directory.  Verification checks the whole-file identity
before NumPy parses an archive.  The upstream repository's MIT notice is
preserved for its software; this module deliberately does not infer separate
redistribution rights for the datasets contained in that repository.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import stat
import urllib.request
import uuid
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final

import numpy as np

from gbdn.heterophily_contract import (
    ArrayIdentity,
    DATASET_REGISTRY,
    DatasetIdentityCandidate,
    DatasetTaskSpec,
    GraphIdentity,
    OFFICIAL_SOURCE_COMMIT,
    OFFICIAL_SOURCE_URL,
    OFFICIAL_SPLITS,
    ProtocolContractError,
    SplitIdentity,
    validate_dataset_identity,
)


IDENTITY_SCHEMA: Final[str] = "gbdn-platonov5-dataset-identity-v1"
RAW_BASE_URL: Final[str] = (
    "https://raw.githubusercontent.com/yandex-research/heterophilous-graphs/"
    f"{OFFICIAL_SOURCE_COMMIT}"
)
LICENSE_RELATIVE_PATH: Final[str] = (
    "licenses/third_party/yandex_heterophilous_graphs_MIT.txt"
)
LICENSE_SOURCE_URL: Final[str] = f"{RAW_BASE_URL}/LICENCE.txt"
LICENSE_SIZE_BYTES: Final[int] = 1080
LICENSE_SHA256: Final[str] = (
    "71a17759c33e65c9660ee8afced33efdb24f0aea921467730a287dcbea451a0c"
)
MANIFEST_RELATIVE_PATH: Final[str] = (
    "results_submission/reports/heterophily_dataset_identity.json"
)
LOCAL_ACQUISITION_POLICY: Final[str] = "local-acquisition-only-v1"

ARRAY_SERIALIZATION: Final[str] = (
    "sha256-u64be-canonical-json-header(dtype,order,shape)-c-order-bytes-v1"
)
RAW_EDGE_SERIALIZATION: Final[str] = (
    "stable-lexicographic-raw-edge-rows-little-endian-int64-v1"
)
EXPANDED_EDGE_SERIALIZATION: Final[str] = (
    "stable-lexicographic-bidirected-edge-rows-little-endian-int64-v1"
)
SPLIT_INDEX_SERIALIZATION: Final[str] = (
    "sorted-node-indices-little-endian-int64-v1"
)
FILE_SERIALIZATION: Final[str] = "raw-file-bytes-v1"

_REQUIRED_ARRAYS: Final[tuple[str, ...]] = (
    "node_features",
    "node_labels",
    "edges",
    "train_masks",
    "val_masks",
    "test_masks",
)
_EXPECTED_ARRAY_HASHES: Final[Mapping[str, Mapping[str, str]]] = MappingProxyType(
    {
        "Roman-empire": MappingProxyType(
            dict(
                node_features="57cc4eaca147661eed8e109eed6e502fb5495f4405b33a790db477697ddf650f",
                node_labels="998ab2ade487eeddbebc2357587cf4986e6e2988e5dd1131b4b7825ad722467c",
                edges="fe320b29326c66cdf07d95a930dc661b9a835fb42b9380c14bfcaf01ead59077",
                train_masks="30e1b5d780eb6ff43ceb7b99b5ba9871b7067cb97c734a89278629d3de4acc1d",
                val_masks="af1e8fff789ebf8314aeb1833d48a509e28b1815f7f114d75ebabc9f918afbf2",
                test_masks="697e86865a17eb4e15b844f953a921b81c511f438bc1af91651a6fc089077880",
            )
        ),
        "Amazon-ratings": MappingProxyType(
            dict(
                node_features="6671bd714707679210693c2a5d7a4ed0205da2d51b39ed9dcea78429c7d0a084",
                node_labels="459bd6846ab900361d0c7cd7c92aedaf11730d64b791c7ffe6cb4605d06b8538",
                edges="639b03242157516691a60c490379d2947364911adae16b83ff57571f1be42f54",
                train_masks="1e375534e23e6524369aee7982793369d4bbb6dc01eb860b5545eb5b86f2fabc",
                val_masks="c7d9ccc1aaa85391a1e83d6bc4ecb7cd8b3af158283bbace5325746d39fd29aa",
                test_masks="23a1150e0800ad093d7296dfe7b23311bb152c6afde2d37f73c794d4ea72e5e9",
            )
        ),
        "Minesweeper": MappingProxyType(
            dict(
                node_features="94b4a7b985c7efc032c2257f97883db8df0c658dc7024cf39511dc8249a6fae2",
                node_labels="acdfd465600a11a64552cf8ce846f24bc71e276c4e0dea9523a7c6baa5db3887",
                edges="6b04520a037d00c9361c8ffa29a1989f1a710f64ef97e63b2e5f4e537e6aa22e",
                train_masks="98c56dffc21de6658713cb98a5dd690ca7a8b44557c952bd280652524098bd4e",
                val_masks="d6a30f935b3b63b2d371ad3f78db640e0f1451f4392245324f2ec29a54f31a43",
                test_masks="89e0ebffbfa3b822c1788bb3ed66ff1e47edf8651322009b18330e30421d6376",
            )
        ),
        "Tolokers": MappingProxyType(
            dict(
                node_features="6390afd1673d61969e599282827cd990735c3a3d77ee0bd929787bdc0836159e",
                node_labels="304868dda1e5ad0b1e439817f93ed72be4d979227e989904191c50ebd3dcb183",
                edges="d6993af4236813a1bd4e6ee20e4fd229cb64ecbaa64cc6ae2afa3856d06b2421",
                train_masks="1c44a899b35374c924605f52be940e9361b4b7565e6414e4026300adaa5bb188",
                val_masks="5b2ca9b8ea893aa814c62cab9486fa50ffb225d7108f656312c18fb44134fdaf",
                test_masks="5b220eb5765b8373ce7e8d80670071df360ab30b6ccc4c95b5f307fde7c72760",
            )
        ),
        "Questions": MappingProxyType(
            dict(
                node_features="791e0b004e33679e257803d6584c31529db1cd091e5fd12da502cc44d2a3dfcf",
                node_labels="2af20c8b8ee2cb1b57546b52c70e8accdd905845926f1e7991ff95eb56933767",
                edges="e85d1e41237d0fe02cff05eac07963e53ad716c3fe65a5d6eef52e8a07e881cb",
                train_masks="dcd988d861d729359ccc2fcdcd4587903b7b4ddbd07d775839fe95d28aa81649",
                val_masks="d6b95c30650af9135631cadb23f6ae063f0398d6d6d599b58323f18569e8dc05",
                test_masks="369f8c96c34796535cc3918f1259ea90a45867cc5bcdca57f61b2585fa39d09a",
            )
        ),
    }
)
_EXPECTED_GRAPH_HASHES: Final[Mapping[str, tuple[str, str]]] = MappingProxyType(
    {
        "Roman-empire": (
            "a38be2bc4b8c8b9d03a3c4dc407e7b4be6fc5efcbc23028eda5a15e975f9179a",
            "1096134adf66b46cd25944426625c6ebc421ecce5d8dd8d12977e7089dc90d50",
        ),
        "Amazon-ratings": (
            "5f31df5ac0dc18c7fd6bfacdc35f8f328fc987d0c0f245ff99a5619a8c43b057",
            "43a3a0ec59d75639eb1ced3b6e33e6b7fecf7cf92ef8bec773ca06ebc27a6c3c",
        ),
        "Minesweeper": (
            "6d8aee14222a04ff00a23d12106e4a644cebf390c0ac3230113746f78306e3fc",
            "8974be716ddae54c20fdad5ff034ff99731bdf4aa224ff897d1ebb4d1ae18005",
        ),
        "Tolokers": (
            "bd80c60721e11373581539af0f96f4e10473370832d3a6c037b144bf365957e2",
            "0de869a745efb0dd4de109fbe569155d022c4048a83a3c0db7719dc7b869f39f",
        ),
        "Questions": (
            "b165be96dfb304ad2a2a779c09d729e5c23398aeeceecfffe8988558b8af022b",
            "97104e2d7b7e992a5d1323c1479e165288fc9b9103d10eda56908c0609f1a039",
        ),
    }
)

Downloader = Callable[[str, Path, int], None]


def official_raw_url(spec: DatasetTaskSpec) -> str:
    """Return the only admitted acquisition URL for an official archive."""

    if spec.canonical_name not in DATASET_REGISTRY or DATASET_REGISTRY[spec.canonical_name] != spec:
        raise ProtocolContractError("acquisition accepts only a frozen registry dataset")
    return f"{RAW_BASE_URL}/{spec.npz_path}"


def _regular_file(path: Path, field: str) -> os.stat_result:
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise ProtocolContractError(f"missing {field}: {path}") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ProtocolContractError(f"{field} must be a regular, non-symlink file: {path}")
    return metadata


def _verified_archive_snapshot(path: Path, spec: DatasetTaskSpec) -> bytes:
    """Read and authenticate one immutable in-memory snapshot of an archive."""

    before = _regular_file(path, "dataset archive")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode):
            raise ProtocolContractError("dataset archive changed to a non-regular file")
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise ProtocolContractError("dataset archive changed while it was opened")
        payload = stream.read(spec.npz_size_bytes + 1)
        if stream.read(1):
            raise ProtocolContractError(
                f"{spec.canonical_name} archive identity mismatch: exceeds the pinned size"
            )
    if len(payload) != spec.npz_size_bytes:
        raise ProtocolContractError(
            f"{spec.canonical_name} archive identity mismatch: size differs from the pinned size"
        )
    sha256 = hashlib.sha256(payload).hexdigest()
    git_blob_digest = hashlib.sha1(f"blob {len(payload)}\0".encode("ascii"))
    git_blob_digest.update(payload)
    git_blob = git_blob_digest.hexdigest()
    if (sha256, git_blob) != (spec.npz_sha256, spec.git_blob_sha1):
        raise ProtocolContractError(
            f"{spec.canonical_name} archive identity mismatch: expected "
            f"{(spec.npz_size_bytes, spec.npz_sha256, spec.git_blob_sha1)}, got "
            f"{(len(payload), sha256, git_blob)}"
        )
    return payload


def verify_archive_bytes(path: Path, spec: DatasetTaskSpec) -> None:
    """Fail on a byte mismatch before any archive parsing can occur."""

    _verified_archive_snapshot(path, spec)


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _array_sha256(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array)
    header = _canonical_json_bytes(
        {
            "dtype": contiguous.dtype.str,
            "order": "C",
            "shape": list(contiguous.shape),
        }
    )
    digest = hashlib.sha256()
    digest.update(len(header).to_bytes(8, "big"))
    digest.update(header)
    digest.update(contiguous.tobytes(order="C"))
    return digest.hexdigest()


def _byte_order(dtype: np.dtype[Any]) -> str:
    if dtype.byteorder == "|":
        return "not-applicable"
    if dtype.byteorder == ">" or (dtype.byteorder == "=" and not np.little_endian):
        return "big"
    return "little"


def _sorted_edge_rows(edges: np.ndarray) -> np.ndarray:
    rows = np.ascontiguousarray(edges.astype("<i8", copy=False))
    order = np.lexsort((rows[:, 1], rows[:, 0]))
    return np.ascontiguousarray(rows[order])


def _edge_sha256(edges: np.ndarray) -> str:
    return hashlib.sha256(_sorted_edge_rows(edges).tobytes(order="C")).hexdigest()


def _index_sha256(mask: np.ndarray) -> str:
    indices = np.flatnonzero(mask).astype("<i8", copy=False)
    return hashlib.sha256(np.ascontiguousarray(indices).tobytes(order="C")).hexdigest()


def _connected_component_count(node_count: int, undirected_edges: np.ndarray) -> int:
    parents = np.arange(node_count, dtype=np.int64)
    ranks = np.zeros(node_count, dtype=np.uint8)

    def find(node: int) -> int:
        while int(parents[node]) != node:
            parents[node] = parents[int(parents[node])]
            node = int(parents[node])
        return node

    for left_raw, right_raw in undirected_edges:
        left = find(int(left_raw))
        right = find(int(right_raw))
        if left == right:
            continue
        if ranks[left] < ranks[right]:
            left, right = right, left
        parents[right] = left
        if ranks[left] == ranks[right]:
            ranks[left] += 1
    return len({find(node) for node in range(node_count)})


def _require_array_contract(arrays: Mapping[str, np.ndarray], spec: DatasetTaskSpec) -> None:
    expected = {
        "node_features": (np.dtype("<f4"), (spec.node_count, spec.feature_count)),
        "node_labels": (np.dtype("<i8"), (spec.node_count,)),
        "edges": (np.dtype("<i8"), (spec.stored_undirected_edges, 2)),
        "train_masks": (np.dtype("bool"), (len(OFFICIAL_SPLITS), spec.node_count)),
        "val_masks": (np.dtype("bool"), (len(OFFICIAL_SPLITS), spec.node_count)),
        "test_masks": (np.dtype("bool"), (len(OFFICIAL_SPLITS), spec.node_count)),
    }
    for name, (dtype, shape) in expected.items():
        array = arrays[name]
        if array.dtype != dtype or array.shape != shape:
            raise ProtocolContractError(
                f"{spec.canonical_name} {name} expected dtype/shape {dtype.str}/{shape}, "
                f"got {array.dtype.str}/{array.shape}"
            )


def inspect_verified_archive(
    path: Path,
    spec: DatasetTaskSpec,
    *,
    expected_array_hashes: Mapping[str, str] | None = None,
    expected_graph_hashes: tuple[str, str] | None = None,
) -> DatasetIdentityCandidate:
    """Inspect a byte-verified NPZ with pickle disabled and prove its invariants."""

    payload = _verified_archive_snapshot(path, spec)
    try:
        with np.load(io.BytesIO(payload), allow_pickle=False) as archive:
            if tuple(sorted(archive.files)) != tuple(sorted(_REQUIRED_ARRAYS)) or len(archive.files) != 6:
                raise ProtocolContractError(
                    f"{spec.canonical_name} must contain exactly the six official NPZ keys"
                )
            arrays = {name: np.asarray(archive[name]) for name in _REQUIRED_ARRAYS}
    except ProtocolContractError:
        raise
    except Exception as error:
        raise ProtocolContractError(
            f"{spec.canonical_name} could not be parsed safely with allow_pickle=False"
        ) from error

    _require_array_contract(arrays, spec)
    array_identities = tuple(
        ArrayIdentity(
            name=name,
            sha256=_array_sha256(arrays[name]),
            dtype=arrays[name].dtype.str,
            shape=tuple(int(value) for value in arrays[name].shape),
            byte_order=_byte_order(arrays[name].dtype),
            canonical_serialization=ARRAY_SERIALIZATION,
        )
        for name in _REQUIRED_ARRAYS
    )
    if expected_array_hashes is not None:
        observed_hashes = {item.name: item.sha256 for item in array_identities}
        if observed_hashes != dict(expected_array_hashes):
            raise ProtocolContractError(
                f"{spec.canonical_name} array identities differ from the independent audit"
            )

    labels = arrays["node_labels"]
    if labels.min(initial=0) < 0 or labels.max(initial=-1) >= spec.class_count:
        raise ProtocolContractError(f"{spec.canonical_name} labels are outside the class range")
    if np.unique(labels).size != spec.class_count:
        raise ProtocolContractError(f"{spec.canonical_name} does not contain every registered class")

    edges = arrays["edges"]
    if edges.min(initial=0) < 0 or edges.max(initial=-1) >= spec.node_count:
        raise ProtocolContractError(f"{spec.canonical_name} edges contain an invalid node index")
    self_loops = int(np.count_nonzero(edges[:, 0] == edges[:, 1]))
    canonical_undirected = np.sort(edges, axis=1)
    sorted_undirected = _sorted_edge_rows(canonical_undirected)
    duplicate_pairs = int(
        np.count_nonzero(np.all(sorted_undirected[1:] == sorted_undirected[:-1], axis=1))
    )
    if self_loops or duplicate_pairs:
        raise ProtocolContractError(
            f"{spec.canonical_name} is not a simple stored-once undirected graph"
        )
    expanded = np.concatenate((edges, edges[:, ::-1]), axis=0)
    sorted_expanded = _sorted_edge_rows(expanded)
    duplicate_directed = int(
        np.count_nonzero(np.all(sorted_expanded[1:] == sorted_expanded[:-1], axis=1))
    )
    if duplicate_directed or expanded.shape[0] != 2 * edges.shape[0]:
        raise ProtocolContractError(f"{spec.canonical_name} bidirection expansion is invalid")
    reversed_expanded = _sorted_edge_rows(expanded[:, ::-1])
    if not np.array_equal(sorted_expanded, reversed_expanded):
        raise ProtocolContractError(f"{spec.canonical_name} expanded edges lack reciprocals")
    components = _connected_component_count(spec.node_count, canonical_undirected)
    if components != 1:
        raise ProtocolContractError(f"{spec.canonical_name} graph is disconnected")

    raw_edge_hash = _edge_sha256(edges)
    expanded_edge_hash = hashlib.sha256(sorted_expanded.tobytes(order="C")).hexdigest()
    if expected_graph_hashes is not None and (
        raw_edge_hash,
        expanded_edge_hash,
    ) != expected_graph_hashes:
        raise ProtocolContractError(
            f"{spec.canonical_name} sorted graph identities differ from the independent audit"
        )

    split_identities: list[SplitIdentity] = []
    for split_id in OFFICIAL_SPLITS:
        train = arrays["train_masks"][split_id]
        validation = arrays["val_masks"][split_id]
        test = arrays["test_masks"][split_id]
        disjoint = not bool(
            np.any(train & validation) or np.any(train & test) or np.any(validation & test)
        )
        coverage = bool(np.all(train | validation | test))
        if not disjoint or not coverage:
            raise ProtocolContractError(
                f"{spec.canonical_name} split {split_id} is not a full disjoint partition"
            )
        expected_partition_sizes = (
            spec.node_count // 2,
            spec.node_count // 4,
            spec.node_count - spec.node_count // 2 - spec.node_count // 4,
        )
        observed_partition_sizes = tuple(
            int(np.count_nonzero(mask)) for mask in (train, validation, test)
        )
        if observed_partition_sizes != expected_partition_sizes:
            raise ProtocolContractError(
                f"{spec.canonical_name} split {split_id} does not preserve the supplied "
                "50/25/25 partition sizes"
            )

        def class_counts(mask: np.ndarray) -> tuple[int, ...]:
            counts = np.bincount(labels[mask], minlength=spec.class_count)
            return tuple(int(value) for value in counts)

        split_identities.append(
            SplitIdentity(
                split_id=split_id,
                train_index_sha256=_index_sha256(train),
                validation_index_sha256=_index_sha256(validation),
                test_index_sha256=_index_sha256(test),
                train_count=int(np.count_nonzero(train)),
                validation_count=int(np.count_nonzero(validation)),
                test_count=int(np.count_nonzero(test)),
                train_class_counts=class_counts(train),
                validation_class_counts=class_counts(validation),
                test_class_counts=class_counts(test),
                pairwise_disjoint=True,
                covers_all_nodes=True,
            )
        )

    graph = GraphIdentity(
        node_count=spec.node_count,
        stored_undirected_edges=spec.stored_undirected_edges,
        expanded_directed_edges=2 * spec.stored_undirected_edges,
        feature_count=spec.feature_count,
        class_count=spec.class_count,
        self_loop_count=self_loops,
        duplicate_directed_edge_count=duplicate_directed,
        connected_component_count=components,
        bidirection_expansion_count=1,
        raw_edge_sha256=raw_edge_hash,
        expanded_edge_sha256=expanded_edge_hash,
    )
    candidate = DatasetIdentityCandidate(
        dataset=spec.canonical_name,
        source_commit=OFFICIAL_SOURCE_COMMIT,
        npz_path=spec.npz_path,
        npz_size_bytes=spec.npz_size_bytes,
        npz_sha256=spec.npz_sha256,
        redistribution_terms_record=LOCAL_ACQUISITION_POLICY,
        arrays=array_identities,
        graph=graph,
        splits=tuple(split_identities),
    )
    if spec.canonical_name in DATASET_REGISTRY:
        validate_dataset_identity(candidate)
    return candidate


def _default_downloader(url: str, target: Path, expected_size: int) -> None:
    if not url.startswith(f"{RAW_BASE_URL}/data/"):
        raise ProtocolContractError("refusing a dataset URL outside the exact pinned raw source")
    request = urllib.request.Request(url, headers={"User-Agent": "GBDN-dataset-acquisition/1"})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - frozen HTTPS URL
        if response.geturl() != url:
            raise ProtocolContractError("dataset download redirected away from the pinned URL")
        declared = response.headers.get("Content-Length")
        if declared is not None and int(declared) != expected_size:
            raise ProtocolContractError("download Content-Length differs from the pinned size")
        written = 0
        with target.open("xb") as stream:
            while chunk := response.read(1024 * 1024):
                written += len(chunk)
                if written > expected_size:
                    raise ProtocolContractError("download exceeded the pinned size")
                stream.write(chunk)
            stream.flush()
            os.fsync(stream.fileno())
        if written != expected_size:
            raise ProtocolContractError("download size differs from the pinned size")


def _install_without_overwrite(
    *,
    url: str,
    destination: Path,
    spec: DatasetTaskSpec,
    downloader: Downloader,
) -> None:
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.part")
    try:
        downloader(url, temporary, spec.npz_size_bytes)
        verify_archive_bytes(temporary, spec)
        try:
            os.link(temporary, destination)
        except FileExistsError:
            verify_archive_bytes(destination, spec)
        else:
            verify_archive_bytes(destination, spec)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _verify_license_notice(repository_root: Path) -> None:
    notice = repository_root / LICENSE_RELATIVE_PATH
    metadata = _regular_file(notice, "upstream MIT notice")
    digest = hashlib.sha256(notice.read_bytes()).hexdigest()
    if (metadata.st_size, digest) != (LICENSE_SIZE_BYTES, LICENSE_SHA256):
        raise ProtocolContractError("the frozen upstream MIT notice has drifted")


def _array_to_mapping(identity: ArrayIdentity) -> dict[str, Any]:
    return {
        "byte_order": identity.byte_order,
        "canonical_serialization": identity.canonical_serialization,
        "dtype": identity.dtype,
        "name": identity.name,
        "sha256": identity.sha256,
        "shape": list(identity.shape),
    }


def _split_to_mapping(identity: SplitIdentity) -> dict[str, Any]:
    return {
        "covers_all_nodes": identity.covers_all_nodes,
        "index_serialization": SPLIT_INDEX_SERIALIZATION,
        "pairwise_disjoint": identity.pairwise_disjoint,
        "split_id": identity.split_id,
        "test_class_counts": list(identity.test_class_counts),
        "test_count": identity.test_count,
        "test_index_sha256": identity.test_index_sha256,
        "train_class_counts": list(identity.train_class_counts),
        "train_count": identity.train_count,
        "train_index_sha256": identity.train_index_sha256,
        "validation_class_counts": list(identity.validation_class_counts),
        "validation_count": identity.validation_count,
        "validation_index_sha256": identity.validation_index_sha256,
    }


def build_identity_manifest(candidates: Sequence[DatasetIdentityCandidate]) -> dict[str, Any]:
    """Build and semantically validate the compact machine-readable identity report."""

    ordered = tuple(candidates)
    if tuple(item.dataset for item in ordered) != tuple(DATASET_REGISTRY):
        raise ProtocolContractError("identity manifest requires all five datasets in registry order")
    datasets: list[dict[str, Any]] = []
    for candidate in ordered:
        spec = validate_dataset_identity(candidate)
        graph = candidate.graph
        datasets.append(
            {
                "arrays": [_array_to_mapping(item) for item in candidate.arrays],
                "canonical_name": spec.canonical_name,
                "git_blob_sha1": spec.git_blob_sha1,
                "graph": {
                    "bidirection_expansion_count": graph.bidirection_expansion_count,
                    "class_count": graph.class_count,
                    "connected_component_count": graph.connected_component_count,
                    "duplicate_directed_edge_count": graph.duplicate_directed_edge_count,
                    "expanded_directed_edges": graph.expanded_directed_edges,
                    "expanded_edge_serialization": EXPANDED_EDGE_SERIALIZATION,
                    "expanded_edge_sha256": graph.expanded_edge_sha256,
                    "feature_count": graph.feature_count,
                    "node_count": graph.node_count,
                    "raw_edge_serialization": RAW_EDGE_SERIALIZATION,
                    "raw_edge_sha256": graph.raw_edge_sha256,
                    "self_loop_count": graph.self_loop_count,
                    "stored_undirected_edges": graph.stored_undirected_edges,
                },
                "npz_path": spec.npz_path,
                "npz_serialization": FILE_SERIALIZATION,
                "npz_sha256": spec.npz_sha256,
                "npz_size_bytes": spec.npz_size_bytes,
                "raw_url": official_raw_url(spec),
                "splits": [_split_to_mapping(item) for item in candidate.splits],
            }
        )
    manifest = {
        "datasets": datasets,
        "license_record": {
            "dataset_redistribution_rights": "not_asserted",
            "notice_path": LICENSE_RELATIVE_PATH,
            "notice_sha256": LICENSE_SHA256,
            "notice_size_bytes": LICENSE_SIZE_BYTES,
            "repository_code_license": "MIT",
            "source_url": LICENSE_SOURCE_URL,
        },
        "policy": LOCAL_ACQUISITION_POLICY,
        "raw_archives_tracked": False,
        "schema_version": IDENTITY_SCHEMA,
        "source": {
            "commit": OFFICIAL_SOURCE_COMMIT,
            "raw_base_url": RAW_BASE_URL,
            "repository_url": OFFICIAL_SOURCE_URL,
        },
    }
    validate_identity_manifest(manifest)
    return manifest


def _expect_keys(value: Mapping[str, Any], expected: set[str], field: str) -> None:
    if set(value) != expected:
        raise ProtocolContractError(f"{field} keys differ from schema")


def _candidate_from_mapping(record: Mapping[str, Any]) -> DatasetIdentityCandidate:
    _expect_keys(
        record,
        {
            "arrays",
            "canonical_name",
            "git_blob_sha1",
            "graph",
            "npz_path",
            "npz_serialization",
            "npz_sha256",
            "npz_size_bytes",
            "raw_url",
            "splits",
        },
        "dataset",
    )
    name = record["canonical_name"]
    if type(name) is not str or name not in DATASET_REGISTRY:
        raise ProtocolContractError("manifest contains an unknown dataset")
    spec = DATASET_REGISTRY[name]
    if (
        record["git_blob_sha1"] != spec.git_blob_sha1
        or record["npz_serialization"] != FILE_SERIALIZATION
        or record["raw_url"] != official_raw_url(spec)
    ):
        raise ProtocolContractError(f"{name} source identity differs from the frozen registry")
    arrays_value = record["arrays"]
    if type(arrays_value) is not list:
        raise ProtocolContractError(f"{name}.arrays must be a JSON array")
    arrays: list[ArrayIdentity] = []
    for item in arrays_value:
        if type(item) is not dict:
            raise ProtocolContractError(f"{name}.arrays entries must be objects")
        _expect_keys(
            item,
            {"byte_order", "canonical_serialization", "dtype", "name", "sha256", "shape"},
            f"{name}.array",
        )
        if item["canonical_serialization"] != ARRAY_SERIALIZATION or type(item["shape"]) is not list:
            raise ProtocolContractError(f"{name} array serialization differs from the contract")
        arrays.append(
            ArrayIdentity(
                name=item["name"],
                sha256=item["sha256"],
                dtype=item["dtype"],
                shape=tuple(item["shape"]),
                byte_order=item["byte_order"],
                canonical_serialization=item["canonical_serialization"],
            )
        )
    observed_array_hashes = {item.name: item.sha256 for item in arrays}
    if observed_array_hashes != dict(_EXPECTED_ARRAY_HASHES[name]):
        raise ProtocolContractError(f"{name} array hashes differ from the independent audit")
    expected_array_metadata = {
        "node_features": ("<f4", (spec.node_count, spec.feature_count), "little"),
        "node_labels": ("<i8", (spec.node_count,), "little"),
        "edges": ("<i8", (spec.stored_undirected_edges, 2), "little"),
        "train_masks": ("|b1", (10, spec.node_count), "not-applicable"),
        "val_masks": ("|b1", (10, spec.node_count), "not-applicable"),
        "test_masks": ("|b1", (10, spec.node_count), "not-applicable"),
    }
    if tuple(item.name for item in arrays) != _REQUIRED_ARRAYS or any(
        (item.dtype, item.shape, item.byte_order) != expected_array_metadata[item.name]
        for item in arrays
    ):
        raise ProtocolContractError(f"{name} array order, dtype, shape, or byte order differs")

    graph_value = record["graph"]
    if type(graph_value) is not dict:
        raise ProtocolContractError(f"{name}.graph must be an object")
    graph_keys = {
        "bidirection_expansion_count",
        "class_count",
        "connected_component_count",
        "duplicate_directed_edge_count",
        "expanded_directed_edges",
        "expanded_edge_serialization",
        "expanded_edge_sha256",
        "feature_count",
        "node_count",
        "raw_edge_serialization",
        "raw_edge_sha256",
        "self_loop_count",
        "stored_undirected_edges",
    }
    _expect_keys(graph_value, graph_keys, f"{name}.graph")
    if (
        graph_value["raw_edge_serialization"] != RAW_EDGE_SERIALIZATION
        or graph_value["expanded_edge_serialization"] != EXPANDED_EDGE_SERIALIZATION
        or (graph_value["raw_edge_sha256"], graph_value["expanded_edge_sha256"])
        != _EXPECTED_GRAPH_HASHES[name]
    ):
        raise ProtocolContractError(f"{name} graph serialization or hashes differ from the audit")
    graph = GraphIdentity(
        **{
            key: graph_value[key]
            for key in graph_keys
            if key not in {"raw_edge_serialization", "expanded_edge_serialization"}
        }
    )

    splits_value = record["splits"]
    if type(splits_value) is not list:
        raise ProtocolContractError(f"{name}.splits must be a JSON array")
    split_keys = {
        "covers_all_nodes",
        "index_serialization",
        "pairwise_disjoint",
        "split_id",
        "test_class_counts",
        "test_count",
        "test_index_sha256",
        "train_class_counts",
        "train_count",
        "train_index_sha256",
        "validation_class_counts",
        "validation_count",
        "validation_index_sha256",
    }
    splits: list[SplitIdentity] = []
    for item in splits_value:
        if type(item) is not dict:
            raise ProtocolContractError(f"{name}.splits entries must be objects")
        _expect_keys(item, split_keys, f"{name}.split")
        if item["index_serialization"] != SPLIT_INDEX_SERIALIZATION:
            raise ProtocolContractError(f"{name} split index serialization differs from contract")
        for counts in ("train_class_counts", "validation_class_counts", "test_class_counts"):
            if type(item[counts]) is not list:
                raise ProtocolContractError(f"{name}.{counts} must be a JSON array")
        splits.append(
            SplitIdentity(
                **{
                    key: tuple(item[key]) if key.endswith("_class_counts") else item[key]
                    for key in split_keys
                    if key != "index_serialization"
                }
            )
        )
    return DatasetIdentityCandidate(
        dataset=name,
        source_commit=OFFICIAL_SOURCE_COMMIT,
        npz_path=record["npz_path"],
        npz_size_bytes=record["npz_size_bytes"],
        npz_sha256=record["npz_sha256"],
        redistribution_terms_record=LOCAL_ACQUISITION_POLICY,
        arrays=tuple(arrays),
        graph=graph,
        splits=tuple(splits),
    )


def validate_identity_manifest(manifest: Mapping[str, Any]) -> tuple[DatasetIdentityCandidate, ...]:
    """Strictly validate schema, pinned identities, invariants, and license scope."""

    if type(manifest) is not dict:
        raise ProtocolContractError("identity manifest must be a JSON object")
    _expect_keys(
        manifest,
        {"datasets", "license_record", "policy", "raw_archives_tracked", "schema_version", "source"},
        "manifest",
    )
    if (
        manifest["schema_version"] != IDENTITY_SCHEMA
        or manifest["policy"] != LOCAL_ACQUISITION_POLICY
        or manifest["raw_archives_tracked"] is not False
    ):
        raise ProtocolContractError("manifest schema or local-only policy differs from the contract")
    source = manifest["source"]
    if type(source) is not dict:
        raise ProtocolContractError("manifest.source must be an object")
    _expect_keys(source, {"commit", "raw_base_url", "repository_url"}, "source")
    if source != {
        "commit": OFFICIAL_SOURCE_COMMIT,
        "raw_base_url": RAW_BASE_URL,
        "repository_url": OFFICIAL_SOURCE_URL,
    }:
        raise ProtocolContractError("manifest source differs from the pinned upstream commit")
    license_record = manifest["license_record"]
    if type(license_record) is not dict:
        raise ProtocolContractError("manifest.license_record must be an object")
    expected_license = {
        "dataset_redistribution_rights": "not_asserted",
        "notice_path": LICENSE_RELATIVE_PATH,
        "notice_sha256": LICENSE_SHA256,
        "notice_size_bytes": LICENSE_SIZE_BYTES,
        "repository_code_license": "MIT",
        "source_url": LICENSE_SOURCE_URL,
    }
    if license_record != expected_license:
        raise ProtocolContractError("manifest license record overstates or differs from reviewed scope")
    records = manifest["datasets"]
    if type(records) is not list:
        raise ProtocolContractError("manifest.datasets must be a JSON array")
    candidates = tuple(_candidate_from_mapping(record) for record in records)
    if tuple(item.dataset for item in candidates) != tuple(DATASET_REGISTRY):
        raise ProtocolContractError("manifest must contain all five datasets in registry order")
    for candidate in candidates:
        validate_dataset_identity(candidate)
    return candidates


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_identity_manifest(path: Path) -> dict[str, Any]:
    _regular_file(path, "dataset identity manifest")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ProtocolContractError(f"non-finite JSON constant: {token}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ProtocolContractError("dataset identity manifest is not strict UTF-8 JSON") from error
    validate_identity_manifest(value)
    return value


def _manifest_bytes(manifest: Mapping[str, Any]) -> bytes:
    validate_identity_manifest(manifest)
    return (
        json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def write_identity_manifest(
    repository_root: Path,
    manifest: Mapping[str, Any],
    *,
    destination: Path | None = None,
) -> Path:
    """Atomically create the canonical report, refusing overwrite drift."""

    root = repository_root.resolve(strict=True)
    canonical = root / MANIFEST_RELATIVE_PATH
    requested = canonical if destination is None else destination.absolute()
    if requested != canonical or canonical.resolve(strict=False) != canonical:
        raise ProtocolContractError("identity manifest must be written under results_submission/reports")
    target = canonical
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.parent.is_symlink():
        raise ProtocolContractError("identity report directory must not be a symlink")
    content = _manifest_bytes(manifest)
    if target.exists():
        _regular_file(target, "dataset identity manifest")
        if target.read_bytes() != content:
            raise ProtocolContractError("refusing to overwrite a different identity manifest")
        return target
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.part")
    try:
        with temporary.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, target)
        except FileExistsError:
            if target.read_bytes() != content:
                raise ProtocolContractError("identity manifest changed during atomic creation")
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return target


def acquire_official_datasets(
    repository_root: Path,
    *,
    offline: bool = False,
    downloader: Downloader | None = None,
    write_manifest: bool = True,
) -> dict[str, Any]:
    """Acquire missing official archives or verify an existing local cache."""

    root = repository_root.resolve(strict=True)
    _verify_license_notice(root)
    data_directory = root / "data"
    if data_directory.exists() and data_directory.is_symlink():
        raise ProtocolContractError("data directory must not be a symlink")
    if offline:
        if not data_directory.is_dir():
            raise ProtocolContractError("offline verification requires a preexisting data directory")
    else:
        data_directory.mkdir(exist_ok=True)
    fetch = _default_downloader if downloader is None else downloader
    candidates: list[DatasetIdentityCandidate] = []
    for spec in DATASET_REGISTRY.values():
        destination = root / spec.npz_path
        if destination.exists() or destination.is_symlink():
            verify_archive_bytes(destination, spec)
        else:
            if offline:
                raise ProtocolContractError(
                    f"offline verification requires the preexisting archive {spec.npz_path}"
                )
            _install_without_overwrite(
                url=official_raw_url(spec),
                destination=destination,
                spec=spec,
                downloader=fetch,
            )
        candidates.append(
            inspect_verified_archive(
                destination,
                spec,
                expected_array_hashes=_EXPECTED_ARRAY_HASHES[spec.canonical_name],
                expected_graph_hashes=_EXPECTED_GRAPH_HASHES[spec.canonical_name],
            )
        )
    manifest = build_identity_manifest(candidates)
    if write_manifest:
        write_identity_manifest(root, manifest)
    return manifest


def verify_manifest_against_local_data(repository_root: Path, manifest_path: Path) -> None:
    """Require an existing manifest to equal a fresh offline verification exactly."""

    expected = load_identity_manifest(manifest_path)
    observed = acquire_official_datasets(repository_root, offline=True, write_manifest=False)
    if expected != observed:
        raise ProtocolContractError("identity manifest differs from freshly verified local data")


__all__ = [
    "ARRAY_SERIALIZATION",
    "EXPANDED_EDGE_SERIALIZATION",
    "FILE_SERIALIZATION",
    "IDENTITY_SCHEMA",
    "LICENSE_RELATIVE_PATH",
    "LOCAL_ACQUISITION_POLICY",
    "MANIFEST_RELATIVE_PATH",
    "RAW_BASE_URL",
    "RAW_EDGE_SERIALIZATION",
    "SPLIT_INDEX_SERIALIZATION",
    "acquire_official_datasets",
    "build_identity_manifest",
    "inspect_verified_archive",
    "load_identity_manifest",
    "official_raw_url",
    "validate_identity_manifest",
    "verify_archive_bytes",
    "verify_manifest_against_local_data",
    "write_identity_manifest",
]
