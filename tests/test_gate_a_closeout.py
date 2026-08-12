"""Gate-A center/width closeout and coverage-report regression tests."""

from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess
import sys

import torch

from gbdn import (
    cayley_map,
    mapped_zero_pole,
    parameterize_center_width_roots,
    tight_split_responses,
)
from gbdn.diagnostics import bernstein_ellipse_parameter
from gbdn.gate_a_report import (
    CollectedNode,
    PytestInventory,
    build_report,
    extract_gate_ids,
)


ROOT = Path(__file__).resolve().parents[1]
SCALAR_TOL = 5e-12


def _logit(probability: float) -> float:
    return math.log(probability / (1.0 - probability))


def test_ga23_exact_center_width_and_frozen_angular_counterexample(
    record_property,
):
    """GA-23: exact center/HWHM/pole/ellipse and angular-anchor boundary."""

    mu = 1.0
    gamma = 0.25
    gamma_min = 0.05
    gamma_max = 1.0
    raw_width_probability = (gamma - gamma_min) / (gamma_max - gamma_min)
    parameters = torch.tensor(
        [[_logit(mu / 2.0), _logit(raw_width_probability)]],
        dtype=torch.float64,
    )
    root = parameterize_center_width_roots(
        parameters,
        gamma_min=gamma_min,
        gamma_max=gamma_max,
    )
    zero, pole = mapped_zero_pole(root)

    mapped_zero_error = abs(complex(zero.item()) - complex(mu, gamma))
    mapped_pole_error = abs(complex(pole.item()) - complex(mu, -gamma))
    assert mapped_zero_error <= SCALAR_TOL
    assert mapped_pole_error <= SCALAR_TOL

    probes = torch.tensor(
        [mu - gamma, mu, mu + gamma],
        dtype=torch.float64,
    )
    derivative = tight_split_responses(probes, root)["phase_derivative"]
    expected_peak = 2.0 / gamma
    center_peak_error = abs(float(derivative[1].item()) - expected_peak)
    left_hwhm_error = abs(float(derivative[0].item()) - expected_peak / 2.0)
    right_hwhm_error = abs(float(derivative[2].item()) - expected_peak / 2.0)
    assert center_peak_error <= SCALAR_TOL
    assert left_hwhm_error <= SCALAR_TOL
    assert right_hwhm_error <= SCALAR_TOL
    assert int(torch.argmax(derivative).item()) == 1

    pole_ellipse_parameter = bernstein_ellipse_parameter(
        complex(pole.item()) - 1.0
    )
    admissible_rho = 0.5 * (1.0 + pole_ellipse_parameter)
    assert 1.0 < admissible_rho < pole_ellipse_parameter

    anchor_mu = torch.tensor([1.0], dtype=torch.float64)
    anchor_root = 0.5 * cayley_map(anchor_mu)
    anchor_zero, _ = mapped_zero_pole(anchor_root)
    angular_center = float(anchor_zero.real.item())
    angular_center_error = abs(angular_center - 0.8)
    assert angular_center_error <= SCALAR_TOL
    assert abs(angular_center - 1.0) > 0.1

    anchor_grid = torch.linspace(0.0, 2.0, 4001, dtype=torch.float64)
    anchor_derivative = tight_split_responses(
        anchor_grid,
        anchor_root,
    )["phase_derivative"]
    observed_anchor_peak = float(
        anchor_grid[int(torch.argmax(anchor_derivative).item())].item()
    )
    assert abs(observed_anchor_peak - 0.8) <= 5e-4

    absolute_residual = max(
        mapped_zero_error,
        mapped_pole_error,
        center_peak_error,
        left_hwhm_error,
        right_hwhm_error,
        angular_center_error,
    )
    record_property(
        "gate_a_metrics",
        json.dumps(
            {
                "absolute_residual": absolute_residual,
                "admissible_bernstein_rho": admissible_rho,
                "device": str(root.device),
                "dtype": str(root.dtype),
                "fixture": "scalar-center-width-and-angular-anchor",
                "graph_hash": None,
                "observed_angular_peak": observed_anchor_peak,
                "observed_phase_peak": float(derivative[1].item()),
                "parameterization": "exact-center-width",
                "pole_ellipse_parameter": pole_ellipse_parameter,
                "predicted_phase_peak": expected_peak,
                "realization_tag": "exact",
                "relative_residual": absolute_residual / expected_peak,
                "root": {
                    "imag": float(root.imag.item()),
                    "real": float(root.real.item()),
                },
                "scalar_absolute_tolerance": SCALAR_TOL,
            },
            sort_keys=True,
        ),
    )


