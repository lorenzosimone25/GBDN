# Canonical Scientific Contract

This file defines the scientific identity that the mathematics, implementation, experiments, and paper must share.

## Phase-0 adjudication — 2026-08-11

The following decisions are frozen for Gate A.

1. **Paper identity:** foundational movable-pole paraunitary graph spectral filter-bank work. Heterophily and long-range behavior are evaluation domains, not the paper identity unless later gates support that change.
2. **Primary method:** Tight GBDN. Product-sum GBDN is a secondary expressivity variant. Canonical GBDN+ is a separately labeled relaxation. The preserved H100 implementation is always named **Legacy GBDN+** and cannot define or validate the revised method.
3. **Realization tags:** every theorem, model, run, figure, and table must identify `exact`, `chebyshev-K`, or `legacy`. Exact guarantees never transfer silently to a finite realization.
4. **Coefficient order:** the canonical complete tuple and public API order are
   \[
   (r_0,\ldots,r_{D-1},h_D).
   \]
   Any internal alternative order must be exposed only through an explicit tested permutation.
5. **Norms:** matrix-valued graph signals use the Frobenius norm; complete coefficients use the corresponding Hilbert direct-sum norm; operator bounds use the induced spectral norm.
6. **Graph contract:** the canonical operator accepts only a finite self-adjoint graph operator. Graph construction must either reject asymmetric/negative inputs or apply an explicit, deterministic, recorded undirected-weight policy before building the Laplacian. Silent reliance on a Hermitian eigensolver is invalid.
7. **Root semantics:** the unrestricted canonical parameterization remains radial polar. The proposal `alpha = rho phi(mu)` is rejected as an **exact** frequency-center parameterization because its mapped-zero real part is generally not `mu` for finite `rho`. An optional interpretable parameterization may use
   \[
   \alpha=\phi(\mu+i\gamma),\qquad \mu\in[0,2],\quad \gamma>0,
   \]
   which places the mapped zero exactly at `mu+i gamma`; it must be evaluated as an ablation before adoption.
8. **Optional unitary routing:** dropped from the primary method for this submission unless Gate B exposes a specific failure that it remedies under the same scientific contract.
9. **Phenomenon claims:** complete-map isometry permits a global injectivity/conditioning statement only. It does not imply carried-state non-dissipation, practical anti-oversmoothing, nonzero source-to-target sensitivity, or mitigation of oversquashing.
10. **Evidence admission:** legacy H100 and simplified Peptides artifacts remain diagnostic-only. No claim-bearing H100 job may start before Gate A and immutable artifact infrastructure pass independent review.

## 1. Canonical paper identity

Preferred framing:

> **GBDN is a learned movable-pole Blaschke–Cayley paraunitary graph spectral filter bank. Blaschke roots control localized spectral phase transitions; interference with the identity converts phase into complementary amplitude-selective channels; and the complete exact multilevel representation is Parseval tight.**

Do not frame the work as a direct graph implementation of classical phase unwinding or as a graph analytic signal.

## 2. Domain and operator assumptions

Primary theory scope:

- finite undirected weighted graph;
- self-adjoint symmetric normalized Laplacian
  \[
  L = U\Lambda U^*, \qquad \lambda_i\in[0,2];
  \]
- complex lifted feature signal
  \[
  h\in\mathbb C^{|V|\times d};
  \]
- scalar spectral functional calculus;
- exact operators distinguished from finite-degree sparse realizations.

Extensions to directed, magnetic, time-varying, or non-normal graph operators require separate theory.

## 3. Canonical transform convention

Use:

\[
\phi(\lambda)=\frac{\lambda-i}{\lambda+i},
\qquad
B_\alpha(z)=\frac{z-\alpha}{1-\overline{\alpha}z},
\qquad |\alpha|<1,
\]

and

\[
T_R=B_R(\phi(L)).
\]

The implementation, paper, dense oracle, and tests must agree on:

- whether the denominator uses \(\overline{\alpha}\);
- transform direction;
- coefficient conjugation;
- Chebyshev zeroth-coefficient convention.

No implicit inverse or conjugate convention is permitted.

## 4. Root parameterization

Minimum valid parameterization:

\[
\alpha=\rho_{\max}\sigma(s)e^{i\theta},
\qquad
0<\rho_{\max}<1.
\]

Rejected-as-centered parameterization, retained only if described as an angular anchor:

\[
\alpha_r=\rho_r\,\phi(\mu_r),
\qquad
\mu_r\in[0,2],
\qquad
0<\rho_r<\rho_{\max}.
\]

Here \(\mu_r\) is not generally the exact graph-frequency center when \(\rho_r<1\). The true center and width are the real and imaginary parts of the mapped zero.

Preferred exact center-width parameterization to evaluate:

\[
\alpha_r=\phi(\mu_r+i\gamma_r),
\qquad
\mu_r\in[0,2],\quad \gamma_r>0.
\]

