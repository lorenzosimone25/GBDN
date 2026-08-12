# REV-GATEA-PREFLIGHT — independent Gate-A contract review

## Verdict

**BLOCKED pending contract clarification.** The frozen contract is substantially safer than the pre-audit paper and preserves a viable exact mathematical core. It is not yet sufficiently determinate to serve as the implementation and Gate-A acceptance contract. The blockers are definitional: one graph-input policy is still undecided, the linear theorems do not explicitly freeze roots with respect to the analyzed input, `chebyshev-K` realizations are polynomials rather than literal movable-pole operators, and several candidate theorems lack the quantifiers needed for a pass/fail test.

No claim-bearing experiment is admitted. Engineering may implement uncontroversial exact primitives and independent oracles, but should not freeze the public API or theorem tests until the stop-line items below are adjudicated.

Reviewed base: `baaa6183bc607c341610b366ec38fc25ab09888f`, using `sub_plans/01_SCIENTIFIC_CONTRACT.md`, `PHASE0_AUDIT.md`, and `math/phase0_theorem_audit.md`. The canonical `src/gbdn` package and Gate-A tests are not present in this worktree/base, so this is a contract preflight, not an implementation acceptance.

## Scientific decisions under attack

### 1. Paper identity and terminology

The defensible identity is a **learned Blaschke-root-parameterized, nonsubsampled Parseval graph spectral analysis bank**. Calling the whole construction “paraunitary” is risky unless the paper explicitly defines a graph-frequency analysis vector whose Hermitian squared norm is one. In classical signal processing, “paraunitary filter bank” often invokes a polyphase matrix and sampling structure that are absent here. Minimum safe policy:

- lead with “nonsubsampled Parseval-tight spectral analysis bank”;
- define any use of “paraunitary” locally rather than relying on the classical implication;
- never call `P_l^+` or `P_l^-` a projection;
- acknowledge that tightness, additive reconstruction, weighted Parseval, and conditioning follow generically from a unitary split and are not Blaschke-specific novelty.

The theorem count must not substitute for novelty. The potentially distinctive claim is narrower: learned Blaschke roots induce movable poles in an **exact target response**, identity interference converts phase to complementary amplitude responses, and this target can be approximated sparsely with a measurable defect. That distinction still requires prior-work and matched-comparator review.

### 2. Exact, finite, and legacy objects

The realization tags are necessary but not sufficient. A degree-`K` Chebyshev realization is a polynomial and has no finite rational poles. Its saved “mapped poles” are the poles of the exact response it targets, not singularities of the realized operator. Every `chebyshev-K` artifact and paper statement must therefore use wording such as “target mapped poles” or “pole-parameterized target response.” Literal movable-pole language applies to `exact` only.

Exact isometry, exact weighted Parseval, condition number one, and exact adjoint reconstruction must never transfer to `chebyshev-K`. Shared approximate half-channels do retain additive reconstruction, but that is algebraic and not Parseval synthesis. `legacy` remains a different method and cannot validate either object.

### 3. Graph/operator assumptions

The contract says the implementation may either reject invalid graph input or symmetrize it. That is not a frozen policy: different symmetrization rules produce different operators and results. Select one canonical behavior before implementation. Recommended split:

- the mathematical/core operator accepts a prevalidated self-adjoint `L` or rejects violations;
- a separate preprocessing function applies one explicitly named rule (for example, reciprocal mean), records it, and returns the validated operator;
- negative or nonfinite weights are rejected;
- duplicates, self-loops, isolated vertices, normalization, dtype tolerance, and spectral-bound checks are specified.

Theorems require finite-dimensional, aligned, self-adjoint operators. “Graph perturbation stability” is only an operator perturbation result until a separate bound maps edge/weight changes to normalized-Laplacian changes under degree lower bounds.

### 4. Root semantics and linearity

The unrestricted radial-polar parameterization is admissible if `0 < r_max < 1` is validated. In finite precision, sigmoid underflow can produce `alpha=0`; tests and claims should require `|alpha| < 1`, not numerical strict positivity. Root permutation leaves a Blaschke product unchanged and must be tested. Root ordering is non-identifiable and should not be interpreted.

The rejected `alpha=rho phi(mu)` decision is correct: `mu` is only an angular anchor at finite `rho`. The optional `alpha=phi(mu+i gamma)` parameterization does give mapped zero `mu+i gamma`, but needs:

- `mu` constrained to `[0,2]` if it is called an in-spectrum center;
- a positive lower pole-margin `gamma_min`, not merely `gamma>0`;
- declared numerical upper/range policy and extreme-gradient tests;
- comparison with unrestricted radial roots before adoption.

For unrestricted roots whose mapped-zero real part lies outside `[0,2]`, it is misleading to call that point the observed graph-frequency maximum; the maximum over the graph interval occurs at a boundary.

Most importantly, all statements involving a linear map `A_D`, `A_D^*A_D`, singular values, condition number, or Jacobian isometry require `L` and all roots to be fixed independently of the input being analyzed. If roots are ever predicted from `h`, per-input energy identities may remain true while linearity, adjoints, conditioning, and Jacobian claims fail. Freeze “global trainable roots, fixed during each analysis map” in the contract and test that no input-conditioned root path exists in the primary method.

