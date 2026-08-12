# Independent theory-heavy review of MATH-002--011

## Reviewed object and verdict

- Commit: `7b7909899e65d1f86bfc523e452c15c0ccf97e53`
- Branch reviewed: `agent/math/MATH-002-011`
- Sections reviewed in full: `02_preliminaries.tex`, `03_method.tex`,
  `04_theory.tex`, and `A_appendix_proofs.tex`
- Governing sources reviewed in full: the frozen scientific contract, theorem
  ledger, proof audit, counterexample register, theorem-to-test contract,
  Gate-A preflight, and MATH-002--011 handoff

**Verdict: BLOCKED FOR PAPER PROMOTION; CONDITIONALLY ACCEPTABLE AS AN INTERNAL
THEORY DRAFT.**

The abstract mathematical core is substantially correct. I found no fatal
counterexample to the exact partition/isometry results, the commuting-weight
identity, the heterogeneous finite-frame recurrence, the conditional
reduced-pole separation, or the fixed-root resolvent bound. The patch also
draws the essential negative boundary correctly: complete-map isometry does
not imply carried-state non-dissipation, target-specific sensitivity, or
oversquashing mitigation.

The patch cannot yet enter a claim-bearing manuscript. At the reviewed commit,
two present-tense paper--implementation assertions are false: the public
coefficient order is carry-first in code rather than residual-first, and the
graph constructor neither rejects nor explicitly symmetrizes asymmetric input.
The required 36-row Gate-A contract is also not implemented or passed. These
are stop-the-line correspondence failures, not cosmetic issues.

## Findings in priority order

### 1. Stop-line: coefficient order contradicts the reviewed implementation

The paper says that the canonical order used by the implementation and
artifacts is
`(r_0,...,r_{D-1},h_D)` (`03_method.tex:23--27`). At this commit,
`TightAnalysisOutput.components` returns
`[final_carry, *bands]` (`src/gbdn/model.py:30--31`), and the node predictor
concatenates that property directly (`src/gbdn/model.py:206`). Thus the
paper's implementation-correspondence statement is false in the exact tree
under review.

This does not invalidate the residual-first mathematics: an output
permutation is unitary. It does invalidate provenance, readout semantics, and
the claim that paper, API, and artifacts share one order. Merge the engineering
order fix first, add semantic sentinel/serialization/readout tests, and only
then retain the present-tense sentence.

### 2. Stop-line: graph validation claim contradicts the reviewed constructor

The paper says that the canonical implementation rejects asymmetric,
negative-weight, and nonfinite graph input at the operator boundary
(`02_preliminaries.tex:14--18`). The reviewed `normalized_laplacian` merely
passes the edge list to PyG `get_laplacian` and does not perform those checks
or record a preprocessing policy (`src/gbdn/layers.py:25--45`). Its docstring
calls the result symmetric, but a directed edge list is accepted without an
explicit reciprocal-mean transform or rejection.

The self-adjoint theorems remain correct as mathematics, but the sparse model
does not currently enforce their premise. This is a Gate-A blocker because an
asymmetric operator also breaks the advertised coefficient-conjugation
adjoint. The core must reject invalid input, while any adjacency
symmetrization must live in a separate hash-recording preprocessor, exactly as
the frozen contract requires.

### 3. Stop-line: front-half promotion conflicts with the patch's own status

`04_theory.tex:3--8` labels all statements paper-blocked pending Gate A and
independent review. The abstract and introduction nevertheless say "we prove"
the isometry and reconstruction results, and the conclusion says algebraic
tests support the structural claims. `05_experiments.tex:8` also reports an
obsolete 20-test inventory. An independent run at this commit gives 30 passing
tests, but only 10 are the old `test_gate_a.py` regression subset; this is not
the frozen 36-row acceptance suite.

The internal draft marker is appropriate. Before submission, either keep the
front half explicitly provisional or, preferably, promote claims only after
GA-00--GA-35 pass with provenance and independent review. Do not interpret the
30 passing legacy/boundary/regression tests as Gate-A acceptance.

### 4. Mandatory hypothesis fix: center-width range is incomplete

The optional parameterization in `02_preliminaries.tex:46--50` bounds
`gamma` but omits the frozen requirement `mu in [0,2]`. Proposition 1 then
calls `mu` the exact phase-derivative center without distinguishing a center
on the full real axis from the maximum observed on the graph interval. The
Lorentzian statement is mathematically correct for every real `mu`, but if
`mu` lies outside `[0,2]` its in-domain maximum is at an endpoint.

Add `mu in [0,2]` wherever this is called an in-spectrum center, retain
`0 < gamma_min <= gamma <= gamma_max`, and require the target-pole margin to
be emitted. If unrestricted `mu` is desired, call it the real-axis center and
state the interval boundary behavior.

