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
