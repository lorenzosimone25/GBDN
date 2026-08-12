# MATH-001 proof audit

## 1. Mathematical setting

Let
\[
\mathcal H=\mathbb C^{n\times d},
\qquad
\langle X,Y\rangle_F=\operatorname{tr}(X^*Y).
\]
Let \(L=L^*\) with \(\operatorname{spec}(L)\subseteq[0,2]\). The graph interpretation additionally requires a recorded construction from real, symmetric, nonnegative weights. The proofs below only need the self-adjoint operator statement unless graph locality or edge perturbations are discussed.

For \(|\alpha|<1\), define
\[
\phi(\lambda)=\frac{\lambda-i}{\lambda+i},
\qquad
B_\alpha(z)=\frac{z-\alpha}{1-\overline\alpha z}.
\]
For a finite root multiset \(\mathcal R\),
\[
t_{\mathcal R}(\lambda)=
\prod_{\alpha\in\mathcal R}B_\alpha(\phi(\lambda)),
\qquad
T_{\mathcal R}=t_{\mathcal R}(L).
\]
At level \(\ell\),
\[
P_\ell^\pm=\frac{I\pm T_\ell}{2},
\quad
r_\ell=P_\ell^-h_\ell,
\quad
h_{\ell+1}=P_\ell^+h_\ell.
\]

Exact means spectral functional calculus. Chebyshev-\(K\) means a degree-\(K\) polynomial interpolant evaluated through a sparse recurrence. Legacy is outside these theorems.

## 2. Root admissibility and corrected center semantics

### Lemma 2.1: radial-polar admissibility

If
\[
\alpha=\rho_{\max}\sigma(s)e^{i\theta},
\qquad 0<\rho_{\max}<1,
\]
and \(s,\theta\) are finite, then \(|\alpha|<\rho_{\max}<1\).

Proof: the logistic function satisfies \(0<\sigma(s)<1\) for finite \(s\), and the complex exponential has modulus one.

Finite-precision implementation may round to the declared radius unless a numerical margin is included. The mathematical statement is strict; the executable contract must check strict unit-disk membership and the implementation's advertised finite-precision bound separately.

### Lemma 2.2: exact center-width admissibility

Let \(w=\mu+i\gamma\) with \(\gamma>0\), and set
\[
\alpha=\phi(w)=\frac{w-i}{w+i}.
\]
Then
\[
|\alpha|^2
=\frac{\mu^2+(\gamma-1)^2}
       {\mu^2+(\gamma+1)^2}<1.
\]
The inverse Cayley map gives
\[
i\frac{1+\alpha}{1-\alpha}=w=\mu+i\gamma.
\]
Thus this optional family has exact center \(\mu\) and half-width \(\gamma\).

What it does not prove: this restricted family is preferable to unrestricted radial-polar roots, satisfies a desired radius cap without further constraints, or improves learning.

## 3. Phase and mapped-pole geometry

### Proposition 3.1

For real \(\lambda\) and \(|\alpha|<1\),
\[
|B_\alpha(\phi(\lambda))|=1.
\]
Writing
\[
z_\alpha=i\frac{1+\alpha}{1-\alpha}
=a_\alpha+i b_\alpha,
\qquad b_\alpha>0,
\qquad p_\alpha=\overline{z_\alpha},
\]
the response has the reduced rational form
\[
B_\alpha(\phi(\lambda))
=c_\alpha\frac{\lambda-z_\alpha}{\lambda-p_\alpha},
\qquad
c_\alpha=\frac{1-\alpha}{1-\overline\alpha},
\qquad |c_\alpha|=1.
\]
For a continuous unwrapped phase,
\[
\frac{d}{d\lambda}\arg B_\alpha(\phi(\lambda))
=\frac{2b_\alpha}
       {(\lambda-a_\alpha)^2+b_\alpha^2}>0.
\]

Proof: \(\phi(\lambda)\) lies on the unit circle, where numerator and denominator magnitudes of \(B_\alpha\) agree. Direct substitution and clearing \(\lambda+i\) gives the rational form. Differentiating the logarithm of
\((\lambda-z_\alpha)/(\lambda-\overline z_\alpha)\) gives the Lorentzian derivative.

