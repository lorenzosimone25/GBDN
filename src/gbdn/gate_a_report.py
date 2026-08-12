"""Read-only Gate-A pytest coverage and execution reporting.

The report distinguishes an executed test ID from scientific Gate-A
acceptance. It never edits tests or result trees and emits deterministic JSON
without timestamps. Frozen fixture declarations are cross-validated against
typed computed evidence rather than inferred from test names, so provenance
drift remains visible even when every ID has a passing pytest node.
"""

from __future__ import annotations

from collections import defaultdict
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
import argparse
import hashlib
import inspect
import io
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from typing import Any, Final

from gbdn.gate_a_evidence import (
    EVIDENCE_SCHEMA,
    evaluate_gate_a_evidence,
    evidence_decision_failures,
    evidence_field_counts,
    validate_evidence_catalog,
)


REPORT_SCHEMA: Final[str] = "gbdn-gate-a-coverage-v3"
REQUIRED_IDS: Final[tuple[str, ...]] = tuple(f"GA-{index:02d}" for index in range(36))

NUMERICAL_TOLERANCES: Final[dict[str, float]] = {
    "scalar_absolute": 5e-12,
    "exact_operator_relative": 1e-10,
    "exact_energy_relative": 1e-10,
    "zero_denominator_absolute": 1e-12,
    "sparse_dense_operator_relative": 1e-8,
    "inequality_relative_slack": 1e-10,
}

REQUIRED_FIXTURE_MATRIX: Final[tuple[str, ...]] = (
    "paths-at-least-two-sizes",
    "even-cycle",
    "odd-cycle-with-repeated-eigenvalues",
    "rectangular-grid",
    "star",
    "complete-with-repeated-eigenspace",
    "disconnected-union",
    "random-undirected-positive-nonuniform-weights",
    "equal-sized-nonisomorphic-pair",
    "asymmetric-directed-knn-policy-input",
    "negative-weight-policy-input",
)

FIXTURE_MATRIX_DECLARATION: Final[dict[str, dict[str, Any]]] = {
    "paths-at-least-two-sizes": {
        "declared_covered": True,
        "observed_sizes": [2, 5, 6, 7, 8, 9, 10, 14, 20],
        "observed_gate_ids": ["GA-03", "GA-04", "GA-05", "GA-06", "GA-07", "GA-09", "GA-17", "GA-19"],
    },
    "even-cycle": {
        "declared_covered": True,
        "observed_sizes": [6, 10],
        "observed_gate_ids": ["GA-03", "GA-04", "GA-05", "GA-06", "GA-07", "GA-09", "GA-17"],
    },
    "odd-cycle-with-repeated-eigenvalues": {
        "declared_covered": True,
        "observed_sizes": [7, 9],
        "observed_gate_ids": ["GA-05", "GA-06", "GA-07", "GA-09", "GA-19"],
    },
    "rectangular-grid": {
        "declared_covered": True,
        "observed_sizes": [8],
        "observed_gate_ids": ["GA-03", "GA-04", "GA-05", "GA-06", "GA-07", "GA-09", "GA-19"],
    },
    "star": {
        "declared_covered": True,
        "observed_sizes": [7],
        "observed_gate_ids": ["GA-03", "GA-04", "GA-05", "GA-06", "GA-07", "GA-09", "GA-19"],
    },
    "complete-with-repeated-eigenspace": {
        "declared_covered": True,
        "observed_sizes": [5, 6],
        "observed_gate_ids": ["GA-03", "GA-04", "GA-05", "GA-06", "GA-07", "GA-09", "GA-11", "GA-13", "GA-16"],
    },
    "disconnected-union": {
        "declared_covered": True,
        "observed_sizes": [6, 7],
        "observed_gate_ids": ["GA-03", "GA-04", "GA-05", "GA-06", "GA-07", "GA-09", "GA-34"],
    },
    "random-undirected-positive-nonuniform-weights": {
        "declared_covered": True,
        "observed_sizes": [8],
        "observed_gate_ids": ["GA-03", "GA-04", "GA-05", "GA-06", "GA-07", "GA-09", "GA-19"],
        "fixture_policy": "frozen-seed-1701-edge-and-positive-weight-list",
    },
    "equal-sized-nonisomorphic-pair": {
        "declared_covered": True,
        "observed_sizes": [10],
        "observed_gate_ids": ["GA-17"],
    },
    "asymmetric-directed-knn-policy-input": {
        "declared_covered": True,
        "observed_sizes": [5],
        "observed_gate_ids": ["GA-00"],
        "policy_result": "core-rejection",
    },
    "negative-weight-policy-input": {
        "declared_covered": True,
        "observed_sizes": [2],
        "observed_gate_ids": ["GA-00"],
    },
}

