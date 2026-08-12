"""Independent post-freeze evaluator for official heterophily predictions."""

from __future__ import annotations

import hashlib
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np

from gbdn.artifacts import (
    ArtifactValidationError,
    canonical_json_bytes,
    canonical_json_sha256,
    sha256_file,
)
from gbdn.heterophily_contract import OFFICIAL_SPLITS, resolve_dataset
from gbdn.heterophily_statistics import recompute_primary_metric


PREDICTION_FORMAT: Final[str] = "gbdn-official-heterophily-predictions-v1"
EVALUATION_SCHEMA: Final[str] = "gbdn-independent-heterophily-evaluation-v1"
_MAX_ARCHIVE_BYTES: Final[int] = 512 * 1024 * 1024
_MAX_MEMBER_BYTES: Final[int] = 256 * 1024 * 1024
_MEMBERS: Final[frozenset[str]] = frozenset(
    {"dataset.npy", "format.npy", "indices.npy", "logits.npy", "run_id.npy", "split_id.npy"}
)


@dataclass(frozen=True)
class IndependentlyEvaluatedMetric:
    run_id: str
    dataset: str
    split: int
    metric_name: str
    value: float
    prediction_sha256: str
    example_count: int


@dataclass(frozen=True)
class AuthoritativeSplit:
    indices: np.ndarray
    labels: np.ndarray
    dataset_sha256: str
    indices_sha256: str
    labels_sha256: str


