from __future__ import annotations

import copy
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gbdn.artifacts import (  # noqa: E402
    ArtifactConflictError,
    ArtifactStateError,
    ArtifactValidationError,
    AtomicRunBundle,
    DirtySourceError,
    EnvironmentMetadata,
    FailureRecord,
    NA_ID,
    PredictionArtifactManifest,
    ResumeState,
    RunConfigRecord,
    RunIdentity,
    RunMode,
    RunResultRecord,
    SCHEMA_VERSION,
    SourceMetadata,
    canonical_json_bytes,
    canonical_json_sha256,
    canonical_run_bundle_path,
    capture_environment_metadata,
    capture_source_metadata,
    classify_resume,
    load_failure_record,
    run_slot_relative_path,
    sha256_file,
    validate_prediction_manifest,
    verify_file_sha256,
    write_failure_record,
)


FIXED_TIME = "2026-08-12T00:00:00Z"
DATASET_HASH = "1" * 64
SOURCE_HASH = "2" * 64
LOCK_HASH = "3" * 64
CONFIG = {"depth": 4, "optimizer": {"lr": 0.001, "weight_decay": 0.0}}


def _source(*, dirty: bool = False, dirty_override: bool = False) -> SourceMetadata:
    return SourceMetadata(
        repository_commit="a" * 40,
        repository_tree="b" * 40,
        source_sha256=SOURCE_HASH,
        dirty=dirty,
        dirty_fingerprint_sha256="c" * 64 if dirty else None,
        dirty_override=dirty_override,
    )


def _environment() -> EnvironmentMetadata:
    return EnvironmentMetadata(
        python_version="3.11.0",
        python_implementation="CPython",
        platform="test-platform",
        machine="test-machine",
        executable="python",
        dependency_lock_path="requirements.lock",
        dependency_lock_sha256=LOCK_HASH,
        cuda_visible_devices="0",
        cublas_workspace_config=":4096:8",
        pythonhashseed="0",
    )


def _identity(
    *,
    frozen_config: dict | None = None,
    split_id: int | str = 0,
    seed: int | str = 0,
    trial_id: int | str = 0,
    **changes,
) -> RunIdentity:
    fields = {
        "schema_version": SCHEMA_VERSION,
        "experiment": "heterophily_confirm",
        "dataset_name": "Roman-empire",
        "dataset_sha256": DATASET_HASH,
        "model_name": "TightGBDN",
        "model_variant": "tight",
        "split_id": split_id,
        "seed": seed,
        "trial_id": trial_id,
        "frozen_config_sha256": canonical_json_sha256(frozen_config or CONFIG),
        "source_sha256": SOURCE_HASH,
        "dependency_lock_sha256": LOCK_HASH,
        "baseline_upstream_commit": NA_ID,
        "precision_mode": "deterministic-fp32",
    }
    fields.update(changes)
    return RunIdentity(**fields)


def _config_record(
    identity: RunIdentity,
    *,
    frozen_config: dict | None = None,
    source: SourceMetadata | None = None,
    environment: EnvironmentMetadata | None = None,
    run_mode: str = "full",
) -> RunConfigRecord:
    return RunConfigRecord.create(
        identity=identity,
        frozen_config=frozen_config or CONFIG,
        source=source or _source(),
        environment=environment or _environment(),
        run_mode=run_mode,
        created_at_utc=FIXED_TIME,
    )


def _result_record(
    identity: RunIdentity,
    prediction: PredictionArtifactManifest,
    *,
    source: SourceMetadata | None = None,
    environment: EnvironmentMetadata | None = None,
) -> RunResultRecord:
    return RunResultRecord.create(
        identity=identity,
        predictions=prediction,
        result_payload={"compute": {}, "diagnostics": {}, "metrics": {}},
        source=source or _source(),
        environment=environment or _environment(),
        created_at_utc=FIXED_TIME,
    )


def _commit_bundle(
    repository_root: Path,
    *,
    identity: RunIdentity | None = None,
    frozen_config: dict | None = None,
    prediction_bytes: bytes = b"fake-npz-predictions",
):
    identity = identity or _identity(frozen_config=frozen_config)
    config = _config_record(identity, frozen_config=frozen_config)
    bundle = AtomicRunBundle(config, repository_root=repository_root)
    file_manifest = bundle.write_bytes("predictions.npz", prediction_bytes)
    prediction = PredictionArtifactManifest.from_file_manifest(
        identity.run_id,
        file_manifest,
        format="logits_and_labels",
    )
    result = _result_record(identity, prediction)
    final = bundle.commit(result)
    return identity, config, result, final


