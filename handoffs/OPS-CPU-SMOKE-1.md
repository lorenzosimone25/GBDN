# OPS-CPU-SMOKE-1 handoff

## Task

- **Task ID:** OPS-CPU-SMOKE-1
- **Agent:** Research Software Engineer
- **Branch:** `agent/engineering/OPS-CPU-SMOKE-1`
- **Starting commit:** `b9f33383124f8afaa52c112b3a46105800c016ef`
- **Ending commit:** commit containing this handoff; SHA reported separately
- **Status proposed:** REVIEW

## Objective

Implement only the Stage-1 CPU submission orchestration milestone: a safe CLI
and reusable API for preflight and exactly one frozen synthetic smoke job,
executed in an isolated subprocess and committed through the existing immutable
artifact/resume core. No CUDA job, dataset download, official benchmark,
notebook, paper asset, or scientific claim is in scope.

## Summary

`scripts/run_submission.py` now exposes `preflight`, `smoke`, and an internal
`run-job` worker. Before importing the canonical package or PyTorch, it sets
`CUDA_VISIBLE_DEVICES=-1`. The public Stage-1 plan accepts one canonical JSON
configuration containing one fixed synthetic binary job and no absolute paths.

The parent binds the config, source, dependency lock, and synthetic dataset to
one `RunIdentity`; launches a fresh Python worker; and accepts completion only
after the existing `AtomicRunBundle` validator and a separate prediction-file
metric recomputation both pass. The worker's reported accuracy is computed
without reading the NPZ, while the verifier independently loads the stored
logits and labels. A second invocation classifies the bundle as
`matching-complete`, returns `skipped`, and preserves the original worker PID,
proving that resume does not rerun the job.

A post-implementation adversarial pass additionally binds the completed
bundle's full source and environment metadata back to the parent plan, permits
only the repository's canonical worker script, supplies an explicit isolated
child environment, limits compressed prediction archives and members, and
rejects a canonical output root that resolves through a symlink outside the
repository. These checks close gaps not covered by the original seven tests.

Every non-smoke mode is blocked. Dirty claim-bearing source fails through the
existing source policy; clean claim-bearing source also fails because the
independent Gate-A token/schema is absent. Merely adding a token-shaped file
cannot unlock this Stage-1 implementation.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `configs/submission/cpu_smoke.json` | Adds the single portable, frozen diagnostic CPU plan. | Yes; canonical configuration. |
| `src/gbdn/submission.py` | Adds plan validation, identity binding, smoke worker, subprocess orchestration, semantic resume verification, and independent metric recomputation. | Yes; canonical engineering source. |
| `scripts/run_submission.py` | Adds the Stage-1 CLI and pre-import CPU isolation. | Yes; canonical runner. |
| `tests/test_submission_smoke.py` | Adds preflight, subprocess, immutable commit, resume/no-rerun, tamper, metric, gate, boundary, and CLI tests. | Yes; canonical tests. |
| `README.md` | Replaces the now-stale “interface absent” text with the precise diagnostic-only Stage-1 boundary. | Authorized narrow documentation update. |
| `handoffs/OPS-CPU-SMOKE-1.md` | Records scope, evidence, and blockers. | Yes; required handoff. |

No manuscript, notebook, result, generated asset, legacy source, frozen result,
audit, or execution-board file changed. Test artifacts were created only under
pytest temporary repositories.

## Scientific impact

- **Claims enabled:** none. The smoke validates an operational path only.
- **Claims narrowed:** a hash-valid bundle is skippable by this runner only when
  its stored prediction schema and independently recomputed accuracy also agree.
- **Claims rejected:** none.
- **Paper sections affected:** none.

Gate A remains blocked and this patch does not alter its state.

## Evidence

### Tests

```text
command: PYTHONPATH=src python -m pytest -q tests/test_submission_smoke.py
         -p no:cacheprovider
result:  PASS, 7 passed

command: PYTHONPATH=src python -m pytest -q
         tests/test_submission_smoke.py tests/test_artifact_core.py
         tests/test_gate_a_provenance.py -p no:cacheprovider
result:  PASS before adversarial extension; rerun required with current tree

command: PYTHONPATH=src python -m pytest -q tests -p no:cacheprovider
result:  superseded by the current integrated full-suite record

command: python -m py_compile src/gbdn/submission.py
         scripts/run_submission.py
result:  PASS
```

