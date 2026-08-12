# REV-OPS-SCHEDULER-5 independent review

## Verdict

**ACCEPT** the scheduler substrate at exact reviewed commit
`d3df9e92a933ad5bf0db815444feebf6e974f982`.

The repair closes the fourth review's ABA defect. Semantic evaluation captures
one bounded prediction byte snapshot, verifies its size and SHA-256 against the
immutable result manifest, parses and scores those same bytes, and binds the
attestation to that snapshot hash. Path replacement after capture cannot alter
the arrays scored.

This acceptance is deliberately narrow. The canonical worker
`scripts/run_heterophily_job.py` is absent at the reviewed commit, so no
official or H100 claim-bearing execution is authorized.

## Independent ABA witness

I reproduced the prior function-boundary attack without timing assumptions:

1. Capture manifest-bound archive A.
2. At the evaluator boundary, replace the path with distinct archive B.
3. During metric recomputation, restore A.
4. Inspect the logits actually scored and the emitted attestation.

Observed evidence:

```text
A SHA-256:              682eb9a736f530c282e1a2024ffbdd52595805f5916ab7e8fef7b5e3f1f7ea15
B SHA-256:              4febd54528084276cc9452d70b538a3b6234dc46c5f3100da12865ee2eba75e1
A logits SHA-256:       f54e454e484c9aee48ddf5bec8d55346ff808533081100decc23fe4e06dc1b42
B logits SHA-256:       3b2e80e9c9bac494a9ccc562b33d6ab016deb4e30a2f2c8a244bb8c3cf6745e6
scored logits SHA-256:  f54e454e484c9aee48ddf5bec8d55346ff808533081100decc23fe4e06dc1b42
attested prediction:    682eb9a736f530c282e1a2024ffbdd52595805f5916ab7e8fef7b5e3f1f7ea15
path restored to A:     true
authority values saved: false
```

The scored logits are A's, not B's, and the attestation binds A. The old ABA
witness therefore no longer crosses the trust boundary.

## Boundary attacks and static audit

- A snapshot whose size or SHA-256 differs from `result.json` is rejected
  before parsing or scoring.
- Empty, non-`bytes`, or over-limit snapshots are rejected; ZIP membership and
  decompressed-member limits are enforced on the captured bytes.
- Malformed ZIP/NPY payloads, extra members, and object arrays fail closed.
- Expected and stored split IDs require exact integer scalar types; floats,
  booleans, and vectors are rejected.
- Replacement or deletion of the prediction path after snapshot capture is
  irrelevant to parsing and scoring.
- The evaluation record persists hashes of authoritative indices and labels,
  not the authority values themselves.
- Static inspection found no independent second pathname read in the semantic
  score path: hashing, `np.load`, metric recomputation, and attestation all
  derive from the same `bytes` object.

## Focused test evidence

```text
PYTHONPATH=src python -m pytest -q \
  tests/test_submission_scheduler.py \
  tests/test_heterophily_evaluator.py \
  tests/test_artifact_core.py \
  tests/test_submission_verify.py -p no:cacheprovider

53 passed, 1 skipped, 2 warnings in 9.52s
```

The skip is the existing platform-conditional symlink test. Both warnings are
the known PyTorch `torch.jit.script` deprecations under Python 3.14.

## Acceptance boundary

| Criterion | Decision |
|---|---|
| Static manifest replacement | PASS: rejected |
| ABA path replacement | PASS: immutable A snapshot is scored and attested |
| Snapshot size/hash binding | PASS |
| ZIP/NPY and split-type trust boundaries | PASS |
| Post-capture path mutation | PASS: irrelevant to scored bytes |
| Authority values excluded from attestation | PASS |
| Focused scheduler/evaluator/artifact/verifier suite | PASS |
| Canonical worker present and independently reviewed | **FAIL: absent** |
| Scheduler substrate | **ACCEPT** |
| Claim-bearing/H100 execution | **BLOCKED** |

No scheduler acceptance token was issued by this review. The orchestrator may
record the bounded scheduler decision, but must keep execution blocked until a
canonical worker and its independent acceptance exist.
