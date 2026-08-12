# Claim-to-Evidence Matrix

| Claim | Revised statement | Implementation | Automated evidence | Planned mechanism evidence | Status |
|---|---|---|---|---|---|
| Forward phase geometry | Proposition `prop:phase-pole` | `blaschke_cayley_symbol`, `tight_split_responses`, `mapped_zero_pole` | Phase finite differences, pole conjugacy, unit modulus | Completed root angle/radius sweep | Verified theory and controlled evidence |
| Exact factor unitarity | Theorem `thm:tight-split` | `blaschke_cayley_exact` | Double-precision `T* T=I` | Exact-versus-Chebyshev study | Gate B aligned |
| Tight channel energy | Theorem `thm:tight-split` | `GraphBlaschkeLayerTight` | One-level channel-energy identity | Sphere frame error at numerical precision | Verified theory and controlled evidence |
| Multilevel reconstruction | Theorem `thm:multilevel-pr` | `TightAnalysisOutput`, `GBDNTight.analyze`, `GBDNTight.synthesize`, exact spectral helpers | Depth-16 isometry and adjoint reconstruction | Graph-family depth sweep | Gate B aligned |
| Energy separation | Theorem `thm:energy-separation` | Minus-channel response | Numerical inequality check | Magnitude-objective comparison | Gate B aligned |
| Complex recovery | Corollary `cor:complex-recovery` | Complex minus-channel response | Numerical squared-error bound | Completed five-seed sphere recovery | Verified distinction on one controlled family |
| Pole-distance approximation | Theorem `thm:pole-distance-cheb` | `mapped_zero_pole`, Chebyshev coefficients | Sparse operator error and approximate frame bound | Completed radius/angle/pole-distance sweep | Verified theory and controlled evidence |
| Product-sum interpolation | Theorem `thm:product-sum-vandermonde` | `GBDNProductSum` | Zero-root Vandermonde rank | Matched response fitting | Gate B aligned |
| Stability scope | Final theory remark | Exact factors and full coefficient tuple | Separate unitary, carry, and coefficient tests | Separate singular-value plots | Gate B aligned |
| Graph analytic signal | Removed | None | None | Future oriented operator only | Removed |

No abstract claim currently depends on an unfinished downstream benchmark. The
abstract's empirical sentence is limited to the completed controlled sphere
study and identifies the H100 rows as single-run diagnostics. The legacy
heterophily and Peptides-func artifacts demonstrate executable benchmark-scale
pipelines but do not support superiority, generalization, or significance
claims. Those claims remain inadmissible until Gate C and a matched multi-seed
benchmark protocol pass.
