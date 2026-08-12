# OPS-SCHEDULER-1 handoff

## Scope

Implemented a guarded sequential scheduler state machine and synthetic worker
tests. No canonical training worker, Gate-A token, real plan, dataset, baseline,
H100 process, result, or paper artifact was created.

## Scheduler behavior

- Revalidates independent Gate-A acceptance and the complete run plan before
  examining any job.
- Accepts only the exact nonsymlinked canonical worker path.
- Runs `MAX_WORKERS=1` behavior through isolated subprocesses with each job's
  frozen CUDA/determinism environment.
- Skips only validated matching complete bundles; partial/corrupt/conflicting
  state blocks. Prior failure records require an explicit retry flag.
- Converts nonzero exit, timeout, and zero-exit-without-complete-bundle cases
  into immutable content-addressed failure records.
- Continues independent jobs only when configured, never deletes state, and
  never overwrites an identical failure record.

## Verification

- Scheduler/verifier focused suite: 8 passed, 1 privilege-dependent symlink
  skip.
- Failure-isolation fixture preserved both a subprocess failure and a worker
  postcondition failure while continuing to the second job.
- Full repository suite: 645 passed, 2 privilege-dependent symlink skips, 3
  known environment warnings.

## Remaining block

The canonical `scripts/run_heterophily_job.py` worker is intentionally absent.
Authoritative dataset identity, admitted baselines, real plan, evaluator
binding, independent Gate-A token, and independent operations acceptance are
mandatory before adding or running it.
