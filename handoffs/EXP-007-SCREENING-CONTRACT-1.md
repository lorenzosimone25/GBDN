# Validation-screening contract handoff

## Task

- **Task ID:** EXP-007-SCREENING-CONTRACT-1
- **Agent:** Screening-contract specialist
- **Branch:** `agent/screening-contract`
- **Starting commit:** `59d97b4fd915798a8de0d889ae6ddd8e2d6b074d`
- **Ending commit:** task commit containing this handoff
- **Status proposed:** REVIEW

## Objective

Define the smallest CPU-only deterministic contract for equal-budget,
validation-only candidate screening across ChebNet and future canonical GBDN
method spaces, without running experiments or choosing final configurations.

## Summary

Added a pure contract module that validates compact search spaces, enumerates
typed Cartesian candidates, selects an equal-budget deterministic subset by
SHA-256 ranking, reconstructs canonical manifests from their bound source
files, and selects complete validation-only evidence with a stable hash tie
rule. The screening manifest freezes validation units as well as seed and
budget. Selection decisions bind all candidate-observation hashes, preventing
the winning record from being presented without the losing candidates that
establish fair selection.

No budget or plan artifact was frozen. The accompanying design note proposes
12 candidates on three split/seed validation units per method--dataset, subject
to Stage-3 runtime measurement and independent fairness review.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `src/gbdn/screening_contract.py` | Pure schedule/manifest/selection contract | Yes |
| `tests/test_screening_contract.py` | Determinism and adversarial fail-closed tests | Yes |
| `docs/experiments/validation_screening_contract.md` | Scientific boundary and non-frozen budget proposal | Yes |
| `handoffs/EXP-007-SCREENING-CONTRACT-1.md` | Review handoff | Yes |

## Scientific impact

- Claims enabled: none; infrastructure only.
- Claims narrowed: a search space alone is not selection provenance, and a
  selected candidate alone does not establish an equal-budget search.
- Claims rejected: test-informed tuning, best-run reporting, silent unequal
  budgets, PRNG-dependent candidate subsets, or confirmatory readiness before
  final configuration review.
- Paper sections affected: none before actual reviewed screening artifacts.

## Evidence

### Proofs

- The subset is a deterministic function of canonical candidate identity,
  method, dataset, source hash, seed, and policy version.
- Candidate uniqueness and without-replacement selection are checked at run
  time; exact ties are resolved by candidate SHA-256.
- Counterexamples checked: injected test field, wrong official metric, changed
  validation units, partial observations, altered manifest trial, altered
  search source, noncanonical JSON, duplicate values, invalid paths, Boolean
  integer fields, and excessive/unequal budgets.

### Tests

```text
PYTHONPATH=src python -m pytest -q tests/test_screening_contract.py
12 passed
```

```text
PYTHONPATH=src python -m pytest -q tests
778 passed, 2 skipped, 1 expected integration failure
```

The sole full-suite failure is
`test_current_repository_verifier_is_read_only_and_blocked`: the independent
Gate-A token correctly rejects an uncommitted canonical source-tree change.
The focused scientific/software suites pass. The orchestrator must integrate
this commit into its separately owned narrowed Gate/operations review surfaces
and reissue acceptance before expecting that repository-state test to pass.

### Experiment artifacts

- run IDs: none;
- result paths: none;
- aggregate paths: none;
- generated paper assets: none.

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Candidate enumeration is deterministic and typed | PASS | Unit/adversarial tests |
| Candidate subset is seed/source/dataset bound | PASS | Repeated and changed-seed schedules |
| Budget is one equal exact integer | PASS | Constructor checks/tests |
| Validation units are prespecified and equal | PASS | Manifest field and observation checks |
| Test evidence cannot enter selection schema | PASS | Exact-key and attestation tests |
| Manifest detects source/trial tampering | PASS | Reconstruction tests |
| Specific H100 budget frozen | NOT RUN / INTENTIONAL | Runtime evidence is unavailable |
| Final configurations selected | NOT RUN / INTENTIONAL | No experiments authorized |

## Known limitations

- Only ChebNet currently has a repository search space. Future GBDN spaces must
  be complete and independently audited for fair ranges.
- This module defines the evidence contract but does not launch training or
  physically isolate test files; the execution layer must use the worker's
  selection-only process.
- Validation observation records are not yet immutable run bundles. The future
  execution layer must bind observation values to run/checkpoint identities.
- The proposed 12-trial/three-unit policy is not frozen and must not be cited as
  completed tuning.

## Reviewer questions

1. Are SHA-256-ranked subsets an acceptable prespecified approximation when
   Cartesian spaces exceed the common budget?
2. Are the candidate ranges across methods comparable enough to call the
   integer trial budget equal opportunity rather than merely equal count?
3. Should the final frozen validation units use more splits or seeds after the
   Stage-3 runtime measurement?
4. Must selection evidence bind per-epoch histories in addition to immutable
   validation run/checkpoint IDs?

## Conflicts or decisions needed

The orchestrator must choose the final budget and validation units after
runtime measurement, and must reject or revise method search spaces that make
an equal trial count scientifically unfair. No confirmatory plan or registry
promotion may precede that decision and an independent review.

## Reproduction instructions

```powershell
$env:PYTHONPATH=(Resolve-Path -LiteralPath src).Path
python -m pytest -q tests/test_screening_contract.py
```

## Rollback

Revert the single bounded task commit. No experiment, result, data, manuscript,
notebook, setup, Gate, operations-acceptance, or legacy file was changed.
