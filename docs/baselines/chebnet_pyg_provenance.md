# ChebNet PyG adapter provenance

Status: **NOT ADMITTED** to confirmatory scope.

The canonical adapter in `src/gbdn/baselines/chebnet.py` wraps
`torch_geometric.nn.ChebConv` from dependency-pinned PyTorch Geometric 2.8.0.
The upstream project is MIT-licensed. The layer implements the Chebyshev
recurrence described by Defferrard et al., *Convolutional Neural Networks on
Graphs with Fast Localized Spectral Filtering*, Eq. (5), with the symmetric
normalized Laplacian and explicit `lambda_max=2`.

This adapter is a **ChebNet** comparator. It is not ChebNetII and must never be
reported under that name. The local two-layer architecture, task head,
dropout, polynomial order, and resource-count convention are explicit in the
adapter and its tests. The first-layer sparse output is independently checked
against a dense recurrence on a weighted reciprocal graph.

The adapter remains outside `results_submission/baseline_registry.json` until
all of the following exist and pass:

- a pinned licensed PyG source commit and preserved license notice;
- a frozen official-task reference configuration;
- independent end-to-end parity evidence on a predeclared fixture;
- official dataset head/loss/metric dispatch tests;
- parameter and feature-matrix SpMV accounting for the frozen configuration;
- an independently reviewed registry-v2 record binding every artifact hash.

No upstream ChebNetII, BernNet, GPR-GNN, CayleyNet, or WaveGC source code was
copied into this adapter.
