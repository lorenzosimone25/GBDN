# ENG-HET-WORKER-1 handoff

## Task

- **Task ID:** ENG-HET-WORKER-1
- **Agent:** Research Software Engineer
- **Branch:** `agent/engineering/CANONICAL-WORKER`
- **Starting commit:** `d1bc65d24aeb830de59d48557ffaeb8bdc80a4c3`
- **Ending commit:** commit containing this handoff; SHA reported separately
- **Status proposed:** REVIEW

## Objective

Implement the canonical official-heterophily training worker required by the
accepted sequential scheduler, without downloading datasets, running a GPU
job, fabricating method configurations, admitting baselines, or changing an
acceptance token/protected operations contract.

## Summary

The new canonical script delays every PyTorch-transitive import until after it
has verified one-device CUDA isolation and deterministic environment values.
It selects exactly one validated run-plan entry, repeats source/environment and
input-file binding checks, requires the pinned official NPZ identity, and
loads only explicit, closed, source-bound method configurations. There are no
training hyperparameter defaults.

One trusted orchestrator prepares two temporary snapshots from the pinned NPZ.
The fresh training subprocess receives graph/features plus train and validation
indices/labels only; its archive has no test member. It uses the official
dataset-specific head/loss and validation metric, keeps the earliest
validation-selected checkpoint, and records bounded deterministic training
history. A fresh evaluation subprocess receives only the frozen checkpoint and
the test view. It writes one-logit binary or official multiclass predictions in
the scheduler's exact archive schema. The scheduler remains responsible for
independent recomputation from authoritative data.

Checkpoint, prediction, selection/evaluation snapshot, method-config, source,
environment, run-plan, confirmatory-plan, registry, and worker bytes are
rechecked or hash-bound. Completed output uses `AtomicRunBundle`; it contains
the immutable config/result records, predictions, checkpoint, and
validation-only training record. Test data cannot change checkpoint or epoch
selection.

The implementation supports the canonical adapters that actually exist:
`TightGBDN`, `ProductSumGBDN`, `GBDNPlus`, and licensed PyG `ChebNet`. Any
unimplemented or unverified method fails closed.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `src/gbdn/heterophily_worker.py` | Dataset validation/snapshot isolation, closed method configs, deterministic training, post-freeze evaluation, and atomic artifact assembly. | Yes |
| `scripts/run_heterophily_job.py` | Canonical scheduler executable with CUDA/env checks before PyTorch import. | Yes |
| `tests/test_heterophily_worker.py` | CPU synthetic training/evaluation, task dispatch, leakage boundary, byte drift, JSON, graph, and prediction-recomputation tests. | Yes |
| `handoffs/ENG-HET-WORKER-1.md` | This handoff. | Yes |

## Scientific impact

- **Claims enabled:** none until frozen configurations, registry, run plan,
  dataset rights, and operations acceptance all pass independent review.
- **Claims narrowed:** a zero-exit training process is insufficient; only an
  atomic bundle whose predictions pass the independent evaluator is complete.
- **Claims rejected:** no universal CE/AUROC path, no test-visible checkpoint
  selection, no implicit hyperparameters, and no execution of unsupported
  methods.
- **Paper sections affected:** future official heterophily protocol/results
  only; no manuscript file changed.

## Evidence

### Tests

```text
command: PYTHONPATH=src python -m pytest -q tests/test_heterophily_worker.py
result:  10 passed, 1 known sparse-invariant warning

command: PYTHONPATH=src python -m pytest -q
         tests/test_heterophily_worker.py tests/test_heterophily_training.py
         tests/test_heterophily_evaluator.py tests/test_run_plan.py
         tests/test_submission_scheduler.py tests/test_artifact_core.py
result:  73 passed, 1 skipped, 3 known warnings

command: PYTHONPATH=src python -m pytest -q tests -p no:cacheprovider
result:  710 passed, 2 skipped, 145 known warnings
```

