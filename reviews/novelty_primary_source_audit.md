# REV-NOVELTY-001 — Primary-source novelty audit

**Audit date:** 2026-08-12
**Repository base:** `8a41705e83e4629dbc49bb83bb815cc5770e116c`
**Decision:** **BLOCKED for claim-bearing novelty language; the construction may proceed to mechanism validation.**

## Executive verdict

The present defensible identity is narrower than the draft's broad filter-bank and
stability language:

> GBDN combines independently learned Blaschke all-pass factors, whose disk roots
> map to generic lower-half-plane poles, with complementary `I±T` channels and a
> redundant, nonsubsampled multilevel coefficient stack that is exactly isometric
> for the exact spectral operator.

No mandatory comparator audited here was found to combine all three ingredients.
That is a plausible construction-level distinction, not yet a sufficient A* result.
The Parseval/reconstruction identity is algebraically automatic once `T` is unitary,
and tight/perfect-reconstruction graph filter banks and undecimated graph framelets
are established prior art. The paper therefore needs matched evidence that the free
pole geometry buys response quality, parameter efficiency, sparse-operator
efficiency, or a useful inductive bias. Without that evidence, an A* reviewer can
reasonably characterize the method as an elegant recombination of known ingredients.

Two corrections are stop-line issues:

1. CayleyNet does **not** have globally fixed poles. Its scale `h>0` is optimized in
   training. A scalar order-`r` filter has a learned but restricted shared pole locus
   at `±i/h` (the analytic half has `-i/h`), whereas GBDN permits independently
   learned generic lower-half-plane poles.
2. Graph-QMF is a critically sampled, down/up-sampled bipartite graph filter bank
   with alias-cancellation conditions. GBDN's complete `(r_0,...,r_{D-1},h_D)` stack
   contains `D+1` full graph signals and is redundant/nonsubsampled. They are not the
   same sampling architecture. Undecimated graph framelets are the closer precedent
   for the complete tight stack.

## Object being compared

The exact GBDN target uses

```text
phi(lambda) = (lambda-i)/(lambda+i)
B_alpha(z) = (z-alpha)/(1-conj(alpha) z),  |alpha|<1
T_R = B_R(phi(L))
P_- = (I-T_R)/2,  P_+ = (I+T_R)/2.
```

For one root, the exact scalar factor is

```text
B_alpha(phi(lambda)) =
  ((1-alpha)lambda-i(1+alpha)) /
  ((1-conj(alpha))lambda+i(1+conj(alpha))).
```

Its pole is

```text
p_alpha = -i(1+conj(alpha))/(1-conj(alpha)),
```

which ranges over the lower half-plane as `alpha` ranges over the unit disk. For
`alpha=a+ib`,

```text
Re p_alpha = -2b / ((1-a)^2+b^2),
Im p_alpha = -(1-|alpha|^2) / ((1-a)^2+b^2) < 0.
```

This pole statement applies only to the **exact rational target**. A finite Chebyshev
realization is a polynomial in the chosen rescaled graph operator and has no literal
finite poles. It approximates a target whose poles control approximation difficulty.
Any sentence assigning movable poles to the finite polynomial implementation is
false and must be removed.

The one-level identity

```text
||P_-x||^2 + ||P_+x||^2 = ||x||^2
```

follows immediately from `T_R^*T_R=I`; the multilevel identity telescopes. These are
correct and useful conditioning statements, but the proof mechanism is not itself a
novel filter-bank theorem.

## CayleyNet adjudication

The primary CayleyNet paper defines, in Eq. (3), printed p. 4,

```text
g_{c,h}(lambda) = c_0 + 2 Re sum_{j=1}^r
                   c_j ((h lambda-i)/(h lambda+i))^j,
```

with real `c_0`, complex `c_j`, and `h>0`. Eq. (4) and the surrounding optimization
text on the same page state that both `c` and `h` are optimized during training.
Section 3.2, printed pp. 5–6, explains the spectral zoom induced by `h`.

Let `q_h(z)=(hz-i)/(hz+i)`. On the real axis the published real response has the
rational continuation

```text
G(z)=c_0 + sum_j [c_j q_h(z)^j + conj(c_j) q_h(z)^(-j)].
```

For effective order `r>0`, uncancelled poles are confined to the conjugate pair
`{-i/h,+i/h}`; the analytic half `sum_j c_j q_h^j` has the lower-axis pole `-i/h`.
Thus the accurate comparison is:

| Family | Pole freedom of one scalar filter |
|---|---|
| CayleyNet | `h` is learned; all Cayley powers share a restricted imaginary-axis locus (`±i/h` for the real response). |
| Exact GBDN | Each admissible Blaschke root independently selects a generic lower-half-plane pole; factors need not share center or width. |

The draft phrase “fixed-pole Cayley filters” is false unless `h` has explicitly been
frozen. “No free roots” is also unsafe: learned Cayley coefficients can induce
numerator zeros and band selectivity. The defensible distinction is **independently
parameterized Blaschke all-pass roots and generic pole locations versus a learned,
shared, restricted Cayley pole locus**.

### Permitted exact non-equivalence corollary

