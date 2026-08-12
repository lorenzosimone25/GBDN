from __future__ import annotations

import copy
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gbdn.artifacts import (  # noqa: E402
    ArtifactFileManifest,
    ArtifactValidationError,
    AtomicRunBundle,
    EnvironmentMetadata,
    NA_ID,
    PredictionArtifactManifest,
    ResumeState,
    RunConfigRecord,
    RunIdentity,
    RunResultRecord,
    SCHEMA_VERSION,
    SourceMetadata,
    TIGHT_ANALYSIS_MANIFEST_PATH,
    TIGHT_ANALYSIS_PAYLOAD_PATH,
    canonical_json_sha256,
    classify_resume,
)
from gbdn.coefficient_artifacts import (  # noqa: E402
    TightAnalysisArtifactManifest,
    load_tight_analysis_artifact,
    write_tight_analysis_artifact,
)
from gbdn.model import TightAnalysisOutput  # noqa: E402


FIXED_TIME = "2026-08-12T00:00:00Z"
CONFIG = {"depth": 2, "realization": "chebyshev-8"}
DATASET_HASH = "1" * 64
SOURCE_HASH = "2" * 64
LOCK_HASH = "3" * 64


def _source() -> SourceMetadata:
    return SourceMetadata(
        repository_commit="a" * 40,
        repository_tree="b" * 40,
        source_sha256=SOURCE_HASH,
        dirty=False,
        dirty_fingerprint_sha256=None,
        dirty_override=False,
    )


