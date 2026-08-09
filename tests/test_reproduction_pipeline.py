from __future__ import annotations

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import legacy_reproduction as legacy  # noqa: E402

SPEC = importlib.util.spec_from_file_location(
    "reproduce_legacy_cli", ROOT / "scripts" / "reproduce_legacy.py"
)
assert SPEC and SPEC.loader
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


def _provenance(identity: str = "test") -> dict:
    return {
        "identity": identity,
        "source": "test",
        "source_sha256": "0" * 64,
        "config": {},
        "environment": {},
        "duration_seconds": 1.0,
        "peak_cuda_memory_bytes": 1,
    }


def test_atomic_json_is_immutable_without_explicit_rerun(tmp_path):
    path = tmp_path / "result.json"
    first = {"value": 1, "reproduction": {"identity": "one"}}
    legacy._write_json(path, first)
    legacy._write_json(path, first)
    assert json.loads(path.read_text(encoding="utf-8")) == first
    assert not path.with_suffix(".json.tmp").exists()

    second = {"value": 2, "reproduction": {"identity": "two"}}
    with pytest.raises(FileExistsError):
        legacy._write_json(path, second)
    legacy._write_json(path, second, rerun=True)
    assert json.loads(path.read_text(encoding="utf-8")) == second


def test_run_model_preserves_order_and_resumes_from_rng_checkpoints(tmp_path, monkeypatch):
    output_root = tmp_path / "results_repro"
    state_root = tmp_path / "state"
    observed: list[str] = []
    manifest = {"test": True}

    monkeypatch.setattr(legacy, "verify_h100", lambda: {"name": "H100"})
    monkeypatch.setattr(legacy, "environment_manifest", lambda gpu=None: manifest)

    def fake_run(dataset, model, output, data, rerun=False, epochs=None, reseed=True):
        observed.append(dataset)
        torch.rand(1)
        config = legacy._hetero_run_config(dataset, model, epochs)
        identity = legacy._identity(config, manifest)
        path = output / dataset / f"{model}.json"
        legacy._write_json(path, {"reproduction": {"identity": identity}}, rerun)
        return path

    monkeypatch.setattr(legacy, "run_heterophily", fake_run)
    first = legacy.run_model(
        "MLP", output_root, tmp_path / "data", state_root, epochs=2
    )
    assert observed == list(legacy.HETERO_DATASETS)
    assert len(first) == 5

    observed.clear()
    second = legacy.run_model(
        "MLP", output_root, tmp_path / "data", state_root, epochs=2
    )
    assert observed == []
    assert second == first


def test_verifier_reports_metric_drift_and_cli_exits_nonzero(tmp_path, monkeypatch):
    monkeypatch.setattr(legacy, "HETERO_DATASETS", ("Dataset",))
    monkeypatch.setattr(legacy, "HETERO_MODELS", ("Model",))
    monkeypatch.setattr(legacy, "LRGB_MODELS", ("GraphModel",))

    original = tmp_path / "original" / "Dataset"
    reproduced = tmp_path / "reproduced" / "Dataset"
    original_lrgb = tmp_path / "original_lrgb"
    reproduced_lrgb = tmp_path / "reproduced_lrgb"
    for directory in (original, reproduced, original_lrgb, reproduced_lrgb):
        directory.mkdir(parents=True)

    predictions = [[0.9, 0.1], [0.1, 0.9]]
    reference = {
        "dataset": "Dataset",
        "model": "Model",
        "test_probs": predictions,
        "test_labels": [0, 1],
        "test_acc": 1.0,
        "test_auroc": 0.5,
    }
    rerun = {
        **reference,
        "test_auroc": 1.0,
        "reproduction": _provenance(),
    }
    (original / "Model.json").write_text(json.dumps(reference), encoding="utf-8")
    (reproduced / "Model.json").write_text(json.dumps(rerun), encoding="utf-8")

    lrgb_reference = {
        "dataset": "Peptides-func",
        "model": "GraphModel",
        "best_val_ap": 0.5,
        "test_ap": 0.5,
    }
    lrgb_rerun = {**lrgb_reference, "reproduction": _provenance()}
    (original_lrgb / "GraphModel.json").write_text(
        json.dumps(lrgb_reference), encoding="utf-8"
    )
    (reproduced_lrgb / "GraphModel.json").write_text(
        json.dumps(lrgb_rerun), encoding="utf-8"
    )
    (tmp_path / "reproduced" / "run_manifest.json").write_text("{}", encoding="utf-8")

    problems = legacy.verify_reproduction(
        tmp_path / "original",
        tmp_path / "reproduced",
        original_lrgb,
        reproduced_lrgb,
    )
    assert any("metric drift" in problem for problem in problems)

    monkeypatch.setattr(cli, "verify_reproduction", lambda *args: problems)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "reproduce_legacy.py",
            "verify",
            "--original-root",
            str(tmp_path / "original"),
            "--reproduced-root",
            str(tmp_path / "reproduced"),
            "--original-lrgb-root",
            str(original_lrgb),
            "--reproduced-lrgb-root",
            str(reproduced_lrgb),
        ],
    )
    assert cli.main() == 1


def test_parallel_supervisor_does_not_cancel_other_models(tmp_path, monkeypatch):
    output_root = tmp_path / "results_repro"
    lrgb_output_root = tmp_path / "results_LRGB_repro"
    output_root.mkdir()
    lrgb_output_root.mkdir()
    calls: list[str] = []

    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "verify_h100", lambda: {"name": "H100"})
    monkeypatch.setattr(cli, "environment_manifest", lambda gpu=None: {"gpu": gpu})
    monkeypatch.setattr(cli, "_resolve_workers", lambda value: 3)

    def fake_logged(command, log_path):
        model = command[command.index("--model") + 1]
        calls.append(model)
        return 1 if model == "GAT" else 0

    monkeypatch.setattr(cli, "_run_logged", fake_logged)
    args = Namespace(
        workers="auto",
        data_root=tmp_path / "data",
        output_root=output_root,
        lrgb_output_root=lrgb_output_root,
        state_root=tmp_path / "state",
        rerun=False,
    )
    assert cli._run_all(args) == 1
    assert set(legacy.HETERO_MODELS).issubset(calls)
    assert "GBDN+" in calls  # the separate Peptides-func subprocess also ran
    manifest = json.loads((output_root / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert manifest["worker_status"]["GAT"] == 1