This maps the zero to \(\mu_r+i\gamma_r\), so \(\mu_r\) is the exact phase-derivative center and \(\gamma_r\) its half-width. The implementation must constrain \(\mu_r\) and \(\gamma_r\), verify \(|\alpha_r|<1\), and compare this restricted interpretable family with the unrestricted radial family before it becomes primary.

Independent Cartesian `tanh` constraints are invalid because they do not enforce the joint modulus.

## 5. Method variants

### 5.1 Tight GBDN

For level \(\ell\),

\[
P_\ell^+=\frac{I+T_\ell}{2},
\qquad
P_\ell^-=\frac{I-T_\ell}{2},
\]

\[
r_\ell=P_\ell^-h_\ell,
\qquad
h_{\ell+1}=P_\ell^+h_\ell.
\]

The complete coefficient tuple is

\[
A_Dh_0=(r_0,\ldots,r_{D-1},h_D).
\]

This is the primary method.

### 5.2 Product-sum GBDN

\[
Q_0=I,\qquad Q_\ell=T_\ell Q_{\ell-1},
\]

\[
H_{\mathrm{PS}}h=\sum_{\ell=0}^D c_\ell Q_\ell h.
\]

This is an expressive secondary variant, not generally tight.

### 5.3 GBDN+

Parallel root-parameterized branches with unconstrained polynomial correction and learned skip mixing.

This is an empirical relaxation. It cannot inherit exact all-pass, tightness, or synthesis claims.

## 6. Reconstruction distinction

The paper must explicitly separate:

### Additive reconstruction

\[
r_\ell+h_{\ell+1}=h_\ell.
\]

This follows directly from the complementary definitions and remains exact when both channels use the same approximate factor. It does **not** require unitarity.

### Adjoint synthesis

\[
h_\ell=(P_\ell^-)^*r_\ell+(P_\ell^+)^*h_{\ell+1}.
\]

This is exact for the Parseval analysis bank and is the meaningful structural synthesis guarantee.

Do not market additive reconstruction alone as the central theorem.

## 7. Claim ledger

### 7.1 Already supported in the exact linear setting

Subject to independent rechecking:

- each exact Blaschke–Cayley factor is unitary;
- the one-level complementary bank is Parseval tight;
- the exact multilevel coefficient map is an isometry;
- adjoint synthesis reconstructs the analyzed lifted signal;
- the carried branch is contractive;
- mapped poles control finite-degree approximation difficulty;
- Product-sum can interpolate arbitrary multipliers on a finite set of distinct eigenvalues with sufficiently many terms.

### 7.2 Candidate headline theorems

The Math Agent must prove, condition, narrow, or reject each item.

#### T-A: Pointwise paraunitary partition

Define

\[
p_\ell^\pm(\lambda)=\frac{1\pm t_\ell(\lambda)}2,
\]

\[
a_\ell(\lambda)=
p_\ell^-(\lambda)\prod_{j<\ell}p_j^+(\lambda),
\qquad
a_D(\lambda)=\prod_{j<D}p_j^+(\lambda).
\]

Candidate statement:

\[
\sum_{\ell=0}^D|a_\ell(\lambda)|^2=1
\quad
\forall\lambda\in\operatorname{spec}(L).
\]

#### T-B: Weighted spectral Parseval conservation

For every positive spectral operator \(W=w(L)\succeq0\),

\[
\sum_{\ell=0}^{D-1}\|W^{1/2}r_\ell\|_F^2+
\|W^{1/2}h_D\|_F^2
=
\|W^{1/2}h_0\|_F^2.
\]

Important cases include \(W=I,L,L^s\), and spectral projectors.

Preferred wording:

> The complete exact GBDN analysis is non-dissipative in every graph-spectral quadratic energy.

Do not apply this wording to the carried branch alone.

#### T-C: Conditioning, perturbation isometry, and limited anti-collapse

Candidate statements:

\[
A_D^*A_D=I,
\qquad
\kappa(A_D)=1,
\qquad
\|A_D\delta h\|=\|\delta h\|.
\]

A possible node-level lower bound follows from the additive left inverse:

\[
\|z_u-z_v\|_2
\ge
\frac{\|h_0(u)-h_0(v)\|_2}{\sqrt{D+1}},
\]

where \(z_v\) concatenates all coefficients at node \(v\).

This is a limited anti-collapse result, not a universal no-oversmoothing theorem.

#### T-D: Finite-degree multilevel frame bound

If

\[
\|T_\ell-\widetilde T_\ell\|_{\mathrm{op}}\le\epsilon_\ell,
\]

derive an explicit bound

\[
\|\widetilde A_D^*\widetilde A_D-I\|_{\mathrm{op}}
\le\Delta_D(\epsilon_0,\ldots,\epsilon_{D-1}),
\]

with corresponding lower and upper frame bounds when \(\Delta_D<1\).

