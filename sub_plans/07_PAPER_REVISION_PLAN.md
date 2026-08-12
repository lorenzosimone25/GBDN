# Paper Revision Plan

## Goal

Convert the current foundational draft into a coherent A* submission whose method, theorems, implementation, experiments, and generated artifacts agree exactly.

## Proposed title

Primary candidate:

> **GBDN: Learned Movable-Pole Paraunitary Filter Banks for Graph Spectral Learning**

Alternative after strong heterophily/long-range evidence:

> **Learned Blaschke–Cayley Filter Banks for Heterophilic and Long-Range Graph Learning**

Retain the GBDN acronym, but define the method as Blaschke-inspired rather than a direct transfer of classical phase unwinding.

## Abstract

The final abstract should contain only four elements:

1. limitation of direct polynomial/fixed-pole spectral parameterizations;
2. movable Blaschke roots and phase-to-amplitude complementary channels;
3. the strongest accepted structural guarantees;
4. the strongest confirmatory empirical result.

Remove preliminary single-run H100 diagnostics from the final abstract once confirmatory results exist.

Do not mention oversquashing or long range unless the dedicated gate passes.

## Section 1 — Introduction

### Keep

- motivation for interpretable rational phase geometry;
- all-pass phase cannot attenuate by itself;
- selection emerges through interference with identity;
- clear distinction from PDU and graph analytic signals.

### Add

- explicit paraunitary/filter-bank framing;
- precise novelty over CayleyNets and unitary convolutions;
- claim hierarchy;
- a one-paragraph explanation of why heterophily, oversmoothing, and oversquashing are evaluated separately.

### Contribution order

1. learned movable-pole Blaschke–Cayley graph parameterization;
2. paraunitary multilevel analysis and accepted new theorems;
3. finite-order pole-aware realization;
4. mechanism and official benchmark evidence.

## Section 2 — Preliminaries

Lock:

- self-adjoint graph scope;
- exact Cayley/Blaschke convention;
- root parameterization;
- exact versus finite-order notation;
- Chebyshev coefficient convention;
- graph functional calculus.

Add a compact notation table if space permits.

## Section 3 — Method

### 3.1 Tight GBDN

Present:

- lifted complex features;
- exact factor;
- complementary channels;
- sequential analysis;
- complete coefficient tuple;
- downstream readout.

### 3.2 Synthesis

Separate:

- additive telescoping identity;
- adjoint synthesis from Parseval tightness;
- what is and is not reconstructed.

### 3.3 Product-sum GBDN

Present as the expressive secondary variant.

### 3.4 GBDN+

Present as a relaxed empirical ablation with no structural guarantee.

### 3.5 Sparse realization

Explain:

- finite \(K\);
- streaming recurrence or Clenshaw;
- locality;
- SpMV count;
- graph identity;
- memory.

### Optional 3.6 learned unitary routing

Include only if accepted by the Math Agent, implemented, and empirically justified.

## Section 4 — Theory

Recommended main-paper order:

1. phase localization and mapped pole geometry;
2. exact unitary factor and one-level tightness;
3. pointwise multilevel paraunitary partition;
4. weighted Parseval/non-dissipation;
5. conditioning, perturbation isometry, and limited anti-collapse;
6. finite-order multilevel frame stability;
7. localization–approximation trade-off;
8. movable-pole distinction from fixed-pole Cayley filters;
9. graph perturbation stability;
10. scope of oversmoothing and oversquashing claims.

Move to appendix when page-limited:

- full proofs;
- finite-spectrum Product-sum interpolation;
- optional unitary routing proof;
- extended perturbation constants;
- auxiliary lemmas.

## Section 5 — Experiments

Organize by questions, not datasets.

### 5.1 Can the implementation satisfy the mathematical contract?

Report exact and finite-order diagnostics.

### 5.2 Do movable roots provide useful phase-sensitive filters?

Report the sphere/point-cloud mechanism study and root/pole geometry.

### 5.3 Are movable poles efficient relative to alternatives?

Report matched response-efficiency.

### 5.4 Do the filters improve official heterophily tasks?

Report the frozen multi-split, multi-seed table and paired analysis.

### 5.5 What happens at depth?

Report complete coefficients versus carried state, rank, and performance.

### 5.6 Do they improve target-specific long-range propagation?

Report controlled oversquashing and optional LRGB.

The preliminary legacy table should move to an appendix titled “Legacy reproduction audit” or be removed from the final submission after the new table exists.

## Section 6 — Related work

Use subsections:

1. polynomial and rational graph filters;
2. graph filter banks, wavelets, and framelets;
3. stable and unitary graph propagation;
4. heterophily and adaptive spectral responses;
5. Blaschke and phase-unwinding inspiration;
6. long-range and oversquashing evaluation.

For every closest paper, state one precise shared element and one precise distinction.

## Section 7 — Limitations

Retain and expand:

- exact linear analysis versus nonlinear network;
- full coefficient tuple versus carried state;
- finite-order frame defect;
- root/pole approximation trade-off;
- output-width and memory growth;
- scalar functions of a self-adjoint Laplacian;
- repeated eigenvalue limitations;
- target-specific oversquashing not guaranteed;
- transductive/static graph scope;
- compute and baseline coverage;
- optional application generalization.

Negative experimental findings belong here and in the results discussion, not only in an appendix.

## Figures

### Figure 1 — Method

A clean schematic:

```text
real features -> complex lift -> Cayley/Blaschke factor
             -> complementary phase-interference split
             -> emitted residual bands + carried branch
             -> complete coefficient stack -> readout
```

Show roots in the unit disk, mapped poles, and one spectral response.

### Figure 2 — Mathematical mechanism

Combine:

- pointwise partition of unity;
- exact versus finite-order frame error;
- pole margin versus approximation degree.

### Figure 3 — Controlled recovery

Use median/prespecified run plus aggregate uncertainty. Do not show only the best run.

### Figure 4 — Matched response efficiency

Error versus SpMVs/parameters, with pole geometry inset.

### Figure 5 — Official heterophily

Main table may be accompanied by split-level paired-difference plots.

### Figure 6 — Depth and long-range

Separate panels for rank/oversmoothing and source-target sensitivity/oversquashing.

## Tables

Generated only:

- method positioning;
- mathematical guarantees and scope;
- mechanism results;
- response-efficiency;
- official heterophily;
- depth/long-range;
- compute;
- ablations.

## Generated-result binding

The paper includes:

```latex
\input{generated/heterophily_table.tex}
\input{generated/mechanism_table.tex}
\input{generated/depth_table.tex}
\input{generated/compute_table.tex}
```

Figures are referenced from `paper/generated/figures/`.

No reported number may be typed manually after the result freeze.

## Claim editing workflow

1. Math Agent proposes theorem patch.
2. Reviewer Agent checks proof and scope.
3. Software artifacts validate observables.
4. Orchestrator merges accepted theorem text.
5. Results are generated.
6. Reviewer Agent checks interpretation.
7. Orchestrator promotes only accepted claims into abstract/introduction/conclusion.

## Page-budget guidance

Main paper priority:

1. method;
2. central theory;
3. mechanism;
4. official primary results;
5. depth/oversquashing;
6. limitations.

Move implementation detail, full hyperparameters, auxiliary tables, proofs, and legacy audit to appendix/supplement.

## Final paper checks

- one canonical method definition;
- no use of “projection” for \(P^\pm\);
- no conflation of heterophily and long range;
- no best-seed figure;
- no manual table values;
- every theorem has assumptions and proof;
- every primary result has uncertainty and compute;
- code and paper versions are recorded;
- all limitations match the final evidence.
