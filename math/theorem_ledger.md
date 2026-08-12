# MATH-001 theorem ledger

## Purpose and frozen semantics

This ledger is the mathematical source of truth for Gate A. It records correctness, scope, novelty, executable evidence, and paper admissibility separately.

All results use the following contract unless a row states otherwise.

- The graph signal space is the finite-dimensional Hilbert space
  \(\mathcal H=\mathbb C^{n\times d}\) with Frobenius norm.
- \(L=L^*\) and \(\operatorname{spec}(L)\subseteq[0,2]\). A graph constructor must reject invalid input or apply an explicit deterministic symmetric, nonnegative weight policy.
- \(\phi(\lambda)=(\lambda-i)/(\lambda+i)\).
- \(B_\alpha(z)=(z-\alpha)/(1-\overline\alpha z)\), with \(|\alpha|<1\).
- \(t_\ell(\lambda)=B_{\mathcal R_\ell}(\phi(\lambda))\) and
  \(T_\ell=t_\ell(L)\).
- \(P_\ell^\pm=(I\pm T_\ell)/2\),
  \(r_\ell=P_\ell^-h_\ell\), and
  \(h_{\ell+1}=P_\ell^+h_\ell\).
- The canonical complete tuple is
  \(A_Dh=(r_0,\ldots,r_{D-1},h_D)\), in that order, with the Hilbert direct-sum norm.
- Every result is tagged exact, chebyshev-K, or legacy. Exact conclusions do not transfer silently to a finite polynomial realization.
- Tight GBDN, Product-sum GBDN, canonical GBDN+, and Legacy GBDN+ are distinct objects.

The unrestricted root family remains
\[
\alpha=\rho_{\max}\sigma(s)e^{i\theta}.
\]
The expression \(\rho\phi(\mu)\) is only an angular anchor. It is not an exact center parameterization. The optional family
\[
\alpha=\phi(\mu+i\gamma),\qquad \gamma>0,
\]
has exact mapped-zero center \(\mu\) and half-width \(\gamma\), but remains an ablation until empirically justified.

## Status vocabulary

- PROVED: correct under the frozen contract.
- PROVED_WITH_ADDITIONAL_ASSUMPTIONS: correct only with assumptions stated in the ledger.
- EMPIRICAL_ONLY: no promoted theorem is currently justified.
- COUNTEREXAMPLE_FOUND: the proposed stronger statement is false.
- REDUNDANT: correct but algebraically standard or automatic and unsuitable as a headline by itself.
- DROP_FROM_PAPER: false, misleading, or scientifically unhelpful language.

## Current manuscript results

| ID | Result | Status | Exact assumptions and boundary | Novelty / paper decision | Required evidence |
|---|---|---|---|---|---|
| E1 | Blaschke--Cayley unit modulus, phase law, mapped zero and pole | PROVED | Exact; \(|\alpha|<1\); continuous unwrapped phase. For products, derivatives add. | Standard complex-analysis algebra. Retain as the geometric foundation, not a standalone novelty theorem. | Scalar-grid unit modulus, phase finite difference, mapped zero/pole, center/width. |
| E2 | Exact factor unitarity and one-level complementary Parseval split | PROVED and REDUNDANT as a headline | Exact; \(L=L^*\). \(P^\pm\) are not generally projections. | The unitary-to-Parseval construction is automatic. Novelty must come from movable-pole parameterization and its use in a graph bank. | Dense \(\|T^*T-I\|_{\rm op}\), scalar partition, channel energy. |
| E3 | Exact multilevel isometry and adjoint reconstruction | PROVED | Exact complete tuple only. Reconstructs analyzed lift \(h_0\), not necessarily raw input. No commutation across levels is required. | Retain as the main structural guarantee, while acknowledging standard Parseval-cascade algebra. | Energy telescoping, dense singular values, \(A_D^*A_D\), adjoint reconstruction. |
| E4 | Spectral energy separation | PROVED and REDUNDANT | Exact scalar multiplier; target is a spectral projector or union of whole eigenspaces. | A diagonal multiplier inequality. Retain as a supporting lemma, not a contribution claim. | Direct spectral inequality with matrix-valued features. |
| E5 | Complex spectral packet recovery | PROVED and REDUNDANT | Same as E4; finite approximation adds a norm perturbation term. | Supporting lemma distinguishing magnitude selection from complex recovery. | Exact error identity and finite-factor perturbation bound. |
| E6 | Chebyshev interpolant error from mapped poles | PROVED_WITH_ADDITIONAL_ASSUMPTIONS | Nonempty reduced pole set; analytic on and inside a closed Bernstein ellipse; first-kind degree-\(K\) interpolation; \(M_\varrho\) finite. | Standard approximation theorem applied to learned mapped poles. Retain with citation and without claiming the ellipse parameter alone determines error. | Node interpolation, uniform symbol error, spectral operator error, pole ellipse parameter. |
| E7 | One-level approximate frame bounds | PROVED | \(\|\widetilde T-T\|_{\rm op}\le\epsilon<1\) for exact unitary \(T\). A one-vector error is not this premise. | Supporting approximation guarantee. It does not establish multilevel finite-\(K\) tightness. | True dense operator norm and observed frame spectrum. |
| E8 | Finite-spectrum Product-sum interpolation | PROVED | Exact factors; \(m\) distinct eigenvalues; \(m\) cumulative functions including \(q_0\); sufficiently small nonzero admissible roots. | Elementary finite-set universality. Appendix only; no graph-size-independent efficiency claim. | Nonzero representable roots, evaluation rank, conditioning, interpolation residual, repeated-eigenvalue limitation. |
| E9 | Exact/approximate stability scope remark | PROVED_WITH_ADDITIONAL_ASSUMPTIONS | Per-factor operator errors are genuine operator norms. Product bound concerns factor products, not the complete frame or nonlinear network. | Retain only as scope clarification. | Per-factor norms and separately measured multilevel frame defect. |

