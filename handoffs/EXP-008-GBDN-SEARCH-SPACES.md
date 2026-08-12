# GBDN-family prespecified search-space handoff

## Task

- **Task ID:** EXP-008-GBDN-SEARCH-SPACES
- **Agent:** Search-space audit specialist
- **Branch:** `agent/engineering/GBDN-SEARCH-SPACES`
- **Starting commit:** `715ebd4cfc02f60a54e459749a9f96ab9988262b`
- **Ending commit:** task commit containing this handoff
- **Status proposed:** REVIEW

## Objective

Audit and, only if scientifically defensible, add CPU-only prespecified search
spaces for Tight GBDN, Product-sum GBDN, and GBDN+ that are executable by the
canonical heterophily worker and comparable with the existing ChebNet space.
Do not train, access data, freeze screening execution decisions, or create
claim-bearing evidence.

## Summary

The candidate spaces are supportable under a narrow resource-alignment claim.
All four methods use the same widths, optimizer family and constants, learning
rate and weight-decay grids, deterministic FP32 execution, epoch/patience
limits, and validation-only checkpoint selection. Their polynomial settings
map to the same canonical feature-matrix SpMV tiers `{2,6,10}` despite the
different meanings of `K` in ChebNet and GBDN.

Tight GBDN and Product-sum fix two sequential levels/factors, one root per
factor, `r_max=0.95`, and the forward convention. GBDN+ fixes two parallel
branches with one shared Chebyshev basis. Dropout is tuned only in GBDN+ and
ChebNet because the canonical Tight and Product-sum models do not expose it.

This is not a parameter-matched comparison. It does not choose the screening
seed, equal trial budget, validation units, final configurations, or execution
manifest.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `configs/submission/search_spaces/TightGBDN.json` | 81 complete prespecified candidates | Yes |
| `configs/submission/search_spaces/ProductSumGBDN.json` | 81 complete prespecified candidates | Yes |
| `configs/submission/search_spaces/GBDNPlus.json` | 243 complete prespecified candidates | Yes |
| `docs/experiments/gbdn_search_space_rationale.md` | Fairness, resource mapping, and limitations | Yes |
| `tests/test_gbdn_search_spaces.py` | Full candidate audit and adversarial tests | Yes |
| `handoffs/EXP-008-GBDN-SEARCH-SPACES.md` | Review boundary and reproduction record | Yes |

No operations, Gate, notebook, setup, manuscript, result, final-configuration,
dataset, or user-owned file was edited.

## Scientific impact

- Claims enabled: the prespecified spaces are complete worker-valid CPU-audited
  configuration sources; their canonical SpMV tiers and common optimization
  choices are aligned.
- Claims narrowed: resource alignment means equal reported feature-matrix SpMV
  tiers, not equal trainable parameters, wall time, memory, or approximation
  power.
- Claims rejected: confirmatory readiness, fair final model selection,
  predictive superiority, exact guarantees for finite realizations, and any
  result based on these unexecuted spaces.
- Paper sections affected: none before validation-only screening, independent
  review, and confirmatory execution.

## Evidence

### Proofs

- theorem/lemma: none;
- assumptions: canonical worker resource-count conventions at the starting
  commit;
- counterexamples checked: a common integer `K` does not produce a common SpMV
  count; method-specific dropout cannot be injected into Tight/Product-sum;
  equal SpMV tiers do not imply equal parameter counts.

### Tests

```text
PYTHONPATH=src python -m pytest -q -p no:cacheprovider \
  tests/test_gbdn_search_spaces.py tests/test_screening_contract.py
25 passed in 3.52s
```

Every one of the 405 GBDN-family candidates passes the actual worker model,
optimizer, and training validators. For each candidate and each of the five
official task heads, the test constructs the canonical model on CPU before a
forward pass, constructs its optimizer, proves the optimizer covers all
registered trainable parameters, checks exact parameter accounting, and checks
that its SpMV count belongs to `{2,6,10}`. No training or data load occurs.

