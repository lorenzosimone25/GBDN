"""Repository output boundaries shared by canonical GBDN runners.

This module deliberately contains no model or experiment logic. Canonical
writers use it to keep new artifacts out of frozen legacy result trees and to
make artifact creation non-overwriting by default.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final


FROZEN_LEGACY_RESULT_DIRS: Final[tuple[str, ...]] = (
    "results",
    "results_repro",
    "results_LRGB",
    "results_LRGB_repro",
)
CANONICAL_RESULT_DIR: Final[str] = "results_submission"


class RepositoryBoundaryError(ValueError):
    """Raised when canonical code targets a path outside its output tree."""


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def canonical_output_path(
    output_path: str | Path,
    *,
    repository_root: str | Path,
) -> Path:
    """Resolve and validate one canonical output file path.

    Relative paths are interpreted from ``repository_root``. Only descendants
    of ``results_submission`` are accepted. Resolution also prevents an
    existing symlink from escaping that directory.
    """

    root = Path(repository_root).resolve(strict=True)
    requested = Path(output_path)
    target = (requested if requested.is_absolute() else root / requested).resolve(
        strict=False
    )

    for name in FROZEN_LEGACY_RESULT_DIRS:
        frozen_root = (root / name).resolve(strict=False)
        if target == frozen_root or _is_within(target, frozen_root):
            raise RepositoryBoundaryError(
                f"canonical writers cannot target frozen legacy tree: {name}"
            )

    canonical_root = (root / CANONICAL_RESULT_DIR).resolve(strict=False)
    if target == canonical_root or not _is_within(target, canonical_root):
        raise RepositoryBoundaryError(
            f"canonical outputs must be files below {CANONICAL_RESULT_DIR}/"
        )
    return target


def write_new_canonical_artifact(
    output_path: str | Path,
    payload: bytes,
    *,
    repository_root: str | Path,
) -> Path:
    """Create a canonical artifact once, without overwriting an existing file."""

    target = canonical_output_path(output_path, repository_root=repository_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(payload)
    return target
