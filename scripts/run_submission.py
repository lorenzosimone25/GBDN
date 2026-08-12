#!/usr/bin/env python3
"""Safe command-line entry point for the Stage-1 CPU submission smoke."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


# Stage-1 is CPU-only. This must precede importing gbdn, whose package imports
# PyTorch. The later H100 interface will isolate one selected GPU separately.
if "torch" in sys.modules:
    raise RuntimeError("PyTorch was imported before CPU device isolation")
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gbdn.artifacts import RunMode  # noqa: E402
from gbdn.submission import (  # noqa: E402
    build_smoke_plan,
    execute_smoke_job,
    require_canonical_output_root,
    run_smoke_subprocess,
)


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
        choices=(RunMode.SMOKE.value, RunMode.FULL.value),
        default=RunMode.SMOKE.value,
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.repository_root.resolve(strict=True)
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