## Required reconstruction and structural results

| ID | Result | Status | Exact statement | Paper decision |
|---|---|---|---|---|
| R1 | Additive reconstruction | PROVED and REDUNDANT | For any shared operator, exact or approximate, \(r_\ell+h_{\ell+1}=h_\ell\), hence \(h_0=\sum_{\ell<D}r_\ell+h_D\). | State explicitly and separate from adjoint synthesis. Never market as the central perfect-reconstruction theorem. |
| R2 | Adjoint synthesis | PROVED | For the exact Parseval bank, \(h_\ell=(P_\ell^-)^*r_\ell+(P_\ell^+)^*h_{\ell+1}\). For chebyshev-K, applying the analysis adjoint returns \(\widetilde A_D^*\widetilde A_Dh\), with bounded defect rather than exact recovery. | Central structural synthesis statement. |
| R3 | Coefficient order correspondence | PROVED once implemented and tested | The public tuple order is \((r_0,\ldots,r_{D-1},h_D)\). Any alternative order is an explicit unitary permutation. | Contract requirement, not a research theorem. |

## Candidate T-A through T-H

| ID | Candidate | Status | Strongest correct theorem | Headline decision |
|---|---|---|---|---|
| T-A | Pointwise paraunitary partition | PROVED | Effective atoms \(a_\ell(\lambda)\) satisfy \(\sum_{\ell=0}^{D}|a_\ell(\lambda)|^2=1\) for every real \(\lambda\), not merely the graph spectrum. | Strong main-theory candidate, but position relative to nonsubsampled paraunitary banks. |
| T-B | Weighted spectral Parseval conservation | PROVED_WITH_ADDITIONAL_ASSUMPTIONS | Holds for every \(W\succeq0\) commuting with all levels, in particular \(W=w(L)\). Use \(L^s\) for \(s>0\), with \(W=I\) handled separately. Generic node projectors do not qualify. | Main-theory candidate if phrased as complete coefficient spectral-energy conservation. |
| T-C1 | Exact conditioning and perturbation isometry | PROVED | All singular values of rectangular \(A_D\) equal one; \(\kappa(A_D)=1\); \(\|A_D\delta h\|_\oplus=\|\delta h\|_F\). | Main guarantee. It is global and complete-representation only. |
| T-C2 | Nodewise limited anti-collapse | PROVED and REDUNDANT | With \(z_v=(r_0(v),\ldots,r_{D-1}(v),h_D(v))\), \(\|z_u-z_v\|_2\ge\|h_0(u)-h_0(v)\|_2/\sqrt{D+1}\). It also holds for shared approximate channels by additive reconstruction. | Supporting corollary only. Do not call it practical anti-oversmoothing. |
| T-D | Finite-degree multilevel frame bound | PROVED_WITH_ADDITIONAL_ASSUMPTIONS | If \(\|\widetilde T_\ell-T_\ell\|_{\rm op}\le\epsilon_\ell\), then \(\|\widetilde A_D^*\widetilde A_D-I\|_{\rm op}\le\Delta_D\), with explicit heterogeneous and uniform formulas in proof_audit.md. | Main approximation theorem after executable validation. |
| T-E | Root localization versus approximation complexity | PROVED_WITH_ADDITIONAL_ASSUMPTIONS; old centered-anchor claim has COUNTEREXAMPLE_FOUND | Each mapped zero \(a+ib\) contributes Lorentzian phase derivative \(2b/((\lambda-a)^2+b^2)\). The nearest reduced pole bounds the admissible Bernstein ellipse, and a fixed-ellipse tolerance gives an explicit degree bound. \(M_\varrho\) remains essential. | Main geometric theorem. Use corrected center/width semantics. |
| T-F | Movable-pole distinction from fixed-pole Cayley families | PROVED_WITH_ADDITIONAL_ASSUMPTIONS | Equality on a real interval forces equality of reduced rational functions and hence pole multisets. A generic GBDN pole outside a comparison family's allowed pole locus cannot be represented exactly by that family on a continuum. | Potential novelty theorem; requires independent prior-work review and must exclude finite-spectrum and cancellation cases. |
| T-G | Graph perturbation stability | PROVED_WITH_ADDITIONAL_ASSUMPTIONS | For aligned self-adjoint \(L,L'\), fixed roots, and positive pole margins, a resolvent bound is linear in \(\|L-L'\|_{\rm op}\); product constants add. | Supporting theorem. It is not an edge-edit theorem without normalized-degree assumptions. |
| T-H | Locality and sparse complexity | PROVED | Exact nonconstant rational factors are generally global. A degree-\(K\) polynomial realization is \(K\)-hop localized; \(D\) sequential factors cost \(DK\) Laplacian SpMVs and have degree/reach at most \(DK\). | Required scope and fair-comparison theorem. |

