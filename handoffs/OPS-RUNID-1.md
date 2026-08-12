# OPS-RUNID-1 Handoff

## Task

- **Task ID:** OPS-RUNID-1
- **Agent:** Research Software Engineer
- **Branch:** `agent/engineering/OPS-RUNID-1`
- **Starting commit:** `708837eb55dbbb44f0d70ee6d0c8b784d03e21e6`
- **Ending commit:** the commit containing this handoff (reported on delivery)
- **Status proposed:** REVIEW

## Objective

Implement only the immutable, non-experimental submission-artifact core:
deterministic identity serialization, complete run hashing, typed records,
canonical paths, non-overwriting atomic bundles, resume classification, file
verification, prediction binding, and dirty-source enforcement.  Do not run
experiments or edit manuscripts, notebooks, scripts, configurations, legacy
code, frozen results, or the execution board.

## Summary

The new `gbdn.artifacts` module provides a stdlib-only artifact boundary over
the existing canonical output guard.  A run identity hashes every field frozen
by `08_RESULTS_AND_ARTIFACT_SCHEMA.md`.  Its path always spells out
experiment, dataset, model, variant, split, seed, trial, and the full run ID;
inapplicable split/seed/trial values use the validated `na` sentinel.

Completed runs are privately staged under `results_submission/state/staging`,
validated as a closed file set, claimed through exclusive creation in their
logical slot, and exposed by one same-tree directory rename.  `bundle.json` is
written only after config, predictions, result, and their hashes are present.
The resume classifier distinguishes `matching-complete`, `partial`, `corrupt`,
and `conflict`; only a fully matching bundle is safe to skip.  A prior failure
record permits a fresh attempt, but an interrupted staging directory remains
fail-closed for a later explicit quarantine policy.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `src/gbdn/artifacts.py` | Adds canonical JSON, full run identity, typed config/result/failure records, source/environment capture, manifests, atomic bundles, failure writing, and resume classification. | Yes; canonical engineering source. |
| `src/gbdn/provenance.py` | Rejects a `results_submission` root that resolves through a symlink/junction outside the repository. | Yes; existing canonical output guard. |
| `tests/test_artifact_core.py` | Adds adversarial identity, record, bundle, corruption, failure, source, environment, and resume tests. | Yes; canonical tests. |
| `tests/test_repository_boundaries.py` | Adds traversal, sibling-prefix, nested symlink, and symlinked-root escape tests, including Windows junction fallback. | Yes; canonical tests. |
| `handoffs/OPS-RUNID-1.md` | Records scope, verification, limitations, and review questions. | Yes; required governance handoff. |

No manuscript, notebook, script, configuration, dataset, legacy file, result,
generated asset, or execution-board file changed.  No raw artifact was created
inside the repository.

## Scientific impact

- **Claims enabled:** none.  This patch creates the provenance and immutability
  prerequisite for later claim-bearing runs.
- **Claims narrowed:** a directory or `result.json` alone is never evidence of
  completion; predictions and every indexed file must be present and hash-valid.
- **Claims rejected:** none.
- **Paper sections affected:** none.

## Evidence

### Proofs

- Not applicable.  This is an operational artifact contract.
- Security invariants are exercised through adversarial filesystem and record
  tests rather than promoted as mathematical theorems.

### Tests

```text
command: root virtual-environment Python with PYTHONPATH=<OPS worktree>/src,
         python -m pytest tests/test_artifact_core.py
                          tests/test_repository_boundaries.py
                          -q -p no:cacheprovider
result:  PASS, 39 passed

command: same environment,
         python -m pytest tests -q -p no:cacheprovider
result:  PASS, 476 passed, 2 third-party torch.jit deprecation warnings

command: same environment,
         python -m py_compile src/gbdn/artifacts.py
                              tests/test_artifact_core.py
                              tests/test_repository_boundaries.py
result:  PASS
```

The focused suite verifies:

- canonical JSON is stable under object-key order and rejects nonfinite or
  unsupported values;
- changing every one of the fourteen frozen identity dimensions changes the
  identity hash;
- split, seed, and trial always appear in the path, including `na`;
- traversal, sibling-prefix, symlink, and Windows-junction escapes are rejected;
- repeated writes and same-slot identities cannot overwrite completed runs;
- interrupted staging and incomplete final directories classify as partial;
- result or prediction tampering, missing predictions, and unindexed files
  classify as corrupt;
