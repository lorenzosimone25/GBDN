# REV-001 Phase-0 correspondence review

## Decision

**STOP LINE — Phase 0 does not pass.** The exact linear filter-bank algebra is a defensible starting point, but the repository does not yet establish Gate A, paper-to-artifact traceability, canonical benchmark execution, or an A* empirical contribution. No large or claim-bearing H100 experiment should start yet.

Reviewed state: public `HEAD` `fcfa84111df8fcd66cd7266066bcd4c2aa97b852`; active manuscript `papers/revision/main.tex` and 18-page PDF; canonical `src/gbdn`; preserved legacy implementation and 62 archived plus 62 reproduced artifacts; notebooks, tests, scripts, dependency files, and pinned baseline checkouts.

Read-only checks:

- `python -m pytest tests -q -p no:cacheprovider`: **20 passed**.
- `python scripts/reproduce_legacy.py verify ...`: **failed with 28 problems**, including two metric drifts, 25 stored-metric validation errors, and a missing run manifest.
- The active manuscript, canonical package, Gate-A tests, mechanism artifacts, figures, and plans are ignored/untracked at the public commit. A clean checkout cannot reproduce the active paper.

## Claim-to-object correspondence

| Paper claim/object | Theory | Canonical code | Evidence | Classification | Reviewer disposition |
|---|---|---|---|---|---|
| Blaschke all-pass modulus, phase derivative, and mapped zero/pole geometry | Proposition and appendix proof are substantially correct for admissible roots and self-adjoint `L` | `src/gbdn/spectral.py` uses the forward convention and radial roots | Narrow numerical checks | **proved**, pending independent math audit | Keep; state assumptions and complex/Frobenius norm convention precisely. |
| One-level complementary Parseval split | Algebra follows automatically from unitary `T` | `GraphBlaschkeLayerTight` implements half-sum/half-difference | One path-graph test | **proved**, but not by itself novel | Keep as structural property, not the primary novelty claim. |
| Exact multilevel isometry and adjoint reconstruction | Telescoping proof is credible for the exact complete coefficient map | Analysis/synthesis code represents a finite Chebyshev approximation | Exact helper test plus limited finite test | **proved for exact analyzed lift only** | Never transfer this claim to the finite network, carried state, nonlinear readout, or original real input. Use Frobenius notation instead of ambiguous `||.||_2` for matrix-valued signals. |
| Complete coefficient ordering | Paper defines `(r_0,...,r_{D-1},h_D)` | `TightAnalysisOutput.components` returns `[h_D,r_0,...]` | No correspondence test | **unsupported correspondence** | MAJOR: align implementation and manuscript or explicitly document the permutation. |
| Energy separation | Conditional spectral inequalities are direct consequences of their hypotheses | Exact response utilities exist | Test constructs quantities already satisfying the inequalities | **proved but algebraically weak** | Do not present as demonstrated selectivity without learning/generalization evidence. |
| Phase-sensitive packet recovery | Conditional corollary is credible | Controlled exact spectral fitting exists | Five initializations; mean and sample SD only | **empirically supported in one controlled setting**, not comparative | Retain narrowly after preserving all runs and replacing the selected-best figure. |
| “Mapped-pole distance predicts error more precisely than radius” | Chebyshev analyticity bound is plausible, subject to math review | Pole sweep runner exists | One hand-designed grid; Spearman `chi=-1`, radius `0.873`; the bound constant is not evaluated | **suggestive only** | Weaken to “orders the tested errors”; require prespecified sweeps, uncertainty, and direct predicted-versus-observed validation. |
| Finite-spectrum product-sum interpolation | Vandermonde witness at zero and continuity argument are plausible | Product-sum uses cumulative factors and scalar complex coefficients | Test uses exact zero roots, which finite radial logits cannot represent | **proved in principle; implementation validation incomplete** | Add nonzero representable-root tests and conditioning/efficiency analysis; do not infer parameter efficiency. |
| Sparse graph computation | Chebyshev recurrence gives sparse compatibility | Sparse recurrence exists, but materializes the full basis and rebuilds a Laplacian per layer in normal `forward` | One sparse-versus-dense path case | **suggestive only** | Add locality/SpMV proposition, streaming/Clenshaw implementation, graph-family tests, and compute accounting. |
| Controlled sphere improvements | No generalization theorem | Exact spectral objective runner | Aggregate summary and only `sphere_best_run.npz` | **suggestive only** | The main figure explicitly shows the **best of five**. Preserve per-seed artifacts and use a prespecified or median run. |
| Legacy H100 benchmark scale | Not theory-bearing | Uses legacy GBDN+ and local baseline implementations, not canonical Tight/Product-sum GBDN | 60 heterophily and 2 LRGB reruns | **empirically supported only as execution diagnostics** | Keep out of contribution/superiority claims. |
| Heterophily superiority | None | Official confirmatory pipeline absent | One split, one seed, unverified baselines | **unsupported / remove** | No comparative claim permitted. |
| Oversmoothing resistance | Exact complete-map isometry does not control the carried state or nonlinear representations | No dedicated instrumentation/results | None | **unsupported** | Do not claim. Test complete coefficients and carried state separately. |
| Oversquashing or long-range mitigation | No target-sensitivity theorem | No dedicated tasks | None | **unsupported / false if inferred from isometry** | Do not claim. Finite-degree sparse filters have zero influence beyond their receptive field; even a nodewise unitary map can be isometric while cross-node sensitivity is zero. |
| Movable-pole novelty over Cayley/filter-bank work | Verbal distinction only | Roots do induce movable mapped poles | No theorem or matched comparison | **suggestive only** | Require complete prior-work audit, explicit graph-filter-bank/QMF comparison, movable-pole separation result, and Gate C. |

