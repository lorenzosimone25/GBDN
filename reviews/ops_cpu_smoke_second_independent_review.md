# Second independent operations review

## Binary decisions

**A — Stage-1 diagnostic CPU smoke: ACCEPT, strictly as a non-claim-bearing
operations diagnostic.** The accepted boundary is exactly one fixed synthetic
CPU job. It does not authorize an official dataset, CUDA/H100 execution,
mechanism evidence, a benchmark, or a paper number.

**B — Scheduler safety for binding to a future canonical heterophily worker:
REJECT.** The scheduler must not be connected to a claim-bearing worker yet.
It does not perform the required independent metric recomputation when it
skips an existing bundle or accepts a worker's zero-exit postcondition, and it
does not rebind the frozen job source/environment to the source/interpreter
that will actually execute.

The repository therefore remains **STOP-LINE for H100 and official
confirmatory execution** despite decision A.

## Scope and independence

I reviewed commit `b6db07ff30432948ee4663892f80579941fff04a` in a detached
worktree. I read the H100 preflight, CPU-smoke, run-identity, run-plan,
scheduler, Gate-acceptance, notebook-verification handoffs; the notebook and
its specification; and the artifact, run-plan, scheduler, evaluator,
statistics, verifier, and acceptance implementations and tests.

No H100 job or official dataset was executed. I made no source, test, paper,
result, state, board, notebook, or token change. This review and its handoff
are the only files added.

## Evidence for decision A

The diagnostic CLI sets `CUDA_VISIBLE_DEVICES=-1` before importing `gbdn` or
PyTorch (`scripts/run_submission.py:13-17`). Plan construction independently
requires the same value before environment capture
(`src/gbdn/submission.py:208-215`), and the parent supplies a fresh child
environment with the same isolation (`src/gbdn/submission.py:507-515`). The
worker executes in a separate process and returns a different PID.

The smoke identity binds the frozen fixture, source, dependency lock, and CPU
precision. A completed result is not skipped merely because its bundle hashes
validate: `_read_completed_result` checks the plan identity, exact source and
environment records, closed result schema, CPU compute record, and separately
recomputes accuracy from the stored NPZ (`src/gbdn/submission.py:330-387`).
Both pre-launch resume and post-worker acceptance use that semantic check.

The artifact core creates files exclusively, validates the closed bundle,
takes an exclusive per-slot commit claim, and exposes the completed directory
with one rename (`src/gbdn/artifacts.py:1531-1597`). Static traversal,
symlink/junction, conflicting identity, corrupt file, partial path, and stale
staging states fail closed. There is no automatic recursive deletion or
overwrite path. Concurrent writers can cause one attempt to fail, but cannot
legitimately replace a completed bundle.

Focused authored and adversarially relevant tests for these boundaries passed.
The accepted smoke remains deliberately diagnostic: it has no training,
selection, official labels, or empirical claim.

## Confirmed blockers for decision B

### OPS-B1 — no independent evaluation on skip or completion (critical)

`run_confirmatory_scheduler` increments `skipped` for any
`MATCHING_COMPLETE` result returned by `classify_resume`
(`src/gbdn/submission_scheduler.py:85-88`). After a zero-exit worker it uses
the same condition to increment `completed`
(`src/gbdn/submission_scheduler.py:130-133`). Bundle classification verifies
identity, manifests, hashes, and typed record consistency, but it does not
verify the official prediction archive against authoritative test indices and
labels or recompute the dataset's official metric.

The independent evaluator exists at
`src/gbdn/heterophily_evaluator.py:36`, but the scheduler never imports or
calls it. Consequently, a self-consistent, hash-valid bundle containing a
wrong reported metric, wrong authoritative label binding, or semantically
wrong predictions is currently skippable and countable as complete. This
violates the H100 notebook resume condition and the explicit independent
metric-recomputation gate.

Required repair: a separate trusted evaluation step must load authoritative
dataset/split identity, test indices, and labels; call the independent
evaluator; compare the recomputed metric with the result under a frozen
tolerance; and persist/hash-bind that verification. Both skip and successful
postcondition paths must require it.

