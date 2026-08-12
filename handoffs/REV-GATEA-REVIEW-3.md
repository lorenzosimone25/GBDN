# REV-GATEA-REVIEW-3 handoff

## Task

- **Task ID:** REV-GATEA-REVIEW-3
- **Role:** Independent adversarial A* reviewer
- **Reviewed commit:** `b9f33383124f8afaa52c112b3a46105800c016ef`
- **Worktree:** isolated detached clean worktree
- **Status:** COMPLETE

## Binary verdict

**REJECT / STOP THE LINE.** Thirty-five of 36 mandatory Gate-A rows are accepted. GA-00 remains rejected because public exact eigendecomposition constructors expose an unrestricted `orthogonality_atol`; `10.0` admits the frozen nonorthogonal basis and returns a matrix with unitarity defect `4.83269046506849`.

## Deliverables

- `reviews/gate_a_third_independent_review.md`
- `handoffs/REV-GATEA-REVIEW-3.md`

No source, test, paper, result, plan, board, or H100 artifact was edited.

## Verification

```text
Gate-A test-file selection: 488 passed, 3 warnings
Full repository suite:       558 passed, 3 warnings
Public-boundary suite:        34 passed
Artifact/core suite:          44 passed

Reporter schema: gbdn-gate-a-coverage-v3
Collected Gate-labelled nodes: 462
Row status: 36 PASS
Mapping status: 18 UNIQUE, 18 DUPLICATE, 0 MISSING
Typed evidence: 811 VALUE, 59 N/A
Evidence schema errors: 0
Evidence decision failures: 0
Coverage mismatches: 0
Provenance-link errors: 0
Source tree: clean at b9f3338
Machine acceptance: false; independent review pending
```

Warnings are limited to two upstream Python 3.14/PyTorch TorchScript deprecations and the existing PyTorch sparse-invariant warning.

## Reproduced stop-line witness

Both calls below accepted rather than rejected:

```python
gbdn.blaschke_cayley_exact(
    eigenvalues,
    nonorthogonal_eigenvectors,
    roots,
    orthogonality_atol=10.0,
)

gbdn.exact_blaschke_operator_from_eigendecomposition(
    eigenvalues,
    nonorthogonal_eigenvectors,
    roots,
    orthogonality_atol=10.0,
)
```

Observed:

```text
||T* T-I||_op = 4.83269046506849
singular values = [2.4150963676566803, 0.41406215229841137]
```

Default calls reject the same input. The failure is specifically the public ability to relax a theorem premise, not a defect in valid default arithmetic.

## Repairs accepted in this review

- GA-13 now uses an actual admissible-root Blaschke complementary channel, a whole repeated eigenspace, matrix-valued features, realized separation/leakage quantities, squared recovery identity, recovery bound, and the former prescribed multiplier as a negative control.
- Reporter row `status` is restricted to `PASS`/`FAIL`/`NOT_RUN`; multiplicity is confined to `mapping_status`.
- Frozen fixture/root/depth/degree scope is cross-validated against computed typed evidence with drift/tamper blockers.
- The historical ten-check entry point is explicitly diagnostic and cannot print global Gate acceptance.
- Production and oracle exact arithmetic share validation only and remain arithmetically independent.
- Residual-first coefficient artifacts bind tuple/root order, payload integrity, run identity, source/config/environment, and completed-bundle semantics; permutation/tamper/race tests pass.
- All previously rejected or conditional rows other than GA-00 are accepted with their narrowed scientific scope.

## Required next action

Remove or safely cap caller-controlled orthogonality relaxation at every public exact constructor; add the large-finite-tolerance frozen witness; rerun from a clean commit; request another independent review.

No H100 or Gate-B/C claim-bearing work may proceed before that review passes.
