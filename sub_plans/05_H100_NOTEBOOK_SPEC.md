# H100 Submission Notebook Specification

## Required notebook

```text
notebooks/gbdn_submission_h100.ipynb
```

The existing legacy reproduction notebook remains frozen.

## Purpose

The new notebook is the **operator interface for the complete submission experiment program**. It launches reusable source/CLI jobs successively on one selected H100, monitors them, resumes safely, aggregates artifacts, and produces the final report.

The notebook must not contain model definitions, metric implementations, or duplicated training loops.

## Design principles

1. **Sequential by default.** `MAX_WORKERS = 1`.
2. **Subprocess isolation.** Each long experiment job runs in a fresh process.
3. **Artifact-level resume.** Completed matching run identities are skipped.
4. **No silent overwrite.** A conflicting artifact requires `RERUN = True`.
5. **Continue independent jobs.** One failure does not erase or cancel unrelated jobs.
6. **Fail final verification.** Missing or invalid required artifacts produce a nonzero final status.
7. **Predictions are mandatory.** Primary metrics are recomputed independently.
8. **No test-set selection.** The notebook enforces phase separation between tuning and confirmation.
9. **No manual result transcription.** Tables and figures are generated.

## Notebook modes

```python
MODE = "smoke"       # smoke | pilot | full | render-only | verify-only
RUN_PHASES = [
    "preflight",
    "contract",
    "mechanism",
    "filter-efficiency",
    "heterophily-tune",
    "heterophily-confirm",
    "depth",
    "oversquashing",
    "lrgb",
    "aggregate",
    "render",
    "verify",
]
RERUN = False
CONTINUE_ON_ERROR = True
MAX_WORKERS = 1
```

Defaults:

```python
OFFICIAL_SPLITS = list(range(10))
TRAINING_SEEDS = [0, 1, 2]
TUNING_SEEDS = [0]
```

The orchestrator may freeze different seeds before the full run, but the notebook must record them in the manifest.

## Cell-by-cell contract

### Cell 0 — Human-readable run contract

Markdown only:

- purpose;
- current mode;
- frozen commit;
- output root;
- warning not to overwrite legacy results;
- expected phases;
- how to resume.

### Cell 1 — GPU isolation before PyTorch import

This cell must run before any import that transitively loads CUDA.

Actions:

1. call `nvidia-smi -L`;
2. choose an explicit physical H100 index;
3. set:
   ```python
   CUDA_DEVICE_ORDER=PCI_BUS_ID
   CUDA_VISIBLE_DEVICES=<one index>
   PYTHONHASHSEED=<frozen>
   CUBLAS_WORKSPACE_CONFIG=:4096:8
   ```
4. fail if zero or multiple devices are visible after import;
5. fail if the selected device is not an H100 unless an explicit development override is enabled.

### Cell 2 — Repository and path resolution

Resolve:

```python
ROOT
CONFIG_ROOT
OUTPUT_ROOT = ROOT / "results_submission"
RAW_ROOT
AGGREGATE_ROOT
REPORT_ROOT
LOG_ROOT
STATE_ROOT
PAPER_GENERATED_ROOT
```

Verify the expected source and CLI files exist.

### Cell 3 — Environment and source manifest

Record:

- Python;
- OS;
- PyTorch;
- PyG/DGL as applicable;
- CUDA;
- driver;
- GPU model and memory;
- package lock hash;
- repository commit;
- dirty working-tree status;
- source-tree hash;
- notebook hash;
- timestamp.

A full run should refuse a dirty tree unless `ALLOW_DIRTY = True`, which must be recorded prominently.

### Cell 4 — Frozen experiment configuration

Display and save:

- model registry;
- baseline verification status;
- datasets;
- splits;
- seeds;
- hyperparameter policy;
- trial budget;
- depth values;
- approximation degrees;
- root counts;
- run phases;
- required versus optional jobs.

Write:

```text
results_submission/run_plan.json
results_submission/run_plan.md
```

### Cell 5 — Dry-run inventory

Call:

```bash
python scripts/run_submission.py <phase> --dry-run
```

Collect the exact job count, estimated parameters, and known prior runtimes.

Display:

- required jobs;
- completed matching jobs;
- pending jobs;
- invalid/conflicting jobs;
- estimated time;
- estimated storage.

No GPU training occurs.

### Cell 6 — Smoke tests

In `smoke` or larger modes:

- import package;
- run unit tests;
- run one exact small-graph contract;
- run one sparse approximate contract;
- run one tiny heterophily job;
- interrupt/resume test using a temporary output root;
- recompute the saved metric from predictions.

Stop all later phases if smoke fails.

### Cell 7 — Gate A: mathematical contract

Launch the full contract suite and generate:

```text
aggregate/contract_metrics.csv
reports/contract_report.md
```

Show:

- exact factor unitarity;
- pointwise partition;
- multilevel energy error;
- weighted energy error;
- additive reconstruction;
- adjoint reconstruction;
- sparse approximation error;
- predicted and observed frame defect;
- graph identity and equivariance status.