EXACT_MULTILEVEL_MATRIX: Final[dict[str, dict[str, Any]]] = {
    "paths-at-least-two-sizes": {
        "required_sizes_minimum": 2,
        "required_depths": [1, 2, 4, 8, 16],
        "observed_sizes": [5, 6, 8],
        "observed_depths": [1, 2, 4, 8, 16],
        "complete": True,
        "missing": [],
    },
    "even-cycle": {
        "required_sizes_minimum": 1,
        "required_depths": [1, 2, 4, 8, 16],
        "observed_sizes": [6],
        "observed_depths": [1, 2, 4, 8, 16],
        "complete": True,
        "missing": [],
    },
    "odd-cycle-with-repeated-eigenvalues": {
        "required_sizes_minimum": 1,
        "required_depths": [1, 2, 4, 8, 16],
        "observed_sizes": [7],
        "observed_depths": [1, 2, 4, 8, 16],
        "complete": True,
        "missing": [],
    },
    "rectangular-grid": {
        "required_sizes_minimum": 1,
        "required_depths": [1, 2, 4, 8, 16],
        "observed_sizes": [8],
        "observed_depths": [1, 2, 4, 8, 16],
        "complete": True,
        "missing": [],
    },
    "star": {
        "required_sizes_minimum": 1,
        "required_depths": [1, 2, 4, 8, 16],
        "observed_sizes": [7],
        "observed_depths": [1, 2, 4, 8, 16],
        "complete": True,
        "missing": [],
    },
    "complete-with-repeated-eigenspace": {
        "required_sizes_minimum": 1,
        "required_depths": [1, 2, 4, 8, 16],
        "observed_sizes": [5],
        "observed_depths": [1, 2, 4, 8, 16],
        "complete": True,
        "missing": [],
    },
    "disconnected-union": {
        "required_sizes_minimum": 1,
        "required_depths": [1, 2, 4, 8, 16],
        "observed_sizes": [6],
        "observed_depths": [1, 2, 4, 8, 16],
        "complete": True,
        "missing": [],
    },
    "random-undirected-positive-nonuniform-weights": {
        "required_sizes_minimum": 1,
        "required_depths": [1, 2, 4, 8, 16],
        "observed_sizes": [8],
        "observed_depths": [1, 2, 4, 8, 16],
        "complete": True,
        "missing": [],
    },
}

ROW_MATRIX_DECLARATION: Final[dict[str, dict[str, Any]]] = {
    "GA-03": {
        "dimension": "valid-spectral-graph-fixture-matrix",
        "required": [
            "paths-at-least-two-sizes", "even-cycle",
            "odd-cycle-with-repeated-eigenvalues", "rectangular-grid", "star",
            "complete-with-repeated-eigenspace", "disconnected-union",
            "random-undirected-positive-nonuniform-weights",
        ],
        "observed": [
            "paths-at-least-two-sizes", "even-cycle",
            "odd-cycle-with-repeated-eigenvalues", "rectangular-grid", "star",
            "complete-with-repeated-eigenspace", "disconnected-union",
            "random-undirected-positive-nonuniform-weights",
        ],
        "not_applicable": ["invalid-policy-inputs", "equal-sized-pair-as-a-pair"],
    },
    "GA-04": {
        "dimension": "valid-spectral-graph-fixture-matrix",
        "required": [
            "paths-at-least-two-sizes", "even-cycle",
            "odd-cycle-with-repeated-eigenvalues", "rectangular-grid", "star",
            "complete-with-repeated-eigenspace", "disconnected-union",
            "random-undirected-positive-nonuniform-weights",
        ],
        "observed": [
            "paths-at-least-two-sizes", "even-cycle",
            "odd-cycle-with-repeated-eigenvalues", "rectangular-grid", "star",
            "complete-with-repeated-eigenspace", "disconnected-union",
            "random-undirected-positive-nonuniform-weights",
        ],
        "not_applicable": ["invalid-policy-inputs", "equal-sized-pair-as-a-pair"],
    },
    "GA-05": {
        "dimension": "graph-spectrum-fixtures",
        "required": [
            "paths-at-least-two-sizes",
            "even-cycle",
            "odd-cycle-with-repeated-eigenvalues",
            "rectangular-grid",
            "star",
            "complete-with-repeated-eigenspace",
            "disconnected-union",
            "random-undirected-positive-nonuniform-weights",
        ],
        "observed": [
            "paths-at-least-two-sizes", "even-cycle",
            "odd-cycle-with-repeated-eigenvalues", "rectangular-grid", "star",
            "complete-with-repeated-eigenspace", "disconnected-union",
            "random-undirected-positive-nonuniform-weights",
        ],
    },
    "GA-19": {
        "dimension": "chebyshev-degree",
        "required": [4, 8, 16, 32, 128],
        "observed": [4, 8, 16, 32, 128],
    },
}

ROOT_FIXTURE_DECLARATION: Final[dict[str, dict[str, Any]]] = {
    "real-interior": {
        "presence_observed": True,
        "observed_gate_ids": ["GA-02", "GA-03", "GA-04", "GA-06", "GA-07", "GA-09", "GA-32", "GA-34"],
        "acceptance_complete": True,
        "missing": [],
    },
    "generic-complex": {
        "presence_observed": True,
        "observed_gate_ids": ["GA-02", "GA-03", "GA-04", "GA-06", "GA-07", "GA-09", "GA-24"],
        "acceptance_complete": True,
        "missing": [],
    },
    "multi-root-product": {
        "presence_observed": True,
        "observed_gate_ids": ["GA-02", "GA-03", "GA-04", "GA-05", "GA-06", "GA-07", "GA-09", "GA-24"],
        "acceptance_complete": True,
        "missing": [],
    },
    "conjugate-symmetric-pair-where-relevant": {
        "presence_observed": True,
        "observed_gate_ids": ["GA-02", "GA-03", "GA-04", "GA-06", "GA-07", "GA-09", "GA-19"],
        "acceptance_complete": True,
        "missing": [],
    },
    "near-radius-cap": {
        "presence_observed": True,
        "observed_gate_ids": ["GA-01", "GA-02", "GA-03", "GA-04", "GA-06", "GA-07", "GA-09"],
        "acceptance_complete": True,
        "missing": [],
    },
    "unrestricted-radial-polar": {
        "presence_observed": True,
        "observed_gate_ids": ["GA-01"],
        "acceptance_complete": True,
        "missing": [],
    },
    "exact-center-width": {
        "presence_observed": True,
        "observed_gate_ids": ["GA-01", "GA-23"],
        "acceptance_complete": True,
        "missing": [],
    },
}

