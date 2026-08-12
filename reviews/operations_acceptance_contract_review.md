# Independent operations-acceptance contract review

## Verdict

**REJECT** at exact reviewed commit
`e2bd9559d96add135545d20a33d91b1f6a7505b1`.

The contract does not safely bind the narrow independent scheduler review to
the code that the readiness verifier would authorize. Two executable attacks
cross the boundary, and the frozen protected surface omits the canonical
worker whose mere presence the verifier accepts.

No acceptance token or H100 job is authorized by this review.

## Stop-line defects

### 1. Uncommitted protected code is accepted

`validate_operations_acceptance` checks committed drift with
`git diff <reviewed-commit> HEAD`, but never checks the protected paths in the
working tree or index against `HEAD`. Only the token and review artifact get
an uncommitted-change check.

Independent witness, using the repository's own valid-token fixture:

```text
overwrite src/gbdn/artifacts.py without committing
validate_operations_acceptance(root)
DIRTY_PROTECTED_ACCEPTED d4732cade8164961a0bb93c6b0269e0ef5e7663e
```

Claim-bearing readiness can therefore pass its operations check while the
executed scheduler/evaluator/artifact code differs from the reviewed bytes.

### 2. The review's actual boundary is not enforced

The bound review explicitly says only **scheduler substrate ACCEPT** and
**claim-bearing/H100 execution BLOCKED**, because
`scripts/run_heterophily_job.py` was absent. The validator does not inspect or
machine-bind that scope. It trusts the token author's self-asserted
`review.verdict="ACCEPT"` and `review.independent=true`, so this conditional
review can be upgraded to a generic `independent_operations_acceptance: PASS`.

This is compounded by the protected-path list: it omits
`scripts/run_heterophily_job.py`. `submission_verify.py` accepts that worker
solely when it is a regular file. Thus an arbitrary later worker, never present
at or reviewed in the accepted commit, can satisfy readiness without protected
surface drift.

### 3. Rehashing a forged review remains sufficient

The hash provides integrity only relative to the token; it does not establish
independent authorship or bind the review artifact to a reviewer-controlled
commit. A token author can replace the review, recompute its SHA-256, commit
both files, and obtain acceptance:

```text
replace reviews/ops.md with "FORGED BY TOKEN AUTHOR"
update token review.sha256; commit token and review
validate_operations_acceptance(root)
FORGED_REHASHED_REVIEW_ACCEPTED
eb3b78d08ecfd4c64dc5b7cddba2552eb25ff965524188b624ca14d644c531b4
```

This is especially dangerous because the validator does not require the review
path to be the accepted scheduler review, nor require the review blob to exist
at a frozen independent review commit.

## Additional boundary observations

- Exact top-level/nested keys, canonical serialization, full commit/tree IDs,
  ancestor checks, content hashes, tracked evidence, and committed protected
  drift are useful fail-closed checks.
- Duplicate keys and non-finite constants are not explicitly rejected during
  parsing. Canonical byte comparison generally rejects them, but this should be
  tested directly rather than relied upon implicitly.
- Path validation is weaker than the Gate-A contract: it permits backslashes,
  drive-qualified Windows strings, and `.` segments at the lexical check. An
  explicit POSIX-path validator plus resolved containment check is required.
- The contract does not require every protected path to be a tracked regular
  file at both the reviewed commit and current `HEAD`; deletion is caught as
  committed drift, but an untracked replacement is part of the dirty-tree
  defect above.
- `.gitattributes` freezes Markdown and JSON to LF, which is a sound portability
  prerequisite. Review hashes must still be computed over the checked-out
  bytes and covered by portability tests.

## Required repairs before re-review

1. Reject staged, unstaged, deleted, and untracked changes on every protected
   path, including the canonical worker and its tests.
2. Add the worker, worker tests, task contract, run-plan binding, and every
   claim-bearing scheduler dependency to the exact protected surface.
3. Bind a machine-readable, unconditional operations verdict whose declared
   scope includes the worker and claim-bearing execution; do not reinterpret
   the existing scheduler-only review.
4. Bind the review to an independently authored/tracked review commit or an
   equivalently authenticated provenance mechanism, not a self-asserted token
   field plus a freely recomputable hash.
5. Reuse strict POSIX relative-path and resolved-containment validation, and add
   adversarial tests for duplicate keys, non-finite values, symlinks, escapes,
   dirty protected files, forged reviews, missing protected files, and LF/CRLF
   portability.

## Test evidence

The repository's existing focused tests pass but do not cover the attacks:

```text
python -m pytest -q tests/test_operations_acceptance.py -p no:cacheprovider
4 passed in 3.46s
```

No source, test, token, paper, result, board, or H100 artifact was changed.
