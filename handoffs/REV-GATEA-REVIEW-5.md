# REV-GATEA-REVIEW-5 handoff

## Task

- **Task ID:** REV-GATEA-REVIEW-5
- **Agent:** Independent adversarial A* reviewer
- **Branch:** `agent/reviewer/REV-GATEA-REVIEW-5`
- **Starting reviewed commit:** `a8be64da25de060f7e7d634d45362827fded147c`
- **Ending commit:** commit containing this handoff; SHA reported separately
- **Status proposed:** ACCEPTED

## Objective

Independently adjudicate the two rejected Gate-A package boundaries after
`ENG-GATEA-BOUNDARY-REPAIR-2`, reproduce the frozen and extended adversarial
witnesses through public/canonical aliases, rerun Gate and full suites plus the
clean reporter, and issue a binary decision without changing implementation,
tests, paper, results, state, board, notebook, or acceptance token.

## Decision

**Gate A is ACCEPTED under the frozen scientific contract at reviewed commit
`a8be64da25de060f7e7d634d45362827fded147c`.** GA-00 and GA-27 are repaired
and accepted. The other 34 previously accepted rows remain intact within their
narrow scopes.

This is an independent review artifact, not an acceptance token. It does not
by itself authorize H100 work or any empirical/superiority claim.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `reviews/gate_a_fifth_independent_review.md` | Binary verdict, adversarial evidence, all-row adjudication, claim boundary | Yes; reviewer-owned |
| `handoffs/REV-GATEA-REVIEW-5.md` | This integration and reproduction handoff | Yes; reviewer-owned |

No source, test, paper, result, plan, state, board, notebook, or acceptance
token was changed.

## Evidence

### Independent boundary probes

- Dense public copies from `tensor`, `to_dense`, and root/module compatibility
  unwraps remained isolated under NumPy, `.data`, detached-view, and direct
  storage mutations.
- Sparse public copies from normalized, core, and recorded-preprocessor token
  builders remained isolated under value/index/dense-copy mutation.
- Version-invisible NumPy, `.data`, and direct-storage mutation of private
  stored tensors failed content-hash validation before basis, model, and peel
  consumers. Versioned view mutation also failed closed.
- Root and module exact diagnostic aliases rejected the former GBDN `100.0`
  and CayleyNet `0.3` tolerance overrides, nine alternate keyword spellings,
  and positional extras.
- The GBDN zero--pole distance remained `2.895653538364977` with zero
  cancellations and one reduced pole; the frozen Cayley comparator retained
  effective order three and two multiplicity-three pole loci.

### Tests and reporter

```text
Gate-A selection:       513 passed, 3 warnings in 33.28 s
Full repository suite:  684 passed, 2 skipped, 145 warnings in 76.90 s
Clean reporter:         479 nodes; 36 PASS / 0 FAIL / 0 NOT_RUN
Mappings:               18 UNIQUE / 18 DUPLICATE / 0 MISSING
Typed fields:           841 VALUE / 59 N/A / 900 total
Evidence validation:    0 schema errors / 0 decision failures
Coverage validation:    PASS / 0 mismatches
Provenance links:       0 errors
Reporter blocker:       independent review only
```

The warnings and skips are the documented upstream Python 3.14/PyTorch/PyG
warnings and Windows symlink-privilege skips; none affects the decision.

## Scientific impact

- **Claims enabled after proper token recording:** the frozen Gate-A exact
  algebra, conditioning/reconstruction, finite-frame, fixed-root perturbation,
  and locality/cost statements.
- **Claims not enabled:** practical anti-oversmoothing, oversquashing
  mitigation, approximation efficiency, optimization advantage, predictive or
  benchmark superiority, and long-range reasoning.
- **Downstream authorization:** none beyond mathematical Gate closure. All
  experiment, protocol, baseline, artifact, evaluator, scheduler, leakage, and
  run-plan gates remain independently binding.

## Acceptance-token requirement

The reviewed commit includes the corrected `PROTECTED_PATHS` coverage for all
`test_gate_a*.py` modules and `test_gate_acceptance.py`. The orchestrator may
record this review through the acceptance-token mechanism, but the token must
bind exact reviewed source/report/review hashes and the corrected protected
set. This reviewer did not issue a token.

## Reproduction

From a clean worktree at `a8be64d`:

```powershell
$env:PYTHONPATH=(Resolve-Path -LiteralPath src).Path
$gateFiles=(Get-ChildItem -LiteralPath tests -Filter 'test_gate_a*.py' |
  Sort-Object Name | ForEach-Object {$_.FullName})
python -m pytest @gateFiles -q -p no:cacheprovider
python -m pytest tests -q -p no:cacheprovider
python scripts/report_gate_a.py
```

See `reviews/gate_a_fifth_independent_review.md` for the independent public
alias, private storage-tamper, canonical-consumer, and tolerance-alias probes.

## Integration

Cherry-pick the single reviewer commit reported by this task. The commit adds
only the review and handoff. Do not reinterpret the review as a token or as
permission to bypass any remaining stop-line condition.

## Rollback

Revert the single reviewer commit. No implementation, test, result, paper,
state, board, notebook, or frozen artifact requires rollback.

