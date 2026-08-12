# MATH-001 Agent Handoff

## Task

- **Task ID:** MATH-001
- **Agent:** Mathematical Researcher
- **Branch:** agent/math/MATH-001
- **Starting commit:** baaa6183bc607c341610b366ec38fc25ab09888f
- **Ending commit:** This handoff's commit; SHA reported to the orchestrator.
- **Status proposed:** REVIEW

## Objective

Formalize the frozen Gate A mathematics: classify every current and candidate theorem, provide proofs or precise proof sketches, register counterexamples, and bind each admissible claim to an executable observable and tolerance. Do not edit paper, source, tests, or result artifacts.

## Summary

The exact mathematical core is retained and narrowed. The deliverables prove the exact unitary split, pointwise and weighted Parseval identities, complete multilevel conditioning and adjoint synthesis, limited nodewise lower bound, finite-order multilevel frame defect, corrected root localization, finite-spectrum Product-sum interpolation, conditional movable-pole separation, fixed-root perturbation stability, permutation equivariance, and locality/SpMV complexity.

The root semantics now match the frozen contract: radial-polar roots are unrestricted canonical roots; rho phi(mu) is only an angular anchor; phi(mu+i gamma) is the optional exact center-width family.

The counterexample register rejects carried-state non-dissipation, universal anti-oversmoothing, every-target sensitivity, and oversquashing mitigation from tightness. The test contract specifies 36 mandatory Gate A checks over multiple graph families, depths, and realizations.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| math/theorem_ledger.md | Status, scope, novelty, evidence, and paper-admission ledger. | Yes |
| math/proof_audit.md | Rigorous statements and proofs/proof sketches under frozen semantics. | Yes |
| math/counterexamples.md | Fifteen explicit claim-boundary counterexamples. | Yes |
| math/theorem_to_test_contract.md | Mandatory observables, fixtures, tolerances, and Gate rule. | Yes |
| handoffs/MATH-001.md | This handoff. | Yes |

## Scientific impact

- Claims enabled: exact pointwise paraunitary partition; weighted spectral Parseval; condition-one complete analysis; explicit finite-order multilevel defect; corrected mapped-pole localization; conditional pole-family separation; resolvent perturbation stability; polynomial locality and cost.
- Claims narrowed: exact versus chebyshev-K; analyzed lift versus raw input; complete tuple versus carried state; spectral weights versus node projectors; continuum pole separation versus finite-spectrum interpolation.
- Claims rejected: angular anchor is exact center; additive reconstruction proves tightness; tightness prevents practical oversmoothing; tightness lower-bounds specified source-target influence; tightness solves oversquashing.
- Paper sections affected: future Math Agent patch should touch preliminaries, method reconstruction, theory, proof appendix, Gate A experiments, and limitations. No paper file was edited in this task.

## Evidence

### Proofs

- theorem/lemma: all entries E1--E9, R1--R3, T-A--T-H, and X1--X5.
- assumptions: finite self-adjoint \(L\), spectrum in \([0,2]\), admissible roots, canonical coefficient order, explicit realization tag.
- proof location: math/proof_audit.md.
- counterexamples checked: math/counterexamples.md.

### Tests

No implementation test was run or changed; this was a documentation-only mathematical task. The executable acceptance suite is fully specified in math/theorem_to_test_contract.md.

Repository-scope validation:

    git diff --cached --name-only

must list only the five assigned Markdown files.

### Experiment artifacts

- run IDs: none.
- result paths: none.
- aggregate paths: none.
- generated paper assets: none.

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Every current result classified | PASS | theorem_ledger.md |
| T-A through T-H resolved | PASS | theorem_ledger.md and proof_audit.md |
| Corrected graph/root semantics used | PASS | all four math files |
| Proof or precise proof sketch supplied | PASS | proof_audit.md |
| Counterexamples actively documented | PASS | counterexamples.md |
| Observable and tolerance for every promoted theorem | PASS | theorem_to_test_contract.md |
| No paper/source/test edits | PASS | scoped staged-file check |
| Gate A executable evidence exists | FAIL / downstream blocker | Tests remain to be implemented and independently reviewed |

## Known limitations

- Mathematical correctness does not establish novelty; the Reviewer must verify graph-QMF, framelet, Cayley, unitary-convolution, and wavelet distinctions.
- The movable-pole separation theorem is conditional on the comparison family's reduced pole locus and equality on a continuum.
- The graph perturbation result fixes roots and aligned vertices; it is not a retraining or graph-matching theorem.
- The finite-order frame bound is conservative and awaits observed-versus-predicted tests.
- Practical oversmoothing and oversquashing remain empirical-only after Gate A.

## Reviewer questions

1. Is the pointwise/weighted Parseval package sufficiently nontrivial for main text once prior filter-bank work is considered?
2. Is the reduced-pole description of the frozen Cayley comparison family exact, including learned scale and real-response conjugate terms?
3. Should the epsilon-only multilevel frame theorem be supplemented by the sharper scalar spectral recurrence in the main paper?
4. Are any additional assumptions needed for the normalized-Laplacian perturbation experiment beyond the operator-level theorem?
5. Does any attempted stronger target-block theorem survive C4--C6? The Math Agent finds no universal positive statement.

## Conflicts or decisions needed

- The optional exact center-width parameterization is mathematically valid but remains an ablation; do not silently replace the canonical radial family.
- The engineering graph policy must choose explicit rejection or deterministic symmetrization and record that choice.
- The Reviewer must adjudicate theorem prominence separately from correctness.

## Reproduction instructions

Read the deliverables in this order:

1. math/theorem_ledger.md
2. math/proof_audit.md
3. math/counterexamples.md
4. math/theorem_to_test_contract.md

Then implement the mandatory GA-00 through GA-35 suite without weakening tolerances or substituting one-vector checks for operator norms.

## Rollback

Revert this task commit. It adds only the five assigned Markdown files and does not alter frozen code, paper, tests, or artifacts.
