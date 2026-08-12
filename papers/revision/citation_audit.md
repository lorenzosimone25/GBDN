# Citation audit

Audit date: 2026-08-11. The revision bibliography was checked against publisher,
conference, OpenReview, or arXiv records. The local citation scan reports 12
unique BibTeX keys, 12 cited keys, no placeholders, and no duplicate keys.

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

## 2026-08-12 local re-scan

The citation-verifier local scan reports 12 bibliography keys, 17 citation
occurrences, no placeholder keys, and no duplicate BibTeX keys. This is a
syntax and hygiene result, not a claim-verification result. The independent
primary-source novelty audit identifies mandatory missing families, including
graph-QMF, undecimated graph framelets, BernNet, GPR-GNN, UniFilter, SLOG,
HeroFilter, and Unitary Convolutions. Those entries must be fetched from
verified publisher/proceedings records and claim-checked before Related Work is
submission-ready; no BibTeX entry may be written from memory.
