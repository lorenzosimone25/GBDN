# Agent Handoff — REV-CITATIONS-002

## Task

- **Task ID:** REV-CITATIONS-002
- **Agent:** Independent A* Reviewer / Citation Auditor
- **Branch:** `agent/reviewer/REV-CITATIONS-002`
- **Starting commit:** `282dd75a7935fc150a178a157ab159fd548f9f21`
- **Ending commit:** this handoff commit
- **Status proposed:** **REVIEW**

## Objective

Fetch and verify exact bibliography metadata for the minimum missing comparator
families identified by the novelty audit, then revise Related Work and its comparison
table without overclaiming. The assigned scope was limited to `refs.bib`, the Related
Work section, the citation audit, and this handoff. No experiments were authorized.

## Summary

Added nine claim-bearing sources from primary archival records: graph-QMF,
undecimated graph framelets, BernNet, GPR-GNN, UniFilter, SLOG, HeroFilter, Unitary
Convolutions, and spectral-filter transferability. Related Work is now organized by
methodological object rather than a loose list of baselines. It explicitly separates:

- critically sampled graph-QMF from GBDN's redundant nonsubsampled stack;
- prior tight undecimated graph framelets from learned Blaschke root geometry;
- polynomial/adaptive/non-polynomial response learning from GBDN's candidate
  pole-family distinction;
- CayleyNet's learned restricted shared pole locus from independent generic GBDN
  exact-target poles;
- exact rational targets from finite polynomial Chebyshev realizations;
- complete-map isometry from state-dynamics stability, oversmoothing, and
  source-to-target sensitivity.

The comparison table reports only source-verified scope and states that this is not
independent validation. It contains no priority claim for tightness, perfect
reconstruction, rational filtering, adaptive filtering, or graph-filter stability.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `papers/revision/refs.bib` | Added nine primary-source-verified BibTeX entries with archival identifiers. | Yes, explicitly assigned. |
| `papers/revision/sections/06_related_work.tex` | Reorganized the section and replaced the comparison table with a bounded methodological comparison. | Yes, explicitly assigned. |
| `papers/revision/citation_audit.md` | Added per-entry provenance, claim checks, scan results, and identifier limitations. | Yes, explicitly assigned. |
| `handoffs/REV-CITATIONS-002.md` | Recorded evidence, limitations, and reproduction steps. | Yes. |

No other manuscript section, implementation, test, notebook, result artifact, or
generated paper asset was modified.

## Scientific impact

- **Claims enabled:** precise comparison between independent generic GBDN exact-target
  poles and CayleyNet's learned restricted shared locus; precise distinction between
  critically sampled graph-QMF and the nonsubsampled complete GBDN stack.
- **Claims narrowed:** exact reconstruction/isometry is supporting structure rather
  than priority novelty; any perturbation theorem is construction-specific;
  movable-pole usefulness remains an experimental hypothesis.
- **Claims rejected:** first tight/PR graph bank; first nonsubsampled tight graph
  representation; first rational, complex, adaptive, or non-polynomial spectral GNN;
  fixed-pole CayleyNet; finite Chebyshev factors literally have poles; complete-map
  isometry by itself prevents oversmoothing or oversquashing.
- **Paper sections affected:** Related Work and bibliography only.

## Evidence

### Proofs

- **Theorem/lemma:** no new theorem was introduced.
- **Assumptions:** source descriptions are limited to the cited primary paper's stated
  construction/results; Cayley pole statements retain the scalar, finite-order,
  uncancelled, exact-rational-response scope from REV-NOVELTY-001.
- **Proof location:** existing novelty audit and mathematical contract; this task only
  edits citations and positioning.
- **Counterexamples checked:** learned `h` refutes “fixed Cayley poles”; graph-QMF and
  graph framelets refute tight/PR priority; finite Chebyshev approximation refutes
  literal deployed-pole language; unitary/stable state models refute a field-priority
  anti-oversmoothing claim.

### Tests

```text
command:
python C:\Users\Lough\.codex\skills\citation-verifier\scripts\scan_citations.py papers\revision

result:
PASS — 21 unique BibTeX keys; 20 unique cited keys / 34 citation occurrences;
0 placeholders; 0 duplicate BibTeX keys.
```

