# Gate A third independent review

## Decision

**Gate A: REJECT / STOP THE LINE.**

At source commit `b9f33383124f8afaa52c112b3a46105800c016ef`, the repaired suite and evidence catalog are numerically green, GA-13 now instantiates its actual Blaschke premise, the reporter's status and coverage semantics are substantially repaired, and residual-first coefficient artifacts are semantically bound. I accept 35 of the 36 mandatory rows.

One mandatory package-boundary failure remains. The root-package-exported exact constructors accept a caller-supplied `orthogonality_atol`. Setting it to `10.0` disables the orthonormal-eigenbasis premise and reproduces the exact frozen counterexample that the repair claims to reject:

```text
public function: gbdn.blaschke_cayley_exact
oracle export:    gbdn.exact_blaschke_operator_from_eigendecomposition
eigenvalues:      [0, 1]
eigenvectors:     [[1, 1], [0, 1]]
root:             0.2 + 0.1 i
argument:         orthogonality_atol=10.0

||T* T - I||_op = 4.83269046506849
singular values   = [2.4150963676566803, 0.41406215229841137]
```

The default call correctly rejects this basis, but a claim-bearing constructor cannot let its caller relax the theorem premise arbitrarily while continuing to call the result the validated exact operator. **GA-00 is therefore REJECTED.** No H100 claim-bearing job, Gate-B experiment, or paper claim promotion is authorized by this review.

## Review scope and independence

The review was performed from a detached, clean, isolated worktree at exactly `b9f3338`. I read the governing theorem-to-test contract, the prior independent rejections, the public-boundary engineering handoff, the complete repaired source/test diff, the reporter and computed evidence catalog, canonical package exports, coefficient-artifact implementation/tests, and the earlier mathematical/reviewer ledgers. I did not edit source, tests, paper, results, plans, or the execution board.

Passing tests were treated as execution evidence, not as automatic scientific acceptance. The exact-boundary and tolerance probes were written independently against the public package surface.

## Executed evidence

| Check | Result |
|---|---:|
| Gate-A test-file selection | `488 passed`, 3 warnings, 25.30 s |
| Full repository test suite | `558 passed`, 3 warnings, 28.45 s |
| Public-boundary focused suite | `34 passed`, 1.22 s |
| Immutable artifact/core focused suite | `44 passed`, 2.83 s |
| Clean Gate-A reporter | 462 collected Gate-labelled nodes; all 36 row statuses `PASS` |
| Reporter mapping metadata | 18 `UNIQUE`; 18 legitimate `DUPLICATE`; no missing mapping |
| Typed computed evidence | 811 `VALUE`, 59 `N/A`, 0 schema errors, 0 failed decisions |
| Coverage cross-validation | `PASS`; 0 fixture/root/depth/degree mismatches |
| Provenance links | 0 errors; source tree clean; exact commit recorded |
| Machine acceptance | `accepted=false`; sole recorded blocker is independent-review acceptance |

The warnings were two upstream Python 3.14/PyTorch TorchScript deprecations and the existing PyTorch sparse-invariant warning. They do not explain the rejection.

