"""Fail-closed, source-bound Gate-A acceptance records.

This module validates a future independent review artifact.  It does not issue
acceptance, infer a verdict from tests, or create token files.  In particular,
the current repository has no acceptance token and remains blocked.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any, Final, Mapping

from gbdn.artifacts import ArtifactValidationError, canonical_json_bytes, sha256_file
from gbdn.gate_a_report import REPORT_SCHEMA


ACCEPTANCE_SCHEMA: Final[str] = "gbdn-gate-a-acceptance-v1"
ACCEPTANCE_RELATIVE_PATH: Final[PurePosixPath] = PurePosixPath(
    "configs/submission/frozen/gate_a_acceptance.json"
)
REQUIRED_GATE_IDS: Final[tuple[str, ...]] = tuple(
    f"GA-{index:02d}" for index in range(36)
)
PROTECTED_PATHS: Final[tuple[str, ...]] = (
    "scripts/report_gate_a.py",
    "scripts/run_submission.py",
    "src/gbdn/core.py",
    "src/gbdn/diagnostics.py",
    "src/gbdn/gate_acceptance.py",
    "src/gbdn/gate_a_evidence.py",
    "src/gbdn/gate_a_report.py",
    "src/gbdn/layers.py",
    "src/gbdn/model.py",
    "src/gbdn/oracle.py",
    "src/gbdn/peel.py",
    "src/gbdn/spectral.py",
    "src/gbdn/synthetic.py",
    "src/gbdn/submission.py",
    "tests/test_gate_a.py",
    "tests/test_gate_a_approximation.py",
    "tests/test_gate_a_closeout.py",
    "tests/test_gate_a_core_slice.py",
    "tests/test_gate_a_exact_slice.py",
    "tests/test_gate_a_fixture_completion.py",
    "tests/test_gate_a_fixture_matrix.py",
    "tests/test_gate_a_provenance.py",
    "tests/test_gate_a_public_boundary.py",
    "tests/test_gate_acceptance.py",
)
_GIT_OBJECT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_MAX_TOKEN_BYTES: Final[int] = 128 * 1024
_MAX_REPORT_BYTES: Final[int] = 8 * 1024 * 1024


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ArtifactValidationError(f"{label} keys do not match the frozen schema")


def _safe_path(value: Any, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ArtifactValidationError(f"{label} must be a POSIX relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ArtifactValidationError(f"{label} contains an unsafe path segment")
    return path


def _git(root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ArtifactValidationError(f"git {' '.join(arguments)} failed: {detail}")
    return completed


def _load_canonical_json(path: Path) -> Mapping[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > _MAX_TOKEN_BYTES:
        raise ArtifactValidationError("Gate-A token must be a bounded regular file")
    payload = path.read_bytes()

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in pairs:
            if key in output:
                raise ArtifactValidationError(f"duplicate Gate-A token key: {key}")
            output[key] = value
        return output

    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError("Gate-A token must be UTF-8 JSON") from exc
    if not isinstance(value, dict) or canonical_json_bytes(value) != payload:
        raise ArtifactValidationError("Gate-A token must use canonical JSON serialization")
    return value


def _load_gate_report(path: Path) -> Mapping[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > _MAX_REPORT_BYTES:
        raise ArtifactValidationError("Gate-A report must be a bounded regular file")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=lambda pairs: _unique_pairs(pairs, "Gate-A report"),
            parse_constant=lambda value: _reject_constant(value, "Gate-A report"),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError("Gate-A report must be valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ArtifactValidationError("Gate-A report must be a JSON object")
    return value


def _unique_pairs(pairs: list[tuple[str, Any]], label: str) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise ArtifactValidationError(f"duplicate key in {label}: {key}")
        output[key] = value
    return output


def _reject_constant(value: str, label: str) -> None:
    raise ArtifactValidationError(f"non-standard JSON constant in {label}: {value}")


def _validate_gate_report(
    report: Mapping[str, Any], *, commit: str, tree: str
) -> None:
    """Require the executable report's complete passing pre-review state."""

    try:
        source = report["source"]
        pytest_state = report["pytest"]
        summary = report["summary"]
        evidence = report["gate_a_evidence"]
        cross_validation = report["coverage_evidence_cross_validation"]
        acceptance = report["gate_a_acceptance"]
        ids = report["ids"]
    except KeyError as exc:
        raise ArtifactValidationError("Gate-A report is missing a required section") from exc
    if report.get("schema") != REPORT_SCHEMA:
        raise ArtifactValidationError("Gate-A report has the wrong schema")
    if not isinstance(source, dict) or source.get("tested_source_commit") != commit:
        raise ArtifactValidationError("Gate-A report is not bound to the reviewed commit")
    if source.get("source_tree_dirty") is not False:
        raise ArtifactValidationError("Gate-A report source tree was dirty")
    if not isinstance(pytest_state, dict) or pytest_state.get("tests_executed") is not True:
        raise ArtifactValidationError("Gate-A report did not execute tests")
    if pytest_state.get("exit_code") != 0:
        raise ArtifactValidationError("Gate-A pytest execution failed")
    if not isinstance(summary, dict):
        raise ArtifactValidationError("Gate-A report summary is invalid")
    if summary.get("required_id_count") != 36 or summary.get(
        "all_required_ids_executed_and_passing"
    ) is not True:
        raise ArtifactValidationError("Gate-A report does not pass all 36 required rows")
    for key in (
        "missing_ids",
        "failed_ids",
        "not_run_ids",
        "ids_without_machine_readable_evidence",
    ):
        if summary.get(key) != []:
            raise ArtifactValidationError(f"Gate-A report summary contains {key}")
    if not isinstance(ids, dict) or tuple(sorted(ids)) != REQUIRED_GATE_IDS:
        raise ArtifactValidationError("Gate-A report row inventory is incomplete")
    if any(not isinstance(row, dict) or row.get("execution_status") != "PASS" for row in ids.values()):
        raise ArtifactValidationError("Gate-A report contains a non-passing row")
    if not isinstance(evidence, dict):
        raise ArtifactValidationError("Gate-A evidence section is invalid")
    for key in ("schema_errors", "failed_decisions", "provenance_link_errors"):
        if evidence.get(key) != []:
            raise ArtifactValidationError(f"Gate-A evidence contains {key}")
    if not isinstance(cross_validation, dict) or cross_validation.get("status") != "PASS":
        raise ArtifactValidationError("Gate-A coverage/evidence cross-validation failed")
    # Before the independent verdict is installed, the executable utility must
    # fail closed solely because reviewer acceptance is not self-issued.
    if not isinstance(acceptance, dict) or acceptance.get("accepted") is not False:
        raise ArtifactValidationError("Gate-A executable report improperly self-accepts")
    blockers = acceptance.get("blockers")
    if blockers != ["independent reviewer acceptance has not been recorded by this utility"]:
        raise ArtifactValidationError("Gate-A report has unresolved blockers beyond review")


