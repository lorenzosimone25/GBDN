# ChebNet PyG parity/admission preflight handoff

## Task

- **Task ID:** EXP-007-CHEBNET-PARITY-1
- **Agent:** ChebNet parity specialist
- **Branch:** `agent/engineering/EXP-007-CHEBNET-PARITY-1`
- **Starting commit:** `f6446aabe09a9850be80ea55a503ebe7a1b462dc`
- **Ending commit:** `5820080117cbbc118c00ee82b0c477a2ff8dbf04`
- **Status proposed:** BLOCKED (registry admission); REVIEW (parity patch)

## Objective

Independently audit the licensed PyG ChebNet adapter on CPU-only deterministic
fixtures: upstream identity and license, wrapper output/gradient semantics,
sparse-versus-dense recurrence, task-head dimensions, parameter counts, and
feature-matrix SpMV counts. Do not run datasets, tuning, H100 jobs, or create
paper-result claims. Create admission artifacts only if every registry-v2
attestation can be populated truthfully.

## Summary

The adapter passes a substantially stronger parity preflight, but primary
registry admission is not yet scientifically defensible.

The prior provenance pin was wrong: `cc678a392255a1467872f54582724b8dce434603`
declares PyG 2.9.0. The actual `2.8.0` tag resolves to
`726310a486eae37a89cd6359072b82bbbbb71579`. Its `ChebConv` bytes match the
installed 2.8.0 wheel exactly. The MIT notice is now preserved in the
repository.

PyG 2.8.0 exposes `ChebConv`, not an upstream full `nn.models.ChebNet`. The
wrapper is therefore compared to both (1) a fresh direct composition of two
upstream `ChebConv` modules and (2) a structurally independent dense oracle
that imports no PyG code. Outputs, input gradients, and all parameter gradients
match on deterministic weighted reciprocal graphs. Orders 1, 2, 4, and 6 and
an isolated vertex are covered. Parameter and SpMV formulas are checked for
every official dataset head.

No wrapper configuration, parity JSON, or registry record was created. PyG
does not publish an upstream configuration for this two-layer adapter on the
five Platonov datasets. Calling an invented local configuration an upstream
reference would make the registry-v2 attestation misleading. A later frozen
equal-budget local configuration may close this blocker if its status is
explicit and independently reviewed.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `.gitattributes` | Forces preserved `.txt` notices to LF | Yes |
| `.gitignore` | Allows only third-party text license notices | Yes |
| `licenses/third_party/pytorch_geometric_MIT.txt` | Preserves exact PyG MIT notice | Yes |
| `src/gbdn/baselines/chebnet_oracle.py` | Adds PyG-independent dense operator/network oracle | Yes |
| `tests/test_chebnet_baseline.py` | Adds release, license, forward, gradient, operator, task-head, parameter, and SpMV checks | Yes |
| `docs/baselines/chebnet_pyg_provenance.md` | Corrects source pin and records verified boundary/blocker | Yes |

## Scientific impact

- Claims enabled: the local wrapper implements the documented two-layer PyG
  `ChebConv` composition and its sparse operator agrees with an independent
  dense Chebyshev recurrence on the audited fixtures.
- Claims narrowed: this is a licensed **ChebNet** layer-based comparator, not
  ChebNetII and not an upstream-published full heterophily model.
- Claims rejected: the old `cc678a...` source pin; any claim that PyG 2.8.0
  provides an official `torch_geometric.nn.models.ChebNet`; any current claim
  that the baseline is registry-v2 admitted.
- Paper sections affected: none until a later reviewed registry admission and
  confirmatory experiment exist.

## Evidence

### Proofs

- theorem/lemma: not applicable;
- assumptions: one finite reciprocal nonnegative weighted graph, symmetric
  normalization, explicit `lambda_max=2`, deterministic dropout disabled for
  numerical parity;
- proof location: executable dense recurrence in
  `src/gbdn/baselines/chebnet_oracle.py`;
- counterexamples checked: nonreciprocal graph input is rejected by the dense
  oracle; isolated-vertex semantics are included.

### Tests

```text
command:
  $env:PYTHONPATH=<repo>/src
  C:/Users/Lough/AppData/Local/Python/pythoncore-3.14-64/python.exe \
    -m pytest -q tests/test_chebnet_baseline.py
result:
  32 passed

command:
  $env:PYTHONPATH=<repo>/src
  C:/Users/Lough/AppData/Local/Python/pythoncore-3.14-64/python.exe \
    -m pytest -q tests
result:
  733 passed, 2 skipped
```

Expected environment warnings are PyG/Python-3.14 annotation deprecations,
PyTorch TorchScript deprecation, and one existing sparse-invariant warning.

### Experiment artifacts

- run IDs: none;
- result paths: none;
- aggregate paths: none;
- generated paper assets: none.

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Exact PyG 2.8 source/license identity | PASS | tag commit and byte hashes in provenance; executable wheel checks |
| Wrapper versus fresh upstream functional composition | PASS | bit-exact outputs and gradients |
| Sparse implementation versus independent dense oracle | PASS | output/input/parameter-gradient checks at K=1/2/4/6 |
| Parameter count | PASS | closed-form checks across all five task heads |
| SpMV count | PASS | `2(K-1)` checked against recurrence lengths |
| No dataset/H100/tuning/paper claim | PASS | no run artifacts or result files created |
| Truthful registry-v2 reference configuration | FAIL | no upstream five-dataset configuration exists |
| Machine-readable parity/admission artifact | NOT CREATED | fail-closed conditional behavior |

## Known limitations

- The parity fixtures are small deterministic CPU graphs, not benchmark
  performance reproductions.
- Dropout is disabled for deterministic end-to-end parity; the wrapper calls
  the standard PyTorch dropout function in training mode.
- PyG supplies only the licensed layer. Architecture and future training
  hyperparameters are local choices and must be labeled accordingly.
- Dataset redistribution terms remain a separate repository-wide blocker and
  were not investigated here.

## Reviewer questions

1. Does registry v2 need a distinct `LOCAL_EQUAL_BUDGET_CONFIG` provenance
   mode so a licensed upstream layer can be admitted without implying that the
   full architecture/configuration is upstream-published?
2. Are the dense-oracle independence boundary and gradient tolerances
   sufficient for implementation verification?
3. Should the preserved license notice and source-byte hash become mandatory
   environment checks for every H100 baseline worker?

## Conflicts or decisions needed

The orchestrator must choose whether to extend registry v2 with explicit
configuration provenance or exclude this ChebNet wrapper from the primary
scope. Do not mark it `VERIFIED` under the current ambiguous
`reference_config` meaning.

## Reproduction instructions

From the worktree root, run the two commands in the Tests section. No dataset,
network access, accelerator, or result artifact is required.

## Rollback

Revert commit `5820080117cbbc118c00ee82b0c477a2ff8dbf04`. No frozen result artifact is
altered by the patch.
