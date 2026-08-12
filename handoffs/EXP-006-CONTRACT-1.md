# EXP-006-CONTRACT-1 handoff

## Scope

Implemented a pure CPU metadata contract for the five official Platonov
heterophily datasets. No dataset was downloaded or opened, no test split was
evaluated, and no training, baseline, GPU, manuscript, or result path changed.

## Deliverables

- `src/gbdn/heterophily_contract.py`
- `tests/test_heterophily_contract.py`

The registry freezes canonical names and aliases, official source commit and
NPZ paths, expected graph/task dimensions, exact head/loss/selection/test
metric dispatch, splits `0..9`, and seeds `[0,1,2]`.

## Fail-closed boundaries

- Every registry entry retains unresolved NPZ checksums and dataset-specific
  redistribution terms as explicit blockers.
- Candidate metadata must identify every required NPZ array, ten supplied
  mask rows, exact graph counts, no self-loops/duplicates, one connected
  component, and exactly one bidirection expansion.
- Binary datasets reject universal two-logit cross-entropy/macro-AUROC;
  multiclass datasets reject AUROC selection.
- `TrainingSelectionView` accepts train and validation identities only and
  rejects any extra test index, label, or metric field.
- Confirmatory plan enumeration requires the full five-dataset by method by
  ten-split by three-seed product.

## Scientific status

This is protocol infrastructure only. It enables no benchmark claim and does
not authorize dataset acquisition, test evaluation, H100 execution, or paper
generation. The unresolved checksum/license fields, independent contract
review, data adapter, leakage-separated evaluation process, baseline registry,
and Gate-A acceptance remain blockers.
