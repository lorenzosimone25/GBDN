# Official heterophily protocol audit

**Audit ID:** EXP-006-PREFLIGHT  
**Date:** 2026-08-12  
**Scope:** Roman-empire, Amazon-ratings, Minesweeper, Tolokers, and Questions  
**Decision:** **BLOCK confirmatory execution.** The official dataset/task contract is recoverable, but the legacy runner is not a valid implementation of it and the required dataset checksums and primary-baseline registry are not yet frozen.

This was a source-and-code audit only. No dataset was downloaded, no experiment was run, and no result was inspected or changed.

## Sources and authority

Only first-party project sources were used for protocol facts:

1. Platonov et al., [official paper, arXiv:2302.11640v2](https://arxiv.org/html/2302.11640), especially Section 4 and Appendix A.
2. Yandex Research, [official dataset and baseline repository](https://github.com/yandex-research/heterophilous-graphs/tree/a431395582e929d88271309716bea4fe24ce6318), commit `a431395582e929d88271309716bea4fe24ce6318`.
3. Its [dataset loader](https://github.com/yandex-research/heterophilous-graphs/blob/a431395582e929d88271309716bea4fe24ce6318/datasets.py), which is authoritative for target shape, loss, metric, masks, and edge expansion.
4. Its [MIT license](https://github.com/yandex-research/heterophilous-graphs/blob/a431395582e929d88271309716bea4fe24ce6318/LICENCE.txt). Dataset-specific redistribution rights are not separately stated and remain unresolved.
5. The companion [heterophily-specific evaluation repository](https://github.com/Godofnothing/HeterophilySpecificModels/tree/10d0637688570824f6c54960b86e061b883af0f4), commit `10d0637688570824f6c54960b86e061b883af0f4`, linked by the official repository. It has no visible root license and is therefore not cleared for vendoring.

The local research contract agrees with the official metric split at `sub_plans/06_EXPERIMENTS_AND_STATISTICS.md:154-173` and requires baseline provenance at `sub_plans/08_RESULTS_AND_ARTIFACT_SCHEMA.md:227-261`.

## Frozen official protocol

All five datasets are node-classification problems on connected, undirected, simple graphs without self-loops. In the official NPZ files, an undirected edge is stored once. A loader for a directed graph library must expand every stored edge to both directions exactly once (`dgl.to_bidirected` or `ToUndirected`). It must not add self-loops or regenerate/repartition the graph for this benchmark.

The official paper fixes **ten random 50%/25%/25% train/validation/test splits**. “Official split `s`” means the exact row `s` of `train_masks`, `val_masks`, and `test_masks` in the pinned NPZ, for `s = 0, ..., 9`; it does not mean a newly generated split with the same proportions.

| Dataset | Nodes / stored edges / features | Target | Output and training loss | Validation selection metric | Final test metric |
|---|---:|---|---|---|---|
| Roman-empire | 22,662 / 32,927 / 300 | 18-way syntactic-role class | 18 logits; cross-entropy | accuracy | accuracy |
| Amazon-ratings | 24,492 / 93,050 / 300 | five binned rating classes | 5 logits; cross-entropy | accuracy | accuracy |
| Minesweeper | 10,000 / 39,402 / 7 | mine vs. non-mine | one logit; BCE with logits | binary ROC-AUC | binary ROC-AUC |
| Tolokers | 11,758 / 519,000 / 10 | banned vs. not banned | one logit; BCE with logits | binary ROC-AUC | binary ROC-AUC |
| Questions | 48,921 / 153,540 / 301 | active vs. inactive | one logit; BCE with logits | binary ROC-AUC | binary ROC-AUC |

For binary ROC-AUC, the evaluator must consume the continuous scalar score for the positive class (a raw logit or any strictly monotone transform), not thresholded labels. A two-column macro/multiclass ROC-AUC is a different estimand. Questions is about 97% active, making accuracy particularly misleading; ROC-AUC is the official primary metric.

### Dataset construction facts that adapters must preserve

- **Roman-empire:** one node per word occurrence in the 2022-03-01 English Wikipedia Roman Empire article; edges join sequential words or dependency-tree neighbors; 17 frequent dependency roles plus an “other” class; fastText word features.
- **Amazon-ratings:** product co-purchasing graph from SNAP Amazon metadata; target is average rating binned into five classes; mean fastText description features; largest connected component of the graph's 5-core.
- **Minesweeper:** fixed 100-by-100 eight-neighbor grid; 20% mine labels; one-hot neighboring-mine-count features, with a missing-feature indicator for the 50% whose count is hidden.
- **Tolokers:** workers are adjacent if they worked on the same task among 13 selected Toloka projects; target is whether a worker was banned; profile/performance features.
- **Questions:** Yandex Q medicine-topic user interaction graph over September 2021--August 2022; an edge denotes one user answering another; target is end-of-period activity; mean fastText description features plus a missing-description indicator.

These are identity checks, not instructions to recreate the datasets. Confirmatory work must consume the distributed NPZ and record its checksum.

## Why the legacy universal CE/macro-AUROC path is invalid

The relevant implementation is `src/legacy_reproduction.py`. Its outputs may remain as provenance-labelled diagnostics, but none may enter the official confirmatory table.

| Defect | Local evidence | Scientific classification and consequence |
|---|---|---|
| One training seed and only split 0 | `HETERO_CONFIG` fixes `seed=25` and `split_id=0` at line 66; split selection occurs at line 646 | **Unsupported / diagnostic only.** It cannot estimate variation across official splits or support paired inference. |
| Universal multiclass head/loss | `F.cross_entropy` is used for every heterophily dataset at line 660 | **False protocol for three datasets.** Minesweeper, Tolokers, and Questions require one logit and BCE-with-logits. |
| Universal macro/multiclass ROC-AUC for checkpoint selection | `compute_multiclass_auroc` is called for validation at lines 667-669 | **False protocol.** Roman-empire and Amazon-ratings must select on accuracy; the three binary datasets require binary ROC-AUC, not macro one-vs-rest AUROC over two softmax columns. Rankings and selected epochs can change. |
| Test is evaluated during training | test probabilities and metrics are computed whenever validation improves at lines 672-683 | **Leakage/exposure hazard.** A confirmatory runner must select with train/validation only, freeze the selected checkpoint/configuration, and reveal test exactly once in an isolated evaluation step. |
| Universal verifier repeats the wrong estimand | `validate_heterophily_record` recomputes multiclass AUROC for every record at lines 1107-1114 | **Invalid independent verification.** The verifier must dispatch by dataset contract and compare against an independently implemented accuracy or binary ROC-AUC routine. |
| No split-level inferential design | a single record is produced from the fixed split/seed | **Unsupported superiority claims.** Thirty runs may not be treated as independent replicates, and a 1-by-1 run cannot yield confirmatory uncertainty. |

The defect is not merely the use of cross-entropy: cross-entropy is correct for Roman-empire and Amazon-ratings. The invalidity is the *universal* application of a multiclass formulation and macro-AUROC selection to tasks whose official heads, losses, and metrics differ.

## Leakage-free confirmatory design

For every method `m` and dataset `d`:

1. Freeze the candidate configurations, equal validation-only tuning budget, official split IDs, training seeds, early-stopping rule, practical tie tolerance, and multiplicity family in a hashed experiment plan before any confirmatory test score is produced.
2. Use official splits `0..9` and at least three training seeds per split. The initial frozen seed set may be `[0, 1, 2]`; changing it requires a new plan identity.
3. Training and checkpoint selection may access only the training and validation masks. Selection uses dataset-specific validation accuracy or validation binary ROC-AUC from the table above.
4. After configuration and checkpoint selection are frozen, an evaluation-only process loads the immutable checkpoint and produces predictions for the official test mask. The training process must not log or return test metrics.
5. Save logits/scores, labels or a cryptographic reference to the immutable labels, node IDs, split mask identity, checkpoint hash, and evaluator version. Recompute the primary metric from these artifacts in a separate verifier implementation.
6. Average the training-seed scores within each split: `y_bar[m,d,s] = mean_r y[m,d,s,r]`. The ten split means, not the 30 runs, are the primary statistical observations.
7. Report the mean, standard deviation, and a predeclared 95% confidence interval across the ten split means. Training-seed dispersion is a secondary diagnostic and must not replace split uncertainty.
8. Compare methods on shared splits using paired differences `delta_s`. Report mean paired difference in metric points, a paired confidence interval, a paired standardized effect (`mean(delta)/sd(delta)` when defined), and win/tie/loss under the predeclared practical tie threshold.
9. Use an exact paired sign-flip/randomization test when its assumptions match the frozen analysis. Correct the predeclared family of primary method comparisons with Holm's procedure. Do not retroactively change the family after viewing test outcomes.
10. Do not silently drop failed runs or splits. A missing required run makes the confirmatory artifact incomplete; any predeclared complete-case sensitivity analysis must be labelled secondary.

## Required dataset, split, and run provenance

The following are mandatory before EXP-006 can run:

- source repository URL and full commit SHA;
- official NPZ relative path, byte size, and SHA-256;
- dataset name exactly as resolved by the loader;
- loader package name, exact version/full commit, source-file hash, and transform chain;
- hashes of `node_features`, `node_labels`, raw `edges`, `train_masks`, `val_masks`, and `test_masks`, including dtype, shape, endianness, and canonical serialization rule;
- for each split, split ID, train/validation/test index hashes, counts, per-class counts, disjointness check, and full-node coverage check;
- graph statistics before and after bidirection expansion: node count, stored edge count, directed edge count, feature dimension, number of classes, self-loop count, duplicate-edge count, and connected-component count;
- a canonical graph hash after stable sorting of expanded edges; no hidden self-loop, feature, edge-weight, or normalization transform;
- source commit/tree hash, dirty-worktree status, dependency lock hash, CUDA/PyTorch/PyG versions, device identity, and dataset cache hash;
- immutable run ID derived from dataset/split/seed/method/config/source/environment identities;
- frozen-plan hash, hyperparameter-budget ledger, checkpoint hash, prediction hash, metric implementation/version, independently recomputed metric, runtime, memory, and parameter/operator budgets.

Because this preflight did not download the NPZ files, all dataset and array SHA-256 values are deliberately **UNRESOLVED**. Execution must stop if they are absent, if mask shape/count is not ten, or if the identity checks above disagree with the official statistics.

The repository's MIT file establishes a code-repository license, but it does not separately enumerate terms for each underlying Wikipedia, SNAP, Toloka, or Yandex Q data source. Do not redistribute raw NPZ files in an artifact branch until dataset redistribution rights and required notices are reviewed; prefer a checksum-verified acquisition procedure.

## Minimum baseline provenance audit

| Baseline family | Candidate first-party source | Version | License | Readiness |
|---|---|---|---|---|
| ResNet, ResNet+SGC, ResNet+adj, GCN, SAGE, GAT/GAT-sep, GT/GT-sep | [Official Platonov benchmark](https://github.com/yandex-research/heterophilous-graphs/tree/a431395582e929d88271309716bea4fe24ce6318) | `a431395582e929d88271309716bea4fe24ce6318` | MIT | **Source identified.** Still requires local adapter parity, environment pinning, and an official-result smoke check. |
| H2GCN, CPGNN, GPR-GNN, FSGNN, GloGNN, FAGCN, GBK-GNN, JacobiConv | [Officially linked companion evaluation repository](https://github.com/Godofnothing/HeterophilySpecificModels/tree/10d0637688570824f6c54960b86e061b883af0f4) | `10d0637688570824f6c54960b86e061b883af0f4` | **UNRESOLVED:** no root license visible | **BLOCKED.** Trace each subdirectory to the authors' upstream release, record its license and commit, and verify benchmark adaptations. Do not vendor this aggregate repository as-is. |
| LINKX | No primary upstream/version/license is frozen locally | **UNRESOLVED** | **UNRESOLVED** | **BLOCKED.** |
| CayleyNet | No primary upstream/version/license is frozen locally | **UNRESOLVED** | **UNRESOLVED** | **BLOCKED.** |
| ChebNetII | No primary upstream/version/license is frozen locally | **UNRESOLVED** | **UNRESOLVED** | **BLOCKED.** |
| BernNet (or GPR-GNN as the adaptive polynomial comparator) | GPR-GNN has only the unresolved companion candidate above; BernNet is not frozen | **UNRESOLVED** | **UNRESOLVED** | **BLOCKED.** |
| UniFilter | No primary upstream/version/license is frozen locally | **UNRESOLVED** | **UNRESOLVED** | **BLOCKED.** |
| WaveGC | No primary upstream/version/license is frozen locally | **UNRESOLVED** | **UNRESOLVED** | **BLOCKED.** |

A baseline becomes primary only after `results_submission/baseline_registry.json` records: canonical method name, first-party URL, full SHA/tag, SPDX license and notice path, upstream configuration, any local patch hash, official dataset protocol mapping, parameter and sparse-operator counts, tuning space/budget, and a parity result within a predeclared tolerance. A paper equation or an unverified local reimplementation is insufficient.

## Gate decision and allowed next work

**Allowed now (CPU/no test unblinding):** implement and unit-test the dataset contract registry; validate already-authorized local NPZ metadata/checksums; implement task-specific heads/losses/metrics; construct a train/validation-only runner and isolated test evaluator; add mask/graph identity checks; implement split-first aggregation on synthetic records; and complete the baseline registry/license audit.

**Blocked:** any H100 confirmatory run, benchmark-superiority claim, official paper table, or comparison against an unverified baseline. Unblock only when all five dataset identities/checksums pass, the official task dispatch is tested, the test path is inaccessible to training/selection, independent metric recomputation agrees, all 150 method-dataset runs for a frozen configuration are resumable and immutable, and every primary comparator has upstream/version/license/parity evidence.
