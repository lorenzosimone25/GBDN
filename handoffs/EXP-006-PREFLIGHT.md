# EXP-006 preflight handoff

**Task:** Official Platonov-five heterophily protocol preflight  
**Owner:** Research Software / Experiment Ops  
**Review role:** Independent protocol auditor  
**Status:** **BLOCKED before implementation/execution**  
**Date:** 2026-08-12

## Outcome

The official protocol is now specified from primary sources, but the existing legacy heterophily path cannot produce confirmatory evidence. It uses one split/seed, universal multiclass cross-entropy, universal macro/multiclass AUROC selection, and evaluates test data during training. Existing results from that path must remain labelled `legacy diagnostic` and must not populate official tables.

Deliverables:

- `reviews/official_heterophily_protocol_audit.md`
- `results_submission/reports/official_heterophily_protocol_manifest.md`

No data was downloaded, no run was launched, no test result was exposed, and no code, paper, result, or execution-board file was changed.

## Frozen decisions

- Use the exact ten supplied mask rows (`0..9`), each a fixed 50%/25%/25% train/validation/test split.
- Use at least three training seeds per split; initial frozen set `[0,1,2]`.
- Roman-empire and Amazon-ratings: multiclass logits, cross-entropy, validation/test accuracy.
- Minesweeper, Tolokers, and Questions: one logit, BCE-with-logits, validation/test binary ROC-AUC.
- Treat split, after averaging training seeds within split, as the primary inference unit.
- Training/selection has no test access. Test evaluation occurs only after a configuration/checkpoint is frozen and in an evaluation-only process.
- Recompute metrics independently from immutable predictions and correct paired primary comparisons with the predeclared Holm family.

## Inputs pinned

- Official dataset/baseline repository: `https://github.com/yandex-research/heterophilous-graphs`, commit `a431395582e929d88271309716bea4fe24ce6318`, MIT.
- Official paper protocol: arXiv `2302.11640v2`.
- Officially linked specialized-model evaluation repository: `https://github.com/Godofnothing/HeterophilySpecificModels`, commit `10d0637688570824f6c54960b86e061b883af0f4`; root license unresolved.

## Blocking dependencies

1. **Dataset identity:** acquire through the approved mechanism and record NPZ/array/split/graph SHA-256 values; verify official statistics and mask invariants. Preflight intentionally did not download data.
2. **License/terms:** review dataset-specific redistribution terms. The root MIT license alone does not explicitly enumerate rights for every underlying source.
3. **Protocol adapter:** implement task registry, exact bidirection expansion, task-specific head/loss/metric dispatch, and ten-mask identity checks.
4. **Leakage barrier:** ensure the training process cannot access test indices/labels/metrics; add a post-freeze evaluation-only process.
5. **Independent verifier:** recompute accuracy or binary ROC-AUC from stored predictions with independent code and fail on disagreement.
6. **Run/statistics system:** immutable 10-split-by-3-seed identities, resume/no-overwrite semantics, split-first aggregation, paired inference, effect sizes, win/tie/loss, and frozen multiplicity correction.
7. **Baseline registry:** upstream URL, full version, license, config, patch, parity, budget, and operator-count evidence for every primary comparator. The officially linked specialized repository has no resolved root license; LINKX and the required spectral comparators are not pinned.
8. **Gate A:** confirm the canonical method remains scientifically eligible before claim-bearing benchmark execution.

## Proposed implementation sequence

1. Add a declarative five-dataset task registry and unit tests for output shape, dtype, loss, and metric dispatch.
2. Add a dataset verifier that hashes the authorized NPZ and arrays, validates stats/masks, expands undirected edges exactly once, and emits a signed dataset manifest.
3. Split training/selection from test evaluation at the CLI/process boundary; test artifacts are produced only from a frozen checkpoint/configuration.
4. Add immutable run IDs from dataset/split/seed/method/config/source/environment hashes and reject identity collisions or overwrite attempts.
5. Add prediction artifacts plus an independent task-specific evaluator and disagreement checks.
6. Add synthetic-record tests for seed-within-split aggregation, paired differences, confidence intervals, paired randomization, effect size, W/T/L, Holm correction, and missing-run failure.
7. Complete `results_submission/baseline_registry.json`; verify upstream parity and equal validation-only tuning budgets.
8. Run CPU smoke tests, then one split-by-one seed without test unblinding. Only after review may the frozen 10-by-3 H100 plan run.

## Acceptance criteria

EXP-006 can move to H100 only when:

- all five dataset and split identities are resolved and verified;
- all graph/mask/task invariants pass;
- task-specific validation selection and independent test recomputation agree;
- training has no reachable test path;
- the complete frozen plan contains 10 splits and at least 3 seeds with immutable resumable IDs;
- missing/corrupt runs make the final verifier fail;
- every primary baseline has an accepted upstream/version/license/parity record;
- the reviewer signs off on the smoke artifact without inspecting confirmatory test outcomes.

Until then, all official heterophily benchmark work and associated paper claims remain blocked; CPU implementation and verification work may proceed.
