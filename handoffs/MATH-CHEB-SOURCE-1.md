# MATH-CHEB-SOURCE-1 Handoff

## Task

- **Task ID:** MATH-CHEB-SOURCE-1
- **Role:** Mathematical Researcher / citation audit
- **Branch:** `agent/math/MATH-CHEB-SOURCE-1`
- **Starting commit:** `e5edf72bfe2920834cfcbb8f4fec53935e6b719f`
- **Theory dependency:** `5599a65` (locally cherry-picked as `c18cc32`)
- **Ending commit:** the subsequent bounded commit containing this handoff
- **Status proposed:** REVIEW; attribution block resolved, Gate-A promotion still pending

## Decision

Option A is valid.  For the exact first-kind roots
`cos((j+1/2) pi/(K+1))` used by the canonical implementation, the degree-$K$
interpolant obeys

```text
||g - p_K||_infinity <= 4 M_rho rho^{-K} / (rho - 1).
```

No diagnostic or test constant needs to change.  The published source used for
the one external ingredient is a coefficient theorem.  The manuscript now
derives the first-kind aliasing itself, because the same book's interpolation
theorem is stated for its default second-kind grid and therefore is not a
direct citation for the code's nodes.

## Exact primary source

- Lloyd N. Trefethen, ``Convergence for Analytic Functions,'' Chapter 8,
  pp. 55--62, in *Approximation Theory and Approximation Practice, Extended
  Edition*, SIAM, 2019.
- Result used: **Theorem 8.1**, the bound
  $|a_m|\leq 2M_\varrho\varrho^{-m}$ for analytic-function Chebyshev
  coefficients.
- Chapter DOI: `10.1137/1.9781611975949.ch8`.
- Archival URL:
  <https://epubs.siam.org/doi/10.1137/1.9781611975949.ch8>.
- Author-hosted source inspected for theorem text and conventions:
  <https://people.maths.ox.ac.uk/~trefethen/trefethen_sample.pdf>.  This sample
  has different pagination from the extended edition; the bibliography uses
  the archival chapter page range and DOI.

## Code-convention audit

`src/gbdn/spectral.py` does all three relevant operations consistently:

1. `chebyshev_nodes` returns
   $1+\cos((j+1/2)\pi/(K+1))$, $j=0,\ldots,K$;
2. `dct_synthesis` applies the corresponding first-kind discrete cosine
   transform and halves the constant coefficient;
3. `evaluate_chebyshev` evaluates the unprimed expansion
   $\sum_{k=0}^K c_kT_k(\lambda-1)$.

Thus $N=K+1$ is the number of nodes and $K$ is the polynomial degree.  The
diagnostic uses the same indexing and returns
`4 * M_rho * rho**(-K) / (rho - 1)`.

## Derivation added to the appendix

Let $N=K+1$, $x_j=\cos((j+1/2)\pi/N)$, and $I_K$ be interpolation at those
nodes.  For $m=2qN+s$, $0\leq s<2N$, evaluation at the grid gives

```text
I_K T_m = (-1)^q T_s             for 0 <= s < N,
I_K T_m = 0                      for s = N,
I_K T_m = (-1)^(q+1) T_(2N-s)   for N < s < 2N.
```

Hence both $T_m$ and its alias have interval sup norm at most one.  With the
coefficient theorem and absolute convergence,

```text
||F - I_K F|| <= 2 sum_{m=N}^infinity |a_m|
              <= 4 M_rho sum_{m=N}^infinity rho^{-m}
               = 4 M_rho rho^{-K} / (rho - 1).
```

The argument is over $\mathbb C$ and therefore applies directly to the complex
Blaschke--Cayley response.  Strictly choosing $\varrho$ below every reduced
target-pole ellipse makes that rational response analytic on a neighborhood
of the closed ellipse.

## Files changed relative to the theory dependency

| File | Change |
|---|---|
| `papers/revision/refs.bib` | Adds the verified SIAM Chapter 8 record and DOI. |
| `papers/revision/citation_audit.md` | Records the source, the node-convention mismatch, and the local scan. |
| `papers/revision/sections/04_theory.tex` | Cites the coefficient theorem and removes the attribution-gate paragraph. |
| `papers/revision/sections/A_appendix_proofs.tex` | Gives the explicit first-kind aliasing and tail-sum derivation with exact indexing. |
| `handoffs/MATH-CHEB-SOURCE-1.md` | Records the decision, evidence, scope, and residual gate. |

No source, diagnostic, test, result, legacy, generated-paper, or front-half
manuscript file is changed.

## Verification

### Tests

```text
command: root virtual-environment Python with
         PYTHONPATH=<cheb-source worktree>/src,
         python -m pytest tests -q -p no:cacheprovider
result:  PASS, 447 passed, 2 third-party torch.jit deprecation warnings
```

The existing Gate-A approximation tests cover the exact first-kind DCT
convention and independently compare realized interpolation error with the
same certified constant.  Since the proof validates that constant, no source
or test change was mathematically necessary.

### Citation scan

```text
command: citation-verifier scan_citations.py papers/revision
result:  22 bibliography keys; 21 cited keys / 36 occurrences;
         0 placeholders; 0 duplicate BibTeX keys
```

An independent key-set comparison finds no cited key missing from `refs.bib`.
The one uncited entry remains the already documented `gama2019diffusion`.

### LaTeX and BibTeX

```text
command: pdflatex, bibtex, pdflatex, pdflatex with the available root
         mechanism-figure directory injected into graphicspath
result:  PASS, 24 pages; BibTeX used 21 entries with 0 warnings;
         0 undefined references/citations; 0 duplicate labels;
         0 missing figures; 0 overfull boxes
```

Only pre-existing underfull-box warnings remain.  Build products were written
outside the repository worktree.

## Remaining paper blocks

1. The T-E attribution block is resolved, but T-E and all other claim-bearing
   theory remain PAPER-BLOCKED until the immutable Gate-A artifact set and an
   independent acceptance review establish implementation/equation coverage.
2. The bound is an a priori upper bound involving both an admissible ellipse
   and $M_\varrho$; target-pole distance alone does not determine realized
   approximation error or empirical efficiency.
3. The finite-frame theorem remains conditional on measured true per-level
   approximation errors.  It cannot be promoted from the analytic bound alone.
4. No conclusion about oversmoothing, oversquashing, benchmark performance,
   or superiority follows from this repair.

## Rollback

Revert only the single MATH-CHEB-SOURCE-1 commit after the `5599a65`
dependency.  It contains the citation/bound repair and this handoff, with no
code or result changes.
