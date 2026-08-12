# REV-OPS-SCHEDULER-5 handoff

## Task

- **Task ID:** REV-OPS-SCHEDULER-5
- **Agent:** Independent operations reviewer
- **Starting commit:** `d3df9e92a933ad5bf0db815444feebf6e974f982`
- **Status proposed:** ACCEPTED for scheduler substrate only

## Summary

The immutable-byte-snapshot repair closes the prior ABA race. A deterministic
A-to-B-to-A witness scored A's logits and emitted an attestation bound to A's
manifest SHA-256. Snapshot size/hash, ZIP/NPY parsing, exact split types,
post-capture path mutation, and authority-value non-persistence pass review.
The focused suite reports 53 passed and 1 platform skip.

The canonical worker `scripts/run_heterophily_job.py` remains absent. This
acceptance does not authorize official or H100 claim-bearing execution.

## Files changed

Only this handoff and `reviews/ops_scheduler_fifth_independent_review.md` were
added. No source, tests, paper, results, state, board, notebook, or token was
changed.

## Scientific impact

- **Enabled:** the scheduler may be treated as an independently accepted
  orchestration substrate at the reviewed commit.
- **Still blocked:** canonical worker execution, official confirmatory runs,
  H100 runs, and all claims based on them.
- **Paper impact:** none until valid worker-produced artifacts exist.

## Evidence

- Exact reviewed commit:
  `d3df9e92a933ad5bf0db815444feebf6e974f982`.
- ABA: A SHA `682eb9a7...`; B SHA `4febd545...`; scored logits equal A;
  attestation equals A; no authority values persisted.
- Focused suite: `53 passed, 1 skipped, 2 warnings in 9.52s`.
- No official dataset, GPU, or H100 job was run.

## Acceptance boundary

Scheduler substrate: **ACCEPT**. Canonical worker and claim-bearing execution:
**BLOCKED**.

## Reproduction

Run the focused command and deterministic witness recorded in the review from
a clean checkout of the starting commit.

## Rollback

Revert the single review commit; no artifact cleanup is needed.
