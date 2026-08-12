from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gbdn.provenance import (  # noqa: E402
    FROZEN_LEGACY_RESULT_DIRS,
    RepositoryBoundaryError,
    canonical_output_path,
    write_new_canonical_artifact,
)


def test_clean_checkout_declares_installable_canonical_package():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["project"]["name"] == "gbdn-research"
    assert metadata["project"]["requires-python"] == ">=3.11,<3.13"
    assert metadata["tool"]["setuptools"]["package-dir"] == {"": "src"}
    assert metadata["tool"]["setuptools"]["packages"]["find"]["include"] == [
        "gbdn*"
    ]


def test_h100_setup_installs_and_imports_canonical_package():
    setup = (ROOT / "scripts" / "setup_h100.sh").read_text(encoding="utf-8")

    assert '"${PYTHON}" -m pip install --no-deps --editable "${ROOT}"' in setup
    assert "import gbdn" in setup


@pytest.mark.parametrize("frozen_root", FROZEN_LEGACY_RESULT_DIRS)
def test_canonical_writer_rejects_every_frozen_result_tree(tmp_path, frozen_root):
    target = tmp_path / frozen_root / "new-run" / "result.json"

    with pytest.raises(RepositoryBoundaryError, match="frozen legacy tree"):
        write_new_canonical_artifact(
            target,
            b"must not be written",
            repository_root=tmp_path,
        )

    assert not target.exists()


def test_canonical_writer_accepts_only_submission_descendants(tmp_path):
    relative = Path("results_submission") / "runs" / "run-001" / "result.json"
    expected = (tmp_path / relative).resolve()

    assert canonical_output_path(relative, repository_root=tmp_path) == expected
    assert write_new_canonical_artifact(
        relative,
        b'{"identity":"run-001"}',
        repository_root=tmp_path,
    ) == expected
    assert expected.read_bytes() == b'{"identity":"run-001"}'


@pytest.mark.parametrize(
    "invalid",
    (
        "results_submission",
        "results_submission_backup/run.json",
        "artifacts/run.json",
        "paper/generated/table.tex",
    ),
)
def test_canonical_writer_rejects_non_submission_paths(tmp_path, invalid):
    with pytest.raises(RepositoryBoundaryError, match="results_submission"):
        canonical_output_path(invalid, repository_root=tmp_path)


def test_canonical_writer_never_overwrites_a_completed_identity(tmp_path):
    target = Path("results_submission/runs/run-001/result.json")
    write_new_canonical_artifact(target, b"first", repository_root=tmp_path)

    with pytest.raises(FileExistsError):
        write_new_canonical_artifact(target, b"changed", repository_root=tmp_path)

    assert (tmp_path / target).read_bytes() == b"first"
