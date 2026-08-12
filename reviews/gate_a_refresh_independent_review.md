# Gate A protected-surface refresh: independent review

## Decision

**ACCEPT.** Gate A remains accepted under the frozen scientific contract at
reviewed source commit
`82a83c0390e5850617321bae5efb8491eb9692c6`, tree
`397eca83b7740c5785d3b52db2dc2254bc0a8be8`.

This refresh was required because the old acceptance token treated the
submission launcher as Gate-A source even though that launcher is an
operations boundary. The corrected contract removes
`scripts/run_submission.py`, adds the public package surface and all
import-time dependencies of the Gate implementation and validator, and
removes a stale nonexistent test path. The resulting 26-path set is unique,
exists completely, and is closed under all import-time `gbdn` dependencies.
No GA-00--GA-35 mathematical implementation or evidence semantics were
weakened.

This review is not an acceptance token and does not authorize an H100 run,
confirmatory experimentation, or an empirical claim.

## Reviewed change and boundary analysis

The previous accepted mathematical source was
`a8be64da25de060f7e7d634d45362827fded147c`. Across the corrected protected
surface, the only changed files are:

- `src/gbdn/artifacts.py`: operations failure-artifact extensions; the
  `ArtifactValidationError`, canonical JSON, and SHA-256 primitives consumed
  by Gate acceptance retain their behavior;
- `src/gbdn/gate_acceptance.py`: protected-path scope correction only;
- `tests/test_gate_acceptance.py`: explicit scope regression assertions.

The new protected set adds:

- `src/gbdn/__init__.py`, because Gate tests exercise the public root API;
- `src/gbdn/artifacts.py`, because the acceptance validator directly consumes
  its canonical serialization, hashing, and error primitives;
- `src/gbdn/provenance.py`, imported at module load by `artifacts.py`;
- `src/gbdn/seed.py`, imported at package load by `gbdn.__init__`.

It removes:

- `scripts/run_submission.py`, whose confirm/smoke CLI and device isolation
  contain no theorem, operator, evidence, reporter, or acceptance semantics;
  claim-bearing scheduler and readiness code call
  `validate_gate_a_acceptance` directly, while the launcher remains inside
  the independently reviewed operations surface;
- `tests/test_gate_a_fixture_completion.py`, which does not exist at the
  reviewed source.

An AST import-time closure traversal from every protected `src/gbdn` module
found zero unprotected internal dependencies. All 26 paths exist, are unique,
and the reviewed worktree was clean. Function-local imports in unrelated
artifact bundle validation do not execute on the Gate reporting or acceptance
path and were not improperly pulled into the mathematical gate.

The scope separation is therefore sound: launcher changes cannot alter any
GA result or make Gate acceptance self-issue, and changes to any public API,
mathematical implementation, evidence/reporting component, acceptance
primitive, or Gate regression now invalidate the token.

## Independent execution evidence

All executions used a fresh detached Windows worktree at the exact reviewed
source, with repository `src` on `PYTHONPATH` and the pytest cache disabled.

| Check | Result |
|---|---:|
| Complete `test_gate_a*.py` plus acceptance selection | 514 passed; 3 warnings |
| Clean Gate reporter | 479 Gate-labelled nodes; 36 PASS rows |
| Mappings | 18 UNIQUE; 18 legitimate DUPLICATE; 0 MISSING |
| Evidence validation | 0 schema errors; 0 failed decisions |
| Coverage/evidence cross-validation | PASS; 0 mismatches |
| Provenance validation | 0 errors; clean source at exact commit |
| Full repository suite | 767 passed; 2 skipped; 1 expected stale-token failure |

The full-suite failure is
`test_current_repository_verifier_is_read_only_and_blocked`: at the reviewed
source the committed token still names the superseded protected set and must
fail closed until this independent review is recorded in a refreshed token.
The observed `independent_gate_a_acceptance=FAIL` is therefore the intended
security behavior, not a Gate regression. No other full-suite test failed.
Warnings were the existing Python 3.14/PyTorch/PyG deprecations and sparse
invariant warning; skips were the documented Windows symlink-privilege cases.

I independently regenerated a temporary clean report at the reviewed source;
it passed the same semantic inventory. The tracked clean report committed at
`53c8c4619a6420abfb302107a49bdb8b8556b6dc` was separately byte-checked and
has:

```text
path:    results_submission/reports/gate_a_report.json
schema:  gbdn-gate-a-coverage-v3
sha256:  311896b32b2470a74d43e05b583b8b9364a9755cfcbe5bfa172c1163e39073c8
source:  82a83c0390e5850617321bae5efb8491eb9692c6
dirty:   false
pytest:  exit_code=0, tests_executed=true
```

That report contains all 36 required IDs, no missing, failed, not-run, or
machine-evidence-deficient row, and its sole acceptance blocker is the absence
of a recorded independent review.

## Mandatory-row and claim adjudication

GA-00 through GA-35 are each **ACCEPT** at the exact reviewed source, within
the row boundaries adjudicated in the fifth independent review. The refresh
does not change the operator, oracle, parameterization, proofs-as-tests,
fixtures, numerical tolerances, evidence catalog, or reporter decisions.

In particular, acceptance still supports only the frozen exact complete-map
algebra, conditioning and reconstruction, finite-realization frame
certificates, fixed-root aligned perturbation bounds, and scoped locality and
cost statements. It does not turn Parseval tightness or global Jacobian norm
preservation into carried-state non-dissipation, practical resistance to
oversmoothing, target-specific sensitivity, oversquashing mitigation,
spectral approximation advantage, predictive superiority, or long-range
reasoning.

## Refreshed-token binding requirements

A later token may record this verdict only if it binds exactly:

- reviewed source commit:
  `82a83c0390e5850617321bae5efb8491eb9692c6`;
- reviewed source tree:
  `397eca83b7740c5785d3b52db2dc2254bc0a8be8`;
- the exact 26-path `PROTECTED_PATHS` tuple at that source;
- the tracked Gate report path/schema/SHA-256 above;
- this tracked review path and its filesystem SHA-256;
- binary `ACCEPT` verdicts for GA-00 through GA-35.

The token validator must continue to prove reviewed-source ancestry, no
protected committed or uncommitted drift, canonical token bytes, and exact
report/review content hashes. This reviewer did not issue or edit a token.

