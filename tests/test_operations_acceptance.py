from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

import gbdn.operations_acceptance as operations_acceptance
from gbdn.artifacts import ArtifactValidationError, canonical_json_bytes
from gbdn.operations_acceptance import (
    OPERATIONS_ACCEPTANCE_PATH,
    OPERATIONS_ACCEPTANCE_SCHEMA,
    OPERATIONS_REVIEW_SCHEMA,
    OPERATIONS_REVIEW_SCOPE,
    PROTECTED_OPERATIONS_PATHS,
    validate_operations_acceptance,
)


_TEST_SIGNING_KEY: Path | None = None


@pytest.fixture(autouse=True)
def _test_review_key(tmp_path, monkeypatch):
    global _TEST_SIGNING_KEY
    key = tmp_path / "review-key"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "test-reviewer", "-f", str(key)],
        check=True,
    )
    public = key.with_suffix(".pub").read_text(encoding="utf-8").split()
    fingerprint = subprocess.run(
        ["ssh-keygen", "-lf", str(key.with_suffix(".pub"))],
        check=True, capture_output=True, text=True,
    ).stdout.split()[1]
    monkeypatch.setattr(operations_acceptance, "REVIEWER_PUBLIC_KEY", " ".join(public[:2]))
    monkeypatch.setattr(operations_acceptance, "REVIEWER_KEY_FINGERPRINT", fingerprint)
    _TEST_SIGNING_KEY = key
    yield
    _TEST_SIGNING_KEY = None


def _git(root: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], check=False, capture_output=True, text=True
    )
    if check:
        result.check_returncode()
    return result.stdout.strip()


def _write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _repository(
    tmp_path: Path,
    *,
    review_scope: str = OPERATIONS_REVIEW_SCOPE,
    extra_review_file: bool = False,
) -> tuple[Path, Path, dict, str]:
    root = tmp_path / "repository"
    root.mkdir(parents=True)
    _git(root, "init")
    _git(root, "config", "user.name", "Independent Reviewer")
    _git(root, "config", "user.email", "review@example.org")
    assert _TEST_SIGNING_KEY is not None
    _git(root, "config", "gpg.format", "ssh")
    _git(root, "config", "user.signingkey", str(_TEST_SIGNING_KEY))
    _git(root, "config", "commit.gpgsign", "true")
    for relative in PROTECTED_OPERATIONS_PATHS:
        _write(root / relative, f"protected:{relative}\n".encode())
    _git(root, "add", ".")
    _git(root, "commit", "-m", "reviewed operations source")
    commit = _git(root, "rev-parse", "HEAD")
    tree = _git(root, "show", "-s", "--format=%T", "HEAD")

    review_path = Path("results_submission/reports/operations_review.json")
    handoff_path = Path("handoffs/operations_review.md")
    review_payload = canonical_json_bytes(
        {
            "blockers": [],
            "decision": "ACCEPT",
            "protected_paths": list(PROTECTED_OPERATIONS_PATHS),
            "reviewed_source": {
                "repository_commit": commit,
                "repository_tree": tree,
            },
            "schema_version": OPERATIONS_REVIEW_SCHEMA,
            "scope": review_scope,
        }
    )
    handoff_payload = b"Independent unconditional operations acceptance.\n"
    _write(root / review_path, review_payload)
    _write(root / handoff_path, handoff_payload)
    if extra_review_file:
        _write(root / "src/unreviewed.py", b"unreviewed\n")
    _git(root, "add", review_path.as_posix(), handoff_path.as_posix())
    if extra_review_file:
        _git(root, "add", "src/unreviewed.py")
    _git(root, "commit", "-m", "independent operations review")
    review_commit = _git(root, "rev-parse", "HEAD")

    token = {
        "decision": "ACCEPT",
        "protected_paths": list(PROTECTED_OPERATIONS_PATHS),
        "review": {
            "commit": review_commit,
            "handoff_path": handoff_path.as_posix(),
            "handoff_sha256": hashlib.sha256(handoff_payload).hexdigest(),
            "path": review_path.as_posix(),
            "sha256": hashlib.sha256(review_payload).hexdigest(),
        },
        "reviewed_source": {"repository_commit": commit, "repository_tree": tree},
        "schema_version": OPERATIONS_ACCEPTANCE_SCHEMA,
    }
    token_path = root / OPERATIONS_ACCEPTANCE_PATH
    _write(token_path, canonical_json_bytes(token))
    _git(root, "add", token_path.relative_to(root).as_posix())
    _git(root, "commit", "-m", "bind independent operations acceptance")
    return root, token_path, token, review_commit


