# Gate A second independent review

## Decision

**Gate A: REJECT / STOP THE LINE.**

At source commit `a0d4248d6c3e06c46eb71ce1cc4ae49ed6eeb212`, the numerical suites are green and most of the previous semantic objections are repaired. That is not sufficient for scientific acceptance. Two mandatory rows still fail independent semantic review:

- **GA-00 is REJECTED:** a root-package-exported function named `blaschke_cayley_exact` accepts an invalid eigenbasis, out-of-contract normalized-Laplacian eigenvalues, and inadmissible roots. It can therefore manufacture a nonunitary operator while presenting it as the exact Blaschke--Cayley construction.
- **GA-13 is REJECTED:** its evidence uses an arbitrary prescribed diagonal multiplier that cannot be a complementary channel of an all-pass Blaschke factor. It verifies the implication after assuming the theorem's inequalities, but not the theorem's stated method premise.

The full test suite, clean reporter execution, and this review support 34 of 36 mandatory rows. No H100 claim-bearing run, Gate B experiment, or Gate A acceptance should proceed until the two rejected rows and the reporting defects below are repaired and independently re-reviewed.

## Review scope and independence

This review was performed in a clean isolated worktree on branch `agent/reviewer/REV-GATEA-REVIEW-2`, based exactly on `a0d4248`. It did not edit implementation, tests, manuscript, result artifacts, or the execution board. The audit read the scientific contract, theorem-to-test contract, prior independent review, semantic-repair handoff and complete repair diff, canonical source and public API, all Gate A tests, evidence builders and reporter, theorem/proof/counterexample ledgers, and the relevant paper theorem and proof text.

The reviewer treated a passing pytest node as execution evidence, not as scientific acceptance. Counterexample probes were written independently against the public package surface.

## Executed verification

| Check | Result |
|---|---:|
| Gate A pytest selection | `452 passed`, 3 upstream/runtime warnings, 27.42 s |
| Full repository pytest suite | `503 passed`, 3 upstream/runtime warnings, 26.62 s |
| Clean Gate A reporter | 428 collected nodes; all 36 IDs have `execution_status=PASS` |
| Evidence payload | 735 typed `VALUE` fields plus 57 typed `N/A` fields; 0 schema errors |
| Provenance and declared coverage | 0 reporter-detected source/environment link, fixture, depth, degree, root, or row gaps |
| Worktree at execution | clean; reported source commit is exactly `a0d4248`; `source_tree_dirty=false` |
| Runtime | Python 3.14.5; PyTorch 2.12.0+cpu; CUDA unavailable |

