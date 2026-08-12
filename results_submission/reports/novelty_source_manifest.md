# REV-NOVELTY-001 — Primary-source manifest

**Frozen audit date:** 2026-08-12
**Local source base:** `8a41705e83e4629dbc49bb83bb815cc5770e116c`
**Policy:** archival papers, official proceedings/publisher pages, author/paper-linked
repositories, and the project's own frozen files only. Search-result summaries and
secondary surveys are not evidence. Repository commits below are provenance pins;
they are **not** claims of implementation parity or successful reproduction.

## Locator and attribution convention

- “Printed p.” means the page number printed in the paper; “PDF p.” is used only
  where the document lacks printed pagination.
- “Abstract” means the archival abstract on the linked proceedings or arXiv record.
- Text below is paraphrased unless quotation marks are used. No source is quoted for
  more than 25 words.
- DOI links resolve through `https://doi.org/`. Where the official record exposes no
  DOI, the manifest says so rather than inferring one.
- A source being mandatory means the claim cannot be advanced responsibly without
  comparison; it does not mean the paper must run every source's code in every table.

## Decisive source: CayleyNet pole family

### CAYLEYNET

- **Record:** Ron Levie, Federico Monti, Xavier Bresson, and Michael M. Bronstein,
  “CayleyNets: Graph Convolutional Neural Networks with Complex Rational Spectral
  Filters,” *IEEE Transactions on Signal Processing* 67(1):97–109, 2019.
