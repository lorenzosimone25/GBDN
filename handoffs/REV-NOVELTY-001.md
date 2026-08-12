# Agent Handoff — REV-NOVELTY-001

## Task

- **Task ID:** REV-NOVELTY-001
- **Agent:** Independent A* Reviewer / Adversarial Auditor
- **Branch:** `agent/reviewer/REV-NOVELTY-001`
- **Starting commit:** `8a41705e83e4629dbc49bb83bb815cc5770e116c`
- **Ending commit:** this handoff commit
- **Status proposed:** **BLOCKED** (audit complete; claim-bearing novelty language is blocked pending correction and Gate B/C evidence)

## Objective

Independently audit construction-level novelty against the mandatory primary-source
families; adjudicate CayleyNet's actual pole freedom; distinguish sampled graph-QMF
from the nonsubsampled GBDN stack; and identify the minimum comparator/evidence burden
without editing paper, source, tests, notebooks, or results.

## Summary

The audit finds a plausible but conditional contribution: independent generic
Blaschke pole geometry combined with complementary phase-to-amplitude channels and a
redundant exact coefficient isometry. No mandatory comparator audited here combines
all three. That bounded distinction is not enough by itself for an A* claim because
the Parseval/reconstruction result is automatic from unitarity and tight graph banks
and undecimated graph framelets are prior art.

The decisive correction is that CayleyNet trains its scale `h`; its poles are a
**learned restricted shared imaginary-axis locus**, not globally fixed. A narrow
continuum non-equivalence corollary remains available for an uncancelled GBDN
off-axis pole. Graph-QMF is critically sampled with down/up sampling and alias
cancellation, while GBDN's complete multilevel stack is redundant/nonsubsampled.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `reviews/novelty_primary_source_audit.md` | Adversarial verdict, comparator matrix, claim ledger, stop-line conditions. | Yes—review file only. |
| `results_submission/reports/novelty_source_manifest.md` | Primary URLs/DOIs/arXiv IDs, claim locators, repository provenance pins. | Yes—review evidence only. |
| `handoffs/REV-NOVELTY-001.md` | Task handoff and acceptance record. | Yes. |

No manuscript, source, test, notebook, raw result, or generated paper asset was
modified.

## Scientific impact

- **Claims enabled:** exact GBDN factors independently map admissible disk roots to
  generic lower-half-plane poles; under stated restrictions, an uncancelled off-axis
  exact pole cannot equal a scalar finite-order CayleyNet response on a continuum.
- **Claims narrowed:** construction novelty is the combination of free Blaschke pole
  geometry, complementary channels, and a nonsubsampled complete isometry; Parseval,
  weighted Parseval, and reconstruction are supporting guarantees; perturbation
  stability must be positioned as construction-specific.
- **Claims rejected:** first graph PR/tight/nonsubsampled bank; first rational,
  complex, adaptive, or non-polynomial graph filter; fixed-pole CayleyNet; finite
  Chebyshev implementation literally has poles; unitarity/tightness alone prevents
  oversmoothing or oversquashing.
- **Paper sections affected:** abstract, introduction/contributions, related work and
  comparison table, exact method/approximation boundary, theorem commentary,
  experiments, limitations, and conclusion.

## Evidence

### Proofs

- **Theorem/lemma:** CayleyNet restricted-locus lemma and exact scalar
  non-equivalence corollary.
- **Assumptions:** one scalar finite-order published Cayley response; `h>0`; effective
  order nonzero; uncancelled poles; equality on a real interval with an accumulation
  point; exact GBDN target; no inference to finite spectra or network compositions.
- **Proof location:** derivation and permitted corollary in
  `reviews/novelty_primary_source_audit.md`; source Eq. (3) locator in the manifest.
- **Counterexamples checked:** training `h` refutes a globally fixed-pole description;
  coefficient cancellations refute unconditional pole assertions; Cayley coefficients
  can induce zeros; finite-graph equality does not imply rational identity; finite
  Chebyshev polynomials have no literal finite poles; complete-map isometry does not
  imply carried-state non-dissipation.

### Tests

```text
command: git diff --check
result: PASS (no whitespace errors)

command: git status --short
result: PASS (only the three assigned deliverables staged before commit)

command: archival-source audit using the URLs and equation/section locators in
         results_submission/reports/novelty_source_manifest.md
result: PASS for mandatory primary-paper claims; external code functionality not tested
```

### Experiment artifacts

- **Run IDs:** none; literature/theory audit only.
- **Result paths:** none.
- **Aggregate paths:** none.
- **Generated paper assets:** none.

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Compare every mandatory family using primary sources | PASS | Comparator matrix and source manifest. |
| Resolve whether CayleyNet's scale/poles are learned | PASS | CayleyNet Eq. (3)–(4), printed p. 4; §3.2, pp. 5–6; algebraic pole derivation. |
| Distinguish graph-QMF sampling architecture | PASS | Graph-QMF abstract/§II/Eq. (13) versus full-resolution GBDN stack. |
| Decide novelty sufficiency of movable poles/Parseval | PASS | Parseval alone rejected as novelty; combined construction rated suggestive/conditional. |
| Supply exact URLs/identifiers and claim locators | PASS | `novelty_source_manifest.md`. |
| Avoid paper/source/result modifications | PASS | Only three assigned files changed. |

## Known limitations

- This is a bounded mandatory-family audit, not an exhaustive all-database or patent
  priority search; absolute “first” language remains unauthorized.
- External code commits were located and pinned but not executed or verified against
  the papers.
- No official implementation was verified for UniFilter or SLOG.
- The 2026 Franklin Institute item was evaluated from the primary publisher record;
  full-text claims beyond that record were not assumed.
- Whether generic poles improve fitting or compute efficiency remains experimentally
  unresolved.

## Reviewer questions

1. Will the Math Agent state the Cayley non-equivalence result with all scalar,
   cancellation, continuum, and exact-operator restrictions?
2. Will Gate B compare complex responses fairly, accounting for the real CayleyNet
   response versus GBDN's complex intermediate channels?
3. Will Gate C match parameters, sparse matrix-vector products, effective order,
   output dimensionality, and tuning budget rather than only hidden width?
4. Will the paper explicitly separate complete-stack conditioning from carried-state
   oversmoothing and target-specific long-range transmission?

## Conflicts or decisions needed

The orchestrator should freeze the following language before downstream manuscript
work:

- Replace “fixed-pole Cayley filters” with “learned but restricted shared
  imaginary-axis Cayley pole locus.”
- Treat graph-QMF as critically sampled prior art and undecimated graph framelets as
  the closest tight-stack precedent.
- Make the experimental hypothesis—generic movable poles improve a matched
  response/efficiency criterion—separate from the proved complete-map isometry.
- Do not authorize any “first” claim from this bounded audit.

## Reproduction instructions

From the reviewer worktree at the starting commit:

```powershell
Get-Content reviews\novelty_primary_source_audit.md -Raw
Get-Content results_submission\reports\novelty_source_manifest.md -Raw
git show --stat --oneline HEAD
git diff HEAD^ --check
```

Re-open each archival URL in the manifest and inspect the specified abstract,
equation, page, or section. Repository pins can be checked with:

```powershell
git ls-remote <repository-url> HEAD
```

## Rollback

Revert this single review commit. Because no manuscript, implementation, experiment,
or frozen artifact changed, rollback has no scientific-data side effects.
