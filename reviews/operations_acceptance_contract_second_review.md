# Second independent operations-acceptance contract review

## Verdict

**REJECT** the contract design at exact reviewed source commit
`f6446aa` (`f6446aabe09a9850be80ea55a503ebe7a1b462dc`).

This verdict is limited to the v2 operations-acceptance contract. It does not
adjudicate a canonical heterophily worker, frozen execution inputs, an H100
run, or claim-bearing operations overall. Those artifacts are absent and
remain blocked.

## Stop-line defects

### 1. The protected surface is not a closed executable dependency boundary

The protected evaluator imports `gbdn.heterophily_statistics`, but
`src/gbdn/heterophily_statistics.py` is not protected. Every fresh import of a
`gbdn.*` module also executes `src/gbdn/__init__.py`, which is not protected.
The protected `scripts/run_submission.py` imports `gbdn.submission`, while
`src/gbdn/submission.py` is not protected either.

An independent attack built a valid source -> review -> token history with the
repository fixture, then committed unreviewed implementations after the token.
Both validations passed:

```text
UNREVIEWED_METRIC_CODE_ACCEPTED 8b88d768493668d0df9234ae44d7e575713238da
UNREVIEWED_PACKAGE_INIT_ACCEPTED 8b88d768493668d0df9234ae44d7e575713238da
```

The metric mutation replaced `recompute_primary_metric` with a constant-return
implementation. The package mutation placed executable code in
`src/gbdn/__init__.py`. Either can change claim-bearing behavior after review
without triggering protected-surface drift. This is sufficient by itself to
reject the contract.

The final worker is not present at this source commit, so its import closure
cannot yet be audited. Listing the future worker filename is not a substitute
for freezing its complete executable closure once it exists.

### 2. Git topology does not authenticate reviewer independence

The repair binds the machine review and handoff to a direct-child commit and
prevents rehashing those two files while retaining the original review commit.
It does not establish who created that commit. Git author and committer fields
are self-asserted, and the validator does not require a signature, a trusted
key, or an external attestation.

An independent attack checked out the reviewed source, configured Git as the
GBDN author, created an unconditional machine `ACCEPT` plus handoff as the only
two files in the direct-child commit, and committed a matching token. The
contract accepted the wholly self-issued lineage:

```text
SELF_ISSUED_REVIEW_ACCEPTED 584c02fabc4fb81f38226b0278d45fe40c749f56
REVIEW_AUTHOR GBDN Author <author@example.org>
SIGNED_VERIFY_RETURN_CODE 1
```

Thus v2 provides strong content integrity relative to a selected commit, but
not machine-verifiable independence. A token author can mint a new compliant
review commit instead of modifying an existing one.

### 3. Lexically noncanonical paths are normalized and accepted

`_safe_path` inspects `PurePosixPath.parts` after `PurePosixPath` has already
discarded `.` segments, repeated separators, and a trailing separator. Valid
tokens using each of the following review paths passed:

```text
NONCANONICAL_PATH_ACCEPTED 'results_submission/reports/./operations_review.json'
NONCANONICAL_PATH_ACCEPTED 'results_submission//reports/operations_review.json'
NONCANONICAL_PATH_ACCEPTED 'results_submission/reports/operations_review.json/'
```

The later resolved-containment and prefix checks prevent these examples from
escaping the repository, so this is not as severe as the first two defects.
It does contradict the contract's intended strict POSIX-path rule and leaves
multiple serialized names for one artifact.

## Repairs that are effective

The following first-review attacks are closed in the tested model:

- staged and unstaged protected-source changes are rejected;
- a replacement/rehashed review cannot impersonate the bound review-commit
  blob;
- a scheduler-only scope cannot be upgraded to claim-bearing acceptance;
- an author-controlled intermediate commit is rejected by the direct-parent
  rule;
- a review commit containing extra files is rejected;
- `..`, drive-qualified, and backslash paths are rejected;
- duplicate JSON keys and non-finite constants are rejected;
- protected paths must be tracked regular blobs at the reviewed commit and
  clean regular files at current `HEAD`.

These are meaningful fail-closed improvements, but they do not compensate for
an incomplete runtime boundary or unauthenticated independence.

## Required repair before another review

1. Freeze the transitive executable closure of every claim-bearing entry
   point. At minimum add `src/gbdn/__init__.py`,
   `src/gbdn/heterophily_statistics.py`, and `src/gbdn/submission.py`; after the
   canonical worker exists, audit its actual imports and all dynamically loaded
   implementations. Prefer a deliberately broad protected source boundary over
   a hand-maintained incomplete list.
2. Authenticate independent review with a verifiable trust anchor, such as a
   signed review commit checked against a pinned reviewer key/fingerprint or a
   separately authenticated CI/review attestation. A direct-parent unsigned
   commit is provenance structure, not proof of independence.
3. Reject noncanonical lexical paths before normalization, for example by
   checking raw slash-separated segments and requiring
   `value == PurePosixPath(value).as_posix()`.
4. Add adversarial regression tests for unprotected import-closure mutations,
   a wholly self-issued review lineage, and normalized path aliases.
5. Do not issue an operations token until the canonical worker, task contract,
   frozen plans/registry, and complete dependency surface exist and receive an
   unconditional independent claim-bearing review.

## Evidence

Clean detached checkout:

```text
HEAD f6446aa fix(ops): authenticate claim-bearing acceptance
python -m pytest -q tests/test_operations_acceptance.py -p no:cacheprovider
14 passed in 17.15s
```

No official dataset job or H100 job was run. No token, source, test, result,
paper, notebook, plan, registry, or execution-board file was changed by this
review.
