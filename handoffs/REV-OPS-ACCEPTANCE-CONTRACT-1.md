# REV-OPS-ACCEPTANCE-CONTRACT-1 handoff

## Decision

**REJECT** the operations-acceptance contract at
`e2bd9559d96add135545d20a33d91b1f6a7505b1`.

## Blocking evidence

- Uncommitted mutation of a protected source file is accepted because only
  `commit..HEAD` drift is checked.
- A forged replacement review plus a recomputed token hash is accepted after
  committing the two files; the `independent` assertion is not authenticated.
- The bound independent review accepts only the scheduler substrate and
  explicitly blocks claim-bearing execution, but the token upgrades it to a
  generic operations PASS.
- `scripts/run_heterophily_job.py` is outside the protected surface and the
  readiness verifier checks only that it exists as a regular file.

Exact witnesses and repair requirements are in
`reviews/operations_acceptance_contract_review.md`.

## Evidence

```text
existing focused suite: 4 passed
dirty protected source: accepted (unsafe)
forged/rehashed review: accepted (unsafe)
official/H100 jobs run: none
```

## Files changed

Only this handoff and the independent review were added. No acceptance token,
source, tests, paper, results, state, board, or notebook was edited.

## Next gate

Repair the clean-tree, review-authenticity/scope, strict-path, and complete
protected-surface defects, then obtain a new independent review. The existing
scheduler-only ACCEPT must not authorize a canonical worker or claim-bearing
execution.
