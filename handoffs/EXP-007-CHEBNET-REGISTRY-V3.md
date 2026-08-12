# ChebNet registry-v3 implementation/configuration handoff

## Task

- **Task ID:** EXP-007-CHEBNET-REGISTRY-V3
- **Agent:** Baseline schema specialist
- **Branch:** `agent/engineering/BASELINE-SCHEMA-V3`
- **Starting commit:** `5a166957095f551949d863bd6bd1a5513782a80f`
- **Ending commit:** task commit containing this handoff
- **Status proposed:** REVIEW

## Objective

Separate implementation/operator parity from benchmark-configuration
provenance, truthfully register the licensed PyG ChebNet composition as
implementation-verified, and keep confirmatory admission fail-closed until an
equal-budget validation search has produced a frozen final configuration.

## Summary

Registry v3 has two independent gates. `IMPLEMENTATION_VERIFIED` means the
licensed wrapper, independent oracle, operator-composition checks, official
task heads, and resource counts are hash-bound. `CONFIRMATORY_READY` additionally
requires a hash-bound five-dataset final method configuration and selection
evidence whose trial count equals the confirmatory plan budget and whose
selection partition is validation-only.

The ChebNet record uses `LOCAL_EQUAL_BUDGET_VALIDATION_SEARCH`. It does not
claim that PyG or the ChebNet authors published this two-layer heterophily
architecture, search space, or final configuration. The search space is frozen
and prespecified, but no tuning result or final configuration was created.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `src/gbdn/baseline_contract.py` | Registry-v3 screening/confirmatory contracts | Yes |
| `tests/test_baseline_contract.py` | Migration and adversarial admission tests | Yes |
| `tests/test_run_plan.py` | Registry-v3 final-config fixtures | Yes |
| `configs/submission/search_spaces/ChebNet.json` | Local prespecified candidate space | Yes |
| `results_submission/baseline_registry.json` | Screening-only ChebNet record | Yes |
| `results_submission/reports/chebnet_operator_parity.json` | Test-source-bound compact parity record | Yes |
| `docs/baselines/chebnet_pyg_provenance.md` | Correct implementation/configuration claim boundary | Yes |
| `.gitignore` | Allow only the compact baseline registry at submission root | Yes |

## Scientific impact

- Claims enabled: the PyG ChebNet operator composition is implementation
  verified on the recorded deterministic fixtures.
- Claims narrowed: configuration choices are local validation-search choices,
  not upstream reference settings.
- Claims rejected: full-model upstream reproduction; benchmark-performance
  parity; confirmatory readiness before tuning.
- Paper sections affected: none before confirmatory execution and review.

## Evidence

### Tests

```text
PYTHONPATH=src python -m pytest -q \
  tests/test_baseline_contract.py tests/test_run_plan.py \
  tests/test_chebnet_baseline.py tests/test_heterophily_worker.py
64 passed
```

```text
PYTHONPATH=src python -m pytest -q tests
748 passed, 2 skipped
```

The compact operator evidence also binds the SHA-256 of
`tests/test_chebnet_baseline.py`, the wrapper, independent oracle, PyG source
commit, and preserved license notice.

### Experiment artifacts

- run IDs: none;
- tuning results: none;
- final configuration: none;
- H100 execution: none.

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Implementation and configuration provenance are separate | PASS | Registry-v3 schema/tests |
| Local configuration is not called upstream | PASS | ChebNet record/provenance |
| Search space and official selection metrics are frozen | PASS | Search-space hash and task bindings |
| Screening candidate cannot enter confirmatory plan | PASS | Adversarial plan-binding test |
| Final config must be selected validation-only at equal budget | PASS | Selection-evidence validator/tests |
| Full five-dataset tuning completed | FAIL / NOT RUN | Intentional downstream blocker |

## Known limitations

- The prespecified Cartesian candidate set is larger than the eventual trial
  budget; the future tuning scheduler must define and freeze its deterministic
  candidate-sampling rule before execution.
- Operator parity is not benchmark-accuracy parity.
- The current registry contains only ChebNet. It is a screening registry, not
  the frozen primary comparator set.
- No final method configuration or selection manifest exists.

## Reviewer questions

1. Is `OPERATOR_COMPOSITION` narrow enough to prevent performance-reproduction
   laundering?
2. Does the screening/confirmatory split fail closed under missing or tampered
   final-configuration evidence?
3. Must the future selection evidence additionally bind every tuning run ID
   before `CONFIRMATORY_READY` is issued?

## Conflicts or decisions needed

The orchestrator must freeze one equal integer trial budget and a deterministic
candidate-sampling policy shared across methods. ChebNet must remain excluded
from confirmatory run plans until tuning artifacts and an independent review
support promotion to `CONFIRMATORY_READY`.

## Reproduction instructions

Run the test command above from a clean checkout. To inspect the present
screening record, call `validate_baseline_registry(..., admission="screening")`.
The default confirmatory call is expected to fail.

## Rollback

Revert the single bounded task commit. No raw, legacy, tuning, or benchmark
artifact is modified.
