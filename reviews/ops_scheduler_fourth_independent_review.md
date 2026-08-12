# REV-OPS-SCHEDULER-4 independent review

## Verdict

**REJECT** at exact reviewed commit
`8b75ab3059930f1ecbd4c51bed63702d1f372cb8`.

The narrow repair rejects the prior static metric-equivalent manifest swap and
enforces exact split scalar types. It does not bind evaluation to one immutable
byte snapshot: an ABA replacement can cause archive B to be scored while
manifest-bound archive A is present for both trailing hashes. This remains a
stop-the-line artifact-integrity failure for the scheduler substrate.

The canonical worker `scripts/run_heterophily_job.py` remains absent. No
official or H100 claim-bearing execution is authorized.

## Independent evidence

This review used a fresh detached worktree at the exact commit above and ran no
official dataset or GPU job. The prior same-metric A-to-B replacement is now
rejected before scoring. Mutations left in place either immediately before or
after scoring are rejected by the post-check. Float and bool `expected_split`
values and float, bool, or vector stored `split_id` values are also rejected.

The remaining direct ABA witness was:

1. Create archive A and bind its size and SHA-256 in `result.json`.
2. Let the scheduler's pre-check validate A.
3. Replace A with metric-equivalent archive B immediately before evaluator
   loading, so B's logits are loaded and scored.
4. Restore A during metric recomputation, before the evaluator's trailing path
   hash and scheduler post-check.
5. `_semantic_evaluation` returns successfully and can write an attestation
   for A even though the computed metric used B's loaded logits.

Observed result:

```text
manifest A: 682eb9a736f530c282e1a2024ffbdd52595805f5916ab7e8fef7b5e3f1f7ea15
replacement B: 46919627ecc48af4f2d7e848119886e375802398a3f264a722df5e38b1212ea5
mutation_ABA_B_scored_A_restored=ACCEPTED_ABA
```

The witness used deterministic function-boundary mutation to exercise the
filesystem race without timing assumptions. Pre/post pathname hashes cannot
prove that the arrays scored came from the manifest-bound bytes.

## Required repair

- Read the manifest-validated prediction bytes once into an immutable bounded
  snapshot, hash that exact snapshot, and parse/score the same snapshot.
- Bind the returned metric and attestation to that snapshot hash.
- Add an ABA regression demonstrating that no path replacement can change
  scored arrays while preserving acceptance.

The prior repaired source, environment, dependency, plan, registry, worker,
authoritative-data, failure-evidence, resume, and GPU-isolation boundaries
remain supported by the narrow diff, static review, and focused regression
suite. They do not compensate for the surviving snapshot defect.

## Test evidence

```text
PYTHONPATH=src python -m pytest -q \
  tests/test_submission_scheduler.py \
  tests/test_heterophily_evaluator.py \
  tests/test_artifact_core.py \
  tests/test_submission_verify.py -p no:cacheprovider

52 passed, 1 skipped, 2 warnings in 9.24s
```

The skip is the platform-conditional symlink test; warnings are the existing
PyTorch/Python 3.14 deprecations.

## Acceptance decision

| Criterion | Decision |
|---|---|
| Prior static same-metric manifest swap | PASS: rejected |
| Pre/post evaluation mutation left in place | PASS: rejected |
| Exact expected/stored split scalar typing | PASS |
| One immutable snapshot is both hashed and scored | **FAIL: ABA accepted** |
| Previously repaired source/environment/authority/failure boundaries | PASS by static/test evidence |
| Canonical worker available and reviewed | **FAIL: absent** |
| Scheduler safe for claim-bearing execution | **FAIL** |

No scheduler acceptance token may be issued from this review.
