"""CPU-only tests for the official Platonov-five protocol contract."""

from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from gbdn.heterophily_contract import (
    ArrayIdentity,
    DATASET_REGISTRY,
    DatasetIdentityCandidate,
    GraphIdentity,
    OFFICIAL_SOURCE_COMMIT,
    OFFICIAL_SPLITS,
    ProtocolContractError,
    SplitIdentity,
    TRAINING_SEEDS,
    TrainingSelectionView,
    UNRESOLVED,
    frozen_plan_jobs,
    resolve_dataset,
    validate_dataset_identity,
    validate_task_dispatch,
)


H = "a" * 64


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _balanced_counts(total: int, classes: int) -> tuple[int, ...]:
    base, remainder = divmod(total, classes)
    return tuple(base + (index < remainder) for index in range(classes))


def _candidate(name: str = "Minesweeper") -> DatasetIdentityCandidate:
    spec = resolve_dataset(name)
    arrays = (
        ArrayIdentity("node_features", _hash("node_features"), "float32", (spec.node_count, spec.feature_count), "little", "contiguous-c-order-v1"),
        ArrayIdentity("node_labels", _hash("node_labels"), "int64", (spec.node_count,), "little", "contiguous-c-order-v1"),
        ArrayIdentity("edges", _hash("edges"), "int64", (spec.stored_undirected_edges, 2), "little", "stable-lexicographic-edge-rows-v1"),
        ArrayIdentity("train_masks", _hash("train_masks"), "bool", (10, spec.node_count), "not-applicable", "packed-row-major-bool-v1"),
        ArrayIdentity("val_masks", _hash("val_masks"), "bool", (10, spec.node_count), "not-applicable", "packed-row-major-bool-v1"),
        ArrayIdentity("test_masks", _hash("test_masks"), "bool", (10, spec.node_count), "not-applicable", "packed-row-major-bool-v1"),
    )
    graph = GraphIdentity(
        node_count=spec.node_count,
        stored_undirected_edges=spec.stored_undirected_edges,
        expanded_directed_edges=2 * spec.stored_undirected_edges,
        feature_count=spec.feature_count,
        class_count=spec.class_count,
        self_loop_count=0,
        duplicate_directed_edge_count=0,
        connected_component_count=1,
        bidirection_expansion_count=1,
        raw_edge_sha256=_hash("raw_edges"),
        expanded_edge_sha256=_hash("expanded_edges"),
    )
    train = spec.node_count // 2
    validation = spec.node_count // 4
    test = spec.node_count - train - validation
    splits = tuple(
        SplitIdentity(
            i,
            _hash(f"train-{i}"),
            _hash(f"validation-{i}"),
            _hash(f"test-{i}"),
            train,
            validation,
            test,
            _balanced_counts(train, spec.class_count),
            _balanced_counts(validation, spec.class_count),
            _balanced_counts(test, spec.class_count),
            True,
            True,
        )
        for i in OFFICIAL_SPLITS
    )
    return DatasetIdentityCandidate(
        dataset=spec.canonical_name,
        source_commit=OFFICIAL_SOURCE_COMMIT,
        npz_path=spec.npz_path,
        npz_size_bytes=spec.npz_size_bytes,
        npz_sha256=spec.npz_sha256,
        redistribution_terms_record="reviewed-local-acquisition-only-v1",
        arrays=arrays,
        graph=graph,
        splits=splits,
    )


def test_registry_freezes_exact_five_dataset_task_dispatches():
    assert tuple(DATASET_REGISTRY) == (
        "Roman-empire",
        "Amazon-ratings",
        "Minesweeper",
        "Tolokers",
        "Questions",
    )
    assert OFFICIAL_SPLITS == tuple(range(10))
    assert TRAINING_SEEDS == (0, 1, 2)
    for name in ("Roman-empire", "Amazon-ratings"):
        spec = resolve_dataset(name)
        assert (spec.task_type, spec.loss_id, spec.selection_metric) == (
            "multiclass",
            "cross_entropy",
            "accuracy",
        )
        assert spec.output_logits == spec.class_count
    for name in ("Minesweeper", "Tolokers", "Questions"):
        spec = resolve_dataset(name)
        assert (spec.task_type, spec.output_logits, spec.loss_id, spec.selection_metric) == (
            "binary",
            1,
            "binary_cross_entropy_with_logits",
            "binary_roc_auc",
        )
    assert resolve_dataset("roman_empire").canonical_name == "Roman-empire"
    with pytest.raises(ProtocolContractError, match="outside"):
        resolve_dataset("roman empire maybe")


def test_registry_pins_byte_identity_but_terms_remain_explicit_hard_blockers():
    for spec in DATASET_REGISTRY.values():
        assert len(spec.npz_sha256) == 64
        assert len(spec.git_blob_sha1) == 40
        assert spec.npz_size_bytes > 0
        assert spec.redistribution_terms == UNRESOLVED
        assert spec.ready_for_acquisition is False
        assert spec.blockers == ("dataset-specific redistribution terms are unresolved",)


@pytest.mark.parametrize("dataset", ("Minesweeper", "Tolokers", "Questions"))
def test_binary_tasks_reject_universal_cross_entropy_and_macro_auroc(dataset):
    with pytest.raises(ProtocolContractError, match="task dispatch mismatch"):
        validate_task_dispatch(
            dataset,
            output_logits=2,
            loss_id="cross_entropy",
            selection_metric="macro_roc_auc",
            test_metric="macro_roc_auc",
        )
    spec = resolve_dataset(dataset)
    assert validate_task_dispatch(
        dataset,
        output_logits=1,
        loss_id="binary_cross_entropy_with_logits",
        selection_metric="binary_roc_auc",
        test_metric="binary_roc_auc",
    ) is spec


