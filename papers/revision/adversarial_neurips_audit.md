# Adversarial NeurIPS audit

Audit date: 2026-07-16. This audit applies to the separate revision, not the
preserved baseline draft.

## Readiness assessment

The package is a mathematically coherent, reproducible theory-and-mechanism
revision, but it is not yet a competitive NeurIPS submission because Gate C and
all downstream benchmark evidence remain incomplete.

## High: submission blockers

### H1. The central empirical comparison is unfinished

- **Files:** `sections/05_experiments.tex`, `claim_evidence_matrix.md`
- **Problem:** The paper has one controlled sphere response family and no
  matched comparison against verified CayleyNet, ChebNetII, Stable-ChebNet, or
  WaveGC implementations.
- **Why it matters:** A reviewer can accept the exact filter-bank algebra yet
  still judge the learned parameterization insufficiently motivated.
- **Minimum safe fix:** Complete repeated response-fitting experiments across
  low/high/band/notch/multiband/localized families at matched trainable
  parameters and sparse matrix-vector products. Retain an efficiency claim only
  if it survives family- and seed-level uncertainty.

### H2. No downstream learning result is admissible

- **Files:** `benchmark_protocol.md`, `scripts/run_benchmarks.py`
- **Problem:** The official heterophily and graph-level LRGB protocols are
  specified but have not been run. Existing JSONs are explicitly preliminary.
- **Why it matters:** NeurIPS reviewers normally expect evidence that the new
  inductive bias matters beyond fitting a hand-designed spectral response.
- **Minimum safe fix:** Run official splits and metrics with at least three
  seeds per split, equal HPO trials, verified baselines, parameter/cost matching,
  and confidence intervals. Do not add LRGB until its separate graph-level
  evaluator passes an upstream parity check.

### H3. External-baseline admission is incomplete

- **Files:** `research/baseline_registry.md`
- **Problem:** Three official repositories are pinned, but their isolated
  runners have not passed parity tests; no official CayleyNet implementation has
  been verified. Licensing is absent or unclear in the pinned repositories.
- **Why it matters:** Reimplementations can change both accuracy and cost, and
  unlicensed source cannot safely be copied into this project.
- **Minimum safe fix:** Execute pinned upstream entry points in isolated
  environments, archive their resolved configurations and predictions, and
  compare against reported reference metrics. Report CayleyNet as missing until
  an implementation is provenance-verified.

## Medium: credibility and reader-friction risks

### M1. Reconstruction is of the lifted feature, not necessarily the raw input

- **Files:** `sections/03_method.tex`, `sections/04_theory.tex`
- **Problem:** The exact adjoint reconstructs `h_0`, after the learned complex
  lift. The lift itself is not claimed to be invertible.
- **Why it matters:** “Perfect reconstruction” can be misread as recovery of the
  original real feature matrix.
- **Minimum safe fix:** Preserve “perfect reconstruction of the analyzed/lifted
  signal” everywhere and add one sentence in Methods before submission.

### M2. Exact and finite-order models require continued visual separation

- **Files:** `sections/03_method.tex`, `sections/04_theory.tex`,
  `sections/05_experiments.tex`
- **Problem:** Exact theorems concern spectral functional calculus; deployed
  layers use finite Chebyshev order and only approximate the frame.
- **Why it matters:** Reviewers may otherwise interpret exact perfect
  reconstruction as a property of every finite-order trained network.
- **Minimum safe fix:** Every empirical table must report frame and synthesis
  error beside task metrics and identify exact versus finite-order evaluation.

### M3. Citation provenance has one unresolved archival record

- **Files:** `citation_audit.md`, `refs.bib`
- **Problem:** Stable-ChebNet is conservatively cited as arXiv because a final
  proceedings record was not confirmed in the audit.
- **Why it matters:** Minor alone, but copied venue claims would undermine the
  otherwise strict bibliography repair.
- **Minimum safe fix:** Recheck the final proceedings metadata immediately
  before submission.

### M4. The current PDF is a revision artifact, not the venue package

- **Files:** `main.tex`, `main.pdf`
- **Problem:** The manuscript uses a generic two-column article class and has not
  been transferred to the final NeurIPS style/checklist.
- **Why it matters:** Page budgeting, float placement, anonymity, and checklist
  compliance can change under the venue template.
- **Minimum safe fix:** Move the evidence-complete text into the official
  template, then repeat log and nine-page visual inspection.

## Low: final consistency checks

- Add explicit `\cref` calls to both mechanism figures in the experiment prose;
  their captions and panels are correct, but the text currently relies on float
  proximity.
- Preserve the three canonical names exactly: Tight GBDN, Product-sum GBDN, and
  GBDN+.
- Keep `GBDNStrict` out of every script, figure, and paper artifact.
- Replace “the section will be finalized” in Related Work once no further
  citations are pending.
- Add code/data availability, hardware accounting, and an HPO search-space
  appendix with the completed benchmarks.

## Reviewer-side rejection forecast

- **Contribution sufficiency:** promising if matched response efficiency holds;
  otherwise position as an interpretable reconstructing filter-bank result.
- **Clarity and soundness:** currently strong for the exact linear construction.
- **Empirical strength:** currently weak and submission-blocking.
- **Reproducibility:** strong for correctness/mechanism artifacts; incomplete for
  external baselines and benchmarks.
- **Likely current score:** reject/weak reject despite sound theory, primarily for
  incomplete comparative and downstream evidence.

**Top remaining risk:** the learned-root parameterization may not outperform
polynomial, fixed-rational, or wavelet alternatives at matched cost.

**Next highest-leverage fix:** finish the multi-family matched response study
before spending multi-GPU budget on downstream benchmarks.