For \(\alpha=\rho e^{i\theta}\),
\[
a_\alpha=
\frac{-2\rho\sin\theta}
     {1-2\rho\cos\theta+\rho^2},
\qquad
b_\alpha=
\frac{1-\rho^2}
     {1-2\rho\cos\theta+\rho^2}.
\]
For a product, phase derivatives add:
\[
\frac{d}{d\lambda}\arg t_{\mathcal R}(\lambda)
=\sum_{\alpha\in\mathcal R}
\frac{2b_\alpha}
{(\lambda-a_\alpha)^2+b_\alpha^2}.
\]

Audit conclusion: the original phase and pole proof is correct. The added Lorentzian form is necessary to state center and width precisely. The old interpretation of \(\rho\phi(\mu)\) as exactly centered at \(\mu\) is false.

What it does not prove: the combined product has a peak at each individual center when Lorentzians overlap; every root creates a transition inside \([0,2]\); or narrow phase localization is computationally cheap.

## 4. Exact one-level bank

### Theorem 4.1: unitary factor and Parseval split

For exact \(T=t(L)\),
\[
T^*T=TT^*=I.
\]
For \(P^\pm=(I\pm T)/2\),
\[
(P^-)^*P^-+(P^+)^*P^+=I.
\]
Consequently,
\[
\|P^-h\|_F^2+\|P^+h\|_F^2=\|h\|_F^2,
\qquad
\|P^\pm\|_{\rm op}\le1.
\]

Proof: the spectral theorem diagonalizes \(T\) with diagonal entries of unit modulus. Expanding the two Gram operators cancels cross terms and yields
\(\tfrac12(I+T^*T)=I\). On each eigenmode,
\[
|p^+|=|\cos(\psi/2)|,
\qquad
|p^-|=|\sin(\psi/2)|.
\]

Audit conclusion: correct. The result is algebraically automatic for every unitary \(T\), so it is correctness infrastructure rather than sufficient novelty. The words orthogonal projection must not be used: generally \((P^\pm)^2\ne P^\pm\).

### Lemma 4.2: additive reconstruction

For any linear operator \(S\), without unitarity,
\[
\frac{I-S}{2}h+\frac{I+S}{2}h=h.
\]
Therefore every shared exact or approximate split obeys
\[
r_\ell+h_{\ell+1}=h_\ell
\]
and telescopes to
\[
h_0=\sum_{\ell=0}^{D-1}r_\ell+h_D.
\]

Audit conclusion: correct and mandatory to state, but trivial. It must not be conflated with adjoint synthesis.

## 5. Pointwise and multilevel Parseval analysis

### Theorem 5.1: pointwise paraunitary partition

Define
\[
p_\ell^\pm(\lambda)=\frac{1\pm t_\ell(\lambda)}2,
\]
\[
a_\ell(\lambda)=
p_\ell^-(\lambda)\prod_{j<\ell}p_j^+(\lambda),
\quad 0\le\ell<D,
\qquad
a_D(\lambda)=\prod_{j<D}p_j^+(\lambda).
\]
Then, for every real \(\lambda\),
\[
\sum_{\ell=0}^{D}|a_\ell(\lambda)|^2=1.
\]

Proof: \(|p_\ell^-|^2+|p_\ell^+|^2=1\). Define the remaining energy from level \(j\) by
\[
F_j=
\sum_{\ell=j}^{D-1}
|p_\ell^-|^2\prod_{k=j}^{\ell-1}|p_k^+|^2
+\prod_{k=j}^{D-1}|p_k^+|^2.
\]
Since \(F_D=1\) and
\[
F_j=|p_j^-|^2+|p_j^+|^2F_{j+1},
\]
backward induction gives \(F_0=1\).

Audit conclusion: proved on the full real axis, which is stronger than the candidate graph-spectrum-only statement. It is a nonsubsampled scalar paraunitary column, not a critically sampled graph-QMF result.

