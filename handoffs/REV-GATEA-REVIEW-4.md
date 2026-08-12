# REV-GATEA-REVIEW-4 handoff

## Task

- **Task ID:** REV-GATEA-REVIEW-4
- **Agent:** Independent adversarial A* reviewer
- **Branch:** `agent/reviewer/REV-GATEA-REVIEW-4`
- **Starting commit:** `e21b2743104471f17f56b1b67e013bec5ce28bdb`
- **Ending commit:** commit containing this handoff; SHA reported separately
- **Status proposed:** REJECTED

## Objective

Independently adjudicate every GA-00--GA-35 row and the canonical public
package boundary after the third review's tolerance repair, from a clean
isolated worktree. Run the complete Gate-A and repository suites and reporter,
probe tolerance/spectrum/root/eigenbasis escapes, and issue a binary decision
without editing implementation, tests, paper, results, state, or tokens.

## Summary

Gate A is **REJECTED / STOP THE LINE** at source commit `e21b274`. The focused
Gate suite, full suite, and typed reporter are green, and the exact-eigenbasis
`orthogonality_atol` repair is effective. Independent public probes found two
remaining premise-changing escapes:

1. a `ValidatedLaplacian` exposes a writable tensor alias; NumPy-view mutation
   leaves the version and stored hash unchanged, after which canonical sparse
   computation accepts an asymmetric matrix that fresh validation rejects;
2. root-exported exact GBDN and CayleyNet pole-reduction diagnostics accept
   unbounded cancellation tolerances that erase nonzero poles/terms while
   retaining exact schemas and omitting the tolerance from the record.

GA-00 and GA-27 are rejected. The other 34 rows are accepted under their
frozen narrow scopes. No H100 work or acceptance token is authorized.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `reviews/gate_a_fourth_independent_review.md` | Binary decision, evidence, adversarial witnesses, all-row adjudication, minimum repair | Yes; reviewer-owned |
| `handoffs/REV-GATEA-REVIEW-4.md` | Reproduction and integration handoff | Yes; reviewer-owned |

No other file was changed.

## Scientific impact

- **Claims enabled:** None newly enabled; the review independently confirms
  that 34 rows retain their previously narrowed mathematical scope.
- **Claims narrowed:** A default green validation/report path is insufficient
  if the certified public object or exact reduction can later change its
  premise under the same provenance/realization label.
- **Claims rejected:** Gate-A package acceptance; immutable validated-operator
  provenance; caller-configurable exact reduced-pole claims.
- **Paper sections affected:** No paper edit is authorized. Exact graph-input
  validation and reduced-pole separation must not be promoted until repaired.

## Evidence

### Proofs

- **Theorem/lemma:** GA-00 graph-validation premise; GA-27 reduced-pole
  separation premise.
- **Assumptions:** public validated tokens identify an unchanged self-adjoint
  normalized-Laplacian operator; exact pole reduction cancels only algebraic
  zero/pole coincidences and materially zero coefficients.
- **Proof location:**
  `reviews/gate_a_fourth_independent_review.md`.
- **Counterexamples checked:** frozen nonorthogonal eigensystem; former public
  tolerance keywords; writable validated-token storage alias; GBDN pole/zero
  separation `2.895653538364977` under tolerance `100`; nonzero CayleyNet
  coefficient removed under tolerance `0.3`; invalid spectrum/root/basis and
  graph-validator keyword aliases.

### Tests

```text
Focused Gate-A selection:
503 passed, 3 warnings in 33.60 s

Full repository suite:
653 passed, 2 skipped, 3 warnings in 93.93 s

Clean reporter at e21b274:
470 Gate-labelled nodes
36 PASS / 0 FAIL / 0 NOT_RUN rows
18 UNIQUE / 18 DUPLICATE / 0 MISSING mappings
817 VALUE / 59 N/A / 876 typed fields
0 schema errors
0 decision failures
coverage cross-validation PASS, 0 mismatches
0 provenance-link errors
accepted=false; independent review was the sole reporter blocker
```

Independent probe observations:

```text
ValidatedLaplacian NumPy mutation:
version 0 -> 0
stored hash unchanged
self-adjoint residual 0.625
require_validated_laplacian accepted
fresh validation rejected
ChebyshevBasis consumed the altered token

Exact GBDN pole diagnostic:
default: 0 cancellations, 1 reduced pole
tolerance 100: 1 cancellation at distance 2.895653538364977,
               0 reduced poles, exact tag, no recorded tolerance

Frozen CayleyNet comparator:
default: declared/effective order 3/3, two reduced loci of multiplicity 3
tolerance 0.3: declared/effective order 3/2, empty reduced multiset,
               exact tag, no recorded tolerance
```

### Experiment artifacts

- **Run IDs:** None; no experiment or GPU job was run.
- **Result paths:** None.
- **Aggregate paths:** None.
- **Generated paper assets:** None.

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Clean isolated review of current orchestrator HEAD | PASS | Reporter source state clean at exact `e21b274` |
| Full Gate-A suite and reporter run | PASS | 503 focused tests; 36 reporter rows PASS |
| Full repository regression suite run | PASS | 653 passed, 2 skipped |
| Third-review orthogonality escape closed | PASS | All exact aliases reject tolerance keywords and frozen basis |
| Canonical validated graph object remains valid/immutable | **FAIL** | Writable storage alias bypasses version/hash and is consumed |
| Exact reduced-pole public boundary is fail-closed | **FAIL** | Unbounded unrecorded cancellation tolerances change exact multisets |
| Every GA-00--GA-35 row and package boundary accepted | **FAIL** | GA-00 and GA-27 rejected |
| No forbidden files or H100 artifacts changed | PASS | Only this review and handoff are changed |
| Acceptance token not issued | PASS | No token created or modified |

## Known limitations

1. This review did not modify or propose an implementation patch; repair
   ownership remains with the Software Engineer.
2. CUDA-specific tensor-alias behavior was not required to establish the CPU
   counterexample. The repair should nevertheless verify all supported devices.
3. The reporter correctly measures current default computations but does not
   presently probe either newly found public escape.

## Reviewer questions

1. Can the canonical layer unwrap be made private while public tensor access
   returns a clone, without adding an unchecked alternate path?
2. Should exact pole reduction use symbolic/multiplicity logic with one fixed
   numerical equality threshold, while exploratory thresholding receives a
   separate approximate schema?
3. Are all persisted operator hashes recomputed or otherwise bound after any
   supported device/dtype transfer?

## Conflicts or decisions needed

No ownership conflict. The orchestrator must keep Gate A closed and assign
both repairs before requesting another independent review. This review must
not be interpreted as authorization for H100 execution or claim promotion.

## Reproduction instructions

From a clean worktree at `e21b274`:

```powershell
$env:PYTHONPATH=(Resolve-Path -LiteralPath src).Path
$gateFiles=(Get-ChildItem -LiteralPath tests -Filter 'test_gate_a*.py' |
  Sort-Object Name | ForEach-Object {$_.FullName})
python -m pytest @gateFiles -q -p no:cacheprovider
python -m pytest tests -q -p no:cacheprovider
python scripts/report_gate_a.py
```

Then reproduce the two minimal witnesses in
`reviews/gate_a_fourth_independent_review.md`. Do not create an acceptance
token unless a subsequent independent review accepts the repaired package.

## Rollback

Revert the single review commit. No source, test, paper, result, plan, state,
token, notebook, or frozen artifact requires rollback.
