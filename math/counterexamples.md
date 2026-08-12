# MATH-001 counterexample register

## Purpose

Each entry falsifies a tempting stronger claim while preserving the valid theorem boundary. A counterexample is a successful Gate A artifact: it prevents an invalid headline from entering the manuscript.

## C1. The angular anchor is not the phase-transition center

### Rejected claim

For
\[
\alpha=\rho\phi(\mu),
\]
the phase derivative is centered at \(\mu\).

### Construction

Choose \(\mu=1\) and \(\rho=1/2\). The true center is the real part of the mapped zero:
\[
a=
\operatorname{Re}
\left[
i\frac{1+\rho\phi(\mu)}
       {1-\rho\phi(\mu)}
\right].
\]
Direct evaluation gives
\[
a=0.8\ne1.
\]
Likewise, \(\mu=2\), \(\rho=1/2\) gives
\[
a=\frac{16}{13}\approx1.23077\ne2.
\]

### Consequence

The parameter \(\mu\) may be called an angular anchor, not an exact frequency center. Exact center-width semantics require
\[
\alpha=\phi(\mu+i\gamma),\qquad\gamma>0.
\]

### Executable witness

Evaluate the analytic phase derivative on a dense grid and compare its maximizer with both \(\mu\) and the mapped-zero real part. The maximizer must agree with the latter up to grid resolution.

## C2. Additive reconstruction does not imply tightness

### Rejected claim

If the two channels add to the input, the bank is Parseval and adjoint-reconstructing.

### Construction

Take the shared operator \(\widetilde T=0\). Then
\[
\widetilde P^-=\widetilde P^+=I/2.
\]
For every \(h\),
\[
\widetilde P^-h+\widetilde P^+h=h,
\]
but
\[
\|\widetilde P^-h\|^2+
\|\widetilde P^+h\|^2
=\frac12\|h\|^2,
\]
and
\[
(\widetilde P^-)^*\widetilde P^-h+
(\widetilde P^+)^*\widetilde P^+h
=\frac12h.
\]

### Consequence

Additive reconstruction is exact for every shared factor and is algebraically trivial. Adjoint synthesis and Parseval tightness require unitarity or a controlled frame defect.

## C3. The carried state can annihilate a graph mode exactly

### Rejected claim

Exact factor unitarity makes the carried branch non-dissipative or invertible.

### Construction

For the Laplacian zero mode,
\[
\phi(0)=-1.
\]
Take any real \(\alpha\in(-1,1)\). Then
\[
B_\alpha(-1)
=\frac{-1-\alpha}{1+\alpha}=-1.
\]
Therefore
\[
p^+(0)=\frac{1+B_\alpha(-1)}2=0,
\qquad
p^-(0)=1.
\]

### Consequence

The zero-mode component vanishes from the carried state in one level and is stored entirely in the residual. Exact complete-map isometry does not imply carried-state non-dissipation, same-dimensional unitarity, or anti-oversmoothing.

### Executable witness

Use a cycle graph, its normalized-Laplacian zero eigenvector, and a real admissible root. Require final carry norm below exact tolerance and residual reconstruction at exact tolerance.

## C4. Global isometry does not lower-bound a target block

### Rejected claim

Because the complete analysis is an isometry, every target receives nonvanishing influence from every source.

### Construction

At one level and distinct nodes \(u\ne v\), identity terms have zero off-diagonal entry, so
\[
(P^-)_{vu}=-\frac{T_{vu}}2,
\qquad
(P^+)_{vu}=\frac{T_{vu}}2.
\]
The complete source-to-target block norm is
\[
\left(
|(P^-)_{vu}|^2+|(P^+)_{vu}|^2
\right)^{1/2}
=\frac{|T_{vu}|}{\sqrt2}.
\]

Take a real root \(\alpha=r\to1^-\). For every finite real \(\lambda\),
\[
B_r(\phi(\lambda))\to-1,
\]
so
\[
T\to-I.
\]
Every off-diagonal target block tends to zero, while
\[
A_1^*A_1=I
\]
for every \(r<1\).

A deterministic connected 20-node path at \(r=0.95\) already gives endpoint block norm at numerical zero, while the full Jacobian column norm remains one.

### Consequence

Global perturbation-energy conservation and target-specific information transmission are different properties. Tightness alone does not solve oversquashing.

### Executable witness

