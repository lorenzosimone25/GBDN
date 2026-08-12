# Legacy and canonical repository boundary

This map is normative for repository layout and output isolation. It does not
promote any Phase 0 result to claim-bearing evidence.

| Object | Path | Status | Allowed use |
|---|---|---|---|
| Preserved implementation | `src/legacy_reproduction.py` | Frozen legacy | Reproduce and audit the historical H100 workflow only. |
| Preserved operator notebook | `notebooks/reproduce_legacy.ipynb` | Frozen legacy | Reproduce archived diagnostic runs only. |
| Preserved runners | `scripts/reproduce_legacy.py`, `scripts/run_h100.sh`, `scripts/setup_h100.sh` | Frozen legacy | Legacy reproduction only. |
| Archived result trees | `results/`, `results_repro/`, `results_LRGB/`, `results_LRGB_repro/` | Frozen diagnostic artifacts | Read and verify; canonical code must never write here. |
| Scientific implementation | `src/gbdn/` | Canonical | Define exact, Chebyshev, and relaxed variants using explicit realization tags. |
| Scientific tests | `tests/` | Canonical plus legacy regression | Gate contracts and repository-boundary enforcement. |
| Experiment inputs | `configs/` | Canonical | Frozen plans and configuration registries; no output artifacts. |
| Submission runner | `scripts/` except the named legacy files | Canonical | Thin entry points over reusable canonical modules. |
| Operator notebook | `notebooks/gbdn_submission_h100.ipynb` | Canonical | Orchestration only; no scientific implementation. |
| Raw submission artifacts | `results_submission/` except `reports/` | Canonical, local/H100 | Immutable run outputs; ignored by Git by default. |
| Compact submission reports | `results_submission/reports/` | Canonical | Reviewed manifests and summaries that are safe to version. |
| Generated paper inputs | `paper/generated/` | Canonical, generated | Regenerable LaTeX and compact figure data; never hand edit. |
| Active manuscript source | `papers/revision/` | Canonical | Track source and bibliography, not PDFs or LaTeX build debris. |
| Scientific governance | `sub_plans/`, `reviews/`, `math/`, `handoffs/`, `research-state.yaml`, `research-log.md` | Canonical provenance | Contracts, audits, decisions, and handoffs. |

## Write policy

Canonical run writers must resolve their destination through
`gbdn.provenance.canonical_output_path` (or use
`write_new_canonical_artifact`). The guard accepts only descendants of
`results_submission/` and rejects the repository root, sibling-prefix paths,
paths outside the repository, and every frozen legacy result tree.

`write_new_canonical_artifact` uses exclusive creation. Repeating a run may
resume by reading a valid existing artifact, but it cannot overwrite a file
under the same identity. A changed configuration must receive a different run
identity and therefore a different output path.

This is an application boundary, not an operating-system permission scheme.
Arbitrary code can still modify tracked files, so review must reject any patch
that changes frozen legacy artifacts unless an explicit provenance task
authorizes that exact change.

## Git policy

The root `.gitignore` remains an allowlist. It admits canonical source,
contracts, tests, manuscript source, scaffolds, and compact reports while
excluding caches, compiled PDFs, data, checkpoints, raw predictions, and new
files beneath the frozen diagnostic trees. Files already tracked by Git are
not made immutable by ignore rules; the runtime guard and review boundary are
therefore both required.
