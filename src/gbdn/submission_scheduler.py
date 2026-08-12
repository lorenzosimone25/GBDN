"""Sequential, fail-closed scheduler around validated confirmatory plans."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from gbdn.artifacts import (
    NA_ID,
    ArtifactValidationError,
    FailureRecord,
    ResumeState,
    classify_resume,
    utc_now_iso,
    write_failure_record,
)
from gbdn.gate_acceptance import validate_gate_a_acceptance
from gbdn.run_plan import validate_run_plan


@dataclass(frozen=True)
class SchedulerSummary:
    total: int
    completed: int
    skipped: int
    failed: int
    blocked: int

    @property
    def success(self) -> bool:
        return self.failed == 0 and self.blocked == 0 and self.completed + self.skipped == self.total

    def to_dict(self) -> dict[str, int | bool]:
        return {
            "blocked": self.blocked,
            "completed": self.completed,
            "failed": self.failed,
            "skipped": self.skipped,
            "success": self.success,
            "total": self.total,
        }


def run_confirmatory_scheduler(
    *,
    repository_root: str | Path,
    run_plan_path: str | Path,
    confirmatory_plan_path: str | Path,
    baseline_registry_path: str | Path,
    worker_path: str | Path,
    continue_on_error: bool = True,
    retry_recorded_failures: bool = False,
    timeout_seconds: float = 24 * 60 * 60,
) -> SchedulerSummary:
    """Run validated jobs sequentially; never delete, overwrite, or self-accept."""

    if type(continue_on_error) is not bool or type(retry_recorded_failures) is not bool:
        raise ArtifactValidationError("scheduler flags must be booleans")
    if not isinstance(timeout_seconds, (int, float)) or not 0 < float(timeout_seconds) <= 7 * 24 * 60 * 60:
        raise ArtifactValidationError("scheduler timeout must be positive and at most seven days")
    root = Path(repository_root).resolve(strict=True)
    validate_gate_a_acceptance(root)
    plan = validate_run_plan(
        run_plan_path,
        confirmatory_plan_path=confirmatory_plan_path,
        baseline_registry_path=baseline_registry_path,
        repository_root=root,
    )
    requested_worker = Path(worker_path)
    if requested_worker.is_symlink() or not requested_worker.is_file():
        raise ArtifactValidationError("scheduler worker must be the canonical repository script")
    worker = requested_worker.resolve(strict=True)
    expected_path = root / "scripts" / "run_heterophily_job.py"
    if expected_path.is_symlink() or not expected_path.is_file():
        raise ArtifactValidationError("canonical repository worker is absent or unsafe")
    expected_worker = expected_path.resolve(strict=True)
    if worker != expected_worker:
        raise ArtifactValidationError("scheduler worker must be the canonical repository script")

    completed = skipped = failed = blocked = 0
    for index, job in enumerate(plan.jobs):
        decision = classify_resume(job.identity, repository_root=root)
        if decision is not None and decision.state is ResumeState.MATCHING_COMPLETE:
            skipped += 1
            continue
        if decision is not None and not (
            retry_recorded_failures
            and decision.state is ResumeState.PARTIAL
            and decision.recoverable
        ):
            blocked += 1
            if not continue_on_error:
                break
            continue

        child_environment = os.environ.copy()
        child_environment["CUDA_VISIBLE_DEVICES"] = str(job.environment.cuda_visible_devices)
        child_environment["CUBLAS_WORKSPACE_CONFIG"] = str(job.environment.cublas_workspace_config)
        child_environment["PYTHONHASHSEED"] = str(job.environment.pythonhashseed)
        command = [
            sys.executable,
            str(worker),
            "--repository-root",
            str(root),
            "--run-plan",
            str(Path(run_plan_path).resolve(strict=True)),
            "--job-index",
            str(index),
            "--run-id",
            job.identity.run_id,
        ]
        exception_type = "SubprocessFailure"
        message = ""
        try:
            process = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=float(timeout_seconds),
                env=child_environment,
            )
            if process.returncode != 0:
                stderr = process.stderr.strip()
                message = f"worker exit={process.returncode}: {stderr[-8192:]}"
            else:
                postcondition = classify_resume(job.identity, repository_root=root)
                if postcondition is not None and postcondition.state is ResumeState.MATCHING_COMPLETE:
                    completed += 1
                    continue
                exception_type = "WorkerContractError"
                observed = "missing" if postcondition is None else postcondition.state.value
                message = f"worker exited zero without a matching complete bundle: {observed}"
        except subprocess.TimeoutExpired:
            exception_type = "WorkerTimeout"
            message = f"worker exceeded timeout_seconds={float(timeout_seconds)}"
        failure = FailureRecord(
            identity=job.identity,
            exception_type=exception_type,
            message=message,
            traceback_path=NA_ID,
            partial_artifacts=(),
            source=job.source,
            environment=job.environment,
            created_at_utc=utc_now_iso(),
        )
        try:
            write_failure_record(failure, repository_root=root)
        except FileExistsError:
            # Identical failure content is already preserved; never overwrite it.
            pass
        failed += 1
        if not continue_on_error:
            break
    return SchedulerSummary(len(plan.jobs), completed, skipped, failed, blocked)


__all__ = ["SchedulerSummary", "run_confirmatory_scheduler"]
