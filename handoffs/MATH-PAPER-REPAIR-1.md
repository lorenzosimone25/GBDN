# MATH-PAPER-REPAIR-1 Handoff

## Task

- **Task ID:** MATH-PAPER-REPAIR-1
- **Role:** Mathematical Researcher
- **Branch:** `agent/math/MATH-PAPER-REPAIR-1`
- **Starting commit:** `690b917c3a20a3687de4438fae4eddee8da0cf1f`
- **Integrated draft:** `7b7909899e65d1f86bfc523e452c15c0ccf97e53`
- **Ending commit:** the commit containing this handoff (reported on delivery)
- **Status proposed:** REVIEW; mathematically repaired, still PAPER-BLOCKED

## Objective

Integrate the contract-aligned theory draft into the current orchestrator base,
repair every manuscript-level issue required by the independent theory review,
reconcile the prose with the current canonical API, and leave code, tests,
results, bibliography, and legacy artifacts untouched.

## Files changed

| File | Change |
|---|---|
| `papers/revision/sections/02_preliminaries.tex` | Defines the open disk; records strict graph validation; freezes center--width bounds and target-pole-margin semantics; separates radial mapped centers from interval maxima. |
| `papers/revision/sections/03_method.tex` | Preserves residual-first order; fully defines exact and approximate synthesis recursions, terminal states, and channel notation; conditions sparse-operation counting on the canonical recurrence. |
| `papers/revision/sections/04_theory.tex` | Repairs root hypotheses, Chebyshev target-pole wording, frame-bound terminology, and analyzed-coefficient reconstruction scope; compresses the main theory to the central claim chain; keeps the negative oversmoothing/oversquashing boundary. |
| `papers/revision/sections/A_appendix_proofs.tex` | Moves supporting results out of the main body; repairs direct-sum norms and phase notation; narrows T-F; conditions T-H; handles the one-eigenvalue Product-sum case; aligns proofs with exact/approximate synthesis notation. |
| `handoffs/MATH-PAPER-REPAIR-1.md` | Records evidence, remaining gates, and rollback. |

No source, test, result, bibliography, generated paper asset, or legacy file was
edited.

## Mandatory-review disposition

| Review requirement | Disposition |
|---|---|
| Residual-first paper/API correspondence | Reconciled. Current `TightAnalysisOutput.components`, concatenation, and readout use `(r_0,...,r_{D-1},h_D)`. |
| Strict graph premise | Reconciled. Current core rejects invalid direct adjacency and requires a hash-bearing validated Laplacian token; reciprocal-mean symmetrization is separate and recorded. |
| Center--width semantics | Fixed with `mu in [0,2]`, finite frozen positive gamma bounds, mapped pole `mu-i gamma`, and emitted interval margin `gamma`. |
| Synthesis notation | Fixed with `h_l^{syn}`, explicit terminal state, separately defined approximate channels, and approximate terminal/backward recursion. |
| Approximate reconstruction scope | Fixed. `Delta_D ||h||` applies to adjoint synthesis of coefficients produced by the same approximate analysis, not arbitrary tuples. |
| Sparse cost | Fixed. Exact `DK` applies only to the canonical full per-level recurrence without early truncation or cross-level reuse; one complex application equals two real-channel applications. |
| Chebyshev theorem | Fixed node convention and reduced nonremovable target-pole hypotheses; the missing exact source is explicitly paper-blocking rather than guessed. |
| Norm/disk/angle/frame terminology | Fixed with direct-sum analysis norms, an explicit open-disk definition, distinct `psi` and `vartheta`, and frame bounds (squared singular-value bounds). |
| T-F scope | Moved to the appendix and limited to generic conditional exact-target nonidentity on a continuum. It makes no finite-spectrum, approximation, efficiency, trainability, or superiority claim and names no baseline. |
| Page triage | Weighted Parseval, node-pair and packet bounds, Product-sum interpolation, T-F, perturbation, and detailed locality/cost statements moved to the appendix. Main theory is now pages 4--5 in the draft build. |

## Verification

### Current implementation correspondence

- `src/gbdn/model.py` exposes the residual-first component tuple and uses it in
  concatenation/readout.
