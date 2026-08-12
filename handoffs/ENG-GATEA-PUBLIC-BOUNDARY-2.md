# ENG-GATEA-PUBLIC-BOUNDARY-2 handoff

## Task

- **Task ID:** ENG-GATEA-PUBLIC-BOUNDARY-2
- **Agent:** Research Software Engineer
- **Branch:** `agent/engineering/ENG-R3-ARTIFACT-1`
- **Starting commit:** `3692f524cf3061b34473d80d25bd33f8149f58ac`
- **Ending commit:** commit containing this handoff; SHA reported separately
- **Status proposed:** REVIEW

## Objective

Harden the exported exact Blaschke--Cayley operator boundary, replace the
invalid GA-13 prescribed-multiplier witness with an actual Blaschke channel,
and make Gate-A reporting fail closed under status or coverage-metadata drift.

## Summary

- Added one strict eigendecomposition validator for the public exact operator:
  real finite eigenvalues in `[0,2]`, a square finite orthonormal eigenbasis,
  precision/device agreement, admissible finite complex roots, and an explicit
  convention are required before operator assembly.
- Kept production exact arithmetic separate from the independent oracle
  arithmetic while sharing only validation. The frozen nonorthogonal witness
  with old defect `4.83269046506849` is now rejected.
- Hardened adjacent scalar/theorem-bearing helpers against nonfinite spectral
  values and inadmissible or ambiguous roots. The empty Blaschke product
  remains the mathematically valid identity throughout the public APIs.
- Replaced GA-13's arbitrary diagonal multiplier by
  `q=(1-B_R(phi(lambda)))/2` on a validated weighted graph. The evidence uses
  an admissible root, preserves a whole repeated eigenspace, checks all-pass
  structure, separation/leakage, the exact squared recovery identity, and its
  nontrivial bound. The operator comparison is deliberately named
  `manual_operator_assembly_relative_residual`, not independent.
- Restricted every per-ID reporter `status` to `PASS`, `FAIL`, or `NOT_RUN`.
  Duplicate/missing test mappings remain informational in `mapping_status`.
- Cross-validated frozen fixture, root, depth, and degree declarations against
  computed typed evidence. Missing, undeclared, or tampered scope becomes an
  explicit acceptance blocker.
- Reframed the historical `tests/test_gate_a.py` as a diagnostic subset; its
  direct-execution message cannot claim global Gate-A acceptance.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `src/gbdn/oracle.py` | Strict shared exact-eigendecomposition/root validation | Yes; canonical source only |
| `src/gbdn/spectral.py` | Fail-closed public exact/scalar contracts with separate production arithmetic | Yes; canonical source only |
| `src/gbdn/gate_a_evidence.py` | Public-boundary counterexample and substantive GA-13 computed evidence | Yes; canonical evidence only |
| `src/gbdn/gate_a_report.py` | v3 status contract and evidence-derived coverage cross-validation | Yes; read-only reporter only |
| `src/gbdn/__init__.py` | Export validated public boundary | Yes |
| `tests/test_gate_a_public_boundary.py` | Exact API adversarial and identity regressions | Yes |
| `tests/test_gate_a_exact_slice.py` | Actual-Blaschke GA-13 theorem/bound regression | Yes |
| `tests/test_gate_a_closeout.py` | v3 mapping/status contract regressions | Yes |
| `tests/test_gate_a_provenance.py` | Coverage drift/tamper and explicit blocker regressions | Yes |
| `tests/test_gate_a.py` | Diagnostic-only labeling and non-acceptance output | Yes |
| `handoffs/ENG-GATEA-PUBLIC-BOUNDARY-2.md` | This handoff | Yes |

## Scientific impact

- **Claims enabled:** the canonical exported exact operator now enforces the
  mathematical premises under which its unitary/all-pass statement is valid;
  GA-13 now exercises an actual Blaschke-derived channel.
- **Claims narrowed:** a passing historical subset or duplicated pytest ID is
  not Gate-A acceptance; static coverage claims must match computed evidence.
- **Claims rejected:** arbitrary nonorthogonal eigensystem assembly and an
  arbitrary prescribed multiplier cannot support the exact operator or GA-13
  theorem, respectively.