def test_canonical_json_is_deterministic_under_key_order():
    first = {"z": [3, 2, 1], "a": {"right": 2, "left": 1}}
    second = {"a": {"left": 1, "right": 2}, "z": (3, 2, 1)}

    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert canonical_json_sha256(first) == canonical_json_sha256(second)
    assert canonical_json_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}'


@pytest.mark.parametrize("invalid", ({1: "not-a-string-key"}, {"x": float("nan")}, {"x": {1, 2}}))
def test_canonical_json_rejects_ambiguous_or_nonfinite_values(invalid):
    with pytest.raises((TypeError, ValueError)):
        canonical_json_bytes(invalid)


def test_every_frozen_identity_field_changes_the_hash():
    identity = _identity()
    baseline = identity.run_id
    mutations = {
        "schema_version": lambda value: value.__setitem__("schema_version", "1.1"),
        "experiment": lambda value: value.__setitem__("experiment", "mechanism"),
        "dataset_name": lambda value: value["dataset"].__setitem__("name", "Other"),
        "dataset_sha256": lambda value: value["dataset"].__setitem__("sha256", "4" * 64),
        "model_name": lambda value: value["model"].__setitem__("name", "ProductSum"),
        "model_variant": lambda value: value["model"].__setitem__("variant", "product-sum"),
        "split": lambda value: value.__setitem__("split", 1),
        "seed": lambda value: value.__setitem__("seed", 1),
        "trial": lambda value: value.__setitem__("trial", 1),
        "frozen_config_sha256": lambda value: value.__setitem__("frozen_config_sha256", "5" * 64),
        "source_sha256": lambda value: value.__setitem__("source_sha256", "6" * 64),
        "dependency_lock_sha256": lambda value: value.__setitem__(
            "dependency_lock_sha256", "7" * 64
        ),
        "baseline_upstream_commit": lambda value: value.__setitem__(
            "baseline_upstream_commit", "d" * 40
        ),
        "precision_mode": lambda value: value.__setitem__("precision_mode", "bf16"),
    }

    for field, mutate in mutations.items():
        changed = copy.deepcopy(identity.to_dict())
        mutate(changed)
        assert canonical_json_sha256(changed) != baseline, field


def test_identity_and_records_round_trip_without_order_dependence():
    identity = _identity()
    config = _config_record(identity)
    prediction = PredictionArtifactManifest(
        run_id=identity.run_id,
        path="predictions.npz",
        sha256="8" * 64,
        size_bytes=10,
        format="logits_and_labels",
    )
    result = _result_record(identity, prediction)

    assert RunIdentity.from_dict(identity.to_dict()) == identity
    assert RunConfigRecord.from_dict(config.to_dict()) == config
    assert RunResultRecord.from_dict(result.to_dict()) == result


def test_config_record_rejects_hash_and_dirty_full_run_mismatch():
    identity = _identity()
    with pytest.raises(ArtifactValidationError, match="frozen config"):
        _config_record(identity, frozen_config={"different": True})

    dirty = _source(dirty=True)
    with pytest.raises(DirtySourceError, match="override"):
        _config_record(identity, source=dirty, run_mode="full")

    pilot = _config_record(identity, source=dirty, run_mode="pilot")
    assert pilot.source.dirty and not pilot.source.dirty_override
    assert pilot.run_mode is RunMode.PILOT

    with pytest.raises(ArtifactValidationError, match="unsupported run_mode"):
        _config_record(identity, source=dirty, run_mode="FULL")


def test_prediction_manifest_cannot_alias_a_reserved_bundle_file():
    identity = _identity()
    with pytest.raises(ArtifactValidationError, match="predictions.npz"):
        PredictionArtifactManifest(
            run_id=identity.run_id,
            path="config.json",
            sha256="8" * 64,
            size_bytes=10,
            format="logits_and_labels",
        )


