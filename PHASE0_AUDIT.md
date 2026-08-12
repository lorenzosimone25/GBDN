# GBDN Phase 0 audit

**Audit date:** 2026-08-11

**Frozen public commit:** `fcfa84111df8fcd66cd7266066bcd4c2aa97b852`

**Orchestrator branch:** `agent/orchestrator/ORCH-001`

**Decision:** **Phase 0 complete as an audit; Gate A and all downstream claim-bearing execution are blocked.**

## Executive finding

The exact mathematical core is viable but the current repository is not submission-ready. The strongest defensible identity is a learned movable-pole Blaschke–Cayley paraunitary graph spectral analysis bank whose **complete exact coefficient representation** is isometric and adjoint-reconstructing for a self-adjoint graph operator. This does not establish non-dissipation of the carried state, practical resistance to oversmoothing, target-specific transmission, mitigation of oversquashing, benchmark superiority, or parameter efficiency.

The immediate blockers are repository provenance, an unenforced self-adjoint graph contract, incomplete Gate A coverage, unverified baselines/protocols, nonconfirmatory legacy H100 artifacts, and absent immutable submission infrastructure. No large H100 experiment is authorized until the accepted Gate A contract passes independent review.

## Frozen state and path map

- The worktree began with a preexisting user modification to `REPRODUCTION.md` and a preexisting untracked `reproduction_report.md`; both were preserved.
- The active paper is `papers/revision/main.tex`; the rendered `papers/revision/main.pdf` has 18 pages and is visually serviceable.
- Candidate canonical code is under `src/gbdn/`; preserved public reproduction code is `src/legacy_reproduction.py` plus the tracked legacy scripts/notebook.
- The current theorem-contract suite is `tests/test_gate_a.py`; the full suite collects 20 tests: **10 Gate A plus 10 legacy/pipeline**, not the manuscript's stated 9 plus 11.
- Frozen result roots are `results/`, `results_repro/`, `results_LRGB/`, and `results_LRGB_repro/`. Development mechanism artifacts are under `artifacts/mechanism_v1/`.
- The required operator notebook `notebooks/gbdn_submission_h100.ipynb` does not exist.
- The required generated-paper provenance directory exists only as an empty scaffold; no compliant `paper/generated/*.tex` chain exists.
- Full collection hashes, counts, source/PDF hashes, environments, and deterministic path templates are recorded in `results_submission/reports/phase_0_manifest.json`.

The `.gitignore` allowlist is a critical blocker: the active canonical source, Gate A test, manuscript, plans, mechanism artifacts, and submission scaffolding are ignored at the frozen public commit. A clean H100 pull therefore obtains the legacy reproduction but not the intended scientific method or paper.

## Result-artifact inventory and admission status

| Collection | Files | Classification | Admission decision |
|---|---:|---|---|
| `results/` | 60 | Legacy GBDN+ and local baselines, split 0/seed 25 | Frozen diagnostic only |
| `results_repro/` | 60 | H100 reproduction of legacy pipeline | Frozen diagnostic only; strict verification fails |
| `results_LRGB/` | 2 | Simplified Peptides-func legacy wrapper | Frozen diagnostic only; not official LRGB |
| `results_LRGB_repro/` | 2 | H100 reproduction of simplified wrapper | Frozen diagnostic only; predictions absent |
| `artifacts/mechanism_v1/` | 4 | Five-initialization controlled mechanism development study | Suggestive only; per-run artifacts absent and figure selects best run |

The legacy verifier reports **28 problems**: two material reproduction drifts, 25 stored-metric validation failures caused primarily by tie-sensitive AUROC discrepancies, and a missing `results_repro/run_manifest.json`. The largest scientific drifts include Roman-empire GBDN+ accuracy (`0.296329`), Roman-empire GBDN+ AUROC (`0.164991`), and Minesweeper H2GCN AUROC (`0.035276`). These artifacts cannot support comparative claims.