def _environment() -> EnvironmentMetadata:
    return EnvironmentMetadata(
        python_version="3.14.0",
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


def _identity() -> RunIdentity:
    return RunIdentity(
        schema_version=SCHEMA_VERSION,
        experiment="r3_serialization",
        dataset_name="synthetic-path",
        dataset_sha256=DATASET_HASH,
        model_name="TightGBDN",
        model_variant="tight",
        split_id=0,
        seed=0,
        trial_id=0,
        frozen_config_sha256=canonical_json_sha256(CONFIG),
        source_sha256=SOURCE_HASH,
        dependency_lock_sha256=LOCK_HASH,
        baseline_upstream_commit=NA_ID,
        precision_mode="deterministic-fp64",
    )


def _config() -> RunConfigRecord:
    return RunConfigRecord.create(
        identity=_identity(),
        frozen_config=CONFIG,
        source=_source(),
        environment=_environment(),
        run_mode="full",
        created_at_utc=FIXED_TIME,
    )


def _analysis(dtype: torch.dtype = torch.complex128) -> TightAnalysisOutput:
    real = torch.arange(6, dtype=torch.float64).reshape(2, 3).transpose(0, 1)
    imag = torch.flip(real, dims=(0,)) + 0.25
    base = torch.complex(real, imag).to(dtype=dtype)
    bands = [base + (1.0 + 2.0j), base * (-0.5 + 0.25j)]
    carry = base - (3.0 - 1.5j)
    roots = [
        torch.tensor([0.2 + 0.3j, -0.4 + 0.1j], dtype=dtype),
        torch.tensor([0.65 - 0.2j, 0.1 + 0.05j], dtype=dtype),
    ]
    assert not base.is_contiguous()
    return TightAnalysisOutput(bands=bands, final_carry=carry, roots=roots)


def _open_bundle(tmp_path: Path):
    config = _config()
    bundle = AtomicRunBundle(config, repository_root=tmp_path)
    prediction_file = bundle.write_bytes("predictions.npz", b"immutable-predictions")
    prediction = PredictionArtifactManifest.from_file_manifest(
        config.identity.run_id,
        prediction_file,
        format="logits_and_labels",
    )
    return config, bundle, prediction_file, prediction


def _commit(
    bundle: AtomicRunBundle,
    config: RunConfigRecord,
    prediction: PredictionArtifactManifest,
) -> Path:
    result = RunResultRecord.create(
        identity=config.identity,
        predictions=prediction,
        result_payload={"metrics": {}, "diagnostics": {}},
        source=config.source,
        environment=config.environment,
        created_at_utc=FIXED_TIME,
    )
    return bundle.commit(result)


@pytest.mark.parametrize("dtype", (torch.complex64, torch.complex128))
def test_residual_first_complex_round_trip_is_exact_and_fully_bound(tmp_path, dtype):
    config, bundle, prediction_file, prediction = _open_bundle(tmp_path)
    original = _analysis(dtype)
    record = write_tight_analysis_artifact(
        bundle,
        original,
        bind_artifacts=(prediction_file,),
    )
    final = _commit(bundle, config, prediction)

    restored, loaded_record = load_tight_analysis_artifact(
        final,
        expected_config=config,
    )
    assert loaded_record == record
    assert restored.component_names == ("r_0", "r_1", "h_D")
    assert loaded_record.component_order == restored.component_names
    assert loaded_record.depth == 2
    assert loaded_record.root_order == ("alpha_0", "alpha_1")
    assert loaded_record.bound_artifacts == (prediction_file,)
    assert loaded_record.binding.run_id == config.identity.run_id
    assert loaded_record.binding.frozen_config_sha256 == config.identity.frozen_config_sha256
    assert loaded_record.binding.source_sha256 == config.source.source_sha256
    assert (
        loaded_record.binding.dependency_lock_sha256
        == config.environment.dependency_lock_sha256
    )
    assert loaded_record.binding.source_record_sha256 == canonical_json_sha256(
        config.source.to_dict()
    )
    assert loaded_record.binding.environment_sha256 == canonical_json_sha256(
        config.environment.to_dict()
    )
    assert all(item.dtype == str(dtype).removeprefix("torch.") for item in record.components)
    assert all(item.shape == (3, 2) for item in record.components)
    assert all(item.source_device == "cpu" for item in (*record.components, *record.roots))

    for expected, observed in zip(original.components, restored.components, strict=True):
        assert observed.dtype == expected.dtype
        assert observed.shape == expected.shape
        assert torch.equal(observed, expected)
    for expected, observed in zip(original.roots, restored.roots, strict=True):
        assert observed.dtype == expected.dtype
        assert observed.shape == expected.shape
        assert torch.equal(observed, expected)

    assert {path.relative_to(final).as_posix() for path in final.rglob("*") if path.is_file()} == {
        "analysis/tight_coefficients.bin",
        "analysis/tight_coefficients.json",
        "bundle.json",
        "config.json",
        "predictions.npz",
        "result.json",
    }
    decision = classify_resume(config.identity, repository_root=tmp_path)
    assert decision is not None and decision.state is ResumeState.MATCHING_COMPLETE


def test_manifest_rejects_component_permutation_dtype_shape_and_path_tampering(tmp_path):
    _, bundle, prediction_file, _ = _open_bundle(tmp_path)
    record = write_tight_analysis_artifact(
        bundle,
        _analysis(torch.complex64),
        bind_artifacts=(prediction_file,),
    )

    carry_first = copy.deepcopy(record.to_dict())
    carry_first["component_order"] = ["h_D", "r_0", "r_1"]
    with pytest.raises(ArtifactValidationError, match="residual-first"):
        TightAnalysisArtifactManifest.from_dict(carry_first)

    permuted_descriptors = copy.deepcopy(record.to_dict())
    components = permuted_descriptors["components"]
    components[0], components[-1] = components[-1], components[0]
    with pytest.raises(ArtifactValidationError, match="descriptors"):
        TightAnalysisArtifactManifest.from_dict(permuted_descriptors)

    changed_dtype = copy.deepcopy(record.to_dict())
    changed_dtype["components"][0]["dtype"] = "complex128"
    with pytest.raises(ArtifactValidationError, match="shape and dtype"):
        TightAnalysisArtifactManifest.from_dict(changed_dtype)

    changed_shape = copy.deepcopy(record.to_dict())
    changed_shape["components"][0]["shape"] = [999, 2]
    with pytest.raises(ArtifactValidationError, match="shape and dtype"):
        TightAnalysisArtifactManifest.from_dict(changed_shape)

    escaped_payload = copy.deepcopy(record.to_dict())
    escaped_payload["payload"]["path"] = "../tight_coefficients.bin"
    with pytest.raises(ArtifactValidationError, match="unsafe"):
        TightAnalysisArtifactManifest.from_dict(escaped_payload)


@pytest.mark.parametrize("mutation", ("flip", "truncate", "append"))
def test_payload_tampering_and_truncation_are_corrupt(tmp_path, mutation):
    config, bundle, prediction_file, prediction = _open_bundle(tmp_path)
    write_tight_analysis_artifact(
        bundle,
        _analysis(),
        bind_artifacts=(prediction_file,),
    )
    final = _commit(bundle, config, prediction)
    payload_path = final / TIGHT_ANALYSIS_PAYLOAD_PATH
    payload = payload_path.read_bytes()
    if mutation == "flip":
        payload = bytes([payload[0] ^ 1]) + payload[1:]
    elif mutation == "truncate":
        payload = payload[:-1]
    else:
        payload = payload + b"x"
    payload_path.write_bytes(payload)

    decision = classify_resume(config.identity, repository_root=tmp_path)
    assert decision is not None and decision.state is ResumeState.CORRUPT
    with pytest.raises(ArtifactValidationError):
        load_tight_analysis_artifact(final, expected_config=config)


def test_manifest_tampering_is_corrupt_even_when_json_remains_canonical(tmp_path):
    config, bundle, prediction_file, prediction = _open_bundle(tmp_path)
    write_tight_analysis_artifact(
        bundle,
        _analysis(),
        bind_artifacts=(prediction_file,),
    )
    final = _commit(bundle, config, prediction)
    manifest_path = final / TIGHT_ANALYSIS_MANIFEST_PATH
    payload = manifest_path.read_bytes().replace(b'"r_0"', b'"x_0"')
    manifest_path.write_bytes(payload)

    decision = classify_resume(config.identity, repository_root=tmp_path)
    assert decision is not None and decision.state is ResumeState.CORRUPT
    with pytest.raises(ArtifactValidationError):
        load_tight_analysis_artifact(final, expected_config=config)


def test_writer_rejects_unmanaged_or_changed_binding_before_writing(tmp_path):
    _, bundle, prediction_file, _ = _open_bundle(tmp_path)
    forged = replace(prediction_file, sha256="f" * 64)

    with pytest.raises(ArtifactValidationError, match="unmanaged"):
        write_tight_analysis_artifact(
            bundle,
            _analysis(),
            bind_artifacts=(forged,),
        )
    assert not (bundle.staging_path / TIGHT_ANALYSIS_PAYLOAD_PATH).exists()
    assert not (bundle.staging_path / TIGHT_ANALYSIS_MANIFEST_PATH).exists()

    with pytest.raises(ArtifactValidationError, match="at least one"):
        write_tight_analysis_artifact(bundle, _analysis(), bind_artifacts=())


def test_fixed_paths_are_write_once_and_preserve_first_payload(tmp_path):
    config, bundle, prediction_file, prediction = _open_bundle(tmp_path)
    first = write_tight_analysis_artifact(
        bundle,
        _analysis(),
        bind_artifacts=(prediction_file,),
    )
    first_bytes = (bundle.staging_path / TIGHT_ANALYSIS_PAYLOAD_PATH).read_bytes()

    with pytest.raises(FileExistsError):
        write_tight_analysis_artifact(
            bundle,
            _analysis(torch.complex64),
            bind_artifacts=(prediction_file,),
        )
    assert (bundle.staging_path / TIGHT_ANALYSIS_PAYLOAD_PATH).read_bytes() == first_bytes
    assert first.payload.path == TIGHT_ANALYSIS_PAYLOAD_PATH
    assert first.payload.size_bytes == len(first_bytes)
    final = _commit(bundle, config, prediction)
    assert final.exists()


def test_competing_coefficient_writers_have_exactly_one_winner(tmp_path):
    config, bundle, prediction_file, prediction = _open_bundle(tmp_path)

    def attempt(dtype: torch.dtype):
        try:
            return write_tight_analysis_artifact(
                bundle,
                _analysis(dtype),
                bind_artifacts=(prediction_file,),
            )
        except FileExistsError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, (torch.complex64, torch.complex128)))
    winners = [item for item in outcomes if isinstance(item, TightAnalysisArtifactManifest)]
    conflicts = [item for item in outcomes if isinstance(item, FileExistsError)]
    assert len(winners) == 1
    assert len(conflicts) == 1

    final = _commit(bundle, config, prediction)
    restored, record = load_tight_analysis_artifact(final, expected_config=config)
    expected_dtype = (
        torch.complex64
        if record.components[0].dtype == "complex64"
        else torch.complex128
    )
    assert all(component.dtype == expected_dtype for component in restored.components)


