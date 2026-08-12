# EXP-011-STATISTICS-CONTRACT-1 handoff

## Scope

Implemented task-specific metric recomputation and split-first confirmatory
statistics on synthetic/in-memory records only. No dataset, checkpoint, test
mask, experiment result, H100 process, manuscript, or generated table was
opened or changed.

## Frozen behavior

- Multiclass datasets use accuracy from the argmax of the required logit
  matrix.
- Binary datasets use one-dimensional continuous positive-class scores and an
  independent tie-aware ROC-AUC implementation.
- Every required run must be independently verified, frozen, validation-only
  selected, and present for all ten splits by seeds `[0,1,2]`.
- Seeds are averaged within split before the mean, standard deviation, and
  two-sided Student-t interval over ten official split means.
- Paired comparisons use the same ten splits, exact two-sided sign flips,
  predeclared practical ties, standardized paired effect when defined, and
  win/tie/loss.
- Holm correction operates on one predeclared primary comparison family.

## Scientific status

This is a statistical contract, not evidence. Real predictions, dataset
identity, test isolation, baseline admission, frozen comparison family/tie
threshold, immutable aggregate artifacts, and independent review remain
required before any paper number is produced.
