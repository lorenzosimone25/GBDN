# Official heterophily protocol manifest

**Manifest ID:** `platonov5-v1`  
**Status:** `BLOCKED_PRE_EXECUTION`  
**Protocol source:** [Platonov et al., arXiv:2302.11640v2](https://arxiv.org/html/2302.11640)  
**Dataset/code source:** [yandex-research/heterophilous-graphs](https://github.com/yandex-research/heterophilous-graphs/tree/a431395582e929d88271309716bea4fe24ce6318)  
**Pinned source commit:** `a431395582e929d88271309716bea4fe24ce6318`  
**Repository license:** MIT; dataset-specific redistribution terms require separate review.

This is the frozen human-readable contract for the confirmatory runner. Placeholder hashes are fail-closed values, not optional metadata.

## Dataset registry

| Canonical name | NPZ path at pinned source | Nodes | Stored undirected edges | Features | Classes | Head | Loss | Selection/test metric | NPZ SHA-256 |
|---|---|---:|---:|---:|---:|---|---|---|---|
| `Roman-empire` | `data/roman_empire.npz` | 22,662 | 32,927 | 300 | 18 | 18 logits | cross-entropy | accuracy | `UNRESOLVED_BLOCKER` |
| `Amazon-ratings` | `data/amazon_ratings.npz` | 24,492 | 93,050 | 300 | 5 | 5 logits | cross-entropy | accuracy | `UNRESOLVED_BLOCKER` |
| `Minesweeper` | `data/minesweeper.npz` | 10,000 | 39,402 | 7 | 2 | one logit | BCE with logits | binary ROC-AUC | `UNRESOLVED_BLOCKER` |
| `Tolokers` | `data/tolokers.npz` | 11,758 | 519,000 | 10 | 2 | one logit | BCE with logits | binary ROC-AUC | `UNRESOLVED_BLOCKER` |
| `Questions` | `data/questions.npz` | 48,921 | 153,540 | 301 | 2 | one logit | BCE with logits | binary ROC-AUC | `UNRESOLVED_BLOCKER` |

Required NPZ keys are `node_features`, `node_labels`, `edges`, `train_masks`, `val_masks`, and `test_masks`. The mask arrays must expose exactly ten split rows. The runner must preserve rows `0..9` as immutable split identities.

## Graph and split invariants

For every dataset, verification must establish:

- one connected undirected simple graph with no self-loops;
- each raw NPZ edge represents one undirected edge;
- bidirection expansion occurs exactly once and produces both `(u,v)` and `(v,u)` without changing weights;
- observed node count, stored-edge count, feature width, and class count equal the registry;
- `train_masks.shape[0] == val_masks.shape[0] == test_masks.shape[0] == 10`;
- within every split, train/validation/test masks are pairwise disjoint and their union covers all nodes;
- split fractions are the supplied 50%/25%/25% assignment, subject only to integer rounding in the distributed masks;
- no mask is generated, shuffled, stratified, or remapped by the local runner.

For each NPZ array and each split-index vector, save SHA-256, dtype, shape, endianness, and the canonical serialization used for hashing. Save a stable-sorted raw-edge hash and stable-sorted expanded-edge hash. A processed-cache file is never the sole dataset identity.

## Frozen execution design

```text
OFFICIAL_SPLITS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
TRAINING_SEEDS = [0, 1, 2]
TEST_VISIBLE_DURING_TRAINING = false
SELECTION_SOURCE = validation_only
PRIMARY_INFERENCE_UNIT = official_split
```

The training process receives train and validation indices only. It emits the selected configuration/checkpoint and validation evidence. After the configuration and checkpoint are immutable, an evaluation-only process receives the test indices and writes raw test logits/scores and provenance. A separate verifier recomputes:

- multiclass accuracy from `argmax(logits)` for Roman-empire and Amazon-ratings;
- binary ROC-AUC from the scalar positive-class score for Minesweeper, Tolokers, and Questions.

The verifier must use an implementation independent of the training metric code and must fail on metric disagreement above a frozen numerical tolerance. Predictions, labels/reference, node order, test-index hash, checkpoint hash, and evaluator version are mandatory.

## Selection and tuning isolation

- Candidate configurations and equal per-method validation budgets are frozen before confirmatory execution.
- Early stopping, checkpoint selection, hyperparameter selection, architecture choice, and ablation choice use validation only.
- Test labels/metrics are unavailable to the training subprocess and notebook display during selection.
- Any change to seeds, splits, data transform, metric, tuning space, stopping rule, or source creates a new plan and run identity.
- A completed run is immutable and may not be overwritten by a different configuration.

## Aggregation and inference

For method `m`, dataset `d`, split `s`, and seed `r`, let `y[m,d,s,r]` be the independently verified test primary metric. First compute:

```text
y_bar[m,d,s] = mean over r in [0,1,2] of y[m,d,s,r]
```

Use the ten values `y_bar[m,d,0..9]` for the primary mean, standard deviation, and frozen 95% confidence interval. For comparator `b`, compute paired differences on the same splits:

```text
delta[d,s] = y_bar[m,d,s] - y_bar[b,d,s]
```

Report mean paired difference in metric points, paired confidence interval, paired standardized effect when defined, and win/tie/loss with a predeclared practical tie threshold. Use the predeclared paired randomization/sign-flip test and Holm correction over the frozen family of primary comparisons. Do not treat 30 seed-level runs as 30 independent observations and do not silently drop failures.

## Per-dataset provenance placeholders

The acquisition/verification step must replace every blocker below without editing this generated-by-process manifest by hand:

| Dataset | NPZ bytes | Features hash | Labels hash | Raw edges hash | Expanded graph hash | Train masks hash | Val masks hash | Test masks hash | License/terms record |
|---|---|---|---|---|---|---|---|---|---|
| Roman-empire | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` |
| Amazon-ratings | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` |
| Minesweeper | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` |
| Tolokers | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` |
| Questions | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` | `BLOCKED` |

## Baseline release gate

The official Platonov standard-baseline source is pinned to `a431395582e929d88271309716bea4fe24ce6318` under MIT. The officially linked specialized-model evaluation source is pinned to `10d0637688570824f6c54960b86e061b883af0f4`, but its root license is unresolved. LINKX, CayleyNet, ChebNetII, BernNet, UniFilter, and WaveGC have no frozen first-party URL/version/license record in the local submission infrastructure.

Before any baseline becomes a primary comparator, `results_submission/baseline_registry.json` must satisfy `gbdn-baseline-registry-v2`. The record must explicitly declare either licensed pinned upstream code or a clean-room primary-equation implementation, and must bind the source/paper/equation locator, SPDX notice, implementation provenance, wrapper, reference configuration, independent operator oracle, official-task contract, parameter/operator counts, and typed parity evidence by commit and SHA-256. Missing or inconsistent evidence is a hard blocker.

## Fail-loud conditions

The operator must stop before H100 execution or paper generation if any of these is true:

- a dataset/array/split checksum is unresolved or changed;
- a graph or mask invariant fails;
- a binary dataset uses a two-logit CE/macro-AUROC path;
- a multiclass dataset selects on AUROC rather than accuracy;
- test data is reachable during training, tuning, or checkpoint selection;
- a required split/seed job or its predictions are missing;
- the independent metric disagrees with the recorded metric;
- 30 seed runs are used as independent inferential units;
- a primary baseline lacks upstream/version/license/parity evidence;
- a completed run identity would be overwritten;
- the frozen plan hash, source hash, environment hash, or dataset identity is absent.
