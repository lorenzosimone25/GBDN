"""Baseline implementation, configuration-provenance, and plan contracts.

Registry v3 deliberately separates two scientific questions:

* does the executed implementation match its claimed operator; and
* where did the benchmark configuration come from?

An implementation may be verified before tuning.  It cannot enter a
confirmatory plan until a validation-only final configuration and its
selection provenance are hash-bound to the registry.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence

from gbdn.artifacts import ArtifactValidationError, sha256_file
from gbdn.heterophily_contract import DATASET_REGISTRY, OFFICIAL_SPLITS, TRAINING_SEEDS


REGISTRY_SCHEMA = "gbdn-baseline-registry-v3"
PARITY_EVIDENCE_SCHEMA = "gbdn-baseline-operator-parity-v2"
SEARCH_SPACE_SCHEMA = "gbdn-baseline-search-space-v1"
SELECTION_EVIDENCE_SCHEMA = "gbdn-baseline-selection-evidence-v1"
PLAN_SCHEMA = "gbdn-confirmatory-plan-v1"
LOCAL_SEARCH = "LOCAL_EQUAL_BUDGET_VALIDATION_SEARCH"
UPSTREAM_CONFIG = "UPSTREAM_REFERENCE_CONFIG"
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


def _sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ArtifactValidationError(f"{field} hash is invalid")
    return value


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


def _bound_file(
    root: Path, raw_path: Any, raw_hash: Any, field: str
) -> tuple[str, str]:
    relative = _relative(raw_path, f"{field} path")
    expected = _sha256(raw_hash, field)
    artifact = _regular_repository_file(root, relative, field)
    if sha256_file(artifact) != expected:
        raise ArtifactValidationError(f"{field} hash does not match artifact")
    return relative, expected


def _dataset_bindings() -> dict[str, dict[str, str]]:
    return {
        name: {
            "selection_metric": spec.selection_metric,
            "task_type": spec.task_type,
        }
        for name, spec in DATASET_REGISTRY.items()
    }


def _finite_json_value(value: Any) -> bool:
    if value is None or type(value) in {bool, int, str}:
        return True
    if type(value) is float:
        return math.isfinite(value)
    if isinstance(value, list):
        return bool(value) and all(_finite_json_value(item) for item in value)
    return False


@dataclass(frozen=True)
class VerifiedBaseline:
    name: str
    admission_status: str
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
    source_sha256: str
    protocols: tuple[str, ...]
    operator_parity_scope: str
    parity_evidence_path: str
    parity_evidence_sha256: str
    configuration_provenance: str
    search_space_path: str | None
    search_space_sha256: str | None
    final_config_path: str | None
    final_config_sha256: str | None
    selection_evidence_path: str | None
    selection_evidence_sha256: str | None
    parameter_count_verified: bool
    spmv_count_verified: bool
    independent_operator_oracle_verified: bool
    official_task_contract_verified: bool

    @property
    def reference_config_path(self) -> str:
        """Compatibility name used by the worker; only final configs qualify."""

        if self.final_config_path is None:
            raise ArtifactValidationError(
                f"baseline {self.name} has no finalized validation-only configuration"
            )
        return self.final_config_path

    @property
    def reference_config_sha256(self) -> str:
        if self.final_config_sha256 is None:
            raise ArtifactValidationError(
                f"baseline {self.name} has no finalized validation-only configuration"
            )
        return self.final_config_sha256


def _validate_operator_evidence(
    *,
    root: Path,
    name: str,
    kind: str,
    source_commit: str,
    wrapper_sha256: str,
    oracle_sha256: str,
    parity: Mapping[str, Any],
) -> tuple[str, str, str]:
    _exact_keys(
        parity,
        {"evidence_path", "evidence_sha256", "scope", "status"},
        f"baseline {name} operator parity",
    )
    if parity["scope"] != "OPERATOR_COMPOSITION" or parity["status"] != "PASS":
        raise ArtifactValidationError(
            f"baseline {name} operator-composition parity did not pass"
        )
    path, digest = _bound_file(
        root,
        parity["evidence_path"],
        parity["evidence_sha256"],
        f"baseline {name} operator parity evidence",
    )
    evidence = _load_json(root / path)
    _exact_keys(
        evidence,
        {
            "baseline",
            "checks",
            "implementation_kind",
            "independent_oracle_sha256",
            "scope",
            "schema_version",
            "source_commit",
            "status",
            "test_command",
            "test_path",
            "test_result",
            "test_sha256",
            "wrapper_sha256",
        },
        f"baseline {name} operator parity evidence",
    )
    if (
        evidence["schema_version"] != PARITY_EVIDENCE_SCHEMA
        or evidence["baseline"] != name
        or evidence["implementation_kind"] != kind
        or evidence["source_commit"] != source_commit
        or evidence["wrapper_sha256"] != wrapper_sha256
        or evidence["independent_oracle_sha256"] != oracle_sha256
        or evidence["scope"] != parity["scope"]
        or evidence["status"] != parity["status"]
        or not isinstance(evidence["test_command"], str)
        or not evidence["test_command"]
        or not isinstance(evidence["test_result"], str)
        or not evidence["test_result"]
    ):
        raise ArtifactValidationError(
            f"baseline {name} operator parity evidence is not implementation-bound"
        )
    _bound_file(
        root,
        evidence["test_path"],
        evidence["test_sha256"],
        f"baseline {name} operator parity test source",
    )
    checks = evidence["checks"]
    if not isinstance(checks, dict):
        raise ArtifactValidationError(f"baseline {name} operator checks must be an object")
    mandatory = {
        "independent_dense_operator_forward",
        "independent_dense_operator_gradients",
        "official_task_head_dispatch",
        "parameter_count",
        "spmv_count",
    }
    if kind == "UPSTREAM_CODE":
        mandatory |= {
            "upstream_composition_forward",
            "upstream_composition_gradients",
        }
    if set(checks) != mandatory or any(
        not isinstance(value, dict)
        or set(value) != {"evidence", "status"}
        or value.get("status") != "PASS"
        or not isinstance(value.get("evidence"), str)
        or not value["evidence"]
        for key, value in checks.items()
        if key in mandatory
    ):
        raise ArtifactValidationError(
            f"baseline {name} lacks mandatory passing operator checks"
        )
    return str(parity["scope"]), path, digest


def _validate_configuration(
    *,
    root: Path,
    name: str,
    status: str,
    raw: Mapping[str, Any],
    admission: Literal["screening", "confirmatory"],
    expected_trial_budget: int | None,
) -> tuple[str, str | None, str | None, str | None, str | None, str | None, str | None]:
    _exact_keys(
        raw,
        {
            "budget_binding",
            "final_configuration",
            "kind",
            "search_space_path",
            "search_space_sha256",
            "selection",
        },
        f"baseline {name} configuration",
    )
    kind = raw["kind"]
    if kind not in {LOCAL_SEARCH, UPSTREAM_CONFIG}:
        raise ArtifactValidationError(f"baseline {name} configuration provenance is invalid")
    selection = raw["selection"]
    if not isinstance(selection, dict):
        raise ArtifactValidationError(f"baseline {name} selection must be an object")
    _exact_keys(
        selection,
        {"dataset_bindings", "partition", "test_used_for_selection"},
        f"baseline {name} selection",
    )
    if selection != {
        "dataset_bindings": _dataset_bindings(),
        "partition": "validation",
        "test_used_for_selection": False,
    }:
        raise ArtifactValidationError(
            f"baseline {name} selection is not official-task and validation-only bound"
        )

    search_path: str | None = None
    search_hash: str | None = None
    search_parameters: Mapping[str, Any] | None = None
    if kind == LOCAL_SEARCH:
        if raw["budget_binding"] != "CONFIRMATORY_PLAN_EQUAL_TRIAL_BUDGET":
            raise ArtifactValidationError(
                f"baseline {name} local search is not equal-budget plan-bound"
            )
        search_path, search_hash = _bound_file(
            root,
            raw["search_space_path"],
            raw["search_space_sha256"],
            f"baseline {name} search space",
        )
        search = _load_json(root / search_path)
        _exact_keys(
            search,
            {"method", "parameters", "schema_version", "status"},
            f"baseline {name} search space",
        )
        if (
            search["schema_version"] != SEARCH_SPACE_SCHEMA
            or search["method"] != name
            or search["status"] != "FROZEN_PRESPECIFIED"
            or not isinstance(search["parameters"], dict)
            or not search["parameters"]
        ):
            raise ArtifactValidationError(f"baseline {name} search space is invalid")
        tuned = 0
        search_parameters = search["parameters"]
        for parameter, specification in search_parameters.items():
            if not isinstance(parameter, str) or not parameter or not isinstance(
                specification, dict
            ):
                raise ArtifactValidationError(
                    f"baseline {name} search parameter is invalid"
                )
            _exact_keys(
                specification,
                {"role", "values"},
                f"baseline {name} search parameter {parameter}",
            )
            values = specification["values"]
            if (
                specification["role"] not in {"FIXED", "TUNED"}
                or not isinstance(values, list)
                or not values
                or any(not _finite_json_value(value) for value in values)
                or len({json.dumps(value, sort_keys=True) for value in values})
                != len(values)
                or (specification["role"] == "FIXED" and len(values) != 1)
                or (specification["role"] == "TUNED" and len(values) < 2)
            ):
                raise ArtifactValidationError(
                    f"baseline {name} search parameter values/role are invalid"
                )
            tuned += specification["role"] == "TUNED"
        if tuned == 0:
            raise ArtifactValidationError(
                f"baseline {name} local search has no prespecified tuned parameter"
            )
    else:
        if (
            raw["budget_binding"] != "NOT_APPLICABLE_UPSTREAM_REFERENCE"
            or raw["search_space_path"] is not None
            or raw["search_space_sha256"] is not None
        ):
            raise ArtifactValidationError(
                f"baseline {name} upstream configuration cannot claim a local search"
            )

    final = raw["final_configuration"]
    final_path: str | None = None
    final_hash: str | None = None
    selection_path: str | None = None
    selection_hash: str | None = None
    if final is not None:
        if not isinstance(final, dict):
            raise ArtifactValidationError(
                f"baseline {name} final configuration must be an object or null"
            )
        _exact_keys(
            final,
            {
                "path",
                "selection_evidence_path",
                "selection_evidence_sha256",
                "sha256",
            },
            f"baseline {name} final configuration",
        )
        final_path, final_hash = _bound_file(
            root, final["path"], final["sha256"], f"baseline {name} final configuration"
        )
        frozen = _load_json(root / final_path)
        _exact_keys(
            frozen,
            {"datasets", "method", "schema_version"},
            f"baseline {name} final configuration",
        )
        if (
            frozen["schema_version"] != "gbdn-heterophily-method-config-v1"
            or frozen["method"] != name
            or not isinstance(frozen["datasets"], dict)
            or set(frozen["datasets"]) != set(DATASET_REGISTRY)
            or any(
                not isinstance(value, dict)
                or set(value) != {"model", "optimizer", "training"}
                for value in frozen["datasets"].values()
            )
        ):
            raise ArtifactValidationError(
                f"baseline {name} final configuration does not freeze all official tasks"
            )
        if kind == LOCAL_SEARCH:
            assert search_parameters is not None  # established above
            for parameter, specification in search_parameters.items():
                parts = parameter.split(".")
                if len(parts) != 2 or any(not part for part in parts):
                    raise ArtifactValidationError(
                        f"baseline {name} search parameter path is invalid"
                    )
                section, field = parts
                allowed = {
                    json.dumps(value, sort_keys=True, separators=(",", ":"))
                    for value in specification["values"]
                }
                for dataset, dataset_config in frozen["datasets"].items():
                    selected_section = dataset_config.get(section)
                    if not isinstance(selected_section, dict) or field not in selected_section:
                        raise ArtifactValidationError(
                            f"baseline {name} final configuration omits search parameter "
                            f"{parameter} for {dataset}"
                        )
                    selected = json.dumps(
                        selected_section[field], sort_keys=True, separators=(",", ":")
                    )
                    if selected not in allowed:
                        raise ArtifactValidationError(
                            f"baseline {name} final configuration selects an out-of-space "
                            f"value for {parameter} on {dataset}"
                        )
        selection_path, selection_hash = _bound_file(
            root,
            final["selection_evidence_path"],
            final["selection_evidence_sha256"],
            f"baseline {name} selection evidence",
        )
        evidence = _load_json(root / selection_path)
        _exact_keys(
            evidence,
            {
                "baseline",
                "configuration_kind",
                "final_config_sha256",
                "schema_version",
                "search_space_sha256",
                "selection_partition",
                "status",
                "test_used_for_selection",
                "trial_budget_per_dataset",
            },
            f"baseline {name} selection evidence",
        )
        if kind == LOCAL_SEARCH:
            if expected_trial_budget is None:
                if admission == "confirmatory":
                    raise ArtifactValidationError(
                        "confirmatory baseline validation requires the plan trial budget"
                    )
                budget_ok = type(evidence["trial_budget_per_dataset"]) is int and evidence[
                    "trial_budget_per_dataset"
                ] > 0
            else:
                budget_ok = evidence["trial_budget_per_dataset"] == expected_trial_budget
            expected_search_hash: str | None = search_hash
        else:
            budget_ok = evidence["trial_budget_per_dataset"] is None
            expected_search_hash = None
        if (
            evidence["schema_version"] != SELECTION_EVIDENCE_SCHEMA
            or evidence["baseline"] != name
            or evidence["configuration_kind"] != kind
            or evidence["final_config_sha256"] != final_hash
            or evidence["search_space_sha256"] != expected_search_hash
            or evidence["selection_partition"] != "validation"
            or evidence["test_used_for_selection"] is not False
            or evidence["status"] != "PASS"
            or not budget_ok
        ):
            raise ArtifactValidationError(
                f"baseline {name} final configuration lacks valid selection provenance"
            )

    if status == "IMPLEMENTATION_VERIFIED" and final is not None:
        raise ArtifactValidationError(
            f"baseline {name} status understates its populated final configuration"
        )
    if status == "CONFIRMATORY_READY" and final is None:
        raise ArtifactValidationError(
            f"baseline {name} is missing a finalized validation-only configuration"
        )
    if admission == "confirmatory" and (
        status != "CONFIRMATORY_READY" or final is None
    ):
        raise ArtifactValidationError(
            f"baseline {name} is not confirmatory-ready with a finalized configuration"
        )
    return (
        str(kind),
        search_path,
        search_hash,
        final_path,
        final_hash,
        selection_path,
        selection_hash,
    )


def validate_baseline_registry(
    path: str | Path,
    *,
    repository_root: str | Path,
    required_methods: Sequence[str],
    admission: Literal["screening", "confirmatory"] = "confirmatory",
    expected_trial_budget: int | None = None,
) -> tuple[VerifiedBaseline, ...]:
    """Validate implementation evidence and, when requested, final admission."""

    if admission not in {"screening", "confirmatory"}:
        raise ArtifactValidationError("baseline admission stage is invalid")
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
                "configuration",
                "implementation",
                "license",
                "name",
                "operator_parity",
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
        status = raw["status"]
        if status not in {"IMPLEMENTATION_VERIFIED", "CONFIRMATORY_READY"}:
            raise ArtifactValidationError(f"baseline {name} status is invalid")
        implementation = raw["implementation"]
        license_record = raw["license"]
        wrapper = raw["wrapper"]
        parity = raw["operator_parity"]
        verification = raw["verification"]
        configuration = raw["configuration"]
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
            (wrapper, {"path", "source_sha256"}, "wrapper"),
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
        if not isinstance(parity, dict) or not isinstance(configuration, dict):
            raise ArtifactValidationError(f"baseline {name} parity/configuration must be objects")
        kind = implementation["kind"]
        if kind not in {"UPSTREAM_CODE", "CLEAN_ROOM_EQUATIONS"}:
            raise ArtifactValidationError(f"baseline {name} implementation kind is invalid")
        source_url = _label(implementation["source_repository_url"], "source_repository_url")
        paper_url = _label(implementation["paper_url"], "paper_url")
        if not source_url.startswith("https://") or not paper_url.startswith("https://"):
            raise ArtifactValidationError(f"baseline {name} source and paper must use HTTPS")
        commit = implementation["source_commit"]
        if not isinstance(commit, str) or _SHA.fullmatch(commit) is None:
            raise ArtifactValidationError(
                f"baseline {name} needs a full 40-hex implementation source commit"
            )
        equation_locator = _label(implementation["equation_locator"], "equation_locator")
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
        license_path, license_hash = _bound_file(
            root,
            license_record["notice_path"],
            license_record["notice_sha256"],
            f"baseline {name} license notice",
        )
        wrapper_path, wrapper_hash = _bound_file(
            root, wrapper["path"], wrapper["source_sha256"], f"baseline {name} wrapper source"
        )
        provenance_path, provenance_hash = _bound_file(
            root,
            implementation["provenance_path"],
            implementation["provenance_sha256"],
            f"baseline {name} implementation provenance",
        )
        oracle_path, oracle_hash = _bound_file(
            root,
            implementation["independent_oracle_path"],
            implementation["independent_oracle_sha256"],
            f"baseline {name} independent oracle",
        )
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
        if verification != {
            "independent_operator_oracle": True,
            "official_task_contract": True,
            "parameter_count": True,
            "spmv_count": True,
        }:
            raise ArtifactValidationError(f"baseline {name} resource/task checks are unverified")
        parity_scope, parity_path, parity_hash = _validate_operator_evidence(
            root=root,
            name=name,
            kind=kind,
            source_commit=commit,
            wrapper_sha256=wrapper_hash,
            oracle_sha256=oracle_hash,
            parity=parity,
        )
        (
            configuration_kind,
            search_path,
            search_hash,
            final_path,
            final_hash,
            selection_path,
            selection_hash,
        ) = _validate_configuration(
            root=root,
            name=name,
            status=status,
            raw=configuration,
            admission=admission,
            expected_trial_budget=expected_trial_budget,
        )
        records[name] = VerifiedBaseline(
            name=name,
            admission_status=status,
            implementation_kind=str(kind),
            source_repository_url=source_url,
            source_commit=commit,
            paper_url=paper_url,
            equation_locator=equation_locator,
            upstream_code_used=upstream_used,
            provenance_path=provenance_path,
            provenance_sha256=provenance_hash,
            independent_oracle_path=oracle_path,
            independent_oracle_sha256=oracle_hash,
            spdx_license=spdx,
            license_notice_path=license_path,
            license_notice_sha256=license_hash,
            wrapper_path=wrapper_path,
            source_sha256=wrapper_hash,
            protocols=tuple(protocols),
            operator_parity_scope=parity_scope,
            parity_evidence_path=parity_path,
            parity_evidence_sha256=parity_hash,
            configuration_provenance=configuration_kind,
            search_space_path=search_path,
            search_space_sha256=search_hash,
            final_config_path=final_path,
            final_config_sha256=final_hash,
            selection_evidence_path=selection_path,
            selection_evidence_sha256=selection_hash,
            parameter_count_verified=True,
            spmv_count_verified=True,
            independent_operator_oracle_verified=True,
            official_task_contract_verified=True,
        )
    missing = sorted(set(required_methods) - set(records))
    extra = sorted(set(records) - set(required_methods))
    if missing or extra:
        raise ArtifactValidationError(
            f"baseline registry scope mismatch; missing={missing}, extra={extra}"
        )
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
    if any(
        type(value) not in (int, float)
        or not math.isfinite(float(value))
        or not 0 <= float(value) < 1
        for value in thresholds.values()
    ):
        raise ArtifactValidationError("practical tie thresholds must be finite in [0,1)")
    registry_hash = _sha256(data["baseline_registry_sha256"], "baseline registry")
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
        admission="confirmatory",
        expected_trial_budget=plan.trial_budget_per_method_dataset,
    )
    return plan, baselines


__all__ = [
    "ConfirmatoryPlan",
    "LOCAL_SEARCH",
    "PARITY_EVIDENCE_SCHEMA",
    "PLAN_SCHEMA",
    "REGISTRY_SCHEMA",
    "SEARCH_SPACE_SCHEMA",
    "SELECTION_EVIDENCE_SCHEMA",
    "UPSTREAM_CONFIG",
    "VerifiedBaseline",
    "validate_baseline_registry",
    "validate_confirmatory_plan",
    "validate_plan_registry_binding",
]
