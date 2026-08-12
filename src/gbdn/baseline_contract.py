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


REGISTRY_SCHEMA = "gbdn-baseline-registry-v2"
PARITY_EVIDENCE_SCHEMA = "gbdn-baseline-parity-evidence-v1"
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


def _regular_repository_file(root: Path, relative: str, field: str) -> Path:
    """Resolve one evidence file without permitting parent-link escapes."""

    lexical = root / relative
    if lexical.is_symlink() or not lexical.is_file():
        raise ArtifactValidationError(f"missing regular {field}: {relative}")
    try:
        resolved = lexical.resolve(strict=True)
    except OSError as exc:
        raise ArtifactValidationError(f"cannot resolve {field}: {relative}") from exc
    if not resolved.is_relative_to(root):
        raise ArtifactValidationError(f"{field} escapes repository root: {relative}")
    return resolved


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
    implementation_kind: str
    source_repository_url: str
    source_commit: str
    paper_url: str
    equation_locator: str
    upstream_code_used: bool
    provenance_path: str
    provenance_sha256: str
    independent_oracle_path: str
    independent_oracle_sha256: str
    spdx_license: str
    license_notice_path: str
    license_notice_sha256: str
    wrapper_path: str
    reference_config_path: str
    reference_config_sha256: str
    source_sha256: str
    protocols: tuple[str, ...]
    parity_dataset: str
    parity_metric: str
    parity_expected: float
    parity_observed: float
    parity_tolerance: float
    parity_evidence_path: str
    parameter_count_verified: bool
    spmv_count_verified: bool
    independent_operator_oracle_verified: bool
    official_task_contract_verified: bool


