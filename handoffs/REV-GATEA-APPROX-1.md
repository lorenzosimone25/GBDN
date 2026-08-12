# REV-GATEA-APPROX-1 Handoff

## Task

- **Task ID:** REV-GATEA-APPROX-1
- **Agent:** Independent Gate-A Reviewer
- **Branch:** `agent/reviewer/REV-GATEA-APPROX-1`
- **Starting commit:** `c0f58b52cf24bba2d867ecff03eb8f710f1c3997`
- **Approximation commit audited:** `4145910c31af36c93ee89c399e0e783caf3213b7`
  / integrated cherry-pick `9c11ea9`
- **Ending commit:** the commit containing this handoff (reported on delivery)
- **Status proposed:** BLOCKED

## Objective

Independently audit the finite-realization diagnostic and test slice against
the frozen theorem-to-test contract, with particular attention to GA-18,
GA-20--GA-22, and GA-24--GA-30. Verify formulas, independence, false-positive
risk, and claim scope without editing source, tests, paper, or results.

## Summary

The Bernstein-ellipse, conservative supremum, multilevel frame recurrence, and
fixed-root perturbation formulas are mathematically correct for admissible
inputs. The integrated test slice is blocked: GA-30 crashes because the test
calls `.float()` on a `ValidatedLaplacian`; GA-24 emits neither approximation
error nor `M_rho`; and GA-22 duplicates the frame-defect norm under a synthesis
variable name rather than testing reconstruction. Most remaining tests are
useful deterministic unit witnesses but do not cover the required fixture
matrix or emit Gate-A provenance.

No source/test/paper/result file was modified.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `reviews/gate_a_approximation_review.md` | Independent formula, test-independence, false-positive, and claim-scope audit | Yes; review only |
| `handoffs/REV-GATEA-APPROX-1.md` | Evidence and orchestrator handoff | Yes |

## Scientific impact

- Claims enabled: none; formulas may proceed after executable-contract repair.
- Claims narrowed: GA-29 shows non-finite-hop behavior, not density from its
  current assertion; GA-27 is one premise of a narrow exact continuum
  separation; GA-20's bound is certification, not evidence of approximation
  efficiency.
- Claims rejected: current GA-24, GA-22 reconstruction, and GA-30 PASS labels.
- Paper sections affected: none directly; Gate-A promotion remains blocked.

## Evidence

### Proofs

- theorem/lemma: Chebyshev ellipse error, T-D multilevel frame defect, T-F
  pole-locus premise, T-G resolvent perturbation, T-H locality/cost.
- assumptions: admissible finite roots; exact rational target versus polynomial
  realization; closed analytic ellipse; true per-level operator errors;
  aligned self-adjoint operators and fixed roots; declared full Chebyshev
  recurrence.
- proof location: `math/proof_audit.md`, independently re-derived in
  `reviews/gate_a_approximation_review.md`.
- counterexamples/false positives checked: inflated analytic/frame/perturbation
  bounds, plausible fabricated GA-24 geometry, duplicated reconstruction norm,
  one-entry nonlocality mislabeled density, validated-token API mismatch.

### Tests

```text
command: canonical .venv Python with PYTHONPATH=<review worktree>/src,
         python -m pytest tests/test_gate_a_approximation.py -q
result: FAIL; 22 passed, 1 failed. GA-30 raises AttributeError because
        ValidatedLaplacian has no .float() method.

command: independent metric script reproducing GA-20/22/28 quantities
result: GA-20 bound/error ratios range from 1.39e3 to 7.77e9;
        GA-22 observed/Delta ratios range from 0.524 to 0.028;
        GA-28 observed/bound ratios are approximately 0.864 and 0.760.

command: 200,000-point independent sample of the GA-20 Bernstein ellipse
result: sampled max approximately 1.474; conservative helper bound 3.468;
        target-pole ellipse parameter approximately 3.973 for rho=1.5.
```

### Experiment artifacts

- run IDs: none
- result paths: none
- aggregate paths: none
- generated paper assets: none

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Diagnostic formulas audited | PASS | Formula audit in review |
| Relevant tests run read-only | PASS | 22 pass / 1 fail result |
| GA-18 convention observable independent enough | PASS for unit fixture | Dense oracle cross-check |
| GA-20 analytic bound correct and adequately verified | PARTIAL | Formula valid; loose and assumptions/components not pinned |
| GA-21 one-level frame observable correct | PASS for unit fixture | True operator epsilon and independent frame matrix |
| GA-22 recurrence and reconstruction contract satisfied | FAIL | Bound partial; reconstruction duplicated; no `Delta>=1` case |
| GA-24 contracted quantities emitted | FAIL | Error and `M_rho` absent |
| GA-25/26 expressivity boundary complete | PARTIAL | Stable/toy witnesses only |
| GA-27 comparison scope safe | PARTIAL | Correct off-axis premise; comparator metadata/theorem scope absent |
| GA-28 perturbation formula and inequality | PASS as witness / PARTIAL provenance | Correct constant; meaningful ratios; no independent constant record |
| GA-29 locality/density wording exact | PARTIAL | Locality passes; one nonzero proves nonlocality, not density |
| GA-30 current integrated test passes | FAIL | Validated-token `AttributeError` |
| Required fixture matrix and machine-readable provenance | FAIL | Not implemented in this slice |
| Only review artifacts changed | PASS | Final commit tree |

## Known limitations

- This review targeted the approximation commit and its integrated state at
  `c0f58b5`; GA-19 lives in another slice and was not re-adjudicated here.
- Independent ellipse sampling is a diagnostic check of the conservative
  bound, not a replacement for analytic proof.
- No literature search was performed. GA-27 scope was checked against the
  repository's completed primary-source audit.

## Reviewer questions

1. Will GA-24 become a saved configuration-level diagnostic rather than a
   root-geometry dictionary?
2. Will GA-22 exercise the same synthesis API used by the model and include a
   `Delta_D>=1` no-lower-bound case?
3. Will the Gate report distinguish a conservative `M_rho` upper bound from
   the sampled/actual ellipse supremum?
4. Will GA-27 metadata freeze the learned shared Cayley scale and exact scalar
   response family without implying finite-spectrum separation?
5. Which instrumentation abstraction will count SpMVs if the sparse kernel
   changes from `torch.sparse.mm`?

## Conflicts or decisions needed

The approximation test was authored against a raw-tensor Laplacian API, while
the integrated canonical implementation now requires a validated token. The
orchestrator must resolve that integration and rerun the review. No scientific
identity change is required.

## Reproduction instructions

Create a worktree at `c0f58b5`, set `PYTHONPATH` to that worktree's `src`, and
run `python -m pytest tests/test_gate_a_approximation.py -q`. Inspect the full
review for independent metric scripts and theorem-test mismatches.

## Rollback

Revert the single `REV-GATEA-APPROX-1` review commit. It contains only this
review and handoff.