- prediction manifests bind path, size, SHA-256, format, and run identity;
- failures are typed, content-addressed, immutable, and safely retryable;
- full runs reject a dirty Git tree unless an explicit recorded override was
  used; different dirty content changes the source identity;
- dependency lock files are required and hashed.

### Independent adversarial review

A separate read-only reviewer reproduced one critical issue in an interim
optional staging-cleanup helper: Python on Windows followed a directory
junction during recursive deletion and removed an outside sentinel.  The
helper and all automatic partial deletion were removed entirely.  The final
core classifies that state as `partial` and refuses to resume over it.  No
other critical or high finding was confirmed before closeout; optional extended
probing was stopped at the orchestrator's request.

### Experiment artifacts

- **Run IDs:** none.
- **Result paths:** none.
- **Aggregate paths:** none.
- **Generated paper assets:** none.

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Deterministic canonical JSON | PASS | Key-order and invalid-value tests. |
| Hash every frozen identity field | PASS | Fourteen-field mutation test. |
| Typed/validated identity, config, result, failure | PASS | Round-trip and negative schema tests. |
| Explicit split/seed/trial paths and `na` | PASS | Canonical path tests. |
| Path traversal, sibling-prefix, symlink escape | PASS | Repository boundary tests, including Windows junctions. |
| Exclusive, non-overwriting creation | PASS | Artifact and per-slot claim tests. |
| Resume state classification | PASS | Matching, partial, corrupt, and conflict tests. |
| File SHA-256 verification | PASS | Direct and bundle tamper tests. |
| Prediction presence/hash/identity binding | PASS | Manifest validation and missing/tamper tests. |
| Atomic bundle visibility | PASS | Private staging, complete marker, validation, and single rename. |
| Dirty full-run policy | PASS | Temporary Git repository tests and typed run-mode validation. |
| No metric implementation | PASS | Result payload is opaque canonical JSON; no metric code was added. |
| No out-of-scope mutation or experiment | PASS | Diff inventory and no repository run artifacts. |

## Known limitations

1. Metric recomputation, result-metric semantics, dataset loading, runners, and
   notebook integration are intentionally absent.  They remain later tasks.
2. Partial or corrupt bundles are classified and blocked; this patch does not
   delete or quarantine them.  A later orchestration policy must move an exact
   validated target without following links before retrying.
3. Atomic publication assumes staging and final paths remain on the same
   filesystem.  Both are deliberately beneath `results_submission`.
4. The stdlib environment record captures Python/platform, dependency-lock
   hash, and determinism-related environment variables.  Torch, CUDA, driver,
   GPU, notebook, and package inventories must be supplied by the later H100
   preflight without importing CUDA in this core.
5. This is an application boundary rather than an OS permission sandbox.  A
   hostile process that can mutate directories concurrently may still create
   filesystem time-of-check/time-of-use races; artifact verification detects
   post-commit mutation but does not replace host access control.
6. Prediction validation proves presence, size, hash, expected filename, format
   label, and run binding.  It deliberately does not parse NPZ contents or
   recompute a metric yet.

Gate A and the H100 experiment program remain blocked; this infrastructure
patch does not change either gate decision.

## Reviewer questions

1. Does the later runner treat only `matching-complete` as skippable and refuse
   all other states until an explicit quarantine action succeeds?
2. Does the H100 preflight add accelerator/package/notebook metadata before any
   confirmatory bundle is created?
3. Does the metric task parse prediction contents independently and bind its
   recomputed value to this manifest rather than trusting `result.json`?

## Conflicts or decisions needed

No cross-agent file conflict exists.  The orchestrator must choose and review
the later quarantine policy; this patch intentionally makes no destructive
choice for partial artifacts.

## Reproduction instructions

```powershell
$env:PYTHONPATH='<repository>\src'
<python> -m pytest tests/test_artifact_core.py tests/test_repository_boundaries.py -q -p no:cacheprovider
<python> -m pytest tests -q -p no:cacheprovider
```

## Rollback

Revert the single OPS-RUNID-1 commit.  It removes the new artifact module and
tests and restores the four-line provenance guard change; no frozen artifact
or experimental output requires cleanup.
