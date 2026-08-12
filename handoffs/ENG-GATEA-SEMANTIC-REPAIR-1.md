# ENG-GATEA-SEMANTIC-REPAIR-1 handoff

## Task

- **Task ID:** ENG-GATEA-SEMANTIC-REPAIR-1
- **Agent:** Research Software Engineer
- **Branch:** `agent/engineering/ENG-GATEA-SEMANTIC-REPAIR-1`
- **Starting commit:** `4c2dd0545013a07060ec974c22a83f23a88f4e5b`
- **Ending commit:** commit containing this handoff; SHA reported separately
- **Status proposed:** REVIEW

## Objective

Repair the semantic failures identified by the final independent Gate-A review:
canonical graph-contract bypasses; weak GA-10, GA-14, GA-25, and GA-27
bindings; narrow finite-frame fixtures; and ambiguous finite-record pole
geometry. Keep Gate A blocked pending a new independent review.

## Summary

- Migrated synthetic graph eigensystems through the recorded reciprocal-mean
  preprocessor and validated Laplacian token. The sphere kNN helper no longer
  diagonalizes its directed relation.
- Required `ValidatedLaplacian` tokens in peeling sequences, added an exact
  center-width coefficient helper, and quarantined the misleading angular
  anchor called `oracle_coeffs_for_mode`.
- Replaced GA-10's sentinel-only mandatory regression/evidence with public
  `GBDNTight.analyze_complex` values checked against independently materialized
  dense Chebyshev operators and residual-first oracle analysis. It also checks
  the public readout, public synthesis against dense adjoint synthesis, and a
  carry-first negative control.
- Replaced GA-14's arbitrary perturbation with an actual exact Blaschke factor
  and actual degree-8 first-kind Chebyshev realization on a weighted graph.
  The row measures the full operator norm epsilon_K, exact squared recovery
  identity, induced epsilon_K/2 channel error, and total recovery bound.
- GA-25 mandatory test/evidence now retain stable singular values, numerical
  rank, condition number, interpolation residual, and a separate clustered
  ill-conditioned witness; it makes no finite-K claim.
- Added exact polynomial construction/reduction of the published real scalar
  finite-order CayleyNet rational continuation, including learned shared
  `h>0`, effective order, numerator/common denominator, cancellations, and
  reduced poles. GA-27 compares this frozen multiset with an independently
  reduced exact GBDN pole multiset under continuum-only scope.
- Broadened GA-21/22 to path, complete/repeated-spectrum, and nonuniform
  weighted graphs, representative degrees, and all required multilevel depths.
- Renamed GA-24 geometry to `target_root_pole_geometry` and recorded
  `geometry_scope="exact-target"`; no poles are attributed to the finite
  polynomial.
- Updated machine-readable evidence and report declarations only for fixtures
  actually exercised. Gate acceptance remains false.

## Files changed

| File | Change |
|---|---|
| `src/gbdn/synthetic.py` | Recorded preprocessing and validated eigensystems |
| `src/gbdn/peel.py` | Validated-token boundary; exact center-width helper; unsafe helper quarantined |
| `src/gbdn/diagnostics.py` | Frozen CayleyNet rational reducer, exact GBDN reducer, exact-target GA-24 semantics |
| `src/gbdn/__init__.py` | Exported reduced-pole diagnostic APIs |
| `src/gbdn/gate_a_evidence.py` | Substantive GA-00/10/14/21/22/24/27 evidence repairs |
| `src/gbdn/gate_a_report.py` | Declarations aligned with exercised repaired fixtures |
| `tests/test_gate_a_core_slice.py` | Synthetic/peel boundaries and public-oracle GA-10 |
| `tests/test_gate_a_exact_slice.py` | Actual-factor GA-14 |
| `tests/test_gate_a_approximation.py` | Broader frame matrix, GA-24/25/27 repairs |
| `tests/test_gate_a_provenance.py` | Repaired GA-27 evidence schema assertions |

## Scientific impact

- Enables a second independent Gate-A review of the formerly rejected rows.
- Does not promote Gate A to accepted and does not support finite-spectrum,
  approximation-superiority, trainability, efficiency, oversmoothing, or
  oversquashing claims.
- CayleyNet comparison remains restricted to one published scalar real
  finite-order response and continuum rational identity after cancellation.

## Evidence

```text
$env:PYTHONPATH='src'
py -3.14 -m pytest tests/test_gate_a_core_slice.py tests/test_gate_a_exact_slice.py tests/test_gate_a_approximation.py tests/test_gate_a_provenance.py -q -p no:cacheprovider
149 passed, 3 warnings in 10.94s

py -3.14 -m pytest tests -q -p no:cacheprovider
474 passed, 3 warnings in 25.43s

evaluate_gate_a_evidence + validators
36/36 rows; 735 VALUE + 57 typed N/A = 792 fields;
zero schema errors; zero failed decisions
```

Warnings are two upstream PyTorch/Python 3.14 JIT deprecations and the existing
PyTorch sparse-invariant warning.

## Intentional compatibility changes

- `peel_sequence`, `tight_peel_sequence`, and `strict_forward_states` now
  accept a `ValidatedLaplacian` instead of raw edges. No repository caller was
  found. This is an intentional safety boundary.
- `oracle_coeffs_for_mode` now fails loudly because the scaled Cayley angular
  anchor is not an exact spectral center. Use
  `center_width_coeffs_for_mode`.
- Synthetic helpers preserve existing names and signal/eigenpair keys, while
  returned graph edges now represent the symmetric recorded adjacency. New
  adjacency, Laplacian token, edge weights, and preprocess record fields are
  included.
- GA-24 callers must use `target_root_pole_geometry`; the old ambiguous field
  is intentionally removed.

## Remaining blockers

1. Gate A needs a fresh independent binary review; the reporter must remain
   blocked until that acceptance is recorded externally.
2. Artifact serialization has not yet been implemented, so residual-first
   order beyond public analysis/readout/synthesis remains a later R3 guard.
3. The CayleyNet formula is bound to the existing primary-source audit; review
   must confirm its convention and scope before paper promotion.
4. Product-sum first-step zero root gradients remain a Gate-B optimization
   diagnostic, not a GA-35 lifecycle failure.

## Reproduction

Run the two pytest commands above, then run `py -3.14 scripts/report_gate_a.py`
from a clean integrated commit. The report must continue to state
`accepted=false` pending independent reviewer action.

## Rollback

Revert the task commit. No manuscript, result, notebook, legacy source,
experiment artifact, or user-owned dirty file is changed.
