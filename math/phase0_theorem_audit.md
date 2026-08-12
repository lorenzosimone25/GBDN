# PH0-MATH-001 — Phase 0 theorem and claim audit

## Gate decision

**BLOCK Gate A and every downstream claim-bearing experiment.**

The existing exact tight-bank algebra is mostly correct. The block comes from four contract failures:

1. The canonical Laplacian builder accepts nonsymmetric edge lists without checking or repairing them. The exact theory and adjoint code require a self-adjoint operator.
2. The proposed interpretable parameterization alpha = rho phi(mu) does not center the phase transition at mu except in a boundary limit.
3. The current Gate A suite omits mandatory observables and uses a single-vector relative error where the finite-frame theorem assumes operator-norm error.
4. The manuscript, canonical implementation, Gate A test, and mechanism artifacts are excluded by the repository allowlist, so they are not bound to the recorded source commit.

The strongest defensible identity is:

> Tight GBDN is a nonsubsampled learned movable-pole Blaschke--Cayley spectral analysis bank. For a finite-dimensional self-adjoint graph operator and exact factors, its complete coefficient map is an isometry and reconstructs by its adjoint. These global complete-representation facts do not prevent contraction of the carried state, nodewise collapse in general, or arbitrarily small source-to-target sensitivity.

## Snapshot

- Primary checkout: C:\Users\Lough\Desktop\Research\GBDN [Neurips]
- Recorded commit: fcfa84111df8fcd66cd7266066bcd4c2aa97b852
- Audit branch: agent/math/PH0-MATH-001
- Active manuscript: papers/revision/main.tex
- Implementation: all Python sources under src/gbdn
- Test: tests/test_gate_a.py

The audited scientific inputs are ignored at the recorded commit. Their hashes are:

| Input | SHA-256 |
|---|---|
| papers/revision/main.tex | A6B11478980925DB796248AC7C657AC8BB53AA5AC6AD855C57B45E06A7D49702 |
| papers/revision/sections/04_theory.tex | C89E167F3DE03417C20CD1F4B4DD56B66627B7DA98B7517FF7A5E962FDE3EFB9 |
| papers/revision/sections/A_appendix_proofs.tex | 517291C0053A0E05CB97CDE968EC4A186A53C3953316B19FDA5340E7018270C2 |
| src/gbdn/spectral.py | DC9C58CFF23A1413802BFCC58E5A52726A88609B9457BF100CE52EEF0C3D8648 |
| src/gbdn/layers.py | CE1A613AF8C6AF8B20428DDD82D72278D443D2F685EAF9C9E8D336CF083673AC |
| src/gbdn/model.py | 06069E369B9A4B87E604EBC26441C50349F03D235AF70BE92A55BCC118E67DB8 |
| tests/test_gate_a.py | 504CEE16A9416E888E0907B9757AB53B66393A7A6EB40FEFDAE5D2F7325CE75C |

## Required global assumptions

The paper and code need the following explicit contract:

1. A finite graph/operator domain with aligned vertices.
2. Real, symmetric, nonnegative weights and a fixed isolated-vertex convention.
3. A self-adjoint L with spectrum in [0,2].
4. Scalar spectral functional calculus.
5. All roots satisfy absolute value below one.
6. Exact spectral operators and finite Chebyshev interpolants are distinct.
7. Frobenius signal norm, induced spectral operator norm, and Hilbert direct-sum coefficient norm.
8. Reconstruction refers to the analyzed lift h0, not necessarily the raw real input.

Repeated eigenvalues and disconnected graphs preserve the exact functional-calculus identities, but they limit expressivity and target-specific influence and must be tested.

## Audit of every current numbered result

### Proposition 1: phase and mapped-pole geometry

**Status: PROVED. Standard algebra, not standalone novelty.**

The statement and proof are correct for roots inside the disk. A useful missing equivalent form is

\[
\frac{d}{d\lambda}\arg B_\alpha(\phi(\lambda))
=\frac{2b_\alpha}{(\lambda-a_\alpha)^2+b_\alpha^2},
\]

where z_alpha = a_alpha + i b_alpha is the mapped zero. Thus the exact real-frequency center is a_alpha and the half-width is b_alpha. For alpha = rho exp(i theta),

