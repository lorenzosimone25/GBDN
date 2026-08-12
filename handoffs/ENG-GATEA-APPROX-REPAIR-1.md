# ENG-GATEA-APPROX-REPAIR-1 Handoff

## Task

- **Task ID:** ENG-GATEA-APPROX-REPAIR-1
- **Agent:** Research Software Engineer
- **Branch:** `agent/engineering/ENG-GATEA-APPROX-REPAIR-1`
- **Starting commit:** `92da048`
- **Ending commit:** the commit containing this handoff (reported on delivery)
- **Status proposed:** REVIEW

## Objective

Repair only the independently identified finite-realization diagnostic/test
defects: joined GA-24 evidence, genuine GA-22 synthesis and recurrence checks,
narrow GA-29 semantics, strict diagnostic validation, broader GA-30
instrumentation/storage accounting, and multi-root/near-cap GA-20 coverage.
Do not implement the full fixture/report orchestration or touch the paper,
results, legacy paths, or user-owned files.

## Summary

The finite slice now exposes an immutable-style joined configuration value
object containing the realization tag, degree, graph and interval-grid errors,
chosen ellipse parameter, pole-limited ellipse parameter, explicitly
conservative `M_rho` upper bound, certified interpolation bound, and complete
root/pole geometry. Tests reconstruct its errors and analytic quantities using
independent scalar recurrences and direct formulas.

GA-22 now materializes approximate analyzed coefficients, separately verifies
exact additive reconstruction, applies dense adjoint synthesis to a
deterministic complex signal, compares it with the frame operator, checks all
singular values, pins the heterogeneous prefix-product recurrence, and covers
the `Delta_D >= 1` no-positive-lower-bound case. GA-29 now claims only failure
of finite `K`-hop localization. GA-30 covers four `(D,K)` configurations and
records its complex-SpMV convention, residual-first component count, complex
value count, and coefficient storage bytes.

Public diagnostics now reject empty, nonfinite, noncomplex, or inadmissible
roots; invalid graph spectra and ellipse parameters; empty frame sequences;
and nonfinite/overflowed bound outputs.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `src/gbdn/diagnostics.py` | Joined approximation diagnostic, strict validation, finite-output checks | Yes |
| `tests/test_gate_a_approximation.py` | Independent formula checks and repaired GA-20/22/24/28/29/30 tests | Yes |
| `handoffs/ENG-GATEA-APPROX-REPAIR-1.md` | Implementation evidence and remaining blockers | Yes |

## Scientific impact

- Claims enabled: the finite slice can now report measured approximation error
  beside a correctly labeled conservative theorem certificate; approximate
  adjoint synthesis is directly checked against the frame defect.
- Claims narrowed: GA-29 establishes non-`K`-hop localization for its exact
  witness, not a universal density theorem; a loose Chebyshev certificate is
  not approximation-efficiency evidence.
- Claims rejected: none newly; invalid/overflowed configurations now fail
  rather than generating apparently valid diagnostics.
- Paper sections affected: none in this task.

## Evidence

### Proofs

- theorem/lemma: T-D heterogeneous frame recurrence, T-E Chebyshev certificate,
  T-G perturbation constant, T-H finite locality/cost.
- assumptions: finite admissible roots, self-adjoint graph spectrum in `[0,2]`,
  true operator errors, chosen ellipse certified by the conservative disk
  margin, fixed roots, full per-level Chebyshev recurrence.
- proof location: existing `math/proof_audit.md`; no proof text changed.
- counterexamples checked: `Delta_D >= 1` lower-bound boundary, empty/nonfinite
  inputs, overflowed recurrence, near-cap target with a close endpoint pole,
  exact response beyond polynomial hop reach.

### Tests

```text
command: canonical .venv Python with PYTHONPATH=<repair worktree>/src,
         python -m pytest tests/test_gate_a_approximation.py -q -p no:cacheprovider
result: PASS, 37 passed.

command: canonical .venv Python with PYTHONPATH=<repair worktree>/src,
         python -m pytest tests -q -p no:cacheprovider
result: PASS, 154 passed with 2 upstream torch.jit deprecation warnings.

command: python -m compileall -q
         src/gbdn/diagnostics.py tests/test_gate_a_approximation.py
result: PASS.

command: git diff --check
result: PASS.
```

### Experiment artifacts

- run IDs: none
- result paths: none
- aggregate paths: none
- generated paper assets: none

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| GA-24 joins error, ellipse, `M_rho` bound, geometry, and tag | PASS | `ApproximationConfigurationDiagnostic` and independent test |
| GA-22 exercises analyzed coefficients and dense adjoint synthesis | PASS | Deterministic signal, materialized components, synthesis/frame comparison |
| GA-22 additive reconstruction is separate | PASS | Independent telescoping assertion |
| GA-22 emits/checks singular values | PASS | `record_property` plus squared singular-value/frame-eigenvalue check |
| GA-22 pins heterogeneous recurrence and `Delta>=1` boundary | PASS | Closed-form three-error fixture and `0.8` boundary fixture |
| GA-29 uses narrow non-finite-hop semantics | PASS | Renamed test/docstring and scoped comment |
| Empty/nonfinite/inadmissible/overflow diagnostics fail | PASS | New negative tests |
| GA-30 covers multiple `D,K` and coefficient storage | PASS | `(1,0)`, `(1,3)`, `(2,4)`, `(4,5)` plus bytes/order checks |
| GA-20 includes multi-root and near-cap targets | PASS | Three target families across degrees 4/8/16/32 |
| Analytic/frame/perturbation formulas independently checked | PASS | Direct test-side formulas |
| Full required fixture matrix and machine-readable Gate report | OUT OF SCOPE | Separate orchestrator task |
| Only authorized files changed | PASS | Final commit tree |

## Known limitations

- The conservative `M_rho` upper bound intentionally rejects ellipses whose
  circumscribed disk cannot certify a pole margin, even when the exact ellipse
  itself is pole-free. This is conservative behavior, not a complete numerical
  ellipse maximizer.
- `interval_grid_max_error` is explicitly a deterministic grid maximum, not a
  proof of the continuum supremum.
- SpMV instrumentation defines one `torch.sparse.mm` on a complex feature
  matrix as one complex-feature SpMV. It does not convert that call into an
  equivalent number of real floating-point operations.
- GA-27 comparator metadata and the full graph/root fixture/report layer remain
  separate review/orchestration concerns and were not changed here.

## Reviewer questions

1. Is the field name `conservative_m_rho_upper_bound` sufficiently explicit to
   prevent confusion with an actual ellipse supremum?
2. Should future artifact serialization store both the deterministic grid
   error and an independently optimized continuum estimate?
3. Does the fixture/report task consume the `record_property` values for
   singular spectra, reconstruction, SpMVs, and storage without redefining
   their conventions?

## Conflicts or decisions needed

None within this bounded repair. The full fixture matrix and machine-readable
Gate report are intentionally delegated to the separate orchestrator work.

## Reproduction instructions

From a worktree containing this commit, set `PYTHONPATH` to its `src` directory
and run the focused and full pytest commands above with the canonical virtual
environment.

## Rollback

Revert the single `ENG-GATEA-APPROX-REPAIR-1` commit. It changes no paper,
result, legacy, or generated artifact.