Commands:

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
py -3.14 -m pytest tests/test_gate_a.py tests/test_gate_a_approximation.py tests/test_gate_a_closeout.py tests/test_gate_a_core_slice.py tests/test_gate_a_exact_slice.py tests/test_gate_a_fixture_matrix.py tests/test_gate_a_provenance.py -q -p no:cacheprovider
py -3.14 -m pytest tests -q -p no:cacheprovider
py -3.14 scripts/report_gate_a.py --repository-root .
```

The warnings were two Python 3.14 `torch.jit` deprecation warnings and one PyTorch sparse-invariant warning. They did not explain either scientific rejection.

## Stop-line finding 1: the public exact construction bypasses the graph and root contract

The package root exports both the validated dense oracle and the lower-level `gbdn.blaschke_cayley_exact`. The latter directly computes

```text
(U * symbol) @ U.conj().T
```

without checking that `U` is orthonormal, that the eigenvalues are a validated normalized-Laplacian spectrum, or that roots are finite and strictly inside the open unit disk. The name, docstring, and root-package export do not mark it as unchecked algebra.

The following deterministic witness was run against the public package:

```python
evals = torch.tensor([0.0, 1.0], dtype=torch.float64)
evecs = torch.tensor([[1.0, 1.0], [0.0, 1.0]], dtype=torch.float64)
roots = torch.tensor([0.2 + 0.1j], dtype=torch.complex128)
T = gbdn.blaschke_cayley_exact(evals, evecs, roots)
```

Observed values were:

```text
||T* T - I||_op = 4.83269046506849
||T T* - I||_op = 4.83269046506849
singular values   = [2.4150963676566803, 0.41406215229841137]
```

The same unchecked export also returned finite matrices for eigenvalues `[-4, 7]` and for root `1.2+0j`. By contrast, `exact_blaschke_operator_from_eigendecomposition` rejected the three cases with the following precise diagnostics:

```text
eigenvectors are not orthonormal (residual=1.618033988749895)
normalized-Laplacian eigenvalues must lie in [0, 2], got [-4.0, 7.0]
every root must lie strictly inside the unit disk
```

This is not a claim that the validated graph constructors or dense oracle are wrong; their tested paths reject the witnesses. It is a package-boundary contradiction: two root-package canonical-looking ways to obtain an "exact" operator have materially different admissibility contracts. The graph contract must hold at every claim-bearing public entry point. **GA-00 is therefore REJECTED.**

### Audit of related public spectral helpers

| Public helper | Observed boundary | Review interpretation |
|---|---|---|
| `parameterize_roots` | Rejects nonfinite parameters and enforces a strict radial cap | Validated canonical parameterizer; GA-01 evidence is sound. |
| `parameterize_center_width_roots` / `center_width_from_root` | Validate finite values, width bounds, and disk membership | Validated canonical center--width path; GA-01/23 evidence is sound. |
| `blaschke_factor` | Evaluates the rational formula for arbitrary complex inputs | A raw analytic evaluator can legitimately have this domain, but its public role must be explicitly separated from an admissible Blaschke construction. |
| `blaschke_product` | Docstring calls the object a finite Blaschke product with roots in the disk, but membership/finiteness is not checked | Ambiguous claim boundary. A NaN root returns NaNs rather than rejecting the input. |
| `blaschke_cayley_symbol` | Real spectral values outside `[0,2]` are intentionally meaningful for GA-05, but roots are unchecked | Do not restrict the real scalar grid; do validate or explicitly label the root side as unchecked. |
| `blaschke_product_cheb_coeffs`, `blaschke_cheb_coeffs`, `spectral_response` | Inherit unchecked roots; a NaN root produces NaN coefficients | Claim-bearing approximation helpers require an admissible/finite-root boundary or an unmistakable raw API. |
| `mapped_zero_pole` | Raw Möbius geometry; `alpha=1` returns `(nan+infj, nan-infj)` | The algebraic map may be intentionally partial, but the singular domain must be documented or rejected by canonical geometry APIs. |
| `tight_split_responses` | Uses the positive-phase derivative formula without validating roots | This one is directly unsafe for canonical claims: `alpha=1.2` gave derivatives `[-0.18181818181818177, -0.18144329896907216, -0.18032786885245897]`, contradicting the advertised positive forward derivative. |
| `blaschke_cayley_exact` | Does not validate eigenpairs, spectrum, or roots | Definite canonical-boundary failure, not merely a low-level analytic-domain choice. |
| validated oracle/model paths | Validate the graph/operator and generate admissible roots | No counterexample found on these paths. |

The required repair is not to prohibit all low-level algebra outside the disk. It is to distinguish raw rational evaluation from the validated objects to which Blaschke, paraunitary, normalized-Laplacian, phase-monotonicity, and exact-unitarity claims attach.

## Stop-line finding 2: GA-13 does not instantiate its theorem

The theorem defines

```text
q(lambda) = (1 - B_R(cayley(lambda))) / 2
```

and then derives energy inequalities when this channel response meets target and complement magnitude hypotheses. GA-13 instead records roots as `N/A` and directly prescribes five diagonal response values. Its evidence note explicitly says that it is "not a fitted Blaschke root."

For an exact complementary channel of an all-pass response on the real spectrum, every value must satisfy

```text
|1 - 2 q(lambda)| = 1.
```

The actual GA-13 target value is

```text
q_target = 0.96 exp(0.4 i)
         = 0.8842185542427696 + 0.3738416086163045 i
|1 - 2 q_target| - 1 = 0.07215940187498293.
```

Its complement value is

```text
q_complement = 0.025 exp(-0.7 i)
             = 0.019121054682112212 - 0.016105442180942276 i
