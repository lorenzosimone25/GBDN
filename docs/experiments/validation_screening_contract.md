# Validation-only screening contract

**Status:** proposed CPU-side contract; no screening plan, configuration, or result is frozen by this document.

## Scientific boundary

Hyperparameter screening chooses one configuration per method--dataset pair by
validation evidence only. It is not a confirmatory experiment and must not
produce, receive, or rank by a test score. A selected configuration is still
ineligible for confirmatory execution until the existing baseline/method
admission contract binds the final five-dataset configuration and independently
reviewed selection evidence.

`gbdn.screening_contract` defines four identities:

1. a compact, hash-bound search space;
2. every full typed Cartesian candidate and its SHA-256 identity;
3. a manifest that freezes method, dataset, candidate subset, trial ID,
   screening seed, validation units, and one equal integer trial budget;
4. a validation decision that binds the complete set of candidate-observation
   hashes, the winning observation, the manifest hash, and the deterministic
   tie rule.

The schedule is rebuilt from the source search-space bytes during validation.
It fails if a file hash, candidate count, seed, budget, validation unit, trial
assignment, rank, or candidate payload changes.

## Deterministic candidate subset

Parameter names are sorted lexicographically. Each candidate contains exactly
three sections (`model`, `optimizer`, `training`) and is hashed from canonical
JSON that preserves JSON types. Values such as `false`, `0`, and `0.0` are
distinct. Duplicate typed values are rejected.

For each method, official dataset, and candidate, the sampler hashes:

```text
candidate SHA-256
dataset
method
policy version
screening seed
search-space SHA-256
```

Candidates are sorted by the resulting digest (then by candidate digest), and
the first `B` are assigned trial IDs `0..B-1`. This samples without replacement
and does not depend on Python, NumPy, or PyTorch PRNG behavior. `B` must be the
same positive exact integer for every method--dataset pair and cannot exceed
any participating candidate space.

## Validation selection

The manifest freezes ordered units such as `split=0/seed=0`. Every candidate
and method on a dataset must report the same units and the official validation
metric: accuracy for Roman-empire and Amazon-ratings; binary ROC-AUC for
Minesweeper, Tolokers, and Questions. The decision maximizes the arithmetic
mean across those units. Exact metric ties choose the lexicographically smaller
candidate SHA-256, not the earlier finishing run.

An observation has an exact schema with no test field and must attest:

```json
{"selection_partition":"validation","test_used_for_selection":false}
```

This schema check complements, but does not replace, the worker's process-level
test isolation. Missing trials, extra trials, duplicate identities, changed
units, wrong metrics, booleans/non-finite scores, or scores outside `[0,1]`
fail closed.

## Proposed H100 policy (not yet frozen)

For runtime planning, the proposed initial policy is:

```text
candidate screening seed: 20260812
candidate trial budget B: 12 per method--dataset
validation units: split=0/seed=0, split=1/seed=0, split=2/seed=0
```

This means `12 x 5 x 3 = 180` training jobs per method before retries. The
proposal deliberately remains unfrozen until the one-split/one-seed smoke run
has measured wall time and memory for every participating method. Freezing a
larger budget without those measurements could consume the H100 allocation
without improving scientific coverage; freezing a smaller one could make the
search uncompetitive. The final choice must be recorded in a canonical
manifest before any screening result is generated and must be equal across
methods. Any later change creates a new manifest hash and invalidates prior
selection evidence for confirmatory admission.

## Integration requirements

- Add frozen search spaces for TightGBDN, ProductSumGBDN, and GBDNPlus whose
  candidates are complete worker-valid configurations; ChebNet is currently
  the only registered space.
- Measure Stage-3 runtime, then adjudicate and freeze the proposal above.
- Add an execution layer that launches only the selection subprocess and never
  prepares the test snapshot during screening.
- Bind each observation to immutable validation run IDs/checkpoints in the
  execution artifact schema. The current module validates decision semantics;
  it does not create experiment artifacts.
- Independently review candidate-space fairness before producing a screening
  manifest.
- After all required observations exist, generate final five-dataset method
  configurations and registry selection evidence. Until then, methods remain
  screening-only and no superiority claim is allowed.
