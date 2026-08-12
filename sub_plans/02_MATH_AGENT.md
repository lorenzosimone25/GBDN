# Math Agent Work Plan

## Role

You are the mathematical owner of GBDN. Your objective is not to maximize the number of theorems. Your objective is to produce the narrowest correct statements that establish genuine novelty, match the implementation, and support measurable experiments.

You may edit the method, theory, and proof appendix after the orchestrator resolves the actual LaTeX paths. You do not change benchmark outcomes or implementation details silently.

## Required inputs

Read:

1. the current manuscript;
2. `AGENTS.md`;
3. `00_ORCHESTRATOR.md`;
4. `01_SCIENTIFIC_CONTRACT.md`;
5. the canonical implementation after it exists;
6. the closest-method matrix in `12_ASTAR_REFERENCE_MATRIX.md`.

## Deliverables

Create:

```text
math/theorem_ledger.md
math/proof_audit.md
math/counterexamples.md
math/theorem_to_test_contract.md
paper patch for method/theory/proof appendix
handoffs/<TASK_ID>.md
```

If these directories do not exist, ask the orchestrator to create or map them.

## Work sequence

### MATH-001 — Audit the existing manuscript

For every proposition, theorem, corollary, and remark:

- restate the assumptions;
- verify notation and conjugation;
- verify the proof line by line;
- identify whether the result is novel, standard, algebraic, or redundant;
- identify the exact object: factor, channel, carried state, coefficient map, or nonlinear network;
- identify exact versus finite-order scope;
- attempt a counterexample outside the assumptions;
- assign a status from the scientific contract.

Pay particular attention to:

- the denominator of the Blaschke factor;
- the zero/pole conjugacy statement;
- Chebyshev interpolation conventions;
- the lower and upper finite-order frame inequality;
- the finite-spectrum Product-sum proof;
- repeated eigenvalues;
- root multiplicity;
- disconnected graphs;
- complex feature dimensions;
- the difference between recovering the lifted signal and recovering the original real input.

### MATH-002 — Separate additive and adjoint reconstruction

Add an explicit lemma:

\[
r_\ell+h_{\ell+1}=h_\ell
\]

for any shared channel factor.

Then state clearly that the nontrivial tight-bank result is:

\[
(P_\ell^-)^*P_\ell^-+(P_\ell^+)^*P_\ell^+=I,
\]

which yields adjoint synthesis.

The introduction and abstract must not imply that additive reconstruction requires Blaschke unitarity.

### MATH-003 — Prove pointwise paraunitary partition

Prove the scalar identity for effective multilevel atoms:

\[
\sum_{\ell=0}^{D}|a_\ell(\lambda)|^2=1.
\]

Provide:

- full proof;
- a one-paragraph intuition;
- a numerical test specification;
- a statement of whether it holds on the entire real interval or only on the graph spectrum;
- the relation to nonsubsampled paraunitary filter banks.

### MATH-004 — Prove weighted spectral Parseval conservation

For \(W=w(L)\succeq0\), prove:

\[
\sum_{\ell=0}^{D-1}\|W^{1/2}r_\ell\|_F^2+
\|W^{1/2}h_D\|_F^2
=
\|W^{1/2}h_0\|_F^2.
\]

Discuss:

- \(W=I\);
- \(W=L\);
- \(W=L^s\);
- spectral projectors;
- why node projectors generally do not commute with \(L\);
- why this is a frequency-resolved non-dissipativity statement rather than a target-node propagation guarantee.

### MATH-005 — Conditioning, anti-collapse, and gradient scope

Formalize:

\[
A_D^*A_D=I,
\qquad
\kappa(A_D)=1,
\qquad
\|A_D\delta h\|=\|\delta h\|.
\]

Check and prove the nodewise coefficient lower bound induced by the additive left inverse.

Then state limitations:

- output redundancy grows with depth;
- the bound weakens with \(D\);
- identical lifted node features remain identical under the lower bound;
- a nonlinear readout can discard information;
- the carried state can contract.

### MATH-006 — Oversquashing theorem audit

Do not begin from the assumption that a positive theorem exists.

Perform three steps:

1. **Global statement:** characterize the exact Jacobian of the linear analysis and total perturbation-energy preservation.
2. **Target-specific audit:** analyze the block
   \[
   \frac{\partial z_v}{\partial h_u}.
   \]
3. **Counterexample search:** construct a valid graph/filter setting where the total Jacobian norm is preserved but a specified source-to-target block is zero or arbitrarily small.

Deliver a claim boundary table:

