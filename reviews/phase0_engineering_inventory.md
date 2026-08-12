# PH0-ENG-001 — Phase 0 engineering inventory

## Decision

**BLOCK claim-bearing execution.** The tracked repository reproduces only the preserved legacy H100 workflow. The revised canonical package, Gate A tests, manuscript, plans, and mechanism artifacts are excluded by the allowlist, so pulling the public commit cannot reproduce the intended method or paper.

## Object inventory

| Object | Current location | Classification | Engineering disposition |
|---|---|---|---|
| Preserved legacy implementation | `src/legacy_reproduction.py` and tracked reproduction scripts | Frozen provenance object | Keep executable and immutable; never use as the canonical definition. |
| Older local research code | `src/BlanshkeGraphNetwork.py`, `src/FastBlashkeGraphNetwork.py`, `src/Baselines.py` | Legacy/development | Isolate; known inadmissible roots, cache identity, conventions, and locally named baselines. |
| Revised implementation | `src/gbdn/` | Candidate canonical code | Directionally correct, but ignored, incomplete, and not commit-bound. |
| Gate A suite | `tests/test_gate_a.py` | Candidate theorem-contract tests | Ten tests pass; mandatory contracts and graph-family coverage are missing. |
| Legacy artifacts | `results/`, `results_LRGB/` | Frozen legacy | Diagnostic only; original provenance is incomplete. |
| H100 reproduction artifacts | `results_repro/`, `results_LRGB_repro/` | Frozen legacy reproduction | Diagnostic only; verifier fails and manifest is absent. |
| Mechanism artifacts | `artifacts/mechanism_v1/` | Development evidence | Aggregate plus selected best run; not immutable per initialization. |
| Submission pipeline | required CLI/schema/notebook/generated files | Absent | Must exist and pass smoke/resume/identity verification before H100 confirmation. |

## Critical hazards

1. `.gitignore` excludes the canonical source, paper, tests, plans, and scientific artifacts. Clean H100 pulls cannot recover the active scientific object.
2. Legacy roots use independent Cartesian clipping and can leave the unit disk; legacy caches identify a graph only by node count; legacy coefficient/conjugation conventions differ from the paper.
3. The legacy H2GCN path can create `final_project` after optimizer construction, leaving trainable parameters outside the optimizer.
4. The development benchmark uses two-logit cross-entropy and a universal AUROC path, inspects the test set each epoch, uses a tie-unsafe local AUROC routine, pools runs as independent units, and writes into the frozen `results/` namespace.
5. Local baseline names are not verified against upstream implementations. Only clean reference checkouts for ChebNetII, Stable-ChebNet, and WaveGC are pinned; isolated official runners and license resolution remain open. CayleyNet is unverified.
6. `results_repro/run_manifest.json` is missing; the strict verifier reports 28 failures. Simplified LRGB artifacts contain no predictions.
7. `paper/generated/`, the immutable submission schema/verifier, frozen experiment plan, canonical runner, and `notebooks/gbdn_submission_h100.ipynb` are absent.
8. The canonical sparse recurrence materializes every Chebyshev basis vector, repeatedly rebuilds Laplacians in ordinary layer calls, has no canonical graph-level predictor, and lacks full runtime/memory/SpMV accounting.
9. The canonical Laplacian helper documents a symmetric Laplacian but neither validates nor symmetrizes its input. This must fail loudly or construct an explicitly undirected weighted graph before exact claims are exercised.

## Positive findings

- The candidate canonical code uses a joint radial root parameterization and the conjugated Blaschke denominator.
- Exact spectral helpers provide a useful dense reference path.
- Tight, Product-sum, and relaxed variants are separated in the model package.
- The current full repository suite passes 20 tests, including useful regression checks for legacy immutability/resumption.
- Frozen result collections are intact and their aggregate hashes are recorded in `results_submission/reports/phase_0_manifest.json`.

## Required dependency order

1. Intentionally track the canonical source/tests/paper/plans while retaining frozen legacy paths.
2. Enforce the graph/operator contract and freeze coefficient ordering, conventions, variants, and exact-versus-finite tags.
3. Build an independent dense oracle and complete the theorem-contract suite, including true operator norms.
4. Obtain independent Gate A review.
5. Build immutable run identity, artifact schema, verifier, submission CLI, and single H100 operator notebook.
6. Smoke-test task-specific official protocols and upstream baselines before any tuning or confirmation.

No H100 benchmark, mechanism figure, or paper table may be promoted while steps 1–4 remain open.
