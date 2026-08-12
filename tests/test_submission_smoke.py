from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gbdn.artifacts import (  # noqa: E402
    ArtifactValidationError,
    DirtySourceError,
    ResumeState,
    RunResultRecord,
)
from gbdn.submission import (  # noqa: E402
    build_smoke_plan,
    classify_smoke_resume,
    recompute_smoke_accuracy,
    require_canonical_output_root,
    run_smoke_subprocess,
)


PYTHON = Path(sys.executable)
SCRIPT = ROOT / "scripts" / "run_submission.py"
FROZEN_CONFIG = ROOT / "configs" / "submission" / "cpu_smoke.json"


def _git(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )


def _repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    (repository / "configs" / "submission").mkdir(parents=True)
    (repository / "scripts").mkdir(parents=True)
    shutil.copyfile(FROZEN_CONFIG, repository / "configs" / "submission" / "cpu_smoke.json")
    shutil.copyfile(SCRIPT, repository / "scripts" / "run_submission.py")
    (repository / "requirements.lock").write_text("numpy==2.3.5\n", encoding="utf-8")
    (repository / ".gitignore").write_text("/results_submission/\n", encoding="utf-8")
    _git(repository, "init")
    _git(repository, "config", "user.email", "test@example.com")
    _git(repository, "config", "user.name", "Test User")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "frozen smoke fixture")
    return repository


def _plan(repository: Path):
    with patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "-1"}):
        return build_smoke_plan(
            repository_root=repository,
            config_path=repository / "configs" / "submission" / "cpu_smoke.json",
        )


def _script(repository: Path) -> Path:
    return repository / "scripts" / "run_submission.py"


def test_preflight_is_read_only_and_inventory_is_one_diagnostic_cpu_job(tmp_path):
    repository = _repository(tmp_path)
    plan = _plan(repository)

    assert plan.inventory() == {
        "claim_status": "diagnostic-only",
        "device": "cpu",
        "job_count": 1,
        "repository_root": str(repository.resolve()),
        "run_id": plan.identity.run_id,
        "run_mode": "smoke",
        "state": "pending",
    }
    assert not (repository / "results_submission").exists()
    assert not plan.config.source.dirty


def test_smoke_runs_in_isolated_process_commits_and_resumes(tmp_path):
    repository = _repository(tmp_path)
    plan = _plan(repository)

    first = run_smoke_subprocess(plan, entry_point=_script(repository))
    assert first.state == "completed"
    assert first.worker_pid != 0
    assert first.worker_pid != __import__("os").getpid()
    assert first.metric == pytest.approx(4.0 / 6.0, abs=1e-12)
    assert first.bundle_path.is_relative_to(repository / "results_submission" / "raw")
    assert {path.name for path in first.bundle_path.iterdir()} == {
        "bundle.json",
        "config.json",
        "predictions.npz",
        "result.json",
    }

    result = RunResultRecord.from_dict(
        json.loads((first.bundle_path / "result.json").read_text(encoding="utf-8"))
    )
    assert json.loads(result.result_payload_json)["claim_status"] == "diagnostic-only"
    assert result.environment.cuda_visible_devices == "-1"
    recomputed = recompute_smoke_accuracy(
        first.bundle_path / "predictions.npz",
        expected_run_id=plan.identity.run_id,
    )
    assert recomputed == first.metric

    rebuilt = _plan(repository)
    assert rebuilt.identity.run_id == plan.identity.run_id
    decision = classify_smoke_resume(rebuilt)
    assert decision is not None and decision.state is ResumeState.MATCHING_COMPLETE
    second = run_smoke_subprocess(rebuilt, entry_point=_script(repository))
    assert second.state == "skipped"
    assert second.bundle_path == first.bundle_path
    assert second.worker_pid == first.worker_pid


def test_tampered_predictions_are_never_resumed_as_complete(tmp_path):
    repository = _repository(tmp_path)
    plan = _plan(repository)
    execution = run_smoke_subprocess(plan, entry_point=_script(repository))
    prediction = execution.bundle_path / "predictions.npz"
    prediction.write_bytes(prediction.read_bytes() + b"tamper")

    decision = classify_smoke_resume(plan)
    assert decision is not None and decision.state is ResumeState.CORRUPT
    with pytest.raises(ArtifactValidationError, match="unsafe resume state corrupt"):
        run_smoke_subprocess(plan, entry_point=_script(repository))


def test_independent_metric_rejects_wrong_identity_and_schema(tmp_path):
    prediction = tmp_path / "predictions.npz"
    np.savez_compressed(
        prediction,
        indices=np.arange(2, dtype=np.int64),
        labels=np.asarray([0, 1], dtype=np.int64),
        logits=np.asarray([-1.0, 1.0], dtype=np.float64),
        run_id=np.asarray("a" * 64),
        split_id=np.asarray(0, dtype=np.int64),
    )
    with pytest.raises(ArtifactValidationError, match="another run"):
        recompute_smoke_accuracy(prediction, expected_run_id="b" * 64)

    np.savez_compressed(
        prediction,
        labels=np.asarray([0, 1], dtype=np.int64),
        logits=np.asarray([-1.0, 1.0], dtype=np.float64),
        run_id=np.asarray("a" * 64),
        split_id=np.asarray(0, dtype=np.int64),
    )
    with pytest.raises(ArtifactValidationError, match="archive|arrays"):
        recompute_smoke_accuracy(prediction, expected_run_id="a" * 64)


