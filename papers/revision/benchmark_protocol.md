# Benchmark admission protocol

Benchmarking begins only after Gates A and B and the controlled mechanism study.
It does not determine the mathematical claims. Existing JSON files remain
preliminary development artifacts.

## Node classification

Use the ten official splits supplied with the Platonov heterophily datasets.
Roman-empire and Amazon-ratings use accuracy; Minesweeper, Tolokers, and
Questions use ROC-AUC. Run at least three independent optimization seeds for
every fixed split. Report all 30 split–seed observations, the mean, sample
standard deviation, and a 95% confidence interval, while making the dependence
structure explicit.

Each method receives the same number of HPO trials over a prespecified search
space. Select configurations using validation data only. Parameter counts and
measured sparse-operator time must accompany predictive metrics. Local models
whose implementation differs from a cited method are named as ablations.

## Graph-level LRGB

LRGB results are inadmissible until a graph-level pipeline supports batching,
pooling, the official evaluator, official dataset splits, task-specific losses,
and checkpoint selection. Peptides-func, Peptides-struct, PascalVOC-SP, and
COCO-SP must use their official metrics and must not reuse the node runner.

## Equal-budget comparison

The comparison set is Tight GBDN, Product-sum GBDN, GBDN+, CayleyNet,
ChebNetII, Stable-ChebNet, and WaveGC. A missing verified implementation is
reported as missing—not replaced by an approximation. Architecture-specific
hyperparameters may differ, but the number of trials, data access, early
stopping rule, and compute accounting must be identical.

## Artifact contract

Every run writes an immutable directory containing resolved configuration,
seed, split, metric version, source and dependency hashes, stdout/stderr,
trajectories, checkpoint, final predictions, timing, peak memory, and hardware
metadata. A summary is generated from per-run artifacts rather than edited by
hand. No benchmark number enters the manuscript until the claim-to-evidence
matrix links it to those artifacts.

