# H100 Operations Preflight

## Verdict

**STOP-LINE for H100 execution and claim-bearing experiments.** The repository has a sound immutable-artifact foundation, but it does not yet expose a complete, independently accepted submission runner. Stage-1 CPU infrastructure work may continue without generating benchmark claims.

## Foundations present

- Deterministic `RunIdentity` binding configuration to source and environment identity.
- Source and environment capture suitable for provenance checks.
- Atomic, write-once run bundles with integrity validation.
- Resume classification and explicit failure records.

These components support the future runner; they do not by themselves establish correct datasets, metrics, scheduling, or scientific validity.

## Required interfaces still missing

- `scripts/run_submission.py` as the sole non-notebook orchestration entry point.
- `notebooks/gbdn_submission_h100.ipynb` as a thin operator interface.
- Versioned configurations and a frozen experiment plan.
- Official dataset, split, task-loss, and evaluation-metric contracts.
- Isolated subprocess scheduling, resumable job enumeration, and failure isolation.
- Independent recomputation of metrics from saved predictions.
- Split-first aggregation, uncertainty, paired statistics, and multiplicity correction.
- A verified baseline registry with implementation/version provenance and matched budgets.
- Deterministic table/figure renderers tied to aggregate artifacts.
- A final fail-loud verifier for completeness, identity, integrity, and metric agreement.

## Dependency gates

Stage-1 CPU work may implement and test the missing orchestration interfaces using synthetic or smoke fixtures. No H100 job, Gate B/C run, confirmatory benchmark, or paper claim may proceed until:

1. Gate A receives independent acceptance;
2. a one-job smoke path completes through immutable write, resume, and metric-recomputation checks; and
3. the frozen plan and official task contracts are reviewed.

## Minimal H100-only public branch

Allow only files needed to install, test, execute, resume, verify, and aggregate the frozen experiments:

- `src/gbdn/**`
- `tests/**` limited to canonical operator, artifact, runner, and smoke-contract tests
- `scripts/setup_h100.sh`
- `scripts/run_submission.py`
- `notebooks/gbdn_submission_h100.ipynb`
- frozen `configs/**`
- `pyproject.toml`, `requirements.lock`, and a concise operator README

Exclude orchestration/audit plans, agent prompts and handoffs, manuscript sources and PDFs, generated manuscript material, AI-generated content, exploratory notebooks, legacy diagnostic outputs, credentials, caches, and raw result artifacts. Results should be transferred through the immutable artifact store or a separately reviewed release, not committed to the execution branch.

## Readiness decision

The next permissible milestone is a CPU-only submission-runner smoke test. H100 scheduling remains blocked.