def test_prediction_archive_size_and_member_limits_fail_closed(tmp_path):
    prediction = tmp_path / "predictions.npz"
    prediction.write_bytes(b"x" * (1024 * 1024 + 1))
    with pytest.raises(ArtifactValidationError, match="size limit"):
        recompute_smoke_accuracy(prediction, expected_run_id="a" * 64)

    with zipfile.ZipFile(prediction, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for index in range(5):
            archive.writestr(f"member-{index}.npy", b"x" * (64 * 1024 + 1))
    with pytest.raises(ArtifactValidationError, match="member"):
        recompute_smoke_accuracy(prediction, expected_run_id="a" * 64)


def test_claim_bearing_mode_fails_on_dirty_source_and_missing_acceptance(tmp_path):
    repository = _repository(tmp_path)
    config = repository / "configs" / "submission" / "cpu_smoke.json"

    with pytest.raises(ArtifactValidationError, match="acceptance token is absent"):
        build_smoke_plan(repository_root=repository, config_path=config, run_mode="full")

    (repository / "dirty.txt").write_text("uncommitted\n", encoding="utf-8")
    with pytest.raises(DirtySourceError, match="clean Git tree"):
        build_smoke_plan(repository_root=repository, config_path=config, run_mode="full")


def test_smoke_plan_requires_cpu_isolation_before_metadata_capture(tmp_path):
    repository = _repository(tmp_path)
    config = repository / "configs" / "submission" / "cpu_smoke.json"
    with patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "0"}):
        with pytest.raises(ArtifactValidationError, match="CUDA_VISIBLE_DEVICES=-1"):
            build_smoke_plan(repository_root=repository, config_path=config)


def test_frozen_plan_and_output_boundary_fail_closed(tmp_path):
    repository = _repository(tmp_path)
    config = repository / "configs" / "submission" / "cpu_smoke.json"
    changed = json.loads(config.read_text(encoding="utf-8"))
    changed["device"] = "cuda"
    config.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="device='cpu'"):
        _plan(repository)

    assert require_canonical_output_root(repository, "results_submission") == (
        repository / "results_submission"
    ).resolve()
    with pytest.raises(ArtifactValidationError, match="output_root"):
        require_canonical_output_root(repository, "results")
    with pytest.raises(ArtifactValidationError, match="output_root"):
        require_canonical_output_root(repository, tmp_path / "outside")

    outside = tmp_path / "escaped"
    outside.mkdir()
    link = repository / "results_submission"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation is unavailable")
    with pytest.raises(ArtifactValidationError, match="outside"):
        require_canonical_output_root(repository, "results_submission")


def test_worker_entry_and_completed_environment_are_bound_to_parent_plan(tmp_path):
    repository = _repository(tmp_path)
    plan = _plan(repository)
    with pytest.raises(ArtifactValidationError, match="canonical repository script"):
        run_smoke_subprocess(plan, entry_point=SCRIPT)

    execution = run_smoke_subprocess(plan, entry_point=_script(repository))
    changed_environment = replace(
        plan.config.environment,
        cuda_visible_devices="0",
    )
    changed_plan = replace(
        plan,
        config=replace(plan.config, environment=changed_environment),
    )
    decision = classify_smoke_resume(changed_plan)
    assert decision is not None and decision.state is ResumeState.CORRUPT
    assert "environment metadata differs" in decision.reason
    assert execution.bundle_path.exists()


def test_cli_preflight_and_smoke_emit_machine_readable_results(tmp_path):
    repository = _repository(tmp_path)
    common = [
        "--repository-root",
        str(repository),
        "--config",
        str(repository / "configs" / "submission" / "cpu_smoke.json"),
    ]
    preflight = subprocess.run(
        [str(PYTHON), str(_script(repository)), "preflight", *common],
        check=True,
        capture_output=True,
        text=True,
    )
    inventory = json.loads(preflight.stdout)
    assert inventory["state"] == "pending"
    assert inventory["job_count"] == 1

    smoke = subprocess.run(
        [str(PYTHON), str(_script(repository)), "smoke", *common],
        check=True,
        capture_output=True,
        text=True,
    )
    completed = json.loads(smoke.stdout)
    assert completed["state"] == "completed"
    assert completed["metric"] == pytest.approx(4.0 / 6.0)

    resumed = subprocess.run(
        [str(PYTHON), str(_script(repository)), "smoke", *common],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(resumed.stdout)["state"] == "skipped"
