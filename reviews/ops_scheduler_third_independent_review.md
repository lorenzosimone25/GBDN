# REV-OPS-SCHEDULER-3 independent review

## Verdict

**REJECT** at reviewed commit
`d4b2624dcb5ad22fb30183a095269265d0ab8fdb`.

The repair closes the major defects from the preceding operations review, but
the semantic evaluator is not cryptographically bound to the prediction
manifest it purports to validate. A valid result can therefore be paired with
different prediction bytes after bundle classification and still receive an
independent evaluation attestation and scheduler credit when the replacement
bytes produce the same reported primary metric. This is a stop-the-line
artifact-integrity failure.

The canonical worker `scripts/run_heterophily_job.py` is also absent at the
reviewed commit. Consequently, even after the finding below is repaired, no
official or H100 claim-bearing execution is authorized until that worker and
its own independent acceptance exist.

## Scope and evidence boundary

This review used a fresh detached worktree at the exact commit above. It read
the governing software, notebook, artifact, and global-agent contracts; the
second independent operations rejection; `OPS-SCHEDULER-REPAIR-1`; and the
repaired scheduler, evaluator, artifact core, and tests. It ran no H100 job and
downloaded or executed no official dataset.

## Confirmed blocker: prediction-manifest TOCTOU

`classify_resume` verifies the complete bundle and its prediction manifest,
then returns a path. `_semantic_evaluation` subsequently parses `result.json`
and evaluates `bundle / result.predictions.path`, but never invokes
`validate_prediction_manifest` and never compares the evaluated file's size or
SHA-256 with `result.predictions`. The two reads are therefore not one bound
operation.

Direct adversarial witness:

1. Create prediction archive A and a `RunResultRecord` whose prediction
   manifest records A's SHA-256.
2. Replace `predictions.npz` with distinct archive B. B has the same identity,
   indices, shape, and primary accuracy, but different logits and bytes.
3. Call `_semantic_evaluation` with authoritative indices and labels.
4. The call succeeds and writes an attestation for B's SHA-256, even though
   B's hash differs from the result manifest.

Observed hashes:

```text
manifest/archive A: eec3340e6c8b882b285135ef2948f0ea8471eb23af66700fe0f8ee5e922ad0c9
evaluated/archive B: 7256727a1e79585ed66e654b7c7bfa231b704465678bfda62bace6a21508ab72
ACCEPTED_DRIFT: True
```

In the scheduler this is reachable as a classify-to-evaluate race on both the
skip and successful-worker paths. It can also cause the evaluator attestation
to bind bytes that the immutable bundle manifest rejects. Hashing B inside the
attestation does not repair the broken relationship to `result.json` and
`bundle.json`.

Required repair:

- Validate the prediction manifest at the point of semantic evaluation,
  including run ID, regular/safe path, exact size, and SHA-256.
- Eliminate the check/use window: evaluate one immutable byte snapshot or
  otherwise prove the same bytes validated are the bytes scored; revalidate
  after scoring if a snapshot cannot be used.
- Bind the resulting attestation to the manifest SHA-256 and reject any
  disagreement.
- Add a deterministic regression that replaces the prediction between bundle
  classification and evaluation and requires blocked/failed status with no
  attestation and no skipped/completed credit.

## Secondary schema defect

`evaluate_prediction_archive` obtains the stored split using
`int(np.asarray(stored["split_id"]).item())`. A float scalar such as `0.75` is
silently coerced to official split `0` and accepted. The archive schema should
require exact scalar shape and integer dtype for `split_id`, plus exact scalar
string/Unicode types and bounded lengths for the other identity fields.
This did not produce the main manifest-bypass verdict, but it must be repaired
before scheduler acceptance because archive schema validation is a trust
boundary.

## Findings that passed review

The following repaired behavior is substantively correct in the reviewed
implementation, subject to the blocking race above:

- skip and zero-exit paths invoke semantic evaluation;
- authoritative NPZ loading checks pinned path, byte size, SHA-256, required
  arrays, dtypes, full shapes, official split row, and nonempty test indices;
- authoritative labels and indices remain in the parent evaluator, while the
  attestation stores only their hashes;
- prediction archive membership, decompressed-member limits, identity,
  ordered indices, finite logits, task-specific shape, and official metric are
  checked;
- current source, environment, dependency lock, plan, confirmatory plan,
  registry, and worker are checked before launch and after a zero exit;
- corrupt, conflicting, and unrecoverable partial states are not executed;
- failure evidence is bounded, redacted, hash/size bound, exclusively created,
  and recursively checked for extra, missing, symlinked, or modified files;
- worker selection is restricted to the canonical regular repository path;
- the scheduler imports PyTorch transitively through `gbdn.__init__`, but GPU
  visibility is still established by the notebook/launcher before the
  scheduler process imports the package. The scheduler correctly passes the
  frozen device and determinism environment to each isolated worker child.

The repair therefore represents meaningful progress, but the passed checks do
not compensate for a broken prediction-to-result binding.

## Test evidence

```text
PYTHONPATH=src python -m pytest -q \
  tests/test_submission_scheduler.py \
  tests/test_heterophily_evaluator.py \
  tests/test_artifact_core.py \
  tests/test_submission_verify.py

50 passed, 1 skipped, 2 warnings in 10.61s
```

The skip is the platform-conditional symlink test. The warnings are existing
PyTorch/Python 3.14 deprecations. These green tests do not cover the confirmed
manifest replacement witness.

## Acceptance decision

| Criterion | Decision |
|---|---|
| Structurally valid but semantically wrong skip/zero-exit bundles | PASS for metric mismatch; **FAIL** for manifest-replaced, metric-equivalent bytes |
| Pinned authoritative NPZ identity and split handling | PASS, with scalar `split_id` schema defect |
| No authority labels/indices in worker or attestation | PASS |
| Evaluator invoked on every skip/completion | PASS |
| Source/environment/dependency/plan/registry/worker drift | PASS for checked boundaries |
| Partial/corrupt/conflict/race safety | **FAIL** for classify-to-evaluate prediction replacement |
| Failure evidence immutability, bounds, redaction, hashes | PASS |
| GPU isolation boundary | PASS as orchestration design; no hardware execution performed |
| Canonical worker available and reviewed | **FAIL: absent** |

No scheduler acceptance token may be issued from this review.
