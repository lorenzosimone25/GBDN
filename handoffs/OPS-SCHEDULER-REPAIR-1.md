# OPS-SCHEDULER-REPAIR-1 handoff

## Task

- **Task ID:** OPS-SCHEDULER-REPAIR-1
- **Agent:** Research Software Engineer
- **Branch:** `agent/engineering/OPS-SCHEDULER-REPAIR-1`
- **Starting commit:** `080babd20b3ec10dd03d98701042066cc4a58b7f`
- **Ending commit:** commit containing this handoff; SHA reported separately
- **Status proposed:** REVIEW

## Objective

Repair the scheduler blockers confirmed by the second independent operations
review without adding a canonical worker or running an official/H100 job.

## Summary

The scheduler now recaptures source, interpreter/environment, dependency lock,
plan, registry, and worker identity before every skip/launch and after child
return. A matching bundle is skippable or complete only after the parent opens
the byte-pinned official NPZ, derives the authoritative test row and labels,
invokes the independent evaluator, and compares the recomputed official metric
with a closed result-payload field. It performs that recomputation every time;
an attestation is additional immutable evidence rather than a substitute.

Evaluation attestations bind dataset, split, run, prediction, evaluator,
authoritative index/label, metric, and example-count hashes, but do not persist
indices or labels. Failure attempts persist bounded, conservatively redacted,
hash-bound stdout/stderr/traceback files exclusively. Orphaned, tampered,
symlinked, unexpected, or conflicting failure evidence is corrupt/conflicting
and not retryable. The canonical worker remains absent and execution remains
blocked pending independent operations review.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `src/gbdn/submission_scheduler.py` | Authoritative evaluation, launch-state rebinding, immutable failure evidence. | Yes |
| `src/gbdn/heterophily_evaluator.py` | Pinned official split loader and hash-only attestation contract. | Yes |
| `src/gbdn/artifacts.py` | Hash-bound failure manifests and fail-closed failure-directory validation. | Yes |
| `tests/test_submission_scheduler.py` | Adversarial scheduler, drift, semantic, race, redaction, and failure-state tests. | Yes |
| `tests/test_artifact_core.py` | Align legacy failure fixture with explicit no-traceback sentinel. | Yes |
| `tests/test_submission_verify.py` | Replace stale token-absence assertion with independently accepted Gate requirement. | Yes |
| `handoffs/OPS-SCHEDULER-REPAIR-1.md` | This handoff. | Yes |

## Scientific impact

- **Claims enabled:** none; this is an operations/provenance repair.
- **Claims narrowed:** structural bundle validity alone never establishes a
  valid official metric or safe resume decision.
- **Claims rejected:** scheduler/H100 readiness before a canonical worker and
  independent operations acceptance.
- **Paper sections affected:** none.

## Evidence

### Tests

```text
command: PYTHONPATH=src python -m pytest -q
         tests/test_submission_scheduler.py
         tests/test_heterophily_evaluator.py
         tests/test_artifact_core.py -p no:cacheprovider
result:  47 passed, 1 skipped, 2 known warnings

command: PYTHONPATH=src python -m pytest -q tests -p no:cacheprovider
result:  690 passed, 2 skipped, 1 failed, 145 warnings
failure: tests/test_submission_verify.py requires Gate acceptance PASS; the
         isolated starting commit predates the orchestrator's portable-token
         fix. The orchestrator reports this is fixed at root commit 35a383a.
```

No official dataset or GPU was accessed. The platform skips concern symlink
creation. Warnings are the existing PyTorch/Python 3.14 deprecations and sparse
invariant warning.

### Experiment artifacts

- **Run IDs:** none
- **Result paths:** none
- **Aggregate paths:** none
- **Generated paper assets:** none

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Skip invokes authoritative recomputation | PASS | Scheduler semantic test |
| Zero-exit completion invokes authoritative recomputation | PASS | Wrong-bundle postcondition test |
| Current source/environment/input identity rebound | PASS | Pre/post-child drift and direct recapture tests |
| Attestation stores no labels/indices | PASS | Closed attestation test |
| Failure evidence immutable, bounded, redacted, hash-bound | PASS | Attempt evidence adversarial test |
| Partial/corrupt/conflict failure state fails closed | PASS | Tamper/orphan tests |
| Canonical worker available | FAIL | Intentionally outside this task; worker absent |
| Full integration green on starting commit | FAIL | One known portable-token fixture mismatch; root fix exists |

## Known limitations

The canonical heterophily worker is absent, so worker-side identity repetition,
dataset isolation, checkpoint selection, and artifact production are not yet
reviewable. Path validation is fail-closed against static traversal/symlink
attacks, not a hardened boundary against a privileged process swapping path
components between checks and opens. Redaction is best-effort and bounded;
operators must not print secrets. Dataset redistribution terms remain an
external protocol blocker.

## Reviewer questions

1. Does every skip and successful completion demonstrably invoke the trusted
   evaluator rather than accepting an earlier attestation?
2. Can any source/environment/plan/registry/worker drift evade the pre/post
   launch checks?
3. Can partial, raced, tampered, or path-escaping failure evidence become
   retryable or overwrite an earlier attempt?
4. After integration onto the portable-token root, is the full suite green?

## Conflicts or decisions needed

Cherry-pick onto root commit `35a383a` or later and rerun the verifier test;
do not weaken the Gate acceptance PASS assertion. Do not treat this handoff as
operations acceptance.

## Reproduction instructions

```powershell
$env:PYTHONPATH=(Resolve-Path -LiteralPath src).Path
C:\Users\Lough\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pytest -q `
  tests/test_submission_scheduler.py tests/test_heterophily_evaluator.py `
  tests/test_artifact_core.py tests/test_submission_verify.py -p no:cacheprovider
```

## Rollback

Revert the single OPS-SCHEDULER-REPAIR-1 commit. No result, Gate token, paper,
state, board, official-data, or GPU artifact requires cleanup.
