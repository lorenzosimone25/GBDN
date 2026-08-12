# Submission Readiness Checklist

A submission decision is `GO` only when every blocker item is checked. A waiver requires a written decision, reviewer approval, and explicit paper limitation.

## A. Scientific identity

- [ ] One canonical definition of Tight GBDN appears in paper and code.
- [ ] Product-sum GBDN and GBDN+ are separated.
- [ ] The paper does not claim direct classical phase unwinding on graphs.
- [ ] The novelty over CayleyNets, graph filter banks, and unitary convolutions is precise.
- [ ] Additive reconstruction and adjoint synthesis are distinguished.
- [ ] Exact and finite-order operators are distinguished everywhere.
- [ ] Non-dissipativity names the exact object and norm.
- [ ] Heterophily, oversmoothing, oversquashing, and long range are not conflated.

## B. Mathematics

- [ ] Every theorem has complete assumptions.
- [ ] Every theorem has a complete proof.
- [ ] Every theorem was independently checked.
- [ ] Counterexamples outside assumptions are documented.
- [ ] Pointwise partition theorem is accepted or removed.
- [ ] Weighted Parseval theorem is accepted or removed.
- [ ] Conditioning/anti-collapse claim is correctly scoped.
- [ ] Oversquashing claim boundary includes target-specific limitations.
- [ ] Finite-order multilevel bound is accepted and measured.
- [ ] Pole localization/approximation relation is correct.
- [ ] Cayley separation claim is correct and non-overstated.
- [ ] Perturbation-stability claim is accepted, narrowed, or removed.
- [ ] Locality and SpMV complexity are correct.
- [ ] Repeated-eigenvalue limitations are stated.

## C. Implementation

- [ ] Legacy artifacts are frozen.
- [ ] Canonical package matches paper equations.
- [ ] Root modulus is enforced jointly.
- [ ] Blaschke denominator conjugation is correct.
- [ ] Transform direction is tested against an independent oracle.
- [ ] Chebyshev zeroth coefficient is correct.
- [ ] Sparse realization is streaming or memory-accounted.
- [ ] Graph operators are not cached by node count alone.
- [ ] No parameter is created after optimizer construction.
- [ ] Tight analysis and adjoint synthesis are implemented.
- [ ] All mathematical contract tests pass.
- [ ] Permutation, graph-identity, and repeated-spectrum tests pass.
- [ ] Exact-versus-sparse tolerances are reported.

## D. H100 notebook

- [ ] New notebook is separate from legacy reproduction.
- [ ] GPU visibility is set before PyTorch import.
- [ ] Notebook is an operator UI, not duplicate implementation.
- [ ] Default execution is sequential and subprocess-isolated.
- [ ] Dry-run inventory works.
- [ ] Smoke test works.
- [ ] Interrupted run resumes.
- [ ] Conflicting run identity cannot overwrite.
- [ ] Independent failures do not cancel all jobs.
- [ ] Final verification fails on missing artifacts.
- [ ] Predictions independently reproduce saved metrics.
- [ ] Complete report and generated paper assets are produced.

## E. Heterophily benchmark

- [ ] All five replacement datasets use official files.
- [ ] All official split masks are used.
- [ ] Roman-empire and Amazon-ratings use accuracy.
- [ ] Minesweeper, Tolokers, and Questions use ROC-AUC.
- [ ] Binary tasks use binary loss/output.
- [ ] At least three seeds per split are complete.
- [ ] Configurations were frozen before confirmatory test execution.
- [ ] Test metrics did not influence selection.
- [ ] Primary baselines are upstream-verified.
- [ ] Tuning budgets are equal or clearly labeled.
- [ ] Every primary run saves predictions.
- [ ] Split-level confidence intervals are reported.
- [ ] Paired tests and multiplicity correction are reported.
- [ ] Compute, memory, parameters, and SpMVs are reported.

## F. Mechanism and approximation

- [ ] Exact contract sweep is complete.
- [ ] Phase-sensitive recovery uses sufficient initializations.
- [ ] Main figure is not best-of-seed.
- [ ] Pole-distance prediction is compared with measured error.
- [ ] Matched response-efficiency includes strong alternatives.
- [ ] Parameter and SpMV matching are both reported.
- [ ] Negative mechanism results are retained.

## G. Depth and oversmoothing

- [ ] Each depth is independently trained.
- [ ] Complete coefficients and carried state are both analyzed.
- [ ] Numerical/effective/stable rank are reported.
- [ ] Energy-only measures are not used as sole evidence.
- [ ] Linear-probe/class-separation results are reported.
- [ ] Strong stable/unitary baselines are included.
- [ ] Practical claims match the results.

## H. Oversquashing and long range

- [ ] Dedicated topology-controlled tasks are included.
- [ ] Source-to-target sensitivity is measured.
- [ ] Total sensitivity is reported separately.
- [ ] Distance and bottleneck width are varied.
- [ ] Topology and model-dynamics effects are discussed.
- [ ] No blanket “solves oversquashing” claim appears.
- [ ] LRGB claims use official evaluators and pipeline.

## I. Paper and figures

- [ ] Abstract contains no preliminary single-run claim.
- [ ] Introduction contribution list matches accepted evidence.
- [ ] Method equations match code.
- [ ] Main theory focuses on nontrivial results.
- [ ] Legacy table is removed or clearly appendix-only.
- [ ] Every main result has uncertainty.
- [ ] Every figure is generated.
- [ ] Every table is generated.
- [ ] No number is manually copied after result freeze.
- [ ] Figure captions state run-selection and uncertainty policy.
- [ ] Limitations include memory, finite order, scalar-Laplacian scope, and target-specific oversquashing.

## J. Reproducibility and assets

- [ ] Clean installation instructions exist.
- [ ] Exact commands and notebook path exist.
- [ ] Source and dataset hashes are recorded.
- [ ] Full run manifest exists.
- [ ] Per-run and total compute are reported.
- [ ] Baseline repositories, commits, and licenses are recorded.
- [ ] Dataset versions and licenses are recorded.
- [ ] New code has a license.
- [ ] Anonymous release does not reveal authorship.
- [ ] Generated assets are documented.
- [ ] Final archive passes verification from a clean environment.

## K. Final red-team

- [ ] Theory-heavy simulated review has no blocker.
- [ ] Empirical simulated review has no blocker.
- [ ] All major issues are resolved or explicitly narrowed.
- [ ] Paper PDF builds from the frozen commit.
- [ ] Reproduction archive matches the frozen commit.
- [ ] Final verification reports `PASS`.
- [ ] Final paper and code SHAs are recorded.

## No-go conditions

The submission is automatically `NO-GO` when any of the following remains:

- false or unverified central theorem;
- paper–code mismatch in Tight GBDN;
- primary table uses wrong official metric;
- primary comparison remains single-split or single-seed;
- test leakage;
- unverified primary baseline;
- metrics cannot be recomputed from predictions;
- notebook cannot resume safely;
- unsupported oversquashing/long-range headline;
- generated tables do not trace to immutable artifacts.
