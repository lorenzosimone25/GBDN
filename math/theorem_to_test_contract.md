# MATH-001 theorem-to-test contract

## Gate rule

Gate A passes only when every mandatory row below passes on the prescribed fixture matrix and an independent Reviewer confirms that the observable measures the theorem's actual premise or conclusion. A passing regression subset is not Gate A.

Every test record must include:

- realization tag: exact or chebyshev-K;
- graph fixture and graph hash;
- root values and parameterization;
- depth, degree, dtype, and device;
- absolute and relative residuals;
- predicted bound where applicable;
- observed operator quantity;
- source commit and test name.

Legacy results do not enter this suite.

## Numerical conventions

- Exact dense tests use float64/complex128.
- Scalar analytic identities: maximum absolute residual at most \(5\times10^{-12}\).
- Exact dense operator identities: relative induced-norm residual at most \(10^{-10}\).
- Exact energy/reconstruction identities: relative residual at most \(10^{-10}\), with absolute residual at most \(10^{-12}\) when the denominator is numerically zero.
- Sparse polynomial versus independent dense polynomial: relative operator-norm residual at most \(10^{-8}\).
- Inequality checks use additive numerical slack
  \(10^{-10}\max(1,\text{right-hand side})\).
- Tests must fail on NaN, infinity, empty evaluated sets, or a silently changed coefficient order.
- A theorem-derived approximation bound is checked against the measured error; the error itself is not forced below a universal threshold when the theorem predicts a large defect.

## Required fixture matrix

Use deterministic instances of:

1. paths with at least two sizes;
2. even and odd cycles, including repeated eigenvalues;
3. a rectangular grid;
4. a star;
5. a complete graph with repeated eigenspaces;
6. a disconnected union;
7. a random undirected graph with positive nonuniform weights;
8. two equal-sized nonisomorphic graphs;
9. an asymmetric directed-kNN input that must trigger the selected graph policy;
10. a negative-weight input that must trigger the selected graph policy.

Exact multilevel tests use depths \(1,2,4,8,16\). Sparse tests use representative degrees \(4,8,16,32\), plus a high-order convergence case. Root fixtures include:

- one real interior root;
- one generic complex root;
- a multi-root product;
- a conjugate-symmetric pair where relevant;
- a near-radius-cap root;
- unrestricted radial-polar roots;
- optional exact center-width roots.

Randomized supplements may be added, but deterministic fixtures are the acceptance basis.

## Mandatory tests