def test_explicit_na_identity_has_explicit_safe_path(tmp_path):
    identity = _identity(split_id=NA_ID, seed=NA_ID, trial_id=NA_ID)
    path = run_slot_relative_path(identity)

    assert "split=na" in path.parts
    assert "seed=na" in path.parts
    assert "trial=na" in path.parts
    assert canonical_run_bundle_path(identity, repository_root=tmp_path).is_relative_to(
        (tmp_path / "results_submission").resolve()
    )


def test_identity_labels_cannot_escape_canonical_path(tmp_path):
    identity = _identity(
        experiment="..",
        dataset_name="../outside",
        model_name="nested/model",
    )
    path = canonical_run_bundle_path(identity, repository_root=tmp_path)

    assert path.is_relative_to((tmp_path / "results_submission").resolve())
    assert "experiment=.." in path.parts
    assert not (tmp_path / "outside").exists()


def test_atomic_bundle_commit_and_safe_matching_resume(tmp_path):
    identity, config, result, final = _commit_bundle(tmp_path)

    assert final == canonical_run_bundle_path(identity, repository_root=tmp_path)
    assert {path.name for path in final.iterdir()} == {
        "bundle.json",
        "config.json",
        "predictions.npz",
        "result.json",
    }
    decision = classify_resume(identity, repository_root=tmp_path)
    assert decision is not None
    assert decision.state is ResumeState.MATCHING_COMPLETE
    assert not decision.recoverable
    with pytest.raises(FileExistsError):
        AtomicRunBundle(config, repository_root=tmp_path)

    validate_prediction_manifest(
        final,
        result.predictions,
        expected_run_id=identity.run_id,
    )


def test_different_identity_in_same_slot_is_conflict(tmp_path):
    _commit_bundle(tmp_path)
    changed_config = {"depth": 8}
    changed = _identity(frozen_config=changed_config)

    decision = classify_resume(changed, repository_root=tmp_path)
    assert decision is not None
    assert decision.state is ResumeState.CONFLICT
    with pytest.raises(ArtifactConflictError):
        AtomicRunBundle(
            _config_record(changed, frozen_config=changed_config),
            repository_root=tmp_path,
        )


def test_interrupted_staging_bundle_is_partial_and_never_complete(tmp_path):
    identity = _identity()
    config = _config_record(identity)
    first = AtomicRunBundle(config, repository_root=tmp_path)

    assert first.staging_path.exists()
    assert not canonical_run_bundle_path(identity, repository_root=tmp_path).exists()
    decision = classify_resume(identity, repository_root=tmp_path)
    assert decision is not None
    assert decision.state is ResumeState.PARTIAL
    assert not decision.recoverable
    with pytest.raises(ArtifactStateError):
        AtomicRunBundle(config, repository_root=tmp_path)

def test_final_directory_without_commit_marker_is_partial(tmp_path):
    identity = _identity()
    final = canonical_run_bundle_path(identity, repository_root=tmp_path)
    final.mkdir(parents=True)
    (final / "result.json").write_bytes(b"{}")

    decision = classify_resume(identity, repository_root=tmp_path)
    assert decision is not None
    assert decision.state is ResumeState.PARTIAL


@pytest.mark.parametrize("tamper_target", ("result.json", "predictions.npz"))
def test_tampered_result_or_prediction_is_corrupt(tmp_path, tamper_target):
    identity, _, _, final = _commit_bundle(tmp_path)
    target = final / tamper_target
    target.write_bytes(target.read_bytes() + b"tampered")

    decision = classify_resume(identity, repository_root=tmp_path)
    assert decision is not None
    assert decision.state is ResumeState.CORRUPT


def test_missing_prediction_is_corrupt(tmp_path):
    identity, _, _, final = _commit_bundle(tmp_path)
    (final / "predictions.npz").unlink()

    decision = classify_resume(identity, repository_root=tmp_path)
    assert decision is not None
    assert decision.state is ResumeState.CORRUPT


def test_bundle_commit_refuses_missing_predictions(tmp_path):
    identity = _identity()
    bundle = AtomicRunBundle(_config_record(identity), repository_root=tmp_path)
    missing = PredictionArtifactManifest(
        run_id=identity.run_id,
        path="predictions.npz",
        sha256="9" * 64,
        size_bytes=1,
        format="logits_and_labels",
    )

    with pytest.raises(ArtifactValidationError, match="prediction file"):
        bundle.commit(_result_record(identity, missing))
    assert not canonical_run_bundle_path(identity, repository_root=tmp_path).exists()


