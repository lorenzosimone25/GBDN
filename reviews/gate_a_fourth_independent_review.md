# Gate A fourth independent review

## Decision

**Gate A: REJECT / STOP THE LINE.**

At the clean source commit
`e21b2743104471f17f56b1b67e013bec5ce28bdb`, the authored Gate-A suite,
the full repository suite, and the machine-readable reporter are green. The
specific tolerance repair requested by the third review is also effective:
all three exact eigendecomposition boundaries reject the former
`orthogonality_atol` argument and reject the frozen nonorthogonal basis under
their fixed validation.

The package boundary nevertheless still violates the frozen contract in two
independent ways:

1. a public `ValidatedLaplacian` exposes a writable alias of the tensor it
   certifies; mutation through a NumPy view does not increment PyTorch's
   version counter, so the original hash and token remain accepted while a
   canonical sparse operator consumes a matrix that fresh validation rejects;
2. the two root-exported exact pole-reduction diagnostics expose an unbounded
   `cancellation_tolerance`, allowing a caller to remove nonzero, widely
   separated poles or nonzero comparator terms while the returned object
   retains an `exact` realization tag and does not record the tolerance.

These are premise-changing public escapes, not presentation debt. GA-00 and
GA-27 are rejected; the remaining 34 rows are accepted at the reviewed commit.
No claim-bearing H100 job, Gate-B/C experiment, acceptance token, or paper
claim promotion is authorized by this review.

## Review scope and independence

The review used the isolated worktree
`C:\Users\Lough\Desktop\Research\GBDN-gatea4-review` on the dedicated branch
`agent/reviewer/REV-GATEA-REVIEW-4`, fast-forwarded to the current orchestrator
HEAD before inspection. The tree was clean when the reporter and tests ran.

I read the scientific contract, theorem-to-test contract, third independent
review and handoff, tolerance-repair handoff, public-boundary handoff, complete
Gate-A reporter and typed-evidence implementations, package exports, canonical
core/exact/scalar boundaries, reviewer instructions, handoff template, and the
relevant Gate-A tests. Passing tests were treated as execution evidence rather
than automatic scientific acceptance. The malformed-input and mutation probes
below were written independently against the public package surface.

No source, test, paper, result, state, plan, notebook, or acceptance-token file
was edited. This review does not issue an acceptance token.

## Executed evidence

| Check | Result |
|---|---:|
| Focused `test_gate_a*.py` selection | `503 passed`, 3 warnings, 33.60 s |
| Full repository suite | `653 passed`, 2 skipped, 3 warnings, 93.93 s |
| Clean Gate-A reporter | 470 Gate-labelled nodes; all 36 row statuses `PASS` |
| Reporter mappings | 18 `UNIQUE`; 18 legitimate `DUPLICATE`; 0 `MISSING` |
| Typed evidence | 817 `VALUE`; 59 justified `N/A`; 876 total |
| Evidence validation | 0 schema errors; 0 failed decisions |
| Coverage cross-validation | `PASS`; 0 mismatches |
| Provenance links | 0 errors; clean source tree at exact reviewed commit |
| Machine acceptance | `accepted=false`; reporter-only blocker was independent review |

Commands used:

```powershell
$env:PYTHONPATH=(Resolve-Path -LiteralPath src).Path
$gateFiles=(Get-ChildItem -LiteralPath tests -Filter 'test_gate_a*.py' |
  Sort-Object Name | ForEach-Object {$_.FullName})
python -m pytest @gateFiles -q -p no:cacheprovider
python -m pytest tests -q -p no:cacheprovider
python scripts/report_gate_a.py
```

The warnings were two upstream Python 3.14/PyTorch TorchScript deprecations
and the existing PyTorch sparse-invariant warning. The two skips were the
documented Windows symlink-privilege cases. None explains either rejection.

## Blocker 1: a validated graph token does not remain validated

`ValidatedLaplacian.tensor` returns the token's internal tensor directly
(`src/gbdn/core.py:90`), and the root-exported
`require_validated_laplacian` returns that same alias
(`src/gbdn/core.py:284`). The token checks only `Tensor._version`. A writable
NumPy view changes the underlying storage without incrementing this counter.

Independent public-boundary witness:

```python
raw = torch.eye(2, dtype=torch.float64)
token = gbdn.validate_external_laplacian(raw)
version_before = token.tensor._version
token.tensor.numpy()[0, 1] = 0.625
version_after = token.tensor._version

accepted = gbdn.require_validated_laplacian(token)
gbdn.validate_self_adjoint_operator(token.tensor)  # raises ValueError
```

Observed:

```text
version before / after:                 0 / 0
stored sha256 changed:                  false
self-adjoint residual of current value: 0.625
require_validated_laplacian accepted:    true
fresh canonical validation rejected:    true
ChebyshevBasis consumed altered token:   true
```

The same bypass is available through `Tensor.data`. The NumPy witness is
stronger because it uses the documented CPU tensor interoperability surface,
not a private GBDN attribute. A caller needs neither `_tensor` nor the private
issuance token.