### Theorem 5.2: exact multilevel isometry and adjoint synthesis

The complete analysis satisfies
\[
\|A_Dh\|_\oplus^2
=\sum_{\ell=0}^{D-1}\|r_\ell\|_F^2+\|h_D\|_F^2
=\|h\|_F^2,
\]
\[
A_D^*A_D=I.
\]
Backward adjoint synthesis is
\[
h_\ell=(P_\ell^-)^*r_\ell+
       (P_\ell^+)^*h_{\ell+1}.
\]

Proof: apply the one-level energy identity successively and telescope. Applying the one-level Gram identity to analyzed coefficients reconstructs \(h_\ell\); backward induction reconstructs \(h_0\). This recursion is the adjoint of the nested analysis map.

No inter-level commutation is required. Each level only needs to be a Parseval split on the same Hilbert space.

Audit conclusion: correct. Perfect reconstruction means the analyzed lift. The nonlinear readout is outside the theorem.

### Corollary 5.3: exact conditioning

Every singular value of the rectangular map \(A_D\) is one. In the full-column-rank sense,
\[
\kappa(A_D)=
\frac{\sigma_{\max}(A_D)}{\sigma_{\min}(A_D)}=1.
\]
For all perturbations,
\[
\|A_D\delta h\|_\oplus=\|\delta h\|_F.
\]
The Moore--Penrose left inverse is \(A_D^*\), with norm one.

What it does not prove: conditioning of learned root parameters, optimizer dynamics, the carried state, the readout, or a loss Hessian.

### Corollary 5.4: limited nodewise anti-collapse

Let
\[
z_v=(r_0(v),\ldots,r_{D-1}(v),h_D(v)).
\]
The additive identity and Cauchy--Schwarz give
\[
\|h_0(u)-h_0(v)\|_2
\le\sqrt{D+1}\,\|z_u-z_v\|_2,
\]
hence
\[
\|z_u-z_v\|_2
\ge
\frac{\|h_0(u)-h_0(v)\|_2}{\sqrt{D+1}}.
\]

This result also holds for shared approximate channels because it uses only additive reconstruction.

What it does not prove: distinct nodes with identical inputs become distinguishable; node-feature matrix rank is preserved; class separation survives; a fixed-width or carried representation avoids collapse; or a readout retains the information.

## 6. Weighted spectral Parseval conservation

### Theorem 6.1

Let \(W\succeq0\) commute with every \(T_\ell\). Then
\[
\sum_{\ell=0}^{D-1}
\|W^{1/2}r_\ell\|_F^2+
\|W^{1/2}h_D\|_F^2
=\|W^{1/2}h_0\|_F^2.
\]

Proof: \(W^{1/2}\) commutes with every \(P_\ell^\pm\), so the coefficient tuple of \(W^{1/2}h\) is exactly
\[
(W^{1/2}r_0,\ldots,W^{1/2}r_{D-1},W^{1/2}h_D).
\]
Apply Theorem 5.2.

Important cases are \(W=I\), \(W=L\), \(W=L^s\) for \(s>0\), and spectral projectors. More generally, any positive operator in the joint commutant of the levels qualifies.

Audit conclusion: proved with the commuting assumption. A generic node projector does not commute with \(L\), so the theorem is spectral, not target-node conservation.

## 7. Spectral selection and complex recovery

### Lemma 7.1: energy separation

Let \(\Pi_S\) be a spectral projector and \(h_S=\Pi_Sh\). For \(r=q(L)h\), assume
\[
|q(\lambda)|\ge1-\delta\quad\text{on }S,
\qquad
|q(\lambda)|\le\eta\quad\text{on }S^c.
\]
Then
\[
\|\Pi_Sr\|_F\ge(1-\delta)\|h_S\|_F,
\qquad
\|\Pi_{S^c}r\|_F\le\eta\|h_{S^c}\|_F.
\]
If \(h_S\ne0\), the squared leakage ratio is bounded by
\[
\frac{\|\Pi_{S^c}r\|_F^2}{\|\Pi_Sr\|_F^2}
\le
\frac{\eta^2\|h_{S^c}\|_F^2}
{(1-\delta)^2\|h_S\|_F^2}.
\]