- `src/gbdn/core.py` implements strict graph validation, separate recorded
  reciprocal-mean preprocessing, and hash-bearing validated operators.
- The canonical sparse synthesis implementation applies the adjoint of the
  finite analysis; the manuscript no longer calls it a general inverse.

### Tests

```text
command: root virtual-environment Python with PYTHONPATH=<repair worktree>/src,
         python -m pytest tests -q -p no:cacheprovider
result:  PASS, 140 passed, 2 third-party torch.jit deprecation warnings

command: same environment,
         python -m pytest tests/test_gate_a_core_slice.py
                          tests/test_gate_a_exact_slice.py
                          tests/test_gate_a_approximation.py
                          -q -p no:cacheprovider
result:  PASS, 110 passed
```

These test runs verify correspondence at the assigned base; they do not by
themselves constitute final Gate-A acceptance. In particular, the assigned
base does not expose an explicit `GA-23` binding, and the immutable Gate-A
report plus independent acceptance review remain outstanding.

### Citation scan

```text
command: citation-verifier scan_citations.py papers/revision
result:  21 bibliography keys; 20 cited keys / 34 occurrences;
         0 placeholders; 0 duplicate BibTeX keys
```

No verified bibliography entry establishes the exact first-kind Chebyshev
interpolation estimate
`4 M_rho rho^{-K} / (rho-1)` with the stated node convention. Because the
authorized patch excludes `refs.bib`, no citation was invented or borrowed
from an adjacent graph-filter paper. T-E remains PAPER-BLOCKED until a citation
reviewer adds and verifies the exact approximation-theory source.

### LaTeX

```text
command: pdflatex with the available root figure directory injected,
         bibtex, pdflatex, pdflatex
result:  PASS; 23 pages total including references, appendix, and checklist;
         0 undefined references/citations; 0 duplicate-label warnings;
         0 missing-figure warnings
```

The main theory occupies pages 4--5, experiments begin on page 6, the
limitations/conclusion begins on page 10, and the appendix begins on page 12.
The isolated worktree lacks its own copies of the two mechanism figure PDFs,
so the build reads the available files from the root worktree without copying
or modifying them. Only underfull-box warnings remain; there are no overfull
boxes.

## Theorems still PAPER-BLOCKED

1. **All claim-bearing theory:** final Gate-A artifact coverage, immutable
   provenance, and independent acceptance review are not complete. Passing the
   local test suite is necessary but not sufficient.
2. **T-E:** exact primary-source attribution for the interpolation theorem is
   absent from the verified bibliography.
3. **T-F as a contribution:** the generic nonidentity lemma is proved only
   under its reduced-pole and continuum assumptions. It remains supporting
   theory and cannot imply approximation or empirical superiority; Gate C must
   establish whether the distinction matters.
4. **Practical oversmoothing/oversquashing claims:** no positive inference is
   admitted from complete-map isometry. Dedicated depth and source-to-target
   experiments remain required.
5. **Submission-wide promotion:** the abstract, introduction, experiments, and
   conclusion remain outside this patch's ownership. Their present-tense claim
   language and obsolete test inventory must be reconciled only after Gate A.
6. **Page budget:** theory triage is complete, but the conclusion still begins
   on page 10; submission-wide compression remains necessary.

## Scientific consequence

The strongest defensible main-text chain is now explicit: learned mapped root
geometry converts phase into complementary channels; the exact complete
residual-first coefficient map is an isometry with adjoint reconstruction;
finite Chebyshev realization has a measurable heterogeneous frame defect; and
none of these identities alone establishes resistance to oversmoothing or
oversquashing. Supporting results remain available without being promoted as
headline novelty.

## Recommended next steps

1. Have the independent theory reviewer re-review this bounded patch against
   the current API rather than the stale implementation snapshot.
2. Add a verified exact source for the Chebyshev interpolation theorem through
   the citation-review workflow, then cite it at T-E and in its proof.
3. Complete the explicit GA-00--GA-35 binding and immutable Gate-A report.
4. After Gate A is independently accepted, reconcile the abstract,
   introduction, experiment inventory, conclusion, and visible draft marker.

## Rollback

Revert the single `MATH-PAPER-REPAIR-1` commit. It changes only the four
authorized manuscript sections and this handoff.