The mechanism generator's recorded source hash matches its current source and constructs a symmetric dense sphere graph. However, it retains aggregate statistics plus only the best complex-fit run, not immutable artifacts for every initialization. Its main-paper best-of-five figure violates the prespecified representative-run policy and must be regenerated.

## Paper ↔ theory ↔ code ↔ result correspondence

| Claim or object | Paper location | Theory status | Code/test binding | Evidence status | Orchestrator decision |
|---|---|---|---|---|---|
| Blaschke unit modulus, phase derivative, mapped zero/pole | Preliminaries; Prop. 1 | `PROVED`; mostly standard algebra | `spectral.py`; narrow derivative/pole tests | Numerical consistency only | Retain with explicit assumptions; not standalone novelty |
| Exact factor unitarity and complementary Parseval split | Thm. 1 | `PROVED`; automatic for any unitary factor | Exact dense helper; one graph test | Narrow | Retain as structure, not headline novelty alone |
| Exact multilevel isometry and adjoint reconstruction | Thm. 2 | `PROVED` for the complete analyzed lift | Exact analysis helper; depth-16 test | Narrow graph coverage | Retain; use Frobenius/direct-sum norms and exact scope |
| Additive reconstruction | Implicit/missing | `PROVED`, algebraically automatic and distinct from adjoint synthesis | Implicit in shared half-channels; no test | Missing | Add explicit lemma and exact/finite tests; do not market as central theorem |
| Pointwise multilevel paraunitary partition | Missing | `PROVED` for every real frequency | Response helpers; no test | Missing | Add theorem/test after independent review |
| Weighted spectral Parseval | Missing | `PROVED_WITH_ADDITIONAL_ASSUMPTIONS`: positive weights commuting with all levels | No binding | Missing | Add for `w(L)`; explicitly exclude generic node projectors |
| Exact conditioning and global perturbation-energy preservation | Implicit | `PROVED`: all singular values of complete exact analysis are one | No singular-value/Jacobian test | Missing | Add narrowly; do not translate to target sensitivity |
| Limited nodewise anti-collapse | Missing | `PROVED` via additive left inverse, with `1/sqrt(D+1)` weakening | No test | Missing | Optional corollary; not a universal no-oversmoothing theorem |
| Carried-state non-dissipation | Scope remark rejects it | `FALSE` generally; zero mode can be annihilated in one level | Carried-state tests absent | Unsupported | Never claim |
| Oversquashing mitigation | Explicitly disclaimed | `FALSE` if inferred from tightness; path counterexample preserves total norm while endpoint sensitivity is about `7.6e-17` | Dedicated runner absent | None | Remove/prevent; retain only the precise negative boundary |
| Spectral energy separation | Thm. 3 | `PROVED` but conditional/elementary | Test instantiates the inequalities | Weak | Keep as supporting lemma, not learned selectivity evidence |
| Complex packet recovery | Cor. 1 | `PROVED` conditionally | Controlled sphere objective | Five initializations, aggregate only | Suggestive; rerun immutably and compare matched methods |
| Mapped-pole Chebyshev envelope | Thm. 4 | `PROVED_WITH_ADDITIONAL_ASSUMPTIONS` | Pole sweep and sparse recurrence | Hand-designed sweep | Retain analytic bound with `M_rho`; weaken empirical “predicts” wording |
| One-level finite-order frame bound | Thm. 4 | `PROVED` given a true operator-norm premise | Current test uses one signal, not operator norm | Invalid theorem-test binding | Replace with dense operator-norm and multilevel defect tests |
| Multilevel finite-order frame bound | Missing | Candidate explicit recurrence derived in math audit | No implementation/test | Missing | Gate A requirement |
| Product-sum finite-spectrum interpolation | Thm. 5 | `PROVED`; elementary existence/genericity | Test uses exact zero-root witness, not representable nonzero roots | Incomplete | Move toward appendix; add nonzero/conditioning tests; no efficiency claim |
| Root parameter `rho phi(mu)` is centered at `mu` | Scientific contract candidate | `COUNTEREXAMPLE_FOUND`; center differs for finite `rho` | Not implemented as canonical parameterization | None | Rename `mu` angular anchor or adopt `phi(mu+i gamma)` after decision |
| Movable-pole separation from fixed-pole Cayley filters | Related-work prose only | `PROVED_WITH_ADDITIONAL_ASSUMPTIONS` generically on a continuum after reduced-pole accounting | No matched comparator | Missing | Formalize and audit novelty; Gate C decides usefulness |
| Graph perturbation stability | Missing | Conditional fixed-root resolvent bound is viable | No tests | Missing | Add explicit aligned/self-adjoint/pole-margin assumptions |
| Locality and sparse complexity | Sparse-computation prose | `PROVED`: finite degree is localized; exact rational operator generally global | Recurrence materializes basis; no accounting | Suggestive | State degree/depth/SpMV/memory precisely and implement accounting |
| Canonical Tight/Product-sum/relaxed separation | Method section | Conceptually clear | Separate model classes | No artifact tags | Retain; enforce variant and exact/finite tags in every run |
| Complete coefficient ordering | Paper uses residuals then final carry | Code helper returns final carry before residuals | No correspondence test | Mismatch | Freeze one public ordering or document/test the permutation |
| Mechanism improvement over magnitude-only fitting | Experiments/Fig. 1 | Empirical only | Source-hashed symmetric mechanism runner | Aggregate five-seed result; best-run figure | Suggestive; rerun per seed and use prespecified/median visualization |
| Legacy H100 execution at scale | Tables 1–2 | Not theory-bearing | Preserved legacy pipeline | 62 reproduced jobs | Diagnostic execution fact only |
| Heterophily superiority | Not currently asserted strongly | Unsupported | Official confirmatory runner absent | One split/seed, wrong/unverified protocols | Prohibit |
| LRGB/long-range result | Preliminary Peptides table | Unsupported as official LRGB or long-range evidence | Simplified wrapper discards official elements | No predictions | Remove from claim-bearing tables until official pipeline exists |