This contradicts the class contract that the wrapped tensor cannot be changed
in place and silently reused. More importantly, it breaks the scientific
contract: after one valid check, the token can carry an asymmetric or
out-of-range operator under the old provenance hash into canonical sparse
computation. The authored mutation regression uses `add_`, which increments
`_version`, and therefore does not cover storage-alias mutation.

### Required repair

1. Do not expose a writable alias of the certified internal tensor. Public
   accessors should return detached clones, and the internal unwrap used by
   canonical layers should not be root-exported as a mutable tensor-returning
   helper.
2. If a mutable alias remains public, verify content identity against the
   stored semantic hash at every claim-bearing unwrap; a version check alone
   is not a content-integrity check.
3. Add regressions for both `token.tensor.numpy()` and `token.tensor.data`
   mutation. The altered token must fail before any sparse multiplication.
4. Verify that dense and sparse tokens, CPU/GPU transfers where supported,
   `to_dense`, and every canonical model/layer path share the repaired policy.

Until then, **GA-00 is rejected**.

## Blocker 2: caller-controlled exact pole cancellation

The root package exports both
`reduced_blaschke_pole_diagnostic` and
`frozen_scalar_cayleynet_comparator`. Each exposes
`cancellation_tolerance` with no upper bound. The tolerance changes the
algebraic object reported as the reduced exact rational response, yet neither
returned schema records the supplied tolerance or changes the realization tag
from `exact`.

### GBDN witness

```python
roots = torch.tensor([0.22 + 0.17j], dtype=torch.complex128)
default = gbdn.reduced_blaschke_pole_diagnostic(roots)
relaxed = gbdn.reduced_blaschke_pole_diagnostic(
    roots,
    cancellation_tolerance=100.0,
)
```

Observed:

```text
default cancelled pairs:    0
default reduced poles:      1
relaxed cancelled pairs:    1
cancelled zero-pole distance: 2.895653538364977
relaxed reduced poles:      0
schema:                     gbdn-exact-blaschke-reduced-poles-v1
realization_tag:            exact
tolerance recorded:         false
```

The pole and zero are not algebraically coincident. A separation of about
`2.90` cannot be treated as floating-point cancellation in an exact reduced
pole theorem.

### Frozen comparator witness

With the GA-27 comparator coefficients
`[0.7+0.2i, -0.4+0.3i, 0.15-0.25i]`, scale `1.7`, and `c0=0.3`:

```text
default declared/effective order: 3 / 3
default reduced poles:            two loci, multiplicity 3 each
tolerance 0.3 effective order:    2
tolerance 0.3 reduced poles:      empty
realization_tag:                  exact
tolerance recorded:               false
```

The third coefficient has magnitude about `0.292` and is nonzero. Dropping it
at caller request changes the exact response; it is not an algebraic
cancellation. This can make the frozen comparator locus disappear and thereby
invalidate the premise of the pole-family separation result.

### Required repair

1. Remove caller control from claim-bearing exact reduction, or cap it at one
   fixed, documented, dtype-aware numerical equality threshold that cannot
   discard materially nonzero terms or separated zero/pole pairs.
2. Separate an explicitly approximate diagnostic from the exact reduction if
   exploratory tolerance control is needed. It must use a different schema and
   realization label and record the chosen tolerance.
3. Add the two witnesses above at every root/module export alias. A large
   tolerance must be rejected, not merely disclosed after changing the exact
   multiset.
4. Recompute GA-27 from the fixed exact boundary and preserve the current
   exclusions: no finite-spectrum, approximation-efficiency, optimization, or
   superiority conclusion.

Until then, **GA-27 is rejected**.

## Tolerance-repair adjudication

The repair requested by the third review is accepted as far as it goes.
Independent signature and invocation probes covered the root exports and their
module definitions:

```text
gbdn.blaschke_cayley_exact
gbdn.exact_blaschke_operator_from_eigendecomposition
gbdn.validate_exact_blaschke_eigendecomposition
```

For each, `orthogonality_atol`, generic `atol`, `spectral_atol`, and
`spectral_bounds` were rejected with `TypeError`; the frozen nonorthogonal
basis was rejected with `ValueError` under the default call. Likewise,
`validate_self_adjoint_operator` and `validate_external_laplacian` rejected
`symmetry_atol`, `spectral_atol`, `spectral_bounds`, and `check_spectrum`, and
their invalid default witnesses were rejected.

Thus the third review's exact-eigenbasis tolerance escape is closed. This does
not cure the validated-token storage alias or the separate exact
pole-reduction tolerance escape.

## Mandatory-row adjudication

