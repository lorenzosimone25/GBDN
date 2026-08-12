"""Adversarial tests for the fail-closed Gate-A acceptance contract."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from gbdn.artifacts import ArtifactValidationError, canonical_json_bytes
from gbdn.gate_a_report import REPORT_SCHEMA
from gbdn.gate_acceptance import (
    ACCEPTANCE_RELATIVE_PATH,
    ACCEPTANCE_SCHEMA,
    PROTECTED_PATHS,
    REQUIRED_GATE_IDS,
    validate_gate_a_acceptance,
)


def test_gate_scope_excludes_operations_only_launcher_but_keeps_math_surface():
    assert "scripts/run_submission.py" not in PROTECTED_PATHS
    assert "scripts/report_gate_a.py" in PROTECTED_PATHS
    assert "src/gbdn/__init__.py" in PROTECTED_PATHS
    assert "src/gbdn/artifacts.py" in PROTECTED_PATHS
    assert "src/gbdn/gate_a_report.py" in PROTECTED_PATHS
    assert "src/gbdn/gate_acceptance.py" in PROTECTED_PATHS
    assert "src/gbdn/model.py" in PROTECTED_PATHS
    assert "src/gbdn/provenance.py" in PROTECTED_PATHS
    assert "src/gbdn/seed.py" in PROTECTED_PATHS
    assert "tests/test_gate_acceptance.py" in PROTECTED_PATHS
    assert "tests/test_gate_a_fixture_completion.py" not in PROTECTED_PATHS


def _git(repository: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=check,
        capture_output=True,
        text=True,
    )


def _write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _blob_sha256(repository: Path, relative: str) -> str:
    payload = _git(repository, "show", f"HEAD:{relative}").stdout.encode()
    return hashlib.sha256(payload).hexdigest()


def _accepted_repository(tmp_path: Path, *, failed_row: str | None = None) -> tuple[Path, str]:
    repository = tmp_path / "repository"
    repository.mkdir(parents=True)
    _git(repository, "init")
    _git(repository, "config", "user.email", "review@example.com")
    _git(repository, "config", "user.name", "Independent Reviewer")
    _write(repository / ".gitattributes", b"*.json text eol=lf\n*.md text eol=lf\n")
    for relative in PROTECTED_PATHS:
        _write(repository / relative, f"frozen:{relative}\n".encode())
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "reviewed gate source")
    commit = _git(repository, "rev-parse", "HEAD").stdout.strip()
    tree = _git(repository, "rev-parse", "HEAD^{tree}").stdout.strip()

    verdicts = {gate_id: "ACCEPT" for gate_id in REQUIRED_GATE_IDS}
    if failed_row is not None:
        verdicts[failed_row] = "REJECT"
    report = {
        "coverage_evidence_cross_validation": {"status": "PASS"},
        "gate_a_acceptance": {
            "accepted": False,
            "blockers": [
                "independent reviewer acceptance has not been recorded by this utility"
            ],
        },
        "gate_a_evidence": {
            "failed_decisions": [],
            "provenance_link_errors": [],
            "schema_errors": [],
        },
        "ids": {
            gate_id: {"execution_status": "PASS"}
            for gate_id in REQUIRED_GATE_IDS
        },
        "pytest": {"exit_code": 0, "tests_executed": True},
        "schema": REPORT_SCHEMA,
        "source": {
            "source_tree_dirty": False,
            "tested_source_commit": commit,
        },
        "summary": {
            "all_required_ids_executed_and_passing": True,
            "failed_ids": [],
            "ids_without_machine_readable_evidence": [],
            "missing_ids": [],
            "not_run_ids": [],
            "required_id_count": 36,
        },
    }
    report_path = repository / "results_submission" / "reports" / "gate_a_report.json"
    review_path = repository / "reviews" / "gate_a_fourth_independent_review.md"
    _write(report_path, json.dumps(report, sort_keys=True).encode() + b"\n")
    _write(review_path, b"# Independent Gate-A review\n\nBinary verdict: ACCEPT.\n")
    token = {
        "decision": "ACCEPT",
        "gate": "Gate A",
        "gate_report": {
            "path": report_path.relative_to(repository).as_posix(),
            "schema": REPORT_SCHEMA,
            "sha256": _sha256(report_path),
        },
        "issued_at_utc": "2026-08-12T12:00:00Z",
        "protected_paths": list(PROTECTED_PATHS),
        "review": {
            "independent": True,
            "path": review_path.relative_to(repository).as_posix(),
            "sha256": _sha256(review_path),
            "verdict": "ACCEPT",
        },
        "reviewed_source": {
            "repository_commit": commit,
            "repository_tree": tree,
        },
        "row_verdicts": verdicts,
        "schema_version": ACCEPTANCE_SCHEMA,
    }
    token_path = repository / ACCEPTANCE_RELATIVE_PATH
    _write(token_path, canonical_json_bytes(token))
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "record independent acceptance")
    return repository, commit


def test_valid_acceptance_is_review_source_and_artifact_bound(tmp_path):
    repository, commit = _accepted_repository(tmp_path)
    accepted = validate_gate_a_acceptance(repository)
    assert accepted.reviewed_repository_commit == commit
    assert accepted.gate_report_path.endswith("gate_a_report.json")


def test_protected_paths_cover_every_gate_a_test_module():
    root = Path(__file__).resolve().parents[1]
    gate_tests = {
        path.relative_to(root).as_posix()
        for path in (root / "tests").glob("test_gate_a*.py")
    }
    assert gate_tests <= set(PROTECTED_PATHS)


def test_absent_token_and_wrong_path_fail_closed(tmp_path):
    repository, _ = _accepted_repository(tmp_path)
    (repository / ACCEPTANCE_RELATIVE_PATH).unlink()
    with pytest.raises(ArtifactValidationError, match="absent"):
        validate_gate_a_acceptance(repository)
    with pytest.raises(ArtifactValidationError, match="frozen path"):
        validate_gate_a_acceptance(repository, "acceptance.json")


def test_nonaccepted_row_cannot_authorize_claim_bearing_work(tmp_path):
    repository, _ = _accepted_repository(tmp_path, failed_row="GA-00")
    with pytest.raises(ArtifactValidationError, match="non-accepted row"):
        validate_gate_a_acceptance(repository)


def test_uncommitted_or_committed_protected_source_change_invalidates_token(tmp_path):
    repository, _ = _accepted_repository(tmp_path)
    protected = repository / PROTECTED_PATHS[0]
    protected.write_text("changed\n", encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="uncommitted"):
        validate_gate_a_acceptance(repository)
    _git(repository, "add", str(protected))
    _git(repository, "commit", "-m", "change protected source")
    with pytest.raises(ArtifactValidationError, match="changed after independent review"):
        validate_gate_a_acceptance(repository)


def test_report_or_review_tampering_invalidates_token(tmp_path):
    repository, _ = _accepted_repository(tmp_path)
    report = repository / "results_submission" / "reports" / "gate_a_report.json"
    report.write_text("{}", encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="hash|uncommitted"):
        validate_gate_a_acceptance(repository)

    repository, _ = _accepted_repository(tmp_path / "second")
    review = repository / "reviews" / "gate_a_fourth_independent_review.md"
    review.write_text("changed", encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="hash|uncommitted"):
        validate_gate_a_acceptance(repository)


def test_token_must_be_canonical_tracked_and_at_exact_location(tmp_path):
    repository, _ = _accepted_repository(tmp_path)
    token_path = repository / ACCEPTANCE_RELATIVE_PATH
    token = json.loads(token_path.read_text(encoding="utf-8"))
    token_path.write_text(json.dumps(token, indent=2), encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="canonical"):
        validate_gate_a_acceptance(repository)

    repository, _ = _accepted_repository(tmp_path / "untracked")
    _git(repository, "rm", "--cached", ACCEPTANCE_RELATIVE_PATH.as_posix())
    with pytest.raises(ArtifactValidationError, match="not tracked"):
        validate_gate_a_acceptance(repository)


def test_rehashed_forged_report_with_unresolved_failure_is_rejected(tmp_path):
    repository, _ = _accepted_repository(tmp_path)
    report_path = repository / "results_submission" / "reports" / "gate_a_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["summary"]["failed_ids"] = ["GA-00"]
    report["summary"]["all_required_ids_executed_and_passing"] = False
    report_path.write_text(json.dumps(report, sort_keys=True), encoding="utf-8")
    token_path = repository / ACCEPTANCE_RELATIVE_PATH
    token = json.loads(token_path.read_text(encoding="utf-8"))
    token["gate_report"]["sha256"] = _sha256(report_path)
    token_path.write_bytes(canonical_json_bytes(token))
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "attempt forged report")
    with pytest.raises(ArtifactValidationError, match="does not pass all 36"):
        validate_gate_a_acceptance(repository)


def test_gate_report_hash_binds_tracked_blob_not_checkout_line_endings(tmp_path):
    repository, _ = _accepted_repository(tmp_path)
    report_relative = "results_submission/reports/gate_a_report.json"
    token_path = repository / ACCEPTANCE_RELATIVE_PATH
    token = json.loads(token_path.read_text(encoding="utf-8"))

    report_path = repository / report_relative
    report_path.write_bytes(report_path.read_bytes().replace(b"\n", b"\r\n"))
    assert _sha256(report_path) != token["gate_report"]["sha256"]
    accepted = validate_gate_a_acceptance(repository)
    assert accepted.gate_report_sha256 == token["gate_report"]["sha256"]
