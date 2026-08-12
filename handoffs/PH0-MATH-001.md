# PH0-MATH-001 Agent Handoff

## Task

- **Task ID:** PH0-MATH-001
- **Agent:** Mathematical Researcher
- **Branch:** agent/math/PH0-MATH-001
- **Starting commit:** fcfa84111df8fcd66cd7266066bcd4c2aa97b852
- **Ending commit:** This handoff's commit; SHA reported to the orchestrator.
- **Status proposed:** BLOCKED

## Objective

Independently audit the current manuscript's theorem claims, assumptions, proofs, counterexamples, implementation bindings, and Gate A evidence without editing the primary checkout.

## Summary

The exact complete-analysis algebra is viable: exact Blaschke--Cayley factors are unitary for self-adjoint L, the complementary split is Parseval, and the nested complete coefficient map is an isometry with adjoint reconstruction. Gate A remains blocked because graph construction does not enforce self-adjointness, the proposed root frequency-center interpretation is false as written, mandatory tests are absent, and the canonical scientific inputs are not commit-bound. Explicit counterexamples reject any inference from tightness to carried-state non-dissipation or target-specific oversquashing prevention.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| math/phase0_theorem_audit.md | Added theorem ledger, proof audit, counterexamples, code/test map, and blockers. | Yes |
| handoffs/PH0-MATH-001.md | Added this handoff. | Yes |

## Scientific impact

- Claims enabled: exact factor unitarity; one-level Parseval split; complete exact multilevel isometry and adjoint synthesis; conditional weighted Parseval, finite-order frame, pole-separation, perturbation, and locality results.
- Claims narrowed: phase localization must use mapped-zero center/width; finite-order statements require measured operator defects; reconstruction concerns the analyzed lift.
- Claims rejected: rho phi(mu) has exact center mu; tightness prevents oversmoothing; tightness guarantees nonzero source-to-target sensitivity or solves oversquashing.
- Paper sections affected: preliminaries, method reconstruction distinction, theory, Gate A experiments, limitations, abstract, and introduction.

## Evidence

### Proofs

- theorem/lemma: every current numbered result plus candidate T-A through T-H.
- assumptions: finite-dimensional self-adjoint L, spectrum in [0,2], admissible roots, exact/finite distinction.
- proof location: math/phase0_theorem_audit.md.
- counterexamples checked: carried zero-mode annihilation; connected-path target sensitivity near zero with global isometry; disconnected targets; repeated eigenspaces; constant-feature node collapse; finite-hop locality.

### Tests

Command: .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_gate_a.py

Result: 10 passed.

The suite is insufficient for Gate A: pointwise partition, weighted Parseval, additive reconstruction, conditioning, permutation equivariance, repeated/disconnected graphs, true operator-norm sparse comparison, multilevel finite-order frame defect, and target-block sensitivity are missing.

### Experiment artifacts

- run IDs: none; Phase 0 read-only audit.
- result paths: existing artifacts/mechanism_v1 inspected only.
- aggregate paths: none created.
- generated paper assets: none.

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Audit every current numbered result | PASS | math/phase0_theorem_audit.md |
| State assumptions and novelty boundary | PASS | Global assumptions and result audit |
| Seek counterexamples | PASS | Counterexamples section |
| Bind theory to code/tests | PASS | Correspondence and Gate A tables |
| Modify only assigned files | PASS | Git diff contains two files |
| Gate decision | FAIL/BLOCKED | Self-adjointness, parameterization, test, and provenance blockers |

## Known limitations

- This is Phase 0 only; no source, test, paper, or artifact repair was authorized.
- Literature novelty conclusions require independent Reviewer verification.
- The existing mechanism artifact lacks enough provenance to identify its graph construction.

## Reviewer questions

1. Does prior graph-QMF/framelet work make the tight cascade too standard for headline status?
2. Is the reduced-pole separation theorem materially novel relative to CayleyNets?
3. Are the finite-order multilevel defect constants acceptable, or is a sharper scalar spectral bound preferable?
4. Does any valid connected-graph assumption support a target-block lower bound? This audit predicts no universal one.

## Conflicts or decisions needed

- Retain alpha = rho phi(mu) as an angular anchor or replace it with alpha = phi(mu + i gamma) for exact center/width semantics.
- Symmetrize graph inputs deterministically or reject asymmetric inputs.
- Freeze canonical scientific sources in version control before accepting evidence.

## Reproduction instructions

From the primary checkout, run:

    .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_gate_a.py

## Rollback

Revert this task commit. It adds only the two audit Markdown files and does not touch frozen artifacts or the primary checkout.