REALIZATION_TAGS: Final[dict[str, tuple[str, ...]]] = {
    **{f"GA-{index:02d}": ("exact",) for index in range(36)},
    "GA-08": ("exact", "chebyshev-K"),
    "GA-10": ("exact", "chebyshev-K"),
    "GA-14": ("exact", "chebyshev-K"),
    "GA-15": ("exact", "chebyshev-K"),
    "GA-17": ("chebyshev-K",),
    "GA-18": ("chebyshev-K",),
    "GA-19": ("chebyshev-K",),
    "GA-20": ("exact", "chebyshev-K"),
    "GA-21": ("exact", "chebyshev-K"),
    "GA-22": ("exact", "chebyshev-K"),
    "GA-24": ("exact", "chebyshev-K"),
    "GA-29": ("exact", "chebyshev-K"),
    "GA-30": ("chebyshev-K",),
    "GA-31": ("exact", "chebyshev-K"),
    "GA-34": ("exact", "chebyshev-K"),
    "GA-35": ("chebyshev-K",),
}

ID_FIXTURES: Final[dict[str, tuple[str, ...]]] = {
    "GA-00": (
        "directed-knn-rejection-input",
        "negative-weight-rejection-input",
        "reciprocal-mean-laplacian",
        "reciprocal-mean-output",
        "reciprocal-mean-policy-input",
        "sphere-directed-knn-preprocessed-output",
        "sphere-validated-laplacian",
    ),
    "GA-03": ("complete_5", "cycle_even_6", "cycle_odd_7", "disconnected_7", "grid_2x4", "path_5", "path_8", "random_weighted_seed_1701", "star_7"),
    "GA-04": ("complete_5", "cycle_even_6", "cycle_odd_7", "disconnected_7", "grid_2x4", "path_5", "path_8", "random_weighted_seed_1701", "star_7"),
    "GA-05": ("complete_5", "cycle_even_6", "cycle_odd_7", "disconnected_7", "grid_2x4", "path_5", "path_8", "random_weighted_seed_1701", "star_7"),
    "GA-06": ("complete_5", "cycle_even_6", "cycle_odd_7", "disconnected_7", "grid_2x4", "path_5", "path_8", "random_weighted_seed_1701", "star_7"),
    "GA-07": ("complete_5", "cycle_even_6", "cycle_odd_7", "disconnected_7", "grid_2x4", "path_5", "path_8", "random_weighted_seed_1701", "star_7"),
    "GA-08": ("path_8",),
    "GA-09": ("complete_5", "cycle_even_6", "cycle_odd_7", "disconnected_7", "grid_2x4", "path_5", "path_8", "random_weighted_seed_1701", "star_7"),
    "GA-10": ("weighted_6",),
    "GA-11": ("complete_5",),
    "GA-12": ("path_2",),
    "GA-13": ("weighted_6",),
    "GA-14": ("weighted_6",),
    "GA-15": ("weighted_6", "weighted_6_permuted"),
    "GA-16": ("complete_6",),
    "GA-17": ("cycle_even_10", "path_10"),
    "GA-18": ("path_8",),
    "GA-19": ("cycle_odd_9", "grid_2x4", "path_8", "random_weighted_seed_1701", "star_7"),
    "GA-20": ("path_9",),
    "GA-21": ("complete_5", "path_8", "weighted_6"),
    "GA-22": ("complete_5", "path_8", "weighted_6"),
    "GA-24": ("path_9",),
    "GA-28": ("weighted_path_8_base", "weighted_path_8_scale_0.0001", "weighted_path_8_scale_0.001", "weighted_path_8_scale_0.01"),
    "GA-29": ("path_14",),
    "GA-30": ("path_8",),
    "GA-31": ("weighted_6",),
    "GA-32": ("cycle_odd_7",),
    "GA-33": ("path_6",),
    "GA-34": ("disconnected_6", "path_20", "path_8"),
    "GA-35": ("path_6",),
}

ID_DEPTHS: Final[dict[str, tuple[int, ...]]] = {
    "GA-05": (16,),
    "GA-06": (1, 2, 4, 8, 16),
    "GA-07": (1, 2, 4, 8, 16),
    "GA-09": (1, 2, 4, 8, 16),
    "GA-08": (3,),
    "GA-10": (2,),
    "GA-11": (8,),
    "GA-12": (1,),
    "GA-15": (4,),
    "GA-22": (1, 2, 4, 8, 16),
    "GA-30": (1, 2, 4),
    "GA-31": (4,),
    "GA-32": (1,),
    "GA-33": (8,),
    "GA-34": (1, 4),
}

ID_DEGREES: Final[dict[str, tuple[int, ...]]] = {
    "GA-10": (4,),
    "GA-14": (8,),
    "GA-15": (12,),
    "GA-17": (3,),
    "GA-18": (12,),
    "GA-19": (4, 8, 16, 32, 128),
    "GA-20": (4, 8, 16, 32),
    "GA-21": (8, 16),
    "GA-22": (8, 12, 16),
    "GA-24": (12,),
    "GA-29": (3,),
    "GA-30": (0, 3, 4, 5),
    "GA-31": (8,),
    "GA-34": (1,),
}

