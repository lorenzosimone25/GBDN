"""Fail-closed validation of independently reviewed heterophily operations."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Final, Mapping

from gbdn.artifacts import ArtifactValidationError, canonical_json_bytes, sha256_file


OPERATIONS_ACCEPTANCE_SCHEMA: Final[str] = "gbdn-operations-acceptance-v2"
OPERATIONS_REVIEW_SCHEMA: Final[str] = "gbdn-operations-independent-review-v1"
OPERATIONS_REVIEW_SCOPE: Final[str] = "CLAIM_BEARING_HETEROPHILY_EXECUTION"
OPERATIONS_ACCEPTANCE_PATH: Final[PurePosixPath] = PurePosixPath(
    "configs/submission/frozen/operations_acceptance.json"
)
PROTECTED_OPERATIONS_PATHS: Final[tuple[str, ...]] = (
    "configs/submission/frozen/confirmatory_plan.json",
    "requirements.lock",
    "results_submission/baseline_registry.json",
    "results_submission/run_plan.json",
    "scripts/run_heterophily_job.py",
    "scripts/run_submission.py",
    "src/gbdn/__init__.py",
    "src/gbdn/artifacts.py",
    "src/gbdn/baseline_contract.py",
    "src/gbdn/baselines/__init__.py",
    "src/gbdn/baselines/chebnet.py",
    "src/gbdn/baselines/chebnet_oracle.py",
    "src/gbdn/coefficient_artifacts.py",
    "src/gbdn/core.py",
    "src/gbdn/diagnostics.py",
    "src/gbdn/gate_a_evidence.py",
    "src/gbdn/gate_a_report.py",
    "src/gbdn/gate_acceptance.py",
    "src/gbdn/heterophily_contract.py",
    "src/gbdn/heterophily_evaluator.py",
    "src/gbdn/heterophily_statistics.py",
    "src/gbdn/heterophily_training.py",
    "src/gbdn/heterophily_worker.py",
    "src/gbdn/layers.py",
    "src/gbdn/model.py",
    "src/gbdn/operations_acceptance.py",
    "src/gbdn/oracle.py",
    "src/gbdn/paper_results.py",
    "src/gbdn/peel.py",
    "src/gbdn/provenance.py",
    "src/gbdn/run_plan.py",
    "src/gbdn/seed.py",
    "src/gbdn/spectral.py",
    "src/gbdn/submission.py",
    "src/gbdn/submission_scheduler.py",
    "src/gbdn/submission_verify.py",
    "src/gbdn/synthetic.py",
    "src/gbdn/viz.py",
    "tests/test_artifact_core.py",
    "tests/test_baseline_contract.py",
    "tests/test_chebnet_baseline.py",
    "tests/test_heterophily_contract.py",
    "tests/test_heterophily_evaluator.py",
    "tests/test_heterophily_training.py",
    "tests/test_heterophily_worker.py",
    "tests/test_operations_acceptance.py",
    "tests/test_run_plan.py",
    "tests/test_submission_scheduler.py",
    "tests/test_submission_verify.py",
)
REVIEWER_PRINCIPAL: Final[str] = "gbdn-independent-operations-review"
REVIEWER_PUBLIC_KEY: Final[str] = (
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHPXlfQwFGHMVE/sZuROb6HjTMsaDeUG1gmcx4sHTj21"
)
REVIEWER_KEY_FINGERPRINT: Final[str] = (
    "SHA256:25CtFgz2KnzGOIfQNrvGrem/Sbt0wOTgc6e9mBAZ21s"
)
_GIT = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_MAX_JSON_BYTES: Final[int] = 256 * 1024


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False
    )
    if check and result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ArtifactValidationError(
            f"operations acceptance git check failed: {' '.join(args)}: {detail}"
        )
    return result


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ArtifactValidationError(f"{label} keys do not match the frozen schema")


def _safe_path(value: Any, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ArtifactValidationError(f"{label} must be a POSIX relative path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or any(part in {"", ".", ".."} for part in value.split("/"))
        or value != path.as_posix()
    ):
        raise ArtifactValidationError(f"{label} contains an unsafe path segment")
    return path


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise ArtifactValidationError(f"duplicate JSON key: {key}")
        output[key] = value
    return output


def _reject_constant(value: str) -> None:
    raise ArtifactValidationError(f"non-standard JSON constant: {value}")


def _load_canonical_json_bytes(payload: bytes, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_unique_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError(f"{label} is invalid UTF-8 JSON") from exc
    if not isinstance(value, dict) or canonical_json_bytes(value) != payload:
        raise ArtifactValidationError(f"{label} is not canonical JSON")
    return value


def _load_regular_json(path: Path, label: str) -> tuple[bytes, Mapping[str, Any]]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > _MAX_JSON_BYTES:
        raise ArtifactValidationError(f"{label} is absent or unsafe")
    payload = path.read_bytes()
    return payload, _load_canonical_json_bytes(payload, label)


def _regular_blob_at(root: Path, commit: str, relative: str, label: str) -> bytes:
    listing = _git(root, "ls-tree", commit, "--", relative).stdout.decode().strip()
    fields = listing.split(maxsplit=3)
    if len(fields) != 4 or fields[0] not in {"100644", "100755"} or fields[1] != "blob":
        raise ArtifactValidationError(f"{label} is not a tracked regular blob at {commit}")
    return _git(root, "show", f"{commit}:{relative}").stdout


def _require_clean_regular_paths(root: Path, paths: tuple[str, ...], label: str) -> None:
    status = _git(
        root, "status", "--porcelain=v1", "--untracked-files=all", "--", *paths
    ).stdout
    if status.strip():
        raise ArtifactValidationError(f"{label} has staged, unstaged, deleted, or untracked changes")
    for relative in paths:
        lexical = root / PurePosixPath(relative)
        if lexical.is_symlink() or not lexical.is_file():
            raise ArtifactValidationError(f"{label} path is not a regular file: {relative}")
        resolved = lexical.resolve(strict=True)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ArtifactValidationError(f"{label} path escapes repository: {relative}") from exc
        _regular_blob_at(root, "HEAD", relative, label)


def _require_complete_canonical_package(root: Path) -> None:
    tracked = {
        line
        for line in _git(root, "ls-files", "src/gbdn/*.py", "src/gbdn/**/*.py")
        .stdout.decode()
        .splitlines()
        if line
    }
    frozen = {path for path in PROTECTED_OPERATIONS_PATHS if path.startswith("src/gbdn/")}
    source_root = root / "src" / "gbdn"
    filesystem: set[str] = set()
    for path in source_root.rglob("*.py"):
        if path.is_symlink() or not path.is_file():
            raise ArtifactValidationError("canonical package contains an unsafe Python path")
        filesystem.add(path.relative_to(root).as_posix())
    if tracked != frozen or filesystem != frozen:
        missing = sorted((tracked | filesystem) - frozen)
        stale = sorted(frozen - (tracked & filesystem))
        raise ArtifactValidationError(
            f"canonical package is outside frozen operations closure: extra={missing}, absent={stale}"
        )


def _verify_review_signature(root: Path, review_commit: str) -> None:
    allowed = f"{REVIEWER_PRINCIPAL} {REVIEWER_PUBLIC_KEY}\n"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", suffix=".allowed_signers", delete=False
    ) as stream:
        stream.write(allowed)
        allowed_path = Path(stream.name)
    try:
        verified = _git(
            root,
            "-c", f"gpg.ssh.allowedSignersFile={allowed_path}",
            "verify-commit", "--raw", review_commit,
            check=False,
        )
    finally:
        allowed_path.unlink(missing_ok=True)
    output = (verified.stdout + verified.stderr).decode("utf-8", errors="replace")
    if verified.returncode != 0 or REVIEWER_KEY_FINGERPRINT not in output:
        raise ArtifactValidationError("independent review commit lacks the frozen reviewer signature")


def _validate_machine_review(
    data: Mapping[str, Any], *, reviewed_commit: str, reviewed_tree: str
) -> None:
    _exact_keys(
        data,
        {
            "blockers",
            "decision",
            "protected_paths",
            "reviewed_source",
            "schema_version",
            "scope",
        },
        "operations independent review",
    )
    if data["schema_version"] != OPERATIONS_REVIEW_SCHEMA:
        raise ArtifactValidationError("operations independent review schema is invalid")
    if data["decision"] != "ACCEPT" or data["blockers"] != []:
        raise ArtifactValidationError("operations independent review is not unconditional ACCEPT")
    if data["scope"] != OPERATIONS_REVIEW_SCOPE:
        raise ArtifactValidationError("operations independent review scope is insufficient")
    if data["protected_paths"] != list(PROTECTED_OPERATIONS_PATHS):
        raise ArtifactValidationError("operations independent review protected scope differs")
    source = data["reviewed_source"]
    if not isinstance(source, dict):
        raise ArtifactValidationError("operations independent review source is invalid")
    _exact_keys(source, {"repository_commit", "repository_tree"}, "review source")
    if source != {"repository_commit": reviewed_commit, "repository_tree": reviewed_tree}:
        raise ArtifactValidationError("operations independent review is bound to another source")


@dataclass(frozen=True)
class OperationsAcceptance:
    reviewed_commit: str
    reviewed_tree: str
    review_commit: str
    review_path: str
    review_sha256: str
    handoff_path: str
    handoff_sha256: str


def validate_operations_acceptance(repository_root: str | Path) -> OperationsAcceptance:
    root = Path(repository_root).resolve(strict=True)
    token = root / OPERATIONS_ACCEPTANCE_PATH
    token_payload, data = _load_regular_json(token, "independent operations acceptance token")
    _exact_keys(
        data,
        {"decision", "protected_paths", "review", "reviewed_source", "schema_version"},
        "operations acceptance token",
    )
    if data["schema_version"] != OPERATIONS_ACCEPTANCE_SCHEMA:
        raise ArtifactValidationError("operations acceptance schema is invalid")
    if data["decision"] != "ACCEPT" or data["protected_paths"] != list(PROTECTED_OPERATIONS_PATHS):
        raise ArtifactValidationError("operations acceptance decision/scope is invalid")

    source, review = data["reviewed_source"], data["review"]
    if not isinstance(source, dict) or not isinstance(review, dict):
        raise ArtifactValidationError("operations acceptance bindings are invalid")
    _exact_keys(source, {"repository_commit", "repository_tree"}, "reviewed source")
    _exact_keys(
        review,
        {"commit", "handoff_path", "handoff_sha256", "path", "sha256"},
        "independent review binding",
    )
    commit, tree, review_commit = (
        source["repository_commit"], source["repository_tree"], review["commit"]
    )
    if any(not isinstance(value, str) or _GIT.fullmatch(value) is None for value in (commit, tree, review_commit)):
        raise ArtifactValidationError("operations source/review Git identity is invalid")
    if _git(root, "rev-parse", f"{commit}^{{tree}}").stdout.decode().strip() != tree:
        raise ArtifactValidationError("operations reviewed commit/tree is inconsistent")
    parents = _git(root, "show", "-s", "--format=%P", review_commit).stdout.decode().split()
    if parents != [commit]:
        raise ArtifactValidationError("independent review commit must directly follow reviewed source")
    _verify_review_signature(root, review_commit)
    for ancestor, descendant, label in (
        (commit, review_commit, "review commit does not descend from reviewed source"),
        (review_commit, "HEAD", "review commit is not an ancestor of HEAD"),
    ):
        if _git(root, "merge-base", "--is-ancestor", ancestor, descendant, check=False).returncode:
            raise ArtifactValidationError(label)

    review_path = _safe_path(review["path"], "operations review path")
    handoff_path = _safe_path(review["handoff_path"], "operations handoff path")
    if not review_path.as_posix().startswith("results_submission/reports/"):
        raise ArtifactValidationError("machine review must be under results_submission/reports")
    if not handoff_path.as_posix().startswith("handoffs/"):
        raise ArtifactValidationError("review handoff must be under handoffs")
    changed_by_review = tuple(
        line for line in _git(
            root, "diff-tree", "--no-commit-id", "--name-only", "-r", review_commit
        ).stdout.decode().splitlines() if line
    )
    if set(changed_by_review) != {review_path.as_posix(), handoff_path.as_posix()}:
        raise ArtifactValidationError("independent review commit contains files outside review and handoff")

    bound: list[tuple[str, PurePosixPath, Any]] = [
        ("machine review", review_path, review["sha256"]),
        ("review handoff", handoff_path, review["handoff_sha256"]),
    ]
    blobs: dict[str, bytes] = {}
    for label, relative, expected_hash in bound:
        if not isinstance(expected_hash, str) or _SHA256.fullmatch(expected_hash) is None:
            raise ArtifactValidationError(f"{label} hash is invalid")
        blob = _regular_blob_at(root, review_commit, relative.as_posix(), label)
        if hashlib.sha256(blob).hexdigest() != expected_hash:
            raise ArtifactValidationError(f"{label} review-commit blob hash does not match")
        current = root / relative
        if current.is_symlink() or not current.is_file() or sha256_file(current) != expected_hash:
            raise ArtifactValidationError(f"{label} current artifact does not match reviewed blob")
        blobs[label] = blob
    _validate_machine_review(
        _load_canonical_json_bytes(blobs["machine review"], "machine review"),
        reviewed_commit=commit,
        reviewed_tree=tree,
    )

    if _git(root, "merge-base", "--is-ancestor", commit, "HEAD", check=False).returncode:
        raise ArtifactValidationError("operations reviewed commit is not an ancestor")
    _require_complete_canonical_package(root)
    changed = _git(root, "diff", "--name-only", commit, "HEAD", "--", *PROTECTED_OPERATIONS_PATHS)
    if changed.stdout.strip():
        raise ArtifactValidationError("protected operations surface changed after review")
    for relative in PROTECTED_OPERATIONS_PATHS:
        _regular_blob_at(root, commit, relative, "reviewed operations surface")
    evidence_paths = (
        OPERATIONS_ACCEPTANCE_PATH.as_posix(), review_path.as_posix(), handoff_path.as_posix()
    )
    _require_clean_regular_paths(root, (*PROTECTED_OPERATIONS_PATHS, *evidence_paths), "operations acceptance surface")
    if canonical_json_bytes(data) != token_payload:
        raise ArtifactValidationError("operations token changed during validation")
    return OperationsAcceptance(
        commit, tree, review_commit, review_path.as_posix(), review["sha256"],
        handoff_path.as_posix(), review["handoff_sha256"]
    )


__all__ = [
    "OPERATIONS_ACCEPTANCE_PATH",
    "OPERATIONS_ACCEPTANCE_SCHEMA",
    "OPERATIONS_REVIEW_SCHEMA",
    "OPERATIONS_REVIEW_SCOPE",
    "PROTECTED_OPERATIONS_PATHS",
    "REVIEWER_KEY_FINGERPRINT",
    "REVIEWER_PRINCIPAL",
    "REVIEWER_PUBLIC_KEY",
    "OperationsAcceptance",
    "validate_operations_acceptance",
]
