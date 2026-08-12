# REV-OPS-CPU-SMOKE-2 handoff

## Task

- **Task ID:** REV-OPS-CPU-SMOKE-2
- **Agent:** Independent operations/reproducibility reviewer
- **Branch:** detached independent worktree
- **Starting commit:** `b6db07ff30432948ee4663892f80579941fff04a`
- **Ending commit:** commit containing this handoff; SHA reported separately
- **Status proposed:** REVIEW for diagnostic smoke; REJECTED for scheduler binding

## Objective

Independently review CPU-only smoke isolation, immutable resume behavior,
failure isolation, source/Gate refusal, scheduler/evaluator separation, and
filesystem boundaries without running H100 hardware or official datasets.

## Summary

The one-job synthetic CPU smoke is accepted only as a diagnostic operations
primitive. The future confirmatory scheduler is rejected for worker binding:
its skip and zero-exit completion paths do not invoke independent official
metric evaluation, it does not rebind current source/environment to the frozen
job, required failure logs are absent, and the canonical worker does not yet
exist. The repository remains stop-line for H100 and claim-bearing work.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `reviews/ops_cpu_smoke_second_independent_review.md` | Binary independent review and findings. | Yes |
| `handoffs/REV-OPS-CPU-SMOKE-2.md` | Bounded handoff. | Yes |

No source, tests, paper, results, state, board, notebook, or token changed.

## Scientific impact

- **Claims enabled:** none; only diagnostic execution behavior is accepted.
- **Claims narrowed:** a hash-valid future bundle is not sufficient for
  scheduler skip/completion without independent official metric evaluation.
- **Claims rejected:** scheduler readiness for a canonical claim-bearing
  worker; H100 readiness.
- **Paper sections affected:** none.

## Evidence

### Tests

```text
command: PYTHONPATH=src python -m pytest -q
         tests/test_submission_smoke.py tests/test_artifact_core.py
         tests/test_repository_boundaries.py tests/test_submission_scheduler.py
         tests/test_run_plan.py tests/test_heterophily_evaluator.py
         tests/test_heterophily_statistics.py tests/test_submission_verify.py
         tests/test_gate_acceptance.py -p no:cacheprovider
result:  88 passed, 2 skipped, 1 failed
```

The failure is a stale verifier assertion that still expects the now-present
Gate-A acceptance token to be absent. The skips are platform-conditional
symlink tests. No H100 or official dataset was used.

### Experiment artifacts

- **Run IDs:** none retained
- **Result paths:** none
- **Aggregate paths:** none
- **Generated paper assets:** none

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| CPU isolation before PyTorch | PASS | CLI pre-import guard, plan guard, child environment, focused tests |
| One fixed diagnostic job only | PASS | Exact frozen plan schema |
| Immutable non-overwrite/resume | PASS | Exclusive artifacts, slot claim, semantic smoke recheck |
| Corrupt/partial/conflict fail closed | PASS | Artifact core and smoke tests |
| Subprocess isolation | PASS | Separate worker PID and timeout/exit handling |
| Dirty/full/Gate refusal | PASS | Full mode remains blocked after validating Gate token |
| Independent official evaluation in scheduler | FAIL | Evaluator is never called on skip or completion |
| Current source/environment rebound | FAIL | Frozen records are not compared to recaptured launch state |
| Complete immutable failure evidence | FAIL | Logs/traceback manifests are absent |
| Canonical worker available | FAIL | `scripts/run_heterophily_job.py` absent |
| Integrated focused suite green | FAIL | 1 stale verifier assertion |

## Known limitations

The smoke is not training or benchmark evidence. Static path attacks are
covered, but the path-based implementation is not a hardened boundary against
a privileged concurrent local filesystem attacker. The notebook remains
fail-closed and has no launch cells.

## Conflicts or decisions needed

None. Repair scheduler semantic verification and launch-state binding before
implementing or attaching the worker. Do not reinterpret diagnostic-smoke
acceptance as H100 authorization.

## Reproduction instructions

Run the focused command above from a clean checkout at the starting commit.
Read the full adjudication in
`reviews/ops_cpu_smoke_second_independent_review.md`.

## Rollback

Revert the single review commit; no source or artifact cleanup is required.
