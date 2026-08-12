# Citation audit

Audit updated: 2026-08-12. The revision bibliography was checked against publisher,
conference, OpenReview, PMLR, or arXiv records. REV-CITATIONS-002 added the minimum
claim-bearing sources identified by the independent novelty audit; metadata was not
copied from the preserved draft or written from memory.

## Revision records

| Key | Verdict | Primary record | Notes |
|---|---|---|---|
| `levie2019cayleynets` | verified | IEEE DOI `10.1109/TSP.2018.2879624`; arXiv `1705.07664` | Journal version used |
| `defferrard2016chebnet` | verified | NeurIPS 2016 proceedings | No DOI required |
| `he2022chebnetii` | verified | NeurIPS 2022 proceedings | Official code link also confirmed |
| `gravina2023adgn` | verified | ICLR 2023 OpenReview | Third author is Claudio Gallicchio |
| `hariri2025stablechebnet` | verified | NeurIPS 2025 proceedings, volume 38, pp. 136166--136196; DOI `10.52202/085713-4545` | Final archival record used |
| `liu2025wavegc` | verified | PMLR 267, ICML 2025, pp. 38598--38622 | Official code link confirmed |
| `gama2019diffusion` | verified | ICLR 2019 OpenReview; arXiv `1806.08829` | Claim limited to diffusion-wavelet stability |
| `coifman2025pdu` | verified | arXiv `2508.10861` | Preprint status explicit |
| `zhang2025bdn` | verified | OpenReview `UMu4JPQxti` | Withdrawn ICLR 2026 submission; not a TechRxiv paper |
| `platonov2023heterophily` | verified | ICLR 2023/OpenReview; arXiv `2302.11640` | Official author list and year corrected |
| `dwivedi2022lrgb` | verified | NeurIPS 2022 Datasets and Benchmarks | First author and year corrected |
| `rampasek2022graphgps` | verified | NeurIPS 2022 proceedings | Author order corrected |
| `narang2012graphqmf` | verified | IEEE DOI `10.1109/TSP.2012.2188718`; arXiv `1106.3693` | Volume 60(6), pp. 2786--2799; critically sampled PR claim checked |
| `zheng2021framelets` | verified | PMLR 139, ICML 2021, pp. 12761--12771; arXiv `2009.04950` | Official PMLR BibTeX used; undecimated/tight claim checked in the paper |
| `he2021bernnet` | verified | NeurIPS 2021, volume 34, pp. 14239--14251; arXiv `2106.10994` | Official proceedings BibTeX and arbitrary-response claim checked |
| `chien2021gprgnn` | verified | ICLR 2021 OpenReview; arXiv `2006.07988` | Adaptive signed GPR-weight claim checked in Section 3 |
| `huang2024unifilter` | verified | PMLR 235, ICML 2024, pp. 20310--20330; arXiv `2405.12474` | Official PMLR BibTeX used; adaptive polynomial-basis claim checked |
| `xu2024slog` | verified | PMLR 235, ICML 2024, pp. 55348--55370 | Official PMLR BibTeX used; non-polynomial/inductive claim checked |
| `zhang2025herofilter` | verified | NeurIPS 2025, volume 38, pp. 64537--64559; DOI `10.52202/085713-2162` | Official proceedings BibTeX used; nonmonotone heterophily/filter claim checked |
| `kiani2024unitary` | verified | NeurIPS 2024, volume 37, pp. 136922--136961; DOI `10.52202/079017-4351` | Official proceedings BibTeX used; unitary/anti-oversmoothing scope checked |
| `levie2019transferability` | verified | SampTA 2019, pp. 1--5; DOI `10.1109/SampTA45681.2019.9030932`; arXiv `1901.10524` | Final IEEE conference record used; linear stability and transferability claim checked |

## Critical errors in the preserved draft bibliography

The baseline draft is intentionally unchanged, but its entries must not be
copied back into the revision:

- `gravina2023adgn` names Lorenzo Livi instead of Claudio Gallicchio.
- `platonov2022heterophily` has the wrong year and four incorrect/missing authors.
- `heineken2023lrgb` gives a nonexistent first author and wrong year.
- `dwivedi2022graphgps` uses the wrong first author.
- `koishekenov2024wavegc` has the wrong title, authors, and year.
- `zhang2025bdn` labels a withdrawn OpenReview submission as TechRxiv and gives
  an author list inconsistent with the current public record.
- The CayleyNets conference-only record omits the verified 2019 journal version
  and DOI.

## Remaining minimum safe step

Any new claim-bearing citation must repeat this audit rather than inherit
metadata from the preserved draft.

## REV-CITATIONS-002 claim checks

- Graph-QMF is described as critically sampled and is not conflated with GBDN's
  redundant, nonsubsampled complete stack.
- Undecimated graph framelets are acknowledged as the closer tight-stack precedent;
  no priority claim is made for tight multiscale graph decomposition.
- CayleyNet's `h` is described as learned. Its pole family is called restricted and
  shared, never fixed, and coefficient-induced zeros are not denied.
- Polynomial, adaptive, and non-polynomial comparators block priority claims based
  only on learnability, heterophily, response flexibility, or non-polynomial form.
- The transferability citation blocks a field-first graph-perturbation claim.
- Unitary Convolutions, A-DGN, and Stable-ChebNet are separated from complete-map
  isometry because their guarantees concern network propagation or dynamics.
- Exact rational GBDN targets are separated from finite Chebyshev realizations; the
  latter are not assigned literal poles.

## 2026-08-12 local re-scan

The citation-verifier scan reports 21 unique bibliography keys and 34 citation
occurrences across 20 cited keys, with no placeholders and no duplicate BibTeX keys.
An independent set comparison finds no cited key missing from `refs.bib`.
`gama2019diffusion` remains as one verified but currently uncited bibliography entry;
BibTeX excludes it from the rendered reference list.

## Identifier status and unresolved sources

All nine entries added in this pass have verified archival records. SLOG's official
PMLR record exposes neither a DOI nor an arXiv identifier, so none is asserted. The
transferability paper uses its final IEEE SampTA 2019 record and DOI rather than only
the preprint. PMLR entries without a DOI retain their official PMLR URL and, where
independently verified, an arXiv identifier. These are source-status limitations, not
placeholder references.

## Minimum safe next step

The new Related Work is claim-verified for the cited statements, but baseline code
parity is outside citation verification. Before any method enters a primary empirical
table, record its upstream commit, license, configuration, and independent metric
reproduction. Any future novelty claim or new comparator must repeat the primary-
source check rather than inherit metadata from this audit.
