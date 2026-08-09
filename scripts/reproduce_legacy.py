#!/usr/bin/env python3
"""CLI for the notebook-faithful legacy result reproduction."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import os
import platform
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legacy_reproduction import (  # noqa: E402
    HETERO_DATASETS,
    HETERO_MODELS,
    LRGB_MODELS,
    environment_manifest,
    generate_report,
    run_heterophily,
    run_lrgb,
    run_model,
    verify_h100,
    verify_reproduction,
)


def _add_output_arguments(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument("--data-root", type=Path, default=ROOT / "data" / "legacy")
    subparser.add_argument("--output-root", type=Path, default=ROOT / "results_repro")
    subparser.add_argument(
        "--lrgb-output-root", type=Path, default=ROOT / "results_LRGB_repro"
    )
    subparser.add_argument(
        "--state-root", type=Path, default=ROOT / "reproduction_state"
    )
    subparser.add_argument("--rerun", action="store_true")


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    subcommands = command.add_subparsers(dest="command", required=True)

    run = subcommands.add_parser("run", help="run one exact experiment")
    _add_output_arguments(run)
    run.add_argument("--dataset", required=True, choices=(*HETERO_DATASETS, "Peptides-func"))
    run.add_argument("--model", required=True)

    run_one_model = subcommands.add_parser(
        "run-model", help="run one model over all heterophily datasets in legacy order"
    )
    _add_output_arguments(run_one_model)
    run_one_model.add_argument("--model", required=True, choices=HETERO_MODELS)

    all_runs = subcommands.add_parser(
        "run-all", help="run all 62 jobs with isolated model-level concurrency"
    )
    _add_output_arguments(all_runs)
    all_runs.add_argument(
        "--workers",
        default="auto",
        help="parallel model workers (auto or an integer from 1 to 12)",
    )

    smoke = subcommands.add_parser("smoke", help="run a two-epoch GPU integration check")
    _add_output_arguments(smoke)
    smoke.add_argument("--dataset", choices=HETERO_DATASETS, default="Minesweeper")
    smoke.add_argument("--model", choices=HETERO_MODELS, default="MLP")

    report = subcommands.add_parser("report", help="write the comparison report")
    report.add_argument("--original-root", type=Path, default=ROOT / "results")
    report.add_argument("--reproduced-root", type=Path, default=ROOT / "results_repro")
    report.add_argument("--original-lrgb-root", type=Path, default=ROOT / "results_LRGB")
    report.add_argument(
        "--reproduced-lrgb-root", type=Path, default=ROOT / "results_LRGB_repro"
    )
    report.add_argument("--output", type=Path, default=ROOT / "reproduction_report.md")

    verify = subcommands.add_parser("verify", help="enforce complete reproduction acceptance")
    verify.add_argument("--original-root", type=Path, default=ROOT / "results")
    verify.add_argument("--reproduced-root", type=Path, default=ROOT / "results_repro")
    verify.add_argument("--original-lrgb-root", type=Path, default=ROOT / "results_LRGB")
    verify.add_argument(
        "--reproduced-lrgb-root", type=Path, default=ROOT / "results_LRGB_repro"
    )
    verify.add_argument("--drift-tolerance", type=float, default=0.02)
    return command


def _resolve_workers(value: str) -> int:
    if value != "auto":
        workers = int(value)
        if not 1 <= workers <= len(HETERO_MODELS):
            raise ValueError(f"workers must be between 1 and {len(HETERO_MODELS)}")
        return workers

    import torch

    total_memory = torch.cuda.get_device_properties(0).total_memory
    gpu_slots = max(1, total_memory // (6 * 2**30))
    cpu_slots = max(1, (os.cpu_count() or 2) // 2)
    return int(min(len(HETERO_MODELS), gpu_slots, cpu_slots))


def _git_commit() -> str | None:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(path)


def _model_command(args: argparse.Namespace, model: str) -> list[str]:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "run-model",
        "--model",
        model,
        "--data-root",
        str(args.data_root),
        "--output-root",
        str(args.output_root),
        "--lrgb-output-root",
        str(args.lrgb_output_root),
        "--state-root",
        str(args.state_root),
    ]
    if args.rerun:
        command.append("--rerun")
    return command


def _run_logged(command: list[str], log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=os.environ.copy(),
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    return result.returncode


def _run_all(args: argparse.Namespace) -> int:
    gpu = verify_h100()
    workers = _resolve_workers(args.workers)
    started = dt.datetime.now(dt.timezone.utc)
    session = started.strftime("%Y%m%dT%H%M%SZ")
    log_dir = ROOT / "reproduction_logs" / session
    print(f"Launching {len(HETERO_MODELS)} model pipelines with {workers} workers")

    statuses: dict[str, int] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                _run_logged,
                _model_command(args, model),
                log_dir / f"{model}.log",
            ): model
            for model in HETERO_MODELS
        }
        for future in concurrent.futures.as_completed(futures):
            model = futures[future]
            try:
                statuses[model] = future.result()
            except Exception as error:  # supervisor must let other workers finish
                statuses[model] = 1
                (log_dir / f"{model}.supervisor-error.log").write_text(
                    f"{type(error).__name__}: {error}\n", encoding="utf-8"
                )
            print(f"{model}: {'complete' if statuses[model] == 0 else 'failed'}")

    lrgb_command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "run",
        "--dataset",
        "Peptides-func",
        "--model",
        "GBDN+",
        "--data-root",
        str(args.data_root),
        "--output-root",
        str(args.output_root),
        "--lrgb-output-root",
        str(args.lrgb_output_root),
        "--state-root",
        str(args.state_root),
    ]
    if args.rerun:
        lrgb_command.append("--rerun")
    statuses["Peptides-func"] = _run_logged(lrgb_command, log_dir / "Peptides-func.log")
    print(
        "Peptides-func: "
        + ("complete" if statuses["Peptides-func"] == 0 else "failed")
    )

    hetero_count = sum(1 for _ in args.output_root.glob("*/*.json"))
    lrgb_count = sum(1 for _ in args.lrgb_output_root.glob("*.json"))
    manifest = {
        "started_utc": started.isoformat(),
        "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "complete" if all(code == 0 for code in statuses.values()) else "failed",
        "expected_artifacts": 62,
        "observed_artifacts": hetero_count + lrgb_count,
        "workers": workers,
        "worker_status": statuses,
        "environment": environment_manifest(gpu),
        "git_commit": _git_commit(),
        "host": platform.node(),
    }
    _atomic_json(args.output_root / "run_manifest.json", manifest)
    print(f"Observed {hetero_count + lrgb_count}/62 artifacts")
    print(f"Logs: {log_dir}")
    return 0 if all(code == 0 for code in statuses.values()) else 1


def main() -> int:
    args = parser().parse_args()
    if args.command == "report":
        path = generate_report(
            args.original_root,
            args.reproduced_root,
            args.original_lrgb_root,
            args.reproduced_lrgb_root,
            args.output,
        )
        print(path)
        return 0

    if args.command == "verify":
        problems = verify_reproduction(
            args.original_root,
            args.reproduced_root,
            args.original_lrgb_root,
            args.reproduced_lrgb_root,
            args.drift_tolerance,
        )
        if problems:
            print(f"Reproduction verification failed with {len(problems)} problem(s):")
            for problem in problems:
                print(f"- {problem}")
            return 1
        print("Reproduction verification passed: 62/62 artifacts are valid.")
        return 0

    if args.command == "run-all":
        return _run_all(args)

    verify_h100()
    if args.command == "run-model":
        completed = run_model(
            args.model,
            args.output_root,
            args.data_root,
            args.state_root,
            rerun=args.rerun,
        )
        print(f"completed {len(completed)}/5 datasets for {args.model}")
        return 0 if len(completed) == len(HETERO_DATASETS) else 1

    if args.command == "smoke":
        path = run_heterophily(
            args.dataset,
            args.model,
            args.output_root / "_smoke",
            args.data_root,
            rerun=args.rerun,
            epochs=2,
        )
        print(path)
        return 0

    if args.dataset == "Peptides-func":
        if args.model not in LRGB_MODELS:
            raise SystemExit(f"Peptides-func model must be one of: {', '.join(LRGB_MODELS)}")
        path = run_lrgb(
            args.model,
            args.lrgb_output_root,
            args.data_root,
            rerun=args.rerun,
        )
    else:
        if args.model not in HETERO_MODELS:
            raise SystemExit(f"heterophily model must be one of: {', '.join(HETERO_MODELS)}")
        path = run_heterophily(
            args.dataset,
            args.model,
            args.output_root,
            args.data_root,
            rerun=args.rerun,
        )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
