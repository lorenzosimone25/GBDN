# Results and Artifact Schema

## Principles

- immutable;
- self-describing;
- recomputable;
- hash-addressed;
- paper-traceable;
- safe to resume;
- explicit about failures.

## Directory layout

```text
results_submission/
    run_plan.json
    run_plan.md
    raw/
        <experiment>/
            <dataset>/
                <model>/
                    split=<id>/
                        seed=<id>/
                            trial=<id>/
                                result.json
                                predictions.npz
                                history.jsonl
                                diagnostics.npz
                                config.yaml
                                stdout.log
                                stderr.log
    state/
    failures/
    aggregate/
        run_index.parquet
        metrics.csv
        split_level_metrics.csv
        paired_tests.csv
        compute.csv
        roots_and_poles.csv
        contract_metrics.csv
    reports/
        phase_*.md
        submission_report.md
        verification_report.md
    figures/
```

For experiments without split or seed, use explicit sentinel values such as `split=na`, never omit identity fields.

## Run identity

Compute a deterministic hash from:

- schema version;
- experiment;
- dataset and checksum;
- model and variant;
- split;
- seed;
- trial;
- frozen config hash;
- source hash;
- dependency-lock hash;
- baseline upstream commit;
- precision mode.

A matching completed identity may be skipped. A different identity must not overwrite it.

## `result.json`

Recommended schema:

```json
{
  "schema_version": "1.0",
  "run_id": "sha256...",
  "status": "complete",
  "experiment": "heterophily_confirm",
  "dataset": {
    "name": "Roman-empire",
    "version": "...",
    "sha256": "...",
    "split_id": 0
  },
  "model": {
    "name": "TightGBDN",
    "variant": "tight",
    "source_commit": "...",
    "upstream_commit": null,
    "parameter_count": 0,
    "spmv_per_forward": 0
  },
  "randomness": {
    "seed": 0,
    "deterministic": true
  },
  "selection": {
    "policy": "frozen_validation",
    "metric": "accuracy",
    "best_epoch": 0,
    "config_hash": "..."
  },
  "metrics": {
    "train": {},
    "validation": {},
    "test": {}
  },
  "predictions": {
    "path": "predictions.npz",
    "sha256": "...",
    "format": "logits_and_labels"
  },
  "diagnostics": {
    "frame_error": null,
    "reconstruction_error": null,
    "roots": null,
    "mapped_poles": null,
    "effective_response_path": null
  },
  "compute": {
    "device": "NVIDIA H100 ...",
    "duration_seconds": 0.0,
    "peak_cuda_memory_bytes": 0,
    "epochs": 0,
    "optimizer_steps": 0
  },
  "environment": {
    "python": "...",
    "torch": "...",
    "cuda": "...",
    "lock_sha256": "..."
  },
  "created_at_utc": "..."
}
```

Use `null` only when a field is genuinely inapplicable, not when collection was forgotten.

## Predictions

Primary benchmark artifacts must save sufficient data to recompute the official metric:

### Multiclass

- test logits or probabilities;
- integer labels;
- node indices;
- split ID.

### Binary

- one-dimensional test scores/logits;
- binary labels;
- node indices;
- split ID.

### Multilabel graph tasks

- graph IDs;
- per-label scores;
- targets including missing-label mask;
- official aggregation metadata.

Predictions should be compressed but not rounded.

## Training history

`history.jsonl` contains one record per evaluation point:

```json
{
  "epoch": 10,
  "train_loss": 0.0,
  "validation_metric": 0.0,
  "learning_rate": 0.0,
  "elapsed_seconds": 0.0
}
```

Do not store test metrics at every epoch in confirmatory runs unless the evaluator is isolated and the values are never used. Prefer evaluating test only at the frozen selected checkpoint.

## GBDN diagnostics

For each trained GBDN variant, save:

- raw root parameters;
- admissible complex roots;
- frequency centers;
- mapped zeros and poles;
- pole margins;
- effective scalar responses on a fixed grid;
- responses on the empirical graph spectrum;
- Chebyshev coefficients;
- per-level coefficient energies;
- carried-path norm;
- frame and synthesis errors;
- approximation error estimate;
- actual SpMV count.

## Failure artifact

A failed job writes:

```json
{
  "schema_version": "1.0",
  "run_id": "...",
  "status": "failed",
  "exception_type": "...",
  "message": "...",
  "traceback_path": "...",
  "partial_artifacts": [],
  "environment": {},
  "created_at_utc": "..."
}
```

Failures are never represented by missing files alone.

## Baseline registry

Create:

```text
results_submission/baseline_registry.json
```

Each baseline record includes:

```json
{
  "name": "WaveGC",
  "paper": "...",
  "repository": "...",
  "commit": "...",
  "license": "...",
  "wrapper": "...",
  "protocols": ["heterophily", "lrgb"],
  "verification": {
    "status": "VERIFIED",
    "dataset": "...",
    "expected": 0.0,
    "observed": 0.0,
    "tolerance": 0.0
  }
}
```

## Aggregation

The aggregator creates one canonical run index. It must reject:

- duplicate identities;
- missing predictions;
- metric drift above tolerance;
- wrong metric names;
- invalid split or seed;
- unfrozen confirmatory configuration;
- primary baseline not verified;
- missing compute;
- test result produced during tuning.

## Statistical outputs

### `split_level_metrics.csv`

One row per method, dataset, split after averaging seeds.

### `paired_tests.csv`

Fields:

- dataset;
- method A;
- method B;
- mean paired difference;
- 95% interval;
- test statistic;
- raw \(p\);
- adjusted \(p\);
- win/tie/loss;
- number of splits;
- analysis policy.

### Confidence intervals

Record the exact procedure, resamples, random seed, and assumptions.

## Generated LaTeX

Each generated `.tex` file begins with comments:

```latex
% AUTO-GENERATED. DO NOT EDIT.
% source_commit: ...
% run_plan_hash: ...
% aggregate_hash: ...
% generated_at_utc: ...
```

The verifier hashes these files and fails when hand edits are detected.

## Paper traceability

Every table row and figure source must be recoverable from:

```text
paper asset -> aggregate file -> run IDs -> result artifacts -> predictions/config/source
```

The final report lists these links.

## Storage and cleanup

- never delete raw confirmatory artifacts before paper freeze;
- temporary tuning checkpoints may be pruned only after selected checkpoints and histories are validated;
- preserve failure artifacts;
- compress large diagnostic arrays;
- record any omitted prediction artifact and exclude it from confirmatory evidence.