The theorem must be measurable from the implementation.

#### T-E: Root localization versus approximation complexity

Formalize the trade-off among:

- root radius and angle;
- phase derivative/Poisson-kernel localization;
- mapped-pole distance from \([0,2]\);
- Bernstein ellipse parameter;
- degree \(K\) required for a target tolerance.

#### T-F: Movable-pole separation from fixed-pole Cayley filters

State a rational-function separation result based on the reduced pole multiset. The claim should be generic and exact, not an unqualified universal superiority statement.

#### T-G: Graph perturbation stability

Seek a resolvent-based bound of the form

\[
\|g(L)-g(L')\|_{\mathrm{op}}
\le C(R,\delta_p)\|L-L'\|_{\mathrm{op}},
\]

under a positive pole margin \(\delta_p\).

#### T-H: Locality and sparse-operation complexity

State the exact relation among Chebyshev degree, sequential depth, effective polynomial degree, receptive field, and sparse matrix–vector multiplications.

### 7.3 Oversmoothing claims

Mathematically defensible candidate:

> The complete exact coefficient analysis cannot globally collapse distinct lifted signals because it is an isometry.

Requires empirical depth analysis before claiming practical resistance to oversmoothing.

The paper must separately analyze:

- complete coefficient tuple;
- carried state;
- residual bands;
- nonlinear readout;
- rank and class separation.

### 7.4 Oversquashing claims

A useful exact statement may be:

> The Jacobian of the exact linear analysis preserves the total norm of any input perturbation across all output nodes and channels.

This does not lower-bound a particular source-to-target block. The Math Agent must attempt a counterexample showing that target-specific sensitivity can still be arbitrarily small or zero.

Therefore the current default conclusion is:

> Tightness prevents global sensitivity dissipation in the complete linear analysis but does not, by itself, solve topological or target-specific oversquashing.

Any stronger statement requires a valid theorem and dedicated experiments.

## 8. Required theorem-to-test bindings

| Statement | Required observable |
|---|---|
| Exact factor unitarity | \(\|T^*T-I\|_{\mathrm{op}}\) |
| Pointwise partition | max spectral partition error |
| Multilevel Parseval | coefficient energy error |
| Weighted Parseval | \(I,L,L^2\), and projector-weighted errors |
| Adjoint synthesis | relative reconstruction error |
| Additive reconstruction | relative telescoping error |
| Conditioning | singular values of dense \(A_D\) on small graphs |
| Finite-\(K\) frame bound | predicted versus observed frame defect |
| Pole approximation | error versus mapped-pole ellipse parameter |
| Perturbation stability | operator change versus \(\|L-L'\|\) |
| Anti-collapse | pairwise lower-bound verification |
| Global sensitivity | Jacobian column norm |
| Oversquashing boundary | source-target Jacobian by distance/bottleneck |

## 9. Allowed paper language

Use:

- “learned movable-pole spectral phase parameterization”;
- “paraunitary” or “Parseval-tight coefficient analysis”;
- “complete coefficient representation”;
- “global perturbation-energy preservation”;
- “dedicated experiments assess oversmoothing and oversquashing separately.”

Avoid:

- “graph Blaschke decomposition” without the qualifier “Blaschke-inspired”;
- “projection” for \(P^\pm\);
- “non-dissipative dynamics” unless the object and norm are named;
- “long-range” based only on the heterophily datasets;
- “state of the art” without the frozen confirmatory table and paired analysis.

## 10. Scientific decision outcomes

For every candidate theorem or claim, the Math Agent and Reviewer Agent must assign one:

```text
PROVED
PROVED_WITH_ADDITIONAL_ASSUMPTIONS
EMPIRICAL_ONLY
COUNTEREXAMPLE_FOUND
REDUNDANT
DROP_FROM_PAPER
```

The orchestrator records the final status in the execution board.

## 11. Gate-A acceptance additions from Phase 0

Gate A also requires:

- explicit unit-modulus checks over scalar grids and graph spectra;
- graph-input rejection/symmetrization tests, including the directed-kNN failure case;
- one canonical coefficient-order correspondence test;
- exact and shared-approximate additive reconstruction;
- pointwise multilevel partition over the full real interval;
- weighted Parseval for `I`, `L`, `L^2`, and spectral projectors, plus a noncommuting node-projector counterexample;
- dense singular values of the exact complete analysis;
- permutation equivariance;
- weighted, disconnected, repeated-eigenvalue, path, cycle, grid, star, and random graph cases across multiple depths;
- sparse-versus-dense **operator** agreement rather than one-vector agreement;
- multilevel predicted-versus-observed finite-order frame defect;
- nonzero representable Product-sum roots and interpolation conditioning;
- carried-state annihilation and target-specific sensitivity counterexamples;
- verification that all trainable parameters exist before optimizer construction.

Passing the pre-Phase-0 ten-test contract is regression evidence only and does not pass Gate A.
