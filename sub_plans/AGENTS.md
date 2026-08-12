# Global Agent Rules

These rules apply to the orchestrator, Math Agent, Reviewer Agent, Software Engineer Agent, and any temporary sub-agent.

## 1. Source-of-truth hierarchy

When two sources conflict, use this order:

1. verified mathematics and executable contract tests;
2. immutable result artifacts and independently recomputed metrics;
3. the canonical implementation;
4. `01_SCIENTIFIC_CONTRACT.md`;
5. the current LaTeX manuscript;
6. legacy notebooks and archived artifacts;
7. informal notes.

Prose must be corrected to match evidence. Evidence must never be altered to preserve prose.

## 2. Evidence binding for every paper claim

Every claim that enters the abstract, introduction, conclusion, or main result discussion must be bound to one or more of:

- a numbered theorem and complete proof;
- an executable mathematical contract test;
- a prespecified experiment with immutable artifacts;
- an official benchmark protocol and statistical analysis;
- a clearly labeled limitation or negative result.

The handoff must identify the evidence path. Claims without evidence remain aspirational and must be labeled as such.

## 3. Method variants must remain separate

Use these names consistently:

- **Tight GBDN**: exact Blaschke–Cayley factors, complementary channels, multilevel coefficient analysis, adjoint synthesis, and the associated exact guarantees.
- **Product-sum GBDN**: cumulative all-pass products with a learned complex sum; expressive but not generally tight.
- **GBDN+**: relaxed empirical architecture with unconstrained polynomial correction; no strict all-pass, tightness, or reconstruction guarantee.

Results from one variant cannot be used to support the guarantees of another.

## 4. Exact versus approximate operators

Every theorem, test, result, and plot must label whether it concerns:

- an exact spectral operator computed through eigendecomposition;
- a finite-degree Chebyshev or Clenshaw realization;
- a learned nonlinear model containing the operator.

Never report exact unitarity or exact tightness for an approximate factor unless the measured tolerance and finite-order defect are explicitly stated.

## 5. Oversmoothing and oversquashing language

Allowed before confirmatory experiments:

- the exact complete coefficient map is isometric;
- the exact complete representation is injective and has condition number one;
- the exact linear analysis preserves total perturbation energy;
- the carried branch is contractive;
- these statements do not imply target-specific long-range sensitivity.

Forbidden without direct proof and dedicated experiments:

- “GBDN solves oversquashing”;
- “GBDN cannot oversmooth”;
- “GBDN guarantees long-range reasoning”;
- “non-dissipativity proves heterophily performance”;
- “tightness implies non-vanishing source-to-target influence.”

The Math Agent should seek precise positive statements and counterexamples, not force an unsupported theorem.

## 6. Benchmark integrity

- Test labels and test metrics may not influence hyperparameter selection, early stopping, baseline choice, or model inclusion.
- Binary heterophily tasks use the official binary loss and ROC-AUC.
- Multiclass heterophily tasks use the official multiclass loss and accuracy.
- All official split masks must be retained.
- The primary confirmatory table requires all fixed splits and at least three training seeds per split.
- The split, not the individual seed, is the unit of paired statistical inference.
- A baseline may enter the primary table only after upstream commit, license, configuration, and metric reproduction are recorded as verified.
- Equal-budget tuning and upstream-configuration evaluation must be labeled separately.

## 7. Repository safety

- Never overwrite `results/`, `results_LRGB/`, or any other frozen legacy reference artifact.
- Move or wrap legacy code rather than silently changing its behavior.
- Do not cache a graph operator by node count alone.
- Do not define trainable parameters lazily after optimizer construction.
- Do not duplicate model or metric logic inside a notebook.
- Generated tables and figures must never be hand-edited.
- Result artifacts are immutable. A different run identity must write to a different path or require an explicit rerun flag.

## 8. Ownership and concurrency

Only one agent owns a file at a time.

| Area | Default owner |
|---|---|
| Theory statements and proof appendix | Math Agent |
| Review reports and red-team patches | Reviewer Agent |
| `src/`, `tests/`, `scripts/`, `configs/`, `notebooks/` | Software Engineer Agent |
| Execution board, decision log, accepted integrations | Orchestrator |
| `paper/generated/` | Generated only; no human owner |

Agents may propose changes outside their ownership through a handoff. They may not silently edit those files.

## 9. Branch and commit protocol

Use one branch per task:

```text
agent/math/<TASK_ID>
agent/reviewer/<TASK_ID>
agent/engineering/<TASK_ID>
```

Each commit message begins with the task ID. A task is not complete until:

1. required tests pass;
2. artifacts are generated;
3. a handoff file follows `11_HANDOFF_TEMPLATE.md`;
4. the reviewer or orchestrator records a gate decision.

## 10. Required failure behavior

Stop the line and mark the task `BLOCKED` when:

- paper and implementation disagree;
- a theorem fails under a valid counterexample;
- an official metric cannot be reproduced;
- a baseline implementation is not verifiable;
- a test artifact is missing predictions or provenance;
- a result depends on test-set model selection;
- the H100 notebook cannot resume safely;
- a generated paper number lacks a run identifier.

Do not “fix” a failed result by weakening a test or changing the reported metric without an explicit scientific decision.

## 11. Definition of done

A task is `DONE` only when its acceptance criteria, evidence, files, tests, limitations, and downstream dependencies are all documented. “Code written,” “proof sketched,” or “notebook executed” are intermediate states, not completion.