## Additional exact contract results

| ID | Result | Status | Boundary |
|---|---|---|---|
| X1 | Root admissibility | PROVED | Radial-polar roots obey \(|\alpha|<\rho_{\max}<1\) for finite logits. Center-width roots \(\phi(\mu+i\gamma)\) obey \(|\alpha|<1\) iff \(\gamma>0\). |
| X2 | Permutation equivariance | PROVED | For a permutation \(\Pi\), exact and polynomial operators obey \(g(\Pi L\Pi^*)=\Pi g(L)\Pi^*\); all analysis coefficients permute. |
| X3 | Repeated-eigenspace invariance | PROVED | Every scalar \(g(L)\) is \(g(\lambda)I\) within a repeated eigenspace. Choice of eigenbasis does not affect the operator. |
| X4 | Product-sum repeated-eigenvalue limitation | PROVED | Scalar spectral multipliers cannot assign different values to vectors within one repeated eigenspace. |
| X5 | Exact complete-analysis Jacobian norm | PROVED | The linear Jacobian is \(A_D\); every input perturbation preserves total output norm across all nodes and coefficient channels. |

## Phenomenon claims

| Claim | Status | Admissible wording |
|---|---|---|
| The complete exact representation is globally injective and conditioned | PROVED | The complete exact coefficient analysis preserves pairwise Hilbert-space distances and has condition number one. |
| The carried state is non-dissipative | COUNTEREXAMPLE_FOUND; DROP_FROM_PAPER | The carried branch is contractive and can annihilate an eigenmode exactly. |
| Tight GBDN cannot oversmooth in practice | EMPIRICAL_ONLY | Exact complete-map injectivity motivates, but does not replace, depth-dependent rank and class-separation experiments. |
| Every target receives nonzero source influence | COUNTEREXAMPLE_FOUND; DROP_FROM_PAPER | Total perturbation energy is preserved, but any specified target block can be zero or arbitrarily small. |
| Tightness mitigates or solves oversquashing | COUNTEREXAMPLE_FOUND; DROP_FROM_PAPER | Tightness alone does not solve target-specific or topological oversquashing. |
| Heterophily accuracy establishes high-frequency or long-range mechanism | DROP_FROM_PAPER | Heterophily, high-frequency labels, oversmoothing, oversquashing, and long-range dependence require separate evidence. |

## Novelty boundary

The following are correctness infrastructure, not sufficient novelty by themselves:

- unitary factor implies complementary Parseval split;
- telescoping multilevel energy;
- additive reconstruction;
- weighted Parseval once every atom commutes with \(W\);
- finite-set Vandermonde interpolation with one term per distinct eigenvalue.

The candidate distinctive contribution is the combination of:

1. freely learned movable Blaschke poles;
2. phase-to-amplitude conversion by interference with the identity;
3. a complete nonsubsampled Parseval coefficient stack;
4. a sparse polynomial realization with pole-dependent, measurable frame defect.

This identity is not paper-allowed as a novelty claim until the Reviewer completes comparison with Cayley filters, graph-QMF, graph framelets, unitary graph convolutions, and learned graph wavelets.

## Promotion state

- Mathematically proved and ready for independent review: E1--E9 under their conditions, R1--R2, T-A, T-B, T-C, T-D, corrected T-E, conditional T-F, conditional T-G, T-H, and X1--X5.
- Blocked from paper promotion pending executable Gate A evidence: T-A through T-H and X1--X5.
- Permanently rejected without a new theorem: carried-state non-dissipation, universal anti-oversmoothing, every-target sensitivity, and oversquashing mitigation from tightness.