The deterministic/checkpoint-safe loop applies the relevant
`ml-training-recipes` principles: explicit seeding, finite loss/gradient
checks, optional explicitly configured clipping, `zero_grad(set_to_none=True)`,
and validation-only early stopping. The frozen scientific protocol overrides
generic recipe defaults, so no optimizer, learning rate, schedule, precision,
or epoch choice was invented.

### Experiment artifacts

- **Run IDs:** none
- **Result paths:** none
- **Aggregate paths:** none
- **Generated paper assets:** none

No network, dataset download, official dataset, CUDA device, H100, manuscript,
or result artifact was accessed or created.

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Official CE vs one-logit BCE dispatch | PASS | Existing loss contract plus task-dispatch worker tests |
| Validation-only checkpoint/epoch selection | PASS | Selection snapshot/record tests; snapshot contains no test member |
| Separate post-freeze test process | PASS | Distinct internal train/evaluate stage APIs and archives |
| Deterministic split and seed | PASS | Plan identity, exact split scalar, explicit seed/deterministic algorithms |
| Scheduler-compatible immutable prediction bundle | PASS | CPU end-to-end stage test plus independent evaluator recomputation |
| Source/environment/plan/registry/config binding | PASS | Pre/post runtime checks and byte hashes in result payload |
| No invented method hyperparameters | PASS | Closed config parser with no defaults; repository contains no fabricated configs |
| Full repository regression suite | PASS | 710 passed, 2 skipped |
| Full H100 execution readiness | FAIL | External/frozen inputs listed below remain absent or blocked |

## Known limitations

- `configs/submission/frozen/confirmatory_plan.json`,
  `results_submission/baseline_registry.json`,
  `results_submission/run_plan.json`, and explicit five-dataset method config
  files are not present at this starting commit. The worker intentionally fails
  closed rather than inventing them.
- Only four methods have canonical executable adapters. Every other desired
  comparator needs a separately licensed, parity-verified adapter and explicit
  configuration before it can enter a plan.
- Dataset-specific redistribution terms remain unresolved even though byte
  identities are pinned. No dataset was downloaded or redistributed.
- The accepted scheduler does not pass its `authoritative_dataset_root` to the
  child. Consequently the worker consumes the pinned `data/*.npz` relative to
  the repository root; the H100 operator must stage checksum-verified data
  there (it remains ignored), or a separately reviewed scheduler/worker
  interface change must pass an external root explicitly.
- Deterministic sparse CUDA backward must still pass the eventual one-job H100
  smoke. A deterministic-algorithm failure is a stop-the-line result, not a
  reason to weaken determinism silently.
- Runtime and peak allocated memory are recorded per worker stage; total
  scheduler/process overhead remains a separate compute-report field.

## Reviewer questions

1. Can any test index/label reach the training or checkpoint-selection
   subprocess through a snapshot member, CLI argument, config, or return value?
2. Can a changed plan, registry, method config, checkpoint, prediction, or
   worker file be committed under the original run identity?
3. Does each supported adapter emit exactly the official head shape and use
   only the dataset's official loss/validation metric?
4. Can a validation tie replace the earlier checkpoint, or can a test metric
   alter selected epoch/configuration?
5. Does the result bundle remain compatible with scheduler-side authoritative
   recomputation and resume validation under races or byte drift?

## Conflicts or decisions needed

The orchestrator must freeze explicit method configurations after baseline
admission and validation-only tuning. It must not make an unimplemented method
nominally `VERIFIED` merely to populate the run plan. Operations acceptance
must review these exact worker/module/test paths after integration; this
handoff is not an acceptance token.

## Reproduction instructions

```powershell
$env:PYTHONPATH=(Resolve-Path -LiteralPath src).Path
C:\Users\Lough\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pytest -q `
  tests/test_heterophily_worker.py tests/test_submission_scheduler.py `
  tests/test_heterophily_evaluator.py -p no:cacheprovider
```

## Rollback

Revert the single ENG-HET-WORKER-1 commit. No result, dataset, checkpoint,
acceptance token, paper asset, or GPU state requires cleanup.