\[
a_\alpha=\frac{-2\rho\sin\theta}
{1-2\rho\cos\theta+\rho^2},
\qquad
b_\alpha=\frac{1-\rho^2}
{1-2\rho\cos\theta+\rho^2}.
\]

Code binding: cayley_map, blaschke_factor, blaschke_cayley_symbol, mapped_zero_pole, tight_split_responses.

Test binding: phase finite difference and pole/zero tests. Missing are direct unit modulus, center/width, boundary angle, and phase-additivity tests.

### Theorem 1: exact unitary factor and tight split

**Status: PROVED; REDUNDANT as a headline without stronger positioning.**

For self-adjoint L, the exact factor is unitary and

\[
(P^+)^*P^+ + (P^-)^*P^-=I.
\]

This is an automatic construction from any unitary T, not Blaschke-specific. Neither channel is generally an orthogonal projection. The contraction of P+ is correct.

Code binding: blaschke_cayley_exact and GraphBlaschkeLayerTight. The model layer is finite-order, so exact language does not transfer automatically.

### Theorem 2: multilevel isometry and adjoint reconstruction

**Status: PROVED. Correct but a standard cascade of Parseval splits.**

The telescoping proof does not require levels to commute. The backward recursion is the adjoint of the nested analysis map and A_D* A_D = I. All singular values of the complete exact coefficient map are one.

The theorem applies only to the complete tuple. It does not apply to the carried state, one band, the learned lift, or the nonlinear readout.

### Missing mandatory lemma: additive reconstruction

**Status: PROVED; REDUNDANT as a contribution.**

\[
r_\ell+h_{\ell+1}=h_\ell,\qquad
h_0=\sum_{\ell=0}^{D-1}r_\ell+h_D.
\]

This holds for any shared operator, including a nonunitary approximation. It must be separated from the nontrivial adjoint Parseval synthesis claim.

### Theorem 3: spectral energy separation

**Status: PROVED; REDUNDANT as a headline.**

The bounds are diagonal multiplier inequalities. They do not prove achievable response fitting, learning, efficiency, or comparative advantage. For multiple feature channels, the appendix should use row-vector norms. For repeated eigenvalues, target sets should be invariant subspaces or commuting spectral projectors, not basis-dependent eigenvector indices.

The current test uses an arbitrary response vector rather than a Blaschke channel or graph operator.

### Corollary 1: complex spectral packet recovery

**Status: PROVED; REDUNDANT as a headline.**

The exact bound and the epsilon_K / 2 perturbation term are correct. If a total approximate recovery bound is reported, the exact and approximation terms must be combined explicitly by the triangle inequality.

### Theorem 4: mapped-pole Chebyshev interpolation

**Status: PROVED_WITH_ADDITIONAL_ASSUMPTIONS.**

The factor 4 bound is correct for the degree-K first-kind Chebyshev interpolant. Add:

- a nonempty root set or a separate constant case;
- analyticity on and inside the closed ellipse;
- a standard approximation-theory citation;
- reduced poles if later sums permit cancellations;
- explicit acknowledgement that M_rho, residues, aliasing, and roundoff also affect finite-K error.

The ellipse parameter alone does not universally predict the exact error.

### Theorem 4: one-level approximate frame bound

**Status: PROVED, but not uniformly tested.**

The parallelogram proof is correct when the premise is an operator-norm error. The test variable called operator_error is only

\[
\frac{\|(\widetilde T-T)h\|}{\|h\|}
\]

for one sampled signal. It cannot validate a uniform frame theorem. No multilevel finite-order theorem or test currently exists.

### Theorem 5: finite-spectrum Product-sum interpolation

**Status: PROVED; algebraically elementary.**

The zero-root Vandermonde witness plus continuity proves existence of representable small nonzero roots. The generic claim should invoke the real-analytic function given by the squared modulus of the determinant. Repeated eigenvalues necessarily share a scalar multiplier.

The test covers only the inadmissible zero-root witness, not a parameterized nonzero root, interpolation coefficients, genericity, repeated eigenvalues, or finite-order degradation.

### Final stability remark

**Status: PROVED_WITH_ADDITIONAL_ASSUMPTIONS.**

The product norm bound follows from an operator-norm approximation premise. It is not a multilevel frame bound, nonlinear optimization theorem, or graph perturbation theorem.

## Candidate theorem ledger

