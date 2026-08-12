# ENG-GATEA-TOLERANCE-REPAIR-1 handoff

## Task

- **Task ID:** ENG-GATEA-TOLERANCE-REPAIR-1
- **Role:** Research Software Engineer
- **Starting commit:** `65122cd5235ecd51663bbcbae9d8f86ae4b7f08a`
- **Ending commit:** commit containing this handoff; SHA reported separately
- **Status proposed:** REVIEW

## Objective

Close the GA-00 public tolerance escape identified by the third independent
review. Claim-bearing exact constructors and canonical graph validators must
not let a caller relax the premises required for exact unitarity or a valid
normalized-Laplacian operator.

## Implementation

- Removed the public `orthogonality_atol` parameter from:
  - `blaschke_cayley_exact`;
  - `exact_blaschke_operator_from_eigendecomposition`;
  - `validate_exact_blaschke_eigendecomposition`.
- Retained a fixed internal orthogonality threshold of
  `100 * finfo(eigenvalue_dtype).eps`. Production and oracle arithmetic still
  share only validation; their scalar and matrix assembly remain separate.
- Removed caller-controlled `symmetry_atol` from public `validate_adjacency`.
- Split operator validation into a private
  `_validate_self_adjoint_operator(..., check_spectrum=...)` and the public
  `validate_self_adjoint_operator(operator)`. The public function always uses
  fixed self-adjointness tolerance, the normalized-Laplacian interval `[0,2]`,
  and fixed spectral slack. Only the immediately post-construction internal
  path may omit a redundant spectral eigendecomposition.
- Added regressions proving that every root-package exact alias rejects the
  former `orthogonality_atol=10.0` keyword and still rejects the frozen
  nonorthogonal witness under its fixed validation.
- Added regressions proving public graph validators reject former relaxation
  keywords, including large finite, NaN, infinity, negative values, and an
  attempted `spectral_bounds=None` bypass.
- Added a computed GA-00 evidence metric recording zero accepted tolerance
  overrides across all three public exact boundaries.

## Intentional compatibility break

This is an intentional fail-closed API break. Callers that previously passed
`orthogonality_atol`, `symmetry_atol`, `spectral_atol`, or `spectral_bounds`
to canonical public validators now receive `TypeError`. Such calls could
change or disable scientific premises while retaining canonical validation
names. Diagnostic code requiring noncanonical tolerances must implement an
explicitly private/local diagnostic and cannot mint a `ValidatedLaplacian` or
return a claim-bearing exact operator.

Valid supported behavior is preserved:

- float32 and float64 eigendecompositions;
- real or precision-matched complex orthonormal eigenvectors;
- forward and inverse conventions;
- strict dtype and device matching;
- finite roots strictly inside the unit disk;
- the mathematically valid empty-root identity product.

## Frozen counterexample

The repaired boundaries were probed with:

```text
eigenvalues  = [0, 1]
eigenvectors = [[1, 1], [0, 1]]
root         = 0.2 + 0.1 i
former argument = orthogonality_atol=10.0
```

Before repair, the public production and oracle constructors accepted this
call and returned an operator with
`||T* T-I||_op = 4.83269046506849`. After repair, the former keyword is not in
any claim-bearing signature, and the default call rejects the basis as not
orthonormal.

The public graph validator also no longer accepts either
`symmetry_atol=2` for a triangular operator or `spectral_atol=10` /
`spectral_bounds=None` for `diag(-4,7)`.

## Files changed

| File | Change |
|---|---|
| `src/gbdn/oracle.py` | Fixed exact-eigenbasis threshold; removed public relaxation parameters |
| `src/gbdn/spectral.py` | Removed production exact-constructor relaxation parameter |
| `src/gbdn/core.py` | Fixed public graph validation and private redundant-spectrum path |
| `src/gbdn/gate_a_evidence.py` | GA-00 no-tolerance-bypass observable |
| `tests/test_gate_a_public_boundary.py` | All public exact alias regressions |
| `tests/test_gate_a_core_slice.py` | Public graph-validator relaxation regressions |
| `handoffs/ENG-GATEA-TOLERANCE-REPAIR-1.md` | This handoff |

## Verification before commit

```text
Focused exact/core/provenance suite: 70 passed, 3 warnings
Full repository suite:               566 passed, 3 warnings

Reporter schema: gbdn-gate-a-coverage-v3
Collected Gate-labelled nodes: 470
Row status: 36 PASS
Typed evidence: 817 VALUE, 59 N/A
Evidence schema errors: 0
Evidence decision failures: 0
Coverage mismatches: 0
Provenance-link errors: 0
GA-00 public invalid acceptance count: 0
GA-00 tolerance-override acceptance count: 0
```

Warnings are the two existing upstream Python 3.14/PyTorch TorchScript
deprecations and the existing PyTorch sparse-invariant warning.

The pre-commit reporter correctly remained blocked by the dirty source tree
and independent-review policy. It must be rerun from the clean committed SHA.

## Scientific status

This task repairs the third review's sole rejected observable. It does not
self-accept Gate A. Gate A remains blocked until a fourth independent reviewer
runs the full suite and reporter from the clean committed SHA and accepts the
package boundary. No H100 or Gate-B/C claim-bearing work is authorized by this
handoff.

No paper, result, execution board, notebook, legacy implementation, or user
artifact was modified.