@dataclass(frozen=True)
class GateAAcceptance:
    reviewed_repository_commit: str
    reviewed_repository_tree: str
    gate_report_path: str
    gate_report_sha256: str
    review_artifact_path: str
    review_artifact_sha256: str
    issued_at_utc: str


def validate_gate_a_acceptance(
    repository_root: str | Path,
    token_path: str | Path = ACCEPTANCE_RELATIVE_PATH,
) -> GateAAcceptance:
    """Validate a tracked independent acceptance record against current source.

    The reviewed commit must be an ancestor of ``HEAD`` and none of the frozen
    mathematical implementation, evidence, reporter, or Gate-A test paths may
    have changed since that commit.  Report and review files are content-bound
    and tracked.  This function never accepts a partial/conditional verdict.
    """

    root = Path(repository_root).resolve(strict=True)
    requested = Path(token_path)
    token = (requested if requested.is_absolute() else root / requested).resolve(
        strict=False
    )
    try:
        relative_token = token.relative_to(root).as_posix()
    except ValueError as exc:
        raise ArtifactValidationError("Gate-A token lies outside the repository") from exc
    if relative_token != ACCEPTANCE_RELATIVE_PATH.as_posix():
        raise ArtifactValidationError("Gate-A token is not at the frozen path")
    if not token.exists():
        raise ArtifactValidationError(
            "claim-bearing mode is blocked: independent Gate-A acceptance token is absent"
        )
    data = _load_canonical_json(token)
    _exact_keys(
        data,
        {
            "decision",
            "gate",
            "gate_report",
            "issued_at_utc",
            "protected_paths",
            "review",
            "reviewed_source",
            "row_verdicts",
            "schema_version",
        },
        "Gate-A token",
    )
    if data["schema_version"] != ACCEPTANCE_SCHEMA or data["gate"] != "Gate A":
        raise ArtifactValidationError("Gate-A token schema or gate identity is invalid")
    if data["decision"] != "ACCEPT":
        raise ArtifactValidationError("Gate-A token does not contain binary acceptance")
    if data["protected_paths"] != list(PROTECTED_PATHS):
        raise ArtifactValidationError("Gate-A protected path set differs from the frozen contract")
    verdicts = data["row_verdicts"]
    if not isinstance(verdicts, dict) or tuple(sorted(verdicts)) != REQUIRED_GATE_IDS:
        raise ArtifactValidationError("Gate-A token must adjudicate GA-00 through GA-35 exactly")
    if any(value != "ACCEPT" for value in verdicts.values()):
        raise ArtifactValidationError("Gate-A token contains a non-accepted row")

    source = data["reviewed_source"]
    report = data["gate_report"]
    review = data["review"]
    for value, expected, label in (
        (source, {"repository_commit", "repository_tree"}, "reviewed_source"),
        (report, {"path", "schema", "sha256"}, "gate_report"),
        (review, {"independent", "path", "sha256", "verdict"}, "review"),
    ):
        if not isinstance(value, dict):
            raise ArtifactValidationError(f"{label} must be an object")
        _exact_keys(value, expected, label)
    commit = source["repository_commit"]
    tree = source["repository_tree"]
    if not isinstance(commit, str) or _GIT_OBJECT.fullmatch(commit) is None:
        raise ArtifactValidationError("reviewed commit is not a full Git object ID")
    if not isinstance(tree, str) or _GIT_OBJECT.fullmatch(tree) is None:
        raise ArtifactValidationError("reviewed tree is not a full Git object ID")
    if report["schema"] != REPORT_SCHEMA:
        raise ArtifactValidationError("Gate-A report schema is not the executable schema")
    if review["independent"] is not True or review["verdict"] != "ACCEPT":
        raise ArtifactValidationError("review artifact does not declare independent acceptance")
    issued = data["issued_at_utc"]
    if not isinstance(issued, str) or not issued.endswith("Z"):
        raise ArtifactValidationError("Gate-A token issued_at_utc is invalid")
    try:
        issued_time = datetime.fromisoformat(issued[:-1] + "+00:00")
    except ValueError as exc:
        raise ArtifactValidationError("Gate-A token issued_at_utc is invalid") from exc
    if issued_time.utcoffset() != timedelta(0):
        raise ArtifactValidationError("Gate-A token issued_at_utc must use UTC")

    observed_tree = _git(root, "rev-parse", f"{commit}^{{tree}}").stdout.decode().strip()
    if observed_tree != tree:
        raise ArtifactValidationError("reviewed commit/tree pair is inconsistent")
    if _git(root, "merge-base", "--is-ancestor", commit, "HEAD", check=False).returncode != 0:
        raise ArtifactValidationError("reviewed commit is not an ancestor of current HEAD")
    changed = _git(root, "diff", "--name-only", commit, "HEAD", "--", *PROTECTED_PATHS)
    if changed.stdout.strip():
        raise ArtifactValidationError("Gate-A protected source changed after independent review")
    if _git(root, "diff", "--quiet", "HEAD", "--", *PROTECTED_PATHS, check=False).returncode != 0:
        raise ArtifactValidationError("Gate-A protected source has uncommitted changes")

    bound: dict[str, tuple[PurePosixPath, str]] = {
        "gate report": (_safe_path(report["path"], "gate report path"), report["sha256"]),
        "review artifact": (_safe_path(review["path"], "review artifact path"), review["sha256"]),
    }
    for label, (relative, expected_hash) in bound.items():
        if not isinstance(expected_hash, str) or _SHA256.fullmatch(expected_hash) is None:
            raise ArtifactValidationError(f"{label} SHA-256 is invalid")
        artifact = (root / relative).resolve(strict=False)
        try:
            artifact.relative_to(root)
        except ValueError as exc:
            raise ArtifactValidationError(f"{label} lies outside the repository") from exc
        if artifact.is_symlink() or not artifact.is_file():
            raise ArtifactValidationError(f"{label} must be a regular file")
        if sha256_file(artifact) != expected_hash:
            raise ArtifactValidationError(f"{label} content hash does not match token")
        if _git(root, "ls-files", "--error-unmatch", relative.as_posix(), check=False).returncode != 0:
            raise ArtifactValidationError(f"{label} is not tracked")
        if _git(root, "diff", "--quiet", "HEAD", "--", relative.as_posix(), check=False).returncode != 0:
            raise ArtifactValidationError(f"{label} has uncommitted changes")
        if label == "gate report":
            _validate_gate_report(_load_gate_report(artifact), commit=commit, tree=tree)
    if _git(root, "ls-files", "--error-unmatch", relative_token, check=False).returncode != 0:
        raise ArtifactValidationError("Gate-A token is not tracked")
    if _git(root, "diff", "--quiet", "HEAD", "--", relative_token, check=False).returncode != 0:
        raise ArtifactValidationError("Gate-A token has uncommitted changes")
    return GateAAcceptance(
        commit,
        tree,
        report["path"],
        report["sha256"],
        review["path"],
        review["sha256"],
        issued,
    )


__all__ = [
    "ACCEPTANCE_RELATIVE_PATH",
    "ACCEPTANCE_SCHEMA",
    "GateAAcceptance",
    "PROTECTED_PATHS",
    "REQUIRED_GATE_IDS",
    "validate_gate_a_acceptance",
]