def test_operations_protected_scope_covers_claim_bearing_worker_and_dependencies():
    required = {
        "configs/submission/frozen/confirmatory_plan.json",
        "results_submission/baseline_registry.json",
        "results_submission/run_plan.json",
        "scripts/run_heterophily_job.py",
        "src/gbdn/heterophily_worker.py",
        "tests/test_heterophily_worker.py",
        "src/gbdn/submission_scheduler.py",
        "src/gbdn/heterophily_evaluator.py",
        "src/gbdn/baseline_contract.py",
        "src/gbdn/run_plan.py",
    }
    assert required <= set(PROTECTED_OPERATIONS_PATHS)


def test_valid_operations_acceptance_is_review_commit_and_source_bound(tmp_path):
    root, _, _, review_commit = _repository(tmp_path)
    accepted = validate_operations_acceptance(root)
    assert accepted.review_commit == review_commit
    assert accepted.review_path == "results_submission/reports/operations_review.json"


@pytest.mark.parametrize("staged", [False, True])
def test_operations_acceptance_rejects_dirty_protected_source(tmp_path, staged):
    root, _, _, _ = _repository(tmp_path)
    protected = root / PROTECTED_OPERATIONS_PATHS[0]
    protected.write_text("unreviewed mutation\n", encoding="utf-8")
    if staged:
        _git(root, "add", protected.relative_to(root).as_posix())
    with pytest.raises(ArtifactValidationError, match="changes"):
        validate_operations_acceptance(root)


def test_operations_acceptance_rejects_committed_protected_drift(tmp_path):
    root, _, _, _ = _repository(tmp_path)
    protected = root / PROTECTED_OPERATIONS_PATHS[0]
    protected.write_text("committed mutation\n", encoding="utf-8")
    _git(root, "add", protected.relative_to(root).as_posix())
    _git(root, "commit", "-m", "unreviewed protected drift")
    with pytest.raises(ArtifactValidationError, match="changed after review"):
        validate_operations_acceptance(root)


def test_rehashed_forged_review_cannot_replace_independent_commit_blob(tmp_path):
    root, token_path, token, review_commit = _repository(tmp_path)
    review = root / token["review"]["path"]
    forged = canonical_json_bytes(
        {
            "blockers": [],
            "decision": "ACCEPT",
            "protected_paths": list(PROTECTED_OPERATIONS_PATHS),
            "reviewed_source": token["reviewed_source"],
            "schema_version": OPERATIONS_REVIEW_SCHEMA,
            "scope": OPERATIONS_REVIEW_SCOPE,
        }
    ) + b" "
    review.write_bytes(forged)
    token["review"]["sha256"] = hashlib.sha256(forged).hexdigest()
    token_path.write_bytes(canonical_json_bytes(token))
    _git(root, "add", ".")
    _git(root, "commit", "-m", "token author forges review")
    assert token["review"]["commit"] == review_commit
    with pytest.raises(ArtifactValidationError, match="blob hash"):
        validate_operations_acceptance(root)


def test_scheduler_only_review_cannot_be_upgraded_to_claim_bearing_acceptance(tmp_path):
    root, _, _, _ = _repository(tmp_path, review_scope="SCHEDULER_SUBSTRATE_ONLY")
    with pytest.raises(ArtifactValidationError, match="scope"):
        validate_operations_acceptance(root)


@pytest.mark.parametrize(
    "mutation,match",
    [
        (b'{"decision":"ACCEPT","decision":"ACCEPT"}\n', "duplicate"),
        (b'{"decision":NaN}\n', "non-standard"),
    ],
)
def test_operations_acceptance_rejects_duplicate_keys_and_nonfinite_constants(
    tmp_path, mutation, match
):
    root, token, _, _ = _repository(tmp_path)
    token.write_bytes(mutation)
    with pytest.raises(ArtifactValidationError, match=match):
        validate_operations_acceptance(root)


