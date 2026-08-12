# Claim-to-evidence matrix

This matrix is an admission ledger, not a list of intended claims. A mathematical
argument, a passing regression test, and paper-admissible evidence are separate
states. The controlling assumptions and acceptance criteria are in
`sub_plans/01_SCIENTIFIC_CONTRACT.md` and
`math/theorem_to_test_contract.md`.

| Claim | Class | Required implementation / observable | Current evidence | Admission state |
|---|---|---|---|---|
| Root admissibility, mapped zero/pole geometry, and Lorentzian phase law | THEOREM | Radial and optional bounded center-width roots; GA-01/02/23 | Proof draft and executable rows pass; final provenance and review remain open | PAPER-BLOCKED |
| Exact factor unitarity and one-level complementary Parseval split | THEOREM | Independent dense oracle; GA-03/04 over the required fixtures | Required graph/root matrices pass locally | PAPER-BLOCKED pending provenance and review |
| Pointwise multilevel partition | THEOREM | Effective scalar atoms; GA-05 on an interval and graph spectra | Proof draft and required executable spectra pass locally | PAPER-BLOCKED pending provenance and review |
| Complete exact multilevel isometry, conditioning, and adjoint synthesis | THEOREM | Residual-first block analysis; GA-06/07/09/10 | Required graph/depth/root matrix and semantic coefficient-order rows pass locally | PAPER-BLOCKED pending provenance and review |
| Additive reconstruction | THEOREM (algebraic) | Exact, polynomial, and deliberately nonunitary shared factors; GA-08 | Focused GA-08 tests pass | Supporting result only; full review pending |
| Weighted spectral Parseval conservation | THEOREM | Commuting weights and noncommuting counterexample; GA-11/12 | Proof, positive row, and counterexample row pass locally | PAPER-BLOCKED pending provenance and review |
| Spectral energy separation and complex packet recovery | THEOREM | Whole-eigenspace projectors; GA-13/14 | Proof and executable rows pass locally | PAPER-BLOCKED pending provenance and review |
| Finite-Chebyshev operator error and multilevel frame defect | THEOREM | True full-operator errors and predicted `Delta_D`; GA-18--22 | Repaired approximation, synthesis, frame, and degree-128 oracle rows pass locally; the first-kind interpolation constant is now explicitly derived from a verified coefficient bound | PAPER-BLOCKED pending provenance and review |
| Product-sum finite-spectrum interpolation | THEOREM (limited) | Nonzero admissible roots, rank, singular values, conditioning; GA-25/26 | Nonzero-root existence, generic rank, and conditioning rows pass locally | PAPER-BLOCKED pending provenance and review |
| Generic reduced-pole continuum separation | THEOREM (conditional) | Reduced pole multisets; GA-27; primary-source family audit | Conditional proof, symbolic cancellation row, and family-locus audit exist | PAPER-BLOCKED; no baseline-specific superiority corollary |
| Fixed-root aligned graph-operator perturbation | THEOREM (conditional) | Resolvent margin and observed bound; GA-28 | Proof and aligned fixed-root bound rows pass locally | PAPER-BLOCKED pending provenance and review |
| Polynomial locality and sparse cost | THEOREM | Hop support and instrumented SpMV count; GA-29/30 | Repaired finite-hop and complex sparse-application rows pass locally | PAPER-BLOCKED pending provenance and review |
| Complete-map global sensitivity and its target-specific limitation | THEOREM + COUNTEREXAMPLE | GA-31--34 | Global norm identity and connected, disconnected, carried-state, and finite-hop counterexamples pass locally | PAPER-BLOCKED pending provenance and review |
| Phase-sensitive objectives improve controlled recovery | EXPERIMENT | Immutable per-seed runs, prespecified representative, aggregate provenance | Existing artifact stores aggregates and a selected best run only | DIAGNOSTIC; not claim-admissible |
| Target mapped-pole geometry predicts finite-order approximation difficulty | EXPERIMENT | Immutable radius/angle/degree sweep with regenerated aggregate | Existing compact aggregate is not bound to per-run identities | DIAGNOSTIC; not claim-admissible |
| Legacy H100 benchmark values | EXPERIMENT / LIMITATION | Frozen artifacts and independent verifier | Strict verifier reports 28 problems; baselines and protocol are not confirmatory | DIAGNOSTIC ONLY |
| Benchmark superiority, practical anti-oversmoothing, or oversquashing mitigation | EXPERIMENT | Gates C, E, and F under official protocols | No admissible evidence | UNSUPPORTED; absent from contribution claims |

## Current gate snapshot

- The local suite passes 447 tests.  The Gate-A collector maps 410 parametrized
  nodes to every GA-00--GA-35 row and reports no declared graph, depth, root,
  degree, or row-matrix gap.
- Gate A still requires complete row-level numerical provenance and independent
  theorem-to-test acceptance.  Passing tests and complete ID coverage are not
  sufficient for paper admission.
- No abstract, introduction, figure caption, result table, or conclusion may call
  a paper-blocked row verified.
- Exact rational targets and finite Chebyshev realizations must remain distinct in
  every artifact and sentence.
