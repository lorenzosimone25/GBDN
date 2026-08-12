from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from gbdn.artifacts import ArtifactValidationError
from gbdn.submission_verify import validate_operator_notebook, verify_submission_readiness


ROOT = Path(__file__).resolve().parents[1]


def test_current_repository_verifier_is_read_only_and_blocked():
    before = sorted(path.as_posix() for path in (ROOT / "results_submission").rglob("*"))
    report = verify_submission_readiness(ROOT)
    after = sorted(path.as_posix() for path in (ROOT / "results_submission").rglob("*"))
    assert report.status == "BLOCKED"
    assert not report.ready_for_claim_bearing_execution
    assert not report.submission_complete
    assert before == after
    assert any("acceptance token is absent" in blocker for blocker in report.blockers)
    assert any("confirmatory_plan.json" in blocker for blocker in report.blockers)
    assert any("operations acceptance" in blocker for blocker in report.blockers)


def test_verify_cli_fails_loudly_with_machine_readable_inventory():
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_submission.py"), "verify"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["status"] == "BLOCKED"
    assert payload["ready_for_claim_bearing_execution"] is False
    assert payload["submission_complete"] is False
    assert completed.stderr == ""


def test_operator_notebook_is_thin_unexecuted_and_fail_loud(tmp_path):
    source = ROOT / "notebooks" / "gbdn_submission_h100.ipynb"
    validate_operator_notebook(source)
    notebook = json.loads(source.read_text(encoding="utf-8"))
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    code_cells[0]["source"] = ["import torch\n", "os.environ['CUDA_VISIBLE_DEVICES']='0'\n"]
    changed = tmp_path / "changed.ipynb"
    changed.write_text(json.dumps(notebook), encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="isolate GPU"):
        validate_operator_notebook(changed)