@pytest.mark.parametrize("unsafe", ["../review.json", "C:/review.json", "reviews\\ops.json"])
def test_operations_acceptance_rejects_unsafe_review_paths(tmp_path, unsafe):
    root, token_path, token, _ = _repository(tmp_path)
    token["review"]["path"] = unsafe
    token_path.write_bytes(canonical_json_bytes(token))
    with pytest.raises(ArtifactValidationError, match="path"):
        validate_operations_acceptance(root)


def test_review_commit_cannot_hide_extra_authored_files(tmp_path):
    root, _, _, _ = _repository(tmp_path, extra_review_file=True)
    with pytest.raises(ArtifactValidationError, match="outside review and handoff"):
        validate_operations_acceptance(root)


def test_review_commit_must_directly_follow_reviewed_source(tmp_path):
    root, token_path, token, _ = _repository(tmp_path)
    marker = root / "docs" / "intermediate.md"
    _write(marker, b"intermediate author-controlled commit\n")
    _git(root, "add", marker.relative_to(root).as_posix())
    _git(root, "commit", "-m", "unreviewed intermediate commit")
    review_path = root / token["review"]["path"]
    handoff_path = root / token["review"]["handoff_path"]
    review_path.write_bytes(review_path.read_bytes() + b" ")
    handoff_path.write_bytes(handoff_path.read_bytes() + b" ")
    _git(root, "add", token["review"]["path"], token["review"]["handoff_path"])
    _git(root, "commit", "-m", "late review")
    token["review"]["commit"] = _git(root, "rev-parse", "HEAD")
    token["review"]["sha256"] = hashlib.sha256(review_path.read_bytes()).hexdigest()
    token["review"]["handoff_sha256"] = hashlib.sha256(handoff_path.read_bytes()).hexdigest()
    token_path.write_bytes(canonical_json_bytes(token))
    _git(root, "add", token_path.relative_to(root).as_posix())
    _git(root, "commit", "-m", "bind late review")
    with pytest.raises(ArtifactValidationError, match="directly follow"):
        validate_operations_acceptance(root)


def test_unsigned_self_issued_review_is_rejected(tmp_path):
    root, token_path, token, _ = _repository(tmp_path)
    reviewed = token["reviewed_source"]["repository_commit"]
    _git(root, "checkout", reviewed)
    _git(root, "config", "commit.gpgsign", "false")
    review_path = Path(token["review"]["path"])
    handoff_path = Path(token["review"]["handoff_path"])
    review_payload = canonical_json_bytes(
        {
            "blockers": [],
            "decision": "ACCEPT",
            "protected_paths": list(PROTECTED_OPERATIONS_PATHS),
            "reviewed_source": token["reviewed_source"],
            "schema_version": OPERATIONS_REVIEW_SCHEMA,
            "scope": OPERATIONS_REVIEW_SCOPE,
        }
    )
    handoff_payload = b"Self-issued review.\n"
    _write(root / review_path, review_payload)
    _write(root / handoff_path, handoff_payload)
    _git(root, "add", review_path.as_posix(), handoff_path.as_posix())
    _git(root, "commit", "-m", "unsigned self review")
    token["review"].update(
        commit=_git(root, "rev-parse", "HEAD"),
        sha256=hashlib.sha256(review_payload).hexdigest(),
        handoff_sha256=hashlib.sha256(handoff_payload).hexdigest(),
    )
    _write(token_path, canonical_json_bytes(token))
    _git(root, "add", token_path.relative_to(root).as_posix())
    _git(root, "commit", "-m", "self-issued token")
    with pytest.raises(ArtifactValidationError, match="signature"):
        validate_operations_acceptance(root)


@pytest.mark.parametrize(
    "alias",
    [
        "results_submission/reports/./operations_review.json",
        "results_submission//reports/operations_review.json",
        "results_submission/reports/operations_review.json/",
    ],
)
def test_operations_acceptance_rejects_noncanonical_path_aliases(tmp_path, alias):
    root, token_path, token, _ = _repository(tmp_path)
    token["review"]["path"] = alias
    token_path.write_bytes(canonical_json_bytes(token))
    with pytest.raises(ArtifactValidationError, match="path"):
        validate_operations_acceptance(root)