On connected paths of increasing length, record endpoint block norm, global Jacobian column norm, distance, and root radius. The global norm must remain one while endpoint sensitivity can decay below \(10^{-12}\).

## C5. Disconnected graphs give exact zero cross-component sensitivity

### Rejected claim

Every source influences every target under an exact rational graph filter.

### Construction

Let
\[
L=L_1\oplus L_2.
\]
Every scalar functional calculus operator is block diagonal:
\[
g(L)=g(L_1)\oplus g(L_2).
\]
All analysis atoms are block diagonal. If \(u\) and \(v\) belong to different connected components,
\[
\frac{\partial z_v}{\partial h_u}=0.
\]

### Consequence

No theorem over the frozen graph class can assert universal all-pairs sensitivity. Connectedness would remove this simplest counterexample but not C4.

## C6. Finite polynomial locality gives exact distant zeros

### Rejected claim

A finite Chebyshev realization has global target sensitivity because its exact rational target is global.

### Construction

A degree-\(K\) polynomial in a one-hop graph operator has zero \((v,u)\) entry whenever
\[
\operatorname{dist}(u,v)>K.
\]
At depth \(D\), every effective coefficient has degree at most \(DK\), so targets beyond that radius have exact zero sensitivity.

### Consequence

Exact rational globality cannot be used as evidence for long-range influence of chebyshev-\(K\). Receptive-field reach and target sensitivity must be reported for the realized operator.

## C7. Complete-map isometry does not prevent identical node rows

### Rejected claim

An isometric complete coefficient map prevents nodewise oversmoothing.

### Construction

Take a connected regular graph and a constant node signal
\[
h_0=\mathbf 1x^*.
\]
The constant vector is a Laplacian eigenvector. Every scalar spectral atom maps it to another constant vector, so every coefficient has identical node rows:
\[
z_u=z_v
\quad\text{for all }u,v.
\]
The global coefficient norm is nevertheless exactly preserved.

### Consequence

Hilbert-space injectivity does not imply node separability, feature-matrix rank, class separation, or useful representations. The nodewise lower bound only protects pairs whose input rows were already distinct.

## C8. A nonlinear or narrow readout can discard an isometric representation

### Rejected claim

Because the analysis is invertible, the learned network cannot collapse or lose task information.

### Construction

Compose the exact analysis with the zero readout:
\[
R(A_Dh)=0.
\]
More generally, any readout with a nontrivial nullspace discards coefficient directions.

### Consequence

The analysis guarantee does not transfer to predictions, nonlinear optimization, gradients through learned feature mixing, or a compressed readout.

## C9. Repeated eigenvalues prevent orientation-specific scalar filtering

### Rejected claim

Movable poles let a scalar spectral GBDN assign arbitrary behavior to every eigenvector.

### Construction

Let \(E_\lambda\) have dimension at least two. For any scalar multiplier,
\[
g(L)|_{E_\lambda}=g(\lambda)I_{E_\lambda}.
\]
Choose orthonormal \(u,v\in E_\lambda\) and desired targets
\[
g(L)u=u,\qquad g(L)v=-v.
\]
No scalar \(g(L)\) can satisfy both because it applies the same scalar to \(u\) and \(v\).

### Consequence

Product-sum finite-spectrum universality concerns functions of distinct eigenvalues only. It does not overcome scalar spectral incompleteness or define Fourier orientation in repeated cycle eigenspaces.

## C10. Spectral weighted Parseval does not imply nodewise energy conservation

### Rejected claim

Weighted Parseval holds for every positive weight, including a target-node projector.

### Construction

For one level,
\[
\|W^{1/2}P^-h\|^2+\|W^{1/2}P^+h\|^2
=\frac12h^*(W+T^*WT)h.
\]
This equals \(h^*Wh\) for all \(h\) only if
\[
T^*WT=W.
\]

On the two-node edge graph, choose a nonconstant exact Blaschke--Cayley factor and let \(W=e_1e_1^*\). Then \(T\) has a nonzero off-diagonal entry and does not commute with \(W\). Taking \(h=e_2\) gives
\[
h^*Wh=0
\]
but
\[
\|W^{1/2}P^-h\|^2+
\|W^{1/2}P^+h\|^2
=\frac12|T_{12}|^2>0.
\]

### Consequence

The weighted theorem is restricted to positive operators commuting with the analysis levels, especially spectral weights \(w(L)\). It is not a target-node conservation theorem.

## C11. A one-vector approximation error is not an operator norm

