# REV-GATEA-PREFLIGHT handoff

## Task

- **Task ID:** REV-GATEA-PREFLIGHT
- **Agent:** Independent A* Reviewer / Adversarial Auditor
- **Branch:** `agent/reviewer/REV-GATEA-PREFLIGHT`
- **Starting commit:** `baaa6183bc607c341610b366ec38fc25ab09888f`
- **Ending commit:** Commit containing this handoff; exact SHA reported after commit
- **Status proposed:** **BLOCKED**

## Objective

Independently preflight the frozen Gate-A scientific contract, attack assumptions, novelty, coefficient and root semantics, classify every proposed theorem/claim, and define stop-line tests without editing paper, source, or tests.

## Summary

The contract preserves a viable exact Parseval analysis construction but is not yet determinate enough for Gate-A acceptance. Eight definitional stop-line issues remain: graph preprocessing policy, fixed-root linearity, paraunitary terminology, exact-versus-polynomial pole semantics, incomplete T-D/T-F/T-G quantifiers, optional center-width numerical constraints, executable coefficient order, and absent canonical source/tests at the reviewed base.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `reviews/gate_a_contract_preflight.md` | Added independent theorem ledger, terminology/semantics audit, required tests, and verdict | Yes; review-only |
| `handoffs/REV-GATEA-PREFLIGHT.md` | Added bounded handoff and acceptance evidence | Yes; handoff-only |

## Scientific impact

- Claims enabled: fixed-root exact unit modulus, complete-map Parseval/isometry, adjoint synthesis, and narrowly conditioned pole/locality results remain viable.
- Claims narrowed: “paraunitary,” “movable pole,” weighted non-dissipation, conditioning, root center, graph stability, and sparse locality all require explicit object/assumption qualifiers.
- Claims rejected: carried-state non-dissipation, oversquashing mitigation, target-specific sensitivity, and empirical superiority from Gate A.
- Novelty decision: automatic consequences of a unitary split are supporting structure, not independent Blaschke contributions.

## Evidence

### Proofs

- theorem/lemma: T-A through T-H, existing exact claims, additive reconstruction, Product-sum, and phenomenon boundaries classified in the review.
- assumptions: fixed roots and `L`, self-adjointness, admissibility, commuting weights, true operator-norm finite errors, reduced pole sets, aligned perturbations, and exact/finite tags.
- proof location reviewed: `math/phase0_theorem_audit.md`; final proof ownership remains with Math Agent.
- counterexamples retained: carried-state annihilation, noncommuting weighted-energy failure, constant-node collapse, and arbitrarily small/zero target sensitivity.

### Tests

```text
command: no tests run — contract-only preflight
result: canonical src/gbdn and tests/test_gate_a.py are absent at base baaa618; implementation acceptance is impossible on this branch.
```

### Experiment artifacts

- run IDs: none; no experiments authorized or run.
- result paths: none.
- aggregate paths: none.
- generated paper assets: none.

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Read frozen contract, Phase-0 audit, and math audit | PASS | All three controlling files reviewed. |
| Independently classify proposed theorems/claims | PASS | Claim ledger in review. |
| Attack novelty, assumptions, coefficient order, and root semantics | PASS | Dedicated sections and stop-line list. |
| Specify Gate-A test obligations | PASS | Twelve-part full-operator test contract. |
| Modify only assigned review/handoff files | PASS | No scientific source or artifact edits. |
| Contract ready for Gate-A acceptance | FAIL | Eight unresolved stop-line definitions. |

## Known limitations

This is a preflight of the frozen written contract, not a formal proof sign-off, source review, or test execution. Closest-prior-work novelty still requires an independent literature audit. Numerical bounds must be rechecked against the implementation after canonical source/tests are merged.

## Reviewer questions

1. Will the core reject invalid graphs, with symmetrization isolated as recorded preprocessing?
2. Are Tight GBDN roots always global parameters fixed with respect to the analyzed input?
3. Will the paper lead with “nonsubsampled Parseval” and define any use of “paraunitary”?
4. Will finite artifacts call poles properties of the exact target rather than the polynomial realization?
5. What exact comparator family and pole-reduction rules define T-F?
6. Is T-G an operator perturbation theorem or a graph perturbation theorem with an additional graph-to-L bound?

## Conflicts or decisions needed

The orchestrator must adjudicate the eight stop-line issues before treating the contract as implementation-frozen. In particular, “reject or symmetrize” cannot remain a runtime choice under one canonical run identity.

## Reproduction instructions

Read the three controlling inputs at commit `baaa618` and compare them with `reviews/gate_a_contract_preflight.md`. No experimental reproduction is applicable.

## Rollback

Revert the single `REV-GATEA-PREFLIGHT` commit. No paper, source, test, notebook, or artifact is affected.