### 5. Mandatory reconstruction fix: define the backward recursion completely

The method reuses `widehat h` for two incompatible objects: graph Fourier
coefficients in the preliminaries and a synthesized state in
`03_method.tex:47--55`. The synthesis recursion also omits the terminal
condition `h_D^{syn}=h_D`. Finally, the displayed recursion uses exact
`P_l^+/-` and then discusses finite factors without ever defining
`tilde P_l^+/-=(I +/- tilde T_l)/2`.

Use a non-Fourier symbol such as `h_l^{syn}`, initialize it at `h_D`, and give
separate exact and approximate notation. In T-D, say explicitly that
`Delta_D ||h||` bounds adjoint reconstruction **of analyzed coefficients**;
it is not an inverse guarantee for arbitrary coefficient tuples.

### 6. Mandatory scope fix: the `DK` cost is conditional, not purely algebraic

The locality part of T-H is correct: degree is at most `DK`, residual level
`l` reaches at most `(l+1)K`, and the final carry reaches at most `DK`. The
claim that the realization "uses `DK`" sparse products is an implementation
statement. It is exact only when every level evaluates the full degree-`K`
recurrence without cross-level reuse, early truncation, or a different batched
operator schedule.

State that assumption in the proposition, or say "at most/nominally `DK`"
until GA-30 instruments the canonical runner. The arithmetic and activation
counts should also identify whether complex operations are counted as one or
multiple real operations.

### 7. Required attribution and notation cleanup

- T-E invokes a specific first-kind Chebyshev interpolation constant but gives
  no citation. The proof ledger itself requires a citation. Cite the exact
  approximation result and its node convention.
- State "reduced nonremovable target poles" in T-E. This is already essential
  in T-F and prevents a later extension to channel combinations from silently
  counting cancelled poles.
- In `A_appendix_proofs.tex:100`, use the direct-sum norm for
  `A_D x`, not a plain Frobenius norm on a tuple.
- Define the open disk `D` before T-A.
- Do not reuse `theta` first as the unit-circle phase and then as the root
  angle in the proof of Proposition 1.
- In T-D, call `1-Delta_D` and `1+Delta_D` frame bounds (equivalently squared
  singular-value bounds), not "squared frame bounds."

### 8. T-F is mathematically valid but not yet a contribution claim

The reduced-pole identity argument is correct under its stated continuum,
common-domain, and nonremovable-pole hypotheses. It excludes neither matching
on a finite graph spectrum nor approximation by a polynomial/fixed-pole
family. It may also be vacuous for a comparator whose allowed locus already
contains all relevant poles.

Keep T-F generic and conditional until the independent primary-source audit
freezes an actual comparator family and its learned scale. Even then, it is a
representation nonidentity lemma, not evidence of efficiency, trainability,
or empirical superiority. Appendix placement is preferable unless Gate C
shows that the distinction has measurable consequences.

### 9. NeurIPS clarity and page budget require triage

A full draft build after BibTeX has 21 pages; the limitations/conclusion begins
on main-text page 10 before the bibliography. The theory section currently
places nearly every supporting lemma in the main body. For an A* review, the
strongest main-text chain is:

1. mapped root geometry and phase-to-amplitude split;
2. complete exact isometry plus adjoint synthesis;
3. finite-order frame defect tied to measurable operator error;
4. one concise proposition delimiting oversmoothing/oversquashing inference.

Weighted Parseval, packet recovery, finite-spectrum Product-sum interpolation,
T-F, the perturbation lemma, and detailed locality accounting can be moved to
the appendix unless later evidence makes one central. The visible
"paper-blocked" paragraph is useful internally but must be removed from the
submission only after the gate actually passes.

## Theorem-by-theorem audit and claim classification

