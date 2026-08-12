from __future__ import annotations

import io
import zipfile

import numpy as np
import pytest

from gbdn.artifacts import ArtifactValidationError
from gbdn.heterophily_evaluator import PREDICTION_FORMAT, evaluate_prediction_archive


def _archive(path, *, dataset="Roman-empire", split=0, run_id="a" * 64, indices=None, logits=None):
    indices = np.asarray([4, 9, 12], dtype=np.int64) if indices is None else indices
    if logits is None:
        logits = np.zeros((3, 18), dtype=np.float32)
        logits[0, 1] = 3
        logits[1, 0] = 2
        logits[2, 2] = 4
    np.savez_compressed(
        path,
        dataset=np.asarray(dataset),
        format=np.asarray(PREDICTION_FORMAT),
        indices=indices,
        logits=logits,
        run_id=np.asarray(run_id),
        split_id=np.asarray(split, dtype=np.int64),
    )


def test_multiclass_accuracy_is_recomputed_from_authoritative_labels(tmp_path):
    path = tmp_path / "predictions.npz"
    _archive(path)
    result = evaluate_prediction_archive(
        path,
        expected_run_id="a" * 64,
        expected_dataset="Roman-empire",
        expected_split=0,
        expected_test_indices=np.asarray([4, 9, 12], dtype=np.int64),
        authoritative_test_labels=np.asarray([1, 1, 2], dtype=np.int64),
    )
    assert result.metric_name == "accuracy"
    assert result.value == pytest.approx(2 / 3)
    assert result.example_count == 3


def test_binary_auc_is_tie_aware_and_uses_scalar_logits(tmp_path):
    path = tmp_path / "predictions.npz"
    indices = np.asarray([2, 7, 8, 10], dtype=np.int64)
    _archive(
        path,
        dataset="Questions",
        indices=indices,
        logits=np.asarray([0.9, 0.5, 0.5, 0.1], dtype=np.float64),
    )
    result = evaluate_prediction_archive(
        path,
        expected_run_id="a" * 64,
        expected_dataset="Questions",
        expected_split=0,
        expected_test_indices=indices,
        authoritative_test_labels=np.asarray([1, 1, 0, 0], dtype=np.int64),
    )
    assert result.metric_name == "binary_roc_auc"
    assert result.value == pytest.approx(0.875)


@pytest.mark.parametrize(
    ("change", "match"),
    (
        ({"expected_run_id": "b" * 64}, "identity"),
        ({"expected_split": 1}, "identity"),
        ({"expected_dataset": "Amazon-ratings"}, "identity"),
        ({"expected_test_indices": np.asarray([9, 4, 12], dtype=np.int64)}, "indices"),
    ),
)
def test_identity_split_dataset_and_order_mismatch_fail_closed(tmp_path, change, match):
    path = tmp_path / "predictions.npz"
    _archive(path)
    arguments = {
        "expected_run_id": "a" * 64,
        "expected_dataset": "Roman-empire",
        "expected_split": 0,
        "expected_test_indices": np.asarray([4, 9, 12], dtype=np.int64),
        "authoritative_test_labels": np.asarray([1, 1, 2], dtype=np.int64),
    }
    arguments.update(change)
    with pytest.raises(ArtifactValidationError, match=match):
        evaluate_prediction_archive(path, **arguments)


def test_wrong_head_shape_nonfinite_logits_and_bad_authority_fail_closed(tmp_path):
    path = tmp_path / "predictions.npz"
    _archive(path, logits=np.zeros((3, 2), dtype=np.float32))
    kwargs = dict(
        expected_run_id="a" * 64,
        expected_dataset="Roman-empire",
        expected_split=0,
        expected_test_indices=np.asarray([4, 9, 12], dtype=np.int64),
        authoritative_test_labels=np.asarray([1, 1, 2], dtype=np.int64),
    )
    with pytest.raises(ArtifactValidationError, match="shape"):
        evaluate_prediction_archive(path, **kwargs)
    _archive(path, logits=np.full((3, 18), np.nan, dtype=np.float32))
    with pytest.raises(ArtifactValidationError, match="finite"):
        evaluate_prediction_archive(path, **kwargs)
    kwargs["expected_test_indices"] = np.asarray([4, 4, 12], dtype=np.int64)
    with pytest.raises(ArtifactValidationError, match="unique"):
        evaluate_prediction_archive(path, **kwargs)


def test_extra_archive_member_and_object_payload_are_rejected(tmp_path):
    path = tmp_path / "predictions.npz"
    _archive(path)
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr("extra.npy", b"x")
    with pytest.raises(ArtifactValidationError, match="members"):
        evaluate_prediction_archive(
            path,
            expected_run_id="a" * 64,
            expected_dataset="Roman-empire",
            expected_split=0,
            expected_test_indices=np.asarray([4, 9, 12], dtype=np.int64),
            authoritative_test_labels=np.asarray([1, 1, 2], dtype=np.int64),
        )


def test_split_ids_require_exact_integer_scalars(tmp_path):
    path = tmp_path / "predictions.npz"
    _archive(path)
    kwargs = dict(
        expected_run_id="a" * 64,
        expected_dataset="Roman-empire",
        expected_test_indices=np.asarray([4, 9, 12], dtype=np.int64),
        authoritative_test_labels=np.asarray([1, 1, 2], dtype=np.int64),
    )
    with pytest.raises(ArtifactValidationError, match="outside official"):
        evaluate_prediction_archive(path, expected_split=0.75, **kwargs)
    with pytest.raises(ArtifactValidationError, match="outside official"):
        evaluate_prediction_archive(path, expected_split=True, **kwargs)

    with np.load(path, allow_pickle=False) as stored:
        values = {name: np.asarray(stored[name]) for name in stored.files}
    values["split_id"] = np.asarray(0.75, dtype=np.float64)
    np.savez_compressed(path, **values)
    with pytest.raises(ArtifactValidationError, match="exact integer scalar"):
        evaluate_prediction_archive(path, expected_split=0, **kwargs)

    stream = io.BytesIO()
    np.save(stream, np.asarray([object()], dtype=object), allow_pickle=True)
    with zipfile.ZipFile(path, "w") as archive:
        for name in ("dataset", "format", "indices", "logits", "run_id", "split_id"):
            archive.writestr(f"{name}.npy", stream.getvalue())
    with pytest.raises(ArtifactValidationError, match="invalid"):
        evaluate_prediction_archive(
            path,
            expected_run_id="a" * 64,
            expected_dataset="Roman-empire",
            expected_split=0,
            expected_test_indices=np.asarray([4, 9, 12], dtype=np.int64),
            authoritative_test_labels=np.asarray([1, 1, 2], dtype=np.int64),
        )