def test_completed_bundle_cannot_contain_only_half_of_coefficient_pair(tmp_path):
    config, bundle, _, prediction = _open_bundle(tmp_path)
    bundle.write_bytes(TIGHT_ANALYSIS_PAYLOAD_PATH, b"orphan-payload")

    with pytest.raises(ArtifactValidationError, match="pair is incomplete"):
        _commit(bundle, config, prediction)
    assert not bundle.final_path.exists()


@pytest.mark.parametrize("field", ("config", "source", "environment"))
def test_loader_requires_exact_config_source_and_environment_binding(tmp_path, field):
    config, bundle, prediction_file, prediction = _open_bundle(tmp_path)
    write_tight_analysis_artifact(
        bundle,
        _analysis(),
        bind_artifacts=(prediction_file,),
    )
    final = _commit(bundle, config, prediction)

    if field == "config":
        expected = replace(config, created_at_utc="2026-08-12T00:00:01Z")
    elif field == "source":
        expected = replace(
            config,
            source=replace(config.source, repository_commit="c" * 40),
        )
    else:
        expected = replace(
            config,
            environment=replace(config.environment, executable="other-python"),
        )
    with pytest.raises(ArtifactValidationError, match="expected config"):
        load_tight_analysis_artifact(final, expected_config=expected)


