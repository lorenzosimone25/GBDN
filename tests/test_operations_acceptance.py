from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from gbdn.artifacts import ArtifactValidationError, canonical_json_bytes
from gbdn.operations_acceptance import (
    OPERATIONS_ACCEPTANCE_PATH,
    OPERATIONS_ACCEPTANCE_SCHEMA,
    PROTECTED_OPERATIONS_PATHS,
    validate_operations_acceptance,
)


def test_operations_protected_scope_covers_scheduler_evaluator_and_contract_tests():
    required = {
        "src/gbdn/artifacts.py",
        "src/gbdn/heterophily_evaluator.py",
        "src/gbdn/operations_acceptance.py",
        "src/gbdn/submission_scheduler.py",
        "src/gbdn/submission_verify.py",
        "tests/test_artifact_core.py",
        "tests/test_heterophily_evaluator.py",
        "tests/test_operations_acceptance.py",
        "tests/test_submission_scheduler.py",
        "tests/test_submission_verify.py",
    }
    assert set(PROTECTED_OPERATIONS_PATHS) == required


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _repository(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repository"
    root.mkdir(parents=True)
    _git(root, "init")
    _git(root, "config", "user.name", "Independent Reviewer")
    _git(root, "config", "user.email", "review@example.org")
    for relative in PROTECTED_OPERATIONS_PATHS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"protected:{relative}\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "reviewed operations source")
    commit = _git(root, "rev-parse", "HEAD")
    tree = _git(root, "rev-parse", "HEAD^{tree}")
    review = root / "reviews" / "ops.md"
    review.parent.mkdir()
    review.write_text("Verdict: ACCEPT\n", encoding="utf-8")
    token = {
        "decision": "ACCEPT",
        "protected_paths": list(PROTECTED_OPERATIONS_PATHS),
        "review": {
            "independent": True,
            "path": "reviews/ops.md",
            "sha256": hashlib.sha256(review.read_bytes()).hexdigest(),
            "verdict": "ACCEPT",
        },
        "reviewed_source": {"repository_commit": commit, "repository_tree": tree},
        "schema_version": OPERATIONS_ACCEPTANCE_SCHEMA,
    }
    token_path = root / OPERATIONS_ACCEPTANCE_PATH
    token_path.parent.mkdir(parents=True)
    token_path.write_bytes(canonical_json_bytes(token))
    _git(root, "add", ".")
    _git(root, "commit", "-m", "bind independent operations acceptance")
    return root, token_path


def test_valid_operations_acceptance_is_review_and_source_bound(tmp_path):
    root, _ = _repository(tmp_path)
    accepted = validate_operations_acceptance(root)
    assert accepted.review_path == "reviews/ops.md"


def test_operations_acceptance_rejects_tamper_and_protected_drift(tmp_path):
    root, _ = _repository(tmp_path)
    (root / "reviews" / "ops.md").write_text("changed\n", encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="hash"):
        validate_operations_acceptance(root)

    root, _ = _repository(tmp_path / "drift")
    protected = root / PROTECTED_OPERATIONS_PATHS[0]
    protected.write_text("changed\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "drift protected surface")
    with pytest.raises(ArtifactValidationError, match="changed after review"):
        validate_operations_acceptance(root)


def test_operations_acceptance_rejects_noncanonical_or_untracked_token(tmp_path):
    root, token = _repository(tmp_path)
    data = json.loads(token.read_text(encoding="utf-8"))
    token.write_text(json.dumps(data, indent=2), encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="canonical"):
        validate_operations_acceptance(root)

    root, token = _repository(tmp_path / "untracked")
    _git(root, "rm", "--cached", token.relative_to(root).as_posix())
    with pytest.raises(ArtifactValidationError, match="not tracked"):
        validate_operations_acceptance(root)
