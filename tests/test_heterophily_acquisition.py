"""Network-free tests for pinned official-dataset acquisition and identity."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from gbdn.heterophily_acquisition import (
    ARRAY_SERIALIZATION,
    EXPANDED_EDGE_SERIALIZATION,
    IDENTITY_SCHEMA,
    LICENSE_RELATIVE_PATH,
    LICENSE_SHA256,
    LOCAL_ACQUISITION_POLICY,
    MANIFEST_RELATIVE_PATH,
    RAW_BASE_URL,
    RAW_EDGE_SERIALIZATION,
    SPLIT_INDEX_SERIALIZATION,
    _EXPECTED_ARRAY_HASHES,
    _EXPECTED_GRAPH_HASHES,
    _install_without_overwrite,
    acquire_official_datasets,
    build_identity_manifest,
    inspect_verified_archive,
    load_identity_manifest,
    official_raw_url,
    validate_identity_manifest,
    verify_archive_bytes,
    write_identity_manifest,
)
from gbdn.heterophily_contract import (
    ArrayIdentity,
    DATASET_REGISTRY,
    DatasetIdentityCandidate,
    DatasetTaskSpec,
    GraphIdentity,
    OFFICIAL_SOURCE_COMMIT,
    OFFICIAL_SPLITS,
    ProtocolContractError,
    SplitIdentity,
)


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _archive_spec(path: Path, *, nodes: int = 20, edges: int = 20) -> DatasetTaskSpec:
    payload = path.read_bytes()
    git_blob = hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()
    return DatasetTaskSpec(
        canonical_name="Synthetic-fixture",
        aliases=("synthetic_fixture",),
        npz_path="data/synthetic_fixture.npz",
        node_count=nodes,
        stored_undirected_edges=edges,
        feature_count=3,
        class_count=2,
        task_type="binary",
        output_logits=1,
        loss_id="binary_cross_entropy_with_logits",
        selection_metric="binary_roc_auc",
        test_metric="binary_roc_auc",
        npz_size_bytes=len(payload),
        git_blob_sha1=git_blob,
        npz_sha256=hashlib.sha256(payload).hexdigest(),
    )


def _synthetic_arrays(*, nodes: int = 20) -> dict[str, np.ndarray]:
    features = np.arange(nodes * 3, dtype="<f4").reshape(nodes, 3)
    labels = (np.arange(nodes) % 2).astype("<i8")
    edges = np.asarray([(node, (node + 1) % nodes) for node in range(nodes)], dtype="<i8")
    train = np.zeros((10, nodes), dtype=bool)
    validation = np.zeros((10, nodes), dtype=bool)
    test = np.zeros((10, nodes), dtype=bool)
    for split in OFFICIAL_SPLITS:
        order = (np.arange(nodes) + split) % nodes
        train[split, order[: nodes // 2]] = True
        validation[split, order[nodes // 2 : nodes // 2 + nodes // 4]] = True
        test[split, order[nodes // 2 + nodes // 4 :]] = True
    return {
        "node_features": features,
        "node_labels": labels,
        "edges": edges,
        "train_masks": train,
        "val_masks": validation,
        "test_masks": test,
    }


def _write_npz(path: Path, arrays: dict[str, np.ndarray]) -> DatasetTaskSpec:
    np.savez_compressed(path, **arrays)
    return _archive_spec(path, nodes=arrays["node_features"].shape[0], edges=arrays["edges"].shape[0])


def _balanced(total: int, classes: int) -> tuple[int, ...]:
    quotient, remainder = divmod(total, classes)
    return tuple(quotient + int(index < remainder) for index in range(classes))


def _official_candidate(name: str) -> DatasetIdentityCandidate:
    spec = DATASET_REGISTRY[name]
    dtypes = {
        "node_features": ("<f4", (spec.node_count, spec.feature_count), "little"),
        "node_labels": ("<i8", (spec.node_count,), "little"),
        "edges": ("<i8", (spec.stored_undirected_edges, 2), "little"),
        "train_masks": ("|b1", (10, spec.node_count), "not-applicable"),
        "val_masks": ("|b1", (10, spec.node_count), "not-applicable"),
        "test_masks": ("|b1", (10, spec.node_count), "not-applicable"),
    }
    arrays = tuple(
        ArrayIdentity(
            array_name,
            _EXPECTED_ARRAY_HASHES[name][array_name],
            dtype,
            shape,
            byte_order,
            ARRAY_SERIALIZATION,
        )
        for array_name, (dtype, shape, byte_order) in dtypes.items()
    )
    train_count = spec.node_count // 2
    validation_count = spec.node_count // 4
    test_count = spec.node_count - train_count - validation_count
    splits = tuple(
        SplitIdentity(
            split_id,
            _sha(f"{name}-train-{split_id}"),
            _sha(f"{name}-validation-{split_id}"),
            _sha(f"{name}-test-{split_id}"),
            train_count,
            validation_count,
            test_count,
            _balanced(train_count, spec.class_count),
            _balanced(validation_count, spec.class_count),
            _balanced(test_count, spec.class_count),
            True,
            True,
        )
        for split_id in OFFICIAL_SPLITS
    )
    graph_hashes = _EXPECTED_GRAPH_HASHES[name]
    return DatasetIdentityCandidate(
        dataset=name,
        source_commit=OFFICIAL_SOURCE_COMMIT,
        npz_path=spec.npz_path,
        npz_size_bytes=spec.npz_size_bytes,
        npz_sha256=spec.npz_sha256,
        redistribution_terms_record=LOCAL_ACQUISITION_POLICY,
        arrays=arrays,
        graph=GraphIdentity(
            node_count=spec.node_count,
            stored_undirected_edges=spec.stored_undirected_edges,
            expanded_directed_edges=2 * spec.stored_undirected_edges,
            feature_count=spec.feature_count,
            class_count=spec.class_count,
            self_loop_count=0,
            duplicate_directed_edge_count=0,
            connected_component_count=1,
            bidirection_expansion_count=1,
            raw_edge_sha256=graph_hashes[0],
            expanded_edge_sha256=graph_hashes[1],
        ),
        splits=splits,
    )


def test_inspector_checks_exact_arrays_graph_and_splits_without_network(tmp_path: Path):
    archive = tmp_path / "fixture.npz"
    spec = _write_npz(archive, _synthetic_arrays())
    candidate = inspect_verified_archive(archive, spec)
    assert [identity.name for identity in candidate.arrays] == [
        "node_features",
        "node_labels",
        "edges",
        "train_masks",
        "val_masks",
        "test_masks",
    ]
    assert all(identity.canonical_serialization == ARRAY_SERIALIZATION for identity in candidate.arrays)
    assert candidate.graph.connected_component_count == 1
    assert candidate.graph.expanded_directed_edges == 40
    assert all(split.pairwise_disjoint and split.covers_all_nodes for split in candidate.splits)
    assert len({split.train_index_sha256 for split in candidate.splits}) == 10


def test_whole_file_identity_is_checked_before_numpy_parsing(tmp_path: Path, monkeypatch):
    archive = tmp_path / "fixture.npz"
    spec = _write_npz(archive, _synthetic_arrays())
    archive.write_bytes(archive.read_bytes() + b"drift")
    called = False

    def forbidden_load(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("np.load must not be reached")

    monkeypatch.setattr(np, "load", forbidden_load)
    with pytest.raises(ProtocolContractError, match="archive identity mismatch"):
        inspect_verified_archive(archive, spec)
    assert called is False


@pytest.mark.parametrize("defect", ("dtype", "extra_key", "object", "self_loop", "duplicate", "disconnected", "mask_gap"))
def test_inspector_rejects_unsafe_or_nonofficial_structure(tmp_path: Path, defect: str):
    arrays = _synthetic_arrays()
    if defect == "dtype":
        arrays["node_features"] = arrays["node_features"].astype("<f8")
    elif defect == "extra_key":
        arrays["unexpected"] = np.asarray([1], dtype="<i8")
    elif defect == "object":
        arrays["node_features"] = arrays["node_features"].astype(object)
    elif defect == "self_loop":
        arrays["edges"][0] = (0, 0)
    elif defect == "duplicate":
        arrays["edges"][1] = arrays["edges"][0, ::-1]
    elif defect == "disconnected":
        arrays["edges"] = np.asarray(
            [(node, (node + 1) % 10) for node in range(10)]
            + [(node, 10 + (node - 9) % 10) for node in range(10, 20)],
            dtype="<i8",
        )
    else:
        arrays["test_masks"][0, np.flatnonzero(arrays["test_masks"][0])[0]] = False
    archive = tmp_path / f"{defect}.npz"
    spec = _write_npz(archive, arrays)
    with pytest.raises(ProtocolContractError):
        inspect_verified_archive(archive, spec)


def test_atomic_injected_download_uses_exact_url_and_never_overwrites_drift(tmp_path: Path):
    source = tmp_path / "source.npz"
    spec = _write_npz(source, _synthetic_arrays())
    payload = source.read_bytes()
    destination = tmp_path / "data" / "synthetic_fixture.npz"
    destination.parent.mkdir()
    observed: list[str] = []

    def downloader(url: str, target: Path, expected_size: int) -> None:
        observed.append(url)
        assert expected_size == len(payload)
        target.write_bytes(payload)

    exact_url = f"{RAW_BASE_URL}/data/synthetic_fixture.npz"
    _install_without_overwrite(
        url=exact_url,
        destination=destination,
        spec=spec,
        downloader=downloader,
    )
    verify_archive_bytes(destination, spec)
    assert observed == [exact_url]

    destination.write_bytes(b"local-drift")
    with pytest.raises(ProtocolContractError, match="archive identity mismatch"):
        _install_without_overwrite(
            url=exact_url,
            destination=destination,
            spec=spec,
            downloader=downloader,
        )
    assert destination.read_bytes() == b"local-drift"


def test_official_urls_are_exact_commit_bound_raw_github_urls():
    for spec in DATASET_REGISTRY.values():
        assert official_raw_url(spec) == f"{RAW_BASE_URL}/{spec.npz_path}"
        assert official_raw_url(spec).startswith("https://raw.githubusercontent.com/")
        assert OFFICIAL_SOURCE_COMMIT in official_raw_url(spec)
    with pytest.raises(ProtocolContractError, match="frozen registry"):
        official_raw_url(replace(next(iter(DATASET_REGISTRY.values())), npz_size_bytes=1))


def test_offline_mode_never_invokes_downloader(tmp_path: Path):
    source_notice = Path(__file__).resolve().parents[1] / LICENSE_RELATIVE_PATH
    notice = tmp_path / LICENSE_RELATIVE_PATH
    notice.parent.mkdir(parents=True)
    notice.write_bytes(source_notice.read_bytes())
    called = False

    def forbidden_downloader(url: str, target: Path, expected_size: int) -> None:
        nonlocal called
        called = True

    with pytest.raises(ProtocolContractError, match="offline verification requires"):
        acquire_official_datasets(
            tmp_path,
            offline=True,
            downloader=forbidden_downloader,
            write_manifest=False,
        )
    assert called is False
    assert not (tmp_path / "data").exists()


def test_manifest_is_strict_pinned_local_only_and_atomic(tmp_path: Path):
    candidates = tuple(_official_candidate(name) for name in DATASET_REGISTRY)
    manifest = build_identity_manifest(candidates)
    assert manifest["schema_version"] == IDENTITY_SCHEMA
    assert manifest["raw_archives_tracked"] is False
    assert manifest["license_record"]["dataset_redistribution_rights"] == "not_asserted"
    assert all(
        record["graph"]["raw_edge_serialization"] == RAW_EDGE_SERIALIZATION
        and record["graph"]["expanded_edge_serialization"] == EXPANDED_EDGE_SERIALIZATION
        and all(split["index_serialization"] == SPLIT_INDEX_SERIALIZATION for split in record["splits"])
        for record in manifest["datasets"]
    )
    root = tmp_path.resolve()
    target = write_identity_manifest(root, manifest)
    assert target == root / MANIFEST_RELATIVE_PATH
    assert load_identity_manifest(target) == manifest
    assert write_identity_manifest(root, manifest) == target

    changed = json.loads(json.dumps(manifest))
    changed["license_record"]["dataset_redistribution_rights"] = "redistribution-permitted"
    with pytest.raises(ProtocolContractError, match="license record"):
        validate_identity_manifest(changed)
    changed = json.loads(json.dumps(manifest))
    changed["datasets"][0]["arrays"][0]["dtype"] = "<f8"
    with pytest.raises(ProtocolContractError, match="dtype"):
        validate_identity_manifest(changed)
    target.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ProtocolContractError, match="overwrite"):
        write_identity_manifest(root, manifest)


def test_manifest_loader_rejects_duplicate_keys_and_nonfinite_json(tmp_path: Path):
    path = tmp_path / "identity.json"
    path.write_text('{"schema_version":"x","schema_version":"y"}', encoding="utf-8")
    with pytest.raises(ProtocolContractError, match="duplicate JSON key"):
        load_identity_manifest(path)
    path.write_text('{"schema_version":NaN}', encoding="utf-8")
    with pytest.raises(ProtocolContractError, match="non-finite"):
        load_identity_manifest(path)


def test_frozen_upstream_notice_matches_pinned_license_record():
    root = Path(__file__).resolve().parents[1]
    notice = root / LICENSE_RELATIVE_PATH
    assert hashlib.sha256(notice.read_bytes()).hexdigest() == LICENSE_SHA256
    assert b"MIT License" in notice.read_bytes()
    assert b"Yandex Research" in notice.read_bytes()


def test_raw_data_stays_ignored():
    root = Path(__file__).resolve().parents[1]
    assert "data/" in (root / ".gitignore").read_text(encoding="utf-8").splitlines()
