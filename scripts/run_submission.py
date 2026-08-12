#!/usr/bin/env python3
"""Fail-closed submission entry point for diagnostics and confirmatory runs."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


# Device isolation is established in ``main`` before importing gbdn/Torch.
if "torch" in sys.modules:
    raise RuntimeError("PyTorch was imported before device isolation")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "submission" / "cpu_smoke.json",
    )
    parser.add_argument("--output-root", type=Path, default=Path("results_submission"))
    parser.add_argument(
        "--mode",
        choices=("smoke", "full"),
        default="smoke",
        help="full is blocked until an independently reviewed Gate-A token exists",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    preflight = subparsers.add_parser(
        "preflight", help="validate and inventory the frozen CPU plan"
    )
    _add_common(preflight)
    smoke = subparsers.add_parser(
        "smoke", help="run or resume one isolated diagnostic CPU job"
    )
    _add_common(smoke)
    worker = subparsers.add_parser("run-job", help=argparse.SUPPRESS)
    _add_common(worker)
    worker.add_argument("--run-id", required=True)
    verify = subparsers.add_parser(
        "verify", help="read-only fail-loud submission readiness inventory"
    )
    verify.add_argument("--repository-root", type=Path, default=ROOT)
    confirm = subparsers.add_parser(
        "confirm", help="run or resume the independently accepted confirmatory grid"
    )
    confirm.add_argument("--repository-root", type=Path, default=ROOT)
    confirm.add_argument(
        "--run-plan", type=Path, default=Path("results_submission/run_plan.json")
    )
    confirm.add_argument(
        "--confirmatory-plan",
        type=Path,
        default=Path("configs/submission/frozen/confirmatory_plan.json"),
    )
    confirm.add_argument(
        "--baseline-registry",
        type=Path,
        default=Path("results_submission/baseline_registry.json"),
    )
    confirm.add_argument(
        "--worker", type=Path, default=Path("scripts/run_heterophily_job.py")
    )
    confirm.add_argument(
        "--authoritative-dataset-root", type=Path, default=Path("data")
    )
    confirm.add_argument("--stop-on-error", action="store_true")
    confirm.add_argument("--retry-recorded-failures", action="store_true")
    confirm.add_argument("--timeout-seconds", type=float, default=24 * 60 * 60)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.repository_root.resolve(strict=True)
    if args.command == "confirm":
        visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
        if not visible or visible == "-1" or "," in visible:
            raise RuntimeError("confirm requires exactly one pre-isolated CUDA device")
        if os.environ.get("PYTHONHASHSEED") != "0":
            raise RuntimeError("confirm requires PYTHONHASHSEED=0")
        if os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
            raise RuntimeError("confirm requires CUBLAS_WORKSPACE_CONFIG=:4096:8")
        from gbdn.submission_scheduler import run_confirmatory_scheduler
        from gbdn.submission_verify import verify_submission_readiness

        def inside(path: Path) -> Path:
            return path if path.is_absolute() else root / path

        report = verify_submission_readiness(root)
        if not report.ready_for_claim_bearing_execution:
            print(json.dumps(report.to_dict(), sort_keys=True))
            return 2
        summary = run_confirmatory_scheduler(
            repository_root=root,
            run_plan_path=inside(args.run_plan),
            confirmatory_plan_path=inside(args.confirmatory_plan),
            baseline_registry_path=inside(args.baseline_registry),
            worker_path=inside(args.worker),
            authoritative_dataset_root=inside(args.authoritative_dataset_root),
            continue_on_error=not args.stop_on_error,
            retry_recorded_failures=args.retry_recorded_failures,
            timeout_seconds=args.timeout_seconds,
        )
        print(json.dumps(summary.to_dict(), sort_keys=True))
        return 0 if summary.success else 2
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    from gbdn.submission import (
        build_smoke_plan,
        execute_smoke_job,
        require_canonical_output_root,
        run_smoke_subprocess,
    )
    from gbdn.submission_verify import verify_submission_readiness

    if args.command == "verify":
        report = verify_submission_readiness(root)
        print(json.dumps(report.to_dict(), sort_keys=True))
        return 0 if report.submission_complete else 2
    require_canonical_output_root(root, args.output_root)
    plan = build_smoke_plan(
        repository_root=root,
        config_path=args.config,
        run_mode=args.mode,
    )
    if args.command == "preflight":
        output = plan.inventory()
    elif args.command == "smoke":
        output = run_smoke_subprocess(plan, entry_point=Path(__file__)).to_dict()
    else:
        output = execute_smoke_job(plan, expected_run_id=args.run_id).to_dict()
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
