# ENG-R3-ARTIFACT-1 handoff

## Task

- **Task ID:** ENG-R3-ARTIFACT-1
- **Agent:** Research Software Engineer
- **Branch:** `agent/engineering/ENG-R3-ARTIFACT-1`
- **Starting commit:** `64a14502625322319a2edf95d78dc064bd58d505`
- **Ending commit:** commit containing this handoff; SHA reported separately
- **Status proposed:** REVIEW

## Objective

Close the remaining R3 artifact boundary for canonical Tight GBDN outputs:
serialize and restore the complete residual-first tuple
`(r_0, ..., r_{D-1}, h_D)` without dtype, shape, value, or ordering drift, and
bind it fail-closed to the immutable run and existing bundle artifacts.

## Summary

- Added a non-pickle, explicitly little-endian binary codec for finite
  complex64/complex128 coefficient and root tensors.
- Added a strict canonical JSON manifest with frozen depth, residual-first
  component order, root order, per-tensor shape/dtype/source-device/range/hash,
  and whole-payload hash.
- Bound each record to the canonical `RunIdentity`, full `RunConfigRecord`,
  frozen config, full source record, full environment record, dependency lock,
  and at least one already-written managed artifact hash.
- Added a read-only managed-artifact verifier to `AtomicRunBundle`; forged,
  changed, duplicate, absent, or unmanaged binding manifests fail before the
  coefficient payload is written.
- Integrated semantic coefficient validation into completed-bundle validation.
  An incomplete pair, invalid order/shape/dtype/range, nonfinite value, changed
  binding, or hash mismatch prevents commit/resume classification as complete.
- Kept fixed paths and exclusive writes. Concurrent attempts have exactly one
  winner, and a second write cannot replace the first payload.

## Files changed

| File | Change |
|---|---|
| `src/gbdn/artifacts.py` | Fixed artifact paths, generic file-manifest verifier, semantic completed-bundle hook, and read-only managed binding validation |
| `src/gbdn/coefficient_artifacts.py` | Typed manifest, deterministic complex tensor codec, bound writer, validator, and loader |
| `tests/test_coefficient_artifacts.py` | Exact round trips and adversarial order/dtype/shape/hash/truncation/path/binding/write-once/race tests |
| `handoffs/ENG-R3-ARTIFACT-1.md` | This handoff |

## Scientific impact

- The public complete coefficient representation now has a tested immutable
  serialization boundary with the same residual-first order used by analysis,
  synthesis, and readout.
- Stored values are recovered bit-for-bit at their recorded complex dtype and
  shape; noncontiguous inputs are safely canonicalized without numerical
  conversion.
- This is provenance/integrity infrastructure only. It does not accept Gate A,
  validate experimental results, or support anti-oversmoothing,
  anti-oversquashing, approximation-efficiency, or benchmark claims.

## Evidence

```text
$env:PYTHONPATH='src'
py -3.14 -m pytest tests/test_coefficient_artifacts.py tests/test_artifact_core.py -q -p no:cacheprovider
43 passed

py -3.14 -m pytest tests/test_coefficient_artifacts.py -q -p no:cacheprovider
19 passed in each of five consecutive runs

py -3.14 -m pytest tests -q -p no:cacheprovider
522 passed, 3 warnings in 28.48s
```

Warnings are two upstream PyTorch/Python 3.14 JIT deprecations and the existing
PyTorch sparse-invariant warning.

## Intentional API constraints

- Serialization accepts only `TightAnalysisOutput`, not an untyped tensor
  tuple, so carry-first data cannot enter through an ambiguous flatten API.
- Coefficients and roots must be nonempty, finite complex64/complex128 strided
  tensors. Autograd history is intentionally not serialized.
- The source device is recorded. Loading defaults safely to CPU and supports
  an explicit non-meta `map_location`; it does not implicitly allocate on a
  recorded accelerator.
- At least one pre-existing managed artifact must be bound. The intended first
  use is the prediction manifest returned by the same open bundle.

## Remaining scope

1. Canonical runners/notebook still need to call the new writer when learned
   complete coefficients are a required run artifact.
2. A future artifact-schema revision would be needed for real, sparse,
   quantized, or non-complex coefficient tensors; none are silently coerced.
3. Gate A remains blocked pending independent re-review; this task supplies
   only the previously missing R3 serialization integration guard.

## Reproduction

Run the focused and full pytest commands above from a clean integrated commit.
Round-trip tests exercise both complex dtypes, distinct residual/carry values,
noncontiguous inputs, roots, and completed atomic bundle validation.

## Rollback

Revert the task commit. No manuscript, result, notebook, legacy source,
experiment artifact, execution board, or user-owned dirty file is changed.