### OPS-B2 — execution source and environment are not rebound (high)

Run-plan validation requires that job records share one clean recorded source
and environment (`src/gbdn/run_plan.py:136-163`), but it does not recapture the
current repository source or current interpreter environment and compare them
with those records. The scheduler validates only that the worker path resolves
to `scripts/run_heterophily_job.py`, then launches it with `sys.executable`
and selected environment variables. It does not hash-bind the worker at launch
or prove that `sys.executable`, dependencies, source commit/tree, and lock are
the frozen job environment.

Required repair: before every launch and skip decision, recapture current
source/environment and require exact equality with the job record; bind the
canonical worker file to the frozen source; and require the worker to repeat
the same checks before artifact creation. A changed run-plan file must also be
detected between parent validation and worker read.

### OPS-B3 — scheduler failure evidence is incomplete (medium)

The scheduler captures stdout/stderr in memory, but does not persist the
required per-run logs. Failure records store only a truncated stderr suffix in
`message`, use `traceback_path=na`, and declare no partial artifacts
(`src/gbdn/submission_scheduler.py:118-151`). A timeout or worker exception is
isolated and later jobs may continue, but the resulting record does not meet
the notebook/result-schema provenance requirement.

Required repair: write immutable, bounded stdout/stderr/traceback manifests
and bind them to the failure record without overwriting previous attempts.

### OPS-B4 — no canonical worker exists (blocking fact)

`scripts/run_heterophily_job.py` is absent at the reviewed commit. The
scheduler intentionally refuses launch in that state. Therefore its interface
cannot yet be end-to-end reviewed against worker-side identity, official
dataset, checkpoint-selection, prediction, or independent-evaluation behavior.

## Integrated test finding

The focused command completed with **88 passed, 2 skipped, 1 failed**. The
failure is
`tests/test_submission_verify.py::test_current_repository_verifier_is_read_only_and_blocked`:
the test still requires an "acceptance token is absent" blocker even though
commit `b6db07f` installs the independently accepted Gate-A token. This is a
stale integration assertion, not a smoke artifact-integrity failure, so it
does not reverse decision A. It does mean the reviewed repository is not
fully green and must be repaired before the next operations acceptance.

The two skips are the platform-conditional symlink cases. Static path escape
coverage otherwise passed.

## Race and filesystem boundary

The implementation is fail-closed for the tested single-operator model and
for static symlink/junction/traversal attacks. Like ordinary `pathlib` checks,
it is not a hardened security boundary against another privileged local
process that swaps directory components between resolution and open/rename.
No destructive cleanup makes such a race less dangerous, and an unexpected
state remains partial/corrupt/conflicting rather than resumable. Before shared
or hostile multi-user execution, directory-handle-relative no-follow opens or
equivalent platform primitives would be needed. This limitation does not
authorize weakening any current path test.

## Notebook decision

The five-cell notebook is correctly thin and fail-closed, but it exposes no
phase-launch interface. Its final cell calls the read-only verifier and raises
unless the full submission is complete. It therefore does not bypass the
scheduler rejection, and it must not be interpreted as an accepted H100
operator notebook yet.

## Commands executed

```powershell
$env:PYTHONPATH=(Resolve-Path -LiteralPath src).Path
python -m pytest -q \
  tests/test_submission_smoke.py \
  tests/test_artifact_core.py \
  tests/test_repository_boundaries.py \
  tests/test_submission_scheduler.py \
  tests/test_run_plan.py \
  tests/test_heterophily_evaluator.py \
  tests/test_heterophily_statistics.py \
  tests/test_submission_verify.py \
  tests/test_gate_acceptance.py \
  -p no:cacheprovider
```

Result: `88 passed, 2 skipped, 1 failed` in 61.74 seconds, with two existing
PyTorch/Python 3.14 deprecation warnings.

## Authorization boundary

Decision A accepts only the diagnostic CPU primitive. Decision B rejects
worker binding. H100 execution, official datasets, confirmatory artifacts,
aggregation, paper tables, and any scientific claim remain blocked until
OPS-B1 through OPS-B4 are repaired and independently reviewed, the stale
verifier test is corrected, and the full suite is green.