ID_ROOTS: Final[dict[str, tuple[str, ...]]] = {
    "GA-00": ("public_exact_control",),
    "GA-01": ("exact-center-width-extremes", "radial-polar-extremes"),
    "GA-02": ("conjugate_pair", "generic_complex", "multi_root", "near_radius_cap", "real_interior"),
    "GA-03": ("conjugate_pair", "generic_complex", "multi_root", "near_radius_cap", "real_interior"),
    "GA-04": ("conjugate_pair", "generic_complex", "multi_root", "near_radius_cap", "real_interior"),
    "GA-05": ("conjugate_pair", "generic_complex", "multi_root", "near_radius_cap", "real_interior"),
    "GA-06": ("conjugate_pair", "generic_complex", "multi_root", "near_radius_cap", "real_interior"),
    "GA-07": ("conjugate_pair", "generic_complex", "multi_root", "near_radius_cap", "real_interior"),
    "GA-08": ("generic_complex",),
    "GA-09": ("conjugate_pair", "generic_complex", "multi_root", "near_radius_cap", "real_interior"),
    "GA-10": ("public_model_layer_0", "public_model_layer_1"),
    "GA-11": ("multi_root",),
    "GA-12": ("generic_complex",),
    "GA-13": ("spectral_selection",),
    "GA-14": ("multi-root-first-two",),
    "GA-15": ("conjugate_pair", "generic_complex", "multi_root", "real_interior"),
    "GA-16": ("multi_root",),
    "GA-19": ("conjugate_pair", "generic_complex", "multi_root"),
    "GA-20": ("generic_complex", "multi_root", "near_radius_cap"),
    "GA-21": ("generic_complex",),
    "GA-22": ("generic_complex", "multi_root", "real_interior"),
    "GA-23": ("angular_anchor_counterexample", "exact_center_width"),
    "GA-24": ("multi_root",),
    "GA-25": ("nonzero-small-radius",),
    "GA-27": ("generic_complex",),
    "GA-28": ("generic_complex", "multi_root"),
    "GA-29": ("generic_complex",),
    "GA-30": ("model_depth_1_degree_0_level_0", "model_depth_1_degree_3_level_0", "model_depth_2_degree_4_level_0", "model_depth_2_degree_4_level_1", "model_depth_4_degree_5_level_0", "model_depth_4_degree_5_level_1", "model_depth_4_degree_5_level_2", "model_depth_4_degree_5_level_3"),
    "GA-31": ("conjugate_pair", "generic_complex", "multi_root", "real_interior"),
    "GA-32": ("real-interior-zero-mode-witness",),
    "GA-33": ("multi_root",),
    "GA-34": ("real-interior-connected-endpoint", "real-interior-disconnected"),
}

ID_TOLERANCE_KEYS: Final[dict[str, tuple[str, ...]]] = {
    "GA-00": ("exact_operator_relative",),
    "GA-01": ("scalar_absolute",),
    "GA-02": ("scalar_absolute",),
    "GA-03": ("exact_operator_relative",),
    "GA-04": ("exact_operator_relative", "exact_energy_relative"),
    "GA-05": ("scalar_absolute",),
    "GA-06": ("exact_operator_relative", "exact_energy_relative"),
    "GA-07": ("exact_operator_relative",),
    "GA-08": ("zero_denominator_absolute",),
    "GA-09": ("exact_energy_relative",),
    "GA-11": ("exact_energy_relative",),
    "GA-15": ("exact_operator_relative", "sparse_dense_operator_relative"),
    "GA-16": ("exact_operator_relative",),
    "GA-18": ("exact_operator_relative", "sparse_dense_operator_relative"),
    "GA-19": ("sparse_dense_operator_relative",),
    "GA-20": ("exact_operator_relative", "inequality_relative_slack"),
    "GA-21": ("inequality_relative_slack",),
    "GA-22": ("inequality_relative_slack",),
    "GA-23": ("scalar_absolute",),
    "GA-25": ("exact_operator_relative",),
    "GA-28": ("inequality_relative_slack",),
    "GA-29": ("zero_denominator_absolute",),
    "GA-31": ("inequality_relative_slack",),
    "GA-32": ("exact_energy_relative",),
    "GA-33": ("exact_operator_relative",),
    "GA-34": ("zero_denominator_absolute",),
}


def extract_gate_ids(text: str) -> tuple[str, ...]:
    """Extract explicit IDs and expand compact ``GA-03/04`` or ranges."""

    found: set[str] = set()
    pattern = re.compile(r"GA-(\d{2})(?:(/|--)(?:GA-)?(\d{2}))?")
    for match in pattern.finditer(text):
        start = int(match.group(1))
        separator = match.group(2)
        end_text = match.group(3)
        if separator == "--" and end_text is not None:
            end = int(end_text)
            found.update(f"GA-{index:02d}" for index in range(start, end + 1))
        else:
            found.add(f"GA-{start:02d}")
            if separator == "/" and end_text is not None:
                found.add(f"GA-{int(end_text):02d}")
    return tuple(sorted(found))


@dataclass
class CollectedNode:
    node_id: str
    definition_id: str
    gate_ids: tuple[str, ...]


