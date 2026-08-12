"""Independent post-freeze evaluator for official heterophily predictions."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np

from gbdn.artifacts import ArtifactValidationError, sha256_file
from gbdn.heterophily_contract import OFFICIAL_SPLITS, resolve_dataset
from gbdn.heterophily_statistics import recompute_primary_metric


PREDICTION_FORMAT: Final[str] = "gbdn-official-heterophily-predictions-v1"
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
    if expected_split not in OFFICIAL_SPLITS:
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
            split = int(np.asarray(stored["split_id"]).item())
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
    "IndependentlyEvaluatedMetric",
    "PREDICTION_FORMAT",
    "evaluate_prediction_archive",
]