1 - |1 - 2 q_complement| = 0.037702862276130955.
```

Thus neither prescribed value belongs to the complementary all-pass circle. The current test correctly checks a generic diagonal-multiplier norm implication and uses a whole repeated eigenspace, but it cannot validate a statement about a GBDN/Blaschke channel. **GA-13 is REJECTED.** A repair must use actual admissible roots, evaluate the actual exact operator on a graph with a whole repeated eigenspace selected, compute the realized `delta` and `eta`, and then verify the stated inequalities.

## Machine-reporting defects that independently prevent sign-off

### Row status violates the required schema

The scientific contract requires each mandatory ID to be reported as `PASS`, `FAIL`, or `NOT_RUN`. The reporter instead sets row `status="DUPLICATE"` for 18 valid multiple-definition mappings:

```text
GA-00, GA-02, GA-03, GA-04, GA-05, GA-06, GA-07, GA-09, GA-17,
GA-19, GA-20, GA-21, GA-22, GA-27, GA-28, GA-30, GA-34, GA-35
```

Their `execution_status` values are `PASS`, and the reporter does not treat `DUPLICATE` as a blocker. Legitimate multiple test definitions are mapping metadata, not execution outcomes. Row `status` must remain `PASS`/`FAIL`/`NOT_RUN`; multiplicity can remain in `mapping_status` and the summary. A regression must assert the allowed status enum for every row.

### The historical ten-check script prints a false global acceptance

Direct execution of `py -3.14 tests/test_gate_a.py` ends with:

```text
Gate A passed: 10 checks
```

The scientific contract explicitly says the pre-Phase-0 ten-test subset is regression evidence only. The file-level docstring likewise overlabels this diagnostic subset. In addition, its function named `test_chebyshev_sparse_operator_matches_exact_and_frame_bound` derives epsilon from a single-vector error, whereas the mandatory frame rows require a full operator norm. The comprehensive suite now contains the correct operator tests; the old entry point must be renamed/quarantined and must never print global acceptance.

### Coverage is declared rather than derived

The current report cleanly binds every collected node to the central source/environment record and to a typed evidence row; its schema and tamper regressions are useful. However, fixture/depth/degree/root coverage is accepted from static declarations such as `FIXTURE_MATRIX_DECLARATION`, `ROW_MATRIX_DECLARATION`, `ROOT_FIXTURE_DECLARATION`, and `ID_*`, not derived from or cross-validated against executed node parameters and computed evidence payloads. Manual inspection found the declarations consistent with the present suite, so this is not an additional row rejection. It remains a provenance-drift vulnerability: changing a test fixture without updating its declaration can leave the report green. Before immutable confirmatory use, coverage must be computed from, or checked against, executed evidence and tested with declaration/evidence tampering.

### Residual-first artifact semantics are not yet bound

GA-10 now validates the public coefficient tuple, public readout, public synthesis, and a deliberately wrong carry-first permutation. The immutable artifact core, however, remains generic and does not encode a typed Tight-coefficient schema or residual-first order. Therefore GA-10's method-level criterion is accepted, but downstream H100 artifacts must not yet assume that stored coefficient arrays are semantically bound to that order.

## Re-adjudication of previously rejected rows

- **GA-10 — ACCEPT.** Public `GBDNTight.analyze_complex` coefficients agree with an independently materialized dense residual-first analysis; the tuple residual is `1.26e-16`. The public readout residual is `3.47e-16`, public synthesis residual is `1.09e-16`, and component residual is `2.22e-16`. Carry-first permutation gives coefficient separation `1.414` and readout separation `0.276`, so the negative control is meaningful.
- **GA-14 — ACCEPT.** The evidence now uses actual exact multi-root Blaschke factors and an actual degree-8 first-kind interpolant. Epsilon is a full operator norm, the channel perturbation is epsilon/2, and the squared recovery identity and total triangle bound are evaluated directly.
- **GA-25 — ACCEPT.** Nonzero admissible roots generated by finite parameters produce a full-rank evaluation matrix with condition number `63.23` and interpolation residual `3.06e-15`. The deliberately clustered case reports condition number `9.145e11` and residual `3.55e-5` without claiming the well-conditioned guarantee.
- **GA-27 — ACCEPT.** The comparator implements the published real scalar CayleyNet response `c0 + 2 Re sum_j c_j q_h^j` with a common positive `h`. The frozen reduced comparator poles are `+/-0.588235 i` with multiplicity three and nonzero reduced numerator values; the GBDN witness pole `-0.5335007061-1.4478267692i` survives cancellation and is separated by `1.01169`. The paper limits this to generic exact-target family separation and makes no efficiency or superiority claim.
- **GA-00 — REJECT.** The direct graph/model paths were strengthened, but the exported exact bypass above leaves the package-wide contract inconsistent.

## Finite-frame, exact-target, and public-interface review

- **GA-21/22 — ACCEPT.** The evidence covers a path, a complete graph with repeated spectrum, and a positive nonuniform weighted graph. GA-21 uses degrees 8 and 16. GA-22 uses depths 1, 2, 4, 8, and 16 and degrees 8, 12, and 16. It computes true per-level operator errors, the full analysis matrix, frame spectrum/defect, `Delta_D`, singular values, additive reconstruction, and adjoint synthesis. A separate boundary case confirms that `Delta_D >= 1` suppresses the positive lower-frame claim.
- **GA-24 — ACCEPT.** Evidence explicitly records `geometry_scope="exact-target"` and exact-target root/pole geometry; the finite realization is tagged `chebyshev-K` and is not assigned literal poles. The row is descriptive and makes no monotonicity claim.
- **Public analysis/synthesis/readout — ACCEPT for the mandatory forward convention.** The repaired independent dense witnesses cover public values and order. A read-only inverse-convention probe also agreed with the independent dense polynomial oracle (`2.42e-16` maximum component relative error; `1.36e-16` synthesis error). Invalid conventions are rejected on first analysis. No convention mismatch was found.
- **Lifecycle — ACCEPT.** All canonical model variants preserve parameter identities across the first forward pass and optimizer construction.
- **Package-wide boundary — REJECT overall because of GA-00.** Passing the main model path does not neutralize an exported canonical-looking exact path that bypasses the same contract.

## First-kind Chebyshev derivation and attribution

The finite approximation theorem uses degree `K` and `N=K+1` first-kind roots

```text
x_j = cos((j+1/2) pi / N),  j=0,...,N-1.
```

The code uses that convention. The appendix correctly derives the first-kind aliasing cases for `m=2qN+s`, `0 <= s < 2N`: aliases have sign `(-1)^q` for `s<N`, vanish for `s=N`, and have sign `(-1)^(q+1)` and degree `2N-s` for `s>N`. Combining this with `|a_m| <= 2 M_rho rho^{-m}` yields the stated envelope

```text
||f - I_K f||_infinity <= 4 M_rho rho^{-K} / (rho - 1).
```

The proof remains valid for the complex-valued Blaschke response because interpolation is complex-linear and the estimates use absolute values. The source chain is exact: Lloyd N. Trefethen, *Approximation Theory and Approximation Practice*, extended edition, SIAM, 2019, Chapter 8, pp. 55--62, DOI `10.1137/1.9781611975949.ch8`, together with the book's first-kind node convention in Exercise 2.4. The author-hosted sample is `https://people.maths.ox.ac.uk/~trefethen/trefethen_sample.pdf`. The manuscript appropriately does not misapply the book's second-kind interpolation theorem directly. No placeholder or duplicate bibliography key was found among the 22 cited entries.

