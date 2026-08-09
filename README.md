# GBDN: Graph Blaschke Decomposition Networks

GBDN is a spectral graph neural network built around learnable Blaschke
responses. This repository contains the compact implementation and experiment
pipeline needed to reproduce the original GBDN+ and baseline results on a
single NVIDIA H100.

## 🧭 Overview

Polynomial graph filters are efficient, but their spectral response is tied to
a fixed polynomial parameterization. GBDN instead starts from Blaschke factors,
whose complex-valued geometry provides a flexible way to shape graph-frequency
responses. The resulting filters are evaluated with a Chebyshev approximation,
so training remains compatible with sparse graph operations.

The reproduction target is intentionally narrow: the saved JSON artifacts from
the original single-seed benchmark protocol. The repository does not mix these
results with the later multi-seed development runner.

## 🧠 Method

GBDN+ follows five steps:

1. Lift real node features into a complex hidden representation.
2. Build a Chebyshev basis of the normalized graph Laplacian.
3. Learn bounded complex Blaschke parameters for each decomposition layer.
4. Convert the Blaschke response into Chebyshev coefficients and apply it with
   sparse matrix operations.
5. Combine the filtered representation with a learnable skip connection, then
   concatenate its real and imaginary parts for prediction.

The benchmark implementation keeps the original architecture, optimizer,
initialization, dataset order, seed, split, and validation-selection rule.

## 🧪 Reproduced benchmarks

| Benchmark | Datasets | Models | Protocol |
|---|---:|---:|---|
| Heterophilous graphs | 5 | 12 | Seed 25, split 0, 1,000 epochs |
| Peptides-func | 1 | 2 | Seed 25, official splits, 100 epochs |

The heterophily suite contains Roman-empire, Amazon-ratings, Minesweeper,
Tolokers, and Questions. It evaluates GBDN+, ChebNet, ChebNetII, H2GCN, FAGCN,
MLP, MixHop, GAT, GraphSAGE, ADGN, ResNet, and ResNet+SGC. Peptides-func
evaluates GBDN+ and ChebNet_K10.

Reference artifacts live in `results/` and `results_LRGB/`. Fresh runs are
written separately and compared against those references.

## ⚡ Run on one H100

Requirements: Linux, Python 3.11, one accessible NVIDIA H100, `nvidia-smi`,
internet access for PyG dataset downloads, and persistent disk storage.

```bash
git clone https://github.com/lorenzosimone25/GBDN.git
cd GBDN

bash scripts/setup_h100.sh
bash scripts/run_h100.sh smoke
bash scripts/run_h100.sh run-all --workers auto
bash scripts/run_h100.sh report
bash scripts/run_h100.sh verify
```

`run-all` assigns one process to each model pipeline and runs several pipelines
concurrently. Every model still visits the five heterophily datasets in the
original order, preserving its RNG stream. The Peptides-func pair runs
sequentially because its initialization order is part of the original protocol.

Training remains in deterministic FP32. TF32, mixed precision, and compilation
are disabled so H100 acceleration does not silently alter the experiment.

## 📦 Outputs and reproducibility

```text
results/                 Reference heterophily JSON
results_LRGB/            Reference Peptides-func JSON
results_repro/           Fresh heterophily JSON and run manifest
results_LRGB_repro/      Fresh Peptides-func JSON
reproduction_report.md   Reference-versus-rerun comparison
```

Outputs are atomic and immutable by default. Matching completed jobs are
resumed through local RNG checkpoints; replacing a different run identity
requires `--rerun`. Each artifact records its configuration, source hash,
software environment, GPU, runtime, and peak CUDA memory.

The final verification command requires all 62 artifacts, recomputes saved
heterophily metrics from predictions, checks provenance, and rejects absolute
metric drift greater than `0.02`.

See [REPRODUCTION.md](REPRODUCTION.md) for command options, paths, and recovery
behavior.

## 🔬 Repository layout

```text
src/legacy_reproduction.py     Models, training loops, metrics, validation
scripts/reproduce_legacy.py    Experiment CLI and parallel supervisor
scripts/setup_h100.sh          Pinned Python/CUDA environment setup
scripts/run_h100.sh            GPU isolation, logging, and command launcher
tests/                         Reproduction and failure-path tests
```

Datasets, virtual environments, logs, checkpoints, manuscripts, figures,
notebooks, and research scratch files are deliberately excluded from Git.
