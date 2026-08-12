"""Safe, immutable serialization for Tight GBDN analysis coefficients.

The wire order is frozen as ``(r_0, ..., r_{D-1}, h_D)``.  Tensor payloads
use an explicit little-endian raw representation rather than pickle, while a
canonical JSON manifest binds every byte range to the run, configuration,
source, environment, and already-existing bundle artifacts.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import numpy as np
import torch

from gbdn.artifacts import (
    ArtifactFileManifest,
    ArtifactValidationError,
    AtomicRunBundle,
    BundleManifest,
    RunConfigRecord,
    TIGHT_ANALYSIS_MANIFEST_PATH,
    TIGHT_ANALYSIS_PAYLOAD_PATH,
    _load_canonical_json,
    _require_exact_keys,
    _require_mapping,
    _validate_bundle_directory,
    _validate_label,
    _validate_sha256,
    canonical_json_sha256,
    validate_artifact_file_manifest,
)
from gbdn.model import TightAnalysisOutput


TIGHT_ANALYSIS_ARTIFACT_KIND: Final[str] = "gbdn.tight-analysis"
TIGHT_ANALYSIS_SCHEMA_VERSION: Final[str] = "1.0"
_DTYPE_ITEMSIZE: Final[dict[str, int]] = {
    "complex64": 8,
    "complex128": 16,
}
_TORCH_DTYPE_NAMES: Final[dict[torch.dtype, str]] = {
    torch.complex64: "complex64",
    torch.complex128: "complex128",
}
_NUMPY_DTYPES: Final[dict[str, np.dtype[Any]]] = {
    "complex64": np.dtype("<c8"),
    "complex128": np.dtype("<c16"),
}


@dataclass(frozen=True)
class TightAnalysisRunBinding:
    """Cryptographic binding to the complete immutable run context."""

    run_id: str
    identity_sha256: str
    config_record_sha256: str
    frozen_config_sha256: str
    source_sha256: str
    source_record_sha256: str
    environment_sha256: str
    dependency_lock_sha256: str

    def __post_init__(self) -> None:
        for field, value in (
            ("run_id", self.run_id),
            ("identity_sha256", self.identity_sha256),
            ("config_record_sha256", self.config_record_sha256),
            ("frozen_config_sha256", self.frozen_config_sha256),
            ("source_sha256", self.source_sha256),
            ("source_record_sha256", self.source_record_sha256),
            ("environment_sha256", self.environment_sha256),
            ("dependency_lock_sha256", self.dependency_lock_sha256),
        ):
            _validate_sha256(value, field)
        if self.identity_sha256 != self.run_id:
            raise ArtifactValidationError("identity hash must equal the canonical run_id")

    @classmethod
    def from_config(cls, config: RunConfigRecord) -> "TightAnalysisRunBinding":
        return cls(
            run_id=config.identity.run_id,
            identity_sha256=canonical_json_sha256(config.identity.to_dict()),
            config_record_sha256=canonical_json_sha256(config.to_dict()),
            frozen_config_sha256=config.identity.frozen_config_sha256,
            source_sha256=config.source.source_sha256,
            source_record_sha256=canonical_json_sha256(config.source.to_dict()),
            environment_sha256=canonical_json_sha256(config.environment.to_dict()),
            dependency_lock_sha256=config.environment.dependency_lock_sha256,
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "config_record_sha256": self.config_record_sha256,
            "dependency_lock_sha256": self.dependency_lock_sha256,
            "environment_sha256": self.environment_sha256,
            "frozen_config_sha256": self.frozen_config_sha256,
            "identity_sha256": self.identity_sha256,
            "run_id": self.run_id,
            "source_record_sha256": self.source_record_sha256,
            "source_sha256": self.source_sha256,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "TightAnalysisRunBinding":
        data = _require_mapping(value, "tight-analysis run binding")
        _require_exact_keys(
            data,
            {
                "config_record_sha256",
                "dependency_lock_sha256",
                "environment_sha256",
                "frozen_config_sha256",
                "identity_sha256",
                "run_id",
                "source_record_sha256",
                "source_sha256",
            },
            "tight-analysis run binding",
        )
        return cls(**data)


@dataclass(frozen=True)
class TensorPayloadManifest:
    """Typed description and digest of one contiguous tensor byte range."""

    name: str
    dtype: str
    byte_order: str
    shape: tuple[int, ...]
    source_device: str
    offset_bytes: int
    size_bytes: int
    sha256: str

    def __post_init__(self) -> None:
        _validate_label(self.name, "tensor name")
        if self.dtype not in _DTYPE_ITEMSIZE:
            raise ArtifactValidationError(
                f"unsupported coefficient tensor dtype: {self.dtype!r}"
            )
        if self.byte_order != "little":
            raise ArtifactValidationError("tensor byte_order must be 'little'")
        if not isinstance(self.shape, tuple):
            raise ArtifactValidationError("tensor shape must be a tuple")
        if any(type(dimension) is not int or dimension < 0 for dimension in self.shape):
            raise ArtifactValidationError("tensor shape dimensions must be nonnegative integers")
        element_count = math.prod(self.shape) if self.shape else 1
        if element_count == 0:
            raise ArtifactValidationError("empty coefficient tensors are not serializable")
        _validate_label(self.source_device, "tensor source_device")
        if type(self.offset_bytes) is not int or self.offset_bytes < 0:
            raise ArtifactValidationError("tensor offset_bytes must be nonnegative")
        expected_size = element_count * _DTYPE_ITEMSIZE[self.dtype]
        if type(self.size_bytes) is not int or self.size_bytes != expected_size:
            raise ArtifactValidationError(
                "tensor size_bytes disagrees with its shape and dtype"
            )
        _validate_sha256(self.sha256, "tensor sha256")

    def to_dict(self) -> dict[str, Any]:
        return {
            "byte_order": self.byte_order,
            "dtype": self.dtype,
            "name": self.name,
            "offset_bytes": self.offset_bytes,
            "sha256": self.sha256,
            "shape": list(self.shape),
            "size_bytes": self.size_bytes,
            "source_device": self.source_device,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "TensorPayloadManifest":
        data = _require_mapping(value, "tensor payload manifest")
        _require_exact_keys(
            data,
            {
                "byte_order",
                "dtype",
                "name",
                "offset_bytes",
                "sha256",
                "shape",
                "size_bytes",
                "source_device",
            },
            "tensor payload manifest",
        )
        shape = data["shape"]
        if not isinstance(shape, list):
            raise ArtifactValidationError("tensor shape must be a JSON list")
        return cls(
            name=data["name"],
            dtype=data["dtype"],
            byte_order=data["byte_order"],
            shape=tuple(shape),
            source_device=data["source_device"],
            offset_bytes=data["offset_bytes"],
            size_bytes=data["size_bytes"],
            sha256=data["sha256"],
        )


@dataclass(frozen=True)
class TightAnalysisArtifactManifest:
    """Semantic manifest for one residual-first Tight GBDN analysis."""

    artifact_kind: str
    schema_version: str
    binding: TightAnalysisRunBinding
    depth: int
    component_order: tuple[str, ...]
    components: tuple[TensorPayloadManifest, ...]
    root_order: tuple[str, ...]
    roots: tuple[TensorPayloadManifest, ...]
    payload: ArtifactFileManifest
    bound_artifacts: tuple[ArtifactFileManifest, ...]

    def __post_init__(self) -> None:
        if self.artifact_kind != TIGHT_ANALYSIS_ARTIFACT_KIND:
            raise ArtifactValidationError("unsupported tight-analysis artifact kind")
        if self.schema_version != TIGHT_ANALYSIS_SCHEMA_VERSION:
            raise ArtifactValidationError("unsupported tight-analysis schema version")
        if type(self.depth) is not int or self.depth < 1:
            raise ArtifactValidationError("tight-analysis depth must be a positive integer")

        expected_components = tuple(
            [f"r_{index}" for index in range(self.depth)] + ["h_D"]
        )
        expected_roots = tuple(f"alpha_{index}" for index in range(self.depth))
        if self.component_order != expected_components:
            raise ArtifactValidationError(
                "component_order is not canonical residual-first order"
            )
        if tuple(item.name for item in self.components) != expected_components:
            raise ArtifactValidationError(
                "component descriptors do not follow residual-first order"
            )
        if self.root_order != expected_roots:
            raise ArtifactValidationError("root_order does not match analysis depth")
        if tuple(item.name for item in self.roots) != expected_roots:
            raise ArtifactValidationError("root descriptors do not match root_order")

        coefficient_shapes = {item.shape for item in self.components}
        coefficient_dtypes = {item.dtype for item in self.components}
        if len(coefficient_shapes) != 1 or len(coefficient_dtypes) != 1:
            raise ArtifactValidationError(
                "all residual-first coefficients must share shape and dtype"
            )

        cursor = 0
        names: set[str] = set()
        for item in (*self.components, *self.roots):
            if item.name in names:
                raise ArtifactValidationError("tensor payload names must be unique")
            names.add(item.name)
            if item.offset_bytes != cursor:
                raise ArtifactValidationError(
                    "tensor payload ranges must be contiguous and canonical"
                )
            cursor += item.size_bytes
        if self.payload.path != TIGHT_ANALYSIS_PAYLOAD_PATH:
            raise ArtifactValidationError("unexpected tight-analysis payload path")
        if self.payload.size_bytes != cursor:
            raise ArtifactValidationError(
                "payload size disagrees with its tensor descriptor ranges"
            )

        ordered_bindings = tuple(
            sorted(self.bound_artifacts, key=lambda item: item.path)
        )
        if not ordered_bindings:
            raise ArtifactValidationError("at least one existing artifact hash is required")
        binding_paths = [item.path for item in ordered_bindings]
        if len(binding_paths) != len(set(binding_paths)):
            raise ArtifactValidationError("bound artifact paths must be unique")
        forbidden = {
            "bundle.json",
            "config.json",
            "result.json",
            TIGHT_ANALYSIS_MANIFEST_PATH,
            TIGHT_ANALYSIS_PAYLOAD_PATH,
        }
        if forbidden & set(binding_paths):
            raise ArtifactValidationError(
                "run metadata and tight-analysis files cannot be self-bound artifacts"
            )
        object.__setattr__(self, "bound_artifacts", ordered_bindings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_kind": self.artifact_kind,
            "binding": self.binding.to_dict(),
            "bound_artifacts": [item.to_dict() for item in self.bound_artifacts],
            "component_order": list(self.component_order),
            "components": [item.to_dict() for item in self.components],
            "depth": self.depth,
            "payload": self.payload.to_dict(),
            "root_order": list(self.root_order),
            "roots": [item.to_dict() for item in self.roots],
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "TightAnalysisArtifactManifest":
        data = _require_mapping(value, "tight-analysis artifact manifest")
        _require_exact_keys(
            data,
            {
                "artifact_kind",
                "binding",
                "bound_artifacts",
                "component_order",
                "components",
                "depth",
                "payload",
                "root_order",
                "roots",
                "schema_version",
            },
            "tight-analysis artifact manifest",
        )
        component_order = data["component_order"]
        root_order = data["root_order"]
        components = data["components"]
        roots = data["roots"]
        bound_artifacts = data["bound_artifacts"]
        for name, collection in (
            ("component_order", component_order),
            ("root_order", root_order),
            ("components", components),
            ("roots", roots),
            ("bound_artifacts", bound_artifacts),
        ):
            if not isinstance(collection, list):
                raise ArtifactValidationError(f"{name} must be a JSON list")
        if not all(isinstance(item, str) for item in component_order):
            raise ArtifactValidationError("component_order must contain strings")
        if not all(isinstance(item, str) for item in root_order):
            raise ArtifactValidationError("root_order must contain strings")
        return cls(
            artifact_kind=data["artifact_kind"],
            schema_version=data["schema_version"],
            binding=TightAnalysisRunBinding.from_dict(data["binding"]),
            depth=data["depth"],
            component_order=tuple(component_order),
            components=tuple(TensorPayloadManifest.from_dict(item) for item in components),
            root_order=tuple(root_order),
            roots=tuple(TensorPayloadManifest.from_dict(item) for item in roots),
            payload=ArtifactFileManifest.from_dict(data["payload"]),
            bound_artifacts=tuple(
                ArtifactFileManifest.from_dict(item) for item in bound_artifacts
            ),
        )


def _encode_tensor(
    tensor: torch.Tensor,
    *,
    name: str,
    offset_bytes: int,
) -> tuple[TensorPayloadManifest, bytes]:
    if not isinstance(tensor, torch.Tensor):
        raise TypeError(f"{name} must be a torch.Tensor")
    if tensor.layout is not torch.strided:
        raise ArtifactValidationError(f"{name} must use strided tensor storage")
    dtype_name = _TORCH_DTYPE_NAMES.get(tensor.dtype)
    if dtype_name is None:
        raise ArtifactValidationError(f"{name} must use complex64 or complex128")
    if tensor.numel() == 0:
        raise ArtifactValidationError(f"{name} cannot be empty")
    if not bool(torch.isfinite(tensor).all().item()):
        raise ArtifactValidationError(f"{name} contains non-finite values")
    try:
        cpu_tensor = tensor.detach().resolve_conj().resolve_neg().cpu().contiguous()
    except RuntimeError as exc:
        raise ArtifactValidationError(f"{name} cannot be copied to CPU") from exc
    array = np.ascontiguousarray(
        cpu_tensor.numpy().astype(_NUMPY_DTYPES[dtype_name], copy=False)
    )
    payload = array.tobytes(order="C")
    manifest = TensorPayloadManifest(
        name=name,
        dtype=dtype_name,
        byte_order="little",
        shape=tuple(tensor.shape),
        source_device=str(tensor.device),
        offset_bytes=offset_bytes,
        size_bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
    )
    return manifest, payload


def _decode_tensor(
    payload: bytes,
    manifest: TensorPayloadManifest,
    *,
    map_location: str | torch.device,
) -> torch.Tensor:
    stop = manifest.offset_bytes + manifest.size_bytes
    chunk = payload[manifest.offset_bytes:stop]
    if len(chunk) != manifest.size_bytes:
        raise ArtifactValidationError(f"truncated tensor payload: {manifest.name}")
    if hashlib.sha256(chunk).hexdigest() != manifest.sha256:
        raise ArtifactValidationError(f"tensor payload hash mismatch: {manifest.name}")
    element_count = math.prod(manifest.shape) if manifest.shape else 1
    array = np.frombuffer(
        chunk,
        dtype=_NUMPY_DTYPES[manifest.dtype],
        count=element_count,
    ).copy()
    array = array.reshape(manifest.shape)
    if not bool(np.isfinite(array).all()):
        raise ArtifactValidationError(f"non-finite tensor payload: {manifest.name}")
    tensor = torch.from_numpy(array)
    device = torch.device(map_location)
    if device.type == "meta":
        raise ArtifactValidationError("map_location='meta' cannot restore values")
    try:
        return tensor.to(device=device)
    except (RuntimeError, TypeError) as exc:
        raise ArtifactValidationError(
            f"cannot restore {manifest.name} on {device}"
        ) from exc


def _validate_binding(
    binding: TightAnalysisRunBinding,
    config: RunConfigRecord,
) -> None:
    expected = TightAnalysisRunBinding.from_config(config)
    if binding != expected:
        raise ArtifactValidationError(
            "tight-analysis artifact run/config/source/environment binding mismatch"
        )


def write_tight_analysis_artifact(
    bundle: AtomicRunBundle,
    analysis: TightAnalysisOutput,
    *,
    bind_artifacts: Sequence[ArtifactFileManifest],
) -> TightAnalysisArtifactManifest:
    """Write one residual-first analysis exactly once into an open bundle."""

    if not isinstance(bundle, AtomicRunBundle):
        raise TypeError("bundle must be an AtomicRunBundle")
    if not isinstance(analysis, TightAnalysisOutput):
        raise TypeError("analysis must be a TightAnalysisOutput")
    bindings = bundle.validate_managed_artifacts(bind_artifacts)

    chunks: list[bytes] = []
    component_manifests: list[TensorPayloadManifest] = []
    root_manifests: list[TensorPayloadManifest] = []
    cursor = 0
    for name, tensor in zip(analysis.component_names, analysis.components, strict=True):
        item, chunk = _encode_tensor(tensor, name=name, offset_bytes=cursor)
        component_manifests.append(item)
        chunks.append(chunk)
        cursor += len(chunk)
    for index, tensor in enumerate(analysis.roots):
        item, chunk = _encode_tensor(
            tensor,
            name=f"alpha_{index}",
            offset_bytes=cursor,
        )
        root_manifests.append(item)
        chunks.append(chunk)
        cursor += len(chunk)

    payload = b"".join(chunks)
    payload_manifest = ArtifactFileManifest(
        path=TIGHT_ANALYSIS_PAYLOAD_PATH,
        sha256=hashlib.sha256(payload).hexdigest(),
        size_bytes=len(payload),
    )
    manifest = TightAnalysisArtifactManifest(
        artifact_kind=TIGHT_ANALYSIS_ARTIFACT_KIND,
        schema_version=TIGHT_ANALYSIS_SCHEMA_VERSION,
        binding=TightAnalysisRunBinding.from_config(bundle.config),
        depth=len(analysis.bands),
        component_order=analysis.component_names,
        components=tuple(component_manifests),
        root_order=tuple(f"alpha_{index}" for index in range(len(analysis.roots))),
        roots=tuple(root_manifests),
        payload=payload_manifest,
        bound_artifacts=bindings,
    )

    observed_payload = bundle.write_bytes(TIGHT_ANALYSIS_PAYLOAD_PATH, payload)
    if observed_payload != payload_manifest:
        raise ArtifactValidationError("managed payload digest changed during write")
    bundle.write_json(TIGHT_ANALYSIS_MANIFEST_PATH, manifest.to_dict())
    bundle.validate_managed_artifacts(bindings)
    return manifest


def _read_tight_analysis_bundle_files(
    bundle_root: Path,
    *,
    config: RunConfigRecord,
    bundle_manifest: BundleManifest,
    map_location: str | torch.device,
) -> tuple[
    TightAnalysisArtifactManifest,
    tuple[torch.Tensor, ...],
    tuple[torch.Tensor, ...],
]:
    files = {item.path: item for item in bundle_manifest.files}
    required = {TIGHT_ANALYSIS_MANIFEST_PATH, TIGHT_ANALYSIS_PAYLOAD_PATH}
    present = required & set(files)
    if not present:
        raise ArtifactValidationError("run bundle has no tight-analysis artifact")
    if present != required:
        raise ArtifactValidationError("tight-analysis manifest/payload pair is incomplete")
    if bundle_manifest.run_id != config.identity.run_id:
        raise ArtifactValidationError("bundle/config run identity mismatch")

    manifest_file = files[TIGHT_ANALYSIS_MANIFEST_PATH]
    validate_artifact_file_manifest(bundle_root, manifest_file)
    manifest = TightAnalysisArtifactManifest.from_dict(
        _load_canonical_json(bundle_root / TIGHT_ANALYSIS_MANIFEST_PATH)
    )
    _validate_binding(manifest.binding, config)
    if files[TIGHT_ANALYSIS_PAYLOAD_PATH] != manifest.payload:
        raise ArtifactValidationError("payload manifest is absent or differs from bundle index")
    payload_path = validate_artifact_file_manifest(bundle_root, manifest.payload)

    for bound in manifest.bound_artifacts:
        if files.get(bound.path) != bound:
            raise ArtifactValidationError(
                f"bound artifact differs from bundle index: {bound.path}"
            )
        validate_artifact_file_manifest(bundle_root, bound)

    payload = payload_path.read_bytes()
    if len(payload) != manifest.payload.size_bytes:
        raise ArtifactValidationError("tight-analysis payload was truncated")
    if hashlib.sha256(payload).hexdigest() != manifest.payload.sha256:
        raise ArtifactValidationError("tight-analysis payload hash mismatch")
    components = tuple(
        _decode_tensor(payload, item, map_location=map_location)
        for item in manifest.components
    )
    roots = tuple(
        _decode_tensor(payload, item, map_location=map_location)
        for item in manifest.roots
    )
    return manifest, components, roots


def validate_tight_analysis_bundle_files(
    bundle_root: str | Path,
    *,
    config: RunConfigRecord,
    bundle_manifest: BundleManifest,
) -> TightAnalysisArtifactManifest:
    """Validate the semantic coefficient pair inside an indexed bundle.

    This function intentionally does not call the outer bundle validator; it
    is its model-specific hook and therefore must remain non-recursive.
    """

    root = Path(bundle_root).resolve(strict=True)
    manifest, _, _ = _read_tight_analysis_bundle_files(
        root,
        config=config,
        bundle_manifest=bundle_manifest,
        map_location="cpu",
    )
    return manifest


def load_tight_analysis_artifact(
    bundle_root: str | Path,
    *,
    expected_config: RunConfigRecord,
    map_location: str | torch.device = "cpu",
) -> tuple[TightAnalysisOutput, TightAnalysisArtifactManifest]:
    """Validate a completed bundle and reconstruct its exact tensor values."""

    root = Path(bundle_root).resolve(strict=True)
    _validate_bundle_directory(root, expected_config.identity)
    bundled_config = RunConfigRecord.from_dict(_load_canonical_json(root / "config.json"))
    if bundled_config != expected_config:
        raise ArtifactValidationError("completed bundle differs from expected config record")
    bundle_manifest = BundleManifest.from_dict(
        _load_canonical_json(root / "bundle.json")
    )
    manifest, components, roots = _read_tight_analysis_bundle_files(
        root,
        config=expected_config,
        bundle_manifest=bundle_manifest,
        map_location=map_location,
    )
    depth = manifest.depth
    analysis = TightAnalysisOutput(
        bands=list(components[:depth]),
        final_carry=components[depth],
        roots=list(roots),
    )
    if analysis.component_names != manifest.component_order:
        raise ArtifactValidationError("deserialized coefficient order changed")
    return analysis, manifest


__all__ = [
    "TIGHT_ANALYSIS_ARTIFACT_KIND",
    "TIGHT_ANALYSIS_SCHEMA_VERSION",
    "TensorPayloadManifest",
    "TightAnalysisArtifactManifest",
    "TightAnalysisRunBinding",
    "load_tight_analysis_artifact",
    "validate_tight_analysis_bundle_files",
    "write_tight_analysis_artifact",
]