def test_gate_a_report_id_parser_expands_compound_ids():
    parsed = extract_gate_ids("GA-03/04; GA-31--34; GA-23; GA-99")
    assert parsed == (
        "GA-03",
        "GA-04",
        "GA-23",
        "GA-31",
        "GA-32",
        "GA-33",
        "GA-34",
        "GA-99",
    )


def test_gate_a_report_distinguishes_execution_mapping_and_acceptance():
    inventory = PytestInventory()
    inventory.nodes = {
        "tests/a.py::test_first": CollectedNode(
            "tests/a.py::test_first",
            "tests/a.py:1:test_first",
            ("GA-00",),
        ),
        "tests/b.py::test_second": CollectedNode(
            "tests/b.py::test_second",
            "tests/b.py:2:test_second",
            ("GA-00",),
        ),
        "tests/c.py::test_unique": CollectedNode(
            "tests/c.py::test_unique",
            "tests/c.py:3:test_unique",
            ("GA-01",),
        ),
        "tests/d.py::test_failure": CollectedNode(
            "tests/d.py::test_failure",
            "tests/d.py:4:test_failure",
            ("GA-02",),
        ),
    }
    for node_id in inventory.nodes:
        inventory.phases[node_id]["call"] = (
            "FAIL" if node_id.endswith("test_failure") else "PASS"
        )

    report = build_report(
        inventory,
        repository_root=ROOT,
        tests_executed=True,
        pytest_exit_code=1,
    )

    assert report["ids"]["GA-00"]["status"] == "DUPLICATE"
    assert report["ids"]["GA-00"]["execution_status"] == "PASS"
    assert report["ids"]["GA-01"]["status"] == "PASS"
    assert report["ids"]["GA-02"]["status"] == "FAIL"
    assert report["ids"]["GA-03"]["status"] == "MISSING"
    assert report["gate_a_acceptance"]["accepted"] is False
    assert report["required_depths"]["gaps"] == []
    assert report["required_degrees"]["GA-19_acceptance"]["missing"] == []
    conjugate = report["required_root_fixtures"]["coverage"][
        "conjugate-symmetric-pair-where-relevant"
    ]
    assert conjugate["acceptance_complete"] is True
    assert report["row_specific_coverage"]["rows"]["GA-03"]["complete"] is True


def test_gate_a_report_cli_collect_only_is_deterministic_machine_readable_json():
    command = [sys.executable, str(ROOT / "scripts" / "report_gate_a.py"), "--collect-only"]
    first = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    second = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert first.stdout == second.stdout
    report = json.loads(first.stdout)
    assert report["schema"] == "gbdn-gate-a-coverage-v2"
    assert len(report["ids"]) == 36
    assert report["ids"]["GA-23"]["collected_node_ids"]
    assert report["ids"]["GA-23"]["execution_status"] == "NOT_RUN"
    assert report["summary"]["all_required_ids_executed_and_passing"] is False
    assert report["gate_a_acceptance"]["accepted"] is False
    assert report["required_depths"]["gaps"] == []
    assert report["summary"]["ids_without_machine_readable_evidence"] == []
    assert report["gate_a_evidence"]["schema_errors"] == []