## Stop-line discrepancies and blockers

### Blockers

1. **The canonical scientific object is not versioned.** No result can be tied to the frozen public commit until the intentional allowlist is repaired and a clean checkout is verified.
2. **Self-adjointness is assumed but not enforced.** `normalized_laplacian` accepts asymmetric inputs; `src/gbdn/synthetic.py::sphere_graph_data` produces directed kNN edges with about `8.22e-2` relative Laplacian asymmetry. The separate mechanism runner symmetrizes its graph, so this defect is a general API/Gate A blocker rather than proof that the current mechanism artifact used an asymmetric graph.
3. **Gate A is incomplete.** Passing 10 scientific tests does not cover weighted Parseval, pointwise partition, additive reconstruction, conditioning, permutation equivariance, repeated/disconnected/weighted graphs, true sparse–dense operator agreement, multilevel frame distortion, gradient checks, or source-target sensitivity boundaries.
4. **Exact, finite, and legacy objects can be conflated.** The paper's exact theorems, finite Chebyshev canonical models, and legacy relaxed GBDN+ must have explicit variant/realization tags throughout code and artifacts.
5. **No compliant experiment/provenance system exists.** Run identity, immutable raw schema, prediction verifier, frozen plan, submission CLI, generated-paper chain, and operator notebook are absent.
6. **Legacy benchmark verification fails.** Its results are inadmissible for confirmation.

### Major issues