Proof: use the orthogonal spectral decomposition and row-vector norms for matrix-valued features.

### Corollary 7.2: complex recovery

If instead
\[
|q(\lambda)-1|\le\delta\quad\text{on }S,
\qquad
|q(\lambda)|\le\eta\quad\text{on }S^c,
\]
then
\[
\|q(L)h-h_S\|_F^2
\le
\delta^2\|h_S\|_F^2+
\eta^2\|h_{S^c}\|_F^2.
\]
If \(q=(1-t)/2\), \(\widetilde q=(1-\widetilde t)/2\), and
\(\|\widetilde T-T\|_{\rm op}\le\epsilon_K\), then
\[
\|\widetilde q(L)h-h_S\|_F
\le
\sqrt{\delta^2\|h_S\|_F^2+
\eta^2\|h_{S^c}\|_F^2}
+\frac{\epsilon_K}{2}\|h\|_F.
\]

Audit conclusion: correct supporting inequalities. They do not prove response achievability, trainability, or comparative efficiency.

## 8. Chebyshev approximation and mapped-pole complexity

### Theorem 8.1: interpolation bound

Let \(g(\lambda)=t_{\mathcal R}(\lambda)\) have a nonempty reduced pole set \(\{p_r\}\). Set \(x=\lambda-1\), \(\xi_r=p_r-1\), and
\[
\chi(\xi_r)=
\max_\pm\left|\xi_r\pm\sqrt{\xi_r^2-1}\right|.
\]
For
\[
1<\varrho<\min_r\chi(\xi_r),
\]
suppose \(g(x+1)\) is analytic on and inside the closed Bernstein ellipse \(E_\varrho\), and define
\[
M_\varrho=\max_{z\in E_\varrho}|g(z+1)|.
\]
The degree-\(K\) first-kind Chebyshev interpolant \(p_K\) satisfies
\[
\sup_{\lambda\in[0,2]}
|g(\lambda)-p_K(\lambda)|
\le
\frac{4M_\varrho}{\varrho-1}\varrho^{-K}.
\]
For self-adjoint \(L\),
\[
\|g(L)-p_K(L)\|_{\rm op}
\le
\sup_{\lambda\in[0,2]}|g(\lambda)-p_K(\lambda)|.
\]

Proof: the pole condition gives analyticity on the closed ellipse; apply the standard Chebyshev interpolation theorem, then the spectral theorem.

For a target tolerance \(\tau>0\), any integer
\[
K\ge
\left\lceil
\frac{\log\!\left(
4M_\varrho/((\varrho-1)\tau)
\right)}
{\log\varrho}
\right\rceil
\]
suffices when the numerator is positive; otherwise \(K=0\) already satisfies the bound.

Audit conclusion: correct under the added analytic assumptions. Pole distance determines the largest admissible ellipse but not the prefactor \(M_\varrho\), residues, cancellation, interpolation aliasing, or roundoff.

### Theorem 8.2: localization/complexity geometry

For a mapped zero \(a+ib\), one factor has phase derivative
\[
\frac{2b}{(\lambda-a)^2+b^2}.
\]
The peak is \(2/b\), its half-width at half maximum is \(b\), and its full width at half maximum is \(2b\). Its pole is \(a-ib\). Thus sharper interior phase transitions correspond to poles closer to the real interval and smaller admissible Bernstein ellipses.

For the optional exact center-width family,
\[
\alpha=\phi(\mu+i\gamma),
\]
the zero and pole are \(\mu\pm i\gamma\), and the phase derivative is
\[
\frac{2\gamma}{(\lambda-\mu)^2+\gamma^2}.
\]

For unrestricted radial roots, use the exact \(a_\alpha,b_\alpha\) formulas in Proposition 3.1. Radius alone does not order approximation difficulty across angles. For multiple roots, derivatives add and the nearest reduced pole limits the common analytic ellipse.