@dataclass(eq=False)
class PytestInventory:
    nodes: dict[str, CollectedNode] = field(default_factory=dict)
    phases: dict[str, dict[str, str]] = field(
        default_factory=lambda: defaultdict(dict)
    )
    metrics: dict[str, list[dict[str, Any]]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def pytest_collection_modifyitems(self, items: list[Any]) -> None:
        for item in items:
            function = getattr(item, "function", None)
            documentation = inspect.getdoc(function) or ""
            gate_ids = extract_gate_ids(f"{item.nodeid}\n{documentation}")
            if not gate_ids:
                continue
            location = item.location
            definition_id = f"{location[0]}:{location[1] + 1}:{location[2]}"
            self.nodes[item.nodeid] = CollectedNode(
                node_id=item.nodeid,
                definition_id=definition_id,
                gate_ids=gate_ids,
            )

    def pytest_runtest_logreport(self, report: Any) -> None:
        if report.nodeid not in self.nodes:
            return
        if report.failed:
            outcome = "FAIL"
        elif report.skipped:
            outcome = "NOT_RUN"
        else:
            outcome = "PASS"
        self.phases[report.nodeid][report.when] = outcome
        if report.when == "call":
            for key, raw_value in report.user_properties:
                if key != "gate_a_metrics":
                    continue
                try:
                    value = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
                except (TypeError, json.JSONDecodeError):
                    value = {"unparsed": str(raw_value)}
                if isinstance(value, dict):
                    self.metrics[report.nodeid].append(value)


def _node_execution_status(
    node_id: str,
    inventory: PytestInventory,
    *,
    tests_executed: bool,
) -> str:
    if not tests_executed:
        return "NOT_RUN"
    phases = inventory.phases.get(node_id, {})
    if any(outcome == "FAIL" for outcome in phases.values()):
        return "FAIL"
    if phases.get("call") == "PASS":
        return "PASS"
    return "NOT_RUN"


def _git_value(repository_root: Path, arguments: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository_root), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "UNKNOWN"


def _source_state(repository_root: Path) -> dict[str, Any]:
    status = _git_value(repository_root, ["status", "--porcelain", "--untracked-files=all"])
    digest = hashlib.sha256(status.encode("utf-8")).hexdigest() if status else None
    return {
        "tested_source_commit": _git_value(repository_root, ["rev-parse", "HEAD"]),
        "source_tree_dirty": bool(status),
        "source_status_sha256": digest,
    }


def _environment_state() -> dict[str, str]:
    """Return deterministic environment identity relevant to numeric evidence."""

    import torch

    return {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda or "NONE",
        "platform": platform.platform(),
    }


def _node_record(
    node_id: str,
    inventory: PytestInventory,
    *,
    tests_executed: bool,
    evidence_reference: str,
) -> dict[str, Any]:
    node = inventory.nodes[node_id]
    return {
        "node_id": node_id,
        "definition_id": node.definition_id,
        "execution_status": _node_execution_status(
            node_id,
            inventory,
            tests_executed=tests_executed,
        ),
        "phase_statuses": dict(sorted(inventory.phases.get(node_id, {}).items())),
        "evidence_reference": evidence_reference,
        "execution_context_reference": "gate_a_evidence.source+environment",
        "pytest_recorded_properties": inventory.metrics.get(node_id, []),
    }


def _declaration(gate_id: str) -> dict[str, Any]:
    tolerance_keys = ID_TOLERANCE_KEYS.get(gate_id, ())
    return {
        "realization_tags": list(REALIZATION_TAGS[gate_id]),
        "fixtures": list(ID_FIXTURES.get(gate_id, ())),
        "depths": list(ID_DEPTHS.get(gate_id, ())),
        "degrees": list(ID_DEGREES.get(gate_id, ())),
        "root_fixtures": list(ID_ROOTS.get(gate_id, ())),
        "tolerances": {
            key: NUMERICAL_TOLERANCES[key]
            for key in tolerance_keys
        },
    }


def _typed_value(field: Any) -> Any | None:
    if isinstance(field, dict) and field.get("status") == "VALUE":
        return field.get("value")
    return None


def _evidence_fixture_names(row: dict[str, Any]) -> tuple[str, ...]:
    values = _typed_value(row.get("graph_semantic_hashes"))
    if not isinstance(values, list):
        return ()
    return tuple(
        sorted(
            {
                str(item["fixture"])
                for item in values
                if isinstance(item, dict) and isinstance(item.get("fixture"), str)
            }
        )
    )


def _evidence_root_names(row: dict[str, Any]) -> tuple[str, ...]:
    values = _typed_value(row.get("root_fixtures_and_values"))
    if not isinstance(values, list):
        return ()
    return tuple(
        sorted(
            {
                str(item["fixture"])
                for item in values
                if isinstance(item, dict) and isinstance(item.get("fixture"), str)
            }
        )
    )


def _collect_configuration_integers(value: Any, dimension: str) -> tuple[int, ...]:
    observed: set[int] = set()

    def visit(current: Any) -> None:
        if isinstance(current, dict):
            for key, child in current.items():
                if key == dimension or key == f"{dimension}s" or key.endswith(
                    f"_{dimension}"
                ):
                    if type(child) is int:
                        observed.add(child)
                    elif isinstance(child, list):
                        observed.update(item for item in child if type(item) is int)
                visit(child)
        elif isinstance(current, list):
            for child in current:
                visit(child)

    visit(value)
    return tuple(sorted(observed))


def _evidence_configuration_values(
    row: dict[str, Any],
    dimension: str,
) -> tuple[int, ...]:
    configuration = _typed_value(row.get("configuration"))
    return _collect_configuration_integers(configuration, dimension)


def cross_validate_coverage_declarations(
    evidence_catalog: dict[str, Any],
) -> dict[str, Any]:
    """Cross-check every static row declaration against computed evidence.

    Static declarations remain the frozen acceptance requirements. Computed
    evidence is authoritative for what was actually exercised. Exact set
    equality is deliberate: both missing coverage and stale/undeclared scope
    are provenance drift and must block the reporter.
    """

    rows = evidence_catalog.get("rows")
    if not isinstance(rows, dict):
        return {
            "status": "FAIL",
            "rows": {},
            "mismatches": ["evidence catalog has no typed rows mapping"],
        }
    records: dict[str, dict[str, Any]] = {}
    mismatches: list[str] = []
    extractors = {
        "fixtures": _evidence_fixture_names,
        "root_fixtures": _evidence_root_names,
        "depths": lambda row: _evidence_configuration_values(row, "depth"),
        "degrees": lambda row: _evidence_configuration_values(row, "degree"),
    }
    declaration_maps: dict[str, dict[str, tuple[Any, ...]]] = {
        "fixtures": ID_FIXTURES,
        "root_fixtures": ID_ROOTS,
        "depths": ID_DEPTHS,
        "degrees": ID_DEGREES,
    }
    for gate_id in REQUIRED_IDS:
        row = rows.get(gate_id)
        row_record: dict[str, Any] = {}
        if not isinstance(row, dict):
            message = f"{gate_id}: missing computed evidence row"
            mismatches.append(message)
            records[gate_id] = {
                "status": "FAIL",
                "mismatches": [message],
            }
            continue
        row_mismatches: list[str] = []
        for dimension, extractor in extractors.items():
            expected = tuple(sorted(declaration_maps[dimension].get(gate_id, ())))
            observed = tuple(extractor(row))
            missing = tuple(value for value in expected if value not in observed)
            undeclared = tuple(value for value in observed if value not in expected)
            row_record[dimension] = {
                "declared": list(expected),
                "computed_from_evidence": list(observed),
                "missing_from_evidence": list(missing),
                "undeclared_in_static_contract": list(undeclared),
                "matches": not missing and not undeclared,
            }
            if missing or undeclared:
                message = (
                    f"{gate_id} {dimension}: missing={list(missing)}, "
                    f"undeclared={list(undeclared)}"
                )
                row_mismatches.append(message)
                mismatches.append(message)
        row_record["status"] = "PASS" if not row_mismatches else "FAIL"
        row_record["mismatches"] = row_mismatches
        records[gate_id] = row_record
    return {
        "status": "PASS" if not mismatches else "FAIL",
        "rows": records,
        "mismatches": mismatches,
    }


def validate_report_provenance(report: Any) -> list[str]:
    """Validate source/environment and pytest-node-to-evidence links."""

    errors: list[str] = []
    if not isinstance(report, dict):
        return ["report: expected mapping"]
    source = report.get("source")
    if not isinstance(source, dict):
        errors.append("report.source: expected mapping")
    else:
        commit = source.get("tested_source_commit")
        if not isinstance(commit, str) or not commit.strip():
            errors.append("report.source.tested_source_commit: missing value")
        if not isinstance(source.get("source_tree_dirty"), bool):
            errors.append("report.source.source_tree_dirty: expected Boolean")
        status_digest = source.get("source_status_sha256")
        if status_digest is not None and not re.fullmatch(
            r"[0-9a-f]{64}", str(status_digest)
        ):
            errors.append("report.source.source_status_sha256: invalid sha256")

    environment = report.get("environment")
    required_environment = (
        "python_implementation",
        "python_version",
        "torch_version",
        "cuda_version",
        "platform",
    )
    if not isinstance(environment, dict):
        errors.append("report.environment: expected mapping")
    else:
        for key in required_environment:
            value = environment.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"report.environment.{key}: missing value")

    ids = report.get("ids")
    if not isinstance(ids, dict):
        errors.append("report.ids: expected mapping")
        return errors
    for gate_id in REQUIRED_IDS:
        row = ids.get(gate_id)
        path = f"report.ids.{gate_id}"
        if not isinstance(row, dict):
            errors.append(f"{path}: missing row")
            continue
        if row.get("status") not in {"PASS", "FAIL", "NOT_RUN"}:
            errors.append(f"{path}.status: invalid value")
        if row.get("execution_status") not in {"PASS", "FAIL", "NOT_RUN"}:
            errors.append(f"{path}.execution_status: invalid value")
        if row.get("mapping_status") not in {"UNIQUE", "DUPLICATE", "MISSING"}:
            errors.append(f"{path}.mapping_status: invalid value")
        reference = row.get("computed_evidence_reference")
        expected_reference = f"gate_a_evidence.rows.{gate_id}"
        if reference != expected_reference:
            errors.append(f"{path}.computed_evidence_reference: invalid link")
        if row.get("execution_context_reference") != (
            "gate_a_evidence.source+environment"
        ):
            errors.append(f"{path}.execution_context_reference: invalid link")
        collected = row.get("collected_node_ids")
        nodes = row.get("node_records")
        if not isinstance(collected, list) or not isinstance(nodes, list):
            errors.append(f"{path}: node lists are missing")
            continue
        if [node.get("node_id") for node in nodes if isinstance(node, dict)] != collected:
            errors.append(f"{path}.node_records: node IDs disagree with collection")
        for index, node in enumerate(nodes):
            node_path = f"{path}.node_records[{index}]"
            if not isinstance(node, dict):
                errors.append(f"{node_path}: expected mapping")
                continue
            if node.get("evidence_reference") != expected_reference:
                errors.append(f"{node_path}.evidence_reference: invalid link")
            if node.get("execution_context_reference") != (
                "gate_a_evidence.source+environment"
            ):
                errors.append(f"{node_path}.execution_context_reference: invalid link")
            if node.get("execution_status") not in {
                "PASS",
                "FAIL",
                "NOT_RUN",
            }:
                errors.append(f"{node_path}.execution_status: invalid value")
    return errors