```text
command:
PowerShell set comparison of every \cite{...} key against every refs.bib key

result:
PASS — no cited key is missing. The sole uncited entry is the previously verified
gama2019diffusion record; BibTeX omits it from the rendered references.
```

```text
command:
pdflatex (graphicx demo mode) -> bibtex -> pdflatex -> pdflatex

result:
PASS — 19-page full-source build; no undefined citations, multiply-defined keys,
LaTeX errors, or package errors. Demo mode was used because the worktree lacks
fig_sphere_decomposition.pdf and fig_pole_distance.pdf.
```

```text
command:
Poppler render at 160 dpi; visual inspection of Related Work pages 7--9

result:
PASS — comparison table and prose have no clipping, overlap, margin spill, broken
glyphs, or illegible columns. Temporary PDF/PNG/build files were removed afterward.
```

```text
command: git diff --check
result: PASS
```

### Experiment artifacts

- **Run IDs:** none; literature/citation task only.
- **Result paths:** none.
- **Aggregate paths:** none.
- **Generated paper assets:** none committed; compile/render files were temporary and
  removed after inspection.

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Add all nine minimum missing families from primary records | PASS | `refs.bib` and per-entry citation audit. |
| No placeholders or memory-derived metadata | PASS | Primary proceedings/DOI/PMLR/OpenReview/arXiv records and citation scan. |
| Methodologically organize Related Work | PASS | Five bounded paragraphs and comparison table. |
| Correct CayleyNet and sampling distinctions | PASS | Table plus graph-bank and rational-filter paragraphs. |
| Avoid unsupported priority or performance claims | PASS | Claim-bounded prose; usefulness remains an experimental question. |
| Resolve every in-text citation | PASS | Set comparison and BibTeX build. |
| Compile and visually inspect the table | PASS | Demo-mode full build and Poppler inspection. |
| Touch only assigned files plus handoff | PASS | Final Git status/diff scope. |

## Known limitations

- SLOG's official PMLR record exposes neither a DOI nor an arXiv identifier; the
  PMLR URL, volume, and pages are used without inventing either identifier.
- Several proceedings records appropriately have no DOI: graph framelets, BernNet,
  GPR-GNN, and UniFilter. Verified PMLR/NeurIPS/OpenReview URLs and available arXiv
  identifiers are retained.
- External implementation parity, licenses, configurations, and empirical result
  reproduction were not part of this task. A citation does not qualify a baseline for
  the primary results table.
- This bounded comparator audit still does not authorize absolute “first” language.
- The two experiment figure PDFs were absent. The full source was compiled in
  `graphicx` demo mode, so final figure fidelity was not inspected in this task.

## Reviewer questions

1. Does the Math Agent preserve the exact-target and scalar-response restrictions if
   the Cayley pole non-equivalence corollary enters the paper?
2. Will Gate B/C implement fair real/complex channel matching for CayleyNet and match
   parameters, SpMVs, effective order, output dimensionality, and tuning budget?
3. Should the final page-budget pass retain the full comparison table in the main
   paper or move the lower-priority rows to the appendix after empirical evidence is
   frozen?

## Conflicts or decisions needed

No citation conflict remains. The orchestrator should preserve these decisions:

- Parseval/reconstruction is a guarantee, not the sole novelty claim.
- CayleyNet has a learned restricted shared locus, never “fixed poles.”
- Graph-QMF is critically sampled; undecimated framelets are the closer tight-stack
  precedent.
- The finite Chebyshev implementation approximates a movable-pole target and is not
  itself rational.
- State-level oversmoothing and long-range claims require dedicated proof and
  experiments.

## Reproduction instructions

From the repository root:

```powershell
python C:\Users\Lough\.codex\skills\citation-verifier\scripts\scan_citations.py papers\revision
git diff --check
```

When the two figure PDFs are available, run a normal full build from
`papers/revision`:

```powershell
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Until then, the citation/table build can be reproduced in an isolated output
directory with `\PassOptionsToPackage{demo}{graphicx}` before `\input{main.tex}`, then
BibTeX and two additional pdfLaTeX passes. Inspect the resulting Related Work pages
with Poppler rather than relying only on log output.

## Rollback

Revert this single commit. No experimental artifact or generated paper asset depends
on it, so rollback has no data side effects.