def _array_sha256(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    return canonical_json_sha256(
        {
            "dtype": array.dtype.str,
            "shape": list(array.shape),
            "bytes_sha256": hashlib.sha256(array.tobytes()).hexdigest(),
        }
    )


def load_authoritative_split(
    dataset_root: str | Path, *, dataset: str, split: int
) -> AuthoritativeSplit:
    """Load only the pinned test row and labels in the trusted parent process."""

    spec = resolve_dataset(dataset)
    if split not in OFFICIAL_SPLITS:
        raise ArtifactValidationError("prediction split is outside official rows 0..9")
    root = Path(dataset_root)
    if root.is_symlink() or not root.is_dir():
        raise ArtifactValidationError("authoritative dataset root must be a regular directory")
    archive = root / spec.npz_path
    if archive.is_symlink() or not archive.is_file():
        raise ArtifactValidationError("authoritative dataset archive is absent or unsafe")
    if archive.stat().st_size != spec.npz_size_bytes or sha256_file(archive) != spec.npz_sha256:
        raise ArtifactValidationError("authoritative dataset archive differs from pinned identity")
    try:
        with np.load(archive, allow_pickle=False) as stored:
            if "node_labels" not in stored or "test_masks" not in stored:
                raise ArtifactValidationError("authoritative dataset lacks labels or test masks")
            all_labels = np.asarray(stored["node_labels"]).reshape(-1)
            masks = np.asarray(stored["test_masks"])
    except ArtifactValidationError:
        raise
    except (OSError, ValueError, TypeError, KeyError, zipfile.BadZipFile) as exc:
        raise ArtifactValidationError("authoritative dataset archive is invalid") from exc
    if all_labels.dtype != np.int64 or all_labels.shape != (spec.node_count,):
        raise ArtifactValidationError("authoritative labels differ from the official contract")
    if masks.dtype != np.bool_ or masks.shape != (len(OFFICIAL_SPLITS), spec.node_count):
        raise ArtifactValidationError("authoritative test masks differ from the official contract")
    indices = np.flatnonzero(masks[split]).astype(np.int64, copy=False)
    labels = np.ascontiguousarray(all_labels[indices], dtype=np.int64)
    if indices.size == 0:
        raise ArtifactValidationError("authoritative test split is empty")
    return AuthoritativeSplit(
        indices,
        labels,
        spec.npz_sha256,
        _array_sha256(indices),
        _array_sha256(labels),
    )


def evaluation_attestation(
    metric: IndependentlyEvaluatedMetric,
    authority: AuthoritativeSplit,
    *,
    evaluator_sha256: str,
) -> dict[str, object]:
    """Create a deterministic, non-label-bearing evaluation attestation."""

    return {
        "attestation_sha256": canonical_json_sha256(
            {
                "dataset": metric.dataset,
                "dataset_sha256": authority.dataset_sha256,
                "evaluator_sha256": evaluator_sha256,
                "example_count": metric.example_count,
                "indices_sha256": authority.indices_sha256,
                "labels_sha256": authority.labels_sha256,
                "metric_name": metric.metric_name,
                "metric_value": metric.value,
                "prediction_sha256": metric.prediction_sha256,
                "run_id": metric.run_id,
                "split": metric.split,
            }
        ),
        "dataset": metric.dataset,
        "dataset_sha256": authority.dataset_sha256,
        "evaluator_sha256": evaluator_sha256,
        "example_count": metric.example_count,
        "indices_sha256": authority.indices_sha256,
        "labels_sha256": authority.labels_sha256,
        "metric_name": metric.metric_name,
        "metric_value": metric.value,
        "prediction_sha256": metric.prediction_sha256,
        "run_id": metric.run_id,
        "schema_version": EVALUATION_SCHEMA,
        "split": metric.split,
    }


def evaluate_prediction_archive(
    path: str | Path,
    *,
    expected_run_id: str,
    expected_dataset: str,
    expected_split: int,
    expected_test_indices: np.ndarray,
    authoritative_test_labels: np.ndarray,
) -> IndependentlyEvaluatedMetric:
    """Recompute one primary metric without accessing training/checkpoint state."""

    archive_path = Path(path)
    if archive_path.is_symlink() or not archive_path.is_file():
        raise ArtifactValidationError("prediction archive must be a regular file")
    if archive_path.stat().st_size > _MAX_ARCHIVE_BYTES:
        raise ArtifactValidationError("prediction archive exceeds the evaluator size limit")
    spec = resolve_dataset(expected_dataset)
    if type(expected_split) is not int or expected_split not in OFFICIAL_SPLITS:
        raise ArtifactValidationError("prediction split is outside official rows 0..9")
    expected_indices = np.asarray(expected_test_indices)
    labels = np.asarray(authoritative_test_labels)
    if expected_indices.dtype != np.int64 or expected_indices.ndim != 1 or expected_indices.size == 0:
        raise ArtifactValidationError("authoritative test indices must be a nonempty int64 vector")
    if labels.dtype != np.int64 or labels.shape != expected_indices.shape:
        raise ArtifactValidationError("authoritative test labels must be aligned int64 values")
    if np.unique(expected_indices).size != expected_indices.size or np.any(expected_indices < 0):
        raise ArtifactValidationError("authoritative test indices must be unique and nonnegative")
    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = archive.infolist()
            if frozenset(member.filename for member in members) != _MEMBERS:
                raise ArtifactValidationError("prediction archive members do not match schema")
            if any(member.is_dir() or member.file_size > _MAX_MEMBER_BYTES for member in members):
                raise ArtifactValidationError("prediction archive contains an unsafe member")
        with np.load(archive_path, allow_pickle=False) as stored:
            dataset = str(np.asarray(stored["dataset"]).item())
            format_name = str(np.asarray(stored["format"]).item())
            indices = np.asarray(stored["indices"])
            logits = np.asarray(stored["logits"])
            run_id = str(np.asarray(stored["run_id"]).item())
            stored_split = np.asarray(stored["split_id"])
            if stored_split.ndim != 0 or stored_split.dtype.kind not in {"i", "u"}:
                raise ArtifactValidationError(
                    "prediction split_id must be one exact integer scalar"
                )
            split = stored_split.item()
            if type(split) is not int:
                raise ArtifactValidationError(
                    "prediction split_id must be one exact integer scalar"
                )
    except ArtifactValidationError:
        raise
    except (OSError, ValueError, TypeError, KeyError, zipfile.BadZipFile) as exc:
        raise ArtifactValidationError("prediction archive is invalid") from exc
    if run_id != expected_run_id or dataset != spec.canonical_name or split != expected_split:
        raise ArtifactValidationError("prediction identity differs from frozen evaluation request")
    if format_name != PREDICTION_FORMAT:
        raise ArtifactValidationError("prediction format is unsupported")
    if indices.dtype != np.int64 or not np.array_equal(indices, expected_indices):
        raise ArtifactValidationError("prediction indices differ from authoritative ordered test indices")
    if logits.dtype not in (np.dtype("float32"), np.dtype("float64")) or not np.all(np.isfinite(logits)):
        raise ArtifactValidationError("prediction logits must be finite float32/float64")
    expected_shape = (
        (expected_indices.size, spec.output_logits)
        if spec.task_type == "multiclass"
        else (expected_indices.size,)
    )
    if logits.shape != expected_shape:
        raise ArtifactValidationError("prediction logit shape does not match official task head")
    metric_name, metric = recompute_primary_metric(spec.canonical_name, logits, labels)
    return IndependentlyEvaluatedMetric(
        run_id,
        spec.canonical_name,
        split,
        metric_name,
        metric,
        sha256_file(archive_path),
        expected_indices.size,
    )


__all__ = [
    "AuthoritativeSplit",
    "EVALUATION_SCHEMA",
    "IndependentlyEvaluatedMetric",
    "PREDICTION_FORMAT",
    "evaluation_attestation",
    "evaluate_prediction_archive",
    "load_authoritative_split",
]