| Result | Classification | Independent assessment | Paper decision |
|---|---|---|---|
| Root admissibility | **PROVED** | Radial logits give modulus below `r_max`; `phi(mu+i gamma)` is in the disk iff `gamma>0`. The paper must restore `mu in [0,2]` for in-spectrum semantics. | Retain as setup, not novelty. |
| Mapped zero/pole and phase derivative | **PROVED** | Rational form, conjugate pole, Poisson-kernel chain rule, and Lorentzian law are correct. Product derivatives add on a continuous branch. | Retain as geometric foundation. |
| Exact factor unitarity and one-level split | **PROVED; algebraically standard** | Functional calculus of a unit-modulus scalar gives a unitary operator; the half-split Gram identity follows immediately. `P^+/-` are not projections. | Retain as a construction property, not headline novelty alone. |
| T-A pointwise multilevel partition | **PROVED; algebraically standard** | The backward scalar recurrence is correct for every real frequency. Residual-first atom order is consistent mathematically. | Retain, but use "pointwise paraunitary" only after the local definition. |
| Additive reconstruction | **PROVED; REDUNDANT** | Holds for any shared exact or approximate factor without unitarity. | State briefly and never market as perfect-reconstruction novelty. |
| T-C multilevel isometry/conditioning | **PROVED under fixed roots and self-adjoint `L`** | Telescoping proves `A_D^* A_D=I`; all nonzero/input-domain singular values are one. `A_D A_D^*` is generally a proper projection. | Main structural guarantee after Gate A. |
| Adjoint synthesis | **PROVED for exact analyzed coefficients** | Backward induction is valid once the terminal state is initialized. Approximate adjoint synthesis returns `tilde A_D^* tilde A_D h`, not an inverse in general. | Main guarantee; repair notation and initialization. |
| T-B weighted Parseval | **PROVED WITH ADDITIONAL ASSUMPTIONS** | Positivity and commutation with every level are sufficient; `W=w(L)` is safe. A node projector is correctly excluded. | Supporting result, not nodewise conservation. |
| Nodewise coefficient lower bound | **PROVED; weak and REDUNDANT** | Follows from rowwise additive reconstruction and Cauchy--Schwarz, including shared approximate channels. | Corollary/limitation only; not anti-oversmoothing. |
| Energy separation and packet recovery | **PROVED; elementary** | Orthogonal spectral decomposition gives the inequalities and squared recovery bound. The finite perturbation term is correct. | Supporting mechanism observable, not achievability or trainability. |
| T-E Chebyshev interpolation bound | **PROVED WITH ADDITIONAL ASSUMPTIONS** | The ellipse restriction and `4 M_rho rho^{-K}/(rho-1)` bound are coherent; `M_rho` is indispensable. Pole distance does not determine realized error alone. | Retain with citation and reduced-pole wording; title must not imply pole-only prediction. |
| T-D heterogeneous multilevel frame defect | **PROVED WITH ADDITIONAL ASSUMPTIONS** | Re-derivation gives `e_l <= d_l+c_l e_{l+1}` and the stated prefix-product `Delta_D`. No commutation is needed. Positive lower bound only follows for `Delta_D<1`. | Strong main approximation theorem after true operator-norm validation. |
| Product-sum finite-spectrum interpolation | **PROVED WITH SCOPE LIMITS** | At the zero-root closure the evaluation matrix is Vandermonde; continuity supplies small nonzero admissible witnesses. It uses `m` terms for `m` distinct eigenvalues and can be arbitrarily ill-conditioned. | Appendix expressivity fact, not efficiency. Clarify the vacuous `m=1` edge case. |
| T-F reduced-pole separation | **PROVED WITH ADDITIONAL ASSUMPTIONS; contribution SUGGESTIVE ONLY** | Meromorphic identity forces reduced pole multisets to agree on a continuum. The theorem says nothing about a finite spectrum or approximation. | Keep conditional and baseline-agnostic pending novelty review. |
| T-G fixed-root operator perturbation | **PROVED WITH ADDITIONAL ASSUMPTIONS** | The resolvent identity yields the stated one-factor constant; unitary telescoping sums constants for a product. It is not an edge-edit/retraining theorem. | Supporting theorem; prefer "operator perturbation" over unqualified graph stability. |
| T-H locality | **PROVED** | A degree-`K` polynomial is at most `K`-hop localized and sequential degrees add. Exact nonpolynomial rational filters are generally global. | Retain with cost assumptions made explicit. |
| Exact global Jacobian norm | **PROVED** | For fixed roots, the Jacobian is the isometric complete analysis map. | Complete-output statement only. |
| Carried-state non-dissipation | **FALSE / REMOVE** | A real root sends the zero mode entirely to the residual in one level. | Preserve the counterexample. |
| Practical anti-oversmoothing | **UNSUPPORTED / EMPIRICAL ONLY** | Isometry does not preserve node rank, class separation, a narrow readout, or the carry. | Block pending depth experiments. |
| Universal source-to-target sensitivity | **FALSE / REMOVE** | The `r -> 1` connected witness, disconnected graphs, and finite-hop polynomial zeros are valid counterexamples. | Preserve the negative boundary. |
| Oversquashing mitigation from tightness | **FALSE / REMOVE** | Global norm preservation supplies no target-block lower bound. | No positive claim without dedicated math and experiments. |

## Adversarial proof checks

### Phase and mapped geometry

Direct substitution confirms

`B_alpha(phi(lambda)) = ((1-alpha)lambda-i(1+alpha)) /
((1-conj(alpha))lambda+i(1+conj(alpha)))`.

