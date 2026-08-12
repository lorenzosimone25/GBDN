# GBDN research log

## 2026-08-11 — Phase 0 freeze

- Froze repository state at `fcfa84111df8fcd66cd7266066bcd4c2aa97b852` and moved orchestration work to `agent/orchestrator/ORCH-001`.
- Preserved the preexisting modification to `REPRODUCTION.md` and the preexisting untracked `reproduction_report.md` without editing either file.
- Read the complete governance sequence through `sub_plans/12_ASTAR_REFERENCE_MATRIX.md`, including the newly supplied software-engineering charter.
- Created isolated worktrees for the mathematical, reviewer, and engineering audits.
- Inventoried 128 frozen legacy/reproduction result files and four mechanism-study files; recorded collection-level hashes in `results_submission/reports/phase_0_manifest.json`.
- Ran the current test suite: 20 tests passed with three warnings.
- Ran strict legacy verification: it failed with 28 problems, including two material drift findings, numerous tie-sensitive AUROC mismatches, and a missing run manifest.
- Visually inspected the current 18-page manuscript PDF. Layout is serviceable; scientific and provenance blockers remain.
- Enforced the stop line: no benchmark-superiority claim and no new H100 sweep until Gate A and artifact identity are repaired and independently reviewed.

## Pending Phase 0 closure

- Completed: merged and adjudicated the independent Math and Reviewer reports, preserved the Engineering findings, and published the consolidated correspondence matrix in `PHASE0_AUDIT.md`.
- Corrected an overbroad audit inference: the reusable sphere helper is asymmetric, but the mechanism generator uses a separate explicitly symmetric graph construction whose recorded source hash matches the current source.
- Closed Phase 0 as an audit and opened `SCI-001`; `MATH-001` and `ENG-001` are ready in parallel. Gate A and H100 claim-bearing execution remain blocked.

## 2026-08-11 — SCI-001 scientific contract freeze

- Froze a foundational paper identity with Tight GBDN primary, Product-sum secondary, canonical relaxed GBDN+ separate, and Legacy GBDN+ provenance-only.
- Froze exact/Chebyshev/legacy realization tags, residual-first coefficient order, Frobenius/direct-sum/spectral norm conventions, and a fail-or-explicitly-symmetrize graph contract.
- Rejected `rho*phi(mu)` as an exact frequency-center parameterization. Kept unrestricted radial roots primary and admitted `phi(mu+i*gamma)` only as a Gate-B ablation candidate.
- Dropped optional unitary routing from the primary scope and froze the negative boundary from complete-map isometry to oversquashing claims.
- Opened MATH-001 and ENG-001 in parallel; no claim-bearing experiment is authorized.

## 2026-08-12 — Gate A preflight adjudication

- Accepted the 36-test GA-00–GA-35 mathematical contract as the Gate A target; none of these claims is promoted until executable evidence and independent review pass.
- Chose a deterministic graph policy: the core rejects invalid operators; a separate recorded preprocessor may use `A_sym=(A+A^T)/2` after coalescing, removing/counting self-loops, and validating nonnegative finite weights.
- Froze roots and `L` with respect to each analyzed input, qualified pointwise paraunitary terminology, and reserved literal mapped-pole language for the exact rational target.
- Froze the heterogeneous finite-order frame formula and complete hypotheses for generic reduced-pole separation and fixed-root operator perturbation stability.
- Merged ENG-001 provenance isolation and output-boundary tests, the MATH-001 theorem/proof/counterexample ledgers, and the independent Gate-A contract preflight.

## 2026-08-12 — Gate A implementation, first canonical slice

- Integrated `c4c03ac`, which adds the strict graph-input boundary, a separately recorded reciprocal-mean preprocessor, and an independent small-graph dense oracle.
- Changed the public Tight GBDN coefficient API and readout to the frozen residual-first order `(r_0,...,r_{D-1},h_D)` and added exact additive reconstruction.
- Added focused executable coverage for GA-00, GA-03, GA-04, GA-08, GA-10, GA-16, GA-17, GA-19, and GA-35.
- Re-ran the full local suite: 47 tests passed with two environment deprecation warnings.
- Kept Gate A closed: 27 mandatory IDs, the full fixture/depth matrix, machine-readable reporting, and independent theorem-to-test review remain incomplete.
- Completed a contract-aligned MATH-002--011 paper patch on its isolated branch; it remains paper-blocked pending independent proof review and executable Gate A evidence.
- Completed the primary-source novelty audit. It corrected CayleyNet from "fixed poles" to a learned shared imaginary-axis pole locus, identified undecimated graph framelets as the closest tight-stack precedent, and kept A* novelty conditional on matched mechanism and efficiency evidence.

## 2026-08-12 — Gate A exact/finite integration and literature closure

- Integrated the second exact contract slice and finite-realization diagnostics. The canonical boundary now validates external self-adjoint Laplacians once, binds them to a mutation-detecting hash token, and rejects raw precomputed tensors.
- Added executable coverage for every mandatory Gate-A ID except GA-23, including residual-first multilevel isometry/conditioning, adjoint and additive reconstruction, weighted Parseval, permutation equivariance, repeated eigenspaces, full sparse-versus-dense operators, finite frame bounds, perturbation, locality, complexity, and negative long-range-sensitivity witnesses.
- Repaired the combined GA-30 interface to consume the validated operator token. The full local suite passes: 140 tests, with two environment deprecation warnings.
- Kept Gate A closed because numeric ID presence is insufficient: GA-23, the prescribed fixture/degree/root matrix, residual-rich machine-readable reporting, and independent theorem-test acceptance remain incomplete.
- Completed the independent theory-patch review. It found no fatal counterexample to the core exact mathematics, but blocked paper promotion pending notation, hypothesis, attribution, and exact-versus-finite repairs.
- Verified nine missing comparison families from primary archival records and rebuilt Related Work. The bibliography now has 21 keys, no placeholders or duplicates, no unresolved cited key, and a clean LaTeX/BibTeX build.
- Preserved the novelty boundary: Parseval/perfect reconstruction is prior-supported structure; the candidate contribution is the combined learned generic Blaschke target-pole geometry, complementary phase-to-amplitude channels, and nonsubsampled complete-map isometry. Its usefulness still requires matched Gate B/C evidence.
- Independently rejected promotion of the finite-realization slice despite correct core formulas: GA-24 omitted approximation error and the ellipse supremum bound, GA-22 duplicated a frame-defect norm instead of testing synthesis, and GA-29's witness established non-finite-hop behavior rather than full density. A bounded corrective implementation is now in progress.