def test_bundle_commit_uses_exclusive_slot_claim(tmp_path):
    identity = _identity()
    bundle = AtomicRunBundle(_config_record(identity), repository_root=tmp_path)
    file_manifest = bundle.write_bytes("predictions.npz", b"predictions")
    prediction = PredictionArtifactManifest.from_file_manifest(
        identity.run_id, file_manifest, format="logits_and_labels"
    )
    slot = tmp_path / run_slot_relative_path(identity)
    slot.mkdir(parents=True)
    (slot / ".bundle-commit.lock").write_bytes(b"other writer")

    with pytest.raises(FileExistsError):
        bundle.commit(_result_record(identity, prediction))
    assert not canonical_run_bundle_path(identity, repository_root=tmp_path).exists()


def test_prediction_manifest_enforces_identity_binding(tmp_path):
    identity, _, result, final = _commit_bundle(tmp_path)
    other = replace(identity, seed=1)

    with pytest.raises(ArtifactValidationError, match="another run"):
        validate_prediction_manifest(
            final,
            result.predictions,
            expected_run_id=other.run_id,
        )


def test_file_sha256_verification_detects_tampering(tmp_path):
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"original")
    digest = sha256_file(path)
    assert verify_file_sha256(path, digest)

    path.write_bytes(b"changed")
    assert not verify_file_sha256(path, digest)


def test_failure_artifact_is_typed_immutable_and_recoverable(tmp_path):
    identity = _identity()
    record = FailureRecord(
        identity=identity,
        exception_type="RuntimeError",
        message="synthetic failure",
        traceback_path="logs/traceback.txt",
        partial_artifacts=("history.jsonl",),
        source=_source(),
        environment=_environment(),
        created_at_utc=FIXED_TIME,
    )
    path = write_failure_record(record, repository_root=tmp_path)

    assert load_failure_record(path) == record
    with pytest.raises(FileExistsError):
        write_failure_record(record, repository_root=tmp_path)
    decision = classify_resume(identity, repository_root=tmp_path)
    assert decision is not None
    assert decision.state is ResumeState.PARTIAL
    assert decision.recoverable

    bundle = AtomicRunBundle(_config_record(identity), repository_root=tmp_path)
    assert bundle.staging_path.exists()


def test_failure_record_rejects_unsafe_traceback_path():
    identity = _identity()
    with pytest.raises(ArtifactValidationError, match="unsafe"):
        FailureRecord(
            identity=identity,
            exception_type="RuntimeError",
            message="failure",
            traceback_path="../traceback.txt",
            partial_artifacts=(),
            source=_source(),
            environment=_environment(),
            created_at_utc=FIXED_TIME,
        )


def _git(repository: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_source_metadata_rejects_dirty_full_run_and_records_override(tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init")
    _git(repository, "config", "user.email", "test@example.com")
    _git(repository, "config", "user.name", "Test User")
    tracked = repository / "source.py"
    tracked.write_text("value = 1\n", encoding="utf-8")
    _git(repository, "add", "source.py")
    _git(repository, "commit", "-m", "initial")

    clean = capture_source_metadata(repository, full_run=True)
    assert not clean.dirty
    assert clean.dirty_fingerprint_sha256 is None

    tracked.write_text("value = 2\n", encoding="utf-8")
    with pytest.raises(DirtySourceError, match="clean Git tree"):
        capture_source_metadata(repository, full_run=True)

    dirty = capture_source_metadata(repository, full_run=True, allow_dirty=True)
    assert dirty.dirty and dirty.dirty_override
    assert dirty.source_sha256 != clean.source_sha256

    tracked.write_text("value = 3\n", encoding="utf-8")
    changed = capture_source_metadata(repository, full_run=False)
    assert changed.dirty and not changed.dirty_override
    assert changed.dirty_fingerprint_sha256 != dirty.dirty_fingerprint_sha256


def test_environment_metadata_requires_and_hashes_dependency_lock(tmp_path):
    lock = tmp_path / "requirements.lock"
    lock.write_text("package==1.0\n", encoding="utf-8")
    metadata = capture_environment_metadata(lock, repository_root=tmp_path)

    assert metadata.dependency_lock_path == "requirements.lock"
    assert metadata.dependency_lock_sha256 == sha256_file(lock)
    with pytest.raises(FileNotFoundError):
        capture_environment_metadata(tmp_path / "missing.lock")
