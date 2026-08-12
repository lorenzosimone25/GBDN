# GBDN: learned Blaschke--Cayley graph filter banks

This repository contains two deliberately separated workflows:

1. a frozen legacy GBDN+ reproduction retained for provenance; and
2. the canonical implementation and gated experiment system for the current
   Tight GBDN / Product-sum GBDN study.

The legacy single-seed results are diagnostics.  They are not evidence for the
current method and are not mixed with new submission artifacts.

## Canonical method

The current construction learns admissible roots of Blaschke all-pass factors
after a Cayley transform of a self-adjoint graph operator.  Complementary
half-sum and half-difference channels turn spectral phase into a redundant,
nonsubsampled analysis bank.  The canonical package distinguishes:

- `TightGBDN`: exact or finite-Chebyshev complementary analysis with explicit
  residual-first coefficients and reconstruction utilities;
- `ProductSumGBDN`: cumulative all-pass products with a learned complex sum;
- canonical relaxed `GBDN+`: an empirical relaxation without tightness or
  reconstruction claims; and
- Legacy GBDN+: the frozen historical implementation only.

Exact rational targets and finite Chebyshev realizations are different
scientific objects.  A finite realization is polynomial and has no literal
poles; reported mapped poles belong to its parameterized exact target.

## Current scientific gate

The repository is under a stop-line policy:

- all 36 prespecified Gate-A correctness IDs have executable coverage;
- the full local suite currently passes 640 tests, with one platform-specific
  symlink test skipped where Windows privileges are unavailable;
- the third independent review accepted 35/36 rows; its final public-tolerance
  finding is repaired and awaits a fourth independent adjudication; and
- no new claim-bearing H100 benchmark is authorized until that gate closes.

The active manuscript therefore labels existing mechanism studies and the
legacy H100 tables as diagnostics.  It makes no state-of-the-art,
anti-oversmoothing, oversquashing, or long-range claim.

## Clean checkout

Use Python 3.11.  On an H100 host, the pinned environment can be created with:

```bash
git clone https://github.com/lorenzosimone25/GBDN.git
cd GBDN
bash scripts/setup_h100.sh
```

That setup validates the GPU and runs the test suite.  The tracked
`scripts/run_h100.sh` command is explicitly the frozen legacy launcher.  Do not
use it for the current submission study.

The canonical Stage-1 operator interface now includes:

```text
python scripts/run_submission.py preflight
python scripts/run_submission.py smoke
```

These commands run exactly one CPU-only, synthetic, diagnostic job through an
isolated subprocess and the immutable artifact/resume path. They do not launch
official datasets, CUDA work, or claim-bearing experiments. The H100 operator
notebook and the broader submission phases remain absent and blocked pending
independent Gate-A acceptance and reviewed official task contracts.

The official five-dataset task/metadata registry is implemented, but its NPZ
checksums, redistribution records, adapters, test-isolated evaluator, verified
baseline registry, and full scheduler are intentionally unresolved. A passing
CPU smoke must not be interpreted as benchmark readiness.

## Legacy reproduction

The historical single-seed, split-0 workflow remains available unchanged:

```bash
bash scripts/run_h100.sh smoke
bash scripts/run_h100.sh run-all --workers auto
bash scripts/run_h100.sh report
bash scripts/run_h100.sh verify
```

It writes only to `results_repro/` and `results_LRGB_repro/`.  See
[`REPRODUCTION.md`](REPRODUCTION.md) for the frozen protocol and its known
limitations.

## Repository layout

```text
src/gbdn/                         canonical operators, models, diagnostics
tests/                            Gate-A and repository-boundary tests
math/                             theorem, proof, and counterexample ledgers
reviews/                          independent scientific audits
papers/revision/                  active anonymous manuscript source
paper/generated/                  regenerated paper inputs only
results_submission/              canonical immutable local/H100 artifacts
results_submission/reports/      compact reviewed reports safe to version
src/legacy_reproduction.py        frozen legacy implementation
scripts/reproduce_legacy.py       frozen legacy CLI
notebooks/reproduce_legacy.ipynb  frozen legacy operator notebook
sub_plans/                        scientific contracts and execution board
```

Canonical writers are restricted to `results_submission/` and must never
overwrite the frozen result trees.  See
[`docs/LEGACY_CANONICAL_BOUNDARY.md`](docs/LEGACY_CANONICAL_BOUNDARY.md) for the
normative write and Git policy.