### 5. Coefficient semantics and order

The public order `(r_0,...,r_{D-1},h_D)` is acceptable and must be normative for exact and finite analysis outputs, flattening, diagnostics, saved artifacts, readouts, and synthesis input. An internal final-carry-first representation is permissible only behind named conversion functions.

A shape-only test is insufficient. Use distinct sentinel coefficients or effective atoms to verify index semantics, round-trip flatten/unflatten, public readout concatenation, artifact serialization, and adjoint synthesis. The order itself has no mathematical novelty; its purpose is to prevent silent paper/code/artifact permutations.

## Candidate theorem and claim ledger

| Item | Classification | Preflight decision |
|---|---|---|
| Exact unit modulus and mapped zero/pole formula | `PROVED` | Retain with admissible-root and real-frequency assumptions; standard algebra, not standalone novelty. |
| Exact one-level unitary factor and tight split | `PROVED`, `REDUNDANT` as headline | Retain as construction property. It follows from splitting any unitary operator. |
| Exact multilevel complete-map isometry and adjoint reconstruction | `PROVED` | Retain for fixed roots, self-adjoint `L`, complete tuple, and analyzed lift only. Present as a standard cascade enabled by the construction. |
| Additive reconstruction | `PROVED`, `REDUNDANT` | State separately; holds for exact and shared approximate factors without unitarity. Do not market as perfect-reconstruction novelty. |
| T-A pointwise multilevel partition | `PROVED`, `REDUNDANT` | Strengthen to every real `lambda` for fixed exact all-pass factors. It is the scalar form of the same telescoping identity. |
| T-B weighted spectral Parseval | `PROVED_WITH_ADDITIONAL_ASSUMPTIONS`, `REDUNDANT` | Require positive `W` commuting with every level; `W=w(L)` is safe. Restrict `L^s` to defined nonnegative exponents (or specify pseudoinverse conventions). Include a noncommuting node-projector counterexample. |
| T-C exact conditioning/perturbation isometry | `PROVED` | Define rectangular-map condition number as `sigma_max/sigma_min` on the input domain; state `A_D A_D^* != I` generally. Fixed roots are mandatory. |
| T-C nodewise anti-collapse bound | `PROVED`, `REDUNDANT` | Optional limitation/corollary only. It follows from additive reconstruction, weakens as `1/sqrt(D+1)`, concerns lifted input rows, and says nothing about carried state, rank, classes, normalization, or readout. |
| T-D finite-degree multilevel frame bound | `PROVED_WITH_ADDITIONAL_ASSUMPTIONS` | The math-audit recurrence is plausible for per-level **operator-norm** errors and fixed approximate maps. Freeze the formula, indexing, and `Delta_D<1` condition before tests. Do not estimate epsilon from one signal. |
| T-E localization versus approximation complexity | `PROVED_WITH_ADDITIONAL_ASSUMPTIONS` for components; otherwise not theorem-ready | Exact center/width and Bernstein-envelope statements are valid. “Degree complexity” additionally depends on `M_rho`, chosen ellipse, residues/cancellation, and tolerance. Do not claim monotonicity in root radius or that ellipse parameter alone predicts error. |
| T-F movable-pole separation from Cayley filters | `PROVED_WITH_ADDITIONAL_ASSUMPTIONS` | Define the comparator family, trainable Cayley scale, order, reduced pole multisets, equality on a continuum, and cancellation exceptions. It does not apply to equality on a finite spectrum and proves neither efficiency nor superiority. |
| T-G graph perturbation stability | `PROVED_WITH_ADDITIONAL_ASSUMPTIONS` as an `L`-operator result | Require aligned self-adjoint `L,L'`, fixed roots, spectra in the domain, and positive pole margins for both. Call it graph stability only after bounding graph-to-L perturbation. Standard resolvent analysis, not central novelty. |
| T-H locality and sparse complexity | `PROVED`, `REDUNDANT` | Exact rational response is generally global. Degree `K` is at most `K`-hop; sequential depth `D` is at most `DK`-hop and costs `DK` Laplacian SpMVs for Tight/Product-sum, subject to the actual streaming implementation. Separate relaxed parallel complexity. |
| Product-sum finite-spectrum interpolation | `PROVED`, `REDUNDANT` as headline | Retain as appendix expressivity fact. Test representable nonzero roots, conditioning, solved interpolation, repeated-eigenvalue limitation, and finite-`K` degradation. No parameter-efficiency implication. |
| “Complete exact analysis cannot globally collapse distinct lifted signals” | `PROVED` as injectivity only | Safe if roots are fixed. Avoid “anti-oversmoothing” in the theorem title. |
| Practical oversmoothing resistance | `EMPIRICAL_ONLY` | Block until depth experiments separately measure complete coefficients, carry, bands, and readout. |
| Global perturbation/Jacobian energy preservation | `PROVED` only for the fixed linear exact map | Do not use if roots are input-conditioned; never infer a particular target block. |
| Nonzero source-to-target sensitivity or oversquashing mitigation | `COUNTEREXAMPLE_FOUND`, `DROP_FROM_PAPER` | Preserve the negative boundary. Isometry is compatible with zero/arbitrarily small target sensitivity and finite-hop zeros. |
| Carried-state non-dissipation | `COUNTEREXAMPLE_FOUND`, `DROP_FROM_PAPER` | A real root can annihilate the zero mode in the carried branch while the residual stores it. |
| Heterophily/long-range superiority | `EMPIRICAL_ONLY`, currently unsupported | Outside Gate A and prohibited from the foundational identity. |