@pytest.mark.parametrize("dataset", ("Roman-empire", "Amazon-ratings"))
def test_multiclass_tasks_select_and_test_on_accuracy(dataset):
    spec = resolve_dataset(dataset)
    with pytest.raises(ProtocolContractError, match="task dispatch mismatch"):
        validate_task_dispatch(
            dataset,
            output_logits=spec.class_count,
            loss_id="cross_entropy",
            selection_metric="macro_roc_auc",
            test_metric="macro_roc_auc",
        )


def test_valid_supplied_metadata_passes_without_loading_a_dataset():
    candidate = _candidate()
    assert validate_dataset_identity(candidate).canonical_name == "Minesweeper"


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("self_loop_count", 1),
        ("duplicate_directed_edge_count", 1),
        ("connected_component_count", 2),
        ("bidirection_expansion_count", 2),
        ("expanded_directed_edges", 39402),
    ),
)
def test_graph_identity_rejects_loops_duplicates_disconnection_and_bad_expansion(field, value):
    candidate = _candidate()
    graph = replace(candidate.graph, **{field: value})
    with pytest.raises(ProtocolContractError, match="graph invariants"):
        validate_dataset_identity(replace(candidate, graph=graph))


def test_identity_rejects_missing_hashes_wrong_array_shape_and_unresolved_terms():
    candidate = _candidate()
    with pytest.raises(ProtocolContractError, match="lowercase hex"):
        validate_dataset_identity(replace(candidate, npz_sha256=UNRESOLVED))
    with pytest.raises(ProtocolContractError, match="byte identity"):
        validate_dataset_identity(replace(candidate, npz_sha256="f" * 64))
    with pytest.raises(ProtocolContractError, match="byte identity"):
        validate_dataset_identity(
            replace(candidate, npz_size_bytes=candidate.npz_size_bytes + 1)
        )
    with pytest.raises(ProtocolContractError, match="redistribution"):
        validate_dataset_identity(replace(candidate, redistribution_terms_record=UNRESOLVED))
    changed = tuple(
        replace(array, shape=(9, resolve_dataset(candidate.dataset).node_count))
        if array.name == "train_masks"
        else array
        for array in candidate.arrays
    )
    with pytest.raises(ProtocolContractError, match="ten supplied"):
        validate_dataset_identity(replace(candidate, arrays=changed))


def test_identity_rejects_generated_missing_reordered_or_invalid_splits():
    candidate = _candidate()
    with pytest.raises(ProtocolContractError, match="exactly ten"):
        validate_dataset_identity(replace(candidate, splits=candidate.splits[:-1]))
    reordered = (candidate.splits[1], candidate.splits[0], *candidate.splits[2:])
    with pytest.raises(ProtocolContractError, match="ordered official"):
        validate_dataset_identity(replace(candidate, splits=reordered))
    bad = (replace(candidate.splits[0], pairwise_disjoint=False), *candidate.splits[1:])
    with pytest.raises(ProtocolContractError, match="partition"):
        validate_dataset_identity(replace(candidate, splits=bad))
    aliased = (
        replace(
            candidate.splits[0],
            validation_index_sha256=candidate.splits[0].train_index_sha256,
        ),
        *candidate.splits[1:],
    )
    with pytest.raises(ProtocolContractError, match="distinct"):
        validate_dataset_identity(replace(candidate, splits=aliased))
    bad_classes = (
        replace(candidate.splits[0], train_class_counts=(candidate.splits[0].train_count,)),
        *candidate.splits[1:],
    )
    with pytest.raises(ProtocolContractError, match="class/count"):
        validate_dataset_identity(replace(candidate, splits=bad_classes))


def test_training_selection_view_structurally_rejects_test_information():
    payload = {
        "dataset": "Questions",
        "split_id": 0,
        "train_index_sha256": H,
        "validation_index_sha256": H,
        "selection_metric": "binary_roc_auc",
    }
    view = TrainingSelectionView.from_mapping(payload)
    assert not hasattr(view, "test_index_sha256")
    assert not hasattr(view, "test_metric")
    for leaked in ("test_index_sha256", "test_labels", "test_metric"):
        with pytest.raises(ProtocolContractError, match="keys mismatch"):
            TrainingSelectionView.from_mapping({**payload, leaked: H})
    with pytest.raises(ProtocolContractError, match="wrong validation metric"):
        TrainingSelectionView.from_mapping({**payload, "selection_metric": "accuracy"})


def test_frozen_plan_is_complete_product_and_rejects_reduced_scope():
    jobs = frozen_plan_jobs(("GBDN", "CayleyNet"))
    assert len(jobs) == 5 * 2 * 10 * 3
    assert len(set(jobs)) == len(jobs)
    with pytest.raises(ProtocolContractError, match="all official"):
        frozen_plan_jobs(("GBDN",), splits=(0,))
    with pytest.raises(ProtocolContractError, match="frozen seeds"):
        frozen_plan_jobs(("GBDN",), seeds=(25,))
    with pytest.raises(ProtocolContractError, match="unique"):
        frozen_plan_jobs(("GBDN", "GBDN"))
