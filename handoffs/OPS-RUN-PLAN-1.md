# OPS-RUN-PLAN-1 handoff

## Scope

Implemented immutable confirmatory run-plan validation and read-only resume
inventory using synthetic records only. No real plan, job, dataset, baseline,
GPU process, result, or paper artifact was created.

## Frozen behavior

- The run plan hashes the admitted baseline registry and confirmatory plan.
- It requires exactly `methods × 5 datasets × 10 splits × 3 seeds`, with no
  duplicate logical job or run identity.
- Every job uses `heterophily_confirm`, the frozen variant, trial zero, full
  mode, one shared clean source/environment, one isolated non-CPU GPU,
  deterministic environment variables, and a config bound to method, dataset,
  split, seed, equal budget, registry hash, and plan hash.
- Baseline jobs must carry the exact admitted upstream commit; TightGBDN uses
  the explicit not-applicable sentinel.
- Dry-run inventory calls the immutable artifact classifier and reports
  pending/complete/partial/corrupt/conflict counts without creating paths.
- The readiness verifier validates the run plan when it appears and blocks
  unsafe artifact states.

## Verification

- Run-plan/baseline/verifier focused suite: 22 passed.
- Synthetic exact inventory: 450 pending jobs, no output directory created.
- Full repository suite: 632 passed, 1 Windows privilege skip, 3 known
  environment warnings.

## Remaining block

No real registry/plan exists. The independent Gate-A token, dataset identity,
actual verified baselines, frozen method/budget/threshold decisions, isolated
post-freeze evaluator, subprocess scheduler/failure handling, and independent
operations review are still required.
