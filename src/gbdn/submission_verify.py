"""Read-only fail-loud inventory for submission readiness."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from gbdn.artifacts import ArtifactValidationError
from gbdn.gate_acceptance import validate_gate_a_acceptance


def validate_operator_notebook(path: str | Path) -> None:
    """Validate the thin, unexecuted, fail-loud H100 operator notebook."""

    notebook_path = Path(path)
    if (
        notebook_path.is_symlink()
        or not notebook_path.is_file()
        or notebook_path.stat().st_size > 1024 * 1024
    ):
        raise ArtifactValidationError("operator notebook must be a bounded regular file")
    try:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError("operator notebook must be valid UTF-8 JSON") from exc
    if not isinstance(notebook, dict) or notebook.get("nbformat") != 4:
        raise ArtifactValidationError("operator notebook must use nbformat 4")
    cells = notebook.get("cells")
    if not isinstance(cells, list) or len(cells) < 5:
        raise ArtifactValidationError("operator notebook is missing required interface cells")
    code_cells = [cell for cell in cells if isinstance(cell, dict) and cell.get("cell_type") == "code"]
    if len(code_cells) < 3:
        raise ArtifactValidationError("operator notebook has too few code cells")
    for cell in code_cells:
        if cell.get("execution_count") is not None or cell.get("outputs") != []:
            raise ArtifactValidationError("tracked operator notebook must be unexecuted")
        if not isinstance(cell.get("source"), list) or not all(
            isinstance(line, str) for line in cell["source"]
        ):
            raise ArtifactValidationError("operator notebook cell source is invalid")
    isolation = "".join(code_cells[0]["source"])
    torch_offset = isolation.find("import torch")
    cuda_offset = isolation.find("CUDA_VISIBLE_DEVICES")
    if cuda_offset < 0 or torch_offset < 0 or cuda_offset > torch_offset:
        raise ArtifactValidationError("operator notebook does not isolate GPU before PyTorch import")
    if "torch.cuda.device_count() != 1" not in isolation or "H100" not in isolation:
        raise ArtifactValidationError("operator notebook does not enforce one H100")
    final = "".join(code_cells[-1]["source"])
    if (
        "scripts' / 'run_submission.py" not in final
        or "'verify'" not in final
        or "verification.returncode != 0" not in final
        or "SUBMISSION PIPELINE: FAIL" not in final
    ):
        raise ArtifactValidationError("operator notebook final cell is not fail-loud")


@dataclass(frozen=True)
class VerificationReport:
    status: str
    ready_for_claim_bearing_execution: bool
    submission_complete: bool
    checks: tuple[dict[str, Any], ...]
    execution_blockers: tuple[str, ...]
    completion_blockers: tuple[str, ...]
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "blockers": list(self.blockers),
            "checks": list(self.checks),
            "completion_blockers": list(self.completion_blockers),
            "execution_blockers": list(self.execution_blockers),
            "ready_for_claim_bearing_execution": self.ready_for_claim_bearing_execution,
            "status": self.status,
            "submission_complete": self.submission_complete,
        }


def verify_submission_readiness(repository_root: str | Path) -> VerificationReport:
    """Inventory mandatory interfaces without writing or executing a job."""

    root = Path(repository_root).resolve(strict=True)
    checks: list[dict[str, Any]] = []
    execution_blockers: list[str] = []
    completion_blockers: list[str] = []

    required_files = (
        "requirements.lock",
        "scripts/run_submission.py",
        "src/gbdn/artifacts.py",
        "src/gbdn/heterophily_contract.py",
        "src/gbdn/heterophily_statistics.py",
    )
    for relative in required_files:
        path = root / relative
        passed = path.is_file() and not path.is_symlink()
        checks.append({"check": f"required_file:{relative}", "status": "PASS" if passed else "FAIL"})
        if not passed:
            execution_blockers.append(f"missing required regular file: {relative}")

    try:
        validate_gate_a_acceptance(root)
    except ArtifactValidationError as exc:
        checks.append({"check": "independent_gate_a_acceptance", "status": "FAIL"})
        execution_blockers.append(str(exc))
    else:
        checks.append({"check": "independent_gate_a_acceptance", "status": "PASS"})

    execution_inputs = (
        "configs/submission/frozen/confirmatory_plan.json",
        "results_submission/baseline_registry.json",
        "results_submission/run_plan.json",
    )
    notebook_relative = "notebooks/gbdn_submission_h100.ipynb"
    try:
        validate_operator_notebook(root / notebook_relative)
    except ArtifactValidationError as exc:
        checks.append({"check": f"execution_input:{notebook_relative}", "status": "FAIL"})
        execution_blockers.append(str(exc))
    else:
        checks.append({"check": f"execution_input:{notebook_relative}", "status": "PASS"})
    for relative in execution_inputs:
        path = root / relative
        passed = path.is_file() and not path.is_symlink()
        checks.append({"check": f"execution_input:{relative}", "status": "PASS" if passed else "FAIL"})
        if not passed:
            execution_blockers.append(f"missing execution input: {relative}")
    # File presence is not semantic validation. Keep authorization false until
    # the frozen plan, baseline registry, scheduler, and test-isolated
    # evaluator schemas are implemented and independently reviewed.
    execution_blockers.append(
        "claim-bearing scheduler and execution-input semantic validators are not implemented"
    )

    completion_outputs = (
        "results_submission/aggregate/split_level_metrics.csv",
        "results_submission/aggregate/paired_tests.csv",
        "results_submission/reports/verification_report.md",
    )
    for relative in completion_outputs:
        path = root / relative
        passed = path.is_file() and not path.is_symlink()
        checks.append({"check": f"completion_output:{relative}", "status": "PASS" if passed else "FAIL"})
        if not passed:
            completion_blockers.append(f"missing completion output: {relative}")

    ready = not execution_blockers
    complete = ready and not completion_blockers
    blockers = tuple((*execution_blockers, *completion_blockers))
    return VerificationReport(
        "PASS" if complete else "BLOCKED",
        ready,
        complete,
        tuple(checks),
        tuple(execution_blockers),
        tuple(completion_blockers),
        blockers,
    )


__all__ = ["VerificationReport", "validate_operator_notebook", "verify_submission_readiness"]