| Test ID | Theorem / risk | Observable | Acceptance criterion |
|---|---|---|---|
| GA-00 | Graph contract | symmetry, nonnegativity, spectrum, recorded policy | Invalid directed/negative inputs are rejected or explicitly transformed; resulting \(L=L^*\) within \(10^{-14}\), spectrum lies in \([0,2]\) within \(10^{-12}\), and policy metadata is present. |
| GA-01 | X1 root admissibility | maximum root modulus; mapped zero recovery | Radial roots remain strictly inside unit disk and advertised cap; center-width roots satisfy \(|\alpha|<1\), inverse map returns \(\mu+i\gamma\) within \(5\times10^{-12}\). |
| GA-02 | E1 phase/pole geometry | unit modulus, phase finite difference, zero/pole residual, Lorentzian law | Scalar-grid maximum residual meets scalar tolerance over interior and near-cap roots; forward derivative is positive. |
| GA-03 | E2 exact unitarity | \(\|T^*T-I\|_{\rm op}\) and \(\|TT^*-I\|_{\rm op}\) | Both meet exact operator tolerance across fixture matrix. |
| GA-04 | E2 one-level split | \(\|(P^-)^*P^-+(P^+)^*P^+-I\|_{\rm op}\) | Meets exact operator tolerance; channel energy agrees for multiple feature dimensions. |
| GA-05 | T-A pointwise partition | \(\max_{\lambda\in[-R,R]}|\sum|a_\ell|^2-1|\) and graph-spectrum version | Meets scalar tolerance on a dense real grid extending beyond \([0,2]\) and at every fixture eigenvalue. |
| GA-06 | E3/T-C multilevel isometry | relative coefficient energy error and \(\|A_D^*A_D-I\|_{\rm op}\) | Meets exact tolerances at every prescribed depth and graph. |
| GA-07 | T-C conditioning | minimum/maximum singular values of dense \(A_D\) | Every singular value differs from one by at most \(10^{-10}\); reported condition number differs from one by at most \(10^{-10}\). |
| GA-08 | R1 additive reconstruction | one-level and telescoped reconstruction residual | Exact and shared chebyshev-K channels meet \(10^{-12}\) relative residual; include a deliberately nonunitary factor. |
| GA-09 | R2 adjoint synthesis | \(\|A_D^*A_Dh-h\|/\|h\|\) | Exact meets \(10^{-10}\). Approximate result is checked against measured frame defect, not called perfect reconstruction. |
| GA-10 | R3 coefficient order | public tuple versus independently assembled tuple | Exact equality after documented order; deliberately permuted order must fail unless an explicit tested permutation is applied. |
| GA-11 | T-B weighted Parseval | relative weighted-energy residual for \(I,L,L^2\), \(L^s\), and spectral projectors | Meets exact energy tolerance. |
| GA-12 | C10 boundary | node-projector weighted-energy mismatch | Deterministic two-node witness produces mismatch above \(10^{-6}\), confirming the theorem is not nodewise. |
| GA-13 | E4 energy separation | observed target/complement norms versus bounds | All inequalities pass with numerical slack for matrix-valued features and whole repeated eigenspaces. |
| GA-14 | E5 complex recovery | exact squared error and finite-factor total bound | Exact identity/bound and approximation triangle bound pass with slack. |
| GA-15 | X2 permutation equivariance | exact and polynomial coefficient residual after random fixed permutation | Exact residual at most \(10^{-10}\); sparse residual at most \(10^{-8}\). |
| GA-16 | X3 repeated eigenspaces | operator invariance under eigenspace basis rotation | Dense operator changes by at most \(10^{-10}\); multiplier is scalar within each repeated eigenspace. |
| GA-17 | Graph identity/cache safety | equal-sized graph outputs | Distinct graphs produce distinct operators where expected; rebuilding reproduces each own operator within tolerance. |
| GA-18 | Chebyshev coefficient convention | values at first-kind nodes, zeroth coefficient, dense recurrence | Interpolant reproduces node samples within \(10^{-10}\); independent dense recurrence agrees within \(10^{-8}\). |
| GA-19 | Sparse versus dense polynomial | \(\|\widetilde T_{\rm sparse}-U p_K(\Lambda)U^*\|_{\rm op}\) | Relative operator residual at most \(10^{-8}\); comparison is a full operator, not a sampled vector. |
| GA-20 | E6 exact-approximation error | \(\|T-\widetilde T\|_{\rm op}\), graph spectral max error, interval sup-grid error, analytic bound | Operator norm equals graph spectral max within \(10^{-10}\); both measured errors do not exceed the analytic bound plus slack. |
| GA-21 | E7 one-level finite frame | exact measured frame spectrum versus epsilon bound | Observed defect and extremal frame eigenvalues lie inside predicted bounds. Epsilon is a true operator norm. |
| GA-22 | T-D multilevel finite frame | observed \(\|\widetilde A_D^*\widetilde A_D-I\|_{\rm op}\), predicted \(\Delta_D\), reconstruction error | Observed defect is at most \(\Delta_D\) plus slack at all prescribed depths; positive frame bounds asserted only when \(\Delta_D<1\). |
| GA-23 | T-E center/width | phase peak, HWHM, mapped pole, ellipse parameter | Center-width family matches \(\mu,\gamma\) within discretization/analytic tolerance; angular-anchor test explicitly shows center differs from \(\mu\) in the frozen counterexample. |
| GA-24 | T-E approximation ordering | error versus radius, angle, pole ellipse, and \(M_\varrho\) | Descriptive only: all quantities are emitted; no monotonic pass criterion beyond theorem bounds. |
| GA-25 | E8 Product-sum interpolation | evaluation matrix rank, singular values, condition number, interpolation residual | Deterministic nonzero admissible roots give rank \(m\); residual at most \(10^{-10}\) when condition number is at most \(10^8\); ill-conditioned cases are reported, not hidden. |
| GA-26 | X4 repeated-eigenvalue limitation | incompatible within-eigenspace targets | Least-squares residual is provably/non-numerically nonzero; test confirms scalar multiplier cannot fit them. |
| GA-27 | T-F reduced-pole separation | symbolic/numeric reduced pole multisets | GBDN witness has a pole outside the frozen comparison locus and no cancellation; equality-on-grid is not used as proof. |
| GA-28 | T-G perturbation stability | ratio \(\|g(L)-g(L')\|/\|L-L'\|\) and resolvent bound | Observed ratio does not exceed the explicit bound plus slack for multiple margins and perturbation sizes. |
| GA-29 | T-H locality | maximum operator entry outside declared hop radius | At most \(10^{-12}\) for polynomial fixtures; exact rational response is separately shown generally dense. |
| GA-30 | T-H cost | instrumented Laplacian SpMV count and output storage | Count equals \(DK\) for the canonical recurrence, absent documented reuse; coefficient storage/order is recorded. |
| GA-31 | T-C2 nodewise lower bound | all selected node-pair coefficient distances | No pair violates the \(1/\sqrt{D+1}\) bound beyond slack, for exact and shared approximate splits. |
| GA-32 | C3 carried-state annihilation | zero-mode carry and residual norms | Carry is at most \(10^{-10}\) relative and residual equals input within \(10^{-10}\). |
| GA-33 | X5 global sensitivity | dense Jacobian column norms | Every exact complete-analysis column norm differs from one by at most \(10^{-10}\). |
| GA-34 | C4--C6 target sensitivity boundary | source-target blocks by distance/component/reach | Global column norm remains one while connected endpoint sensitivity falls below \(10^{-12}\); disconnected and beyond-reach blocks are at most \(10^{-12}\). |
| GA-35 | Trainable-parameter lifecycle | parameter IDs before and after first forward; optimizer membership | No trainable parameter is created after optimizer construction; sets and identities agree exactly. |

## Independent dense construction

The dense oracle must not call the sparse layer under test. It should:

1. build or accept a validated self-adjoint \(L\);
2. compute \(L=U\Lambda U^*\);
3. evaluate exact scalar symbols directly;
4. construct \(U\operatorname{diag}(g(\Lambda))U^*\);
5. construct polynomial symbols independently from stored coefficients;
6. assemble the full block analysis matrix explicitly on small graphs.

For sparse operator comparison, applying the sparse implementation to one random \(h\) is insufficient. Apply it to the identity or otherwise materialize the full matrix.

## Frame-bound validation details

For each level compute
\[
\epsilon_\ell=
\|\widetilde T_\ell-T_\ell\|_{\rm op},
\quad
d_\ell=\epsilon_\ell+\epsilon_\ell^2/2,
\quad
c_\ell=(1+\epsilon_\ell/2)^2.
\]
Compute
\[
\Delta_D=
\sum_{\ell=0}^{D-1}
d_\ell\prod_{j<\ell}c_j.
\]
Materialize \(\widetilde A_D\) and report:

- all singular values;
- observed frame defect;
- predicted \(\Delta_D\);
- observed lower and upper frame eigenvalues;
- adjoint synthesis error;
- additive reconstruction error.

A case with \(\Delta_D\ge1\) does not fail the inequality, but it fails admission of a positive lower-frame claim at that configuration.

## Perturbation test details

Use the same vertex set and fixed roots. Perturb a symmetric positive weighted adjacency, rebuild both validated normalized Laplacians, and record:

\[
\eta_L=\|L-L'\|_{\rm op},
\qquad
\eta_g=\|g(L)-g(L')\|_{\rm op}.
\]
For each root, record mapped zero, pole, and
\[
\delta_\alpha=\operatorname{dist}(p_\alpha,[0,2]).
\]
The product bound is
\[
C_{\mathcal R}=
\sum_{\alpha\in\mathcal R}
\frac{|p_\alpha-z_\alpha|}{\delta_\alpha^2}.
\]
Require
\[
\eta_g\le C_{\mathcal R}\eta_L+\text{slack}.
\]
This test does not authorize claims about retraining stability or unmatched graph vertices.

## Oversmoothing and oversquashing boundary artifacts

Gate A does not attempt to show practical resistance. It must establish the claim boundary:

- complete exact representation: singular values and global Jacobian norms equal one;
- carried state: explicit annihilation witness;
- node rows: constant-input collapse witness;
- target block: connected-path decay and disconnected exact zero;
- chebyshev-K: exact zero outside realized hop radius;
- readout: no inherited injectivity claim.

Later depth and long-range experiments must consume these objects separately.

## Gate A report

The suite must produce one machine-readable summary with:

- all test IDs;
- PASS, FAIL, or NOT_RUN;
- maximum residual and tolerance;
- fixture coverage;
- realization tag;
- source commit;
- blocker list.

Gate A is accepted only if every mandatory row is PASS, there are no invalid or missing provenance fields, and independent review finds no theorem-test mismatch. Any disagreement between dense and sparse conventions is a stop-the-line failure.