## Gate-A test contract

Gate A must test executable contracts, not restate proofs. All dense tests must use an oracle structurally independent from the sparse recurrence and must build full operator matrices (for example, by applying to a basis), not one sampled vector.

### Required before Gate-A review

1. **Convention and roots:** `r_max` validation; extreme finite parameters; denominator conjugation; forward/inverse direction; zeroth Chebyshev coefficient; scalar and spectral unit modulus; multi-root phase additivity; mapped zero/pole/inverse center-width; root-permutation invariance; optional center-width range and gradients.
2. **Graph contract:** reject or explicitly preprocess directed kNN input; negative/nonfinite/asymmetric weights; duplicates and coalescing; weighted/self-loop/isolated conventions; Hermitian residual; spectrum in `[0,2]`; deterministic graph identity.
3. **Exact bank:** dense `||T^*T-I||`; one-level operator identity; pointwise effective-atom partition on a real grid and graph spectra; multilevel energy and adjoint synthesis; exact additive telescoping.
4. **Weighted/conditioning:** `I,L,L^2`, eigenprojectors, and a valid repeated-eigenspace case; explicit failure for a noncommuting node projector; all singular values of dense `A_D`; confirm `A_D^*A_D=I` and that `A_DA_D^*` is generally a projection rather than identity.
5. **Coefficient order:** semantic sentinel/atom order; flatten/unflatten; serialization; readout concatenation; synthesis round trip; explicit tested permutation if any internal order differs.
6. **Graph families/depths:** weighted paths, cycles, grids, stars, disconnected graphs, complete/bipartite or repeated-eigenvalue graphs, and random symmetric graphs at multiple depths and root counts.
7. **Equivariance:** simultaneous permutation of features, edges/weights, Laplacian, every coefficient, synthesis output, and diagnostics.
8. **Sparse versus dense:** full-operator agreement across `K`, roots, graphs, and complex signals; exact coefficient convention; shared-approximate additive reconstruction; approximate adjoint synthesis; no stale graph cache.
9. **Finite frame theorem:** independently compute every `epsilon_l` in operator norm, dense observed `||A_tilde^*A_tilde-I||`, predicted `Delta_D`, singular-value frame bounds, and adjoint reconstruction defect. Test bound preconditions and the `Delta_D>=1` non-guarantee case.
10. **Product-sum:** nonzero roots obtainable from finite raw parameters; evaluation determinant and condition number; recovery of random finite-spectrum multipliers; root permutation/repeated roots; repeated-eigenvalue limitation; exact-versus-finite degradation.
11. **Negative boundaries:** carried-state annihilation; constant-node collapse; noncommuting weighted-energy failure; connected target-sensitivity decay; disconnected and beyond-`DK` exact zeros. These are regression guards against future overclaim.
12. **Optimization/API safety:** all trainable parameters exist before optimizer construction; gradients through radial and optional center-width roots are finite; no input-conditioned roots in Tight GBDN; parameter, SpMV, receptive-field, and memory counts match the stated realization.

Tests must report tolerances, dtype, graph seed, operator dimensions, and realization tag. Passing numerical tests does not prove a theorem or novelty; Gate A additionally requires accepted proofs and paper/code wording correspondence.

## Stop-line issues

1. **Choose one canonical invalid-graph policy.** “Reject or symmetrize” is scientifically underdetermined.
2. **Add the fixed-root/fixed-operator assumption** to every linear, adjoint, conditioning, and Jacobian statement.
3. **Qualify paraunitary terminology** and lead with nonsubsampled Parseval analysis.
4. **Separate exact target poles from polynomial realization semantics** in code, diagnostics, artifacts, and prose.
5. **Freeze T-D, T-F, and T-G statements with complete hypotheses** before engineering encodes acceptance tests.
6. **Constrain and test optional `phi(mu+i gamma)` numerically**, including a positive pole margin; keep it an ablation.
7. **Make coefficient order executable across the full provenance path**, not only a prose convention.
8. **Merge/version the canonical source and Gate-A suite.** They are absent at the reviewed base, so independent implementation review is impossible.

## Readiness assessment

The scientific direction is viable, but the Gate-A contract is **not ready to pass or to authorize claim-bearing H100 work**. The top risk is presenting generic unitary-split identities and finite polynomial approximations as Blaschke-specific paraunitary/movable-pole novelty. The highest-leverage next fix is to adjudicate the eight stop-line definitions, then implement the independent full-operator test matrix above.