def validate_baseline_registry(
    path: str | Path,
    *,
    repository_root: str | Path,
    required_methods: Sequence[str],
) -> tuple[VerifiedBaseline, ...]:
    """Admit only complete, hash-bound, independently checked baseline records."""

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
                "implementation",
                "license",
                "name",
                "parity",
                "protocols",
                "status",
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
        implementation = raw["implementation"]
        license_record = raw["license"]
        wrapper = raw["wrapper"]
        parity = raw["parity"]
        verification = raw["verification"]
        for value, keys, label in (
            (
                implementation,
                {
                    "equation_locator",
                    "independent_oracle_path",
                    "independent_oracle_sha256",
                    "kind",
                    "paper_url",
                    "provenance_path",
                    "provenance_sha256",
                    "source_commit",
                    "source_repository_url",
                    "upstream_code_used",
                },
                "implementation",
            ),
            (license_record, {"notice_path", "notice_sha256", "spdx"}, "license"),
            (
                wrapper,
                {
                    "path",
                    "reference_config_path",
                    "reference_config_sha256",
                    "source_sha256",
                },
                "wrapper",
            ),
            (
                parity,
                {
                    "dataset",
                    "evidence_path",
                    "evidence_sha256",
                    "expected",
                    "metric",
                    "observed",
                    "status",
                    "tolerance",
                },
                "parity",
            ),
            (
                verification,
                {
                    "independent_operator_oracle",
                    "official_task_contract",
                    "parameter_count",
                    "spmv_count",
                },
                "verification",
            ),
        ):
            if not isinstance(value, dict):
                raise ArtifactValidationError(f"baseline {name} {label} must be an object")
            _exact_keys(value, keys, f"baseline {name} {label}")
        kind = implementation["kind"]
        if kind not in {"UPSTREAM_CODE", "CLEAN_ROOM_EQUATIONS"}:
            raise ArtifactValidationError(f"baseline {name} implementation kind is invalid")
        source_url = _label(
            implementation["source_repository_url"], "source_repository_url"
        )
        paper_url = _label(implementation["paper_url"], "paper_url")
        if not source_url.startswith("https://") or not paper_url.startswith("https://"):
            raise ArtifactValidationError(f"baseline {name} source and paper must use HTTPS")
        commit = implementation["source_commit"]
        if not isinstance(commit, str) or _SHA.fullmatch(commit) is None:
            raise ArtifactValidationError(
                f"baseline {name} needs a full 40-hex implementation source commit"
            )
        equation_locator = _label(
            implementation["equation_locator"], "equation_locator"
        )
        upstream_used = implementation["upstream_code_used"]
        if type(upstream_used) is not bool:
            raise ArtifactValidationError(f"baseline {name} upstream_code_used must be boolean")
        if (kind == "UPSTREAM_CODE") != upstream_used:
            raise ArtifactValidationError(
                f"baseline {name} implementation kind contradicts upstream-code attestation"
            )
        spdx = _label(license_record["spdx"], "license SPDX")
        if _SPDX.fullmatch(spdx) is None or spdx == "NOASSERTION":
            raise ArtifactValidationError(f"baseline {name} license is unresolved")
        evidence_specs = (
            (license_record["notice_path"], license_record["notice_sha256"], "license notice"),
            (wrapper["path"], wrapper["source_sha256"], "wrapper source"),
            (
                wrapper["reference_config_path"],
                wrapper["reference_config_sha256"],
                "reference config",
            ),
            (
                implementation["provenance_path"],
                implementation["provenance_sha256"],
                "implementation provenance",
            ),
            (
                implementation["independent_oracle_path"],
                implementation["independent_oracle_sha256"],
                "independent oracle",
            ),
            (parity["evidence_path"], parity["evidence_sha256"], "parity evidence"),
        )
        paths: list[str] = []
        hashes: list[str] = []
        for raw_path, raw_hash, field in evidence_specs:
            relative = _relative(raw_path, f"baseline {name} {field} path")
            if not isinstance(raw_hash, str) or _SHA256.fullmatch(raw_hash) is None:
                raise ArtifactValidationError(f"baseline {name} {field} hash is invalid")
            artifact = _regular_repository_file(root, relative, f"baseline {name} {field}")
            if sha256_file(artifact) != raw_hash:
                raise ArtifactValidationError(
                    f"baseline {name} {field} hash does not match artifact"
                )
            paths.append(relative)
            hashes.append(raw_hash)
        protocols = raw["protocols"]
        if (
            not isinstance(protocols, list)
            or not protocols
            or any(not isinstance(protocol, str) or not protocol for protocol in protocols)
            or len(set(protocols)) != len(protocols)
        ):
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
        if verification != {
            "independent_operator_oracle": True,
            "official_task_contract": True,
            "parameter_count": True,
            "spmv_count": True,
        }:
            raise ArtifactValidationError(f"baseline {name} resource counts are unverified")
        parity_evidence = _load_json(root / paths[5])
        expected_evidence = {
            "baseline": name,
            "dataset": parity["dataset"],
            "expected": parity["expected"],
            "implementation_kind": kind,
            "independent_oracle_sha256": hashes[4],
            "metric": parity["metric"],
            "observed": parity["observed"],
            "reference_config_sha256": hashes[2],
            "schema_version": PARITY_EVIDENCE_SCHEMA,
            "source_commit": commit,
            "status": parity["status"],
            "tolerance": parity["tolerance"],
            "wrapper_sha256": hashes[1],
        }
        if parity_evidence != expected_evidence:
            raise ArtifactValidationError(
                f"baseline {name} parity evidence is not registry- and implementation-bound"
            )
        records[name] = VerifiedBaseline(
            name=name,
            implementation_kind=kind,
            source_repository_url=source_url,
            source_commit=commit,
            paper_url=paper_url,
            equation_locator=equation_locator,
            upstream_code_used=upstream_used,
            provenance_path=paths[3],
            provenance_sha256=hashes[3],
            independent_oracle_path=paths[4],
            independent_oracle_sha256=hashes[4],
            spdx_license=spdx,
            license_notice_path=paths[0],
            license_notice_sha256=hashes[0],
            wrapper_path=paths[1],
            reference_config_path=paths[2],
            reference_config_sha256=hashes[2],
            source_sha256=hashes[1],
            protocols=tuple(protocols),
            parity_dataset=_label(parity["dataset"], "parity dataset"),
            parity_metric=_label(parity["metric"], "parity metric"),
            parity_expected=float(parity["expected"]),
            parity_observed=float(parity["observed"]),
            parity_tolerance=float(parity["tolerance"]),
            parity_evidence_path=paths[5],
            parameter_count_verified=True,
            spmv_count_verified=True,
            independent_operator_oracle_verified=True,
            official_task_contract_verified=True,
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
    "PARITY_EVIDENCE_SCHEMA",
    "PLAN_SCHEMA",
    "REGISTRY_SCHEMA",
    "VerifiedBaseline",
    "validate_baseline_registry",
    "validate_confirmatory_plan",
    "validate_plan_registry_binding",
]
