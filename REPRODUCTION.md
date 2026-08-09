# Reproducing the GBDN legacy benchmark

This repository reproduces the 60 heterophily JSON artifacts in `results/`
and the two Peptides-func artifacts in `results_LRGB/`. It preserves the
single-seed, split-0 protocol ported from cells 23 and 28 of the original
experiment notebook. It is not the later multi-seed development benchmark.

## Fresh H100 host

Requirements: Linux, Python 3.11, one accessible NVIDIA H100, `nvidia-smi`,
internet access, and enough persistent disk for downloaded PyG datasets.

```bash
git clone https://github.com/lorenzosimone25/GBDN.git
cd GBDN
bash scripts/setup_h100.sh
bash scripts/run_h100.sh smoke
bash scripts/run_h100.sh run-all --workers auto
bash scripts/run_h100.sh report
bash scripts/run_h100.sh verify
```

Set `GPU_INDEX` only when the H100 is not physical index 0. The setup defaults
to the pinned CUDA 12.8 PyTorch wheel; override `TORCH_INDEX_URL` only when the
host driver requires another official wheel index for the same Torch version.

## Outputs and resumption

- Heterophily results: `results_repro/<dataset>/<model>.json`
- Peptides-func results: `results_LRGB_repro/<model>.json`
- Run manifest: `results_repro/run_manifest.json`
- Comparison report: `reproduction_report.md`
- Local logs and failure records: `reproduction_logs/` and
  `reproduction_failures/` (ignored by Git)

Each model is an isolated process and visits the five datasets in the original
order. RNG checkpoints under ignored `reproduction_state/` make interrupted
runs resumable without changing that sequence. Existing matching artifacts are
skipped; a different run identity is never replaced unless `--rerun` is passed.

Training remains deterministic FP32 with TF32, mixed precision, and compilation
disabled. `verify` requires all 62 artifacts, validates stored predictions,
checks provenance, and rejects absolute metric drift above 0.02.