The warnings are the existing two PyTorch/Python 3.14 TorchScript deprecations
and one PyTorch sparse-invariant warning.

### Experiment artifacts

- **Run IDs:** none retained; synthetic run IDs were temporary test fixtures.
- **Result paths:** none retained or committed.
- **Aggregate paths:** none.
- **Generated paper assets:** none.

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Exactly one frozen synthetic job | PASS | Strict config key/value/cardinality validation and negative tests. |
| CPU only, isolated before PyTorch import | PASS | CLI pre-import guard plus persisted worker `CUDA_VISIBLE_DEVICES=-1`. |
| Frozen config/source/lock/run identity | PASS | Existing typed records and deterministic identity used end to end. |
| Isolated subprocess | PASS | Worker PID differs from parent. |
| Immutable atomic bundle | PASS | Existing `AtomicRunBundle`; expected closed bundle file set asserted. |
| Safe resume without rerun | PASS | Second call is `skipped` and returns the original worker PID. |
| Predictions and labels saved | PASS | Typed NPZ schema includes logits, labels, indices, split, and run ID. |
| Independent metric recomputation | PASS | Separate NPZ loader recomputes 4/6 accuracy and gates resume. |
| Tamper fail-closed | PASS | Changed prediction bytes classify `corrupt`; runner refuses them. |
| Parent/worker environment binding | PASS | A completed bundle with environment metadata different from the parent plan classifies corrupt. |
| Canonical worker identity | PASS | Library orchestration rejects a worker script outside the repository root. |
| Compressed input bounds | PASS | Oversized archives and oversized compressed members reject before NumPy loading. |
| Claim-bearing mode blocked | PASS | Dirty-tree and absent/unfrozen Gate-A-token tests. |
| Canonical output only | PASS | Noncanonical and legacy output roots are rejected. |
| No machine-specific config paths | PASS | Portable config contains only scalar plan values. |

## Known limitations

1. This is diagnostic infrastructure, not a mathematical or empirical result.
2. Gate A is independently blocked; no H100, mechanism, benchmark, or paper
   phase may consume this smoke as scientific evidence.
3. The Gate-A acceptance token schema is deliberately unimplemented. A later
   independently reviewed patch must define and source-bind it before any
   claim-bearing mode can exist.
4. Only one fixed accuracy fixture is supported. Official dataset, split,
   task-loss, metric, baseline, tuning, and statistical contracts are absent.
5. Failed or interrupted staging bundles remain fail-closed under the existing
   artifact policy; quarantine and multi-job failure continuation are not part
   of this one-job milestone.
6. The H100 notebook, accelerator selection, scheduler, aggregation, rendering,
   and final submission verifier remain absent.
7. The synthetic prediction NPZ is intentionally small and strict; it is not a
   general benchmark prediction codec.

## Reviewer questions

1. Is the separate reported-metric path versus saved-NPZ recomputation
   sufficiently independent for the Stage-1 operational test?
2. Does `matching-complete` remain the only skippable state under all tamper and
   same-slot identity cases?
3. Is setting `CUDA_VISIBLE_DEVICES=-1` before the first `gbdn` import a strong
   enough CPU isolation proof for this platform matrix?
4. Should failure-record/quarantine orchestration be the next operations slice,
   before the notebook and any GPU scheduler are created?

## Conflicts or decisions needed

No file conflict or scientific decision is introduced. The orchestrator must
not promote this patch beyond diagnostic Stage 1 and must keep H100 execution
blocked while Gate A or official task contracts are unaccepted.

## Reproduction instructions

```powershell
$env:PYTHONPATH='<repository>\src'
<python> scripts/run_submission.py preflight
<python> scripts/run_submission.py smoke
<python> scripts/run_submission.py smoke  # returns skipped; does not rerun
<python> -m pytest -q tests/test_submission_smoke.py -p no:cacheprovider
```

The CLI smoke writes an immutable local diagnostic bundle below
`results_submission/raw`; do not commit that bundle.

## Rollback

Revert the single OPS-CPU-SMOKE-1 commit. No frozen or user-owned artifact needs
cleanup because this task commits no run output.