## Mandatory-row adjudication

`CONDITIONAL` is reserved for a row whose mandatory observable passes but whose use requires a stated external condition. No row needed that classification here: semantic mismatches are rejected, while downstream artifact limitations are recorded separately.

| ID | Verdict | Independent basis |
|---|---|---|
| GA-00 | **REJECT** | Validated graph paths pass, but exported `blaschke_cayley_exact` accepts invalid eigenpairs, spectrum, and roots and yields a grossly nonunitary operator. |
| GA-01 | ACCEPT | Radial and center--width parameterizers enforce finite admissible roots, bounds, inverse recovery, and finite gradients. |
| GA-02 | ACCEPT | Unit modulus, phase derivative, mapped zero/pole, and Lorentzian identities pass over the required root fixtures; unchecked raw helper boundaries remain covered by GA-00's package finding. |
| GA-03 | ACCEPT | Validated dense exact operators satisfy two-sided unitarity over the fixture matrix. |
| GA-04 | ACCEPT | One-level tight split and multi-feature energy identity are independently materialized. |
| GA-05 | ACCEPT | Pointwise partition holds on the full real grid and graph spectra at all tested depths. |
| GA-06 | ACCEPT | Exact complete multilevel analysis is an isometry over required graphs, roots, and depths. |
| GA-07 | ACCEPT | Full analysis singular values and condition numbers equal one within tolerance. |
| GA-08 | ACCEPT | One-level and telescoped additive reconstruction hold for exact and shared finite channels, including a nonunitary factor. |
| GA-09 | ACCEPT | Exact adjoint synthesis passes; finite adjoint error is bounded and not called perfect reconstruction. |
| GA-10 | ACCEPT | Public residual-first tuple/readout/synthesis match independent dense construction; wrong order separates. |
| GA-11 | ACCEPT | Weighted Parseval covers `I`, `L`, `L^2`, fractional spectral weights, and repeated-eigenspace projectors. |
| GA-12 | ACCEPT | Noncommuting node-projector witness establishes the non-nodewise boundary. |
| GA-13 | **REJECT** | Prescribed diagonal values violate `|1-2q|=1` and therefore are not an exact Blaschke complementary channel. |
| GA-14 | ACCEPT | Actual roots and a true finite interpolant validate exact complex recovery and approximation bounds. |
| GA-15 | ACCEPT | Exact and polynomial coefficient maps are permutation equivariant within the respective tolerances. |
| GA-16 | ACCEPT | Repeated-eigenspace basis rotations leave the scalar spectral operator invariant. |
| GA-17 | ACCEPT | Same-sized nonisomorphic graphs remain identity-safe and rebuild reproducibly. |
| GA-18 | ACCEPT | First-kind nodes, DCT normalization, and independent dense recurrence agree. |
| GA-19 | ACCEPT | Sparse application materialized on the identity agrees with the full independent dense polynomial operator. |
| GA-20 | ACCEPT | Operator error equals graph spectral maximum and is bounded together with the interval-grid error by the verified analytic envelope. |
| GA-21 | ACCEPT | One-level finite-frame spectrum and defect lie in true-operator-error bounds across broadened graphs and degrees. |
| GA-22 | ACCEPT | Multilevel defect, `Delta_D`, frame spectrum, and both reconstructions cover broadened graphs/depths/degrees and the `Delta_D>=1` boundary. |
| GA-23 | ACCEPT | Center, half-width, pole geometry, and angular-anchor counterexample match their scoped statements. |
| GA-24 | ACCEPT | Exact-target geometry and finite approximation metadata are separated; the row is descriptive only. |
| GA-25 | ACCEPT | Well-conditioned nonzero-root interpolation succeeds; the ill-conditioned case is disclosed rather than overclaimed. |
| GA-26 | ACCEPT | The universal scalar-multiplier limitation on incompatible repeated-eigenspace targets is established algebraically and numerically. |
| GA-27 | ACCEPT | Frozen real CayleyNet comparator and reduced nonremovable target pole witness support only generic exact-target family separation. |
| GA-28 | ACCEPT | Fixed-root, matched-vertex perturbations satisfy the explicit resolvent bound across margins and perturbations. |
| GA-29 | ACCEPT | Polynomial locality has the declared hop radius; the exact rational response is separately shown generally dense. |
| GA-30 | ACCEPT | Instrumented full recurrence uses `DK` Laplacian SpMVs under the stated no-reuse condition and records complex-operation/storage convention. |
| GA-31 | ACCEPT | Exact and shared finite coefficient maps satisfy the scoped node-pair lower bound. |
| GA-32 | ACCEPT | Zero-mode carry annihilation and residual retention distinguish carried state from complete coefficients. |
| GA-33 | ACCEPT | Exact complete-map global Jacobian column norms equal one. |
| GA-34 | ACCEPT | Connected, disconnected, and beyond-reach target blocks establish the boundary between global sensitivity and target transmission. |
| GA-35 | ACCEPT | Parameter sets and identities remain fixed across optimizer construction and first forward for all canonical variants. |

