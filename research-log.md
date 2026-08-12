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
- Added the missing deterministic Gate-A fixture matrix: two path sizes, even and odd cycles, a rectangular grid, star, complete/repeated-eigenspace graph, disconnected union, and a frozen positive nonuniform weighted graph. Exact sweeps cover depths 1, 2, 4, 8, and 16; full sparse-versus-dense operator tests now include degrees 16, 32, and 64. The full local suite passes 192 tests with two environment warnings.
- Strengthened that matrix to the full graph × depth × declared-root-family product and added a directed kNN-style rejection witness. The expanded local suite passes 429 tests with two environment warnings; scientific acceptance still awaits corrected finite observables, GA-23/report integration, and independent review.

## 2026-08-12 — Gate A matrix and finite-diagnostic closeout

- Added GA-23 center--width, mapped-pole, Bernstein-ellipse, and angular-anchor witnesses plus a deterministic read-only GA-00--GA-35 reporter.
- Completed the prescribed deterministic fixture, depth, root, and row matrices, including a degree-128 sparse-versus-dense high-order case. The reporter now finds no missing ID or declared matrix gap.
- Repaired the independently identified finite-order semantic defects: GA-22 now exercises synthesis and additive reconstruction, GA-24 joins approximation error with the ellipse supremum diagnostic, GA-29 is scoped to failure of finite-hop localization, and GA-30 uses the documented complex sparse-application convention across multiple depths and degrees.
- Integrated the contract-aligned theory rewrite while keeping all claims paper-blocked. The full local suite passes 447 tests with three environment warnings.
- Kept Gate A closed. The remaining blockers are complete per-row machine-readable provenance, independent semantic acceptance, and verified attribution of the exact first-kind Chebyshev interpolation bound.

## 2026-08-12 — Theory attribution and evidence calibration

- Verified the Chebyshev coefficient bound from Trefethen's primary SIAM chapter and added an explicit aliasing derivation for the implementation's exact $K+1$ first-kind roots. This resolves the T-E attribution block without changing the diagnostic bound.
- Rebuilt the full manuscript after the source repair: 24 pages, no undefined citations or references, no missing figures, no duplicate labels, and no overfull boxes. The full local suite remains 447/447 passing.
- Audited the existing mechanism artifacts. The pole-distance sweep retains all 80 grid records, but its composite source hash is not the current source commit; the sphere study retains aggregate moments and one selected run but not the ten per-initialization rows.
- Narrowed the abstract, introduction, mechanism captions, and conclusion accordingly: current mechanism and legacy H100 outputs are diagnostics, not contribution evidence. No claim-bearing experiment was launched.
- Opened immutable run-identity and artifact-bundle infrastructure in parallel; this infrastructure work does not authorize H100 execution.
- Added installable `src`-layout package metadata and made the H100 setup install and import the canonical `gbdn` package before running tests. A fresh wheel smoke test imports `GBDNTight`; the full suite is now 449/449 passing.

## 2026-08-12 — Gate A structured evidence and independent rejection

- Integrated a deterministic, read-only evidence catalog for all 36 mandatory Gate-A rows. It emits 703 measured values and 59 typed, justified not-applicable fields, links them to 410 collected Gate nodes, and reports no schema, linkage, omission, or decision failure.
- Re-ran the integrated repository suite with the canonical source path bound: 456 tests passed with three environment warnings. The reporter remains blocked by design.
- Integrated the independent row-by-row review. It found no counterexample to the core exact mathematics or the first-kind Chebyshev derivation, but rejected GA-00, GA-10, GA-14, GA-25, and GA-27 at the reviewed commit.
- Opened a bounded semantic-repair task for the canonical synthetic graph boundary, public residual-first coefficient correspondence, actual finite Blaschke recovery bound, Product-sum ill-conditioning disclosure, and executable reduced-pole comparator. No H100 experiment or claim-bearing paper promotion is authorized until a second independent review accepts the repaired clean commit.
- Integrated the immutable run-identity and artifact-bundle core after bounded adversarial review. A critical Windows-junction deletion hazard was removed by eliminating automatic recursive cleanup; partial and corrupt bundles are now classified and blocked. The integrated focused artifact/boundary suite passes 41 tests. This infrastructure does not authorize an experiment.
- Integrated the bounded Gate-A semantic repair. The full integration suite passes 503 tests; the evidence catalog links 428 Gate nodes and emits 735 measured values plus 57 justified not-applicable fields with no schema, decision, or provenance-link errors. A second independent adversarial review is running from the clean integration commit; Gate A remains blocked until that review returns a binary acceptance.

## 2026-08-12 â€” Second Gate-A falsification pass and R3 artifact binding

