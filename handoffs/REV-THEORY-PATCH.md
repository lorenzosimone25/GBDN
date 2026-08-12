# REV-THEORY-PATCH Handoff

## Task

- **Task ID:** REV-THEORY-PATCH
- **Agent:** Independent theory-heavy Reviewer
- **Branch:** `agent/reviewer/REV-THEORY-PATCH`
- **Starting commit:** `7b7909899e65d1f86bfc523e452c15c0ccf97e53`
- **Ending commit:** the commit containing this handoff (reported on delivery)
- **Status proposed:** BLOCKED

## Objective

Independently audit every theorem, assumption, proof, realization boundary,
reconstruction statement, coefficient-order assertion, phenomenon claim, and
cross-reference in the MATH-002--011 paper patch. Seek counterexamples, make
no source or paper edits, and commit only the independent review and handoff.

## Summary

The abstract theorem core is conditionally sound. The review independently
re-derived the phase/pole formula, pointwise and operator Parseval identities,
complete-map isometry, weighted conservation law, heterogeneous multilevel
frame recurrence, finite-spectrum Product-sum basis result, generic
reduced-pole separation, fixed-root resolvent perturbation bound, locality,
and the negative source-to-target sensitivity boundary. No fatal algebraic
counterexample was found.

Paper promotion is blocked. At the exact reviewed commit, the paper falsely
states that implementation/artifact order is residual-first while the public
`components` property and readout are carry-first. It also says asymmetric
graph input is rejected while the current constructor performs no such
validation or recorded preprocessing. The 36-row Gate-A suite is not complete.
Additional mandatory fixes concern the omitted `mu in [0,2]` constraint,
undefined approximate synthesis notation and terminal condition, a collision
between Fourier and synthesis hats, unconditioned `DK` cost wording, missing
Chebyshev attribution, and page-budget triage.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `reviews/theory_patch_independent_review.md` | Independent theorem-by-theorem review, counterexample search, classifications, and mandatory fixes | Yes; review only |
| `handoffs/REV-THEORY-PATCH.md` | Evidence and orchestrator handoff | Yes |

## Scientific impact

- Claims enabled: none yet; the proof patch is suitable for Gate-A testing
  after the correspondence fixes.
- Claims narrowed: T-E depends essentially on `M_rho`; T-F is continuum-only
  and generic; T-G is an aligned fixed-root operator result; T-H cost depends
  on the realized recurrence.
- Claims rejected: carried-state non-dissipation, universal target influence,
  anti-oversmoothing from isometry alone, and oversquashing mitigation from
  tightness.
- Paper sections affected: preliminaries, method, theory, proof appendix, and
  ultimately the abstract/introduction/results/conclusion claim state.

## Evidence

### Proofs

- theorem/lemma: Proposition 1, T-A, additive reconstruction, T-B, T-C,
  spectral selection/recovery, T-D--T-H, Product-sum interpolation, and the
  negative sensitivity proposition.
- assumptions: finite self-adjoint operator; roots fixed independently of
  analyzed signal; direct-sum coefficient norm; true operator errors for
  finite-frame bounds; commuting positive weights for T-B; analytic ellipse
  and finite `M_rho` for T-E; reduced continuum pole hypotheses for T-F;
  aligned vertex spaces and fixed roots for T-G.
- proof location: `papers/revision/sections/A_appendix_proofs.tex`; independent
  audit in `reviews/theory_patch_independent_review.md`.
- counterexamples checked: angular anchor is not exact center; additive
  reconstruction without tightness; carry zero-mode annihilation;
  noncommuting node projector; repeated-eigenspace limitation; finite-spectrum
  polynomial matching; Product-sum ill-conditioning; connected/disconnected
  target-sensitivity loss; finite-hop zeros; information-discarding readout.

### Tests