## Claim-boundary assessment

- **Proved and numerically exercised:** exact all-pass/tight identities, complete-map conditioning/reconstruction, weighted spectral Parseval, finite-frame inequalities, Product-sum finite-spectrum result, scoped generic reduced-pole family separation, fixed-root perturbation bound, and polynomial locality/cost statements, subject to the canonical API repair above.
- **Boundary/counterexample supported:** carried-state annihilation, node-projector failure, repeated-eigenspace scalar limitation, and failure of complete-map isometry to imply target-specific transmission.
- **Not authorized by Gate A:** resistance to practical oversmoothing, mitigation of oversquashing, predictive superiority, approximation efficiency superiority, benchmark superiority, or finite-realization literal pole claims.

The manuscript currently preserves the exact-versus-finite-versus-legacy distinction and explicitly denies the prohibited oversmoothing/oversquashing inference. The T-F statement is limited to generic exact-target family separation and does not name a superior method or claim performance superiority.

## Minimal conditions for a new independent review

1. Make every claim-bearing public exact operator path validate eigenbasis/operator, normalized-Laplacian spectral domain where applicable, and finite open-disk roots, or remove/rename raw exports so they cannot be confused with canonical validated construction. Add the nonorthogonal-basis, out-of-range-spectrum, outside-root, and nonfinite-root regressions above.
2. Replace GA-13's prescribed multiplier with an actual exact response from admissible roots on a graph; select whole repeated eigenspaces, derive observed `delta` and `eta`, and test all energy/leakage inequalities.
3. Keep row execution `status` in `{PASS, FAIL, NOT_RUN}` and move multiple-definition information exclusively to mapping metadata. Add a schema regression over all 36 rows.
4. Rename/quarantine the historical ten-check diagnostic entry point and remove its false global Gate A message and single-vector frame-bound labeling.
5. Cross-validate declared fixture/depth/degree/root coverage against executed typed evidence and add drift/tamper regressions.
6. Before any H100 artifact is treated as confirmatory, bind Tight coefficient payloads to an explicit residual-first schema and validate the binding on resume/read.

Until items 1--4 are repaired, Gate A remains rejected. Items 5--6 are required before the reporter and artifact chain can authorize claim-bearing downstream work.
