# ENG-GATEA-PROVENANCE-1 handoff

## Task

- **Task ID:** ENG-GATEA-PROVENANCE-1
- **Agent:** Research Software Engineer
- **Branch:** `agent/engineering/ENG-GATEA-PROVENANCE-1`
- **Starting commit:** `e5edf72bfe2920834cfcbb8f4fec53935e6b719f`
- **Ending commit:** commit containing this handoff; SHA reported to orchestrator
- **Status proposed:** REVIEW

## Objective

Add a deterministic, read-only, machine-readable evidence path for every
mandatory GA-00--GA-35 row. Every row/node must link to applicable semantic
graph hashes, root fixtures/values, dtype/device, absolute and relative
residuals, bounds and observed-versus-bound decisions, source/tree state,
Python/Torch environment, and pytest node status. Mathematically inapplicable
fields must be explicit typed `N/A` values with row-specific rationales. Gate A
must not self-accept.

## Summary

- Added an independent in-memory evidence runner which recomputes at least one
  genuine observable for every GA-00--GA-35 row. It covers the graph contract,
  root/phase geometry, exact fixture/root/depth matrix, reconstruction,
  weighted identities and counterexamples, finite approximation/frame bounds,
  expressivity/limitation witnesses, perturbation/locality/cost, and
  sensitivity/lifecycle boundaries.
- Added typed evidence values: every field is either `VALUE` with serialized
  finite data or `N/A` with a mandatory, row-specific rationale. Passing tests
  are never converted into fabricated zero residuals.
- Added deterministic schema validation for row omission, invalid realization
  tags, nonfinite/non-JSON values, empty evidence, missing roots, malformed
  graph hashes, duplicate metrics, unjustified `N/A`, and malformed
  observed-versus-bound decisions.
- Upgraded the coverage report to schema v2. Every collected pytest node now
  has its node ID, definition, phase/status, record properties, and a stable
  reference to its independently computed GA-row evidence. The report embeds
  tested source commit/tree state and Python/Torch/CUDA/platform identity.
- Strengthened the four reviewer-sensitive semantic rows in the independent
  path: GA-10 binds the public `GBDNTight` model/tuple/readout to an explicit
  residual-first assembly and permuted negative control; GA-14 records the
  finite-factor `epsilon_K/2` channel term; GA-25 reports both stable and
  deliberately ill-conditioned Product-sum matrices; GA-27 serializes the
  numerator-zero, unreduced-pole, cancellation, and reduced-pole multisets
  against the conditional Cayley imaginary-axis locus.
- Kept `gate_a_acceptance.accepted=false`. With tests executed, the only
  current report blocker is missing independent reviewer acceptance.
- No paper, results, legacy implementation, experiment, notebook, or research
  state file was touched.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `src/gbdn/gate_a_evidence.py` | Independent deterministic row evidence, schema validator, decision audit, field counts | Yes; canonical diagnostics only |
| `src/gbdn/gate_a_report.py` | Report v2 source/environment/node/evidence linkage | Yes; read-only reporter only |
| `tests/test_gate_a_provenance.py` | Schema, determinism, omission/tamper, linkage, stdout-only tests | Yes; bounded Gate-A tests only |
| `tests/test_gate_a_closeout.py` | Updated report-schema assertions and evidence checks | Yes; existing reporter tests only |
| `handoffs/ENG-GATEA-PROVENANCE-1.md` | Evidence and limitations | Yes |

## Scientific impact

- Claims enabled: none automatically. The implementation now exposes the
  numeric and semantic evidence needed for independent theorem-test review.
- Claims narrowed: pytest PASS counts alone are explicitly insufficient; each
  row is paired with recomputed observables and provenance.
- Claims rejected: none newly. Existing counterexample rows remain explicit.
- Paper sections affected: none in this task.

## Evidence

### Proofs

- theorem/lemma: no new theorem; evidence bindings implement the frozen
  `math/theorem_to_test_contract.md` observables.
- assumptions: CPU deterministic small-graph diagnostics; float64/complex128
  except GA-30/35 model paths; fixed roots/operators where required; exact and
  `chebyshev-K` tags remain separate.
- proof location: unchanged mathematical audit.
- counterexamples checked: noncommuting node projector, repeated-eigenvalue
  scalar limitation, carried-state annihilation, connected/disconnected and
  beyond-reach target sensitivity.

### Tests

```text
command: $env:PYTHONPATH='src'; py -3.14 -m pytest tests\test_gate_a_provenance.py tests\test_gate_a_closeout.py -q -p no:cacheprovider
result: 11 passed, 1 warning in 14.13s

command: $env:PYTHONPATH='src'; py -3.14 -m pytest tests -q -p no:cacheprovider
result: 454 passed, 3 warnings in 18.24s

command: $env:PYTHONPATH='src'; py -3.14 scripts\report_gate_a.py
result: exit 0; 36/36 evidence rows; 706 linked Gate-A pytest node/row records;
        703 VALUE fields, 59 justified N/A fields, 762 total typed fields;
        zero missing evidence rows, schema errors, or failed decisions;
        every mandatory ID executed and passing;
        gate_a_acceptance.accepted=false; independent review blocker retained
```

