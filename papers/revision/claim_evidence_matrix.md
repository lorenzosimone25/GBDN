# Claim-to-evidence matrix

This matrix is an admission ledger, not a list of intended claims. A mathematical
argument, a passing regression test, and paper-admissible evidence are separate
states. The controlling assumptions and acceptance criteria are in
`sub_plans/01_SCIENTIFIC_CONTRACT.md` and
`math/theorem_to_test_contract.md`.

| Claim | Class | Required implementation / observable | Current evidence | Admission state |
|---|---|---|---|---|
| Root admissibility, mapped zero/pole geometry, and Lorentzian phase law | THEOREM | Radial and optional bounded center-width roots; GA-01/02/23 | Complete proof draft; executable coverage incomplete | PAPER-BLOCKED |
| Exact factor unitarity and one-level complementary Parseval split | THEOREM | Independent dense oracle; GA-03/04 over the required fixtures | Focused GA-03/04 tests pass locally | PAPER-BLOCKED pending fixture matrix and review |
| Pointwise multilevel partition | THEOREM | Effective scalar atoms; GA-05 on an interval and graph spectra | Complete proof draft; GA-05 not yet accepted | PAPER-BLOCKED |
| Complete exact multilevel isometry, conditioning, and adjoint synthesis | THEOREM | Residual-first block analysis; GA-06/07/09/10 | Residual-first API and GA-10 pass; remaining IDs incomplete | PAPER-BLOCKED |
| Additive reconstruction | THEOREM (algebraic) | Exact, polynomial, and deliberately nonunitary shared factors; GA-08 | Focused GA-08 tests pass | Supporting result only; full review pending |
| Weighted spectral Parseval conservation | THEOREM | Commuting weights and noncommuting counterexample; GA-11/12 | Complete proof and counterexample drafts; tests incomplete | PAPER-BLOCKED |
| Spectral energy separation and complex packet recovery | THEOREM | Whole-eigenspace projectors; GA-13/14 | Complete proof draft; tests incomplete | PAPER-BLOCKED |
| Finite-Chebyshev operator error and multilevel frame defect | THEOREM | True full-operator errors and predicted `Delta_D`; GA-18--22 | Full sparse-versus-dense polynomial agreement passes in GA-19; remaining IDs incomplete | PAPER-BLOCKED |
| Product-sum finite-spectrum interpolation | THEOREM (limited) | Nonzero admissible roots, rank, singular values, conditioning; GA-25/26 | Zero-root witness exists only as regression evidence | PAPER-BLOCKED |
| Generic reduced-pole continuum separation | THEOREM (conditional) | Reduced pole multisets; GA-27; primary-source family audit | Proof draft exists; baseline-specific novelty review incomplete | PAPER-BLOCKED |
| Fixed-root aligned graph-operator perturbation | THEOREM (conditional) | Resolvent margin and observed bound; GA-28 | Complete proof draft; test incomplete | PAPER-BLOCKED |
| Polynomial locality and sparse cost | THEOREM | Hop support and instrumented SpMV count; GA-29/30 | Complete proof draft; tests incomplete | PAPER-BLOCKED |
| Complete-map global sensitivity and its target-specific limitation | THEOREM + COUNTEREXAMPLE | GA-31--34 | Constructive path, disconnected, locality, and carried-state counterexamples drafted | PAPER-BLOCKED |
| Phase-sensitive objectives improve controlled recovery | EXPERIMENT | Immutable per-seed runs, prespecified representative, aggregate provenance | Existing artifact stores aggregates and a selected best run only | DIAGNOSTIC; not claim-admissible |
| Target mapped-pole geometry predicts finite-order approximation difficulty | EXPERIMENT | Immutable radius/angle/degree sweep with regenerated aggregate | Existing compact aggregate is not bound to per-run identities | DIAGNOSTIC; not claim-admissible |
| Legacy H100 benchmark values | EXPERIMENT / LIMITATION | Frozen artifacts and independent verifier | Strict verifier reports 28 problems; baselines and protocol are not confirmatory | DIAGNOSTIC ONLY |
| Benchmark superiority, practical anti-oversmoothing, or oversquashing mitigation | EXPERIMENT | Gates C, E, and F under official protocols | No admissible evidence | UNSUPPORTED; absent from contribution claims |

## Current gate snapshot

- The local suite passes 47 tests, but focused accepted coverage currently spans
  only GA-00, GA-03, GA-04, GA-08, GA-10, GA-16, GA-17, GA-19, and GA-35.
- Gate A requires every GA-00--GA-35 row, the prescribed graph/depth/root fixture
  matrix, a machine-readable report, and independent theorem-to-test review.
- No abstract, introduction, figure caption, result table, or conclusion may call
  a paper-blocked row verified.
- Exact rational targets and finite Chebyshev realizations must remain distinct in
  every artifact and sentence.
