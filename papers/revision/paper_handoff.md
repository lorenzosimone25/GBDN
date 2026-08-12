# GBDN revision handoff (superseded where noted)

The canonical source of truth is now `sub_plans/01_SCIENTIFIC_CONTRACT.md`,
followed by `math/theorem_ledger.md` and
`math/theorem_to_test_contract.md`. This earlier handoff remains useful for
historical context, but it must not override those files or the live execution
board.

## Central claim

GBDN is a learned Blaschke–Cayley tight graph filter bank with interpretable all-pass pole–zero geometry and explicit multilevel reconstruction.

When code, theory, figures, or prose disagree with the canonical contract, stop
and resolve the discrepancy before producing new evidence.

## Canonical mathematical convention

For the symmetric normalized Laplacian `L`, use

\[
\phi(\lambda)=\frac{\lambda-i}{\lambda+i},\qquad
B_\alpha(z)=\frac{z-\alpha}{1-\overline\alpha z},\qquad
T_{\mathcal A}=B_{\mathcal A}(\phi(L)).
\]

The canonical implementation convention is `forward`. An inverse factor may be evaluated only through an explicit `convention="inverse"` argument. Figures, theorem statements, and default code paths use `forward`.

Roots use the radial parameterization

\[
\alpha=r_{\max}\,\sigma(s)e^{i\theta},\qquad r_{\max}=0.95.
\]

Independent constraints on real and imaginary coordinates are prohibited because they do not imply `|alpha|<1`.

## Model taxonomy

| Variant | Role | Permitted guarantee |
|---|---|---|
| Tight GBDN | Primary reconstructing analysis model | Exact multilevel isometry and adjoint perfect reconstruction for exact factors; measured approximation error for Chebyshev factors |
| Product-sum GBDN | Expressive BDN-inspired spectral model | Finite-spectrum interpolation after the Vandermonde theorem; unitary individual exact factors |
| GBDN+ | Parallel empirical filter mixture | No strict tightness, reconstruction, or unwinding guarantee |
| GBDNStrict | Deprecated legacy implementation | No paper evidence; its residual-sum readout telescopes to the lifted input |

## Theorem inventory

| ID | Result | Status in revision | Required numerical check |
|---|---|---|---|
| T1 | Unit modulus, forward Poisson phase law, mapped zero and pole | Retain and correct | Unit modulus and finite-difference phase sign |
| T2 | Exact unitary factor and tight one-level split | Retain | Unitarity and channel-energy identity |
| T3 | Multilevel coefficient isometry and adjoint perfect reconstruction | Add | Exact energy and reconstruction through depth 16 |
| T4a | Magnitude-based spectral energy separation | Replace packet theorem | Retained energy and leakage inequalities |
| T4b | Phase-sensitive complex recovery | Add | Complex response and signal error |
| T5 | Chebyshev error governed by mapped-pole distance | Replace radius-only result | Angle/radius sweeps and frame bounds |
| T6 | Product-sum finite-spectrum interpolation | Replace informal proof | Zero-root Vandermonde rank check |
| T7 | Factor-product norm, carried-path contraction, and coefficient-map isometry | Separate statements | Separate operator measurements |
| T8 | Laplacian-only analytic lift | Remove | None; requires an oriented operator in future work |

## Historical candidate claims (not paper-admitted)

The bullets below predate the 36-test contract. They remain hypotheses until
their corresponding Gate-A rows and independent reviews pass.

- Exact Blaschke–Cayley factors are all-pass and unitary.
- Exact complementary channels form a tight split.
- The complete exact multilevel coefficient representation is isometric and reconstructs by adjoint synthesis.
- Root geometry controls phase and mapped-pole location.
- Magnitude selectivity implies energy separation, not complex recovery.
- Product-sum GBDN interpolates a finite graph spectrum with enough terms.

## Prohibited claims before direct evidence

- State-of-the-art performance.
- Oversquashing mitigation or long-range reasoning.
- Graph analytic-signal construction.
- Exact equivalence to PDU or BDN.
- Complex signal recovery from magnitude-only fitting.
- Parameter efficiency from finite-spectrum universality alone.
- Tightness or perfect reconstruction for GBDN+.

## Historical gate summary

**Gate A:** the historical criteria below are regression checks only. Current
acceptance requires every GA-00--GA-35 row and fixture in
`math/theorem_to_test_contract.md`, a machine-readable report, and independent
review.

**Gate B:** theorem statements, appendix proofs, code defaults, test names, and planned figure labels use identical notation and assumptions.

**Gate C:** learned-geometry efficiency is claimed only if repeated, matched-budget mechanism experiments support it across multiple response families.

## Evidence state

The files in `papers/draft/`, `figures/draft/`, `results/`, and `results_LRGB/` are preserved baseline artifacts. They are not automatically valid evidence for the revision. New evidence must identify the exact model variant, convention, seed, configuration, source hash, and numerical summary.
