# Software Engineer Agent Work Plan

## Role

You own the canonical GBDN implementation, exact and sparse tests, benchmark framework, multi-seed execution, result artifacts, and the H100 operator notebook.

The notebook must call reusable source code or CLI commands. It must not become the only place where the method or metrics exist.

## 1. Preserve the legacy record

Do not change the behavior of:

- legacy source used for archived artifacts;
- legacy reproduction notebook;
- frozen `results/` and `results_LRGB/`.

Preferred action:

```text
legacy/
    legacy_reproduction.py
    reproduce_legacy.ipynb
```

If moving files would break references, leave them in place and mark them frozen. New submission code must live under a distinct package and output root.

## 2. Target package

Keep the implementation compact:

```text
src/gbdn/
    core.py          # Cayley map, roots, exact symbols, dense oracle
    models.py        # Tight, Product-sum, GBDN+, node/graph readouts
    diagnostics.py   # frame, reconstruction, roots, poles, sensitivity
    experiments.py   # shared training/evaluation primitives

scripts/
    run_submission.py

configs/submission/
    *.yaml

notebooks/
    gbdn_submission_h100.ipynb
```

Split further only when a file becomes genuinely unmanageable.

## 3. Canonical mathematical implementation

### ENG-001 — Root and symbol layer

Implement:

- radial admissible root parameterization;
- optional frequency-centered root parameterization;
- canonical Blaschke factor with complex conjugation in the denominator;
- finite Blaschke products;
- Cayley composition;
- mapped zero and pole diagnostics;
- phase and phase-derivative evaluation.

Unit tests must verify \(|\alpha|<\rho_{\max}\) under extreme raw parameters.

### ENG-002 — Independent dense oracle

For small self-adjoint Laplacians, implement:

\[
g(L)=Ug(\Lambda)U^*.
\]

This oracle must be structurally independent from the sparse recurrence and used to verify:

- transform direction;
- conjugation;
- coefficient interpolation;
- channel outputs;
- synthesis;
- effective multilevel atoms.

### ENG-003 — Sparse Chebyshev/Clenshaw realization

Implement a finite-degree realization on \([0,2]\), mapped to \([-1,1]\).

Requirements:

- explicit zeroth-coefficient convention;
- complex coefficients;
- sparse graph operations;
- streaming recurrence or Clenshaw evaluation;
- no full basis tensor unless explicitly requested for diagnostics;
- optional precomputed Laplacian passed by the caller;
- no graph cache keyed only by number of nodes;
- exact sparse-operation count;
- operator error diagnostics against the dense oracle.

### ENG-004 — Tight GBDN

Implement:

- sequential complementary analysis;
- complete coefficient tuple;
- additive reconstruction utility;
- adjoint synthesis;
- streaming readout option;
- real/imaginary concatenation;
- per-level roots and responses;
- exact and approximate modes.

Return diagnostics without requiring a second forward pass.

### ENG-005 — Product-sum GBDN

Implement cumulative products and learned complex sum as a separate class. Do not expose tightness flags.

### ENG-006 — GBDN+

Implement the relaxed architecture separately and label every output/artifact as relaxed. Preserve a compatibility wrapper for legacy artifacts only if necessary.

### ENG-007 — Optional unitary routing

Implement only after the Math Agent and orchestrator accept the mathematical value. Keep behind a configuration flag and separate ablation name.

## 4. Contract tests

Create independent tests for:

- root admissibility;
- exact all-pass symbols;
- phase derivative;
- mapped poles;
- exact factor unitarity;
- one-level tightness;
- pointwise partition;
- multilevel isometry;
- weighted Parseval;
- additive reconstruction;
- adjoint synthesis;
- conditioning;
- anti-collapse lower bound;
- exact-versus-sparse agreement;
- finite-order frame bounds;
- graph permutation equivariance;
- repeated eigenvalues;
- weighted and disconnected graphs;
- graph identity/cache safety;
- gradients through root radius and frequency center;
- no lazy parameters after optimizer construction.

Tests should include paths, cycles, complete graphs, complete bipartite graphs, grids, stochastic block models, and small point-cloud graphs.

## 5. Experiment CLI

Implement:

```bash
python scripts/run_submission.py preflight
python scripts/run_submission.py contract
python scripts/run_submission.py mechanism
python scripts/run_submission.py filter-efficiency
python scripts/run_submission.py heterophily-tune
python scripts/run_submission.py heterophily-confirm
python scripts/run_submission.py depth
python scripts/run_submission.py oversquashing
python scripts/run_submission.py lrgb
python scripts/run_submission.py aggregate
python scripts/run_submission.py render
python scripts/run_submission.py verify
```

Each command accepts:

