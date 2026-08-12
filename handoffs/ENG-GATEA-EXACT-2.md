# ENG-GATEA-EXACT-2 handoff

## Task

- **Task ID:** ENG-GATEA-EXACT-2
- **Agent:** Research Software Engineer
- **Branch:** `agent/engineering/ENG-GATEA-EXACT-2`
- **Starting commit:** `c4c03ac12e28358b7ff0809e4aa788e9523b7f8a`
- **Ending commit:** commit containing this handoff; SHA reported to orchestrator
- **Status proposed:** REVIEW

## Objective

Implement the second exact Gate-A slice (GA-01/02/05/06/07/09/11/12/13/14/15
and GA-31--34) and close the raw caller-supplied Laplacian validation gap,
without editing the paper, results, or legacy implementation.

## Summary

- Added bounded exact center-width roots and inverse mapped-zero diagnostics.
- Added an independent dense adjoint-synthesis oracle.
- Required an auditable `ValidatedLaplacian` token for every caller-supplied
  operator. External operators receive a one-time finite, self-adjoint, and
  `[0,2]` spectral check; repeated forwards only unwrap the token and check its
  mutation version.
- Added deterministic exact Gate-A tests across paths, odd cycles, complete
  graphs, disconnected graphs, nonuniform weighted graphs, and depths
  `1,2,4,8,16`.
- Preserved the residual-first public coefficient convention throughout.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `src/gbdn/core.py` | Validated-Laplacian token, one-time external audit, mutation detection | Yes; canonical source only |
| `src/gbdn/layers.py` | Require token for precomputed Laplacians; support validated dense/sparse operators | Yes |
| `src/gbdn/model.py` | Public token type on Tight analysis/synthesis APIs | Yes |
| `src/gbdn/spectral.py` | Bounded center-width parameterization and inverse | Yes |
| `src/gbdn/oracle.py` | Independent residual-first adjoint synthesis | Yes |
| `src/gbdn/__init__.py` | Export new canonical APIs | Yes |
| `tests/test_gate_a_exact_slice.py` | Focused exact Gate-A contracts and counterexamples | Yes |
| `handoffs/ENG-GATEA-EXACT-2.md` | This handoff | Yes |

## Scientific impact

- Claims enabled: exact scalar all-pass geometry; pointwise partition; complete
  fixed-root block isometry/conditioning; exact adjoint reconstruction;
  commuting spectral weighted Parseval; exact permutation equivariance.
- Claims narrowed: weighted Parseval does not extend to arbitrary node
  projectors; complete-map isometry does not preserve the carried state or a
  selected source-to-target block.
- Claims rejected: carried-state non-dissipation and any implication that
  global isometry solves target-specific oversquashing.
- Paper sections affected: none edited; later paper work may consume only the
  reviewed exact results above.

## Evidence

### Proofs

- No new proof is claimed. Tests bind to the frozen theorem-to-test contract.
- Fixed roots and a fixed validated self-adjoint Laplacian are explicit.
- Counterexamples cover a noncommuting two-node projector, zero-mode carry
  annihilation, disconnected target sensitivity, connected endpoint decay,
  and finite-polynomial beyond-reach zeros.

### Tests

```text
py -3.14 -m pytest tests/test_gate_a_exact_slice.py -q -p no:cacheprovider
70 passed

py -3.14 -m pytest tests -q -p no:cacheprovider
117 passed, 3 warnings
```

Warnings are two environment-specific PyTorch-on-Python-3.14 TorchScript
deprecations and one PyTorch sparse-invariant warning. No test warning changes
the numerical verdict.

### Experiment artifacts

- None. No H100 or claim-bearing experiment was run.

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| GA-01 | PASS | Radial cap/extremes; bounded center-width inverse and finite gradients |
| GA-02 | PASS | Unit modulus, mapped zero/pole residuals, phase finite difference, Lorentzian law, phase additivity |
| GA-05 | PASS | Dense real grid beyond `[0,2]` plus path/cycle spectra |
| GA-06/07 | PASS | Full residual-first block at five depths over five deterministic fixtures |
| GA-09 | PASS | Recursive oracle equals explicit `A*` and reconstructs input |
| GA-11 | PASS | `I`, `L`, `L^2`, `L^0.5`, whole repeated-eigenspace projector |
| GA-12 | PASS | Deterministic two-node noncommuting projector mismatch |
| GA-13/14 | PASS | Matrix features, whole repeated eigenspace, recovery identity and finite approximation bound |
| GA-15 | PASS | Exact and sparse polynomial features/edges/operators/coefficients permute jointly |
| GA-31--34 | PASS | Lower bound, carry counterexample, Jacobian columns, connected/disconnected/beyond-reach sensitivity |
| External Laplacian gap | PASS | Raw misuse rejected; one-time spectrum audit; mutation detected |

## Known limitations

- This is not complete Gate A. Remaining IDs are GA-18 and GA-20--30.
- `validate_external_laplacian` intentionally performs a dense spectral check;
  large production graphs should use the canonical validated adjacency builder,
  whose normalized-Laplacian spectral range follows from construction.
- The token is an auditable application boundary, not a security primitive.
- Machine-readable Gate-A reporting remains deferred as requested.

## Reviewer questions

1. Does the one-time external-operator token sufficiently close the raw
   Laplacian bypass without obscuring the graph-construction contract?
2. Do the complete-graph repeated-eigenspace tests bind GA-11 and GA-13 to
   whole eigenspaces rather than arbitrary basis vectors?
3. Are the connected and disconnected GA-34 witnesses appropriately described
   only as claim-boundary counterexamples?

## Conflicts or decisions needed

None. Full Gate A and all claim-bearing H100 work remain blocked.

## Reproduction instructions

Run the two pytest commands in the evidence section from the repository root.

## Rollback

Revert the task commit. No frozen artifact, legacy path, paper, or result tree
was modified.