Commands used:

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
python -m pytest tests/test_gate_a*.py -q -p no:cacheprovider
python -m pytest tests -q -p no:cacheprovider
python scripts/report_gate_a.py
python -m pytest tests/test_coefficient_artifacts.py tests/test_artifact_core.py -q -p no:cacheprovider
```

## Critical finding: caller-controlled exactness defeats GA-00

`blaschke_cayley_exact` delegates input validation to `validate_exact_blaschke_eigendecomposition` and keeps its scalar evaluation and matrix assembly separate from the oracle. That independence is good. However, the public constructor forwards an unrestricted `orthogonality_atol` to the validator. The validator checks only that the residual is no greater than that caller-selected number. Any finite nonnegative value is accepted, with no upper cap tied to dtype or the theorem tolerance.

The same escape hatch exists in the separately exported `exact_blaschke_operator_from_eigendecomposition`. Both therefore return the old grossly nonunitary matrix when invoked with `orthogonality_atol=10.0`. Existing adversarial tests cover malformed tolerance types, negative values, infinity, and the default rejection, but omit a large finite tolerance. The GA-00 computed evidence likewise calls only the safe default.

This is not a cosmetic API concern. The exact construction's unitary conclusion requires an orthonormal basis. The optional argument permits the caller to negate that premise without changing the constructor name, return type, provenance tag, or claimed semantics. The minimum repair is to remove the relaxation from claim-bearing public constructors, or permit only tolerances no larger than the fixed dtype-aware default. Add the exact witness above as a regression for every public exact-constructor alias.

### Related tolerance and helper audit

- The exported low-level `validate_self_adjoint_operator` also accepts caller-selected `symmetry_atol`, `spectral_bounds`, and `spectral_atol`; for example, a triangular matrix passes with `symmetry_atol=2, spectral_bounds=None`, and `diag(-4,7)` passes with `spectral_atol=10`. This is dangerous if presented as canonical validation, but it does not independently mint a `ValidatedLaplacian` token. The canonical `validate_external_laplacian` exposes none of these knobs and rejected both witnesses. I therefore record this as API-hardening debt, not a second row rejection.
- `validate_adjacency` has a configurable symmetry tolerance, but the canonical normalized-Laplacian constructor does not expose it and revalidates adjacency at its fixed tolerance.
- `spectral.alpha_from_eigenvalue` does not validate its `scale`, but it is not exported at the package root, is not used by a canonical model path, and every downstream Blaschke constructor rejects its inadmissible/nonfinite output. It does not expand the mandatory rejection.
- Scalar analytic helpers intentionally retain finite real-line spectral scope for GA-05, while exact normalized-Laplacian operator construction enforces `[0,2]`. This distinction is mathematically coherent.

## GA-13 re-adjudication

**GA-13 is ACCEPTED.** The previous arbitrary diagonal multiplier has been replaced by

```text
q(lambda) = (1 - B_R(phi(lambda))) / 2
```

using the admissible root `-0.43133513652379385 - 0.4313351365237939 i` on the validated `weighted_6` graph. Target indices are `[0,1]`; complement indices are `[2,3,4,5]`; the repeated eigenspace `[2,3]` remains whole in the complement.

Independent inspection reproduced:

| Observable | Value |
|---|---:|
| all-pass unit-modulus residual | `6.66e-16` |
| manual operator-assembly relative residual | `0.0` |
| spectral-action residual | `2.71e-15` |
| repeated-eigenspace split count | `0` |
| target norm ratio | `0.80812` |
| required target lower bound | `0.79674` |
| complement norm ratio | `0.12537` |
| required complement upper bound | `0.13605` |
| target/complement separation gap | `0.68275` |
| squared recovery-identity residual | `2.66e-15` |
| recovery error / bound | `1.51683 / 1.55999` |

The frozen rejected multiplier remains as a meaningful negative control, with target and complement all-pass-circle defects `0.0721594` and `0.0377029`. The operator comparison is accurately labelled manual assembly rather than falsely claiming a wholly independent operator pipeline.

## Reporter and provenance adjudication

The reporter defects from the second review are repaired:

- Every mandatory row's `status` is exactly `PASS`, `FAIL`, or `NOT_RUN`; multiplicity appears only in `mapping_status`.
- Frozen fixture/root/depth/degree declarations are checked for exact equality against the computed typed evidence. Missing, stale, undeclared, and tampered scope is blocker-tested.
- The evidence catalog recomputes numerical observables rather than fabricating residuals from pytest outcomes. All 36 rows have typed evidence and every decision is machine-checkable.
- Each collected node links to its GA evidence row and common source/environment context; source commit and dirty state are recorded.
- `tests/test_gate_a.py` now says `Diagnostic subset passed` and explicitly denies that its ten checks establish Gate A.

The evidence is linked to pytest nodes at GA-ID granularity rather than claiming that each parameterized node emitted every typed field. This is accurately disclosed in the engineering handoff. It leaves a maintainability risk if tests and evidence evaluators diverge, but the computed evaluator is itself substantive, is source-bound, is cross-validated against the frozen coverage requirements, and was independently inspected here. I do not reject a second row on that basis. Future immutable reports should preserve both node identity and evaluator identity rather than weakening the link.

## Oracle independence

**ACCEPT.** Production and oracle exact arithmetic share only validation. The public constructor still ran when the oracle scalar evaluator was patched to raise, and the oracle constructor still ran when the production scalar evaluator was patched to raise. Sparse/dense comparisons materialize full operators. The remaining GA-00 rejection is about validation policy, not arithmetic self-certification.

## Residual-first artifact binding

**ACCEPT for R3 integration.** The serializer accepts `TightAnalysisOutput` rather than an untyped tuple and freezes `(r_0,...,r_{D-1},h_D)`, root order, tensor dtype/shape/device, byte ranges and hashes, run identity, config, source, environment, dependency lock, and managed-artifact bindings. Round trips are bit-exact for complex64/complex128. Carry-first/permuted manifests, descriptor reorderings, dtype/shape/path/hash tampering, truncation, incomplete pairs, replacement, and concurrent writes fail closed. The focused artifact/core suite passed 44 tests.

This validates storage semantics; it does not authorize any empirical claim or H100 run by itself.

## Mandatory-row adjudication

| ID | Verdict | Independent basis |
|---|---|---|
| GA-00 | **REJECT** | Default graph/exact paths reject invalid data, but both exported exact eigendecomposition constructors accept the frozen nonorthogonal basis when the caller supplies a large finite `orthogonality_atol`, reproducing defect `4.83269`. |
| GA-01 | ACCEPT | Canonical radial and center-width parameterizers enforce finite open-disk roots, caps, inverse recovery, and gradients. The noncanonical internal scale helper cannot bypass downstream validation. |
| GA-02 | ACCEPT | Unit modulus, positive forward phase derivative, mapped zero/pole, and Lorentzian identities cover required root fixtures; invalid roots fail at claim-bearing scalar APIs. |
| GA-03 | ACCEPT | Validated dense exact operators satisfy two-sided unitarity across the contracted fixture matrix; acceptance remains conditional on fixing GA-00's public tolerance escape. |
| GA-04 | ACCEPT | One-level complementary split and multi-feature energy identity use full operators. |
| GA-05 | ACCEPT | Pointwise partition holds over the extended real grid and graph spectra at required depths. |
| GA-06 | ACCEPT | Complete residual-first multilevel analysis is an isometry over contracted graphs, roots, and depths. |
| GA-07 | ACCEPT | Full analysis singular values and condition numbers meet the exact criterion. |
| GA-08 | ACCEPT | One-level and telescoped additive reconstruction cover exact, shared finite, and deliberately nonunitary factors. |
| GA-09 | ACCEPT | Exact adjoint synthesis and finite defect-bounded synthesis are separated and public synthesis is bound to independent assembly. |
| GA-10 | ACCEPT | Public analysis/readout/synthesis agree with an independently assembled residual-first tuple; wrong ordering separates; immutable storage now binds the same order. |
| GA-11 | ACCEPT | Weighted Parseval covers `I`, `L`, `L^2`, fractional spectral weights, and whole repeated-eigenspace projectors. |
| GA-12 | ACCEPT | Deterministic noncommuting node-projector witness establishes the non-nodewise boundary. |
| GA-13 | ACCEPT | Actual admissible-root Blaschke channel, whole repeated eigenspace, matrix features, separation/leakage, squared recovery identity, bound, and negative control all pass. |
| GA-14 | ACCEPT | Actual exact multi-root factor and degree-8 first-kind interpolant validate exact recovery and the full operator-norm approximation term. |
| GA-15 | ACCEPT | Exact and polynomial coefficient maps satisfy permutation equivariance at their respective tolerances. |
| GA-16 | ACCEPT | Scalar spectral operators are invariant to rotations within repeated eigenspaces. |
| GA-17 | ACCEPT | Equal-sized nonisomorphic graphs remain identity-safe and rebuild their own operators. |
| GA-18 | ACCEPT | First-kind nodes, DCT normalization, and independent dense recurrence agree. |
| GA-19 | ACCEPT | Sparse application materialized on the identity agrees with the complete independent dense polynomial operator. |
| GA-20 | ACCEPT | True operator error equals graph spectral maximum and both measured errors obey the verified analytic envelope. |
| GA-21 | ACCEPT | One-level finite-frame spectrum/defect use true operator error across broadened graph/degree coverage. |
| GA-22 | ACCEPT | Multilevel defect, `Delta_D`, singular spectrum, additive reconstruction, adjoint synthesis, and the `Delta_D>=1` boundary cover required depths/degrees and broadened graphs. |
| GA-23 | ACCEPT | Exact center/width and mapped geometry are correctly scoped; angular-anchor counterexample is retained. |
| GA-24 | ACCEPT | Exact-target pole geometry is explicitly distinguished from the pole-free finite polynomial realization; row is descriptive. |
| GA-25 | ACCEPT | Stable nonzero-root interpolation reports spectrum/rank/condition/residual, while an ill-conditioned witness is disclosed without a false stable guarantee. |
| GA-26 | ACCEPT | Incompatible targets within one repeated eigenspace cannot be fit by a scalar spectral multiplier. |
| GA-27 | ACCEPT | Frozen real CayleyNet comparator and reduced, noncancelled GBDN pole support only generic exact-continuum family separation. |
| GA-28 | ACCEPT | Fixed-root aligned perturbations satisfy the explicit resolvent bound across margins and perturbation sizes. |
| GA-29 | ACCEPT | Polynomial hop locality and generally nonlocal exact rational response are separately demonstrated. |
| GA-30 | ACCEPT | Instrumented recurrence uses `DK` complex-feature Laplacian SpMVs under the declared convention and records storage/order. |
| GA-31 | ACCEPT | Exact and shared finite complete coefficients obey the scoped node-pair lower bound. |
| GA-32 | ACCEPT | Zero-mode carry annihilation and residual retention correctly refute carried-state non-dissipation. |
| GA-33 | ACCEPT | Exact complete-map global Jacobian column norms equal one. |
| GA-34 | ACCEPT | Connected, disconnected, and beyond-reach target blocks preserve the distinction between global sensitivity and target transmission. |
| GA-35 | ACCEPT | Canonical variants preserve parameter identity and optimizer membership across first forward. |

## Claim boundary

Even after GA-00 is repaired, Gate A supports exact algebra, complete-map conditioning/reconstruction, finite-frame certificates, scoped pole-family separation, fixed-root perturbation bounds, and locality/cost statements only. It does not establish practical anti-oversmoothing, mitigation of oversquashing, approximation-efficiency superiority, predictive superiority, benchmark superiority, or long-range reasoning. The complete coefficient map, carried state, and target-specific transmission must remain separate objects.

## Minimum repair for a fourth review

1. Remove caller-controlled relaxation from `blaschke_cayley_exact` and `exact_blaschke_operator_from_eigendecomposition`, or cap any supplied tolerance at the fixed dtype-aware acceptance tolerance.
2. Add the frozen nonorthogonal witness with a large finite tolerance to every public exact-constructor regression. The call must reject; merely warning or returning a nonunitary matrix is insufficient.
3. Preserve the current default rejections, valid float32/float64 and forward/inverse paths, device/dtype checks, and mathematically valid empty-root identity.
4. Rerun the complete Gate-A selection, full suite, and clean reporter, then obtain a fresh independent review.

Until this repair is committed and independently accepted, Gate A remains rejected.
