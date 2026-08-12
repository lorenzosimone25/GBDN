# ChebNet PyG adapter provenance

Status: **IMPLEMENTATION VERIFIED; NOT CONFIRMATORY READY**.

## Implementation identity

The canonical adapter in `src/gbdn/baselines/chebnet.py` wraps
`torch_geometric.nn.ChebConv` from dependency-pinned PyTorch Geometric 2.8.0.
The upstream project is MIT-licensed. The layer implements the Chebyshev
recurrence described by Defferrard et al., *Convolutional Neural Networks on
Graphs with Fast Localized Spectral Filtering*, Eq. (5), with the symmetric
normalized Laplacian and explicit `lambda_max=2`.

The exact upstream release identity is:

- repository: `https://github.com/pyg-team/pytorch_geometric`;
- tag: `2.8.0`;
- tag commit: `726310a486eae37a89cd6359072b82bbbbb71579`;
- installed distribution: `torch-geometric==2.8.0`;
- upstream and installed `torch_geometric/nn/conv/cheb_conv.py` SHA-256:
  `e6c9039a7511906934a9860ac1e7deea4923fd94a88af52093f510cfdb221c85`;
- installed wheel license SHA-256:
  `89cfb6edc309735916a0c1189dccf761add4af6062ddb34b5a26f60d3efadfea`;
- SPDX license expression: `MIT`.

The previously recorded commit
`cc678a392255a1467872f54582724b8dce434603` was incorrect for this dependency:
its `pyproject.toml` declares version 2.9.0. It is not an admissible source pin
for the installed 2.8.0 wheel. The corrected tag commit above declares version
2.8.0 and its `ChebConv` bytes match the installed wheel exactly. The upstream
license notice is preserved verbatim at
`licenses/third_party/pytorch_geometric_MIT.txt`.

## What was compared

PyTorch Geometric 2.8.0 exposes `ChebConv`; it does **not** expose a complete
`torch_geometric.nn.models.ChebNet` model. Therefore the only truthful
upstream end-to-end reference is a direct functional composition of two fresh
upstream `ChebConv` instances with ReLU and dropout, matching the wrapper's
documented architecture. Tests compare the adapter against that composition
for outputs, input gradients, and every trainable-parameter gradient.

The independent oracle in `src/gbdn/baselines/chebnet_oracle.py` does not
import PyG. It constructs the dense symmetric normalized operator directly and
evaluates both Chebyshev recurrences with dense matrix multiplication. Tests
compare full two-layer outputs and gradients on deterministic reciprocal
weighted graphs, including an isolated vertex, and separately check multiple
orders. Formula-based parameter counts are checked against instantiated
parameters for all five official task heads. The SpMV convention is checked
against the number of upstream recurrence propagations: each layer performs
`K-1` feature-matrix propagations, hence the two-layer wrapper performs
`2(K-1)`.

This adapter is a **ChebNet** comparator. It is not ChebNetII and must never be
reported under that name. No dataset benchmark, hyperparameter tuning, or
paper-result claim was produced by this preflight.

## Configuration provenance and remaining admission blocker

PyG does not publish a complete heterophily ChebNet model or configurations
for the five Platonov datasets. The registry therefore does not make that
claim. Registry v3 records the architecture and future hyperparameters as
`LOCAL_EQUAL_BUDGET_VALIDATION_SEARCH`, independently of the verified
upstream-layer/operator evidence.

The prespecified candidate space is frozen at
`configs/submission/search_spaces/ChebNet.json`. It is explicitly marked not
executed. Its choices are local experimental design choices, not published
ChebNet or PyG recommendations. The same confirmatory-plan trial count must be
used for every method--dataset pair, and the official task-specific validation
metric is the only permitted selection signal.

Consequently, the candidate record in
`results_submission/baseline_registry.json` may be validated only in
implementation-screening mode. Confirmatory validation must fail until the
equal-budget search has actually run, a final five-dataset method
configuration has been frozen, validation-only selection evidence has been
recorded, and an independent reviewer has accepted that evidence. No such
final configuration or tuning result exists yet.

No upstream ChebNetII, BernNet, GPR-GNN, CayleyNet, or WaveGC source code was
copied into this adapter.
