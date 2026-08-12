"""Deterministic, validation-only hyperparameter screening contracts.

This module defines candidate identity and selection policy; it does not run
training, access datasets, or expose a test partition.  Candidate subsets are
chosen without a language/runtime PRNG by SHA-256 ranking, so a frozen seed and
hash-bound search spaces completely determine every method--dataset trial.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Final, Mapping, Sequence

from gbdn.artifacts import (
    ArtifactValidationError,
    canonical_json_bytes,
    canonical_json_sha256,
)
from gbdn.baseline_contract import SEARCH_SPACE_SCHEMA
from gbdn.heterophily_contract import DATASET_REGISTRY, resolve_dataset


SCREENING_MANIFEST_SCHEMA: Final[str] = "gbdn-validation-screening-manifest-v1"
CANDIDATE_SCHEMA: Final[str] = "gbdn-validation-screening-candidate-v1"
OBSERVATION_SCHEMA: Final[str] = "gbdn-validation-screening-observation-v1"
DECISION_SCHEMA: Final[str] = "gbdn-validation-screening-decision-v1"
SAMPLING_POLICY: Final[str] = "sha256_rank_without_replacement-v1"
SELECTION_POLICY: Final[str] = "maximize_mean_validation_metric_then_candidate_sha256-v1"

_MAX_JSON_BYTES: Final[int] = 4 * 1024 * 1024
_MAX_CANDIDATES: Final[int] = 1_000_000
_MAX_SEED: Final[int] = 2**63 - 1
_NAME: Final[re.Pattern[str]] = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
_VALIDATION_UNIT: Final[re.Pattern[str]] = re.compile(r"split=[0-9]+/seed=[0-9]+")
_SECTIONS: Final[tuple[str, ...]] = ("model", "optimizer", "training")


def _reject_constant(value: str) -> None:
    raise ArtifactValidationError(f"non-standard JSON constant: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ArtifactValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_canonical_object(path: str | Path, *, label: str) -> tuple[dict[str, Any], bytes]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise ArtifactValidationError(f"{label} must be a regular file")
    payload = target.read_bytes()
    if not payload or len(payload) > _MAX_JSON_BYTES:
        raise ArtifactValidationError(f"{label} must be bounded nonempty JSON")
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError(f"{label} must be valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ArtifactValidationError(f"{label} root must be an object")
    try:
        canonical = canonical_json_bytes(value)
    except (TypeError, ValueError) as exc:
        raise ArtifactValidationError(f"{label} contains a non-finite or invalid value") from exc
    # Repository-authored compact JSON convention permits one POSIX EOF newline.
    if payload not in {canonical, canonical + b"\n"}:
        raise ArtifactValidationError(f"{label} must use canonical JSON encoding")
    return value, payload


def _source_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ArtifactValidationError("search-space source path is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ArtifactValidationError("search-space source path must be a safe relative POSIX path")
    return path.as_posix()


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ArtifactValidationError(f"{label} keys do not match the frozen schema")


def _parameter_path(value: Any) -> tuple[str, str]:
    if not isinstance(value, str):
        raise ArtifactValidationError("search parameter path must be a string")
    parts = value.split(".")
    if (
        len(parts) != 2
        or parts[0] not in _SECTIONS
        or any(_NAME.fullmatch(part) is None for part in parts)
    ):
        raise ArtifactValidationError(
            f"search parameter path must be section.field with a supported section: {value!r}"
        )
    return parts[0], parts[1]


def _canonical_value_key(value: Any) -> bytes:
    try:
        return canonical_json_bytes(value)
    except (TypeError, ValueError) as exc:
        raise ArtifactValidationError("search parameter contains an invalid JSON value") from exc


@dataclass(frozen=True)
class SearchParameter:
    path: str
    role: str
    values: tuple[Any, ...]


@dataclass(frozen=True)
class FrozenSearchSpace:
    method: str
    source_path: str
    source_sha256: str
    parameters: tuple[SearchParameter, ...]
    candidate_count: int


@dataclass(frozen=True)
class ScreeningCandidate:
    method: str
    search_space_sha256: str
    configuration: Mapping[str, Mapping[str, Any]]
    candidate_sha256: str

    def payload(self) -> dict[str, Any]:
        return {
            "configuration": {
                section: dict(self.configuration[section]) for section in _SECTIONS
            },
            "method": self.method,
            "schema_version": CANDIDATE_SCHEMA,
            "search_space_sha256": self.search_space_sha256,
        }


@dataclass(frozen=True)
class ScreeningTrial:
    method: str
    dataset: str
    trial_id: int
    candidate: ScreeningCandidate
    rank_sha256: str

    def payload(self) -> dict[str, Any]:
        return {
            "candidate": self.candidate.payload(),
            "candidate_sha256": self.candidate.candidate_sha256,
            "dataset": self.dataset,
            "method": self.method,
            "rank_sha256": self.rank_sha256,
            "trial_id": self.trial_id,
        }


@dataclass(frozen=True)
class ScreeningSchedule:
    screening_seed: int
    trial_budget_per_method_dataset: int
    search_spaces: tuple[FrozenSearchSpace, ...]
    datasets: tuple[str, ...]
    validation_unit_ids: tuple[str, ...]
    trials: tuple[ScreeningTrial, ...]

    def payload(self) -> dict[str, Any]:
        return {
            "datasets": list(self.datasets),
            "policy": {
                "candidate_sampling": SAMPLING_POLICY,
                "equal_integer_budget_per_method_dataset": True,
                "partition": "validation",
                "selection": SELECTION_POLICY,
                "test_used_for_selection": False,
            },
            "schema_version": SCREENING_MANIFEST_SCHEMA,
            "screening_seed": self.screening_seed,
            "search_spaces": [
                {
                    "candidate_count": space.candidate_count,
                    "method": space.method,
                    "path": space.source_path,
                    "sha256": space.source_sha256,
                }
                for space in self.search_spaces
            ],
            "trial_budget_per_method_dataset": self.trial_budget_per_method_dataset,
            "trials": [trial.payload() for trial in self.trials],
            "validation_unit_ids": list(self.validation_unit_ids),
        }

    @property
    def sha256(self) -> str:
        return canonical_json_sha256(self.payload())


@dataclass(frozen=True)
class ScreeningDecision:
    method: str
    dataset: str
    candidate_sha256: str
    trial_id: int
    validation_metric: str
    mean_validation_metric: float
    observation_sha256: str
    candidate_observations: tuple[tuple[int, str, str], ...]
    screening_manifest_sha256: str

    def payload(self) -> dict[str, Any]:
        return {
            "candidate_sha256": self.candidate_sha256,
            "candidate_observations": [
                {
                    "candidate_sha256": candidate_sha256,
                    "observation_sha256": observation_sha256,
                    "trial_id": trial_id,
                }
                for trial_id, candidate_sha256, observation_sha256 in self.candidate_observations
            ],
            "dataset": self.dataset,
            "mean_validation_metric": self.mean_validation_metric,
            "method": self.method,
            "observation_sha256": self.observation_sha256,
            "schema_version": DECISION_SCHEMA,
            "screening_manifest_sha256": self.screening_manifest_sha256,
            "selection_partition": "validation",
            "selection_policy": SELECTION_POLICY,
            "test_used_for_selection": False,
            "trial_id": self.trial_id,
            "validation_metric": self.validation_metric,
        }


def _repository_file(root: Path, relative: str, *, label: str) -> Path:
    safe = _source_path(relative)
    lexical = root / PurePosixPath(safe)
    if lexical.is_symlink() or not lexical.is_file():
        raise ArtifactValidationError(f"{label} must be a regular repository file")
    resolved = lexical.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ArtifactValidationError(f"{label} escapes repository root")
    return resolved


def load_search_space(
    path: str | Path,
    *,
    source_path: str,
) -> FrozenSearchSpace:
    """Validate one canonical search-space file and compute its Cartesian size."""

    data, payload = _load_canonical_object(path, label="screening search space")
    _exact_keys(data, {"method", "parameters", "schema_version", "status"}, "search space")
    method = data["method"]
    if (
        data["schema_version"] != SEARCH_SPACE_SCHEMA
        or data["status"] != "FROZEN_PRESPECIFIED"
        or not isinstance(method, str)
        or not method
        or not isinstance(data["parameters"], dict)
        or not data["parameters"]
    ):
        raise ArtifactValidationError("screening search-space identity is invalid")

    parameters: list[SearchParameter] = []
    tuned = 0
    section_counts = {section: 0 for section in _SECTIONS}
    candidate_count = 1
    for name in sorted(data["parameters"]):
        section, _ = _parameter_path(name)
        specification = data["parameters"][name]
        if not isinstance(specification, dict):
            raise ArtifactValidationError(f"search parameter {name} must be an object")
        _exact_keys(specification, {"role", "values"}, f"search parameter {name}")
        role = specification["role"]
        values = specification["values"]
        if role not in {"FIXED", "TUNED"} or not isinstance(values, list) or not values:
            raise ArtifactValidationError(f"search parameter {name} has an invalid role/value list")
        keys = [_canonical_value_key(value) for value in values]
        if len(set(keys)) != len(keys):
            raise ArtifactValidationError(
                f"search parameter {name} contains exact-type duplicate values"
            )
        if (role == "FIXED" and len(values) != 1) or (role == "TUNED" and len(values) < 2):
            raise ArtifactValidationError(f"search parameter {name} role contradicts its values")
        tuned += role == "TUNED"
        section_counts[section] += 1
        candidate_count *= len(values)
        if candidate_count > _MAX_CANDIDATES:
            raise ArtifactValidationError("screening Cartesian space exceeds the safety limit")
        parameters.append(SearchParameter(name, role, tuple(values)))
    if tuned == 0 or any(count == 0 for count in section_counts.values()):
        raise ArtifactValidationError(
            "search space must tune at least one parameter and fully specify all config sections"
        )
    return FrozenSearchSpace(
        method=method,
        source_path=_source_path(source_path),
        source_sha256=hashlib.sha256(payload).hexdigest(),
        parameters=tuple(parameters),
        candidate_count=candidate_count,
    )


def enumerate_candidates(space: FrozenSearchSpace) -> tuple[ScreeningCandidate, ...]:
    """Enumerate the full Cartesian space in canonical parameter/value order."""

    candidates: list[ScreeningCandidate] = []
    for combination in itertools.product(*(parameter.values for parameter in space.parameters)):
        configuration: dict[str, dict[str, Any]] = {section: {} for section in _SECTIONS}
        for parameter, value in zip(space.parameters, combination, strict=True):
            section, field = parameter.path.split(".")
            configuration[section][field] = value
        payload = {
            "configuration": configuration,
            "method": space.method,
            "schema_version": CANDIDATE_SCHEMA,
            "search_space_sha256": space.source_sha256,
        }
        candidates.append(
            ScreeningCandidate(
                method=space.method,
                search_space_sha256=space.source_sha256,
                configuration=configuration,
                candidate_sha256=canonical_json_sha256(payload),
            )
        )
    if len(candidates) != space.candidate_count or len(
        {candidate.candidate_sha256 for candidate in candidates}
    ) != len(candidates):
        raise ArtifactValidationError("screening candidate enumeration is not one-to-one")
    return tuple(candidates)


def build_screening_schedule(
    search_spaces: Sequence[FrozenSearchSpace],
    *,
    datasets: Sequence[str],
    validation_unit_ids: Sequence[str],
    screening_seed: int,
    trial_budget_per_method_dataset: int,
) -> ScreeningSchedule:
    """Freeze equal-budget method--dataset trials by cryptographic ranking."""

    if type(screening_seed) is not int or not 0 <= screening_seed <= _MAX_SEED:
        raise ArtifactValidationError("screening seed must be a nonnegative signed-64-bit integer")
    budget = trial_budget_per_method_dataset
    if type(budget) is not int or budget <= 0:
        raise ArtifactValidationError("screening trial budget must be a positive exact integer")
    if not search_spaces:
        raise ArtifactValidationError("at least one screening search space is required")
    spaces = tuple(sorted(search_spaces, key=lambda item: item.method))
    if len({space.method for space in spaces}) != len(spaces):
        raise ArtifactValidationError("screening methods must be unique")
    if any(space.candidate_count < budget for space in spaces):
        raise ArtifactValidationError("equal trial budget exceeds at least one candidate space")

    units = tuple(validation_unit_ids)
    if (
        not units
        or any(not isinstance(unit, str) or _VALIDATION_UNIT.fullmatch(unit) is None for unit in units)
        or len(set(units)) != len(units)
    ):
        raise ArtifactValidationError(
            "validation unit IDs must be unique split=<int>/seed=<int> strings"
        )

    resolved_datasets = tuple(resolve_dataset(value).canonical_name for value in datasets)
    if resolved_datasets != tuple(DATASET_REGISTRY):
        raise ArtifactValidationError(
            "screening datasets must be all five official tasks in canonical order"
        )

    trials: list[ScreeningTrial] = []
    for space in spaces:
        candidates = enumerate_candidates(space)
        for dataset in resolved_datasets:
            ranked: list[tuple[str, str, ScreeningCandidate]] = []
            for candidate in candidates:
                rank_payload = {
                    "candidate_sha256": candidate.candidate_sha256,
                    "dataset": dataset,
                    "method": space.method,
                    "policy": SAMPLING_POLICY,
                    "screening_seed": screening_seed,
                    "search_space_sha256": space.source_sha256,
                }
                rank = canonical_json_sha256(rank_payload)
                ranked.append((rank, candidate.candidate_sha256, candidate))
            ranked.sort(key=lambda item: (item[0], item[1]))
            for trial_id, (rank, _, candidate) in enumerate(ranked[:budget]):
                trials.append(
                    ScreeningTrial(space.method, dataset, trial_id, candidate, rank)
                )
    return ScreeningSchedule(screening_seed, budget, spaces, resolved_datasets, units, tuple(trials))


def validate_screening_manifest(
    path: str | Path,
    *,
    repository_root: str | Path,
) -> ScreeningSchedule:
    """Rebuild a canonical manifest from its hash-bound search-space sources."""

    data, _ = _load_canonical_object(path, label="screening manifest")
    _exact_keys(
        data,
        {
            "datasets",
            "policy",
            "schema_version",
            "screening_seed",
            "search_spaces",
            "trial_budget_per_method_dataset",
            "trials",
            "validation_unit_ids",
        },
        "screening manifest",
    )
    expected_policy = {
        "candidate_sampling": SAMPLING_POLICY,
        "equal_integer_budget_per_method_dataset": True,
        "partition": "validation",
        "selection": SELECTION_POLICY,
        "test_used_for_selection": False,
    }
    if data["schema_version"] != SCREENING_MANIFEST_SCHEMA or data["policy"] != expected_policy:
        raise ArtifactValidationError("screening manifest policy is invalid")
    records = data["search_spaces"]
    if not isinstance(records, list) or not records:
        raise ArtifactValidationError("screening manifest has no search spaces")
    root = Path(repository_root).resolve(strict=True)
    spaces: list[FrozenSearchSpace] = []
    for record in records:
        if not isinstance(record, dict):
            raise ArtifactValidationError("screening search-space record must be an object")
        _exact_keys(record, {"candidate_count", "method", "path", "sha256"}, "search-space record")
        relative = _source_path(record["path"])
        space = load_search_space(
            _repository_file(root, relative, label="screening search space"),
            source_path=relative,
        )
        if (
            record["method"] != space.method
            or record["sha256"] != space.source_sha256
            or record["candidate_count"] != space.candidate_count
        ):
            raise ArtifactValidationError("screening manifest search-space binding differs")
        spaces.append(space)
    schedule = build_screening_schedule(
        spaces,
        datasets=data["datasets"],
        validation_unit_ids=data["validation_unit_ids"],
        screening_seed=data["screening_seed"],
        trial_budget_per_method_dataset=data["trial_budget_per_method_dataset"],
    )
    if canonical_json_bytes(schedule.payload()) != canonical_json_bytes(data):
        raise ArtifactValidationError("screening manifest differs from deterministic reconstruction")
    return schedule


def select_validation_winners(
    schedule: ScreeningSchedule,
    observations: Sequence[Mapping[str, Any]],
) -> tuple[ScreeningDecision, ...]:
    """Select one candidate per pair from complete validation-only observations.

    Every candidate must be evaluated on the same ordered validation units for
    a dataset.  The exact schema has no test-score field and rejects a record
    unless it explicitly attests that test data was not used for selection.
    """

    expected = {
        (trial.method, trial.dataset, trial.trial_id): trial for trial in schedule.trials
    }
    if len(observations) != len(expected):
        raise ArtifactValidationError("screening observations are incomplete or excessive")
    parsed: dict[tuple[str, str, int], tuple[float, str, str, tuple[str, ...]]] = {}
    for raw in observations:
        if not isinstance(raw, Mapping):
            raise ArtifactValidationError("screening observation must be an object")
        _exact_keys(
            raw,
            {
                "candidate_sha256",
                "dataset",
                "evaluation_unit_ids",
                "method",
                "schema_version",
                "selection_partition",
                "test_used_for_selection",
                "trial_id",
                "validation_metric",
                "validation_values",
            },
            "screening observation",
        )
        trial_id = raw["trial_id"]
        if type(trial_id) is not int or trial_id < 0:
            raise ArtifactValidationError("screening observation trial_id is invalid")
        key = (raw["method"], raw["dataset"], trial_id)
        if key in parsed or key not in expected:
            raise ArtifactValidationError("screening observation identity is unknown or duplicate")
        trial = expected[key]
        spec = resolve_dataset(trial.dataset)
        units = raw["evaluation_unit_ids"]
        values = raw["validation_values"]
        if (
            raw["schema_version"] != OBSERVATION_SCHEMA
            or raw["candidate_sha256"] != trial.candidate.candidate_sha256
            or raw["selection_partition"] != "validation"
            or raw["test_used_for_selection"] is not False
            or raw["validation_metric"] != spec.selection_metric
            or not isinstance(units, list)
            or not units
            or any(not isinstance(unit, str) or not unit for unit in units)
            or len(set(units)) != len(units)
            or not isinstance(values, list)
            or len(values) != len(units)
            or any(
                type(value) not in (int, float)
                or not math.isfinite(float(value))
                or not 0.0 <= float(value) <= 1.0
                for value in values
            )
        ):
            raise ArtifactValidationError(
                "screening observation is not official-metric validation-only evidence"
            )
        frozen_units = tuple(units)
        if frozen_units != schedule.validation_unit_ids:
            raise ArtifactValidationError(
                "all methods and candidates must use the manifest-frozen validation units"
            )
        score = math.fsum(float(value) for value in values) / len(values)
        observation_hash = canonical_json_sha256(dict(raw))
        parsed[key] = (score, raw["validation_metric"], observation_hash, frozen_units)

    decisions: list[ScreeningDecision] = []
    for method in (space.method for space in schedule.search_spaces):
        for dataset in schedule.datasets:
            choices: list[tuple[float, str, int, str, str]] = []
            for trial_id in range(schedule.trial_budget_per_method_dataset):
                trial = expected[(method, dataset, trial_id)]
                score, metric, observation_hash, _ = parsed[(method, dataset, trial_id)]
                choices.append(
                    (score, trial.candidate.candidate_sha256, trial_id, metric, observation_hash)
                )
            winner = sorted(choices, key=lambda item: (-item[0], item[1]))[0]
            candidate_observations = tuple(
                (item[2], item[1], item[4])
                for item in sorted(choices, key=lambda item: item[2])
            )
            decisions.append(
                ScreeningDecision(
                    method=method,
                    dataset=dataset,
                    candidate_sha256=winner[1],
                    trial_id=winner[2],
                    validation_metric=winner[3],
                    mean_validation_metric=winner[0],
                    observation_sha256=winner[4],
                    candidate_observations=candidate_observations,
                    screening_manifest_sha256=schedule.sha256,
                )
            )
    return tuple(decisions)


__all__ = [
    "CANDIDATE_SCHEMA",
    "DECISION_SCHEMA",
    "OBSERVATION_SCHEMA",
    "SAMPLING_POLICY",
    "SCREENING_MANIFEST_SCHEMA",
    "SELECTION_POLICY",
    "FrozenSearchSpace",
    "ScreeningCandidate",
    "ScreeningDecision",
    "ScreeningSchedule",
    "ScreeningTrial",
    "build_screening_schedule",
    "enumerate_candidates",
    "load_search_space",
    "select_validation_winners",
    "validate_screening_manifest",
]