A narrowly stated theorem can proceed:

> For one published scalar finite-order CayleyNet filter with `h>0`, or a frozen
> finite collection of them, every uncancelled pole of its rational continuation is
> on the imaginary axis. An exact GBDN response with an uncancelled off-axis pole
> cannot equal such a scalar response on a real interval with an accumulation point.

It needs the identity theorem for rational functions and must state: scalar response,
finite order, continuum equality, no pole cancellation, and the exact—not finite
Chebyshev—GBDN target. It does **not** establish separation on a finite graph spectrum,
approximation-rate superiority, network-level non-equivalence, or empirical benefit.

There is also an object mismatch: CayleyNet publishes a real-valued response, whereas
GBDN's `P_±` may be complex before real/imaginary feature handling. A matched response
experiment must compare against the analytic Cayley half or allocate sufficient real
Cayley channels to represent both real and imaginary parts.

## Mandatory comparator verdicts

| Family | Primary-source overlap | Defensible distinction | Mandatory role | Reviewer verdict |
|---|---|---|---|---|
| Graph-QMF | Critically sampled two-channel graph bank; PR, orthogonality, alias cancellation; polynomial approximation. | GBDN is redundant/nonsubsampled and has no down/up-sampling or alias-cancellation theorem. | Theory/related work. | Blocks any “first graph PR/filter bank” claim. |
| Undecimated graph framelets | Tight multiscale decomposition/reconstruction with full-resolution low/high coefficients and Chebyshev realization. | GBDN learns rational all-pass phase geometry through Blaschke roots. | Theory; mechanism if learned decomposition is claimed. | Closest prior art for the complete tight stack; blocks “first nonsubsampled tight graph representation.” |
| CayleyNet | Complex-coefficient rational Cayley filters; learned spectral scale and sparse Jacobi approximation. | GBDN has independent generic poles and complementary all-pass split. | Theory, Gate B, matched Gate C baseline. | Closest pole-family comparator; mandatory before movable-pole efficiency claims. |
| ChebNet | Localized sparse polynomial graph filters with linear edge complexity. | Exact GBDN target is rational; deployed approximation remains polynomial. | Historical context and matched SpMV/order control. | Mandatory control for whether rational target geometry helps finite-order approximation. |
| ChebNetII | Learnable Chebyshev interpolation coefficients for flexible polynomial filters. | Blaschke roots constrain a rational all-pass target rather than directly learning interpolation ordinates. | Gate B/C primary baseline. | Mandatory strong polynomial comparator. |
| BernNet | Bernstein polynomial basis designed to fit flexible low/high/band-rejection/comb responses. | Different constrained parameter geometry; no exact all-pass split. | Gate B/C primary or extended baseline. | Blocks vague “arbitrary band-shape” novelty. |
| GPR-GNN | Adaptive signed polynomial propagation weights and heterophily-oriented filtering. | Free roots/poles rather than free polynomial propagation weights. | Mechanism and heterophily baseline. | Blocks “first adaptive spectral filter” and weak heterophily novelty. |
| UniFilter | Adaptive homophily/heterophily polynomial basis. | All-pass phase-to-amplitude construction and complete isometry. | Mechanism and heterophily primary/extended baseline. | Mandatory if heterophily adaptation is central. |
| SLOG | Real-valued adaptive non-polynomial spectral filter with geometric interpretation and inductive sampling. | Different non-polynomial family; GBDN supplies an exact all-pass coefficient isometry. | Theory and mechanism; experiment if reproducible official implementation is available. | Blocks “first non-polynomial/adaptive spectral GNN.” |
| WaveGC | Multiresolution spectral bases, wavelet admissibility, odd/even Chebyshev decomposition, long-/short-range motivation. | Root-controlled rational phase geometry and exact complementary split. | Theory, mechanism, long-range/primary comparator. | Mandatory for multiresolution and long-range positioning. |
| HeroFilter | Adaptive polynomial patch filters motivated by nonmonotone heterophily/filter relationships. | Different local polynomial/mixing architecture. | Heterophily related work and primary/extended baseline. | Blocks simplified “heterophily means high frequency” language. |
| Unitary Convolutions | Same-dimensional unitary graph propagation via a matrix exponential; anti-oversmoothing analysis. | GBDN proves isometry of a redundant complete coefficient stack, not necessarily the carried state. | Theory and depth baseline. | Blocks “first unitary graph propagation” and automatic anti-oversmoothing claims. |
| A-DGN | Stable, non-dissipative antisymmetric graph ODE dynamics and long-range tasks. | Dynamical/Jacobian guarantee versus coefficient-stack isometry. | Depth and long-range baseline. | Mandatory for non-dissipation/long-range claims. |
| Stable-ChebNet | Stable, non-dissipative Chebyshev graph dynamics with long-range evaluation. | State-dynamics stability versus exact analysis-map conditioning. | Depth and long-range baseline. | Mandatory for stable Chebyshev and long-range positioning. |