- Integrated residual-first complex coefficient serialization into the immutable run-bundle core. The codec binds semantic order, depth, component names, complex dtype, shape, RunIdentity, source, environment, and managed-file hashes; permutation, truncation, tamper, overwrite, and concurrent-writer tests fail closed. The integrated suite before the next repair passes 522 tests.
- The second independent review reproduced a live public-API counterexample: exported `blaschke_cayley_exact` accepted a nonorthogonal eigenbasis, out-of-range eigenvalues, and an inadmissible root. A two-node nonorthogonal witness produced an alleged exact factor with operator unitarity defect above five rather than rejecting the input.
- The same review falsified the semantic binding of GA-13. Its prescribed diagonal response does not satisfy the complementary all-pass premise; the target and complement witnesses have unit-modulus residuals of approximately 0.072 and 0.038 for `1-2q`.
- The report also mixes `DUPLICATE` mapping information into the contract's PASS/FAIL/NOT_RUN row status and accepts fixture/root/depth declarations from hard-coded metadata without payload validation. A diagnostic ten-check script can misleadingly print global Gate-A acceptance.
- Opened one bounded public-boundary repair covering validated exact inputs, an actual Blaschke-response GA-13 witness, report semantics/provenance, and removal of false acceptance messaging. Gate A and every claim-bearing H100 run remain blocked.

## 2026-08-12 — H100 operations preflight

- Audited the canonical execution path without launching experiments. Immutable run identities, source/environment capture, atomic write-once bundles, resume classification, and failure records are accepted as foundations.
- Confirmed that the submission CLI, thin H100 notebook, frozen plan/configurations, official task contracts, isolated scheduler, independent metric recomputation, split-first statistics, verified baseline registry, renderers, and fail-loud verifier are still missing.
- Authorized only CPU-side runner and synthetic smoke infrastructure while Gate A is under independent review. H100 jobs, Gate B/C runs, confirmatory benchmarks, and claim-bearing paper outputs remain blocked.
- Froze a future H100-only publication boundary: installable canonical source, relevant tests, setup/runner scripts, one operator notebook, frozen configurations, locked dependencies, and a concise operator README. Audits, agent material, manuscript/generated content, exploratory or legacy outputs, and raw results are excluded.

## 2026-08-12 — Public Gate-A boundary repair

- Hardened the exported exact operator against nonorthogonal eigensystems, spectra outside the normalized-Laplacian interval, inadmissible roots, nonfinite inputs, and precision/device mismatches while preserving the empty-product identity and separate production/oracle arithmetic.
- Replaced GA-13's invalid prescribed multiplier with an admissible Blaschke-derived complementary channel on a validated weighted graph, including repeated-eigenspace, separation, leakage, and recovery-bound checks.
- Split row execution state from duplicate mapping metadata and bound frozen fixture/root/depth/degree coverage declarations to computed typed evidence; tampering now blocks acceptance. The historical ten-check file is explicitly diagnostic only.
- Re-ran the integrated suite: 558 tests passed with three known environment warnings. The evidence catalog reports 36/36 rows, 811 measured values, 59 justified not-applicable fields, and no schema, decision, provenance, or coverage mismatch.
- Opened a third independent Gate-A review from the clean repair commit. Gate A remains closed until that review issues a binary acceptance.

## 2026-08-12 — Third Gate-A review and official protocol freeze

- The third independent review accepted 35 of 36 mandatory rows, including the repaired GA-13 theorem premise, evidence/report semantics, oracle separation, and residual-first artifact binding.
- It rejected GA-00 after reproducing a remaining public-API escape: `orthogonality_atol=10` makes both exact eigendecomposition constructors accept the frozen nonorthogonal basis and return a factor with operator unitarity defect `4.83269046506849`.
- Opened a minimal fourth-pass repair to remove caller-controlled relaxation, freeze dtype-aware validation, and add the exact bypass as a regression. Gate A remains rejected until a different independent reviewer accepts that repair.
- Froze the official Platonov five-dataset task contract from the official paper and repository: Roman-empire and Amazon-ratings use multiclass cross-entropy and accuracy; Minesweeper, Tolokers, and Questions use a scalar binary head, BCE-with-logits, and binary ROC-AUC.
- Formally excluded the legacy one-split/one-seed universal cross-entropy and macro-AUROC path from confirmatory evidence. Dataset checksums, redistribution terms, adapter parity, baseline licenses/versions, and the isolated train/validation-versus-test boundary remain implementation blockers.

## 2026-08-12 — CPU submission smoke path