```text
PYTHONPATH=src python -m pytest -q -p no:cacheprovider
792 passed, 2 skipped, 1 failed in 142.38s
```

The sole full-suite failure is the pre-existing fail-closed Gate-token state at
the exact starting commit:
`test_current_repository_verifier_is_read_only_and_blocked` expects Gate
acceptance to pass, while `validate_gate_a_acceptance` reports
`gate report content hash does not match token`. This task did not edit a Gate
path or token and did not attempt to repair or bypass that independent blocker.

Search-space byte identities:

- Tight GBDN: `62fe55fb8eed9d6456085317661c3fb137e998b1f6fe374bf6ad71af99bb9c80`;
- Product-sum GBDN: `e20685c1c9c26b05d2d704adb58c3dda358a134377c575741c3455f42b549014`;
- GBDN+: `58dfb04753c8920f1fb4838a617b0d6024034be311bce694cc1ecf9efbcfa50d`.

### Experiment artifacts

- run IDs: none;
- result paths: none;
- aggregate paths: none;
- generated paper assets: none;
- final configurations: none;
- H100 execution: none.

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Every candidate fully specifies model/optimizer/training | PASS | Enumeration and worker validation test |
| Every candidate builds for all five official task heads | PASS | CPU builder test |
| Optimizer sees all parameters before first forward | PASS | Parameter-identity test |
| Common optimization choices and SpMV tiers are enforced | PASS | Alignment/adversarial tests |
| Spaces are bounded and support a later common budget | PASS | Candidate counts 81/81/243; minimum 81 |
| Trial budget or validation units remain unfrozen | PASS | No manifest/plan change |
| Parameter-matched comparison established | FAIL / OUT OF SCOPE | Explicit limitation |
| Gate/readiness blocker repaired | FAIL / OUT OF SCOPE | Pre-existing token/report mismatch |

## Known limitations

- Actual trainable-parameter counts differ by architecture and task head.
- Equal SpMV counts omit dense operations and do not imply equal wall time or
  memory. Stage-3 measurements remain mandatory.
- The deterministic sampler can provide different marginal hyperparameter
  coverage because Tight/Product-sum have 81 candidates and ChebNet/GBDN+ have
  243.
- Depth, root count, root parameterization, radius bound, and matched-parameter
  studies remain separate ablations.
- A degree-one GBDN target can have a larger finite-realization defect than a
  higher-degree candidate; validation may choose against it. No exact claim is
  attached to any finite candidate.
- No equal trial budget should be chosen before smoke-run runtime/memory data.

## Reviewer questions

1. Is matching the canonical `{2,6,10}` feature-matrix SpMV tiers sufficiently
   transparent for screening, provided exact parameters/time/memory are also
   reported and a matched-parameter ablation remains required?
2. Is fixing two levels and one root a reasonable primary-search boundary, or
   should root count receive a separate prespecified ablation before final
   configuration freezing?
3. Does the unequal Cartesian size make hash-ranked equal-trial sampling too
   sensitive to marginal coverage, requiring a stratified policy revision?
4. Should the lowest degree-one Tight/Product-sum tier be retained despite its
   possible finite-approximation defect, or excluded only after a prespecified
   mechanism-stage certificate rather than benchmark outcomes?

## Conflicts or decisions needed

The orchestrator must not silently treat these spaces as final configurations.
After Stage-3 measurements, it must independently adjudicate one equal integer
trial budget and validation-unit set. If reviewers reject the hash sampler's
coverage under unequal space sizes, revise the sampling policy before any
screening result exists rather than changing the spaces after seeing metrics.

## Reproduction instructions

Run the focused test command above from a clean checkout at the task commit.
It requires only the repository Python environment and CPU; it never opens an
official dataset or requests CUDA.

## Rollback

Revert the single bounded task commit. No result or frozen legacy artifact is
created or modified.
