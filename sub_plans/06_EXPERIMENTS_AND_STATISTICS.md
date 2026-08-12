# Experiments and Statistical Analysis Plan

The experimental program is claim-driven. Each gate has a distinct scientific question and must not be used as a proxy for another phenomenon.

## Gate A — Exact correctness and finite-order fidelity

### Question

Does the implementation realize the mathematical operators stated in the paper?

### Graph families

- paths;
- cycles;
- complete graphs;
- complete bipartite graphs;
- grids;
- stochastic block models;
- weighted graphs;
- disconnected graphs;
- sphere and point-cloud \(k\)-NN graphs;
- graphs with repeated eigenvalues.

### Depth and degree grid

Example:

```text
D ∈ {1, 2, 4, 8, 16}
K ∈ {4, 8, 16, 32, 64}
```

### Measures

- factor unitarity;
- pointwise partition error;
- complete coefficient energy error;
- \(L\)- and \(L^2\)-weighted energy error;
- additive reconstruction error;
- adjoint synthesis error;
- dense-versus-sparse operator error;
- frame lower/upper empirical bounds;
- singular values and condition number;
- permutation equivariance;
- graph-identity safety.

### Success rule

All exact tests pass at numerical tolerance. Finite-order errors follow the accepted theorem bounds. A failure blocks downstream claims.

## Gate B — Mechanism: phase-sensitive component recovery

### Question

Does learning complex Blaschke phase improve recovery and leakage relative to magnitude-only selection?

### Controlled graph

Retain the sphere \(k\)-NN graph as the main visual mechanism study. Add at least one graph family with a different spectrum.

### Inputs

Construct signals with known spectral components:

- low-frequency component;
- localized packet;
- equal-energy mixture;
- optional multiple packets or notch target.

### Objectives

- magnitude-only band objective;
- complex-response objective.

### Repetitions

At least 10 initializations for final analysis. Five may remain as a pilot.

### Measures

- target recovery NMSE;
- off-target leakage;
- target-band energy retention;
- complex phase error;
- convergence;
- frame and reconstruction errors;
- root and pole trajectories.

### Figure rule

The main visualization uses a prespecified or median-quality run, not the best run. Aggregate uncertainty appears in the same figure or adjacent table.

## Gate C — Matched response efficiency

### Question

Do movable poles provide a measurable representation or computation advantage?

### Target responses

- low-pass;
- high-pass;
- narrow band-pass;
- notch;
- two disjoint bands;
- comb-like response;
- equal-magnitude/different-phase target;
- localized packet response.

### Methods

Minimum:

- Tight GBDN;
- Product-sum GBDN;
- GBDN+;
- CayleyNet;
- ChebNetII;
- BernNet or GPR-GNN;
- WaveGC.

Extended:

- UniFilter;
- SLOG;
- Stable-ChebNet;
- HeroFilter.

### Matching axes

- trainable parameters;
- sparse matrix–vector multiplications;
- effective polynomial degree;
- wall-clock time;
- peak allocated memory.

### Measures

- maximum symbol error;
- graph-signal error;
- phase error;
- convergence;
- robustness to graph perturbation;
- error versus pole margin.

### Decision rule

If GBDN shows no advantage on any matched axis, narrow the novelty claim to structural analysis and reconsider the empirical architecture.

## Gate D — Official heterophily benchmark

### Datasets

- Roman-empire;
- Amazon-ratings;
- Minesweeper;
- Tolokers;
- Questions.

### Official task metrics

| Dataset | Primary metric |
|---|---|
| Roman-empire | accuracy |
| Amazon-ratings | accuracy |
| Minesweeper | ROC-AUC |
| Tolokers | ROC-AUC |
| Questions | ROC-AUC |

### Confirmatory matrix

```text
10 official splits × at least 3 training seeds
```

### Model suites

#### Primary minimum suite

- MLP;
- ResNet;
- residual/normalized standard GNN;
- H2GCN or LINKX;
- ChebNetII;
- CayleyNet;
- GPR-GNN or BernNet;
- A-DGN or Stable-ChebNet;
- WaveGC;
- Tight GBDN;
- Product-sum GBDN;
- GBDN+.

#### Extended suite

- UniFilter;
- SLOG;
- HeroFilter;
- EvenNet;
- Unitary Convolution;
- additional verified methods.

### Tuning

Before full execution, freeze one policy.

#### Policy A: upstream configurations

Use verified official configurations and report this table as upstream-protocol reproduction.

#### Policy B: equal-budget validation search

Use the same number of prespecified validation-only trials per model–dataset pair. Freeze configurations before test execution.

The paper may report both policies, but must not mix them without labels.

### Statistical unit

For method \(m\), dataset \(d\), split \(s\), and seed \(r\), let \(y_{mdsr}\) be the test score.

First compute:

\[
\bar y_{mds}=\frac1R\sum_r y_{mdsr}.
\]

All paired inference compares \(\bar y_{mds}\) across the same splits.