- Added a diagnostic-only `scripts/run_submission.py` interface with `preflight` and `smoke` commands for one fixed synthetic CPU job. It sets `CUDA_VISIBLE_DEVICES=-1` before importing the canonical package or PyTorch.
- Bound the frozen configuration, synthetic dataset, source, dependency lock, environment, split, seed, and trial to one immutable run identity; executed the job in an isolated subprocess and committed predictions/labels through the atomic bundle core.
- Independently recomputed the saved prediction accuracy, rejected tampering, and verified that a second invocation resumes as `skipped` without rerunning the worker. No raw bundle was retained or committed.
- Kept every claim-bearing mode fail-closed behind an intentionally unimplemented, independently reviewed Gate-A acceptance-token schema. The H100 notebook, GPU scheduler, official datasets, multi-job failure handling, statistics, renderers, and final verifier remain absent.
- The integrated smoke/artifact/provenance slice passes 41 tests; the source branch full suite passed 565 tests with three known environment warnings. This operational milestone enables no scientific claim.

## 2026-08-12 — Exact validation tolerance closure

- Removed caller-controlled orthogonality relaxation from every root-exported exact eigendecomposition boundary and froze a dtype-aware internal threshold. The previous `orthogonality_atol=10` bypass is now a rejected keyword on all aliases.
- Removed public symmetry/spectral tolerance and spectrum-disable knobs from canonical graph validators; only a private post-construction path may omit the dense spectrum check after validated normalized-Laplacian construction.
- Added regressions for the frozen nonorthogonal basis, large/NaN/infinite/negative tolerance attempts, spectrum-disable attempts, and out-of-range diagonal spectra. The GA-00 evidence now records zero accepted public bypasses.
- The combined repository suite passes 573 tests with three known environment warnings. A fourth independent review is active; Gate A remains closed until its verdict.

## 2026-08-12 — Official heterophily metadata contract

- Added a declarative, immutable registry for the five official Platonov datasets, including canonical aliases, source commit and NPZ paths, graph/task dimensions, exact heads/losses/selection/test metrics, ten official splits, and three frozen training seeds.
- Added fail-closed metadata validators for required NPZ arrays, canonical serialization and hashes, graph expansion/count invariants, connected simple graphs, ordered official split identities, class counts, disjoint/full-coverage partitions, and the complete dataset/method/split/seed plan product.
- Made unresolved NPZ checksums and dataset-specific redistribution terms explicit blockers rather than placeholder acceptance. No data was downloaded or opened.
- Added a training/checkpoint-selection view whose exact-key parser rejects test indices, labels, or metrics, preserving the future process-level leakage boundary at the contract layer.
- The contract/smoke/artifact slice passes 49 tests and the complete integrated suite passes 590 tests with three known environment warnings. Independent contract review is still required before acquisition or evaluation implementation.

## 2026-08-12 — CPU smoke adversarial hardening

- Found that the reusable smoke API could build a parent plan under one environment and accept a worker bundle captured under another because resume validation compared run identity but not the full parent source/environment records.
- Bound completed source and environment metadata to the parent plan, forced diagnostic plan construction under `CUDA_VISIBLE_DEVICES=-1`, supplied an explicit isolated child environment, and restricted the worker to the canonical repository script.
- Added compressed-archive/member limits before NumPy loading and rejected `results_submission` roots that resolve through a symlink outside the repository. The output-root symlink regression is skipped where Windows symlink privileges are unavailable; the underlying canonical artifact layer retains separate junction/symlink tests.
- The hardened operations/boundary/contract slice passes 67 tests with one platform skip. The complete suite passes 592 tests with the same platform skip and three known environment warnings. Independent operations review remains pending because the delegated reviewer exhausted its service quota without producing evidence.
- Executed the permitted synthetic diagnostic smoke from clean detached commit `b4d751c`: run ID `84e410613b7c03cb2efe420fd537e31633de71343d67fb32b1bae911cbced57d` completed with the fixed `4/6` accuracy fixture, and the second invocation returned `skipped` with the identical worker PID. Config/result/bundle hashes, clean source commit, dependency lock, and `CUDA_VISIBLE_DEVICES=-1` were verified.
- Git detached the temporary smoke worktree but Windows could not remove its directory because of long path names. The explicit external path was left untouched rather than using an unsafe recursive workaround; it is outside the repository and excluded from publication.

## 2026-08-12 — Split-first statistical contract

- Added independent task-specific metric recomputation: multiclass accuracy for Roman-empire/Amazon-ratings and a tie-aware rank-based binary ROC-AUC for Minesweeper/Tolokers/Questions.
- Required the complete frozen `10 splits × seeds [0,1,2]` grid, independent metric verification, frozen configurations, and no test exposure before averaging training seeds within each split.
- Implemented Student-t uncertainty over the ten split means, exact two-sided paired sign-flip comparisons, standardized paired effects when defined, win/tie/loss, and Holm correction for a predeclared comparison family.
- The full repository suite passes 603 tests with one platform-specific skip and three known environment warnings. This is synthetic protocol infrastructure only: no real prediction, test metric, significance claim, or table was produced.