Audit conclusion: this is the corrected T-E. Do not claim global monotonicity of observed finite-\(K\) error in a single root coordinate.

## 9. Finite-order frame distortion

### Theorem 9.1: one-level bound

Let \(T\) be unitary and
\[
\|\widetilde T-T\|_{\rm op}\le\epsilon.
\]
Then
\[
\left\|
(\widetilde P^-)^*\widetilde P^-+
(\widetilde P^+)^*\widetilde P^+-I
\right\|_{\rm op}
\le
\epsilon+\frac{\epsilon^2}{2}.
\]
Equivalently,
\[
\frac{1+(1-\epsilon)^2}{2}\|h\|_F^2
\le
\|\widetilde P^-h\|_F^2+
\|\widetilde P^+h\|_F^2
\le
\frac{1+(1+\epsilon)^2}{2}\|h\|_F^2.
\]

Proof:
\[
(\widetilde P^-)^*\widetilde P^-+
(\widetilde P^+)^*\widetilde P^+
=\frac12(I+\widetilde T^*\widetilde T).
\]
Writing \(\widetilde T=T+E\) gives
\[
\|\widetilde T^*\widetilde T-I\|_{\rm op}
\le2\epsilon+\epsilon^2.
\]
The energy inequalities also follow from
\((1-\epsilon)\|h\|\le\|\widetilde Th\|\le(1+\epsilon)\|h\|\).

### Theorem 9.2: multilevel heterogeneous bound

At level \(\ell\), suppose
\[
\|\widetilde T_\ell-T_\ell\|_{\rm op}
\le\epsilon_\ell.
\]
Define
\[
d_\ell=\epsilon_\ell+\frac{\epsilon_\ell^2}{2},
\qquad
c_\ell=\left(1+\frac{\epsilon_\ell}{2}\right)^2.
\]
Then
\[
\|\widetilde A_D^*\widetilde A_D-I\|_{\rm op}
\le
\Delta_D,
\]
where
\[
\Delta_D=
\sum_{\ell=0}^{D-1}
d_\ell\prod_{j=0}^{\ell-1}c_j.
\]
If \(\Delta_D<1\), the analysis frame bounds are
\[
1-\Delta_D
\quad\text{and}\quad
1+\Delta_D.
\]
For analyzed coefficients, adjoint synthesis obeys
\[
\|\widetilde A_D^*\widetilde A_Dh-h\|_F
\le\Delta_D\|h\|_F.
\]

Proof: let \(S_\ell\) be the frame operator of the remaining nested analysis, with \(S_D=I\). Then
\[
S_\ell=
(\widetilde P_\ell^-)^*\widetilde P_\ell^-+
(\widetilde P_\ell^+)^*S_{\ell+1}\widetilde P_\ell^+.
\]
The one-level defect is at most \(d_\ell\), while
\[
\|\widetilde P_\ell^+\|_{\rm op}
\le1+\epsilon_\ell/2.
\]
Therefore
\[
\|S_\ell-I\|_{\rm op}
\le d_\ell+c_\ell\|S_{\ell+1}-I\|_{\rm op}.
\]
Unrolling the recurrence yields \(\Delta_D\).

For uniform \(\epsilon\), set
\[
d=\epsilon+\epsilon^2/2,
\qquad
c=(1+\epsilon/2)^2.
\]
Then
\[
\Delta_D\le
d\frac{c^D-1}{c-1}
\]
for \(\epsilon>0\), and \(\Delta_D=0\) for \(\epsilon=0\). At one level, the formula reduces to \(d\).

A sharper measurable recurrence is available for simultaneous scalar functions of one self-adjoint \(L\): replace \(d_\ell\) by the observed one-level spectral defect and \(c_\ell\) by
\(\max_\lambda|\widetilde p_\ell^+(\lambda)|^2\).

Audit conclusion: the theorem is proved. It remains paper-blocked until the implementation measures true operator errors and observed frame spectra over multiple graphs and depths.