The pre-commit report correctly records the tree as dirty because it is testing
the uncommitted task patch. The orchestrator should rerun it after integration
to obtain the clean tested commit. Warnings are two upstream PyTorch/Python
3.14 JIT deprecations and one PyTorch sparse-invariant warning.

### Experiment artifacts

- run IDs: none
- result paths: none
- aggregate paths: none
- generated paper assets: none

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Every GA-00--GA-35 row has computed evidence | PASS | 36 rows, zero omissions |
| Every row has at least one genuine observable | PASS | Schema/provenance focused test |
| Applicable graph hashes are recorded | PASS | Canonical Laplacian or recorded input/output SHA-256 values |
| Root fixtures/values are recorded or justified N/A | PASS | Typed root context for every row |
| Dtype/device recorded | PASS | Typed row fields |
| Absolute/relative residuals recorded or justified N/A | PASS | Every metric schema-validated |
| Bounds/decisions recorded or justified N/A | PASS | Boolean decision validation and decision-failure audit |
| Source/tree and Python/Torch environment recorded | PASS | Report v2 top-level and evidence linkage |
| Every collected node links to evidence/status | PASS | 706 node/row records in executed report |
| Deterministic output and mutation isolation | PASS | Repeated byte-equivalent evidence, deep-copy mutation test |
| Omission/tamper failures detected | PASS | Missing row, bad hash, bad N/A, malformed/false decision tests |
| No Gate-A self-acceptance | PASS | `accepted=false`; reviewer blocker retained |
| Full tests | PASS | 454 passing |

## Known limitations

- The numeric evidence runner is independent of pytest assertion bodies but
  intentionally reuses canonical production/oracle/diagnostic APIs. It is not
  a second symbolic proof and requires independent reviewer adjudication.
- One row record may aggregate a fixture/depth/root matrix and is then linked
  to every pytest node carrying that GA ID. Per-node parameter values/statuses
  remain in the node ID and phase record; the shared row record stores maxima
  and case tables. This avoids recomputing 400+ diagnostics individually but
  should be checked against reviewer expectations.
- GA-24 geometry is descriptive, so residual/bound/decision fields for that
  descriptive metric are justified N/A; its certified-error metric remains
  numeric.
- GA-28's observed-to-bound ratio is descriptive because the actual theorem
  decision is separately recorded as zero bound violation.
- GA-35 records roots as N/A because its contract concerns parameter identity
  and optimizer membership, not numerical root values. GA-30 does serialize
  initialized model roots because cost/storage depends on the realized model.
- GA-10 covers the canonical model-to-readout path, but future run-artifact
  serializers must separately preserve the same residual-first convention.
- GA-14 uses a prescribed diagonal finite-factor perturbation so the
  `epsilon_K/2` coefficient is independently visible. GA-20--GA-22 remain the
  evidence for actual Chebyshev operator errors and finite frame behavior.
- GA-25 exposes a stable exact interpolation witness and a clustered,
  ill-conditioned exact boundary case. It does not establish finite-K
  optimization, trainability, or parameter efficiency.
- GA-27 records a one-factor reduced-pole witness and the exact conditional
  continuum scope. Independent literature review must still verify the frozen
  Cayley comparator family; the row cannot support a finite-spectrum or
  superiority claim.
- The reporter is stdout-only and therefore does not itself create an
  immutable submission artifact. Artifact persistence remains a later
  infrastructure gate.
- Source tree state is semantic provenance, not source-content archiving.
- GPU numerical evidence is not part of this CPU Gate-A suite; H100 jobs remain
  blocked until review.

## Reviewer questions

1. Does each independent evaluator measure the theorem premise/conclusion
   rather than merely duplicate the implementation under test?
2. Is row-level aggregation plus node linkage sufficient, or must every
   parameterized pytest node emit its own full numeric residual payload?
3. Are all 59 typed N/A fields mathematically justified, especially GA-24,
   GA-28, and GA-35?
4. Are semantic Laplacian hashes appropriate for valid graph fixtures and
   recorded ordered-input hashes appropriate for rejected directed inputs?
5. Does the finite-error evidence retain the exact-target versus polynomial
   realization boundary everywhere?

## Conflicts or decisions needed

Independent Reviewer sign-off is required before Gate A can be accepted. If
the reviewer requires parameterized-node-level rather than row-level numeric
records, extend the evidence runner with explicit case IDs; do not infer them
from pytest names or weaken the current schema.

## Reproduction instructions

From the repository root:

```powershell
$env:PYTHONPATH='src'
py -3.14 -m pytest tests\test_gate_a_provenance.py tests\test_gate_a_closeout.py -q -p no:cacheprovider
py -3.14 -m pytest tests -q -p no:cacheprovider
py -3.14 scripts\report_gate_a.py
```

Use `--collect-only` for node/evidence linkage without test execution. The
report remains JSON on stdout and makes no filesystem writes.

## Rollback

Revert the task commit. It removes only the evidence/reporter modules, bounded
tests, and handoff; no frozen artifact or manuscript is altered.