- config path;
- output root;
- device;
- rerun flag;
- dry-run flag;
- optional job selector;
- optional failure-continuation flag.

The notebook calls these commands or the same public Python entry points.

## 6. Official heterophily protocol

Use the five replacement datasets and all supplied fixed split masks.

### Task formulation

| Dataset type | Output/loss | Validation and test metric |
|---|---|---|
| Roman-empire, Amazon-ratings | multiclass logits and cross-entropy | accuracy |
| Minesweeper, Tolokers, Questions | one binary logit and binary cross-entropy | ROC-AUC |

Do not select multiclass checkpoints by AUROC when the official metric is accuracy.

### Confirmatory run

Default target:

```text
10 official splits × 3 training seeds
```

Use predeclared seeds. Save every test prediction.

### Hyperparameter policy

Support two labeled modes:

1. **UPSTREAM_CONFIG** — verified upstream configuration, no local test-driven tuning.
2. **EQUAL_BUDGET** — the same predeclared number of validation-only trials per model–dataset pair.

Never mix the two modes in one unlabeled primary table.

Freeze chosen configurations under:

```text
configs/submission/frozen/
```

before confirmatory test execution.

## 7. Baseline registry

Create a machine-readable registry with:

- method name;
- official repository;
- commit;
- license;
- wrapper;
- supported task;
- published reference configuration;
- verification dataset and metric;
- observed versus expected performance;
- status: `UNVERIFIED`, `PILOT`, `VERIFIED`, `EXCLUDED`.

Primary-table baselines must be `VERIFIED`.

Avoid local reimplementations when upstream code is available. When a wrapper is necessary, verify it against the upstream output.

## 8. Core baseline tiers

### Minimum submission tier

- MLP;
- ResNet;
- one standard message-passing baseline with residual/normalization;
- H2GCN or LINKX;
- ChebNetII;
- CayleyNet;
- one adaptive polynomial method such as GPR-GNN or BernNet;
- A-DGN or Stable-ChebNet;
- WaveGC;
- Tight GBDN;
- Product-sum GBDN;
- GBDN+.

### Extended tier

Add UniFilter, SLOG, HeroFilter, Unitary Convolution, EvenNet, and further verified methods when compute and compatibility allow.

The orchestrator freezes the primary tier before the full run.

## 9. Depth and oversquashing experiments

Implement reusable instrumentation for:

- hidden states by depth;
- complete coefficient stack;
- numerical/effective/stable rank;
- pairwise cosine similarity;
- class separation;
- linear probes;
- gradient norms;
- Jacobian-vector products;
- source-to-target sensitivity by distance;
- bottleneck width;
- effective resistance or other prespecified graph measure;
- total sparse-operation count.

Do not infer source-to-target influence from global norm alone.

## 10. LRGB integration

Use official task loaders and evaluators.

For Peptides-func:

- retain node and edge encoders;
- use official multilabel AP aggregation;
- save predictions;
- use official split objects;
- compare against more than one weak baseline.

Treat the current simple mean-pooling legacy wrapper as diagnostic only.

## 11. Artifact requirements

Follow `08_RESULTS_AND_ARTIFACT_SCHEMA.md`.

Every completed run saves:

- immutable `result.json`;
- predictions;
- configuration;
- source and dataset hashes;
- environment;
- selected epoch;
- validation history;
- runtime;
- peak allocated memory;
- parameter count;
- sparse-operation count;
- roots, poles, and effective response for GBDN variants;
- failure record when unsuccessful.

## 12. H100 notebook

Implement exactly the operator workflow in `05_H100_NOTEBOOK_SPEC.md`.

Key constraints:

- set GPU visibility before importing PyTorch;
- default to sequential jobs;
- support safe resume;
- use subprocess isolation for long jobs;
- show nested progress and ETA;
- never overwrite a different run identity;
- final verification must fail when any required job, prediction, manifest, or metric recomputation is missing.

## 13. Generated paper assets

`aggregate` and `render` must create:

```text
paper/generated/heterophily_table.tex
paper/generated/mechanism_table.tex
paper/generated/depth_table.tex
paper/generated/compute_table.tex
paper/generated/paired_tests.tex
paper/generated/figures/*.pdf
paper/generated/figures/*.png
results_submission/reports/submission_report.md
```

Numbers in generated `.tex` files include run-manifest references in comments.

## 14. Completion criteria

The engineering workstream is complete only when:

- exact and sparse implementations match the manuscript;
- all contract tests pass;
- the official metric contract is enforced by tests;
- a clean H100 smoke run resumes after interruption;
- predictions independently reproduce saved metrics;
- the primary multi-split/multi-seed matrix is complete;
- generated paper assets require no manual number copying;
- the Reviewer Agent finds no implementation blocker.