### Cell 8 — Gate B: mechanism studies

Launch all prespecified initializations for:

- magnitude-only fitting;
- complex-response fitting;
- root/pole trajectories;
- sphere or point-cloud components;
- median/prespecified visualization run.

Do not select the best run for the main figure.

### Cell 9 — Gate C: response-efficiency study

Run matched parameter and sparse-operation budgets across the frozen method set.

Write:

- error versus parameters;
- error versus SpMVs;
- error versus time;
- error versus memory;
- approximation degree and pole margin.

### Cell 10 — Heterophily tuning

Only when `MODE` permits.

Requirements:

- use training and validation masks only;
- enforce the same declared trial budget;
- write trial-level artifacts;
- select configurations using the official validation metric;
- freeze chosen configurations;
- create a freeze manifest.

The cell must not display or access confirmatory test metrics.

### Cell 11 — Heterophily confirmatory execution

The confirmatory cell loads only frozen configurations.

Run:

```text
all official splits × all frozen training seeds
```

for every required method–dataset pair.

Default execution is successive and subprocess-isolated. Show nested progress:

```text
method -> dataset -> split -> seed
```

Display validation metrics during execution. Test metrics may be written to artifacts but should not drive progress decisions or early termination.

### Cell 12 — Depth and oversmoothing

Run independently trained models at frozen depths, for example:

```python
DEPTHS = [1, 2, 4, 8, 16, 32, 64]
```

Collect complete coefficient and carried-state diagnostics.

### Cell 13 — Oversquashing and long-range

Run controlled graphs and dedicated tasks.

Collect:

- source-target sensitivity;
- total sensitivity;
- distance;
- bottleneck width;
- task accuracy;
- gradient/Jacobian summaries;
- topology statistics.

### Cell 14 — Optional LRGB

Run only verified official tasks and evaluators. The run plan labels LRGB jobs required or optional.

### Cell 15 — Independent aggregation

Call the aggregator in a fresh process.

It must:

1. validate artifact schemas;
2. recompute metrics from predictions;
3. average seeds within split;
4. compute split-level confidence intervals;
5. perform paired tests;
6. apply multiplicity correction;
7. compute win/tie/loss;
8. aggregate time and memory;
9. extract roots and poles;
10. emit CSV and LaTeX tables.

### Cell 16 — Figure rendering

Generate all paper figures from aggregate artifacts.

No figure reads ad hoc notebook variables.

### Cell 17 — Verification

Run:

```bash
python scripts/run_submission.py verify
```

Verification fails on:

- missing required jobs;
- duplicate run identities;
- conflicting configuration hashes;
- absent predictions;
- metric recomputation drift;
- missing baseline verification;
- wrong official metric;
- incomplete split–seed matrix;
- missing compute;
- missing source/dataset hash;
- hand-edited generated asset checksum mismatch;
- paper table numbers without aggregate source.

### Cell 18 — Final report

Render:

```text
results_submission/reports/submission_report.md
results_submission/reports/submission_report.html
```

The report contains:

- commit and environment;
- run completeness;
- mathematical contract;
- mechanism results;
- primary and secondary tables;
- paired statistics;
- depth and oversquashing results;
- compute;
- failures;
- excluded baselines;
- artifact links;
- exact commands to resume.

The last cell prints a single status:

```text
SUBMISSION PIPELINE: PASS
```

or

```text
SUBMISSION PIPELINE: FAIL
```

with blocker paths.

## Job execution model

Each job receives a deterministic run identity. The notebook should launch:

```bash
python scripts/run_submission.py run-job --job-id <ID>
```

or an equivalent public entry point.

Capture stdout and stderr under:

```text
results_submission/logs/<run_id>.log
```

A failed job writes a failure artifact with stack trace and environment.

## Resume behavior

A job is skipped only when:

- its result schema is valid;
- its identity matches the current run plan;
- required predictions exist and match hashes;
- metric recomputation passes;
- status is `complete`.

A partial or corrupt job is quarantined, never treated as complete.

## Progress and ETA

Use nested `tqdm` bars or an equivalent display. Estimate ETA from completed jobs in the same phase and model family. Mark estimates as provisional until enough jobs exist.

## Memory behavior

- clear Python references after each job;
- use subprocesses for GPU cleanup;
- record `torch.cuda.max_memory_allocated`;
- do not use `nvidia-smi` peak memory as the only measure;
- stream Chebyshev recurrences;
- avoid loading all predictions into memory during aggregation.

## Notebook acceptance tests

The notebook is accepted only when it demonstrates:

1. clean preflight;
2. safe GPU selection;
3. successful smoke;
4. interruption and resume;
5. conflicting-run protection;
6. continued execution after one synthetic failure;
7. independent metric recomputation;
8. generated report;
9. nonzero failure status when an artifact is deliberately removed.