```text
command: root .venv Python with PYTHONPATH=<review worktree>/src,
         python -m pytest tests/test_gate_a.py -q -p no:cacheprovider
result: PASS, 10 passed with 3 warnings; regression subset only, not Gate A.

command: root .venv Python with PYTHONPATH=<review worktree>/src,
         python -m pytest tests -q -p no:cacheprovider
result: PASS, 30 passed with 3 warnings; only 10 are old Gate-A tests.

command: 2,000 randomized noncommuting finite-frame cascades, depths 1--6
result: no violation; maximum observed defect / Delta_D approximately 0.970.
        Diagnostic adversarial search only, not theorem evidence.

command: pdflatex (draft graphics), bibtex, pdflatex, pdflatex
result: PASS; no undefined references/citations after BibTeX; 21 pages; two
        absent pre-existing figure warnings and underfull boxes remain.

command: git diff 7b790989^ 7b790989 --check
result: PASS.
```

### Experiment artifacts

- run IDs: none
- result paths: none
- aggregate paths: none
- generated paper assets: none committed

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Read all assigned governing and patch files in full | PASS | Review scope and theorem ledger in independent report |
| Audit every theorem formula and proof | PASS | Theorem-by-theorem classification table |
| Seek counterexamples | PASS | Counterexample and randomized recurrence checks |
| Exact versus Chebyshev semantics audited | PASS | Dedicated realization section in review |
| Residual-first implementation correspondence holds | FAIL | `src/gbdn/model.py:30--31,206` are carry-first |
| Graph premise enforced by implementation | FAIL | `src/gbdn/layers.py:25--45` lacks rejection/recorded transform |
| Reconstruction distinction correct and unambiguous | FAIL | Missing terminal condition and exact/approximate notation; hat collision |
| Frame recurrence mathematically correct | PASS | Independent derivation and adversarial diagnostic |
| Oversmoothing/oversquashing boundary safe | PASS | Positive claims rejected; constructive witnesses retained |
| Required Gate-A evidence accepted | FAIL | Only 10 old Gate-A tests exist/pass; GA-00--GA-35 incomplete |
| LaTeX and cross-references compile | PASS | Full draft-graphics/BibTeX build |
| Only requested review artifacts changed | PASS | Final status/commit tree |

## Known limitations

- This was a theorem and paper-correspondence review, not a literature novelty
  audit. No baseline-specific T-F corollary is accepted.
- The randomized finite-frame search is not proof or Gate-A evidence.
- The build used draft graphics because two pre-existing figure files are
  absent in the isolated worktree.
- The engineering order/graph fixes were being developed elsewhere and were
  not present in the reviewed commit; the verdict applies to `7b790989`.

## Reviewer questions

1. After engineering fixes land, do semantic order tests cover readout and
   artifact serialization, not only analysis output?
2. Will the graph preprocessor record input/output hashes and the exact
   reciprocal-mean, duplicate, self-loop, and isolated-node policy?
3. Can T-E be tied to measured true operator error without promoting the
   ellipse parameter as a sufficient predictor?
4. Does the primary-source novelty audit identify a nonvacuous comparator
   locus for T-F, or should T-F be omitted?
5. Which three or four results remain in the main paper after page-budget
   compression?

## Conflicts or decisions needed

The paper patch claims two implementation properties that are not present in
its base tree. The orchestrator must merge verified engineering fixes before
promoting or externally circulating the prose. T-F must remain generic until
the independent novelty audit reports. No change to the frozen scientific
identity is recommended.

## Reproduction instructions

From the review worktree, point the canonical virtual environment at this
worktree's `src`, then run the test commands above. From
`papers/revision`, run draft-graphics `pdflatex`, `bibtex`, and two further
`pdflatex` passes. Inspect the named source lines for the two stop-line
paper--implementation mismatches.

## Rollback

Revert the single `REV-THEORY-PATCH` commit. It contains only the review and
handoff, with no source, paper, test, result, or generated-artifact changes.