| Candidate | Status | Strongest correct result |
|---|---|---|
| Pointwise paraunitary partition | PROVED | Effective atoms sum in squared magnitude to one for every real lambda, not only the graph spectrum. |
| Weighted spectral Parseval | PROVED_WITH_ADDITIONAL_ASSUMPTIONS | Holds for every positive W commuting with all levels, including W = w(L); for L^s use s at least zero. |
| Exact conditioning | PROVED | A_D* A_D = I, condition number one, perturbation norm preserved. |
| Nodewise anti-collapse | PROVED but REDUNDANT | Additive left inverse gives a 1/sqrt(D+1) lower bound for initially distinct node rows; it is not a no-oversmoothing theorem. |
| Finite-order multilevel frame | PROVED_WITH_ADDITIONAL_ASSUMPTIONS | Explicit defect recurrence below; missing from paper/tests. |
| Root localization trade-off | COUNTEREXAMPLE_FOUND for proposed center; otherwise conditional | Exact center/width are mapped-zero real/imaginary parts. |
| Movable-pole separation | PROVED_WITH_ADDITIONAL_ASSUMPTIONS | Generic reduced-pole separation on a continuum, not arbitrary finite spectra and not after cancellations. |
| Graph perturbation stability | PROVED_WITH_ADDITIONAL_ASSUMPTIONS | Fixed-root resolvent bound for aligned self-adjoint operators. |
| Locality and sparse complexity | PROVED | Exact rational filters are generally global; degree K is K-hop; depth D uses DK SpMVs and at most DK-hop reach. |
| Practical anti-oversmoothing | EMPIRICAL_ONLY | Complete-map injectivity is the only current positive structural result. |
| Every-target sensitivity or oversquashing prevention | COUNTEREXAMPLE_FOUND; DROP | Only total complete-analysis perturbation energy is preserved. |

### Pointwise partition and weighted Parseval

For real lambda, each exact scalar factor has unit modulus, hence

\[
|p_\ell^+|^2+|p_\ell^-|^2=1.
\]

Backward telescoping proves the effective multilevel atoms have squared magnitudes summing to one. This holds over the entire real axis. If positive W commutes with every level, apply the same Parseval map to W^(1/2) h. Generic node projectors do not commute with L, so this gives no target-node lower bound.

### Explicit finite-order multilevel defect

Assume

\[
\|\widetilde T_\ell-T_\ell\|_{\mathrm{op}}\leq\epsilon_\ell.
\]

Set

\[
d_\ell=\epsilon_\ell+\epsilon_\ell^2/2,\qquad
c_\ell=(1+\epsilon_\ell/2)^2.
\]

The one-level frame defect is at most d_l and the approximate carry norm squared is at most c_l. The nested frame operators satisfy

\[
\|S_\ell-I\|\leq d_\ell+c_\ell\|S_{\ell+1}-I\|,
\qquad S_D=I.
\]

Therefore

\[
\Delta_D=
\sum_{\ell=0}^{D-1}
d_\ell\prod_{j=0}^{\ell-1}c_j
\]

bounds the multilevel frame defect. When Delta_D is below one, frame bounds are 1 minus Delta_D and 1 plus Delta_D, and adjoint reconstruction error is at most Delta_D times the signal norm. Additive reconstruction remains exact separately.

### Corrected frequency parameterization

For alpha = rho phi(mu), the true phase-derivative maximum is the real part of

\[
i\frac{1+\rho\phi(\mu)}{1-\rho\phi(\mu)},
\]

not generally mu. Numerical examples:

- mu = 1 and rho = 0.5 gives center 0.8.
- mu = 2 and rho = 0.5 gives center about 1.23077.

If exact center and width are desired, alpha = phi(mu + i gamma) maps to zero mu + i gamma. Otherwise mu must be called an angular anchor, not the exact frequency center. This is a Phase 1 scientific identity decision.

### Generic movable-pole distinction

A one-factor response has a reduced pole p_alpha in the lower half-plane. A fixed-scale Cayley polynomial has a fixed pole set. If reduced rational functions agree on a real interval, the rational identity theorem forces their pole multisets to match. Thus a generic movable pole outside the fixed set cannot be represented exactly by that fixed-pole family on a continuum.

Exceptions include cancellations, coincident poles, degenerate coefficients, and agreement only on a finite graph spectrum. This is not a universal efficiency or superiority theorem.