## Stop-line findings

| Severity | Finding and evidence | Required resolution |
|---|---|---|
| **BLOCKER** | **The active scientific object is not versioned.** `src/gbdn/*`, `tests/test_gate_a.py`, `papers/revision/*`, `artifacts/mechanism_v1/*`, figures, and plans are ignored/untracked at `fcfa841...`. The public history contains only the legacy H100 workflow/results. | Put canonical code, tests, manuscript source, configs, and regenerable aggregate assets under an intentional anonymized commit. Record source and dirty-tree hashes in every artifact. |
| **BLOCKER** | **Gate A has not passed the stated contract.** Although 20 tests pass, `test_gate_a.py` contains 10 tests (not the manuscript’s stated nine), and the required suite lacks pointwise multilevel partition, weighted Parseval, additive reconstruction, exact conditioning/singular values, permutation equivariance, repeated-eigenvalue behavior, weighted/disconnected graph families, admissible nonzero product-sum roots, graph perturbation, multilevel finite-order frame distortion, gradient checks, and lazy-parameter checks. Some current tests are tautological or use a single-signal error as if it were an operator norm. | Replace the test-count claim with generated evidence and implement the full independent contract over the prescribed graph families/depths. Reviewer must re-audit before experiments. |
| **BLOCKER** | **Exact/approximate/legacy object switching remains possible.** Exact theorems concern `B_R(c(L))`; canonical models use finite Chebyshev factors; the H100 table uses legacy GBDN+ with inverse/conjugated coefficients, an incorrect zeroth-coefficient convention, Cartesian root clipping that can violate `|alpha|<1`, and node-count-only caches. | Give every table/artifact an explicit variant and realization tag. Never use legacy GBDN+ to support Tight GBDN theory or canonical performance. |
| **BLOCKER** | **Central mechanism evidence lacks run-level provenance and uses post hoc selection.** Only aggregates and the best complex run are saved; no complete per-initialization results, immutable run IDs, commit/environment manifest, runtime, or paper-generated trace exists. `--overwrite` deletes the artifact directory. | Re-run cheaply under the submission schema, retain all seeds, declare the displayed run before inspection (or use median), and generate the figure/table from aggregate files. |
| **BLOCKER** | **Legacy H100 verification fails.** The verifier reports 28 issues; GBDN+ Roman accuracy drifts by `0.296329`, GBDN+ Roman AUROC by `0.164991`, and H2GCN Minesweeper AUROC by `0.035276`; `results_repro/run_manifest.json` is absent. | Treat all rows as frozen diagnostics only. Do not tune or build claims from them. |
| **BLOCKER** | **Official confirmatory infrastructure is absent.** `notebooks/gbdn_submission_h100.ipynb`, submission CLI, immutable schema/verifier, frozen configs, prediction-level aggregator, generated LaTeX, depth/oversquashing runners, and canonical graph-level pipeline do not exist. | Implement and smoke-test the specified staged pipeline before full H100 use. |
| **MAJOR** | **Legacy protocols and baselines are scientifically inadmissible.** All heterophily runs use split 0/seed 25 and validation AUROC, including multiclass datasets whose official selection metric is accuracy. All tasks use cross-entropy/two-class softmax rather than the prescribed binary-logit/BCE contract. Local named baselines are unverified; H2GCN creates `final_project` after optimizer construction, so that layer is not trained. | Use official tasks/metrics, 10 splits x >=3 seeds, equal validation-only budgets, upstream-verified baselines, and paired split-level inference. |
| **MAJOR** | **Saved metrics are not independently stable.** All 60 heterophily artifacts contain predictions, but the legacy AUROC implementation is not tie-aware; at tolerance `1e-4`, 17 archived/reproduced scalars differ from tie-aware recomputation, with maximum observed difference about `0.00369`. Paper table values are manually transcribed and no committed generator records the recomputation. LRGB artifacts contain no predictions. | Store official metric version and predictions, recompute in an isolated aggregator, and reject drift. |
| **MAJOR** | **Novelty defense is incomplete.** Tightness/adjoint reconstruction arise generically from splitting any unitary operator. Related work omits or does not resolve graph-QMF/filter banks/framelets, BernNet, GPR-GNN, UniFilter, SLOG, HeroFilter, Unitary Convolutions, and other matrix-listed comparators. CayleyNet distinction is verbal, not proven or experimentally matched. | Center novelty only on the strongest defensible movable-pole phase parameterization after literature, theorem, and matched-budget audits. |
| **MAJOR** | **Statistical reporting is insufficient for the central mechanism result.** `n=5` SDs do not show paired effects, intervals, robustness, or the raw distribution; the best-run visualization encourages selection bias. The checklist’s blanket “Yes” on statistical significance is too strong. | Report paired per-seed differences/effect sizes and uncertainty; show all seeds or a prespecified representative. Re-audit checklist answers. |
| **MAJOR** | **Anonymity/release risk.** The source contains `\author{Lorenzo Simone}` although the compiled PDF displays anonymous authors; the remote URL is identifying. | Build the submission from an anonymized clean tree and verify source, PDF metadata, supplementary files, and URLs. |
| **MINOR** | Current local environment (Python 3.12, CPU Torch 2.13, NumPy 2.5.1) differs from the lock (Python 3.11, Torch 2.11, NumPy 2.3.5) and H100 artifacts (Python 3.10, NumPy 2.2.6). No package metadata exists. | Freeze one supported environment and record lock hashes; test a clean install. |
| **EDITORIAL** | “20 tests, including nine mathematical and 11 compatibility tests” conflicts with collection (10 plus 10). Matrix signals use `||.||_2` despite declaring Frobenius norms. | Generate counts and use `||.||_F` consistently. |

