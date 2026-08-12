# A* Reference and Baseline Matrix

The Reviewer Agent must verify final bibliographic metadata and official code versions before the bibliography freeze. The table below defines why each work matters to GBDN and what obligation it creates.

## Core spectral and filter-bank works

| Work | Venue/status | Relevance | GBDN obligation |
|---|---|---|---|
| ChebNet | NeurIPS 2016 | Sparse Chebyshev spectral filtering | Match degree/SpMV; distinguish direct polynomial coefficients from movable poles |
| BernNet | NeurIPS 2021 | Flexible Bernstein spectral response | Include in response-fitting or heterophily comparison |
| ChebNetII | NeurIPS 2022 | Stable Chebyshev interpolation parameterization | Verify coefficient convention; include strong polynomial baseline |
| Framelets/graph framelet work | ICML 2021 and related | Tight multiscale graph representations | Do not claim first tight graph analysis; state learned Blaschke-root distinction |
| CayleyNets | IEEE TSP, foundational exception | Complex rational Cayley filters | Prove/measure movable-pole distinction; mandatory baseline |
| Graph-QMF and perfect-reconstruction graph banks | foundational exception | Classical graph perfect-reconstruction filter banks | Do not claim first graph PR bank; explain nonsubsampled learned-root contribution |

## Stability, unitarity, and depth

| Work | Venue/status | Relevance | GBDN obligation |
|---|---|---|---|
| A-DGN | ICLR 2023 | Antisymmetric stable graph dynamics | Distinguish state/Jacobian non-dissipation from coefficient-map tightness |
| Unitary Convolutions | NeurIPS 2024 | Same-dimensional unitary graph propagation and oversmoothing theory | Mandatory theoretical comparison; compare carried state versus redundant coefficient map |
| Stable-ChebNet / Return of ChebNet | NeurIPS 2025 | Stable non-dissipative Chebyshev dynamics and long-range evaluation | Include depth/long-range baseline and separate mathematical objects |
| On Vanishing Gradients, Over-Smoothing, and Over-Squashing in GNNs | NeurIPS 2025 | Jacobian and sensitivity perspective | Use target-specific sensitivity framework |
| Are We Measuring Oversmoothing Correctly? | ICLR 2026 | Rank-based oversmoothing measurement | Report numerical/effective rank, not energy alone |
| Demystifying Oversmoothing, Oversquashing, Heterophily, and Long-Range | ICLR 2026 | Separates graph-learning phenomena | Structure experiments and claims independently |

## Heterophily

| Work | Venue/status | Relevance | GBDN obligation |
|---|---|---|---|
| H2GCN | NeurIPS 2020 | Strong heterophily-specific architecture | Verified baseline |
| LINKX | NeurIPS 2021 | Strong non-homophilous baseline | Include when compatible |
| EvenNet | NeurIPS 2022 | Spectral heterophily filtering | Extended spectral baseline |
| Critical Evaluation under Heterophily | ICLR 2023 | Defines replacement datasets, splits, metrics, and evaluation problem | Follow official protocol exactly |
| Characterizing Graph Datasets for Node Classification | NeurIPS 2023 | Beyond raw edge homophily | Report adjusted homophily, label informativeness, and feature–label alignment |
| Understanding Heterophily for GNNs | ICML 2024 | Nuanced heterophily mechanisms | Avoid equating heterophily with high frequency |
| UniFilter | ICML 2024 | Adaptive universal polynomial bases | Compare adaptive spectral expressivity |
| SLOG | ICML 2024 | Non-polynomial spectral parameterization | Distinguish rational root geometry and tight analysis |
| HeroFilter | NeurIPS 2025 | Non-monotone optimal spectral responses | Analyze learned response on empirical spectrum |
| WaveGC | ICML 2025 | Learned graph spectral wavelets and short/long-range separation | Mandatory mechanism/response-efficiency baseline when verified |

## Long-range benchmarks

| Work | Venue/status | Relevance | GBDN obligation |
|---|---|---|---|
| LRGB | NeurIPS 2022 Datasets & Benchmarks | Official long-range graph tasks and evaluators | Use official pipeline for long-range graph claims |
| GraphGPS | NeurIPS 2022 | Common scalable graph benchmark framework | Use or interoperate when integrating LRGB/WaveGC |

## Expressivity limitations

| Work | Venue/status | Relevance | GBDN obligation |
|---|---|---|---|
| Spectral GNNs Are Incomplete on Graphs with a Simple Spectrum | NeurIPS 2025 | Limits of scalar spectral architectures | State that movable poles do not remove all Laplacian-functional expressivity limits |

## Blaschke inspiration

| Work | Venue/status | Relevance | GBDN obligation |
|---|---|---|---|
| Practical Blaschke decomposition for nonstationary signals | arXiv/foundational inspiration | Phase unwinding and practical signal analysis | Do not call it the original Blaschke paper; distinguish time analytic-signal machinery |
| Blaschke products and unwinding in higher dimensions | arXiv/foundational inspiration | Higher-dimensional inner functions | Do not imply it proves a graph extension |
| BDN: Blaschke Decomposition Networks | withdrawn ICLR submission | Product-sum architectural inspiration | Label Product-sum GBDN as inspired, not equivalent; disclose status |

## Required comparison questions

For every closest method, the paper or supplement must answer:

1. Is the operator polynomial, fixed-pole rational, movable-pole rational, wavelet, or learned matrix-valued?
2. Is selection encoded in amplitude, phase, or interference?
3. Is the propagated state unitary, contractive, or unrestricted?
4. Is the complete representation tight or reconstructing?
5. Is the realization exact, rational-iterative, or polynomially approximated?
6. What is the matched SpMV and parameter cost?
7. Which phenomenon is directly evaluated: heterophily, depth collapse, bottleneck sensitivity, or long-range task performance?

## Baseline inclusion rule

A paper's importance does not automatically require rerunning it. It creates one of three obligations:

- **THEORY:** explicit mathematical distinction;
- **MECHANISM:** matched controlled filter comparison;
- **PRIMARY BASELINE:** verified downstream implementation;
- **EXTENDED BASELINE:** include if compute and compatibility permit.

The orchestrator records the obligation in the baseline registry before the full run.