### Primary summary

Report:

- mean over split-level means;
- 95% confidence interval over splits;
- paired mean difference versus each primary comparator;
- paired permutation/randomization test;
- multiplicity-adjusted \(p\)-value;
- win/tie/loss across splits;
- parameter, time, memory, and SpMV counts.

Do not treat the 30 split–seed runs as 30 independent datasets.

## Gate E — Depth and oversmoothing

### Question

How do the complete coefficient representation and carried state behave as depth increases?

### Depths

\[
D\in\{1,2,4,8,16,32,64\}.
\]

Train each depth independently.

### Representations

- input lift;
- complete GBDN coefficient tuple;
- each residual band;
- final carried state;
- Product-sum output;
- GBDN+ output;
- baseline hidden states.

### Baselines

- residual GCN or GraphSAGE;
- Unitary Convolution;
- A-DGN;
- Stable-ChebNet;
- at least one adaptive spectral baseline.

### Measures

- numerical rank;
- effective rank;
- stable rank;
- normalized Rayleigh quotient;
- Dirichlet energy;
- pairwise cosine similarity;
- class separation;
- linear-probe accuracy;
- training gradient norms;
- Jacobian singular-value summaries;
- task performance.

### Claim rule

Only the complete exact linear coefficient analysis may use the isometry argument. Practical no-oversmoothing claims require the observed depth results.

## Gate F — Oversquashing and long-range propagation

### Question

Does GBDN improve target-specific information transfer across distance or graph bottlenecks?

### Controlled topologies

- path;
- ring;
- balanced tree;
- grid;
- barbell;
- lollipop;
- two communities connected by a bridge;
- variable bridge width;
- variable shortest-path distance.

### Tasks

Use tasks where the target label depends explicitly on distant source information. Examples may include:

- source-bit transfer;
- parity or comparison across distant nodes;
- graph-level interaction requiring distant regions;
- established long-range synthetic tasks from verified upstream code.

### Measures

- source-to-target Jacobian norm;
- total perturbation sensitivity;
- sensitivity versus distance;
- sensitivity versus bottleneck width;
- effective resistance or prespecified topology measure;
- task accuracy;
- gradient norm;
- compute.

### Required interpretation

A preserved total Jacobian norm is not a target-specific guarantee. Report both.

## Gate G — Official long-range graph benchmarks

Use the official LRGB pipeline where feasible:

- Peptides-func;
- Peptides-struct;
- PascalVOC-SP;
- COCO-SP;
- PCQM-Contact.

A minimal first submission may select a justified subset. Use official evaluators, edge features, split objects, and task-specific model components.

## Gate H — Optional application extension

Only after the core gates pass.

### 3D option

Use a graph-native mesh or point-cloud task where learned spectral components are visually interpretable. Report graph-construction sensitivity.

### Medical option

Prefer a genuinely graph-native signal, such as:

- EEG sensor graph;
- cortical surface;
- structural or functional connectome.

Do not introduce an arbitrary EHR graph merely to claim medical relevance.

## Ablation plan

Required ablations:

- Tight versus Product-sum versus GBDN+;
- exact versus finite \(K\);
- root count;
- depth;
- radial versus frequency-centered roots;
- learned roots versus fixed roots;
- complex lift versus real-only surrogate;
- complete coefficients versus carried state only;
- additive versus adjoint reconstruction diagnostics;
- polynomial correction on/off;
- optional unitary routing on/off;
- matched parameter and SpMV budgets.

## Robustness

Evaluate:

- edge deletion/addition;
- edge-weight noise;
- point-coordinate noise for \(k\)-NN graphs;
- root initialization;
- pole-margin regularization;
- spectrum estimation or scaling;
- mixed precision versus strict FP32 where allowed.

## Multiple-comparison policy

Before full analysis, freeze:

- primary datasets;
- primary comparators;
- primary metric per dataset;
- one-sided or two-sided hypotheses;
- multiplicity correction;
- tie threshold.

Exploratory comparisons remain clearly labeled.

## Compute staging

### Stage 1 — smoke

One dataset, one split, one seed, minimal epochs.

### Stage 2 — pilot

Representative datasets, two or three splits, one seed. Estimate runtime, memory, and failure rate.

### Stage 3 — tuning

Validation-only according to the frozen policy.

### Stage 4 — confirmatory

All required splits and seeds with frozen configurations.

### Stage 5 — extended

Optional methods and tasks after the primary matrix is complete.

The notebook estimates total compute before Stage 4. The orchestrator may reduce the extended tier, never the primary split–seed contract.

## Negative-result policy

Negative findings are scientifically useful when they delimit claims. Preserve and report:

- carried-state contraction;
- finite-order degradation near poles;
- failure to improve target-specific sensitivity;
- memory costs of full coefficients;
- datasets where GBDN does not improve;
- root instability or approximation difficulty.

Do not delete a valid negative result because it weakens a broad narrative. Narrow the narrative.