### Rejected claim

Small sparse-versus-dense error on one random signal verifies a uniform finite-frame theorem.

### Construction

Let \(h=e_1\) and choose an error operator
\[
E=Me_2e_2^*
\]
with arbitrary \(M>0\). Then
\[
\frac{\|Eh\|}{\|h\|}=0
\]
while
\[
\|E\|_{\rm op}=M.
\]

### Consequence

The finite-frame premise must be measured through a dense operator on small graphs or, for simultaneous scalar functions of self-adjoint \(L\), through the maximum spectral-symbol error. A sampled signal cannot replace it.

## C12. An asymmetric graph operator breaks the stated adjoint

### Rejected claim

Conjugating Chebyshev coefficients always implements the adjoint sparse operator.

### Construction

For
\[
p(L)=\sum_k c_kT_k(L-I),
\]
the true adjoint is
\[
p(L)^*=
\sum_k\overline c_k\,T_k(L^*-I).
\]
The implementation that reuses \(L\) and only conjugates coefficients computes
\[
\sum_k\overline c_k\,T_k(L-I),
\]
which equals the true adjoint only when \(L=L^*\).

Directed k-nearest-neighbor edge lists can produce \(L\ne L^*\) if no explicit symmetrization or rejection policy is applied.

### Consequence

Self-adjointness is an executable API precondition, not merely prose. Silent use of a Hermitian eigensolver or an adjoint coefficient convention cannot repair invalid graph input.

## C13. Pole distance alone does not determine finite-order error

### Rejected claim

Two rational responses with the same nearest-pole ellipse parameter must have the same finite-\(K\) Chebyshev error.

### Construction

The analytic interpolation bound contains
\[
M_\varrho=\max_{z\in E_\varrho}|g(z+1)|.
\]
Responses can share a nearest pole location while differing in residues, other poles, cancellations, and \(M_\varrho\). Scaling a general rational response also changes interpolation error without moving poles. For all-pass factors the boundary magnitude is constrained, but multi-root products and channel interference still change the ellipse supremum and aliasing.

### Consequence

Mapped-pole geometry determines an analytic-rate envelope, not the exact finite-\(K\) error by itself. Empirical rank correlation is mechanism evidence, not a universal theorem.

## C14. Continuum pole separation disappears on a finite spectrum

### Rejected claim

Because GBDN has movable poles, no fixed-pole or polynomial filter can reproduce it on a finite graph.

### Construction

Let \(L\) have \(m\) distinct eigenvalues. Polynomial interpolation produces a degree at most \(m-1\) polynomial matching any assigned scalar values on those eigenvalues, including the values of a GBDN rational response.

### Consequence

The movable-pole separation theorem is an identity-on-a-continuum result. It does not imply finite-graph representational separation or efficiency. Efficiency must be tested at matched degree, parameters, and SpMVs.

## C15. Product-sum universality can be arbitrarily ill-conditioned

### Rejected claim

Full rank of the finite-spectrum evaluation matrix guarantees stable or parameter-efficient fitting.

### Construction

The Vandermonde witness remains nonsingular when Cayley points are distinct, but its smallest singular value can approach zero as distinct eigenvalues cluster or as the number of terms grows. Continuity of nonsingularity does not provide a useful uniform condition-number bound.

### Consequence

Every Product-sum interpolation artifact must report the evaluation matrix's singular values or condition number. Full rank alone is not evidence of trainability or efficiency.

## Claim-boundary summary

| Strong claim | Counterexample | Final status |
|---|---|---|
| Angular anchor equals exact center | C1 | FALSE; corrected semantics required |
| Additive reconstruction proves tightness | C2 | FALSE |
| Carried branch is non-dissipative | C3 | FALSE |
| Isometry gives every-target influence | C4--C6 | FALSE |
| Isometry prevents practical oversmoothing | C7--C8 | UNSUPPORTED |
| Scalar poles resolve repeated eigenspaces | C9 | FALSE |
| Weighted Parseval is nodewise | C10 | FALSE |
| One-vector error verifies a frame theorem | C11 | FALSE |
| Adjoint coefficients work for directed input | C12 | FALSE |
| Pole location alone determines exact error | C13 | FALSE |
| Pole separation holds on any finite graph | C14 | FALSE |
| Product-sum full rank implies efficiency | C15 | FALSE |

These rejected claims must remain absent even if downstream accuracy is favorable.
