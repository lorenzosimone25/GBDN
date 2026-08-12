#!/usr/bin/env python3
"""H100 multi-split heterophily and extended Peptides reproduction CLI."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legacy_reproduction import (  # noqa: E402
    DEFAULT_SEED,
    DEFAULT_SPLITS,
    EXTENDED_LRGB_MODELS,
    HETERO_DATASETS,
    HETERO_MODELS,
    PEPTIDE_DATASETS,
    aggregate_heterophily,
    aggregate_peptides,
    environment_manifest,
    expected_counts,
    generate_extended_report,
    prepare_extended_datasets,
    run_heterophily_split,
    run_peptide,
    verify_extended_results,
    verify_h100,
    verify_reproduction,
)


def _outputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--data-root", type=Path, default=ROOT / "data" / "legacy")
    parser.add_argument("--output-root", type=Path, default=ROOT / "results_multisplit")
    parser.add_argument("--lrgb-output-root", type=Path, default=ROOT / "results_LRGB_extended")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--rerun", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="run one independently resumable raw job")
    _outputs(run)
    run.add_argument("--dataset", required=True, choices=(*HETERO_DATASETS, *PEPTIDE_DATASETS))
    run.add_argument("--model", required=True)
    run.add_argument("--split", type=int)
    run.add_argument("--epochs", type=int)
    run.add_argument("--max-train-batches", type=int)

    run_model = commands.add_parser("run-model", help="run one heterophily model over datasets and splits")
    _outputs(run_model)
    run_model.add_argument("--model", required=True, choices=HETERO_MODELS)
    run_model.add_argument("--datasets", nargs="+", choices=HETERO_DATASETS, default=list(HETERO_DATASETS))
    run_model.add_argument("--splits", type=int, nargs="+", default=list(DEFAULT_SPLITS))
    run_model.add_argument("--epochs", type=int, default=1000)

    run_all = commands.add_parser("run-all", help="run all 190 raw jobs with failure isolation")
    _outputs(run_all)
    run_all.add_argument("--splits", type=int, nargs="+", default=list(DEFAULT_SPLITS))
    run_all.add_argument("--workers", default="auto")
    run_all.add_argument("--heterophily-epochs", type=int, default=1000)
    run_all.add_argument("--peptides-epochs", type=int, default=100)
    run_all.add_argument("--heterophily-datasets", nargs="+", choices=HETERO_DATASETS, default=list(HETERO_DATASETS))
    run_all.add_argument("--heterophily-models", nargs="+", choices=HETERO_MODELS, default=list(HETERO_MODELS))
    run_all.add_argument("--peptides-datasets", nargs="+", choices=PEPTIDE_DATASETS, default=list(PEPTIDE_DATASETS))
    run_all.add_argument("--peptides-models", nargs="+", choices=EXTENDED_LRGB_MODELS, default=list(EXTENDED_LRGB_MODELS))

    smoke = commands.add_parser("smoke", help="run short heterophily and Peptides GPU checks")
    _outputs(smoke)
    smoke.add_argument("--heterophily-dataset", choices=HETERO_DATASETS, default="Minesweeper")
    smoke.add_argument("--heterophily-model", choices=HETERO_MODELS, default="MLP")
    smoke.add_argument("--peptides-dataset", choices=PEPTIDE_DATASETS, default="Peptides-func")
    smoke.add_argument("--peptides-model", choices=EXTENDED_LRGB_MODELS, default="GCN")

    report = commands.add_parser("report", help="verify and generate aggregate Markdown")
    report.add_argument("--output-root", type=Path, default=ROOT / "results_multisplit")
    report.add_argument("--lrgb-output-root", type=Path, default=ROOT / "results_LRGB_extended")
    report.add_argument("--output", type=Path, default=ROOT / "h100_multisplit_report.md")

    verify = commands.add_parser("verify", help="fail loudly on incomplete or inconsistent artifacts")
    verify.add_argument("--output-root", type=Path, default=ROOT / "results_multisplit")
    verify.add_argument("--lrgb-output-root", type=Path, default=ROOT / "results_LRGB_extended")
    verify.add_argument("--splits", type=int, nargs="+", default=list(DEFAULT_SPLITS))
    verify.add_argument("--seed", type=int, default=DEFAULT_SEED)
    # Deprecated comparison inputs retained only so old local automation fails
    # gracefully; the documented interface uses the two extended output roots.
    verify.add_argument("--original-root", type=Path, default=None, help=argparse.SUPPRESS)
    verify.add_argument("--reproduced-root", type=Path, default=None, help=argparse.SUPPRESS)
    verify.add_argument("--original-lrgb-root", type=Path, default=None, help=argparse.SUPPRESS)
    verify.add_argument("--reproduced-lrgb-root", type=Path, default=None, help=argparse.SUPPRESS)
    return parser


# Backward-compatible name used by older local tests/notebook helpers.
parser = build_parser


def _validate_splits(values: list[int]) -> tuple[int, ...]:
    splits = tuple(values)
    if not splits or len(set(splits)) != len(splits) or any(value not in range(10) for value in splits):
        raise ValueError("splits must be unique official columns in [0, 9]")
    return splits


def _resolve_workers(value: str, job_count: int = 22) -> int:
    if value != "auto":
        workers = int(value)
        if workers < 1 or workers > job_count:
            raise ValueError(f"workers must be in [1, {job_count}]")
        return workers
    import torch

    memory = torch.cuda.get_device_properties(0).total_memory
    gpu_slots = max(1, memory // (8 * 2**30))
    cpu_slots = max(1, (os.cpu_count() or 2) // 2)
    return int(min(job_count, gpu_slots, cpu_slots))


def _run_logged(command: list[str], log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        return subprocess.run(command, cwd=ROOT, env=os.environ.copy(), stdout=log, stderr=subprocess.STDOUT, check=False).returncode


def _base_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--sentinel",  # removed before launch; keeps construction tests explicit
    ]
    command.pop()
    return command


def _hetero_pipeline_command(args: argparse.Namespace, model: str) -> list[str]:
    command = _base_command(args) + [
        "run-model", "--model", model, "--data-root", str(args.data_root),
        "--output-root", str(args.output_root), "--lrgb-output-root", str(args.lrgb_output_root),
        "--seed", str(args.seed), "--epochs", str(args.heterophily_epochs),
        "--splits", *map(str, args.splits), "--datasets", *args.heterophily_datasets,
    ]
    if args.rerun:
        command.append("--rerun")
    return command


def _peptide_command(args: argparse.Namespace, dataset: str, model: str) -> list[str]:
    command = _base_command(args) + [
        "run", "--dataset", dataset, "--model", model, "--data-root", str(args.data_root),
        "--output-root", str(args.output_root), "--lrgb-output-root", str(args.lrgb_output_root),
        "--seed", str(args.seed), "--epochs", str(args.peptides_epochs),
    ]
    if args.rerun:
        command.append("--rerun")
    return command


def _atomic_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _run_all(args: argparse.Namespace) -> int:
    args.splits = list(_validate_splits(getattr(args, "splits", list(DEFAULT_SPLITS))))
    args.seed = getattr(args, "seed", DEFAULT_SEED)
    args.heterophily_epochs = getattr(args, "heterophily_epochs", 1000)
    args.peptides_epochs = getattr(args, "peptides_epochs", 100)
    args.heterophily_datasets = getattr(args, "heterophily_datasets", list(HETERO_DATASETS))
    args.heterophily_models = getattr(args, "heterophily_models", list(HETERO_MODELS))
    args.peptides_datasets = getattr(args, "peptides_datasets", list(PEPTIDE_DATASETS))
    args.peptides_models = getattr(args, "peptides_models", list(EXTENDED_LRGB_MODELS))
    gpu = verify_h100()
    jobs = [(f"heterophily/{model}", _hetero_pipeline_command(args, model)) for model in args.heterophily_models]
    jobs += [
        (f"{dataset}/{model}", _peptide_command(args, dataset, model))
        for dataset in args.peptides_datasets for model in args.peptides_models
    ]
    workers = _resolve_workers(args.workers)
    started = dt.datetime.now(dt.timezone.utc)
    log_root = ROOT / "reproduction_logs" / started.strftime("%Y%m%dT%H%M%SZ")
    statuses: dict[str, int] = {}
    print("Preparing shared dataset caches sequentially before parallel workers")
    prepare_extended_datasets(args.data_root, args.heterophily_datasets, args.peptides_datasets)
    requested_raw = len(args.heterophily_datasets) * len(args.heterophily_models) * len(args.splits) + len(args.peptides_datasets) * len(args.peptides_models)
    print(f"Launching {requested_raw} raw runs as {len(jobs)} isolated pipelines with {workers} workers")
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_run_logged, command, log_root / f"{name.replace('/', '__')}.log"): name for name, command in jobs}
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                statuses[name] = future.result()
            except Exception as error:
                statuses[name] = 1
                (log_root / f"{name.replace('/', '__')}.supervisor-error.log").write_text(f"{type(error).__name__}: {error}\n")
            print(f"{name}: {'complete' if statuses[name] == 0 else 'failed'}")
    if all(code == 0 for code in statuses.values()):
        aggregate_heterophily(args.output_root, args.splits, args.seed, datasets=args.heterophily_datasets, models=args.heterophily_models, rerun=args.rerun)
        aggregate_peptides(args.lrgb_output_root, args.seed, datasets=args.peptides_datasets, models=args.peptides_models, rerun=args.rerun)
    counts = {
        "heterophily_raw": len(args.heterophily_datasets) * len(args.heterophily_models) * len(args.splits),
        "peptides_raw": len(args.peptides_datasets) * len(args.peptides_models),
        "heterophily_summaries": len(args.heterophily_datasets) * len(args.heterophily_models),
        "peptides_summaries": len(args.peptides_datasets) * len(args.peptides_models),
    }
    manifest_statuses = dict(statuses)
    for model in args.heterophily_models:
        key = f"heterophily/{model}"
        if key in statuses:
            manifest_statuses.setdefault(model, statuses[key])
    _atomic_manifest(args.output_root / "run_manifest.json", {
        "schema_version": "gbdn-extended-run-manifest-v1",
        "started_utc": started.isoformat(),
        "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "complete" if all(code == 0 for code in statuses.values()) else "failed",
        "expected": counts,
        "expected_total_raw": counts["heterophily_raw"] + counts["peptides_raw"],
        "expected_total_summaries": counts["heterophily_summaries"] + counts["peptides_summaries"],
        "splits": args.splits, "seed": args.seed, "workers": workers,
        "worker_status": manifest_statuses, "environment": environment_manifest(gpu),
    })
    print(f"Logs: {log_root}")
    return 0 if all(code == 0 for code in statuses.values()) else 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "verify":
        if args.original_root is not None:
            problems = verify_reproduction(
                args.original_root, args.reproduced_root, args.original_lrgb_root, args.reproduced_lrgb_root
            )
            if problems:
                for problem in problems:
                    print(f"- {problem}")
                return 1
            return 0
        problems = verify_extended_results(args.output_root, args.lrgb_output_root, _validate_splits(args.splits), args.seed)
        if problems:
            print(f"Verification failed with {len(problems)} problem(s):")
            for problem in problems:
                print(f"- {problem}")
            return 1
        print("Verification passed: 190 raw runs and 70 aggregate summaries are valid.")
        return 0
    if args.command == "report":
        print(generate_extended_report(args.output_root, args.lrgb_output_root, args.output))
        return 0
    if args.command == "run-all":
        return _run_all(args)
    verify_h100()
    if args.command == "run-model":
        splits = _validate_splits(args.splits)
        paths = [run_heterophily_split(dataset, args.model, args.output_root, args.data_root, split=split, seed=args.seed, epochs=args.epochs, rerun=args.rerun) for dataset in args.datasets for split in splits]
        print(f"completed/resumed {len(paths)} raw runs")
        return 0
    if args.command == "smoke":
        smoke_hetero = ROOT / "reproduction_state" / "h100_smoke" / "heterophily"
        smoke_peptide = ROOT / "reproduction_state" / "h100_smoke" / "peptides"
        print(run_heterophily_split(args.heterophily_dataset, args.heterophily_model, smoke_hetero, args.data_root, split=0, seed=args.seed, epochs=2, rerun=args.rerun))
        print(run_peptide(args.peptides_dataset, args.peptides_model, smoke_peptide, args.data_root, seed=args.seed, epochs=1, batch_size=8, max_train_batches=2, rerun=args.rerun))
        return 0
    if args.dataset in HETERO_DATASETS:
        if args.model not in HETERO_MODELS or args.split is None:
            raise SystemExit("heterophily run requires a valid --model and --split")
        path = run_heterophily_split(args.dataset, args.model, args.output_root, args.data_root, split=args.split, seed=args.seed, epochs=args.epochs or 1000, rerun=args.rerun)
    else:
        if args.model not in EXTENDED_LRGB_MODELS or args.split is not None:
            raise SystemExit("Peptides run requires an extended model and no --split")
        path = run_peptide(args.dataset, args.model, args.lrgb_output_root, args.data_root, seed=args.seed, epochs=args.epochs or 100, max_train_batches=args.max_train_batches, rerun=args.rerun)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
