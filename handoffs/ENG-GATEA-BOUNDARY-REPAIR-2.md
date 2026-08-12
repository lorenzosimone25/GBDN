# ENG-GATEA-BOUNDARY-REPAIR-2 handoff

## Task

- **Task ID:** ENG-GATEA-BOUNDARY-REPAIR-2
- **Agent:** Research Software Engineer
- **Branch:** `agent/engineering/ENG-GATEA-BOUNDARY-REPAIR-2`
- **Starting commit:** `e959bcea37bb4f4cd87221d7b5fe7f048fdf2642`
- **Ending commit:** commit containing this handoff; SHA reported separately
- **Status proposed:** REVIEW

## Objective

Repair exactly the two package-boundary blockers in the fourth independent
Gate-A review: writable storage aliases from `ValidatedLaplacian`, and
caller-controlled numerical cancellation in exact pole diagnostics.

## Summary

- Public `ValidatedLaplacian.tensor`, `to_dense()`, and
  `require_validated_laplacian()` now return independent tensor copies.
- Canonical Chebyshev application uses a private unwrap which checks both the
  PyTorch mutation version and the stored semantic SHA-256 before any sparse
  multiplication. This detects NumPy and `Tensor.data` storage mutation even
  when PyTorch's version counter does not change.
- Exact Blaschke pole reduction has no cancellation tolerance. For admissible
  roots, its mapped numerator zeros and reciprocal-conjugate denominator poles
  cannot coincide, so the exact cancelled-pair count is algebraically zero.
- The frozen scalar CayleyNet comparator has no cancellation tolerance. Its
  exact reduced order is the largest index with an exactly nonzero coefficient;
  that coefficient fixes the pole multiplicity at both Cayley loci.
- GA-00 and GA-27 evidence now execute the frozen storage-alias and
  cancellation-override witnesses rather than relying only on tests.

## Intentional API breaks

1. `ValidatedLaplacian.tensor` and root-exported
   `require_validated_laplacian(token)` no longer return the tensor storage
   consumed by canonical layers. Code that mutated or retained those aliases
   must instead treat the token as opaque and pass it to canonical APIs.
2. `frozen_scalar_cayleynet_comparator(..., cancellation_tolerance=...)` and
   `reduced_blaschke_pole_diagnostic(..., cancellation_tolerance=...)` now
   raise `TypeError`. Approximate exploratory reduction was not added because
   it is outside this Gate repair and must not share an exact schema.
3. The exact diagnostic schemas advance from v1 to v2 and include an explicit
   algebraic `reduction_policy` with no caller tolerance.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `src/gbdn/core.py` | Isolated public copies; private version/hash-checked unwrap | Yes |
| `src/gbdn/layers.py` | Canonical layer uses private checked unwrap | Yes |
| `src/gbdn/diagnostics.py` | Algebraic exact pole reduction; removed tolerance controls | Yes |
| `src/gbdn/gate_a_evidence.py` | Added GA-00 alias/tamper and GA-27 override evidence | Yes |
| `tests/test_gate_a_exact_slice.py` | Dense/sparse/model NumPy and `.data` adversarial regressions | Yes |
| `tests/test_gate_a_approximation.py` | Far-pole/nonzero-coefficient witnesses at root and module aliases | Yes |
| `tests/test_gate_a_provenance.py` | Bound evidence to comparator schema v2 | Yes |
| `handoffs/ENG-GATEA-BOUNDARY-REPAIR-2.md` | This handoff | Yes |

No paper, result, state, board, review, legacy, notebook, or acceptance-token
file was changed.

## Scientific impact

- **Claims enabled:** none without a fresh independent review.
- **Claims repaired:** GA-00 validated-operator premise integrity; GA-27 exact
  reduced-pole premise integrity.
- **Claims narrowed:** none beyond the already frozen continuum pole-locus
  scope. This proves neither finite-spectrum separation nor approximation,
  optimization, compute, or predictive superiority.
- **Paper sections affected:** none edited.

## Evidence

### Mathematical basis

- For `|alpha|<1`, a Blaschke numerator zero is at `alpha`, while every factor
  denominator zero is at `1/conj(alpha)` outside the unit disk. The injective
  Cayley inverse therefore cannot map an admissible numerator zero to a
  denominator pole.
- For the frozen Cayley response of exact order `r`, nonzero `c_r` uniquely
  supplies the order-`r` principal part at one Cayley pole, and nonzero
  `conj(c_r)` supplies it at the other. Lower-order terms cannot cancel either
  leading principal part.

### Tests

```text
Focused exact + approximation + provenance:
141 passed, 3 known warnings

All Gate-A test files:
512 passed, 3 known warnings

Full repository suite at this task base:
665 passed, 2 skipped, 3 known warnings
```

The warnings are two upstream PyTorch/Python-3.14 TorchScript deprecations and
the existing PyTorch sparse-invariant warning. The two skips are the documented
Windows symlink-privilege cases.

### Reporter

The pre-commit reporter executed successfully with all test/evidence decisions
green; its source-provenance blocker is expected while the repair is dirty.
The orchestrator or independent reviewer must rerun it from the clean committed
SHA.

### Experiment artifacts

- None. No H100 or claim-bearing experiment was run.

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---:|---|
| Public token access cannot mutate certified storage | PASS | tensor, unwrap, dense, NumPy, `.data`, sparse, and model-path tests |
| Version-invisible private storage tampering fails before multiplication | PASS | content-hash adversarial tests and GA-00 evidence |
| Both exact pole APIs reject former tolerance at root/module aliases | PASS | frozen `100.0` and `0.3` witness tests |
| Exact semantics preserved without magnitude threshold | PASS | far-pole and `1e-30` nonzero-order regressions |
| Gate and full suites pass | PASS | 512 Gate; 665 full |
| Acceptance token issued | NOT DONE | Prohibited; fresh independent review required |

## Known limitations

- Content-integrity hashing is linear in operator storage and transfers data to
  CPU for the SHA-256 calculation. This is a deliberate fail-closed boundary
  and may add overhead for large GPU graphs. Any later optimization must retain
  the no-public-alias property and independently verify equivalent tamper
  detection before changing this policy.
- Exact diagnostic arithmetic is represented in the supplied floating dtype;
  the algebraic reduction decision itself no longer depends on floating
  magnitude or a caller threshold.
- This task does not independently accept Gate A.

## Reviewer questions

1. Do all public/root/model/layer token paths now prevent or detect the frozen
   NumPy and `.data` mutations before multiplication?
2. Is algebraic no-cancellation for admissible Blaschke factors correctly
   reflected by the v2 exact schema?
3. Does exact highest-nonzero-order reduction correctly preserve both frozen
   Cayley comparator pole loci for every nonzero leading coefficient?

## Conflicts or decisions needed

None for integration. Gate A remains stop-line pending fresh independent
package-boundary review. The orchestrator's later baseline work is unrelated;
this repair should be cherry-picked onto its current HEAD.

## Reproduction instructions

```powershell
$env:PYTHONPATH=(Resolve-Path -LiteralPath src).Path
$gateFiles=(Get-ChildItem -LiteralPath tests -Filter 'test_gate_a*.py' |
  Sort-Object Name | ForEach-Object {$_.FullName})
python -m pytest @gateFiles -q -p no:cacheprovider
python -m pytest tests -q -p no:cacheprovider
python scripts/report_gate_a.py
```

## Rollback

Revert the task commit. No frozen artifact, result, paper, state, board,
notebook, or legacy file is involved.
