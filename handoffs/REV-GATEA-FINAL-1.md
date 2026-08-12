# REV-GATEA-FINAL-1 Handoff

## Task

- **Task ID:** REV-GATEA-FINAL-1
- **Agent:** Independent adversarial Gate-A Reviewer
- **Branch:** `agent/reviewer/REV-GATEA-FINAL-1`
- **Starting commit:** `e5edf72bfe2920834cfcbb8f4fec53935e6b719f`
- **Ending commit:** the commit containing this handoff (reported on delivery)
- **Status proposed:** **BLOCKED**

## Objective

Independently audit GA-00--GA-35 against the frozen scientific and
theorem-to-test contracts; run the complete Gate suite and reporter; inspect
equation/API correspondence, oracle independence, fixture/root/depth/degree
coverage, exact-versus-finite semantics, reconstruction, bounds, locality,
perturbation, sensitivity counterexamples, cost accounting, and parameter
lifecycle; make no implementation or paper changes.

## Binary verdict

**GATE A BLOCKED.** All named tests execute and pass, but 35 of 36 rows lack
the required machine-readable residual/provenance record. GA-00, GA-10,
GA-14, GA-25, and GA-27 are independently rejected at this commit for
substantive package/test-contract mismatches. The remaining rows are accepted
only conditionally except GA-23, which has an adequate structured record.

The central mathematics is not rejected. No counterexample was found to the
exact Parseval construction, heterogeneous finite-frame bound, first-kind
Chebyshev bound, fixed-root perturbation theorem, locality statement, or
negative oversquashing boundary.

## Summary of blockers

1. The report returns `accepted=false`; only GA-23 emits a structured
   `gate_a_metrics` record. GA-22/28/30 properties are ignored by the reporter.
2. `src/gbdn/synthetic.py::sphere_graph_data` silently builds an asymmetric
   directed-kNN operator and applies `eigh`, bypassing the validated graph
   boundary. A probe found relative asymmetry `0.228` and eigensystem residual
   `0.161`.
3. Public `GBDNTight` analysis/synthesis is not bound to the dense oracle by a
   mandatory regression. An independent probe shows the current code matches,
   so this is a coverage hole rather than an observed formula bug.
4. GA-10 checks manual sentinels rather than public model output against an
   independently assembled residual-first tuple; full R3 consumer integration
   is a separate Gate-wide guard.
5. GA-14 does not construct actual exact/finite factors or check the true
   `(epsilon_K/2)||h||` term with `epsilon_K=||T_tilde-T||_op`.
6. GA-25's stable exact witness passes, but it does not report its singular
   spectrum/condition/residual and omits the mandatory ill-conditioned case.
   Finite-logit and finite-`K` studies are broader checks, not exact-row defects.
7. GA-27 checks an off-axis, noncancelled one-factor GBDN pole, but not an
   executable frozen comparator's reduced pole multiset or scale/order scope.
8. Finite-frame tests remain path-only, and finite diagnostic pole fields need
   explicit exact-target semantics.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `reviews/gate_a_final_independent_review.md` | Full adversarial review, 36-row adjudication, claim classifications, and minimal repairs | Yes; review only |
| `handoffs/REV-GATEA-FINAL-1.md` | Reviewer handoff and reproducibility evidence | Yes; handoff only |

No source, test, paper, result, notebook, legacy, or generated artifact was
edited.

## Scientific impact

- **Claims enabled:** none for external promotion until re-review; the exact
  theorem core remains scientifically viable.
- **Claims narrowed:** finite mapped poles are target geometry only; T-F is
  exact/continuum/reduced-pole only; T-G is aligned fixed-root operator
  stability; `DK` uses the stated complex-SpMV convention.
- **Claims rejected:** carried-state non-dissipation, universal target
  sensitivity, oversquashing mitigation from tightness, and any approximation
  efficiency claim from the analytic bound.
- **Paper impact:** the later `a19e9cd`/`708837e` first-kind attribution repair
  is mathematically sound; Gate blocking is independent of that former
  citation issue.

