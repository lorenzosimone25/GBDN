# ENG-GATEA-CLOSEOUT-1 handoff

## Task

- **Task ID:** ENG-GATEA-CLOSEOUT-1
- **Agent:** Research Software Engineer
- **Branch:** `agent/engineering/ENG-GATEA-CLOSEOUT-1`
- **Starting commit:** `c0f58b52cf24bba2d867ecff03eb8f710f1c3997`
- **Ending commit:** commit containing this handoff; SHA reported to orchestrator
- **Status proposed:** REVIEW

## Objective

Close GA-23 with an exact center/width contract test and add a read-only,
deterministic, machine-readable coverage report for GA-00--GA-35. The report
must distinguish regression execution from scientific Gate-A acceptance and
must expose fixture-matrix gaps rather than infer coverage from test names.

## Summary

- Added the GA-23 exact center/width test. It verifies the phase-derivative
  peak at `mu`, both half-width-at-half-maximum points at `mu +/- gamma`, the
  mapped pole, and an admissible Bernstein ellipse strictly inside the nearest
  pole ellipse.
- Froze the angular-anchor counterexample `mu=1, rho=0.5`: its mapped
  frequency center is `0.8`, not `1.0`.
- Added a read-only pytest collector/reporter which maps all mandatory IDs to
  source definitions and collected node IDs, optionally executes the suite,
  and emits deterministic JSON to stdout. It records the tested commit and
  dirty-state hash, realization/depth/degree/root declarations, execution and
  duplicate-mapping status, numerical tolerances, and reported residuals.
- Kept `gate_a_acceptance.accepted=false` independently of ID execution. On
  this branch all 36 IDs execute and pass, but the report remains blocked by
  incomplete fixture/depth, row-specific degree/fixture, root applicability,
  per-test provenance, and independent-review evidence.
- Cherry-picked the orchestrator's validated-operator integration fix
  (`bd444c7`, represented as `3344450` on this branch) before verification.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `src/gbdn/gate_a_report.py` | Deterministic read-only Gate-A collector and JSON report | Yes; canonical diagnostics only |
| `scripts/report_gate_a.py` | Thin stdout-only report entry point | Yes; no artifact or result writes |
| `tests/test_gate_a_closeout.py` | GA-23 and reporter regression tests | Yes; bounded Gate-A tests only |
| `handoffs/ENG-GATEA-CLOSEOUT-1.md` | Engineering evidence and limitations | Yes |

## Scientific impact

- Claims enabled: exact center/width semantics now have a direct analytic
  regression test and machine-readable residual evidence.
- Claims narrowed: a complete set of passing GA IDs is explicitly not treated
  as Gate-A acceptance.
- Claims rejected: the frozen angular-root parameterization does not place the
  phase center at its angular anchor (`1.0` maps to center `0.8` at radius
  `0.5`).
- Paper sections affected: none in this task; paper editing remains blocked on
  Gate-A review and complete evidence.

## Evidence

### Proofs

- theorem/lemma: T-E center/width diagnostic contract (GA-23).
- assumptions: one admissible exact center/width root; real scalar spectral
  variable; forward convention; nearest mapped pole outside `[0,2]`.
- proof location: analytic identities are encoded in
  `tests/test_gate_a_closeout.py`; no manuscript proof was edited.
- counterexamples checked: frozen angular anchor `mu=1, rho=0.5`.

### Tests

```text
command: $env:PYTHONPATH='src'; py -3.14 -m pytest tests\test_gate_a_closeout.py -q -p no:cacheprovider
result: 4 passed in 5.31s

command: $env:PYTHONPATH='src'; py -3.14 -m pytest tests -q -p no:cacheprovider
result: 144 passed, 3 warnings in 11.17s

command: $env:PYTHONPATH='src'; py -3.14 scripts\report_gate_a.py
result: exit 0; GA-00--GA-35 executed and passing; GA-23 residual present;
        gate_a_acceptance.status=BLOCKED and accepted=false
```

The warnings are two upstream PyTorch/Python-3.14 JIT deprecations and one
PyTorch sparse-invariant warning; none is introduced by this patch.

### Experiment artifacts

- run IDs: none
- result paths: none
- aggregate paths: none
- generated paper assets: none

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| GA-23 peak at `mu` and HWHM `gamma` | PASS | Analytic three-point derivative check within `5e-12` |
| GA-23 mapped pole and ellipse relation | PASS | Pole residual within `5e-12`; `1 < rho < chi_pole` |
| Frozen angular-anchor counterexample | PASS | Center `0.8` and grid peak `0.8` |
| Map GA-00--GA-35 to pytest nodes | PASS | Reporter collects every mandatory ID |
| Emit deterministic machine-readable JSON | PASS | Two collect-only subprocess reports are byte-identical |
| Separate execution from Gate-A acceptance | PASS | All IDs can pass while acceptance remains explicitly blocked |
| Full regression suite | PASS | 144 tests pass |

## Known limitations

- This branch predates the orchestrator's deterministic fixture-completion
  commits `d35abe8` and `8237cfe`. Their evidence is intentionally not claimed;
  report declarations must be reconciled only after integration.
- On this bounded branch the exact multilevel sweep lacks a second path size,
  an even cycle, rectangular grid, star, and deterministic random positive
  nonuniform weighted graph.
- GA-03/04 do not span the required fixture matrix; GA-05 does not evaluate
  every required graph spectrum; GA-19 has degrees 4 and 8 but not 16, 32, or
  the declared high-order case.
- The applicable-row root matrix is incomplete. In particular,
  conjugate-symmetric roots are absent and real-interior/near-cap coverage is
  not established across every applicable row.
- Only GA-23 currently emits the new machine-readable residual payload. The
  contract still requires graph hashes, roots/parameterizations, dtype/device,
  absolute and relative residuals, predicted bounds, observed quantities,
  source commit, and test name for every mandatory row.
- The reporter records duplicate definitions separately from execution
  failures; duplicates do not by themselves establish or invalidate a
  theorem.
- Independent reviewer acceptance is outside this utility and remains
  mandatory.

## Reviewer questions

1. Does the GA-23 ellipse check use the correct shifted Laplacian coordinate
   and establish exactly the intended analyticity relation?
2. Are the explicit fixture/root/degree declarations conservative after
   merging `d35abe8` and `8237cfe`?
3. Should duplicate mappings remain informational, or should selected IDs be
   required to have one canonical source definition?
4. Which exact rows require each root fixture before
   `applicable-row-matrix-not-enumerated` can be cleared?

## Conflicts or decisions needed

No code conflict is known. The orchestrator must merge the post-base fixture
commits before updating any declaration from incomplete to complete. Gate A
must remain blocked until the integrated report, complete per-test provenance,
and independent review agree.

## Reproduction instructions

From the repository root with Python 3.14 dependencies installed:

```powershell
$env:PYTHONPATH='src'
py -3.14 -m pytest tests\test_gate_a_closeout.py -q -p no:cacheprovider
py -3.14 -m pytest tests -q -p no:cacheprovider
py -3.14 scripts\report_gate_a.py
```

Use `--collect-only` to inspect mappings without executing tests. Both modes
write only JSON to stdout and do not mutate results or paper artifacts.

## Rollback

Revert the task commit reported to the orchestrator. This removes only the
report utility, entry point, closeout tests, and this handoff; frozen artifacts
and scientific implementations are unaffected.
