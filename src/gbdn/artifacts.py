"""Immutable, hash-bound artifacts for canonical submission runs.

This module contains no experiment or metric logic.  It freezes run identity,
records source and environment metadata, commits complete bundles atomically,
and classifies existing bundles for safe orchestration-level resume.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform as platform_module
import re
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Final
from urllib.parse import quote

from gbdn.provenance import (
    CANONICAL_RESULT_DIR,
    canonical_output_path,
    write_new_canonical_artifact,
)


SCHEMA_VERSION: Final[str] = "1.0"
NA_ID: Final[str] = "na"
_SHA256_RE: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}")
_GIT_OBJECT_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:[0-9a-f]{40}|[0-9a-f]{64})"
)
_RESERVED_BUNDLE_FILES: Final[frozenset[str]] = frozenset(
    {"bundle.json", "config.json", "result.json"}
)


class ArtifactValidationError(ValueError):
    """Raised when an artifact or record violates its frozen schema."""


class ArtifactConflictError(RuntimeError):
    """Raised when a logical run slot already contains another identity."""


class DirtySourceError(ArtifactValidationError):
    """Raised when a full run is requested from an unapproved dirty tree."""


class _ArtifactIdentityConflict(ArtifactValidationError):
    """Internal signal used to distinguish identity conflict from corruption."""


class ArtifactStateError(RuntimeError):
    """Raised when an existing partial or corrupt bundle needs intervention."""

    def __init__(self, decision: "ResumeDecision") -> None:
        super().__init__(f"{decision.state.value}: {decision.reason}")
        self.decision = decision


class RunMode(str, Enum):
    SMOKE = "smoke"
    PILOT = "pilot"
    FULL = "full"
    RENDER_ONLY = "render-only"
    VERIFY_ONLY = "verify-only"


def _normalize_json(value: Any, *, location: str = "$") -> Any:
    if value is None or type(value) in (bool, int, str):
        if isinstance(value, str):
            try:
                value.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise TypeError(f"{location} contains a non-UTF-8 string") from exc
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{location} contains a non-finite float")
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{location} has a non-string object key")
            normalized[key] = _normalize_json(item, location=f"{location}.{key}")
        return normalized
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray, memoryview)
    ):
        return [
            _normalize_json(item, location=f"{location}[{index}]")
            for index, item in enumerate(value)
        ]
    raise TypeError(f"{location} contains unsupported JSON type {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    """Return the repository's deterministic UTF-8 JSON representation."""

    normalized = _normalize_json(value)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_json_sha256(value: Any) -> str:
    """Hash a value after deterministic canonical JSON serialization."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA-256 digest of one regular file."""

    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise ArtifactValidationError(f"not a regular artifact file: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file_sha256(path: str | Path, expected_sha256: str) -> bool:
    """Return whether a regular file matches one validated SHA-256 digest."""

    expected = _validate_sha256(expected_sha256, "expected_sha256")
    try:
        observed = sha256_file(path)
    except (FileNotFoundError, ArtifactValidationError, OSError):
        return False
    return observed == expected


def _reject_json_constant(value: str) -> None:
    raise ArtifactValidationError(f"non-standard JSON constant: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ArtifactValidationError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _decode_canonical_json_bytes(payload: bytes, *, label: str) -> Any:
    try:
        text = payload.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError(f"invalid JSON in {label}") from exc
    try:
        expected = canonical_json_bytes(value)
    except (TypeError, ValueError) as exc:
        raise ArtifactValidationError(f"invalid canonical JSON in {label}") from exc
    if expected != payload:
        raise ArtifactValidationError(f"non-canonical JSON serialization in {label}")
    return value


def _load_canonical_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise ArtifactValidationError(f"missing regular JSON artifact: {path}")
    return _decode_canonical_json_bytes(path.read_bytes(), label=str(path))


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ArtifactValidationError(f"{label} must be a JSON object")
    return value


def _require_exact_keys(
    value: Mapping[str, Any], expected: set[str], label: str
) -> None:
    observed = set(value)
    if observed != expected:
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
        raise ArtifactValidationError(
            f"{label} keys mismatch; missing={missing}, extra={extra}"
        )


def _validate_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ArtifactValidationError(f"{field} must be 64 lowercase hex characters")
    return value


def _validate_git_object(value: Any, field: str, *, allow_na: bool = False) -> str:
    if allow_na and value == NA_ID:
        return value
    if not isinstance(value, str) or _GIT_OBJECT_RE.fullmatch(value) is None:
        raise ArtifactValidationError(f"{field} must be a full Git object ID")
    return value


def _validate_label(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ArtifactValidationError(f"{field} must be a nonempty trimmed string")
    if any(ord(character) < 32 for character in value):
        raise ArtifactValidationError(f"{field} contains a control character")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ArtifactValidationError(f"{field} is not valid UTF-8") from exc
    return value


def _validate_index(value: Any, field: str) -> int | str:
    if value == NA_ID:
        return value
    if type(value) is not int or value < 0:
        raise ArtifactValidationError(
            f"{field} must be a nonnegative integer or the explicit '{NA_ID}' sentinel"
        )
    return value


def _validate_timestamp(value: Any, field: str = "created_at_utc") -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ArtifactValidationError(f"{field} must be an ISO-8601 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ArtifactValidationError(f"{field} is not a valid timestamp") from exc
    if parsed.utcoffset() != timedelta(0):
        raise ArtifactValidationError(f"{field} must use UTC")
    return value


def utc_now_iso() -> str:
    """Return a second-resolution UTC timestamp for artifact metadata."""

    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _safe_relative_path(value: Any, field: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ArtifactValidationError(f"{field} must be a nonempty POSIX relative path")
    segments = value.split("/")
    if any(segment in ("", ".", "..") for segment in segments):
        raise ArtifactValidationError(f"{field} contains an unsafe path segment")
    path = PurePosixPath(value)
    if path.is_absolute():
        raise ArtifactValidationError(f"{field} must be relative")
    return path


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


@dataclass(frozen=True)
class RunIdentity:
    """All frozen fields that define one canonical run identity."""

    schema_version: str
    experiment: str
    dataset_name: str
    dataset_sha256: str
    model_name: str
    model_variant: str
    split_id: int | str
    seed: int | str
    trial_id: int | str
    frozen_config_sha256: str
    source_sha256: str
    dependency_lock_sha256: str
    baseline_upstream_commit: str
    precision_mode: str

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ArtifactValidationError(
                f"unsupported schema_version: {self.schema_version!r}"
            )
        _validate_label(self.experiment, "experiment")
        _validate_label(self.dataset_name, "dataset_name")
        _validate_sha256(self.dataset_sha256, "dataset_sha256")
        _validate_label(self.model_name, "model_name")
        _validate_label(self.model_variant, "model_variant")
        _validate_index(self.split_id, "split_id")
        _validate_index(self.seed, "seed")
        _validate_index(self.trial_id, "trial_id")
        _validate_sha256(self.frozen_config_sha256, "frozen_config_sha256")
        _validate_sha256(self.source_sha256, "source_sha256")
        _validate_sha256(self.dependency_lock_sha256, "dependency_lock_sha256")
        _validate_git_object(
            self.baseline_upstream_commit,
            "baseline_upstream_commit",
            allow_na=True,
        )
        _validate_label(self.precision_mode, "precision_mode")

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_upstream_commit": self.baseline_upstream_commit,
            "dataset": {
                "name": self.dataset_name,
                "sha256": self.dataset_sha256,
            },
            "dependency_lock_sha256": self.dependency_lock_sha256,
            "experiment": self.experiment,
            "frozen_config_sha256": self.frozen_config_sha256,
            "model": {"name": self.model_name, "variant": self.model_variant},
            "precision_mode": self.precision_mode,
            "schema_version": self.schema_version,
            "seed": self.seed,
            "source_sha256": self.source_sha256,
            "split": self.split_id,
            "trial": self.trial_id,
        }

    @property
    def run_id(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: Any) -> "RunIdentity":
        data = _require_mapping(value, "identity")
        _require_exact_keys(
            data,
            {
                "baseline_upstream_commit",
                "dataset",
                "dependency_lock_sha256",
                "experiment",
                "frozen_config_sha256",
                "model",
                "precision_mode",
                "schema_version",
                "seed",
                "source_sha256",
                "split",
                "trial",
            },
            "identity",
        )
        dataset = _require_mapping(data["dataset"], "identity.dataset")
        model = _require_mapping(data["model"], "identity.model")
        _require_exact_keys(dataset, {"name", "sha256"}, "identity.dataset")
        _require_exact_keys(model, {"name", "variant"}, "identity.model")
        return cls(
            schema_version=data["schema_version"],
            experiment=data["experiment"],
            dataset_name=dataset["name"],
            dataset_sha256=dataset["sha256"],
            model_name=model["name"],
            model_variant=model["variant"],
            split_id=data["split"],
            seed=data["seed"],
            trial_id=data["trial"],
            frozen_config_sha256=data["frozen_config_sha256"],
            source_sha256=data["source_sha256"],
            dependency_lock_sha256=data["dependency_lock_sha256"],
            baseline_upstream_commit=data["baseline_upstream_commit"],
            precision_mode=data["precision_mode"],
        )


@dataclass(frozen=True)
class SourceMetadata:
    repository_commit: str
    repository_tree: str
    source_sha256: str
    dirty: bool
    dirty_fingerprint_sha256: str | None
    dirty_override: bool

    def __post_init__(self) -> None:
        _validate_git_object(self.repository_commit, "repository_commit")
        _validate_git_object(self.repository_tree, "repository_tree")
        _validate_sha256(self.source_sha256, "source_sha256")
        if type(self.dirty) is not bool or type(self.dirty_override) is not bool:
            raise ArtifactValidationError("dirty flags must be booleans")
        if self.dirty:
            _validate_sha256(
                self.dirty_fingerprint_sha256, "dirty_fingerprint_sha256"
            )
        elif self.dirty_fingerprint_sha256 is not None or self.dirty_override:
            raise ArtifactValidationError(
                "clean source metadata cannot carry dirty state or an override"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "dirty": self.dirty,
            "dirty_fingerprint_sha256": self.dirty_fingerprint_sha256,
            "dirty_override": self.dirty_override,
            "repository_commit": self.repository_commit,
            "repository_tree": self.repository_tree,
            "source_sha256": self.source_sha256,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "SourceMetadata":
        data = _require_mapping(value, "source")
        _require_exact_keys(
            data,
            {
                "dirty",
                "dirty_fingerprint_sha256",
                "dirty_override",
                "repository_commit",
                "repository_tree",
                "source_sha256",
            },
            "source",
        )
        return cls(**data)


@dataclass(frozen=True)
class EnvironmentMetadata:
    python_version: str
    python_implementation: str
    platform: str
    machine: str
    executable: str
    dependency_lock_path: str
    dependency_lock_sha256: str
    cuda_visible_devices: str | None
    cublas_workspace_config: str | None
    pythonhashseed: str | None

    def __post_init__(self) -> None:
        for field, value in (
            ("python_version", self.python_version),
            ("python_implementation", self.python_implementation),
            ("platform", self.platform),
            ("machine", self.machine),
            ("executable", self.executable),
            ("dependency_lock_path", self.dependency_lock_path),
        ):
            _validate_label(value, field)
        _validate_sha256(self.dependency_lock_sha256, "dependency_lock_sha256")
        for field, value in (
            ("cuda_visible_devices", self.cuda_visible_devices),
            ("cublas_workspace_config", self.cublas_workspace_config),
            ("pythonhashseed", self.pythonhashseed),
        ):
            if value is not None:
                _validate_label(value, field)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cublas_workspace_config": self.cublas_workspace_config,
            "cuda_visible_devices": self.cuda_visible_devices,
            "dependency_lock_path": self.dependency_lock_path,
            "dependency_lock_sha256": self.dependency_lock_sha256,
            "executable": self.executable,
            "machine": self.machine,
            "platform": self.platform,
            "python_implementation": self.python_implementation,
            "python_version": self.python_version,
            "pythonhashseed": self.pythonhashseed,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "EnvironmentMetadata":
        data = _require_mapping(value, "environment")
        _require_exact_keys(
            data,
            {
                "cublas_workspace_config",
                "cuda_visible_devices",
                "dependency_lock_path",
                "dependency_lock_sha256",
                "executable",
                "machine",
                "platform",
                "python_implementation",
                "python_version",
                "pythonhashseed",
            },
            "environment",
        )
        return cls(**data)


def _run_git(repository_root: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repository_root), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ArtifactValidationError(f"git {' '.join(arguments)} failed: {message}")
    return completed.stdout


def _dirty_fingerprint(repository_root: Path, status: bytes) -> str:
    digest = hashlib.sha256()

    def add_chunk(label: bytes, payload: bytes) -> None:
        digest.update(len(label).to_bytes(4, "big"))
        digest.update(label)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)

    add_chunk(b"status", status)
    add_chunk(
        b"tracked-diff",
        _run_git(
            repository_root,
            "diff",
            "--binary",
            "--no-ext-diff",
            "HEAD",
            "--",
        ),
    )
    untracked = _run_git(
        repository_root, "ls-files", "--others", "--exclude-standard", "-z"
    )
    for raw_name in sorted(name for name in untracked.split(b"\0") if name):
        relative = os.fsdecode(raw_name)
        path = repository_root / relative
        add_chunk(b"untracked-path", raw_name)
        if path.is_symlink():
            add_chunk(b"untracked-symlink", os.fsencode(os.readlink(path)))
        elif path.is_file():
            add_chunk(b"untracked-file-sha256", bytes.fromhex(sha256_file(path)))
        else:
            add_chunk(b"untracked-special", b"")
    return digest.hexdigest()


def capture_source_metadata(
    repository_root: str | Path,
    *,
    full_run: bool,
    allow_dirty: bool = False,
) -> SourceMetadata:
    """Capture Git-bound source metadata and enforce the full-run dirty policy."""

    root = Path(repository_root).resolve(strict=True)
    commit = _run_git(root, "rev-parse", "HEAD").decode("ascii").strip()
    tree = _run_git(root, "rev-parse", "HEAD^{tree}").decode("ascii").strip()
    status = _run_git(
        root, "status", "--porcelain=v1", "--untracked-files=all", "-z"
    )
    dirty = bool(status)
    if full_run and dirty and not allow_dirty:
        raise DirtySourceError(
            "full runs require a clean Git tree unless allow_dirty=True is recorded"
        )
    fingerprint = _dirty_fingerprint(root, status) if dirty else None
    source_sha256 = canonical_json_sha256(
        {
            "dirty_fingerprint_sha256": fingerprint or "clean",
            "repository_commit": commit,
            "repository_tree": tree,
        }
    )
    return SourceMetadata(
        repository_commit=commit,
        repository_tree=tree,
        source_sha256=source_sha256,
        dirty=dirty,
        dirty_fingerprint_sha256=fingerprint,
        dirty_override=bool(full_run and dirty and allow_dirty),
    )


def capture_environment_metadata(
    dependency_lock_path: str | Path,
    *,
    repository_root: str | Path | None = None,
) -> EnvironmentMetadata:
    """Capture stdlib environment metadata and bind it to a dependency lock."""

    lock_path = Path(dependency_lock_path).resolve(strict=True)
    if not lock_path.is_file() or lock_path.is_symlink():
        raise ArtifactValidationError("dependency lock must be a regular file")
    if repository_root is None:
        recorded_path = str(lock_path)
    else:
        root = Path(repository_root).resolve(strict=True)
        try:
            recorded_path = lock_path.relative_to(root).as_posix()
        except ValueError:
            recorded_path = str(lock_path)
    return EnvironmentMetadata(
        python_version=platform_module.python_version(),
        python_implementation=platform_module.python_implementation(),
        platform=platform_module.platform(),
        machine=platform_module.machine() or "unknown",
        executable=sys.executable,
        dependency_lock_path=recorded_path,
        dependency_lock_sha256=sha256_file(lock_path),
        cuda_visible_devices=os.environ.get("CUDA_VISIBLE_DEVICES"),
        cublas_workspace_config=os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
        pythonhashseed=os.environ.get("PYTHONHASHSEED"),
    )


@dataclass(frozen=True)
class RunConfigRecord:
    identity: RunIdentity
    frozen_config_json: str
    source: SourceMetadata
    environment: EnvironmentMetadata
    run_mode: RunMode
    created_at_utc: str

    def __post_init__(self) -> None:
        try:
            mode = RunMode(self.run_mode)
        except ValueError as exc:
            raise ArtifactValidationError(f"unsupported run_mode: {self.run_mode!r}") from exc
        object.__setattr__(self, "run_mode", mode)
        _validate_timestamp(self.created_at_utc)
        try:
            config = _decode_canonical_json_bytes(
                self.frozen_config_json.encode("utf-8"), label="frozen_config_json"
            )
        except UnicodeEncodeError as exc:
            raise ArtifactValidationError("frozen_config_json is not UTF-8") from exc
        _require_mapping(config, "frozen_config")
        if canonical_json_sha256(config) != self.identity.frozen_config_sha256:
            raise ArtifactValidationError("frozen config does not match run identity")
        if self.source.source_sha256 != self.identity.source_sha256:
            raise ArtifactValidationError("source metadata does not match run identity")
        if (
            self.environment.dependency_lock_sha256
            != self.identity.dependency_lock_sha256
        ):
            raise ArtifactValidationError(
                "dependency lock metadata does not match run identity"
            )
        if (
            self.run_mode is RunMode.FULL
            and self.source.dirty
            and not self.source.dirty_override
        ):
            raise DirtySourceError("dirty full-run config lacks an explicit override")

    @classmethod
    def create(
        cls,
        *,
        identity: RunIdentity,
        frozen_config: Mapping[str, Any],
        source: SourceMetadata,
        environment: EnvironmentMetadata,
        run_mode: str | RunMode,
        created_at_utc: str | None = None,
    ) -> "RunConfigRecord":
        return cls(
            identity=identity,
            frozen_config_json=canonical_json_bytes(frozen_config).decode("utf-8"),
            source=source,
            environment=environment,
            run_mode=run_mode,  # type: ignore[arg-type]
            created_at_utc=created_at_utc or utc_now_iso(),
        )

    def to_dict(self) -> dict[str, Any]:
        config = _decode_canonical_json_bytes(
            self.frozen_config_json.encode("utf-8"), label="frozen_config_json"
        )
        return {
            "created_at_utc": self.created_at_utc,
            "environment": self.environment.to_dict(),
            "frozen_config": config,
            "frozen_config_sha256": self.identity.frozen_config_sha256,
            "identity": self.identity.to_dict(),
            "run_id": self.identity.run_id,
            "run_mode": self.run_mode.value,
            "schema_version": self.identity.schema_version,
            "source": self.source.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Any) -> "RunConfigRecord":
        data = _require_mapping(value, "config record")
        _require_exact_keys(
            data,
            {
                "created_at_utc",
                "environment",
                "frozen_config",
                "frozen_config_sha256",
                "identity",
                "run_id",
                "run_mode",
                "schema_version",
                "source",
            },
            "config record",
        )
        identity = RunIdentity.from_dict(data["identity"])
        if data["schema_version"] != identity.schema_version:
            raise ArtifactValidationError("config schema version mismatch")
        if data["run_id"] != identity.run_id:
            raise _ArtifactIdentityConflict("config run_id does not match identity")
        if data["frozen_config_sha256"] != identity.frozen_config_sha256:
            raise _ArtifactIdentityConflict("config hash does not match identity")
        return cls.create(
            identity=identity,
            frozen_config=_require_mapping(data["frozen_config"], "frozen_config"),
            source=SourceMetadata.from_dict(data["source"]),
            environment=EnvironmentMetadata.from_dict(data["environment"]),
            run_mode=data["run_mode"],
            created_at_utc=data["created_at_utc"],
        )


@dataclass(frozen=True)
class ArtifactFileManifest:
    path: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        _safe_relative_path(self.path, "artifact path")
        _validate_sha256(self.sha256, "artifact sha256")
        if type(self.size_bytes) is not int or self.size_bytes < 0:
            raise ArtifactValidationError("artifact size_bytes must be nonnegative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "ArtifactFileManifest":
        data = _require_mapping(value, "file manifest")
        _require_exact_keys(data, {"path", "sha256", "size_bytes"}, "file manifest")
        return cls(**data)


@dataclass(frozen=True)
class PredictionArtifactManifest:
    run_id: str
    path: str
    sha256: str
    size_bytes: int
    format: str

    def __post_init__(self) -> None:
        _validate_sha256(self.run_id, "prediction run_id")
        _safe_relative_path(self.path, "prediction path")
        if self.path != "predictions.npz":
            raise ArtifactValidationError(
                "the required prediction artifact path is predictions.npz"
            )
        _validate_sha256(self.sha256, "prediction sha256")
        if type(self.size_bytes) is not int or self.size_bytes < 0:
            raise ArtifactValidationError("prediction size_bytes must be nonnegative")
        _validate_label(self.format, "prediction format")

    @classmethod
    def from_file_manifest(
        cls,
        run_id: str,
        file_manifest: ArtifactFileManifest,
        *,
        format: str,
    ) -> "PredictionArtifactManifest":
        return cls(
            run_id=run_id,
            path=file_manifest.path,
            sha256=file_manifest.sha256,
            size_bytes=file_manifest.size_bytes,
            format=format,
        )

    def to_file_manifest(self) -> ArtifactFileManifest:
        return ArtifactFileManifest(
            path=self.path, sha256=self.sha256, size_bytes=self.size_bytes
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": self.format,
            "path": self.path,
            "run_id": self.run_id,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "PredictionArtifactManifest":
        data = _require_mapping(value, "prediction manifest")
        _require_exact_keys(
            data,
            {"format", "path", "run_id", "sha256", "size_bytes"},
            "prediction manifest",
        )
        return cls(**data)


@dataclass(frozen=True)
class RunResultRecord:
    identity: RunIdentity
    predictions: PredictionArtifactManifest
    result_payload_json: str
    source: SourceMetadata
    environment: EnvironmentMetadata
    created_at_utc: str

    def __post_init__(self) -> None:
        _validate_timestamp(self.created_at_utc)
        try:
            payload = _decode_canonical_json_bytes(
                self.result_payload_json.encode("utf-8"), label="result_payload_json"
            )
        except UnicodeEncodeError as exc:
            raise ArtifactValidationError("result_payload_json is not UTF-8") from exc
        _require_mapping(payload, "result payload")
        if self.predictions.run_id != self.identity.run_id:
            raise ArtifactValidationError("prediction manifest is bound to another run")
        if self.source.source_sha256 != self.identity.source_sha256:
            raise ArtifactValidationError("result source does not match run identity")
        if (
            self.environment.dependency_lock_sha256
            != self.identity.dependency_lock_sha256
        ):
            raise ArtifactValidationError("result lock hash does not match run identity")

    @classmethod
    def create(
        cls,
        *,
        identity: RunIdentity,
        predictions: PredictionArtifactManifest,
        result_payload: Mapping[str, Any],
        source: SourceMetadata,
        environment: EnvironmentMetadata,
        created_at_utc: str | None = None,
    ) -> "RunResultRecord":
        return cls(
            identity=identity,
            predictions=predictions,
            result_payload_json=canonical_json_bytes(result_payload).decode("utf-8"),
            source=source,
            environment=environment,
            created_at_utc=created_at_utc or utc_now_iso(),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = _decode_canonical_json_bytes(
            self.result_payload_json.encode("utf-8"), label="result_payload_json"
        )
        return {
            "created_at_utc": self.created_at_utc,
            "environment": self.environment.to_dict(),
            "frozen_config_sha256": self.identity.frozen_config_sha256,
            "identity": self.identity.to_dict(),
            "payload": payload,
            "predictions": self.predictions.to_dict(),
            "run_id": self.identity.run_id,
            "schema_version": self.identity.schema_version,
            "source": self.source.to_dict(),
            "status": "complete",
        }

    @classmethod
    def from_dict(cls, value: Any) -> "RunResultRecord":
        data = _require_mapping(value, "result record")
        _require_exact_keys(
            data,
            {
                "created_at_utc",
                "environment",
                "frozen_config_sha256",
                "identity",
                "payload",
                "predictions",
                "run_id",
                "schema_version",
                "source",
                "status",
            },
            "result record",
        )
        identity = RunIdentity.from_dict(data["identity"])
        if data["schema_version"] != identity.schema_version or data["status"] != "complete":
            raise ArtifactValidationError("result schema version or status is invalid")
        if data["run_id"] != identity.run_id:
            raise _ArtifactIdentityConflict("result run_id does not match identity")
        if data["frozen_config_sha256"] != identity.frozen_config_sha256:
            raise _ArtifactIdentityConflict("result config hash does not match identity")
        return cls.create(
            identity=identity,
            predictions=PredictionArtifactManifest.from_dict(data["predictions"]),
            result_payload=_require_mapping(data["payload"], "result payload"),
            source=SourceMetadata.from_dict(data["source"]),
            environment=EnvironmentMetadata.from_dict(data["environment"]),
            created_at_utc=data["created_at_utc"],
        )


@dataclass(frozen=True)
class FailureRecord:
    identity: RunIdentity
    exception_type: str
    message: str
    traceback_path: str
    partial_artifacts: tuple[str, ...]
    source: SourceMetadata
    environment: EnvironmentMetadata
    created_at_utc: str

    def __post_init__(self) -> None:
        _validate_label(self.exception_type, "exception_type")
        if not isinstance(self.message, str):
            raise ArtifactValidationError("failure message must be a string")
        if self.traceback_path != NA_ID:
            _safe_relative_path(self.traceback_path, "traceback_path")
        normalized = tuple(sorted(self.partial_artifacts))
        if len(set(normalized)) != len(normalized):
            raise ArtifactValidationError("partial_artifacts contains duplicates")
        for path in normalized:
            _safe_relative_path(path, "partial_artifact")
        object.__setattr__(self, "partial_artifacts", normalized)
        _validate_timestamp(self.created_at_utc)
        if self.source.source_sha256 != self.identity.source_sha256:
            raise ArtifactValidationError("failure source does not match run identity")
        if (
            self.environment.dependency_lock_sha256
            != self.identity.dependency_lock_sha256
        ):
            raise ArtifactValidationError("failure lock hash does not match identity")

    @property
    def failure_id(self) -> str:
        return canonical_json_sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at_utc": self.created_at_utc,
            "environment": self.environment.to_dict(),
            "exception_type": self.exception_type,
            "identity": self.identity.to_dict(),
            "message": self.message,
            "partial_artifacts": list(self.partial_artifacts),
            "run_id": self.identity.run_id,
            "schema_version": self.identity.schema_version,
            "source": self.source.to_dict(),
            "status": "failed",
            "traceback_path": self.traceback_path,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "FailureRecord":
        data = _require_mapping(value, "failure record")
        _require_exact_keys(
            data,
            {
                "created_at_utc",
                "environment",
                "exception_type",
                "identity",
                "message",
                "partial_artifacts",
                "run_id",
                "schema_version",
                "source",
                "status",
                "traceback_path",
            },
            "failure record",
        )
        identity = RunIdentity.from_dict(data["identity"])
        if data["schema_version"] != identity.schema_version or data["status"] != "failed":
            raise ArtifactValidationError("failure schema version or status is invalid")
        if data["run_id"] != identity.run_id:
            raise _ArtifactIdentityConflict("failure run_id does not match identity")
        partial = data["partial_artifacts"]
        if not isinstance(partial, list) or not all(isinstance(item, str) for item in partial):
            raise ArtifactValidationError("partial_artifacts must be a string list")
        return cls(
            identity=identity,
            exception_type=data["exception_type"],
            message=data["message"],
            traceback_path=data["traceback_path"],
            partial_artifacts=tuple(partial),
            source=SourceMetadata.from_dict(data["source"]),
            environment=EnvironmentMetadata.from_dict(data["environment"]),
            created_at_utc=data["created_at_utc"],
        )


@dataclass(frozen=True)
class BundleManifest:
    run_id: str
    files: tuple[ArtifactFileManifest, ...]
    created_at_utc: str

    def __post_init__(self) -> None:
        _validate_sha256(self.run_id, "bundle run_id")
        files = tuple(sorted(self.files, key=lambda item: item.path))
        paths = [item.path for item in files]
        if len(paths) != len(set(paths)):
            raise ArtifactValidationError("bundle manifest contains duplicate paths")
        if "bundle.json" in paths:
            raise ArtifactValidationError("bundle manifest cannot hash itself")
        for required in ("config.json", "result.json"):
            if required not in paths:
                raise ArtifactValidationError(f"bundle manifest is missing {required}")
        object.__setattr__(self, "files", files)
        _validate_timestamp(self.created_at_utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at_utc": self.created_at_utc,
            "files": [item.to_dict() for item in self.files],
            "run_id": self.run_id,
            "schema_version": SCHEMA_VERSION,
            "status": "complete",
        }

    @classmethod
    def from_dict(cls, value: Any) -> "BundleManifest":
        data = _require_mapping(value, "bundle manifest")
        _require_exact_keys(
            data,
            {"created_at_utc", "files", "run_id", "schema_version", "status"},
            "bundle manifest",
        )
        if data["schema_version"] != SCHEMA_VERSION or data["status"] != "complete":
            raise ArtifactValidationError("bundle schema version or status is invalid")
        files = data["files"]
        if not isinstance(files, list):
            raise ArtifactValidationError("bundle files must be a list")
        return cls(
            run_id=data["run_id"],
            files=tuple(ArtifactFileManifest.from_dict(item) for item in files),
            created_at_utc=data["created_at_utc"],
        )


def _path_component(value: str) -> str:
    return quote(value, safe="-._~")


def run_slot_relative_path(identity: RunIdentity) -> Path:
    """Return the logical run slot with explicit split/seed/trial components."""

    return (
        Path(CANONICAL_RESULT_DIR)
        / "raw"
        / f"experiment={_path_component(identity.experiment)}"
        / f"dataset={_path_component(identity.dataset_name)}"
        / f"model={_path_component(identity.model_name)}"
        / f"variant={_path_component(identity.model_variant)}"
        / f"split={identity.split_id}"
        / f"seed={identity.seed}"
        / f"trial={identity.trial_id}"
    )


def run_bundle_relative_path(identity: RunIdentity) -> Path:
    return run_slot_relative_path(identity) / f"run={identity.run_id}"


def canonical_run_bundle_path(
    identity: RunIdentity, *, repository_root: str | Path
) -> Path:
    return canonical_output_path(
        run_bundle_relative_path(identity), repository_root=repository_root
    )


def _canonical_run_slot_path(
    identity: RunIdentity, *, repository_root: str | Path
) -> Path:
    return canonical_output_path(run_slot_relative_path(identity), repository_root=repository_root)


def _staging_root(*, repository_root: str | Path) -> Path:
    return canonical_output_path(
        Path(CANONICAL_RESULT_DIR) / "state" / "staging",
        repository_root=repository_root,
    )


def _failure_directory(identity: RunIdentity, *, repository_root: str | Path) -> Path:
    return canonical_output_path(
        Path(CANONICAL_RESULT_DIR) / "failures" / f"run={identity.run_id}",
        repository_root=repository_root,
    )


def write_failure_record(
    record: FailureRecord, *, repository_root: str | Path
) -> Path:
    """Write one content-addressed failure record without replacing prior attempts."""

    relative = (
        Path(CANONICAL_RESULT_DIR)
        / "failures"
        / f"run={record.identity.run_id}"
        / f"failure={record.failure_id}.json"
    )
    return write_new_canonical_artifact(
        relative,
        canonical_json_bytes(record.to_dict()),
        repository_root=repository_root,
    )


def load_failure_record(path: str | Path) -> FailureRecord:
    return FailureRecord.from_dict(_load_canonical_json(Path(path)))


def _bundle_file_path(bundle_root: Path, relative_path: str) -> Path:
    safe = _safe_relative_path(relative_path, "artifact path")
    raw = bundle_root.joinpath(*safe.parts)
    current = bundle_root
    for segment in safe.parts:
        current = current / segment
        if current.is_symlink():
            raise ArtifactValidationError(f"artifact path uses a symlink: {relative_path}")
    try:
        resolved = raw.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ArtifactValidationError(f"missing artifact file: {relative_path}") from exc
    if not _is_within(resolved, bundle_root.resolve(strict=True)):
        raise ArtifactValidationError(f"artifact path escapes its bundle: {relative_path}")
    return resolved


def validate_prediction_manifest(
    bundle_root: str | Path,
    manifest: PredictionArtifactManifest,
    *,
    expected_run_id: str,
) -> Path:
    """Verify prediction presence, identity binding, size, and file hash."""

    expected = _validate_sha256(expected_run_id, "expected_run_id")
    if manifest.run_id != expected:
        raise _ArtifactIdentityConflict("prediction manifest belongs to another run")
    root = Path(bundle_root).resolve(strict=True)
    target = _bundle_file_path(root, manifest.path)
    if not target.is_file():
        raise ArtifactValidationError("prediction artifact is not a regular file")
    if target.stat().st_size != manifest.size_bytes:
        raise ArtifactValidationError("prediction artifact size mismatch")
    if sha256_file(target) != manifest.sha256:
        raise ArtifactValidationError("prediction artifact hash mismatch")
    return target


def _manifest_for_file(root: Path, relative_path: str) -> ArtifactFileManifest:
    target = _bundle_file_path(root, relative_path)
    return ArtifactFileManifest(
        path=relative_path,
        sha256=sha256_file(target),
        size_bytes=target.stat().st_size,
    )


def _validate_bundle_directory(bundle_path: Path, identity: RunIdentity) -> None:
    if bundle_path.is_symlink() or not bundle_path.is_dir():
        raise ArtifactValidationError("run bundle is not a regular directory")
    marker_path = bundle_path / "bundle.json"
    marker = BundleManifest.from_dict(_load_canonical_json(marker_path))
    if marker.run_id != identity.run_id:
        raise _ArtifactIdentityConflict("bundle marker belongs to another run")

    expected_files = {item.path: item for item in marker.files}
    actual_files: set[str] = set()
    for path in bundle_path.rglob("*"):
        if path.is_symlink():
            raise ArtifactValidationError("bundle contains a symlink")
        if path.is_file():
            actual_files.add(path.relative_to(bundle_path).as_posix())
    expected_with_marker = set(expected_files) | {"bundle.json"}
    if actual_files != expected_with_marker:
        missing = sorted(expected_with_marker - actual_files)
        extra = sorted(actual_files - expected_with_marker)
        raise ArtifactValidationError(
            f"bundle file set mismatch; missing={missing}, extra={extra}"
        )
    for relative_path, file_manifest in expected_files.items():
        observed = _manifest_for_file(bundle_path, relative_path)
        if observed != file_manifest:
            raise ArtifactValidationError(f"artifact hash mismatch: {relative_path}")

    config = RunConfigRecord.from_dict(_load_canonical_json(bundle_path / "config.json"))
    result = RunResultRecord.from_dict(_load_canonical_json(bundle_path / "result.json"))
    if config.identity != identity or result.identity != identity:
        raise _ArtifactIdentityConflict("bundle records belong to another run")
    if config.source != result.source or config.environment != result.environment:
        raise ArtifactValidationError("config and result metadata disagree")
    prediction_file = result.predictions.to_file_manifest()
    if expected_files.get(prediction_file.path) != prediction_file:
        raise ArtifactValidationError("prediction manifest is absent from bundle index")
    validate_prediction_manifest(
        bundle_path, result.predictions, expected_run_id=identity.run_id
    )


class ResumeState(str, Enum):
    MATCHING_COMPLETE = "matching-complete"
    PARTIAL = "partial"
    CORRUPT = "corrupt"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class ResumeDecision:
    state: ResumeState
    path: Path
    reason: str
    recoverable: bool = False


def classify_resume(
    identity: RunIdentity, *, repository_root: str | Path
) -> ResumeDecision | None:
    """Classify existing state; ``None`` means that no prior state exists."""

    final_path = canonical_run_bundle_path(identity, repository_root=repository_root)
    slot_path = _canonical_run_slot_path(identity, repository_root=repository_root)

    if slot_path.exists():
        siblings = sorted(
            child
            for child in slot_path.iterdir()
            if child.name.startswith("run=") and child != final_path
        )
        if siblings:
            return ResumeDecision(
                ResumeState.CONFLICT,
                siblings[0],
                "logical run slot contains a different run identity",
            )

    if final_path.exists() or final_path.is_symlink():
        if not final_path.is_dir() or not (final_path / "bundle.json").exists():
            return ResumeDecision(
                ResumeState.PARTIAL,
                final_path,
                "final run path exists without a complete bundle marker",
            )
        try:
            _validate_bundle_directory(final_path, identity)
        except _ArtifactIdentityConflict as exc:
            return ResumeDecision(ResumeState.CONFLICT, final_path, str(exc))
        except (ArtifactValidationError, OSError) as exc:
            return ResumeDecision(ResumeState.CORRUPT, final_path, str(exc))
        return ResumeDecision(
            ResumeState.MATCHING_COMPLETE,
            final_path,
            "bundle identity and all required file hashes match",
        )

    staging_root = _staging_root(repository_root=repository_root)
    if staging_root.exists():
        staged = sorted(staging_root.glob(f"run={identity.run_id}.*"))
        if staged:
            return ResumeDecision(
                ResumeState.PARTIAL,
                staged[0],
                "an interrupted staging bundle exists",
            )
    if slot_path.exists() and any(slot_path.iterdir()):
        return ResumeDecision(
            ResumeState.PARTIAL,
            slot_path,
            "logical run slot contains uncommitted state",
        )

    failure_dir = _failure_directory(identity, repository_root=repository_root)
    if failure_dir.exists() and any(failure_dir.glob("failure=*.json")):
        return ResumeDecision(
            ResumeState.PARTIAL,
            failure_dir,
            "prior failure records exist but no completed bundle exists",
            recoverable=True,
        )
    if slot_path.exists():
        return ResumeDecision(
            ResumeState.PARTIAL,
            slot_path,
            "an empty logical run slot remains from an interrupted attempt",
        )
    return None


def _write_exclusive_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    descriptor = os.open(path, flags, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        raise


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


class AtomicRunBundle:
    """Stage a run privately and expose it only through one directory rename."""

    def __init__(
        self,
        config: RunConfigRecord,
        *,
        repository_root: str | Path,
    ) -> None:
        self.config = config
        self.repository_root = Path(repository_root).resolve(strict=True)
        decision = classify_resume(config.identity, repository_root=self.repository_root)
        if decision is not None:
            if decision.state is ResumeState.MATCHING_COMPLETE:
                raise FileExistsError(decision.path)
            if decision.state is ResumeState.CONFLICT:
                raise ArtifactConflictError(decision.reason)
            if not (decision.state is ResumeState.PARTIAL and decision.recoverable):
                raise ArtifactStateError(decision)

        self.final_path = canonical_run_bundle_path(
            config.identity, repository_root=self.repository_root
        )
        staging_root = _staging_root(repository_root=self.repository_root)
        staging_root.mkdir(parents=True, exist_ok=True)
        self.staging_path = Path(
            tempfile.mkdtemp(
                prefix=f"run={config.identity.run_id}.", dir=staging_root
            )
        ).resolve(strict=True)
        if not _is_within(self.staging_path, staging_root.resolve(strict=True)):
            raise ArtifactValidationError("temporary bundle escaped staging root")
        self._files: dict[str, ArtifactFileManifest] = {}
        self._committed = False
        self._write_managed("config.json", canonical_json_bytes(config.to_dict()))

    def _ensure_open(self) -> None:
        if self._committed:
            raise RuntimeError("run bundle is already committed")

    def _write_managed(self, relative_path: str, payload: bytes) -> ArtifactFileManifest:
        self._ensure_open()
        safe = _safe_relative_path(relative_path, "artifact path")
        normalized = safe.as_posix()
        if normalized in self._files:
            raise FileExistsError(normalized)
        target = self.staging_path.joinpath(*safe.parts)
        unresolved_parent = target.parent.resolve(strict=False)
        if not _is_within(unresolved_parent, self.staging_path):
            raise ArtifactValidationError("artifact parent escapes staging bundle")
        _write_exclusive_bytes(target, payload)
        manifest = ArtifactFileManifest(
            path=normalized,
            sha256=hashlib.sha256(payload).hexdigest(),
            size_bytes=len(payload),
        )
        self._files[normalized] = manifest
        return manifest

    def write_bytes(
        self, relative_path: str, payload: bytes | bytearray | memoryview
    ) -> ArtifactFileManifest:
        """Create one non-reserved artifact exactly once in the staging bundle."""

        normalized = _safe_relative_path(relative_path, "artifact path").as_posix()
        if normalized in _RESERVED_BUNDLE_FILES:
            raise ArtifactValidationError(f"reserved bundle file: {normalized}")
        if not isinstance(payload, (bytes, bytearray, memoryview)):
            raise TypeError("payload must be bytes-like")
        return self._write_managed(normalized, bytes(payload))

    def write_json(self, relative_path: str, value: Any) -> ArtifactFileManifest:
        return self.write_bytes(relative_path, canonical_json_bytes(value))

    def copy_file(
        self, relative_path: str, source_path: str | Path
    ) -> ArtifactFileManifest:
        """Copy one regular source file while computing its immutable manifest."""

        self._ensure_open()
        normalized = _safe_relative_path(relative_path, "artifact path").as_posix()
        if normalized in _RESERVED_BUNDLE_FILES:
            raise ArtifactValidationError(f"reserved bundle file: {normalized}")
        if normalized in self._files:
            raise FileExistsError(normalized)
        source = Path(source_path)
        if source.is_symlink() or not source.is_file():
            raise ArtifactValidationError("copy source must be a regular file")
        target = self.staging_path.joinpath(*PurePosixPath(normalized).parts)
        unresolved_parent = target.parent.resolve(strict=False)
        if not _is_within(unresolved_parent, self.staging_path):
            raise ArtifactValidationError("artifact parent escapes staging bundle")
        target.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        descriptor = os.open(target, flags, 0o644)
        digest = hashlib.sha256()
        size = 0
        with source.open("rb") as input_stream, os.fdopen(descriptor, "wb") as output:
            while chunk := input_stream.read(1024 * 1024):
                output.write(chunk)
                digest.update(chunk)
                size += len(chunk)
            output.flush()
            os.fsync(output.fileno())
        manifest = ArtifactFileManifest(
            path=normalized, sha256=digest.hexdigest(), size_bytes=size
        )
        self._files[normalized] = manifest
        return manifest

    def commit(self, result: RunResultRecord) -> Path:
        """Validate and atomically rename one complete bundle into ``raw/``."""

        self._ensure_open()
        if result.identity != self.config.identity:
            raise ArtifactConflictError("result identity differs from config identity")
        if result.source != self.config.source or result.environment != self.config.environment:
            raise ArtifactValidationError("result metadata differs from config metadata")
        prediction_file = result.predictions.to_file_manifest()
        if self._files.get(prediction_file.path) != prediction_file:
            raise ArtifactValidationError(
                "required prediction file is absent, changed, or bound incorrectly"
            )
        validate_prediction_manifest(
            self.staging_path,
            result.predictions,
            expected_run_id=self.config.identity.run_id,
        )
        self._write_managed("result.json", canonical_json_bytes(result.to_dict()))
        marker = BundleManifest(
            run_id=self.config.identity.run_id,
            files=tuple(self._files.values()),
            created_at_utc=utc_now_iso(),
        )
        _write_exclusive_bytes(
            self.staging_path / "bundle.json", canonical_json_bytes(marker.to_dict())
        )
        _fsync_directory(self.staging_path)
        _validate_bundle_directory(self.staging_path, self.config.identity)

        slot_path = _canonical_run_slot_path(
            self.config.identity, repository_root=self.repository_root
        )
        slot_path.mkdir(parents=True, exist_ok=True)
        commit_claim = slot_path / ".bundle-commit.lock"
        _write_exclusive_bytes(
            commit_claim, self.config.identity.run_id.encode("ascii")
        )
        try:
            siblings = [
                child
                for child in slot_path.iterdir()
                if child.name.startswith("run=") and child != self.final_path
            ]
            if siblings:
                raise ArtifactConflictError(
                    "logical run slot gained a different identity during bundle creation"
                )
            if self.final_path.exists() or self.final_path.is_symlink():
                raise FileExistsError(self.final_path)
            try:
                os.rename(self.staging_path, self.final_path)
            except OSError as exc:
                if self.final_path.exists() or self.final_path.is_symlink():
                    raise FileExistsError(self.final_path) from exc
                raise
        finally:
            try:
                commit_claim.unlink()
            except FileNotFoundError:
                pass
        _fsync_directory(self.final_path.parent)
        self._committed = True
        _validate_bundle_directory(self.final_path, self.config.identity)
        return self.final_path


__all__ = [
    "ArtifactConflictError",
    "ArtifactFileManifest",
    "ArtifactStateError",
    "ArtifactValidationError",
    "AtomicRunBundle",
    "BundleManifest",
    "DirtySourceError",
    "EnvironmentMetadata",
    "FailureRecord",
    "NA_ID",
    "PredictionArtifactManifest",
    "ResumeDecision",
    "ResumeState",
    "RunConfigRecord",
    "RunIdentity",
    "RunMode",
    "RunResultRecord",
    "SCHEMA_VERSION",
    "canonical_json_bytes",
    "canonical_json_sha256",
    "canonical_run_bundle_path",
    "capture_environment_metadata",
    "capture_source_metadata",
    "classify_resume",
    "load_failure_record",
    "run_bundle_relative_path",
    "run_slot_relative_path",
    "sha256_file",
    "utc_now_iso",
    "validate_prediction_manifest",
    "verify_file_sha256",
    "write_failure_record",
]
