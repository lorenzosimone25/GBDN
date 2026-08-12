# Gate A portable artifact binding: independent review

## Decision

**ACCEPT.** Gate A remains accepted under the frozen scientific contract at
reviewed source commit
`af20dd07374ef26a44f47874e8f5946eea24ccec`, tree
`11cfce0cb26e7fea7133888af949f3243d635304`.

The validator now binds report and review hashes to their tracked Git blob
bytes, rather than checkout-converted filesystem bytes, without weakening
tamper detection, source binding, semantic report validation, or resource
bounds. This closes the clean-checkout CRLF portability stop-line.

This review is not an acceptance token and does not authorize H100 execution
or any empirical claim.

## Reviewed repair

The review covered the narrow protected change from the prior accepted Gate
source `82a83c0390e5850617321bae5efb8491eb9692c6` through the final repair source.
The relevant changes are confined to:

- `src/gbdn/gate_acceptance.py`;
- `tests/test_gate_acceptance.py`;
- the stale token/report records that intentionally remain non-authorizing
  until this independent review is recorded.

The validator continues to require each bound artifact to be a nonsymlink
regular worktree file at a safe repository-relative path, tracked at `HEAD`,
and free of semantic uncommitted changes according to Git. It resolves the
tracked tree entry, requires regular-file mode and blob type, hashes the exact
blob bytes, and parses the exact tracked report bytes with duplicate-key,
non-standard-constant, schema, source, complete-row, evidence, provenance,
and cross-validation checks.

The initial portability patch had bypassed the former 8 MiB report bound. I
rejected that intermediate source. The final reviewed source repairs it:
`git cat-file -s <blob>` is evaluated before `git show`, reports larger than
8 MiB fail closed before materialization, and review artifacts retain their
128 KiB bound. Invalid/nondecimal size metadata also fails through the Git
command contract or explicit validation. The exact limit is accepted; only a
strictly larger blob is rejected, matching the prior filesystem policy.

## Independent adversarial evidence

In fresh temporary repositories generated independently from the test helper:

- converting both tracked report and review checkout bytes from LF to CRLF
  changed their filesystem SHA-256 values but remained Git-index-equivalent;
  the validator accepted the authoritative tracked blobs;
- a semantic report worktree edit was rejected as `gate report has
  uncommitted changes`;
- a committed report edit with the unchanged token was rejected as `gate
  report content hash does not match token`;
- the authored forged-and-rehashed report witness remained rejected by the
  complete 36-row semantic validator;
- a mocked oversized blob size was rejected as `gate report exceeds its
  tracked blob size limit`, and instrumentation confirmed that no `git show`
  body read occurred;
- an exact-8-MiB size value proceeded to the blob-read step;
- all previously reviewed ancestry, protected-source-drift, canonical-token,
  path, type, symlink, tracking, report-source, and review-verdict checks
  remain in force.

The byte-level authority is therefore portable without becoming permissive:
checkout-only newline conversion is tolerated precisely when Git regards it
as the same tracked content, while meaningful working-tree or committed
content changes still fail closed.

## Execution evidence

All tests ran in a fresh detached worktree at the exact reviewed source with
repository `src` on `PYTHONPATH` and the pytest cache disabled.

| Check | Result |
|---|---:|
| Focused Gate acceptance suite | 11 passed; 2 upstream warnings |
| Complete Gate selection | 516 passed; 3 warnings |
| CRLF tracked-blob probe | PASS |
| Semantic worktree tamper probe | REJECTED as required |
| Committed blob tamper probe | REJECTED as required |
| Oversized pre-materialization probe | REJECTED before `git show` |
| Exact size-limit probe | PASS |

Warnings were the existing Python 3.14/PyTorch deprecations and sparse
invariant warning; none affects the decision.

The clean report committed at
`db9aefaa7a87ea936565758828f22f54d1ee0f25` was independently read as raw Git
blob bytes and verified as:

```text
path:    results_submission/reports/gate_a_report.json
schema:  gbdn-gate-a-coverage-v3
sha256:  be37db82b661852ab13277da7f79402b041f76bde7d07f87b3e7043a713b1fcc
bytes:   1111607
source:  af20dd07374ef26a44f47874e8f5946eea24ccec
dirty:   false
pytest:  exit_code=0, tests_executed=true
```

It contains 479 Gate-labelled nodes; all GA-00--GA-35 rows pass; all required
IDs are present; there are no failed, missing, not-run, or evidence-deficient
rows; evidence schema, decisions, and provenance contain zero errors; and
coverage/evidence cross-validation passes. Its sole blocker is the external
independent review not yet being recorded by the token.

## Scientific and authorization boundary

GA-00 through GA-35 are each **ACCEPT** within the exact boundaries of the
prior independent reviews. This portability repair changes no operator,
parameterization, oracle, theorem assumption, numerical threshold, evidence
value, or scientific conclusion.

It supports only the frozen exact complete-map algebra, conditioning and
reconstruction, finite-realization frame certificates, fixed-root aligned
perturbation bounds, and scoped locality/cost statements. It does not support
practical anti-oversmoothing, oversquashing mitigation, target-specific
sensitivity, approximation advantage, predictive superiority, or long-range
reasoning.

## Refreshed-token requirements

A later token may record this verdict only if it binds:

- reviewed source commit
  `af20dd07374ef26a44f47874e8f5946eea24ccec`;
- reviewed tree `11cfce0cb26e7fea7133888af949f3243d635304`;
- the exact protected-path tuple at that source;
- the tracked report path/schema/blob SHA-256 above;
- this tracked review path and its tracked Git blob SHA-256;
- binary `ACCEPT` for GA-00 through GA-35.

The token must continue to fail if protected source changes after review, if
the token or bound artifacts change semantically in the worktree, if tracked
blob hashes differ, or if report semantics fail. This reviewer did not issue
or edit a token.

