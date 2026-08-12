# REV-OPS-SCHEDULER-4 handoff

## Task

- **Task ID:** REV-OPS-SCHEDULER-4
- **Agent:** Independent operations reviewer
- **Starting commit:** `8b75ab3059930f1ecbd4c51bed63702d1f372cb8`
- **Status proposed:** REJECTED

## Summary

The repaired scheduler rejects the prior static manifest swap and malformed
split scalar inputs, but an ABA witness scores metric-equivalent archive B and
restores manifest archive A before all trailing hashes. Semantic evaluation
accepts. Pre/post path hashing therefore does not bind the metric to the
manifest bytes. Use one bounded immutable byte snapshot for hashing, parsing,
scoring, and attestation. The canonical worker remains absent.

## Files changed

Only this handoff and
`reviews/ops_scheduler_fourth_independent_review.md` were added. No source,
tests, paper, results, state, board, notebook, or token was changed.

## Evidence

- Exact reviewed commit: `8b75ab3059930f1ecbd4c51bed63702d1f372cb8`.
- ABA outcome: `mutation_ABA_B_scored_A_restored=ACCEPTED_ABA`.
- Focused suite: `52 passed, 1 skipped, 2 warnings in 9.24s`.
- No official dataset, GPU, or H100 execution occurred.

## Scientific impact

No claim is enabled. Scheduler acceptance and all claim-bearing execution stay
blocked. The review covers only the scheduler orchestration substrate, not a
canonical worker or model correctness.

## Reproduction

Run the focused command recorded in the review. Reproduce the ABA witness by
replacing A with same-metric B after the pre-hash, restoring A after arrays are
loaded but before evaluator/scheduler trailing hashes, and observing successful
`_semantic_evaluation`.

## Rollback

Revert this review commit; no artifact cleanup is needed.
