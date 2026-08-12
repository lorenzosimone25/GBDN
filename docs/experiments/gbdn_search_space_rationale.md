# Prespecified GBDN-family screening spaces

**Status:** CPU-audited candidate spaces only. This document does not freeze a
screening seed, trial budget, validation unit, manifest, selected configuration,
or experiment result.

## Scope

The three files under `configs/submission/search_spaces/` prespecify complete
worker configurations for Tight GBDN, Product-sum GBDN, and GBDN+. They are
inputs to the validation-only screening contract. They do not admit any method
to confirmatory execution and do not support a predictive-performance claim.

The spaces deliberately keep the three variants separate. Tight GBDN uses the
complete finite-Chebyshev coefficient representation; Product-sum GBDN uses a
learned sum of cumulative factors; GBDN+ is the relaxed parallel architecture.
Only the first variant is associated with the exact complete-map theory, and
none of the search-space settings transfers exact guarantees to a finite
Chebyshev realization.

## Common training contract

All four currently available methods, including ChebNet, use the same tuned
widths `{32, 64, 128}`, learning rates `{0.001, 0.005, 0.01}`, and weight
decays `{0, 0.0005, 0.005}`. They use Adam with identical betas, epsilon, and
AMSGrad setting; FP32 deterministic execution; at most 1000 epochs; patience
100; zero minimum improvement; earliest-checkpoint tie breaking; no gradient
clipping; and validation-only selection. These choices copy the already frozen
ChebNet optimization contract rather than introducing a method-specific
training advantage.

Dropout is tuned over `{0, 0.3, 0.5}` only for ChebNet and GBDN+, the canonical
models that actually expose dropout. Tight GBDN and Product-sum GBDN have no
dropout field in the worker schema; inventing one in a search file would not be
an executable comparison.

## Sparse-operator tiers

The degree values encode the same reported feature-matrix SpMV tiers
`{2, 6, 10}` per forward pass under the canonical resource counter:

| Method | Fixed structure | Tuned `K` | SpMV formula | Tiers |
|---|---:|---:|---:|---:|
| ChebNet | two ChebConv layers | `{2,4,6}` | `2(K-1)` | `{2,6,10}` |
| Tight GBDN | two sequential levels | `{1,3,5}` | `2K` | `{2,6,10}` |
| Product-sum GBDN | two sequential factors | `{1,3,5}` | `2K` | `{2,6,10}` |
| GBDN+ | one shared basis, two branches | `{2,6,10}` | `K` | `{2,6,10}` |

The differing `K` values are intentional because ChebNet counts `K` basis
terms, while the GBDN implementation counts polynomial degree and recurrence
steps. Matching the integer called `K` would not match sparse operator work.

Two levels/factors are fixed to align the principal sequential depth with
ChebNet's two convolutional layers. One root per factor and the unrestricted
radial upper bound `r_max=0.95` are fixed to the accepted primary
parameterization. The forward Cayley convention is fixed. Depth, root count,
root-family, and radius-bound comparisons remain separate prespecified
ablations; searching them here would spend the equal trial budget on extra
method-only axes and confound the primary comparison.

## Boundedness and limitations

Tight GBDN and Product-sum GBDN each enumerate 81 candidates. GBDN+ enumerates
243 candidates because it exposes dropout; ChebNet also enumerates 243. The
eventual common trial budget therefore cannot exceed 81, but this audit does
not choose that budget. A manifest must later bind an equal integer budget and
the same validation units after Stage-3 runtime and memory measurements.

Equal SpMV tiers, widths, and trial counts do **not** make trainable parameter
counts identical. Tight GBDN's complete-coefficient readout grows with depth,
Product-sum has learned complex combination coefficients, and GBDN+ has a
different nonlinear head. Every screening and confirmatory run must retain the
worker's exact trainable-parameter and SpMV counts. Matched-parameter analyses,
wall-time/memory reporting, and the required architecture ablations remain
separate evidence. The deterministic hash sampler can also give different
marginal coverage when candidate-space sizes differ; this is a limitation of
the equal-trial policy, not a result to conceal.