- **Paper sections affected:** none edited. Any future exact-operator or
  spectral-selection statement should cite the validated premises above.

## Evidence

### Counterexamples checked

- Frozen public-boundary witness: eigenvalues `[0,1]`, basis
  `[[1,1],[0,1]]`, root `0.2+0.1j`; the former unchecked assembly has
  `||T* T-I||_op = 4.83269046506849`, and the public API now rejects it.
- Out-of-range spectra, nonfinite inputs, invalid shapes/dtypes/devices,
  nonorthogonal bases, and roots on/outside the unit disk are rejected.
- The former GA-13 arbitrary target has premise defects about `0.072159` and
  `0.037703`; it is retained only as a negative control.

### Tests

```text
$env:PYTHONPATH='src'
py -3.14 -m pytest tests/test_gate_a_public_boundary.py tests/test_gate_a_exact_slice.py tests/test_gate_a_closeout.py tests/test_gate_a_provenance.py tests/test_gate_a.py -q -p no:cacheprovider
127 passed, 3 warnings in 24.15s

py -3.14 -m pytest tests -q -p no:cacheprovider
558 passed, 3 warnings in 30.04s

py -3.14 scripts/report_gate_a.py --collect-only
schema v3; 811 VALUE fields; 59 typed N/A fields; 0 evidence-schema errors;
0 evidence-decision failures; coverage cross-validation PASS; 36 NOT_RUN rows;
Gate-A accepted=false
```

Warnings are two upstream PyTorch/Python 3.14 JIT deprecations and the existing
PyTorch sparse-invariant warning.

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Invalid exact public inputs fail closed | PASS | Frozen witness and adversarial public-boundary tests |
| Valid exact API retains both conventions/dtypes and identity product | PASS | Public-boundary parameterized tests |
| Production and oracle arithmetic are not delegated to one implementation | PASS | Shared validator; separate production/oracle symbol and assembly paths |
| GA-13 uses a genuine admissible Blaschke factor | PASS | Exact-slice test and typed GA-13 evidence |
| Reporter status enum is unambiguous | PASS | Closeout/provenance schema tests |
| Static coverage metadata cannot drift silently | PASS | Fixture/root/degree drift and acceptance-blocking tamper tests |
| Gate A independently accepted | FAIL | Reporter deliberately remains blocked pending re-review |

## Known limitations

1. Validation of a supplied dense eigendecomposition costs dense orthogonality
   checks; it belongs to the exact/oracle boundary, not sparse production
   forwards.
2. Scalar analytic functions still accept real spectral values outside
   `[0,2]` where mathematically meaningful. The graph-operator constructor is
   the boundary that enforces normalized-Laplacian support.
3. Strict root dtype/device agreement may reject callers that previously
   relied on implicit conversion; this is intentional fail-closed behavior.
4. Computed coverage evidence and pytest execution are linked by GA ID, not by
   claiming that each pytest node independently emitted every evidence field.
5. Gate A remains blocked until an independent reviewer inspects these repairs
   and records acceptance; this implementation does not self-accept the gate.

## Reviewer questions

1. Does the shared-validation/separate-arithmetic design preserve sufficient
   oracle independence for all exact-operator acceptance evidence?
2. Are the GA-13 set definition, whole-eigenspace handling, and recovery bound
   the strongest valid theorem contract rather than a merely convenient case?
3. Does exact equality between frozen coverage declarations and typed evidence
   appropriately fail closed without overstating pytest-node granularity?
4. Are any other exported helpers theorem-bearing enough to require the full
   graph-spectrum `[0,2]` restriction rather than scalar real-line semantics?

## Conflicts or decisions needed

No source-ownership conflict. The orchestrator should request an independent
Gate-A re-review before changing the gate status.

## Reproduction instructions

Run the focused and full commands above, then run
`py -3.14 scripts/report_gate_a.py` from the clean integrated commit. Confirm
all test rows are `PASS`, coverage cross-validation is `PASS`, evidence schema
and decision failures are empty, and acceptance remains blocked only by the
independent-review policy (plus any genuine source-state blocker).

## Rollback

Revert the task commit. No manuscript, results, notebook, legacy source,
execution board, experiment artifact, or user-owned dirty file is modified.
