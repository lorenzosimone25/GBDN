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
- the full local suite currently passes 447 tests;
- final row-level provenance and independent Gate-A acceptance are still in
  progress; and
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

The canonical operator interface will be:

```text
scripts/run_submission.py
notebooks/gbdn_submission_h100.ipynb
```

Those interfaces are admitted only after immutable run identities, artifact
verification, and smoke/resume tests pass.  Until they are present, a clean
checkout intentionally cannot launch the new benchmark program.

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
