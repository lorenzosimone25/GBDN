# REV-GATEA-PORTABILITY-1 handoff

## Task

- **Task ID:** REV-GATEA-PORTABILITY-1
- **Agent:** Independent adversarial Gate-A reviewer
- **Branch:** `agent/reviewer/REV-GATEA-PORTABILITY`
- **Reviewed source:** `af20dd07374ef26a44f47874e8f5946eea24ccec`
- **Reviewed tree:** `11cfce0cb26e7fea7133888af949f3243d635304`
- **Status proposed:** ACCEPTED

## Decision

**ACCEPT.** Hashing authoritative tracked Git blobs fixes CRLF checkout
portability without weakening meaningful tamper rejection. The final repair
also restores resource safety by checking tracked blob size before any body
materialization. The rejected intermediate unbounded implementation is not
the reviewed source.

This review is not a Gate token and does not authorize H100 execution.

## Files changed

| File | Change |
|---|---|
| `reviews/gate_a_portability_independent_review.md` | Binary verdict, portability/tamper/size-bound audit, token bindings |
| `handoffs/REV-GATEA-PORTABILITY-1.md` | Integration and reproduction handoff |

No source, test, token, report, result, paper, notebook, plan, or experiment
was changed by the reviewer.

## Evidence

```text
Focused acceptance suite: 11 passed
Complete Gate selection:   516 passed
CRLF checkout conversion:  accepted as tracked-content equivalent
Semantic worktree tamper:  rejected
Committed blob tamper:     rejected
Oversized report blob:     rejected before body read
Exact size limit:          accepted
```

Clean tracked report:

```text
commit:  db9aefaa7a87ea936565758828f22f54d1ee0f25
path:    results_submission/reports/gate_a_report.json
SHA-256: be37db82b661852ab13277da7f79402b041f76bde7d07f87b3e7043a713b1fcc
source:  af20dd07374ef26a44f47874e8f5946eea24ccec
result:  479 nodes; GA-00..GA-35 PASS; zero evidence/provenance errors
```

## Reproduction

From a clean worktree at the reviewed source:

```powershell
$env:PYTHONPATH=(Resolve-Path -LiteralPath src).Path
python -m pytest tests/test_gate_acceptance.py -q -p no:cacheprovider
$gateFiles=@(Get-ChildItem -LiteralPath tests -Filter 'test_gate_a*.py' |
  Sort-Object Name | ForEach-Object {$_.FullName})
$gateFiles += (Resolve-Path -LiteralPath tests/test_gate_acceptance.py).Path
$gateFiles=$gateFiles | Sort-Object -Unique
python -m pytest @gateFiles -q -p no:cacheprovider
```

See the review artifact for the independent CRLF, worktree/committed tamper,
pre-materialization size, and exact-limit probes.

## Integration

Cherry-pick the single reviewer commit reported separately. Compute the
tracked Git blob SHA-256 of the review after integration; the refreshed token
must bind that exact hash, the reviewed source/tree, the protected-path tuple,
and the clean report blob hash. Do not bind this review commit as the reviewed
scientific source.

## Rollback

Revert the reviewer commit. No implementation or frozen artifact is affected.