### Graph perturbation stability

For aligned self-adjoint L and L-prime with spectra in [0,2], fixed alpha, and pole margin delta_alpha,

\[
\|g_\alpha(L)-g_\alpha(L')\|_{\mathrm{op}}
\leq
\frac{|p_\alpha-z_\alpha|}{\delta_\alpha^2}
\|L-L'\|_{\mathrm{op}}.
\]

The result follows from the resolvent identity. Products inherit a sum of factor constants by unitary telescoping. It requires fixed roots, aligned vertices, and self-adjoint operators. Edge-weight versions additionally require degree lower bounds.

## Counterexamples

### Carried-state annihilation

At lambda = 0, phi(0) = -1. For any real alpha inside the disk,
B_alpha(-1) = -1, so p_plus(0) = 0. The zero mode is removed from the carried state in one level and stored in the residual. Complete-map tightness does not imply carried-state invertibility or non-dissipation.

### Target-specific oversquashing boundary

For u not equal to v, the one-level source-to-target block across both complete channels has norm

\[
\left(|(P^-)_{vu}|^2+|(P^+)_{vu}|^2\right)^{1/2}
=|T_{vu}|/\sqrt 2.
\]

For a real root alpha = r tending to one from below, T tends to minus the identity on every finite graph spectrum. Every off-diagonal target block tends to zero while the complete analysis remains exactly isometric.

A read-only check on a connected 20-node path at the admissible r = 0.95 found endpoint sensitivity about 7.6e-17 while the complete Jacobian column norm was 1. Disconnected components give exact zero influence, and finite-K filters give exact zero outside their effective hop range. Tightness therefore does not prevent oversquashing.

### Nodewise collapse remains possible

On a connected regular graph, a constant input remains constant under every scalar spectral channel. All node rows of the complete representation are identical although global norm is preserved. For initially distinct node rows the additive lower bound prevents exact equality in the full stack, but it weakens with depth and says nothing about class separation, effective rank, a fixed-width state, or the readout.

### Repeated-eigenspace limitation

Every scalar g(L) acts as g(lambda) times identity on a repeated eigenspace. Movable poles cannot distinguish orientations within it. Product-sum spans only scalar multipliers on distinct eigenvalues.

### Self-adjointness implementation failure

normalized_laplacian does not verify reciprocal edges or symmetric weights. sphere_graph_data constructs directed k-nearest-neighbor edges and does not symmetrize them. A read-only reconstruction at n = 600, k = 12 produced

\[
\|L-L^\top\|_F/\|L\|_F\approx 8.22\times10^{-2}.
\]

Calling a Hermitian eigensolver does not repair this. Approximate synthesis conjugates coefficients but reuses L, which is the true adjoint only if L is self-adjoint. The sphere artifact omits edges, raw seed runs, and executable source, so its claimed symmetric graph cannot be verified. That mechanism result is suggestive only until regenerated.

## Paper claim classification

| Claim | Classification | Decision |
|---|---|---|
| Exact factors are all-pass/unitary | Proved | Retain with exact/self-adjoint scope. |
| Complementary split is tight | Proved | Retain, but do not oversell standard algebra. |
| Complete exact multilevel map is isometric and adjoint-reconstructing | Proved | Retain as main structural guarantee. |
| Learned lift/raw input is invertible | Unsupported | Do not claim. |
| rho phi(mu) is centered at mu | False | Change wording or parameterization. |
| Mapped poles give an analytic Chebyshev error envelope | Proved | Retain with M_rho assumptions. |
| Ellipse parameter alone predicts exact error | Suggestive only | Do not universalize the mechanism sweep. |
| Product-sum spans finite-spectrum scalar multipliers | Proved | Retain in appendix; no efficiency claim. |
| Sphere mechanism improvement | Suggestive only | Graph and source provenance are incomplete. |
| Complete analysis prevents global signal collapse | Proved only as injectivity | Use precise Hilbert-space wording. |
| GBDN cannot oversmooth | Unsupported | Requires depth experiments. |
| Tightness solves oversquashing | False/remove | Counterexamples above. |
| Movable poles differ generically from fixed poles | Proved with assumptions | Still requires novelty and matched empirical review. |

## Paper--theory--code--test correspondence

| Object | Paper | Code | Evidence | Finding |
|---|---|---|---|---|
| Forward convention | Preliminaries/Proposition 1 | spectral.py | Phase/pole tests | Aligned. |
| Root admissibility | Preliminaries | parameterize_roots | Extreme logits | Strict radius bound not directly asserted. |
| Self-adjoint L | Preliminaries | normalized_laplacian | Symmetric hand-made fixtures only | Mismatch: not enforced. |
| Exact unitarity/tightness | Theorem 1 | exact helper | One path | Correct but narrow. |
| Exact multilevel map | Theorem 2 | exact helpers | One path, depth 16 | Correct but narrow. |
| Approximate adjoint synthesis | Method | GBDNTight.synthesize | No direct finite-K reconstruction test | Unverified. |
| Additive reconstruction | Missing | Implicit | No test | Missing distinction. |
| Weighted Parseval | Missing | Functional calculus | No test | Missing. |
| Pointwise partition | Missing | Response helpers | No test | Missing. |
| Conditioning | Implicit | Exact helper | No singular-value test | Missing. |
| Chebyshev frame theorem | Theorem 4 | Approximate layer | One-vector error | Uniform theorem not tested. |
| Product-sum interpolation | Theorem 5 | Finite-K model | Zero-root Vandermonde | Weak binding. |
| Permutation equivariance | Required, absent | Expected | No test | Missing. |
| Repeated/disconnected graphs | In scope | Expected | No test | Missing. |
| Graph identity/cache safety | Method | No implicit cache | Path/cycle test | Passed. |
| Sphere mechanism | Experiments | No immutable generator | Aggregate and best-run files | Provenance/graph blocked. |

## Gate A test audit

The existing suite passes 10 Gate A tests. Pytest collects 20 repository tests total: 10 Gate A and 10 reproduction/legacy tests. The manuscript's statement of nine mathematical plus eleven other tests is factually wrong.

Missing or inadequate requirements:

- pointwise partition;
- additive reconstruction for exact and approximate factors;
- weighted Parseval for I, L, L-squared, and spectral projectors;
- dense singular values/conditioning;
- permutation equivariance;
- repeated eigenvalues;
- disconnected graphs;
- multiple graph families and depths;
- true sparse-versus-dense operator comparison;
- true operator-norm approximation error;
- finite-order multilevel frame distortion;
- target-specific sensitivity boundary.

Passing the current tests is useful regression evidence, not completion of Gate A.

## Novelty boundary

The unitary-to-Parseval split, telescoping energy, weighted Parseval extension, and additive reconstruction are standard or automatic. The potentially distinctive core is narrower:

1. multiple learned movable Blaschke poles rather than coefficients over a fixed Cayley pole set;
2. identity interference converting localized all-pass phase into complementary amplitude channels;
3. a complete nonsubsampled Parseval coefficient stack;
4. sparse polynomial realization with measurable pole-dependent defect.

This remains a candidate contribution until the Reviewer checks graph-QMF/framelet prior work and matched mechanism experiments show value over CayleyNet, ChebNetII, BernNet, UniFilter, WaveGC, and related methods.

## Stop-the-line actions

Before downstream experiments:

1. Track/freeze the manuscript, canonical source, tests, and mechanism generator.
2. Enforce symmetric nonnegative graph construction or fail loudly.
3. Regenerate sphere artifacts with stored edges, graph hash, raw initializations, exact/finite flag, and source commit.
4. Decide between an angular-anchor interpretation and exact center/width parameterization.
5. Implement all missing Gate A observables and graph families.
6. Correct the test-count statement to 10 plus 10.

## Parallel work and dependencies

- Math may formalize the proved candidate results, counterexamples, and theorem-to-test contract.
- Engineering may track canonical code, repair graph validation, build a true dense oracle, and expand Gate A.
- Reviewer may independently verify novelty, reduced-pole separation, and the counterexamples.
- Mechanism claims depend on graph/provenance repair.
- Sparse tightness language depends on multilevel defect tests.
- Oversmoothing and oversquashing work depends on accepted Gate A.
- H100 confirmatory benchmarks must not start until the independent Gate A review passes.

## Final verdict

Preserve the exact core, block downstream claims, repair the graph/operator contract, correct the root interpretation, and promote only theorems that survive independent review and executable tests.
