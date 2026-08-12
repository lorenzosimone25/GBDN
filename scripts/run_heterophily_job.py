"""Execute one canonical, validated official-heterophily run-plan job."""

from __future__ import annotations

import argparse
import os


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--run-plan", required=True)
    parser.add_argument("--job-index", required=True, type=int)
    parser.add_argument("--run-id", required=True)
    return parser


def _require_isolated_environment() -> None:
    visible = os.environ.get("CUDA_VISIBLE_DEVICES")
    if not visible or visible == "-1" or "," in visible:
        raise SystemExit("canonical worker requires exactly one isolated CUDA device")
    if os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
        raise SystemExit("canonical worker requires CUBLAS_WORKSPACE_CONFIG=:4096:8")
    if os.environ.get("PYTHONHASHSEED") != "0":
        raise SystemExit("canonical worker requires PYTHONHASHSEED=0")


def main() -> int:
    arguments = _parser().parse_args()
    # This check intentionally precedes imports that transitively import torch.
    _require_isolated_environment()
    from gbdn.heterophily_worker import execute_planned_job

    bundle = execute_planned_job(
        repository_root=arguments.repository_root,
        run_plan_path=arguments.run_plan,
        job_index=arguments.job_index,
        run_id=arguments.run_id,
    )
    print(bundle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
