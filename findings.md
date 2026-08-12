# Current research findings

## Supported structural results pending independent acceptance

- Radial root parameterization keeps learned roots inside the prescribed disk.
- Each exact Blaschke–Cayley factor has unit modulus on the graph spectrum.
- Complementary half-sum/half-difference channels satisfy one-level energy partition.
- The complete exact multilevel coefficient map is an isometry and admits adjoint reconstruction.
- Exact identities concern the complete complex coefficient representation, not the carried state, learned input lift, nonlinear readout, or finite Chebyshev realization.

## Evidence that can currently be used only as exploratory or diagnostic

- The five-initialization sphere experiment suggests phase-sensitive fitting improves recovery and leakage relative to magnitude-only fitting, but its publication figure selects the best run and lacks matched external methods.
- Mapped-pole distance correlates with approximation error in the current synthetic study; parameter-efficiency and superiority claims remain untested.
- The single-split, single-seed H100 runs establish execution at scale only. They do not support comparative performance claims.

## Falsification and stop-line findings

- Strict verification of the legacy reproduction fails; its metrics cannot serve as confirmatory evidence.
- Isometry, unitarity, and invertibility do not imply mitigation of oversquashing.
- The carried path is contractive and may collapse even when the complete coefficient map is perfectly conditioned.
- The new finite-order tests materialize full operators and evaluate true operator-norm defects and theorem-derived bounds; independent semantic review and full fixture coverage are still pending, so these results are not yet paper-promoted.
- The current development benchmark uses scientifically invalid protocol elements for the planned confirmation: a universal two-logit cross-entropy formulation, test evaluation during training, non-tie-aware AUROC, naive run-level aggregation, and writes under a frozen legacy result root.
- The canonical implementation, tests, and manuscript are now trackable on the submission branch, but remain absent from the frozen public `origin/main`; no H100 or public-reproduction claim may rely on them until a reviewed publication commit is created.
- The reusable `sphere_graph_data` path constructs directed kNN edges and can violate self-adjointness; the separate mechanism-study generator mirrors weights and explicitly symmetrizes its Laplacian, so its remaining blockers are per-run provenance and selection policy rather than this particular graph defect.
- A connected-path counterexample preserves total complete-analysis Jacobian norm while making endpoint-to-endpoint sensitivity approximately `7.6e-17`, decisively separating global isometry from oversquashing mitigation.

## Novelty boundary after primary-source review

- Graph-QMF already supplies critically sampled perfect-reconstruction graph banks, and undecimated graph framelets are a close precedent for redundant tight multiscale graph representations.
- CayleyNet learns its shared scale and therefore does not have fixed poles; its published scalar family has a learned but restricted shared imaginary-axis pole locus.
- The defensible candidate distinction is the combination of independently parameterized generic exact-target poles, complementary identity interference, and a nonsubsampled complete coefficient isometry.
- A finite Chebyshev realization is polynomial and has no literal poles. Any movable-pole advantage remains an empirical hypothesis requiring matched Cayley and polynomial comparisons.

## Open hypotheses

- Movable Blaschke poles may fit localized or phase-sensitive graph spectral responses more efficiently than matched polynomial and fixed-pole alternatives.
- A finite-order multilevel frame bound can be stated tightly enough to guide implementation tolerances.
- Graph perturbation stability may hold under explicit spectral-gap or functional-calculus assumptions; a gap-free eigenvector claim is unlikely.
- The complete coefficient representation may resist linear representation collapse, while no comparable claim is currently justified for target-specific long-range transmission.