| Claim | Status | Assumptions | Paper wording |
|---|---|---|---|
| Total perturbation energy is preserved |  |  |  |
| Every target receives non-vanishing influence |  |  |  |
| Bottleneck oversquashing is prevented |  |  |  |
| Gradient norm through the complete analysis is conditioned |  |  |  |

A counterexample is a successful deliverable because it prevents an incorrect headline claim.

### MATH-007 — Finite-degree multilevel frame theorem

Given per-level approximation errors

\[
\|T_\ell-\widetilde T_\ell\|_{\mathrm{op}}\le\epsilon_\ell,
\]

derive an explicit multilevel bound for:

\[
\|\widetilde A_D^*\widetilde A_D-I\|_{\mathrm{op}},
\]

the frame lower and upper bounds, and adjoint reconstruction error.

Requirements:

- the bound must reduce correctly at \(D=1\);
- it must expose depth dependence;
- it must distinguish uniform \(\epsilon\) from heterogeneous \(\epsilon_\ell\);
- it must be numerically testable;
- it must not obscure the exact additive left inverse of shared approximate channels;
- if a much sharper bound is available by pointwise scalar analysis, prefer it.

### MATH-008 — Root localization and approximation trade-off

Derive a clear relation among:

- \(\alpha=\rho e^{i\theta}\);
- phase derivative;
- frequency center on the real Laplacian interval;
- mapped zero and pole;
- pole distance;
- Bernstein ellipse parameter;
- required Chebyshev degree.

Evaluate the interpretable parameterization

\[
\alpha=\rho\,\phi(\mu).
\]

State which quantities are monotone and which are not.

### MATH-009 — Movable-pole separation from CayleyNet

State a generic exact separation theorem based on reduced rational pole multisets.

The theorem must:

- acknowledge shared Cayley rational structure;
- avoid claiming that GBDN represents every filter more efficiently;
- state the exceptional parameter sets where poles cancel or coincide;
- connect directly to the matched response-efficiency experiment.

### MATH-010 — Graph perturbation stability

Attempt a resolvent or rational functional-calculus bound under a positive pole margin.

Deliver one of:

- a valid theorem with explicit constant;
- a conditional theorem with clearly stated normality/self-adjoint assumptions;
- a proof that the proposed form is too strong, plus a narrower replacement.

Bind the theorem to edge-noise and point-cloud graph perturbation experiments.

### MATH-011 — Locality and complexity

State:

- exact rational operators are generally global;
- a degree-\(K\) polynomial realization is \(K\)-hop localized;
- sequential depth changes effective degree and sparse-operation count;
- the complete coefficient stack has memory cost proportional to emitted channels unless streamed.

Use total sparse matrix–vector multiplications as the comparison unit.

### MATH-012 — Optional learned unitary routing

Analyze:

\[
\begin{bmatrix}
r_\ell\\ h_{\ell+1}
\end{bmatrix}
=
U_\ell
\frac1{\sqrt2}
\begin{bmatrix}
h_\ell\\ T_\ell h_\ell
\end{bmatrix},
\qquad U_\ell\in U(2).
\]

Determine:

- exact isometry;
- adjoint synthesis;
- relationship to the current Hadamard split;
- whether additive reconstruction survives;
- whether the added parameterization strengthens the paper enough to justify implementation.

This is optional and may be rejected to preserve focus.

## Proof format

Every accepted result must include:

1. **Statement**
2. **Assumptions**
3. **Proof**
4. **Interpretation**
5. **What it does not prove**
6. **Executable observable**
7. **Required test tolerance**
8. **Paper sections affected**
9. **Closest prior result and distinction**

## Numerical proof assistance

For small graphs, request or provide test specifications that compare:

\[
U g(\Lambda)U^*
\]

against the sparse realization.

Numerical agreement supports implementation correspondence but never substitutes for a proof.

## LaTeX editing rules

- Preserve one notation for \(T_\ell\), \(P_\ell^\pm\), \(r_\ell\), and \(h_{\ell+1}\).
- Number all theorem statements and cross-reference all assumptions.
- Put short proof intuition in the main paper and full details in the appendix when page-limited.
- Move non-central finite-spectrum interpolation to the appendix unless it becomes essential.
- Add a compact “scope of guarantees” table.
- Avoid replacing precise operator statements with broad GNN language.

## Completion criteria

The Math Agent is complete only when:

- every existing theorem has a status;
- every accepted new theorem has a full proof;
- every theorem has a test binding;
- oversmoothing and oversquashing boundaries are explicit;
- the Reviewer Agent has no unresolved mathematical blocker;
- the implementation equations match the paper exactly.