- **DOI:** [10.1109/TSP.2018.2879624](https://doi.org/10.1109/TSP.2018.2879624)
- **arXiv:** [1705.07664](https://arxiv.org/abs/1705.07664)
- **Primary PDF:** [arXiv PDF](https://arxiv.org/pdf/1705.07664)
- **Claim locator:** Eq. (3), printed p. 4, defines
  `g_{c,h}(lambda)=c_0+2 Re sum_{j=1}^r c_j((h lambda-i)/(h lambda+i))^j`
  with `h>0`; Eq. (4) and its immediately following paragraph, printed p. 4, optimize
  both `c` and `h`; §3.2 “Spectral zoom,” printed pp. 5–6, explains that varying `h`
  changes the spectral region resolved by the Cayley transform.
- **Audit inference:** writing `q_h(z)=(hz-i)/(hz+i)`, the analytic half has its
  effective-order pole at `-i/h`. The published real response adds the conjugate
  inverse powers and therefore has the restricted pair `{-i/h,+i/h}`, subject to
  cancellations. Because `h` is trained, the locus is learned—not fixed—but it stays
  on the imaginary axis and is shared by the powers of one scalar filter.
- **Mandatory verdict:** theory, response fitting, and matched spectral expressivity.
  Do not claim CayleyNet has fixed poles or no coefficient-induced zeros. The exact
  distinction is independent generic Blaschke poles versus a learned restricted
  shared Cayley locus.

## Tight graph analysis and reconstruction prior art

### GRAPH-QMF

- **Record:** Sunil K. Narang and Antonio Ortega, “Perfect Reconstruction Two-Channel
  Wavelet Filter-Banks for Graph Structured Data,” *IEEE Transactions on Signal
  Processing* 60(6):2786–2799, 2012.
- **DOI:** [10.1109/TSP.2012.2188718](https://doi.org/10.1109/TSP.2012.2188718)
- **arXiv:** [1106.3693](https://arxiv.org/abs/1106.3693)
- **Primary PDF:** [arXiv PDF](https://arxiv.org/pdf/1106.3693)
- **Claim locator:** Abstract, printed p. 1, identifies a critically sampled
  two-channel graph-QMF construction and states alias-cancellation, orthogonality,
  and perfect-reconstruction conditions. The filter-bank formulation and down/up
  sampling appear in §II, printed pp. 2–4; the graph-QMF PR conditions are given in
  Eq. (13), printed p. 8. The polynomial/Chebyshev approximation discussion states
  that approximation introduces reconstruction and orthogonality error.
- **Mandatory verdict:** related work/theory. This source blocks “first graph PR,”
  “first orthogonal graph bank,” and “first paraunitary graph bank.” It does **not**
  subsume GBDN's sampling architecture: graph-QMF is critically sampled and uses
  bipartite spectral folding/alias cancellation; GBDN's complete `D+1`-signal stack
  is redundant and nonsubsampled.

### UNDECIMATED-FRAMELETS

- **Record:** Xuebin Zheng, Bingxin Zhou, Junbin Gao, Yuguang Wang, Pietro Liò, Ming
  Li, and Guido Montufar, “How Framelets Enhance Graph Neural Networks,” ICML 2021,
  PMLR 139:12761–12771.
- **Proceedings:** [PMLR record](https://proceedings.mlr.press/v139/zheng21c.html)
- **Primary PDF:** [PMLR PDF](https://proceedings.mlr.press/v139/zheng21c/zheng21c.pdf)
- **arXiv:** [2009.04950](https://arxiv.org/abs/2009.04950)
- **DOI:** no DOI exposed by the PMLR record.
- **Claim locator:** Abstract, printed pp. 1–2, describes low-/high-pass multiscale
  coefficients and decomposition/reconstruction that conserves total information.
  §3, printed p. 3 onward, explicitly introduces an undecimated graph-framelet
  system, tight-frame exact representation, filter-bank decomposition and
  reconstruction, and Chebyshev approximation.
- **Mandatory verdict:** theory/related work and, if learned decomposition is a main
  mechanism claim, a mechanism comparator. This is the closer precedent than
  graph-QMF for a redundant full-resolution tight coefficient stack. The remaining
  distinction is learned Blaschke all-pass/root geometry, not tightness alone.

## Polynomial and adaptive spectral comparators

### CHEBNET

- **Record:** Michaël Defferrard, Xavier Bresson, and Pierre Vandergheynst,
  “Convolutional Neural Networks on Graphs with Fast Localized Spectral Filtering,”
  NeurIPS 2016.
- **Proceedings:** [NeurIPS record](https://proceedings.neurips.cc/paper/2016/hash/04df4d434d481c5bb723be1b6df1ee65-Abstract.html)
- **arXiv:** [1606.09375](https://arxiv.org/abs/1606.09375)
- **DOI:** no DOI exposed by the NeurIPS record.
- **Claim locator:** Abstract and §2.2 present localized spectral filters using a
  truncated Chebyshev expansion and sparse linear-time evaluation in the number of
  edges.
- **Mandatory verdict:** historical polynomial baseline and matched finite-order/SpMV
  control. A finite Chebyshev GBDN realization is in this computational family even
  when its target response is rational.
- **Author repository pin observed 2026-08-12:**
  [`mdeff/cnn_graph@c4d2c75`](https://github.com/mdeff/cnn_graph/commit/c4d2c75d1807a1d1189b84bd6f4a0aafca5b8c53).

### CHEBNETII

- **Record:** Mingguo He, Zhewei Wei, and Ji-Rong Wen, “Convolutional Neural Networks
  on Graphs with Chebyshev Approximation, Revisited,” NeurIPS 2022.
- **Proceedings:** [NeurIPS record](https://proceedings.neurips.cc/paper_files/paper/2022/hash/2f9b3ee2bcea04b327c09d7e3145bd1e-Abstract-Conference.html)
- **DOI:** [10.52202/068431-0527](https://doi.org/10.52202/068431-0527)
- **arXiv:** [2202.03580](https://arxiv.org/abs/2202.03580)
- **Claim locator:** Abstract identifies Chebyshev interpolation as the parameterization
  and states the intended ability to learn arbitrary graph convolutions; §4 gives the
  ChebNetII construction from Chebyshev nodes and coefficients.
- **Mandatory verdict:** Gate B/C primary polynomial comparator; blocks novelty based
  merely on flexible learned spectral responses.
- **Author repository pin observed 2026-08-12:**
  [`ivam-he/ChebNetII@ded6c18`](https://github.com/ivam-he/ChebNetII/commit/ded6c18cbe9673234071031767d17826ad632aca).

### BERNNET

- **Record:** Mingguo He, Zhewei Wei, Zengfeng Huang, and Hongteng Xu, “BernNet:
  Learning Arbitrary Graph Spectral Filters via Bernstein Approximation,” NeurIPS
  2021.
- **Proceedings:** [NeurIPS record](https://proceedings.neurips.cc/paper_files/paper/2021/hash/76f1cfd7754a6e4fc3281bcccb3d0902-Abstract.html)
- **arXiv:** [2106.10994](https://arxiv.org/abs/2106.10994)
- **DOI:** no DOI exposed by the NeurIPS record.
- **Claim locator:** Abstract describes an order-`K` Bernstein-polynomial filter and
  explicitly includes low-pass, high-pass, band-rejection, and comb responses; §3
  defines the Bernstein approximation and learned propagation.
- **Mandatory verdict:** Gate B/C primary or extended comparator. It blocks an
  unqualified claim that GBDN uniquely represents complicated band shapes.
- **Author repository pin observed 2026-08-12:**
  [`ivam-he/BernNet@79ef2ba`](https://github.com/ivam-he/BernNet/commit/79ef2bab5930477a12795f9c8530eb685e7c9262).

### GPR-GNN

- **Record:** Eli Chien, Jianhao Peng, Pan Li, and Olgica Milenkovic, “Adaptive
  Universal Generalized PageRank Graph Neural Network,” ICLR 2021.
- **OpenReview:** [official forum](https://openreview.net/forum?id=n6jl7fLxrP)
- **arXiv:** [2006.07988](https://arxiv.org/abs/2006.07988)
- **Primary PDF:** [arXiv PDF](https://arxiv.org/pdf/2006.07988)
- **DOI:** no DOI exposed by OpenReview.
- **Claim locator:** §3, printed pp. 3–4, defines a generalized PageRank polynomial
  `sum_k gamma_k A^k` with learnable signed coefficients; the abstract and §3 frame
  the adaptive filter for homophilic and heterophilic regimes.
- **Mandatory verdict:** mechanism and heterophily primary baseline; blocks “first
  adaptive learnable spectral filter.”
- **Author repository pin observed 2026-08-12:**
  [`jianhao2016/GPRGNN@4e0a7ee`](https://github.com/jianhao2016/GPRGNN/commit/4e0a7ee5435058b70eaec3c23c55fb96dc37f2d5).

### UNIFILTER

- **Record:** Keke Huang, Yu Guang Wang, Ming Li, and Pietro Liò, “How Universal
  Polynomial Bases Enhance Spectral Graph Neural Networks: Heterophily,
  Over-smoothing, and Over-squashing,” ICML 2024, PMLR 235:20310–20330.
- **Proceedings:** [PMLR record](https://proceedings.mlr.press/v235/huang24z.html)
- **arXiv:** [2405.12474](https://arxiv.org/abs/2405.12474)
- **DOI:** no DOI exposed by the PMLR record.
- **Claim locator:** Abstract introduces an adaptive heterophily basis combined with a
  homophily basis to form UniBasis/UniFilter and makes oversmoothing/oversquashing
  claims; the method section defines the polynomial basis and adaptive combination.
- **Mandatory verdict:** mechanism and heterophily primary/extended comparator. No
  author repository was verified from the archival PMLR record in this audit.

## Non-polynomial, multiresolution, and heterophily comparators

### SLOG

- **Record:** Haobo Xu et al., “SLOG: An Inductive Spectral Graph Neural Network
  Beyond Polynomial Filter,” ICML 2024, PMLR 235:55348–55370.
- **Proceedings:** [PMLR record](https://proceedings.mlr.press/v235/xu24aa.html)
- **Primary PDF:** [PMLR PDF](https://raw.githubusercontent.com/mlresearch/v235/main/assets/xu24aa/xu24aa.pdf)
- **OpenReview PDF:** [official PDF](https://openreview.net/pdf?id=0SrNCSklZx)
- **DOI/arXiv:** neither is exposed by the PMLR record; no identifier is inferred.
- **Claim locator:** Abstract explicitly presents a real-valued adaptive spectral
  filter “beyond polynomial,” with geometric interpretation and inductive subgraph
  sampling; the method section defines the non-polynomial filter family.
- **Mandatory verdict:** theory/mechanism; experimental inclusion depends on obtaining
  a reproducible author implementation. It blocks “first adaptive non-polynomial
  spectral GNN.” No official repository was verified in this audit.

### WAVEGC

- **Record:** Nian Liu, Xiaoxin He, Thomas Laurent, Francesco Di Giovanni, Michael M.
  Bronstein, and Xavier Bresson, “A General Graph Spectral Wavelet Convolution via
  Chebyshev Order Decomposition,” ICML 2025, PMLR 267:38598–38622.
- **Proceedings:** [PMLR record](https://proceedings.mlr.press/v267/liu25y.html)
- **arXiv:** [2405.13806](https://arxiv.org/abs/2405.13806)
- **DOI:** no DOI exposed by the PMLR record.
- **Claim locator:** Abstract identifies multiresolution spectral bases, a matrix-valued
  kernel, odd/even Chebyshev decomposition, wavelet admissibility, and short-/long-range
  evaluation; the method section defines the spectral bases and convolution.
- **Mandatory verdict:** theory, mechanism, and primary long-range/multiresolution
  comparator.
- **Paper-linked repository pin observed 2026-08-12:**
  [`liun-online/WaveGC@ec8af1e`](https://github.com/liun-online/WaveGC/commit/ec8af1e5a4cd57dcf296fd6281f728fc6bd04be6).

### HEROFILTER

- **Record:** Shuaicheng Zhang, Haohui Wang, Junhong Lin, Xiaojie Guo, Yada Zhu, Si
  Zhang, Dongqi Fu, and Dawei Zhou, “HeroFilter: Adaptive Spectral Graph Filter for
  Varying Heterophilic Relations,” NeurIPS 2025.
- **Proceedings:** [NeurIPS record](https://proceedings.neurips.cc/paper_files/paper/2025/hash/5d570ed1708bbe19cb60f7a7aff60575-Abstract-Conference.html)
- **Primary PDF:** [NeurIPS PDF](https://proceedings.neurips.cc/paper_files/paper/2025/file/5d570ed1708bbe19cb60f7a7aff60575-Paper-Conference.pdf)
- **DOI:** [10.52202/085713-2162](https://doi.org/10.52202/085713-2162)
- **arXiv:** [2510.10864](https://arxiv.org/abs/2510.10864)
- **Claim locator:** Abstract and introductory discussion reject a monotone mapping
  from graph heterophily to a single desired spectral profile; §4, printed pp. 5–6,
  defines adaptive polynomial patch filters and the mixer.
- **Mandatory verdict:** heterophily positioning and primary/extended benchmark; it
  blocks “heterophily equals high-frequency labels” simplifications.
- **Paper-linked repository pin observed 2026-08-12:**
  [`zshuai8/HeroFilter@f0749d6`](https://github.com/zshuai8/HeroFilter/commit/f0749d617d3c10c411aa2059e4acd863faff58a7).

## Unitary, stable, and long-range comparators

### UNITARY-CONVOLUTIONS

- **Record:** Bobak T. Kiani, Lukas Fesser, and Melanie Weber, “Unitary
  Convolutions for Learning on Graphs and Groups,” NeurIPS 2024.
- **Proceedings:** [NeurIPS record](https://proceedings.neurips.cc/paper_files/paper/2024/hash/f775e2e0e7e12227adecbbf945f43546-Abstract-Conference.html)
- **Primary PDF:** [NeurIPS PDF](https://proceedings.neurips.cc/paper_files/paper/2024/file/f775e2e0e7e12227adecbbf945f43546-Paper-Conference.pdf)
- **DOI:** [10.52202/079017-4351](https://doi.org/10.52202/079017-4351)
- **arXiv:** [2410.05499](https://arxiv.org/abs/2410.05499)
- **Claim locator:** Definition 1, printed p. 4, gives unitary propagation of the form
  `exp(iAt) X U` for symmetric `A`; the abstract and theory connect the construction
  to avoiding oversmoothing.
- **Mandatory verdict:** theory and depth baseline. It concerns same-dimensional
  unitary propagation, whereas GBDN's strongest guarantee concerns a redundant
  complete coefficient map.
- **Paper-linked repository pin observed 2026-08-12:**
  [`Weber-GeoML/Unitary_Convolutions@872aebc`](https://github.com/Weber-GeoML/Unitary_Convolutions/commit/872aebc9500e59ecb61be5abfb2adc30dc1151d1).

### A-DGN

- **Record:** Alessio Gravina, Davide Bacciu, and Claudio Gallicchio, “Anti-Symmetric
  DGN: a stable architecture for Deep Graph Networks,” ICLR 2023.
- **OpenReview:** [official forum](https://openreview.net/forum?id=J3Y7cgZOOS)
- **arXiv:** [2210.09789](https://arxiv.org/abs/2210.09789)
- **DOI:** no DOI exposed by OpenReview.
- **Claim locator:** Abstract and the stability analysis describe antisymmetric graph
  ODE dynamics intended to be stable and non-dissipative and evaluate long-range
  information propagation; the method section defines the discretized architecture.
- **Mandatory verdict:** depth/long-range baseline and theory context. Its guarantee
  is dynamical and Jacobian-oriented, not a redundant analysis-map Parseval identity.
- **Author repository pin observed 2026-08-12:**
  [`gravins/Anti-SymmetricDGN@5a7f7e7`](https://github.com/gravins/Anti-SymmetricDGN/commit/5a7f7e785315dd9b43d4675a1207a4b220fe463d).

### STABLE-CHEBNET

- **Record:** Ali Hariri, Álvaro Arroyo, Alessio Gravina, Moshe Eliasof,
  Carola-Bibiane Schönlieb, Davide Bacciu, Xiaowen Dong, Kamyar Azizzadenesheli, and
  Pierre Vandergheynst, “Return of ChebNet: Understanding and Improving an
  Overlooked GNN on Long Range Tasks,” NeurIPS 2025.
- **Proceedings:** [NeurIPS record](https://papers.nips.cc/paper_files/paper/2025/hash/c6de943558fe0b1bf4ea8f09fbcede44-Abstract-Conference.html)
- **DOI:** [10.52202/085713-4545](https://doi.org/10.52202/085713-4545)
- **arXiv:** [2506.07624](https://arxiv.org/abs/2506.07624)
- **Claim locator:** Abstract identifies stable, non-dissipative Chebyshev graph
  dynamics and long-range evaluation; the stability section states the associated
  state-dynamics result.
- **Mandatory verdict:** depth/long-range baseline and finite-Chebyshev stability
  context; it blocks equating complete-stack tightness with state non-dissipation.
- **Paper-linked repository pin observed 2026-08-12:**
  [`ahariri13/Stable-ChebNet@7d7a7e2`](https://github.com/ahariri13/Stable-ChebNet/commit/7d7a7e2696119891d277fd3fa2b32fdda454b814).

## Stability and adjacent Blaschke uses

### TRANSFERABILITY

- **Record:** Ron Levie, Elvin Isufi, and Gitta Kutyniok, “On the Transferability of
  Spectral Graph Filters.”
- **arXiv:** [1901.10524](https://arxiv.org/abs/1901.10524)
- **Primary PDF:** [arXiv PDF](https://arxiv.org/pdf/1901.10524)
- **Claim locator:** Abstract and the main transferability theorem establish linear
  stability/transferability for Cayley-smooth spectral filters under graph
  perturbations.
- **Mandatory verdict:** theory context for any graph-perturbation result. A GBDN
  resolvent bound can be construction-specific, but must not be sold as the first
  perturbation-stability principle for graph spectral filters.

### MODIFIED-BLASCHKE-GRAPH-2026

- **Record:** Guocheng Hao, Pei Wang, Juan Guo, Xiangbo Li, Cong Liu, and Lei Wang,
  “A modified Blaschke product decomposition method for deep graph signal feature
  extraction and its application on anomaly detection,” *Journal of the Franklin
  Institute* 363 (2026) 108471.
- **Publisher:** [ScienceDirect record](https://www.sciencedirect.com/science/article/pii/S0016003226000712)
- **DOI:** [10.1016/j.jfranklin.2026.108471](https://doi.org/10.1016/j.jfranklin.2026.108471)
- **Claim locator:** Publisher abstract/method summary describes Blaschke unwinding of
  nonstationary vibration signals, treating decomposition roots as vertices of a
  directed graph, followed by graph-variation/frequency analysis.
- **Mandatory verdict:** terminology/related work. It is not a learned Laplacian
  spectral operator or graph filter bank, but it blocks an unqualified “first use of
  Blaschke products on graphs” claim. Full-text access was not assumed in this audit.

### PDU

- **Record:** Ronald R. Coifman and Hau-Tieng Wu, “On the Practical Use of Blaschke
  Decomposition in Nonstationary Signal Analysis.”
- **arXiv:** [2508.10861](https://arxiv.org/abs/2508.10861)
- **Claim locator:** Abstract identifies Phase Dynamics Unwinding as a Blaschke
  decomposition algorithm and presents windowed PDU for nonstationary signals; it
  does not define a learned graph-Laplacian filter bank.
- **Mandatory verdict:** inspiration/terminology only; not a matched GNN baseline.

### BDN

- **Record:** Yanlei Zhang, Damien Martins Gomes, Chen Liu, Guy Wolf, Michael
  Perlmutter, Smita Krishnaswamy, and Dhananjay Bhaskar, “BDN: Blaschke Decomposition
  Networks,” withdrawn ICLR 2026 submission.
- **OpenReview:** [official forum](https://openreview.net/forum?id=UMu4JPQxti)
- **Claim locator:** OpenReview record and manuscript describe the product-sum neural
  construction; the record is marked withdrawn for the ICLR 2026 submission.
- **Mandatory verdict:** disclose as methodological lineage where Product-sum GBDN is
  discussed. It blocks a blanket “first Blaschke network” claim. It is not evidence
  for the tight graph construction.

## Claim-to-source minimum map

| GBDN claim type | Minimum primary sources that must be cited/compared |
|---|---|
| Tight/PR graph filter bank | GRAPH-QMF; UNDECIMATED-FRAMELETS |
| Rational/complex graph filter or pole novelty | CAYLEYNET; SLOG; exact GBDN derivation |
| Flexible learned spectral response | CHEBNETII; BERNNET; GPR-GNN; UNIFILTER; WAVEGC |
| Heterophily motivation | GPR-GNN; UNIFILTER; HEROFILTER; official benchmark protocol literature separately |
| Multiresolution/long-range | UNDECIMATED-FRAMELETS; WAVEGC; A-DGN; STABLE-CHEBNET |
| Unitarity/non-dissipation/oversmoothing | UNITARY-CONVOLUTIONS; A-DGN; STABLE-CHEBNET |
| Graph perturbation stability | TRANSFERABILITY |
| “Graph Blaschke” or “Blaschke network” priority | MODIFIED-BLASCHKE-GRAPH-2026; PDU; BDN |

## Local bibliography and verification status

The frozen revision's citation audit reports 12 unique cited BibTeX keys (17 citation
occurrences), only two DOI-bearing entries, and one arXiv identifier. The mandatory
families above are substantially absent from that bibliography; therefore the current
related-work support is not submission-ready.

Verification performed for this task:

1. Read the frozen scientific contract, Phase-0 audit, mathematical audit, active
   method/theory/related-work sections, and `refs.bib`.
2. Checked each claim above against the linked archival abstract, equation, section,
   or publisher record.
3. Derived the CayleyNet pole locus directly from published Eq. (3), retaining the
   distinction between its analytic half and published real response.
4. Queried author/paper-linked repository `HEAD` values on 2026-08-12 and recorded
   exact commits above.

Not verified here:

- functional parity of any external implementation;
- reproduction of any comparator's numerical results;
- licensing/dependency closure;
- an exhaustive patent- or all-database priority search;
- official implementations for UniFilter and SLOG.

Accordingly, “no mandatory comparator audited here combines all ingredients” is a
bounded finding. It is not authorization for an absolute “first” claim.