@pytest.mark.parametrize(
    "invalid_tensor",
    (
        torch.ones((3, 2), dtype=torch.float64),
        torch.empty((0, 2), dtype=torch.complex128),
        torch.tensor([[complex(float("nan"), 0.0)]], dtype=torch.complex128),
        torch.tensor([[complex(0.0, float("inf"))]], dtype=torch.complex128),
    ),
)
def test_writer_rejects_noncomplex_empty_or_nonfinite_coefficients(
    tmp_path,
    invalid_tensor,
):
    _, bundle, prediction_file, _ = _open_bundle(tmp_path)
    valid = _analysis()
    invalid = TightAnalysisOutput(
        bands=[invalid_tensor, valid.bands[1]],
        final_carry=valid.final_carry,
        roots=valid.roots,
    )
    with pytest.raises(ArtifactValidationError):
        write_tight_analysis_artifact(
            bundle,
            invalid,
            bind_artifacts=(prediction_file,),
        )
    assert not (bundle.staging_path / TIGHT_ANALYSIS_PAYLOAD_PATH).exists()


def test_bound_artifact_manifest_is_typed_and_cannot_escape_bundle():
    with pytest.raises(ArtifactValidationError, match="unsafe"):
        ArtifactFileManifest(
            path="../predictions.npz",
            sha256="f" * 64,
            size_bytes=1,
        )