| ID | Verdict | Independent basis |
|---|---|---|
| GA-00 | **REJECT** | Initial graph and exact-constructor validation is strict, but a public issued `ValidatedLaplacian` can be storage-mutated under its original version/hash and is then consumed by canonical sparse code. |
| GA-01 | ACCEPT | Radial and center-width parameterizers enforce finite joint disk admissibility, caps, inverse mapping, and finite gradients. |
| GA-02 | ACCEPT | Scalar all-pass, positive forward phase derivative, zero/pole geometry, and Lorentzian identities remain correctly bound. |
| GA-03 | ACCEPT | Validated float64 dense exact factors meet two-sided unitarity on the frozen fixture matrix; this does not override GA-00's token failure. |
| GA-04 | ACCEPT | One-level complementary frame and matrix-feature energy identities use full operators. |
| GA-05 | ACCEPT | Pointwise multilevel partition covers the extended real grid and all contracted graph spectra. |
| GA-06 | ACCEPT | The residual-first complete exact analysis is an isometry at all required depths and fixtures. |
| GA-07 | ACCEPT | Dense singular values and condition numbers meet the exact threshold. |
| GA-08 | ACCEPT | Additive reconstruction covers exact, shared finite, and deliberately nonunitary factors. |
| GA-09 | ACCEPT | Exact adjoint synthesis and finite defect-bounded synthesis remain separated. |
| GA-10 | ACCEPT | Public residual-first tuple, readout, synthesis, and immutable coefficient order agree with independent assembly and reject the wrong order. |
| GA-11 | ACCEPT | Weighted Parseval covers `I`, `L`, `L^2`, fractional spectral weights, and a whole repeated eigenspace. |
| GA-12 | ACCEPT | The noncommuting node-projector witness correctly marks the non-nodewise boundary. |
| GA-13 | ACCEPT | The actual admissible-root Blaschke channel satisfies the scoped spectral separation and recovery observables. |
| GA-14 | ACCEPT | Exact recovery decomposition and the full operator-norm finite-factor approximation term pass. |
| GA-15 | ACCEPT | Exact and polynomial complete coefficients satisfy permutation equivariance. |
| GA-16 | ACCEPT | Scalar functional calculus is invariant under basis rotations in repeated eigenspaces. |
| GA-17 | ACCEPT | Equal-sized nonisomorphic graphs remain distinct and rebuild their own polynomial operators. |
| GA-18 | ACCEPT | First-kind DCT normalization, node interpolation, and independent dense recurrence agree. |
| GA-19 | ACCEPT | Sparse application materialized on the identity agrees with the complete independent dense polynomial operator. |
| GA-20 | ACCEPT | True operator error matches graph spectral error and measured errors obey the certified envelope. |
| GA-21 | ACCEPT | One-level finite-frame spectra and defects use true operator error and satisfy their predicted bounds. |
| GA-22 | ACCEPT | Multilevel defect, `Delta_D`, singular spectrum, additive reconstruction, and bounded adjoint synthesis cover required graphs, depths, and degrees. |
| GA-23 | ACCEPT | Exact center/width geometry and the angular-anchor counterexample remain correctly scoped. |
| GA-24 | ACCEPT | Exact target pole geometry is kept distinct from the pole-free finite polynomial realization; the row is descriptive. |
| GA-25 | ACCEPT | Stable nonzero-root interpolation and the disclosed ill-conditioned boundary both remain explicit. |
| GA-26 | ACCEPT | The repeated-eigenspace incompatible-target limitation is substantive. |
| GA-27 | **REJECT** | Default evidence is numerically correct, but both root-exported exact reduction diagnostics let callers erase nonzero poles/terms with unbounded, unrecorded tolerances while retaining exact schemas. |
| GA-28 | ACCEPT | Fixed-root aligned graph perturbations satisfy the explicit resolvent bound across margins and scales. |
| GA-29 | ACCEPT | Polynomial hop locality and generally dense exact rational response are demonstrated separately. |
| GA-30 | ACCEPT | Instrumented recurrence counts `DK` complex-feature SpMVs and records residual-first storage. |
| GA-31 | ACCEPT | Exact and shared finite complete coefficients satisfy the scoped node-pair lower bound. |
| GA-32 | ACCEPT | The zero-mode witness refutes carried-state non-dissipation while retaining the residual. |
| GA-33 | ACCEPT | Exact complete-map global Jacobian column norms equal one. |
| GA-34 | ACCEPT | Connected, disconnected, and beyond-reach witnesses preserve the global-versus-target sensitivity distinction. |
| GA-35 | ACCEPT | Canonical variants retain parameter identity and optimizer membership through first forward/backward. |

## Claim boundary

The accepted rows support the same narrow mathematical conclusions recorded by
the third review: exact complete-map algebra, conditioning and reconstruction;
finite-frame certificates; fixed-root perturbation bounds; and scoped
locality/cost statements. They do not establish practical anti-oversmoothing,
mitigation of oversquashing, approximation-efficiency superiority, predictive
superiority, benchmark superiority, or long-range reasoning.

The two rejected package boundaries additionally prevent Gate-A acceptance
even though the current default evidence values are green. A scientific gate
must certify the public object carrying the premise, not only the value before
that object is handed to a caller.

## Minimum next review

1. Close the writable validated-token alias at every root/module/model/layer
   path and add storage-alias mutation regressions.
2. Remove, safely cap, or explicitly demote caller-controlled cancellation in
   both exact pole-reduction diagnostics; add the frozen far-distance and
   nonzero-coefficient witnesses.
3. Rerun the focused Gate-A selection, full suite, and clean reporter from the
   committed repair.
4. Obtain a fresh independent package-boundary review. The repair must not
   self-issue an acceptance token.

Until these repairs are independently accepted, Gate A remains rejected.
