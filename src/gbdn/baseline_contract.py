"""Baseline-admission and equal-budget confirmatory-plan contracts."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from gbdn.artifacts import ArtifactValidationError, canonical_json_bytes, sha256_file
from gbdn.heterophily_contract import DATASET_REGISTRY, OFFICIAL_SPLITS, TRAINING_SEEDS


REGISTRY_SCHEMA = "gbdn-baseline-registry-v1"
PLAN_SCHEMA = "gbdn-confirmatory-plan-v1"
_SHA = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_SPDX = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+-]*(?:-[A-Za-z0-9.+-]+)*")
_MAX_JSON_BYTES = 2 * 1024 * 1024


def _exact_keys(value: Mapping[str, Any], keys: set[str], label: str) -> None:
    if set(value) != keys:
        raise ArtifactValidationError(f"{label} keys do not match the frozen schema")


def _label(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ArtifactValidationError(f"{field} must be a nonempty trimmed string")
    return value


def _relative(value: Any, field: str) -> str:
    text = _label(value, field)
    path = Path(text)
    if path.is_absolute() or ".." in path.parts or "\\" in text or ":" in text:
        raise ArtifactValidationError(f"{field} must be a safe repository-relative path")
    return path.as_posix()


def _load_json(path: str | Path) -> Mapping[str, Any]:
    target = Path(path)
    if target.is_symlink() or not target.is_file() or target.stat().st_size > _MAX_JSON_BYTES:
        raise ArtifactValidationError("contract JSON must be a bounded regular file")
    try:
        def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            output: dict[str, Any] = {}
            for key, item in pairs:
                if key in output:
                    raise ArtifactValidationError(f"duplicate contract key: {key}")
                output[key] = item
            return output

        value = json.loads(
            target.read_text(encoding="utf-8"),
            object_pairs_hook=unique_object,
            parse_constant=lambda constant: (_ for _ in ()).throw(
                ArtifactValidationError(f"non-standard JSON constant: {constant}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError("contract must be valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ArtifactValidationError("contract root must be an object")
    return value


@dataclass(frozen=True)
class VerifiedBaseline:
    name: str
    repository_url: str
    upstream_commit: str
    spdx_license: str
    license_notice_path: str
    wrapper_path: str
    upstream_config_path: str
    local_patch_sha256: str
    protocols: tuple[str, ...]
    parity_dataset: str
    parity_metric: str
    parity_expected: float
    parity_observed: float
    parity_tolerance: float
    parameter_count_verified: bool
    spmv_count_verified: bool


def validate_baseline_registry(
    path: str | Path,
    *,
    repository_root: str | Path,
    required_methods: Sequence[str],
) -> tuple[VerifiedBaseline, ...]:
    """Admit only complete, verified, tracked upstream baseline records."""

    root = Path(repository_root).resolve(strict=True)
    data = _load_json(path)
    _exact_keys(data, {"baselines", "schema_version"}, "baseline registry")
    if data["schema_version"] != REGISTRY_SCHEMA or not isinstance(data["baselines"], list):
        raise ArtifactValidationError("baseline registry schema is invalid")
    records: dict[str, VerifiedBaseline] = {}
    for index, raw in enumerate(data["baselines"]):
        if not isinstance(raw, dict):
            raise ArtifactValidationError(f"baseline[{index}] must be an object")
        _exact_keys(
            raw,
            {
                "license",
                "name",
                "parity",
                "protocols",
                "repository_url",
                "status",
                "upstream_commit",
                "verification",
                "wrapper",
            },
            f"baseline[{index}]",
        )
        name = _label(raw["name"], "baseline name")
        if name in records:
            raise ArtifactValidationError(f"duplicate baseline name: {name}")
        if raw["status"] != "VERIFIED":
            raise ArtifactValidationError(f"baseline {name} is not VERIFIED")
        url = _label(raw["repository_url"], "repository_url")
        if not url.startswith("https://"):
            raise ArtifactValidationError(f"baseline {name} repository must use HTTPS")
        commit = raw["upstream_commit"]
        if not isinstance(commit, str) or _SHA.fullmatch(commit) is None:
            raise ArtifactValidationError(f"baseline {name} needs a full 40-hex upstream commit")
        license_record = raw["license"]
        wrapper = raw["wrapper"]
        parity = raw["parity"]
        verification = raw["verification"]
        for value, keys, label in (
            (license_record, {"notice_path", "spdx"}, "license"),
            (wrapper, {"local_patch_sha256", "path", "upstream_config_path"}, "wrapper"),
            (parity, {"dataset", "expected", "metric", "observed", "status", "tolerance"}, "parity"),
            (verification, {"parameter_count", "spmv_count"}, "verification"),
        ):
            if not isinstance(value, dict):
                raise ArtifactValidationError(f"baseline {name} {label} must be an object")
            _exact_keys(value, keys, f"baseline {name} {label}")
        spdx = _label(license_record["spdx"], "license SPDX")
        if _SPDX.fullmatch(spdx) is None or spdx == "NOASSERTION":
            raise ArtifactValidationError(f"baseline {name} license is unresolved")
        paths = tuple(
            _relative(value, field)
            for value, field in (
                (license_record["notice_path"], "license notice"),
                (wrapper["path"], "wrapper path"),
                (wrapper["upstream_config_path"], "upstream config path"),
            )
        )
        for relative in paths:
            artifact = root / relative
            if artifact.is_symlink() or not artifact.is_file():
                raise ArtifactValidationError(f"baseline {name} missing regular evidence: {relative}")
        patch_hash = wrapper["local_patch_sha256"]
        if not isinstance(patch_hash, str) or _SHA256.fullmatch(patch_hash) is None:
            raise ArtifactValidationError(f"baseline {name} local patch hash is invalid")
        if sha256_file(root / paths[1]) != patch_hash:
            raise ArtifactValidationError(f"baseline {name} local patch hash does not match wrapper")
        protocols = raw["protocols"]
        if not isinstance(protocols, list) or not protocols or len(set(protocols)) != len(protocols):
            raise ArtifactValidationError(f"baseline {name} protocols must be unique and nonempty")
        if "heterophily" not in protocols:
            raise ArtifactValidationError(f"baseline {name} lacks heterophily protocol verification")
        if parity["status"] != "PASS":
            raise ArtifactValidationError(f"baseline {name} parity did not pass")
        numeric = (parity["expected"], parity["observed"], parity["tolerance"])
        if any(type(value) not in (int, float) or not math.isfinite(float(value)) for value in numeric):
            raise ArtifactValidationError(f"baseline {name} parity numbers must be finite")
        if float(parity["tolerance"]) < 0 or abs(float(parity["observed"]) - float(parity["expected"])) > float(parity["tolerance"]):
            raise ArtifactValidationError(f"baseline {name} parity exceeds tolerance")
        if verification != {"parameter_count": True, "spmv_count": True}:
            raise ArtifactValidationError(f"baseline {name} resource counts are unverified")
        records[name] = VerifiedBaseline(
            name,
            url,
            commit,
            spdx,
            paths[0],
            paths[1],
            paths[2],
            patch_hash,
            tuple(protocols),
            _label(parity["dataset"], "parity dataset"),
            _label(parity["metric"], "parity metric"),
            float(parity["expected"]),
            float(parity["observed"]),
            float(parity["tolerance"]),
            True,
            True,
        )
    missing = sorted(set(required_methods) - set(records))
    extra = sorted(set(records) - set(required_methods))
    if missing or extra:
        raise ArtifactValidationError(f"baseline registry scope mismatch; missing={missing}, extra={extra}")
    return tuple(records[name] for name in required_methods)


@dataclass(frozen=True)
class ConfirmatoryPlan:
    methods: tuple[str, ...]
    primary_baselines: tuple[str, ...]
    trial_budget_per_method_dataset: int
    practical_tie_thresholds: Mapping[str, float]
    baseline_registry_sha256: str


def validate_confirmatory_plan(path: str | Path) -> ConfirmatoryPlan:
    """Validate the frozen 10x3, equal-budget, validation-only plan."""

    data = _load_json(path)
    _exact_keys(
        data,
        {
            "baseline_registry_sha256",
            "datasets",
            "methods",
            "official_splits",
            "primary_baselines",
            "practical_tie_thresholds",
            "schema_version",
            "selection",
            "training_seeds",
            "trial_budget_per_method_dataset",
        },
        "confirmatory plan",
    )
    if data["schema_version"] != PLAN_SCHEMA:
        raise ArtifactValidationError("confirmatory plan schema is invalid")
    if tuple(data["datasets"]) != tuple(DATASET_REGISTRY):
        raise ArtifactValidationError("confirmatory datasets differ from official registry order")
    if tuple(data["official_splits"]) != OFFICIAL_SPLITS or tuple(data["training_seeds"]) != TRAINING_SEEDS:
        raise ArtifactValidationError("confirmatory split/seed grid is not frozen 10x3")
    methods = data["methods"]
    primary = data["primary_baselines"]
    if not isinstance(methods, list) or len(methods) < 2 or len(set(methods)) != len(methods):
        raise ArtifactValidationError("confirmatory methods must be unique and include comparators")
    if "TightGBDN" not in methods:
        raise ArtifactValidationError("confirmatory plan must include TightGBDN")
    if not isinstance(primary, list) or not primary or not set(primary) < set(methods):
        raise ArtifactValidationError("primary baselines must be a nonempty strict method subset")
    selection = data["selection"]
    if selection != {
        "equal_validation_trial_budget": True,
        "freeze_before_test": True,
        "test_process_isolated": True,
        "test_used_for_selection": False,
    }:
        raise ArtifactValidationError("confirmatory selection boundary is not fail-closed")
    budget = data["trial_budget_per_method_dataset"]
    if type(budget) is not int or budget <= 0:
        raise ArtifactValidationError("trial budget must be one positive equal integer")
    thresholds = data["practical_tie_thresholds"]
    if not isinstance(thresholds, dict) or set(thresholds) != set(DATASET_REGISTRY):
        raise ArtifactValidationError("practical tie thresholds must cover all official datasets exactly")
    if any(type(value) not in (int, float) or not math.isfinite(float(value)) or not 0 <= float(value) < 1 for value in thresholds.values()):
        raise ArtifactValidationError("practical tie thresholds must be finite in [0,1)")
    registry_hash = data["baseline_registry_sha256"]
    if not isinstance(registry_hash, str) or _SHA256.fullmatch(registry_hash) is None:
        raise ArtifactValidationError("baseline registry SHA-256 is invalid")
    return ConfirmatoryPlan(tuple(methods), tuple(primary), budget, thresholds, registry_hash)


def validate_plan_registry_binding(
    plan_path: str | Path,
    registry_path: str | Path,
    *,
    repository_root: str | Path,
) -> tuple[ConfirmatoryPlan, tuple[VerifiedBaseline, ...]]:
    plan = validate_confirmatory_plan(plan_path)
    if sha256_file(registry_path) != plan.baseline_registry_sha256:
        raise ArtifactValidationError("confirmatory plan baseline registry hash mismatch")
    baselines = validate_baseline_registry(
        registry_path,
        repository_root=repository_root,
        required_methods=plan.primary_baselines,
    )
    return plan, baselines


__all__ = [
    "ConfirmatoryPlan",
    "PLAN_SCHEMA",
    "REGISTRY_SCHEMA",
    "VerifiedBaseline",
    "validate_baseline_registry",
    "validate_confirmatory_plan",
    "validate_plan_registry_binding",
]