1. Development heterophily code uses cross-entropy/two-logit output for all tasks, a local tie-unsafe AUROC, test evaluation every epoch, naive run-level aggregation, and the frozen legacy result namespace.
2. Official task-specific metrics, equal validation-only search, split-level statistics, and verified upstream baselines are absent.
3. The reusable sphere helper violates graph symmetry; all graph entry points need validation/symmetrization and graph-identity hashes.
4. The main mechanism figure is post hoc best-run selection; all raw initializations must be preserved and a representative policy frozen.
5. The manuscript reports the wrong test split (9+11 rather than 10+10), manually types result tables, and lacks generated traceability.
6. The active source contains an identifying author while the compiled submission PDF is anonymous; anonymized source/supplement/PDF metadata must be verified at release.
7. Local, declared, and H100 environments disagree (Python 3.12/3.11/3.10 and differing numerical packages); a supported clean environment must be frozen.

## Current test and PDF audit

- `python -m pytest tests -q -p no:cacheprovider`: **20 passed**, with two PyTorch JIT deprecation warnings and one sparse-invariant warning.
- Gate A subset: **10 passed**, but Gate A verdict remains **FAIL/BLOCKED** due missing and inadequate contracts.
- `python scripts/reproduce_legacy.py verify`: **FAIL**, 28 problems.
- The 18-page PDF has no obvious catastrophic layout issue. Page 6 explicitly identifies the displayed mechanism result as the best of five; pages 7–8 devote substantial main-paper space to nonconfirmatory H100 tables and a positioning table. These are scientific/page-budget concerns, not typesetting failures.

## Accepted, narrowed, and rejected claims

**Provisionally accepted after independent proof audit:** exact phase/pole algebra; exact unitary factors; exact one-level Parseval split; exact complete multilevel isometry; adjoint reconstruction of the analyzed lift; conditional Chebyshev envelope; finite-spectrum Product-sum existence.

**Narrowed:** weighted spectral non-dissipation applies to the complete exact representation and commuting spectral weights; sparse realizations have measurable defects; movable-pole distinction is generic and exact, not universal efficiency; mechanism evidence is suggestive; legacy H100 only demonstrates that the preserved implementation ran.

**Rejected or prohibited:** `rho phi(mu)` as an exact frequency-center parameterization; inherited Tight-GBDN guarantees for GBDN+; state-of-the-art/heterophily superiority; official LRGB or long-range evidence from the simplified wrapper; no-oversmoothing from tightness; any assertion that tightness solves oversquashing or ensures nonzero target-specific sensitivity.

## Parallel work and dependency blocks

May proceed in parallel now:

- **Math:** formal theorem ledger, additive/adjoint distinction, pointwise and weighted Parseval proofs, conditioning/anti-collapse scope, multilevel finite-order bound, corrected root semantics, movable-pole distinction, perturbation/locality results, and counterexamples.
- **Engineering:** version/freeze the canonical object, isolate legacy code, enforce symmetric graph inputs, align component order, build an independent dense oracle, expand Gate A, and scaffold immutable run identity/schema/verifier/CLI/notebook.
- **Reviewer:** audit the accepted math/counterexamples and closest graph-QMF/framelet/Cayley literature independently; audit baseline licenses/upstream behavior.
- **Paper:** only claim narrowing, exact-versus-finite labeling, reconstruction distinctions, anonymization, and provenance wiring. Do not add superiority language.

Blocked by dependencies:

- Gate B claim-bearing mechanism work waits for Gate A and immutable per-run artifacts.
- Gate C waits for verified comparator implementations and frozen matching budgets.
- Full heterophily tuning/confirmation waits for official task contracts, baseline verification, immutable infrastructure, and H100 smoke/resume tests.
- Oversmoothing/oversquashing conclusions wait for accepted mathematical boundaries plus dedicated instrumentation and runs.
- LRGB waits for an official graph-level pipeline with edge information, official evaluator, splits, and prediction artifacts.

## Immediate execution decision

Phase 0's audit deliverables are complete. The next ready work is the scientific contract plus repository/Gate A repair; large experiments remain blocked. The execution board is the authoritative live dependency record. No benchmark superiority claim is admitted from Phase 0.
