# EXP-006-EVALUATOR-1 handoff

## Scope

Implemented an independent post-freeze evaluator for official heterophily
prediction archives. All tests use synthetic arrays. No official dataset,
checkpoint, test mask, real prediction, H100 process, result, aggregate, or
paper artifact was opened or created.

## Evaluation boundary

- Input is only a bounded hashable prediction archive plus the expected run,
  dataset, split, authoritative ordered test indices, and authoritative labels.
- Archives must contain exactly format, run ID, dataset, split, ordered indices,
  and finite float32/float64 logits. Object deserialization is disabled.
- Roman-empire/Amazon-ratings require the exact multiclass head and accuracy;
  Minesweeper/Tolokers/Questions require one-dimensional scores and tie-aware
  binary ROC-AUC.
- Run/dataset/split/index order, dtype, head shape, finite values, archive
  membership, and size are fail-closed. The returned record includes the
  independent metric and archive SHA-256.
- Training, validation selection, checkpoint state, and per-epoch test metrics
  are outside this interface.

## Verification

- Protocol/evaluator/statistics/verifier focused suite: 39 passed.
- Full repository suite: 640 passed, 1 Windows privilege skip, 3 known
  environment warnings.

## Remaining block

The scheduler must still bind authoritative verified split metadata to this
evaluator in a process isolated from training, record the resulting verified
metric in immutable artifacts, handle failures/resume, and pass independent
operations review. No execution authorization is granted.