## 10. Product-sum finite-spectrum expressivity

### Theorem 10.1

Let \(L\) have \(m\) distinct eigenvalues
\(\mu_1,\ldots,\mu_m\), and set
\(z_j=\phi(\mu_j)\). There exist roots satisfying
\[
0<|\alpha_t|<r_{\max}
\]
such that
\[
q_0(\lambda)=1,
\qquad
q_\ell(\lambda)=
\prod_{t=1}^{\ell}B_{\alpha_t}(\phi(\lambda)),
\quad 1\le\ell<m,
\]
form a basis for complex scalar multipliers on the distinct spectrum.

Proof: at the closure point \(\alpha_t=0\),
\[
q_\ell(\mu_j)=z_j^\ell.
\]
The Cayley map is injective on the real line, so the evaluation matrix is Vandermonde and nonsingular. Continuity preserves nonsingularity for sufficiently small nonzero roots within every positive radius cap. The squared modulus of the determinant is a nontrivial real-analytic function of root coordinates, so its zero set has Lebesgue measure zero; full rank is generic.

Audit conclusion: correct. The implementation's finite logits cannot attain zero, but continuity supplies representable witnesses. The theorem needs \(m\) terms and may be arbitrarily ill-conditioned. It says nothing about parameter efficiency, generalization across graphs, or finite-\(K\) realization.

Repeated eigenvalues cannot receive different values because every scalar function of \(L\) is constant on each eigenspace.

## 11. Movable-pole separation

### Theorem 11.1: conditional reduced-pole separation

Let \(\mathcal F_S\) be a rational-filter family whose reduced poles lie in an allowed set \(S\). Let a Tight GBDN factor or channel have a reduced mapped pole \(p_\alpha\notin S\). Then it cannot equal a member of \(\mathcal F_S\) on any real interval with an accumulation point.

Proof: equality on such an interval implies equality of the two rational functions by analytic continuation after clearing denominators. Equal reduced rational functions have identical poles with multiplicity, contradicting \(p_\alpha\notin S\).

For a fixed-scale Cayley polynomial, the pole locus is fixed. Even if a single Cayley scale is learnable, its pole lies on the imaginary-axis locus, while a generic Blaschke root has a mapped pole with nonzero real part. Multiple roots also permit multiple distinct lower-half-plane poles.

Exceptions and boundaries:

- Product-sum output coefficients can cancel poles.
- Coincident roots alter multiplicity.
- A comparison family may itself permit free poles.
- Equality on a finite graph spectrum does not imply rational identity.
- Separation does not imply better approximation, optimization, or SpMV efficiency.

Audit conclusion: mathematically valid conditional theorem. Independent Reviewer verification of the precise CayleyNet family and closest prior graph rational filters is mandatory before paper promotion.

## 12. Graph perturbation stability

### Theorem 12.1: one-factor resolvent bound