## Protocol and statistics admission decision

The current H100 results fail confirmatory admission: one split and seed; no equal validation-only search; wrong checkpoint metric for Roman-empire/Amazon-ratings; unverified local baseline names; no split-level primary unit; no paired inference, multiplicity correction, effect sizes, or win/tie/loss; incomplete compute; and no source/dataset/checkpoint trace. Peptides-func additionally discards edge information in the simplified wrapper, uses a non-official weighted AP aggregation, and saves no predictions. The paper is appropriately cautious in several sentences, but merely labeling an invalid comparison “preliminary” does not make named boldface baseline tables scientifically useful. Remove them from the main submission unless they serve a narrowly defined artifact case study.

## What may proceed now

May proceed in parallel:

- Math: independent proof/counterexample audit, exact norm notation, weighted Parseval/conditioning, finite-order multilevel bound, locality, perturbation, and oversquashing boundary.
- Engineering: isolate legacy code, implement the independent dense oracle and complete contract tests, align coefficient ordering, build run identity/schema/verifier/CLI/notebook, and verify baselines.
- Reviewer: complete prior-work and baseline-license audit without viewing favorable author interpretations.
- Paper: only narrowing, labeling, anonymization, and provenance scaffolding; no new superiority language.

Blocked by dependencies:

- Gate B claim-bearing mechanism studies until Gate A and immutable run artifacts pass.
- Gate C until external baselines are verified and budgets are frozen.
- Full heterophily confirmation until official task contracts, baseline registry, tuning freeze, and H100 smoke/resume tests pass.
- Oversmoothing/oversquashing conclusions until dedicated instrumentation, experiments, and mathematical boundaries exist.
- LRGB claims until an official graph-level pipeline saves predictions and uses official evaluation.

## Phase-0 reviewer verdict

The strongest currently defensible paper identity is a **foundational exact movable-pole paraunitary graph spectral construction with limited controlled evidence**. It is not yet a defensible NeurIPS empirical submission. Preserve the correct exact statements, explicitly separate exact/canonical-finite/legacy-relaxed objects, and reject any inference from energy conservation to oversquashing or long-range transmission. Re-review is required after the complete Gate-A contract and provenance chain pass.
