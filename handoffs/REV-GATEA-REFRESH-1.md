# REV-GATEA-REFRESH-1 handoff

## Task

- **Task ID:** REV-GATEA-REFRESH-1
- **Agent:** Independent adversarial Gate-A reviewer
- **Branch:** `agent/reviewer/REV-GATEA-REFRESH`
- **Reviewed source:** `82a83c0390e5850617321bae5efb8491eb9692c6`
- **Reviewed tree:** `397eca83b7740c5785d3b52db2dc2254bc0a8be8`
- **Status proposed:** ACCEPTED

## Decision

**ACCEPT.** The corrected Gate-A protected surface is scientifically scoped,
complete under import-time internal dependencies, and passes all mandatory
rows. Removing the operations-only launcher is safe because canonical
claim-bearing consumers directly enforce Gate acceptance and the launcher is
separately operations-protected. Adding `__init__.py`, `artifacts.py`,
`provenance.py`, and `seed.py` closes the true public/validation runtime
surface.

This decision does not issue a token and does not authorize H100 work.

## Files changed

| File | Change |
|---|---|
| `reviews/gate_a_refresh_independent_review.md` | Binary decision, closure audit, execution evidence, claim boundary, token bindings |
| `handoffs/REV-GATEA-REFRESH-1.md` | Integration and reproduction handoff |

No implementation, test, token, report, result, plan, board, paper, notebook,
or experiment was changed by the reviewer.

## Evidence summary

```text
Gate selection: 514 passed, 3 warnings
Gate reporter:  479 nodes; GA-00..GA-35 PASS
Mappings:       18 UNIQUE / 18 DUPLICATE / 0 MISSING
Evidence:       0 schema errors / 0 failed decisions
Cross-check:    PASS / 0 mismatches
Provenance:     0 errors
Full suite:     767 passed / 2 skipped / 1 expected stale-token failure
```

Tracked report at `53c8c4619a6420abfb302107a49bdb8b8556b6dc`:

```text
results_submission/reports/gate_a_report.json
SHA-256 311896b32b2470a74d43e05b583b8b9364a9755cfcbe5bfa172c1163e39073c8
```

The sole full-suite failure correctly observes that the old token is stale
against the corrected protected set. It should pass only after a new token is
created from this independent review and the exact bindings listed in the
review artifact.

## Reproduction

From a clean worktree at the reviewed source:

```powershell
$env:PYTHONPATH=(Resolve-Path -LiteralPath src).Path
$gateFiles=@(Get-ChildItem -LiteralPath tests -Filter 'test_gate_a*.py' |
  Sort-Object Name | ForEach-Object {$_.FullName})
$gateFiles += (Resolve-Path -LiteralPath tests/test_gate_acceptance.py).Path
$gateFiles=$gateFiles | Sort-Object -Unique
python -m pytest @gateFiles -q -p no:cacheprovider
python scripts/report_gate_a.py
python -m pytest tests -q -p no:cacheprovider
```

## Integration

Cherry-pick the single reviewer commit reported separately. After integration,
compute the filesystem SHA-256 of
`reviews/gate_a_refresh_independent_review.md`; a refreshed token must bind
that exact hash plus the reviewed source/tree and tracked report hash. Do not
bind the review commit as the reviewed mathematical source.

## Rollback

Revert the single reviewer commit. No source, result, or frozen artifact is
affected.