Let \(L,L'\) be aligned self-adjoint operators with spectra in \([0,2]\). Fix a root \(\alpha\) and let
\[
\delta_\alpha=
\operatorname{dist}(p_\alpha,[0,2])>0.
\]
Then
\[
\|g_\alpha(L)-g_\alpha(L')\|_{\rm op}
\le
\frac{|p_\alpha-z_\alpha|}
     {\delta_\alpha^2}
\|L-L'\|_{\rm op}.
\]

Proof: with
\[
g_\alpha(\lambda)=
c_\alpha\left(
1+\frac{p_\alpha-z_\alpha}{\lambda-p_\alpha}
\right),
\]
the constant terms cancel. The resolvent identity gives
\[
(L-pI)^{-1}-(L'-pI)^{-1}
=(L-pI)^{-1}(L'-L)(L'-pI)^{-1}.
\]
Each resolvent norm is at most \(1/\delta_\alpha\).

### Corollary 12.2: finite products

For a root multiset \(\mathcal R\),
\[
\|t_{\mathcal R}(L)-t_{\mathcal R}(L')\|_{\rm op}
\le
\left(
\sum_{\alpha\in\mathcal R}
\frac{|p_\alpha-z_\alpha|}
{\delta_\alpha^2}
\right)
\|L-L'\|_{\rm op}.
\]

Proof: telescope the product difference. Every exact factor at \(L\) and \(L'\) is unitary, so surrounding factor norms equal one.

Boundaries:

- roots are held fixed;
- vertex spaces are aligned;
- both operators are self-adjoint;
- the result is not permutation-invariant graph matching;
- converting adjacency perturbation into normalized-Laplacian perturbation requires nonzero degree lower bounds and a recorded normalization policy;
- the theorem does not control learned parameters after retraining.

## 13. Permutation equivariance and repeated spectra

### Theorem 13.1: permutation equivariance

For a permutation matrix \(\Pi\), let
\[
L'=\Pi L\Pi^*,
\qquad h'=\Pi h.
\]
For exact functional calculus or any polynomial \(p\),
\[
g(L')=\Pi g(L)\Pi^*.
\]
Therefore every Tight GBDN coefficient obeys
\[
r_\ell'=\Pi r_\ell,\qquad h_\ell'=\Pi h_\ell.
\]

Proof: powers and resolvents respect unitary similarity; induction handles the analysis recursion.

### Lemma 13.2: repeated eigenspaces

If \(E_\lambda\) is an eigenspace of multiplicity greater than one, then
\[
g(L)|_{E_\lambda}=g(\lambda)I_{E_\lambda}.
\]
Thus the operator is invariant to rotations of the chosen eigenbasis, but cannot distinguish orientations inside the eigenspace.

## 14. Locality and complexity

### Theorem 14.1

A degree-\(K\) polynomial in a graph operator whose off-diagonal support is one-hop is at most \(K\)-hop localized. A sequence of \(D\) degree-\(K\) factors has polynomial degree and receptive-field radius at most \(DK\). Residual level \(\ell\) has reach at most \((\ell+1)K\), and the final carry has reach at most \(DK\).

Computing one Chebyshev basis through degree \(K\) uses \(K\) sparse Laplacian--feature multiplications. Tight or Product-sum depth \(D\) therefore uses \(DK\) such multiplications, excluding feature mixing and readout. Storing every complex coefficient requires \(O((D+1)nd)\) activations unless streamed.

Proof: powers of a one-hop sparse matrix cannot connect vertices beyond their exponent. Polynomial degrees add under multiplication. The Chebyshev three-term recurrence performs one sparse multiplication per new order.

Exact nonconstant rational graph filters are generally dense and global. Special cancellations can reduce degree, support, or cost, so all complexity statements are upper bounds.

## 15. Oversmoothing and oversquashing boundary

### Theorem 15.1: global sensitivity conservation

The Jacobian of exact linear complete analysis is \(A_D\). For every perturbation,
\[
\|J\delta h\|_\oplus=\|\delta h\|_F.
\]
Equivalently, the sum of squared target-node and coefficient-channel sensitivities for each input direction is one.

This is a global complete-output statement.

### Rejected stronger statement

There is no universal positive lower bound for a specified source-to-target block. The counterexamples are formalized in counterexamples.md. Complete-map isometry therefore does not prove oversquashing mitigation.

Likewise, complete-map injectivity does not prove practical anti-oversmoothing. The carried state can annihilate modes; constant inputs can have identical node rows; a readout can discard the complete tuple; and rank/class separation are not controlled.

## 16. Proof-readiness decision

The following results have complete proofs above and may proceed to independent review: root admissibility, phase/pole geometry, exact split, additive reconstruction, pointwise partition, multilevel isometry/synthesis, conditioning, limited nodewise lower bound, weighted Parseval, selection/recovery lemmas, Chebyshev bound under stated analytic conditions, multilevel finite-order defect, Product-sum finite-spectrum interpolation, conditional pole separation, fixed-root perturbation stability, permutation equivariance, repeated-spectrum invariance, and locality/complexity.

No result is paper-allowed until its executable observable in theorem_to_test_contract.md passes and the Reviewer accepts its novelty and claim scope.
