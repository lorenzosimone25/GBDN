"""Schema, linkage, omission, and tamper tests for Gate-A evidence."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys

import torch

from gbdn.gate_a_evidence import (
    EVIDENCE_SCHEMA,
    REQUIRED_IDS,
    evaluate_gate_a_evidence,
    evidence_decision_failures,
    evidence_field_counts,
    validate_evidence_catalog,
)
from gbdn.gate_a_report import collect_and_report, validate_report_provenance


ROOT = Path(__file__).resolve().parents[1]


def _typed_fields(catalog):
    row_fields = (
        "graph_semantic_hashes",
        "root_fixtures_and_values",
        "dtype",
        "device",
        "configuration",
    )
    metric_fields = (
        "observed_quantity",
        "absolute_residual",
        "relative_residual",
        "predicted_bound",
        "observed_vs_bound",
        "tolerance",
    )
    for row in catalog["rows"].values():
        for field in row_fields:
            yield row[field]
        for metric in row["metrics"]:
            for field in metric_fields:
                yield metric[field]


def test_gate_a_evidence_schema_has_every_row_and_genuine_observable():
    torch.manual_seed(9876)
    expected_next_random = torch.rand(8)
    torch.manual_seed(9876)
    catalog = evaluate_gate_a_evidence()
    assert torch.equal(torch.rand(8), expected_next_random)
    assert catalog["schema"] == EVIDENCE_SCHEMA
    assert tuple(sorted(catalog["rows"])) == REQUIRED_IDS
    assert validate_evidence_catalog(catalog) == []
    assert evidence_decision_failures(catalog) == []

    for gate_id, row in catalog["rows"].items():
        assert row["gate_id"] == gate_id
        assert row["metrics"]
        assert any(
            metric["observed_quantity"]["status"] == "VALUE"
            for metric in row["metrics"]
        )
        assert all(
            metric["absolute_residual"]["status"] in {"VALUE", "N/A"}
            and metric["relative_residual"]["status"] in {"VALUE", "N/A"}
            and metric["predicted_bound"]["status"] in {"VALUE", "N/A"}
            for metric in row["metrics"]
        )

    typed_fields = list(_typed_fields(catalog))
    counts = evidence_field_counts(catalog)
    assert counts["TOTAL"] == len(typed_fields)
    assert counts["VALUE"] + counts["N/A"] == counts["TOTAL"]
    assert any(field["status"] == "N/A" for field in typed_fields)
    assert all(
        field["status"] != "N/A" or field["rationale"].strip()
        for field in typed_fields
    )


def test_gate_a_evidence_is_deterministic_and_mutation_isolated():
    first = evaluate_gate_a_evidence()
    second = evaluate_gate_a_evidence()
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)

    first["rows"]["GA-00"]["metrics"][0]["name"] = "tampered-in-caller"
    third = evaluate_gate_a_evidence()
    assert third["rows"]["GA-00"]["metrics"][0]["name"] != "tampered-in-caller"


def test_reviewer_sensitive_rows_expose_their_semantic_observables():
    catalog = evaluate_gate_a_evidence()

    ga10 = catalog["rows"]["GA-10"]
    ga10_metrics = {metric["name"]: metric for metric in ga10["metrics"]}
    assert ga10["configuration"]["value"]["public_model"] == "GBDNTight"
    assert ga10["configuration"]["value"]["expected_order"] == [
        "r_0",
        "r_1",
        "h_D",
    ]
    assert ga10_metrics[
        "wrong_order_readout_relative_separation"
    ]["observed_quantity"]["value"] > 0.0

    ga14 = catalog["rows"]["GA-14"]
    ga14_configuration = ga14["configuration"]["value"]
    assert ga14_configuration["channel_relation"] == "q=(1-t)/2"
    assert ga14_configuration["epsilon_k_over_two"] == (
        0.5 * ga14_configuration["epsilon_k_operator_norm"]
    )
    assert {
        metric["name"] for metric in ga14["metrics"]
    } >= {"induced_channel_epsilon_over_two_residual", "finite_recovery_error"}

    ga25 = catalog["rows"]["GA-25"]
    ga25_metrics = {metric["name"]: metric for metric in ga25["metrics"]}
    stable_condition = ga25_metrics[
        "stable_evaluation_matrix_condition_number"
    ]["observed_quantity"]["value"]
    ill_condition = ga25_metrics[
        "ill_conditioned_evaluation_matrix_condition_number"
    ]["observed_quantity"]["value"]
    assert stable_condition < 1e8
    assert ill_condition > 1e10

    ga27 = catalog["rows"]["GA-27"]
    ga27_configuration = ga27["configuration"]["value"]
    assert ga27_configuration["cancelled_zero_pole_pair_count"] == 0
    assert ga27_configuration["reduced_pole_multiset"]
    assert ga27_configuration["cayley_scale_domain"] == "h>0"
    assert "accumulation point" in ga27_configuration["comparison_scope"]


def test_gate_a_evidence_schema_rejects_omission_na_without_reason_and_bad_hash():
    catalog = evaluate_gate_a_evidence()

    omitted = copy.deepcopy(catalog)
    del omitted["rows"]["GA-17"]
    assert any("missing rows GA-17" in error for error in validate_evidence_catalog(omitted))

    unjustified = copy.deepcopy(catalog)
    unjustified["rows"]["GA-10"]["graph_semantic_hashes"] = {
        "status": "N/A",
        "rationale": "",
    }
    assert any(
        "N/A evidence requires a rationale" in error
        for error in validate_evidence_catalog(unjustified)
    )

    bad_hash = copy.deepcopy(catalog)
    bad_hash["rows"]["GA-03"]["graph_semantic_hashes"]["value"][0][
        "semantic_sha256"
    ] = "not-a-semantic-hash"
    assert any("invalid sha256" in error for error in validate_evidence_catalog(bad_hash))


def test_gate_a_evidence_tampered_decision_is_reported():
    catalog = evaluate_gate_a_evidence()
    comparison = catalog["rows"]["GA-03"]["metrics"][0]["observed_vs_bound"]
    comparison["value"]["decision"] = False
    failures = evidence_decision_failures(catalog)
    assert failures == ["GA-03:maximum_left_unitarity_residual"]
    assert any(
        "recorded decision disagrees" in error
        for error in validate_evidence_catalog(catalog)
    )

    malformed = evaluate_gate_a_evidence()
    malformed["rows"]["GA-03"]["metrics"][0]["observed_vs_bound"]["value"] = {
        "operator": "<=",
        "decision": "yes",
    }
    assert any(
        "Boolean decision" in error for error in validate_evidence_catalog(malformed)
    )


def test_gate_a_collect_only_links_every_node_to_source_environment_and_evidence():
    report = collect_and_report(ROOT, execute_tests=False)
    assert report["gate_a_evidence"]["schema_errors"] == []
    assert report["gate_a_evidence"]["failed_decisions"] == []
    assert report["gate_a_evidence"]["provenance_link_errors"] == []
    assert validate_report_provenance(report) == []
    assert report["summary"]["ids_without_machine_readable_evidence"] == []
    assert report["source"]["tested_source_commit"]
    assert report["environment"]["python_version"]
    assert report["environment"]["torch_version"]
    assert report["gate_a_acceptance"]["accepted"] is False

    for gate_id in REQUIRED_IDS:
        row = report["ids"][gate_id]
        assert row["computed_evidence_available"] is True
        assert row["computed_evidence_reference"] == f"gate_a_evidence.rows.{gate_id}"
        assert row["node_records"]
        for node in row["node_records"]:
            assert node["node_id"]
            assert node["execution_status"] == "NOT_RUN"
            assert node["evidence_reference"] == row["computed_evidence_reference"]

    missing_environment = copy.deepcopy(report)
    del missing_environment["environment"]["torch_version"]
    assert any(
        "environment.torch_version" in error
        for error in validate_report_provenance(missing_environment)
    )

    tampered_link = copy.deepcopy(report)
    tampered_link["ids"]["GA-03"]["node_records"][0][
        "evidence_reference"
    ] = "gate_a_evidence.rows.GA-04"
    assert any(
        "GA-03.node_records[0].evidence_reference" in error
        for error in validate_report_provenance(tampered_link)
    )


def test_gate_a_report_cli_remains_stdout_only_json_with_review_blocker():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "report_gate_a.py"), "--collect-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["gate_a_evidence"]["schema"] == EVIDENCE_SCHEMA
    assert report["gate_a_acceptance"]["accepted"] is False
    assert "independent reviewer acceptance has not been recorded by this utility" in (
        report["gate_a_acceptance"]["blockers"]
    )
    if report["source"]["source_tree_dirty"]:
        assert any(
            "tested source tree is dirty" in blocker
            for blocker in report["gate_a_acceptance"]["blockers"]
        )