## Evidence

### Tests

```text
Gate-only command:
  canonical .venv Python with PYTHONPATH=<review worktree>/src
  pytest tests/test_gate_a.py tests/test_gate_a_core_slice.py
         tests/test_gate_a_exact_slice.py tests/test_gate_a_fixture_matrix.py
         tests/test_gate_a_approximation.py tests/test_gate_a_closeout.py
         -q -p no:cacheprovider
Result: 427 passed.

Full repository test command:
  pytest tests -q -p no:cacheprovider
Result: 447 passed, 2 upstream torch.jit deprecation warnings.

Reporter:
  python scripts/report_gate_a.py
Result: all GA IDs execute/pass; accepted=false; status=BLOCKED;
        35/36 IDs have no structured residual; only GA-23 has one.
```

### Independent probes

```text
Public Tight analysis/synthesis versus independent dense polynomial oracle:
  max component relative error 3.41e-16
  synthesis relative disagreement 1.99e-16
  reconstruction relative error 3.049e-3
  measured frame defect 3.473e-3
  additive residual 1.05e-16

Directed sphere helper, n=50, k=4:
  relative Laplacian asymmetry 0.228035
  relative eigensystem residual 0.161245

Clustered Product-sum diagnostic:
  minimum singular value 9.98e-17
  condition number 5.01e16
```

### Theory

- The frozen proof ledger was independently checked; no new counterexample
  was found.
- The later first-kind aliasing rule at `a19e9cd` is correct for
  `N=K+1`, `m=2qN+s`, `0<=s<2N`, and yields the displayed
  `4 M_rho rho^{-K}/(rho-1)` bound from the cited coefficient estimate.

## Acceptance criteria

| Criterion | Result |
|---|---|
| Read all frozen math/contracts, canonical source/tests/reporter, relevant handoffs, and theory context | PASS |
| Run full Gate-A suite | PASS — 427 tests |
| Run full repository suite | PASS — 447 tests |
| Run machine-readable reporter | PASS as a tool; reporter verdict BLOCKED |
| Classify every GA row | PASS — one ACCEPT, 30 CONDITIONAL, five REJECT |
| Verify equations and proof assumptions independently | PASS |
| Verify public analysis/synthesis correspondence | PASS as read-only probe; missing committed regression |
| Required per-row provenance | FAIL — 35/36 missing |
| Canonical graph contract package-wide | FAIL — directed sphere helper bypass |
| Exact Product-sum conditioning report and reduced-pole comparator binding | FAIL |
| Gate A accepted | **FAIL / BLOCKED** |

## Minimal re-review prerequisites

1. Repair/quarantine `synthetic.py` and `peel.py` graph/convention bypasses.
2. Emit and validate complete `gate_a_metrics` for every row; derive coverage
   from executed records and fail acceptance mode loudly.
3. Commit the minimal GA-10 public-output/independent-tuple/permutation test and
   the broader Tight synthesis/readout/artifact R3 integration guards.
4. Repair GA-14 with true operator epsilon; make GA-25 report stable and
   deliberately ill-conditioned exact conditioning; encode and reduce the
   frozen GA-27 comparator family.
5. Add non-path finite-frame fixtures and explicit exact-target pole metadata.
6. Rerun from a clean commit and obtain a second independent review.

## Known limitations

- This was not a new literature search; T-F comparator scope relies on the
  repository's completed primary-source audit.
- The public-API and conditioning probes were diagnostic and read-only, not
  substitutes for committed deterministic tests.
- The implementation verdict applies to `e5edf72`; later paper-only commits
  were inspected only as claim context.
- No experiment result or H100 artifact was reviewed or authorized.

## Reproduction instructions

Create a clean worktree at `e5edf72`, set `PYTHONPATH` to its `src` directory,
and run the Gate, full-suite, and reporter commands above. The complete
row-by-row evidence and probe descriptions are in
`reviews/gate_a_final_independent_review.md`.

## Rollback

Revert the single `REV-GATEA-FINAL-1` review commit. It contains only this
handoff and the independent review.