Additional mandatory context: Levie, Isufi, and Kutyniok already prove broad
transferability/perturbation results for Cayley-smooth graph filters. A GBDN resolvent
bound may be a useful specialization, but is not the first graph-filter stability
result. The 2026 modified Blaschke-decomposition paper uses Blaschke roots to build a
graph representation of vibration components; it is not a learned Laplacian spectral
bank, but it prevents unqualified “first graph Blaschke” wording.

## Claim ledger

| Proposed claim | Classification | Required action |
|---|---|---|
| Exact one-level complementary energy partition | **PROVED, supporting only** | Keep with explicit exact-unitarity assumption; do not sell the algebraic identity as the central novelty. |
| Exact multilevel complete coefficient isometry | **PROVED, supporting only** | Keep; emphasize redundant complete stack and distinguish carried state. |
| Weighted Parseval for commuting `W=w(L)` | **PROVED, supporting only** | Keep as a consequence of simultaneous spectral diagonalization, not a field-first theorem. |
| First graph PR/tight/paraunitary bank | **FALSE / REMOVE** | Cite graph-QMF and graph-framelet literature. |
| First nonsubsampled tight multiscale graph representation | **FALSE / REMOVE** | Cite undecimated graph framelets. |
| First rational or complex graph filter | **FALSE / REMOVE** | CayleyNet and prior rational graph filters predate GBDN. |
| CayleyNet uses fixed poles | **FALSE / REMOVE** | Replace with learned restricted imaginary-axis pole locus. |
| CayleyNet has no learned roots | **UNSUPPORTED / MISLEADING** | State that it lacks independently parameterized Blaschke all-pass roots; do not deny coefficient-induced zeros. |
| Exact GBDN roots yield independent generic lower-half-plane poles | **PROVED** | Keep for admissible roots and the exact operator only. |
| An uncancelled off-axis exact pole separates GBDN from a scalar finite-order Cayley response on a continuum | **PROVED WITH ASSUMPTIONS** | State the restrictions above; no finite-spectrum or efficiency inference. |
| Movable poles improve response accuracy or parameter/SpMV efficiency | **UNSUPPORTED** | Gate B/C matched distributions over initializations; include CayleyNet, ChebNetII, BernNet, and a non-polynomial comparator. |
| Phase-to-amplitude complementary channels are the first such graph construction | **SUGGESTIVE ONLY** | Describe as the paper's proposed construction, not a “first,” pending broader search. |
| GBDN is the first learnable/adaptive spectral graph filter | **FALSE / REMOVE** | Cite CayleyNet, GPR-GNN, BernNet, ChebNetII, UniFilter, SLOG, and WaveGC. |
| Exact complete-map isometry prevents global coefficient collapse | **PROVED, LIMITED** | Restrict to the complete coefficient map; it does not prove task-relevant state preservation. |
| Tightness/unitarity implies resistance to oversmoothing | **UNSUPPORTED** | Evaluate carried state and learned representations separately against unitary/stable baselines. |
| Tightness/unitarity solves oversquashing or preserves target-specific long-range information | **UNSUPPORTED** | Remove until dedicated sensitivity/bottleneck experiments and mathematics support it. |
| Graph perturbation stability is a new general principle | **FALSE AS A PRIORITY CLAIM** | Position any theorem as a construction-specific bound relative to transferability prior art. |
| The finite Chebyshev implementation has movable poles | **FALSE / REMOVE** | Say it approximates an exact movable-pole target. |
| The combined construction is sufficient A* novelty | **SUGGESTIVE / CONDITIONAL** | Requires a positive matched mechanism/expressivity result plus exact-vs-sparse fidelity. |

## A* stop-line conditions and required evidence

Claim-bearing manuscript revision is blocked until all of the following are true:

1. The CayleyNet row and every “fixed-pole” sentence are corrected.
2. Graph-QMF and undecimated graph framelets are cited and the sampled versus
   nonsampled distinction is explicit.
3. Exact rational targets and finite Chebyshev implementations are never
   object-switched.
4. Gate B compares response fitting across multiple initializations, not a selected
   best run, and reports leakage, recovery error, and finite-order distortion.
5. Gate C includes a matched CayleyNet comparison and strong polynomial controls
   under parameters, sparse matrix-vector products, order, output dimensionality,
   and tuning budget.
6. Oversmoothing language is restricted to what is measured for the complete stack
   and carried state separately; oversquashing language is absent unless dedicated
   sensitivity experiments succeed.
7. The related-work table adds the mandatory families and avoids row entries that
   collapse materially different objects into yes/no labels.

The novelty claim itself may proceed as a hypothesis:

> Independently movable Blaschke poles provide a useful, compact inductive bias for
> learning complementary graph-spectral responses while retaining an exactly
> conditioned complete analysis map.

Its first clause is experimental; its second clause is mathematical. The paper should
not conflate them.

## Bottom line

**Current reviewer recommendation: reject on novelty/evidence positioning if submitted
now; continue through Gate B/C rather than abandon the construction.** The exact
combination appears plausibly distinctive among the mandatory comparators, but
Parseval/reconstruction is prior-art-adjacent and algebraically immediate. The paper
becomes defensible only if movable generic poles deliver a measurable advantage over
the learned restricted Cayley locus and strong polynomial/non-polynomial filters.
