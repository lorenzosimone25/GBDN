# REV-GATEA-REVIEW-2 handoff

## Assignment

- Role: independent adversarial reviewer
- Base commit: `a0d4248d6c3e06c46eb71ce1cc4ae49ed6eeb212`
- Branch: `agent/reviewer/REV-GATEA-REVIEW-2`
- Scope: read-only scientific and package-boundary audit; review documents only
- Experimental work: none
- Source, tests, manuscript, results, notebook, and board changes: none

## Binary verdict

**Gate A is REJECTED.** The suite executes cleanly, but mandatory rows GA-00 and GA-13 fail semantic review. H100 claim-bearing execution and Gate B remain blocked.

## Deliverables

- `reviews/gate_a_second_independent_review.md`: complete evidence-backed adjudication of GA-00--GA-35, counterexamples, source audit, reporting defects, and repair criteria.
- `handoffs/REV-GATEA-REVIEW-2.md`: this bounded handoff.

## Verification performed

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
py -3.14 -m pytest tests/test_gate_a.py tests/test_gate_a_approximation.py tests/test_gate_a_closeout.py tests/test_gate_a_core_slice.py tests/test_gate_a_exact_slice.py tests/test_gate_a_fixture_matrix.py tests/test_gate_a_provenance.py -q -p no:cacheprovider
# 452 passed, 3 warnings in 27.42 s

py -3.14 -m pytest tests -q -p no:cacheprovider
# 503 passed, 3 warnings in 26.62 s

py -3.14 scripts/report_gate_a.py --repository-root .
# clean a0d4248 source; 428 collected nodes; 36/36 execution_status PASS;
# 735 VALUE + 57 N/A evidence fields; no reporter-detected schema/provenance/coverage gaps
```

The public inverse-convention analysis/synthesis probe also passed (`2.42e-16` maximum component relative error; `1.36e-16` synthesis error). No implementation or artifact was changed by these checks.

## Blocking findings and exact witnesses

### 1. GA-00: unchecked exported exact operator

`gbdn.blaschke_cayley_exact` accepts:

- a nonorthogonal eigenbasis `[[1,1],[0,1]]` for eigenvalues `[0,1]` and root `0.2+0.1j`;
- normalized-Laplacian eigenvalues `[-4,7]`;
- outside-disk root `1.2+0j`.

For the first witness it returns an operator with

```text
||T* T-I||_op = ||T T*-I||_op = 4.83269046506849
singular values = [2.4150963676566803, 0.41406215229841137]
```

The validated oracle rejects all three. Related exported raw helpers also leave root admissibility ambiguous. In particular, `tight_split_responses(alpha=1.2)` reports negative forward phase derivatives `[-0.18181818181818177, -0.18144329896907216, -0.18032786885245897]`; NaN roots propagate through products/coefficients; `mapped_zero_pole(alpha=1)` returns NaN/infinity. Raw rational evaluation may remain available, but it must be unmistakably separated from validated Blaschke/paraunitary claims.

### 2. GA-13: theorem-premise mismatch

The row prescribes response values and marks roots N/A. An exact channel `q=(1-B)/2` must satisfy `|1-2q|=1`. Its actual target and complement witnesses violate that constraint by, respectively,

```text
0.07215940187498293
0.037702862276130955
```

The row checks a generic diagonal multiplier, not the stated GBDN/Blaschke channel theorem.

### 3. Reporter schema

Eighteen row `status` fields are `DUPLICATE` although the contract allows only PASS/FAIL/NOT_RUN. Their `execution_status` is PASS and the reporter does not block. Keep multiplicity in `mapping_status`; make `status` execution-only.

### 4. False diagnostic acceptance

Running `tests/test_gate_a.py` directly prints `Gate A passed: 10 checks`. The contract explicitly says that subset is diagnostic only, and one legacy test labels a one-vector error as a frame bound. Rename/quarantine this entry point and remove the global acceptance message.

### 5. Pre-H100 provenance conditions

- Cross-validate static coverage declarations against executed typed evidence.
- Bind serialized Tight coefficients to an explicit residual-first schema; current generic immutable artifacts do not establish that semantic order.

## Row result summary

- ACCEPT: GA-01--GA-12 except GA-00; GA-14--GA-35.
- CONDITIONAL: none.
- REJECT: GA-00, GA-13.
- Total: 34 ACCEPT, 0 CONDITIONAL, 2 REJECT.

Notable repairs accepted by this review include public residual-first analysis/readout/synthesis (GA-10), actual finite-factor recovery bounds (GA-14), finite-spectrum Product-sum conditioning disclosure (GA-25), the correctly scoped real CayleyNet reduced-pole comparison (GA-27), broadened finite-frame matrices (GA-21/22), and exact-target-only pole metadata (GA-24).

## Chebyshev source decision

The degree-`K`, `N=K+1` first-kind aliasing derivation and constant `4 M_rho rho^{-K}/(rho-1)` are correct for the code's nodes and complex response. Primary source: Lloyd N. Trefethen, *Approximation Theory and Approximation Practice*, extended edition, SIAM, 2019, Ch. 8, pp. 55--62, DOI `10.1137/1.9781611975949.ch8`; first-kind node convention appears in Exercise 2.4. Author sample: `https://people.maths.ox.ac.uk/~trefethen/trefethen_sample.pdf`. No unsupported import of the book's second-kind interpolation theorem remains.

## Required next handoff

An implementation author should make a bounded semantic repair for the two rejected rows and the reporter/diagnostic defects. A different independent reviewer should then rerun the clean reporter, full Gate suite, full repository suite, the exact invalid-input witnesses, and an actual-root GA-13 construction. Gate A may be accepted only if all 36 rows are semantically accepted and reporter status/provenance are consistent.

## Rollback

This commit contains documentation only. Reverting it removes the review record and does not alter scientific code or artifacts.
