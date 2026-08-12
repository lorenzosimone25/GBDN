# Mathematical audit

Audit date: 2026-08-11.

## Verified results

- The Cayley transform maps the real spectral axis to the unit circle, and the
  Blaschke quotient has unit modulus there. The stated phase derivative and
  conjugate pole/zero locations follow directly.
- The complementary split satisfies the pointwise unit-energy identity. The
  resulting one-level analysis is an isometry, and repeated analysis with the
  carry branch has adjoint perfect reconstruction.
- The energy-separation inequality and complex-recovery error bound follow from
  the spectral theorem and the pointwise response identities.
- The approximate-frame estimate follows from the operator-norm error of the
  approximated all-pass factor.
- The product-sum responses form a Vandermonde system on a finite set of
  distinct eigenvalues. Although the convenient zero-root witness lies on the
  boundary of the implemented parameterization, nonsingularity persists for
  sufficiently small nonzero representable roots by continuity.

## Corrections incorporated into the manuscript

1. The implementation evaluates the degree-$K$ first-kind Chebyshev
   **interpolant** at $K+1$ nodes, not a truncated Chebyshev series. The analytic
   error bound was therefore corrected from
   $2M_\rho\rho^{-K}/(\rho-1)$ to the standard interpolant bound
   $4M_\rho\rho^{-K}/(\rho-1)$.
2. Product-sum output weights are complex scalars $c_\ell$ in the analyzed
   response theorem; the notation was corrected accordingly.
3. The product-sum existence statement now uses arbitrarily small nonzero roots
   inside the admissible disk instead of implying that the implementation can
   set a root exactly to zero.
4. The validation-suite count was corrected to 20 tests: nine mathematical
   contract tests and eleven reproduction/compatibility tests.

## Scope

The exact theorems apply to finite undirected graphs and linear spectral
analysis. They do not imply nonlinear optimization stability, resistance to
oversquashing, parameter efficiency, or downstream predictive superiority.
