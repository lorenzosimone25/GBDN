# REV-OPS-SCHEDULER-3 handoff

## Task

- **Task ID:** REV-OPS-SCHEDULER-3
- **Agent:** Independent operations reviewer
- **Branch:** detached independent worktree
- **Starting commit:** `d4b2624dcb5ad22fb30183a095269265d0ab8fdb`
- **Ending commit:** commit containing this handoff; SHA reported separately
- **Status proposed:** REJECTED

## Objective

Independently attack the repaired confirmatory scheduler's semantic completion,
authoritative evaluation, drift, resume, failure-evidence, filesystem-race,
and GPU-isolation boundaries without official dataset or H100 execution.

## Summary

The scheduler is rejected because `_semantic_evaluation` scores the current
prediction path without revalidating it against the `result.json` prediction
manifest. A direct witness replaced a manifest-bound archive with distinct,
metric-equivalent bytes; evaluation succeeded and attested the replacement
hash. A float `split_id=0.75` is also silently coerced to split 0. The canonical
worker remains absent, independently blocking claim execution.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `reviews/ops_scheduler_third_independent_review.md` | Binary independent verdict and exact adversarial evidence. | Yes |
| `handoffs/REV-OPS-SCHEDULER-3.md` | Bounded review handoff. | Yes |

No source, tests, paper, result, state, board, notebook, or token was changed.

## Scientific impact

- **Claims enabled:** none.
- **Claims narrowed:** successful semantic recomputation is not valid evidence
  unless the scored bytes are cryptographically bound to the immutable run
  result and bundle.
- **Claims rejected:** scheduler safety for claim-bearing execution; H100
  readiness.
- **Paper sections affected:** none directly; all confirmatory result claims
  remain blocked.

## Evidence

### Tests

```text
command: PYTHONPATH=src python -m pytest -q
         tests/test_submission_scheduler.py
         tests/test_heterophily_evaluator.py
         tests/test_artifact_core.py
         tests/test_submission_verify.py
result:  50 passed, 1 skipped, 2 warnings in 10.61s
```

### Adversarial witnesses

```text
prediction manifest SHA: eec3340e6c8b882b285135ef2948f0ea8471eb23af66700fe0f8ee5e922ad0c9
evaluated replacement SHA: 7256727a1e79585ed66e654b7c7bfa231b704465678bfda62bace6a21508ab72
semantic evaluation accepted and attested replacement: True

float split_id stored in archive: 0.75
observed accepted split after coercion: 0
```

No experiment artifact was retained.

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Every evaluated prediction matches its result manifest | FAIL | Metric-equivalent replacement archive accepted |
| Semantic evaluator handles skip and zero exit | PASS | Static path review and focused tests |
| Authoritative data are pinned and parent-only | PASS | Loader/evaluator static review and tests |
| Prediction scalar schema is exact | FAIL | `split_id=0.75` accepted as 0 |
| Pre/post source and scheduler-input identity | PASS | Static review and tests |
| Failure evidence is immutable and bounded | PASS | Static review and tests |
| Canonical worker exists and is independently accepted | FAIL | Worker absent at reviewed commit |
| Scheduler safe for claim-bearing execution | FAIL | Manifest TOCTOU blocker |

## Known limitations

No official dataset or H100 was used. The review assesses the scheduler as an
orchestration substrate, not model training correctness. GPU isolation was
reviewed statically and through existing CPU tests only.

## Conflicts or decisions needed

None. Repair manifest binding and exact archive scalar typing, add adversarial
regressions, then request another independent operations review. Do not attach
or run the canonical worker before the scheduler is accepted.

## Reproduction instructions

Run the focused command above from a clean checkout at the starting commit.
The full witness recipe and hashes are recorded in the review.

## Rollback

Revert the single review commit. No generated results or source changes require
cleanup.
