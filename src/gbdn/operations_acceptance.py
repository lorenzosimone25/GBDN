"""Fail-closed validation of independent scheduler-operations acceptance."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Final

from gbdn.artifacts import ArtifactValidationError, canonical_json_bytes, sha256_file


OPERATIONS_ACCEPTANCE_SCHEMA: Final[str] = "gbdn-operations-acceptance-v1"
OPERATIONS_ACCEPTANCE_PATH: Final[PurePosixPath] = PurePosixPath(
    "configs/submission/frozen/operations_acceptance.json"
)
PROTECTED_OPERATIONS_PATHS: Final[tuple[str, ...]] = (
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
)
_GIT = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False
    )
    if check and result.returncode:
        raise ArtifactValidationError(f"operations acceptance git check failed: {' '.join(args)}")
    return result


@dataclass(frozen=True)
class OperationsAcceptance:
    reviewed_commit: str
    reviewed_tree: str
    review_path: str
    review_sha256: str


def validate_operations_acceptance(repository_root: str | Path) -> OperationsAcceptance:
    root = Path(repository_root).resolve(strict=True)
    token = root / OPERATIONS_ACCEPTANCE_PATH
    if token.is_symlink() or not token.is_file() or token.stat().st_size > 128 * 1024:
        raise ArtifactValidationError("independent operations acceptance token is absent or unsafe")
    payload = token.read_bytes()
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError("operations acceptance token is invalid JSON") from exc
    if not isinstance(data, dict) or canonical_json_bytes(data) != payload:
        raise ArtifactValidationError("operations acceptance token is not canonical JSON")
    expected = {
        "decision", "protected_paths", "review", "reviewed_source", "schema_version"
    }
    if set(data) != expected or data["schema_version"] != OPERATIONS_ACCEPTANCE_SCHEMA:
        raise ArtifactValidationError("operations acceptance schema is invalid")
    if data["decision"] != "ACCEPT" or data["protected_paths"] != list(PROTECTED_OPERATIONS_PATHS):
        raise ArtifactValidationError("operations acceptance decision/scope is invalid")
    source, review = data["reviewed_source"], data["review"]
    if not isinstance(source, dict) or set(source) != {"repository_commit", "repository_tree"}:
        raise ArtifactValidationError("operations reviewed source is invalid")
    if not isinstance(review, dict) or set(review) != {"independent", "path", "sha256", "verdict"}:
        raise ArtifactValidationError("operations review binding is invalid")
    commit, tree = source["repository_commit"], source["repository_tree"]
    if not isinstance(commit, str) or _GIT.fullmatch(commit) is None:
        raise ArtifactValidationError("operations reviewed commit is invalid")
    if not isinstance(tree, str) or _GIT.fullmatch(tree) is None:
        raise ArtifactValidationError("operations reviewed tree is invalid")
    if review["independent"] is not True or review["verdict"] != "ACCEPT":
        raise ArtifactValidationError("operations review does not independently ACCEPT")
    relative = PurePosixPath(review["path"] if isinstance(review["path"], str) else "")
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ArtifactValidationError("operations review path is unsafe")
    review_hash = review["sha256"]
    if not isinstance(review_hash, str) or _SHA256.fullmatch(review_hash) is None:
        raise ArtifactValidationError("operations review hash is invalid")
    artifact = root / relative
    if artifact.is_symlink() or not artifact.is_file() or sha256_file(artifact) != review_hash:
        raise ArtifactValidationError("operations review artifact hash does not match")
    observed_tree = _git(root, "rev-parse", f"{commit}^{{tree}}").stdout.decode().strip()
    if observed_tree != tree:
        raise ArtifactValidationError("operations reviewed commit/tree is inconsistent")
    if _git(root, "merge-base", "--is-ancestor", commit, "HEAD", check=False).returncode:
        raise ArtifactValidationError("operations reviewed commit is not an ancestor")
    changed = _git(root, "diff", "--name-only", commit, "HEAD", "--", *PROTECTED_OPERATIONS_PATHS)
    if changed.stdout.strip():
        raise ArtifactValidationError("protected operations surface changed after review")
    for relative_path in (OPERATIONS_ACCEPTANCE_PATH.as_posix(), relative.as_posix()):
        if _git(root, "ls-files", "--error-unmatch", relative_path, check=False).returncode:
            raise ArtifactValidationError("operations acceptance evidence is not tracked")
        if _git(root, "diff", "--quiet", "HEAD", "--", relative_path, check=False).returncode:
            raise ArtifactValidationError("operations acceptance evidence has uncommitted changes")
    return OperationsAcceptance(commit, tree, relative.as_posix(), review_hash)


__all__ = [
    "OPERATIONS_ACCEPTANCE_PATH",
    "OPERATIONS_ACCEPTANCE_SCHEMA",
    "PROTECTED_OPERATIONS_PATHS",
    "OperationsAcceptance",
    "validate_operations_acceptance",
]