The mapped zero is in the upper half-plane and the pole is its conjugate. A
finite-difference check at generic complex and near-cap roots agreed with both
forms of the derivative. No sign or conjugation counterexample was found.

### Multilevel frame recurrence

Writing the tail frame operator as

`S_l = P_l^-* P_l^- + P_l^+* S_{l+1} P_l^+`

gives

`||S_l-I|| <= d_l + ||P_l^+||^2 ||S_{l+1}-I||`

with `||P_l^+||^2 <= c_l`. Unrolling amplifies the level-`l` defect by the
preceding carry factors, exactly matching
`sum_l d_l product_{j<l} c_j`. I also searched 2,000 randomized noncommuting
complex matrix cascades (depths 1--6, per-level errors up to 1.2) and found no
bound violation; the largest observed defect-to-bound ratio was approximately
0.970. This numerical search is a diagnostic, not the proof or Gate-A
evidence.

### Product-sum theorem

The zero-root point is outside the finite-logit parameter image but belongs to
its closure. Since the determinant is nonzero there, continuity gives an open
neighborhood containing representable nonzero roots. The theorem therefore
does not rely on attaining zero. It still provides no uniform lower singular
value, and clustered eigenvalues furnish the expected ill-conditioning
counterexample.

### Pole separation and perturbation

T-F survives the finite-spectrum counterexample because it explicitly demands
equality on an interval. T-G survives noncommuting `L,L'` because the resolvent
identity does not require them to commute. The product estimate is valid
because every surrounding exact factor at either operator has norm one.

### Oversmoothing and oversquashing boundaries

The counterexamples are logically sufficient. In particular, the connected
`r -> 1` family is stronger than relying only on disconnected components, and
the Chebyshev reach example prevents exact-target globality from being
transferred to the finite realization. No positive anti-oversquashing theorem
is admissible from the reviewed results.

## Exact versus Chebyshev and reconstruction semantics

The patch generally makes the correct distinctions:

- mapped poles belong to the exact rational target, not the polynomial;
- exact complete analysis is Parseval, whereas finite analysis has a measured
  frame defect;
- additive reconstruction survives shared approximate channels;
- approximate adjoint synthesis is not generally an inverse;
- the complete tuple and carried state are separate objects.

The remaining defects are the undefined approximate channel notation, the
missing synthesis terminal condition, and the implementation's current
carry-first public order. These must be repaired before the prose can be
called contract-aligned.

## Cross-references, build, and presentation evidence

- A static scan found 60 labels, 55 references, no duplicate labels, and no
  undefined reference keys.
- A complete `pdflatex -> bibtex -> pdflatex -> pdflatex` draft-graphics build
  succeeds. After BibTeX there are no undefined references or citations.
- Remaining build warnings are two absent pre-existing figure PDFs and a few
  underfull boxes in tables/checklist material.
- The resulting PDF is 21 pages, with the conclusion starting on main-text
  page 10 before references. The patch therefore needs theorem triage and
  compression for conference form.
- `git diff 7b790989^ 7b790989 --check` passes.

## Mandatory fixes before independent re-review

1. Merge and test residual-first order through API, readout, synthesis,
   flattening, serialization, and artifacts.
2. Enforce the graph contract in code: core rejection plus a separate recorded
   reciprocal-mean preprocessor.
3. Pass all GA-00--GA-35 rows with an independent dense oracle and immutable
   provenance; update the stale experiment test inventory.
4. Restore `mu in [0,2]`, bounded positive `gamma`, and explicit target-pole
   margin semantics.
5. Define exact/approximate synthesis notation, set the terminal condition,
   and remove the Fourier/synthesis hat collision.
6. Condition the `DK` SpMV equality on the canonical full recurrence and
   instrument it.
7. Cite the exact Chebyshev interpolation theorem and clean the listed norm,
   disk, angle, and frame-bound notation.
8. Keep T-F baseline-agnostic and non-headline until the primary-source
   novelty audit is complete.
9. Align the abstract, introduction, results, and conclusion with the actual
   gate state before removing the internal draft marker.
10. Compress the main theory to the central claim chain and move supporting
    results to the appendix.

## Final recommendation

Do not reject the mathematical direction. Do reject any attempt to treat this
commit as a verified submission theory section. After the two paper--code
contradictions and the reconstruction/center-width issues are repaired, the
proof patch is a credible basis for Gate-A verification. The likely strongest
defensible theory contribution is not the generic unitary split itself, but
the combination of learned Blaschke target geometry, complementary
phase-to-amplitude analysis, exact complete-map conditioning, and a measurable
finite-realization frame defect. Whether that combination is novel enough
remains a separate primary-source and matched-experiment question.