def build_report(
    inventory: PytestInventory,
    *,
    repository_root: Path,
    tests_executed: bool,
    pytest_exit_code: int,
    evidence_catalog_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic report from collected nodes and outcomes."""

    nodes_by_id: dict[str, list[str]] = defaultdict(list)
    definitions_by_id: dict[str, set[str]] = defaultdict(set)
    for node in inventory.nodes.values():
        for gate_id in node.gate_ids:
            if gate_id in REQUIRED_IDS:
                nodes_by_id[gate_id].append(node.node_id)
                definitions_by_id[gate_id].add(node.definition_id)

    evidence_catalog = (
        evaluate_gate_a_evidence()
        if evidence_catalog_override is None
        else evidence_catalog_override
    )
    evidence_schema_errors = validate_evidence_catalog(evidence_catalog)
    evidence_failures = evidence_decision_failures(evidence_catalog)
    evidence_counts = evidence_field_counts(evidence_catalog)
    coverage_evidence_cross_validation = cross_validate_coverage_declarations(
        evidence_catalog
    )
    source_state = _source_state(repository_root)
    environment_state = _environment_state()

    records: dict[str, dict[str, Any]] = {}
    for gate_id in REQUIRED_IDS:
        node_ids = sorted(nodes_by_id.get(gate_id, []))
        definitions = sorted(definitions_by_id.get(gate_id, set()))
        outcomes = [
            _node_execution_status(
                node_id,
                inventory,
                tests_executed=tests_executed,
            )
            for node_id in node_ids
        ]
        if not node_ids:
            execution_status = "NOT_RUN"
        elif "FAIL" in outcomes:
            execution_status = "FAIL"
        elif outcomes and all(outcome == "PASS" for outcome in outcomes):
            execution_status = "PASS"
        else:
            execution_status = "NOT_RUN"
        mapping_status = (
            "MISSING"
            if not definitions
            else "DUPLICATE"
            if len(definitions) > 1
            else "UNIQUE"
        )
        status = execution_status

        pytest_properties = [
            metric
            for node_id in node_ids
            for metric in inventory.metrics.get(node_id, [])
        ]
        evidence = evidence_catalog["rows"].get(gate_id)
        evidence_reference = f"gate_a_evidence.rows.{gate_id}"
        node_records = [
            _node_record(
                node_id,
                inventory,
                tests_executed=tests_executed,
                evidence_reference=evidence_reference,
            )
            for node_id in node_ids
        ]
        records[gate_id] = {
            "status": status,
            "execution_status": execution_status,
            "mapping_status": mapping_status,
            "collected_node_ids": node_ids,
            "node_records": node_records,
            "test_definitions": definitions,
            "declaration": _declaration(gate_id),
            "computed_evidence_reference": evidence_reference,
            "execution_context_reference": "gate_a_evidence.source+environment",
            "computed_evidence_available": evidence is not None,
            "pytest_recorded_properties": pytest_properties,
        }

    missing_ids = [
        gate_id
        for gate_id, record in records.items()
        if record["mapping_status"] == "MISSING"
    ]
    failed_ids = [
        gate_id
        for gate_id, record in records.items()
        if record["execution_status"] == "FAIL"
    ]
    not_run_ids = [
        gate_id
        for gate_id, record in records.items()
        if record["execution_status"] == "NOT_RUN"
    ]
    duplicate_ids = [
        gate_id
        for gate_id, record in records.items()
        if record["mapping_status"] == "DUPLICATE"
    ]
    fixture_gaps = [
        fixture
        for fixture in REQUIRED_FIXTURE_MATRIX
        if not FIXTURE_MATRIX_DECLARATION[fixture]["declared_covered"]
    ]
    exact_multilevel_gaps = [
        {
            "fixture": fixture,
            "missing": list(declaration["missing"]),
        }
        for fixture, declaration in EXACT_MULTILEVEL_MATRIX.items()
        if not declaration["complete"]
    ]
    row_matrix: dict[str, dict[str, Any]] = {}
    for gate_id, declaration in ROW_MATRIX_DECLARATION.items():
        required = list(declaration["required"])
        observed = list(declaration["observed"])
        missing = [value for value in required if value not in observed]
        row_matrix[gate_id] = {
            **declaration,
            "complete": not missing,
            "missing": missing,
        }
    row_matrix_gaps = [
        {
            "gate_id": gate_id,
            "dimension": declaration["dimension"],
            "missing": list(declaration["missing"]),
        }
        for gate_id, declaration in row_matrix.items()
        if not declaration["complete"]
    ]
    root_gaps = [
        {
            "root_fixture": root_fixture,
            "missing": list(declaration["missing"]),
        }
        for root_fixture, declaration in ROOT_FIXTURE_DECLARATION.items()
        if not declaration["acceptance_complete"]
    ]
    missing_evidence_ids = [
        gate_id
        for gate_id, record in records.items()
        if not record["computed_evidence_available"]
    ]
    all_ids_passed = not missing_ids and not failed_ids and not not_run_ids
    blockers = [
        *[f"missing fixture: {fixture}" for fixture in fixture_gaps],
        *[
            "incomplete exact multilevel fixture/depth row: "
            f"{gap['fixture']} ({', '.join(gap['missing'])})"
            for gap in exact_multilevel_gaps
        ],
        *[
            f"incomplete {gap['gate_id']} {gap['dimension']}: "
            f"{', '.join(str(value) for value in gap['missing'])}"
            for gap in row_matrix_gaps
        ],
        *[
            "incomplete root-fixture acceptance scope: "
            f"{gap['root_fixture']} ({', '.join(gap['missing'])})"
            for gap in root_gaps
        ],
        "independent reviewer acceptance has not been recorded by this utility",
    ]
    if evidence_schema_errors:
        blockers.append(
            "invalid machine-readable evidence: "
            + "; ".join(evidence_schema_errors)
        )
    if evidence_failures:
        blockers.append(
            "computed evidence contains failed decisions: "
            + ", ".join(evidence_failures)
        )
    if missing_evidence_ids:
        blockers.append(
            "missing computed evidence rows: " + ", ".join(missing_evidence_ids)
        )
    if coverage_evidence_cross_validation["status"] != "PASS":
        blockers.append(
            "static coverage declarations disagree with computed typed evidence: "
            + "; ".join(coverage_evidence_cross_validation["mismatches"])
        )
    if source_state["tested_source_commit"] == "UNKNOWN":
        blockers.append("tested source commit could not be resolved")
    if source_state["source_tree_dirty"]:
        blockers.append(
            "tested source tree is dirty; commit or archive the exact diff "
            "before scientific acceptance"
        )
    if missing_ids:
        blockers.append(f"missing mandatory IDs: {', '.join(missing_ids)}")
    if failed_ids:
        blockers.append(f"failed mandatory IDs: {', '.join(failed_ids)}")
    if not_run_ids:
        blockers.append(f"not-run mandatory IDs: {', '.join(not_run_ids)}")

    report = {
        "schema": REPORT_SCHEMA,
        "source": source_state,
        "environment": environment_state,
        "pytest": {
            "tests_executed": tests_executed,
            "exit_code": pytest_exit_code,
            "collected_gate_node_count": len(inventory.nodes),
        },
        "numerical_tolerances": dict(NUMERICAL_TOLERANCES),
        "required_fixture_matrix": {
            "fixtures": FIXTURE_MATRIX_DECLARATION,
            "gaps": fixture_gaps,
        },
        "required_depths": {
            "exact": [1, 2, 4, 8, 16],
            "exact_multilevel_fixture_matrix": EXACT_MULTILEVEL_MATRIX,
            "gaps": exact_multilevel_gaps,
        },
        "required_degrees": {
            "chebyshev_K": [4, 8, 16, 32],
            "high_order_convergence_case": 128,
            "observed_by_id": {
                gate_id: list(degrees)
                for gate_id, degrees in ID_DEGREES.items()
            },
            "GA-19_acceptance": row_matrix["GA-19"],
        },
        "required_root_fixtures": {
            "coverage": ROOT_FIXTURE_DECLARATION,
            "gaps": root_gaps,
        },
        "row_specific_coverage": {
            "rows": row_matrix,
            "gaps": row_matrix_gaps,
        },
        "coverage_evidence_cross_validation": coverage_evidence_cross_validation,
        "ids": records,
        "gate_a_evidence": {
            "schema": EVIDENCE_SCHEMA,
            "source": source_state,
            "environment": environment_state,
            "rows": evidence_catalog["rows"],
            "typed_field_counts": evidence_counts,
            "schema_errors": evidence_schema_errors,
            "failed_decisions": evidence_failures,
        },
        "summary": {
            "required_id_count": len(REQUIRED_IDS),
            "all_required_ids_executed_and_passing": all_ids_passed,
            "missing_ids": missing_ids,
            "failed_ids": failed_ids,
            "not_run_ids": not_run_ids,
            "duplicate_mapping_ids": duplicate_ids,
            "ids_without_machine_readable_evidence": missing_evidence_ids,
            # Backward-compatible alias: evidence now contains residuals/bounds.
            "ids_without_machine_readable_residuals": missing_evidence_ids,
        },
        "gate_a_acceptance": {
            "accepted": False,
            "status": "BLOCKED",
            "blockers": blockers,
            "note": (
                "Passing node IDs are regression evidence only; Gate A also "
                "requires the complete fixture/provenance matrix and independent review."
            ),
        },
    }
    provenance_errors = validate_report_provenance(report)
    report["gate_a_evidence"]["provenance_link_errors"] = provenance_errors
    if provenance_errors:
        blockers.append(
            "invalid source/environment/node evidence links: "
            + "; ".join(provenance_errors)
        )
    return report


def collect_and_report(
    repository_root: Path,
    *,
    execute_tests: bool,
) -> dict[str, Any]:
    """Collect Gate-A pytest nodes, optionally execute them, and return a report."""

    import pytest

    repository_root = repository_root.resolve()
    test_paths = sorted(
        path.relative_to(repository_root).as_posix()
        for path in (repository_root / "tests").glob("test_gate_a*.py")
    )
    inventory = PytestInventory()
    arguments = [
        *test_paths,
        "-q",
        "-p",
        "no:cacheprovider",
        f"--rootdir={repository_root}",
    ]
    if not execute_tests:
        arguments.append("--collect-only")
    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    previous_directory = Path.cwd()
    try:
        os.chdir(repository_root)
        with redirect_stdout(captured_stdout), redirect_stderr(captured_stderr):
            exit_code = int(pytest.main(arguments, plugins=[inventory]))
    finally:
        os.chdir(previous_directory)
    return build_report(
        inventory,
        repository_root=repository_root,
        tests_executed=execute_tests,
        pytest_exit_code=exit_code,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="collect mappings without executing tests; statuses are NOT_RUN",
    )
    arguments = parser.parse_args(argv)
    report = collect_and_report(
        arguments.repository_root,
        execute_tests=not arguments.collect_only,
    )
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if report["pytest"]["exit_code"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
