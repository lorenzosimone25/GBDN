# Gate A fifth independent review

## Decision

**Gate A: ACCEPT under the frozen scientific contract.**

At the clean reviewed commit
`a8be64da25de060f7e7d634d45362827fded147c`, all 36 mandatory rows
GA-00--GA-35 are accepted within their explicitly narrow scopes. The two
package-boundary failures from the fourth review are closed:

1. public `ValidatedLaplacian` access no longer exposes the tensor storage
   consumed by canonical computation, while private canonical unwraps check
   both the PyTorch mutation version and the stored semantic SHA-256 before
   multiplication;
2. the exact Blaschke and frozen scalar CayleyNet diagnostics no longer accept
   caller-controlled cancellation tolerances and now state their algebraic
   reduction policies in v2 exact schemas.

Independent reproductions of the previous NumPy/`.data` witnesses, additional
storage aliases and canonical consumers, and the former GBDN `100.0` and
CayleyNet `0.3` tolerance overrides all fail closed or leave the certified
object unchanged. GA-00 and GA-27 are therefore accepted. The other 34 rows,
which the fourth review accepted at their frozen boundaries, remain intact;
the repair did not widen them and the complete Gate suite, typed evidence, and
full repository suite remain green.

This acceptance authorizes closure of the mathematical Gate A only. It does
not constitute an acceptance token, authorize H100 execution by itself, or
support claims of practical anti-oversmoothing, oversquashing mitigation,
approximation efficiency, predictive superiority, benchmark superiority, or
long-range reasoning.

## Scope and independence

The review used the isolated worktree
`C:\Users\Lough\Desktop\Research\GBDN-gatea5-review` on branch
`agent/reviewer/REV-GATEA-REVIEW-5`. It was reset to the current orchestrator
commit before final probes and executions. The reviewed commit contains the
boundary repair and the subsequent acceptance-provenance correction that
adds every `test_gate_a*.py` module, including `test_gate_acceptance.py`, to
the protected path set.

I read the canonical scientific contract, theorem-to-test contract, fourth
independent review and handoff, boundary-repair handoff, relevant canonical
source, tests, typed evidence, reporter, package exports, and the small
protected-path correction. Passing authored tests were treated as execution
evidence, not as an automatic decision. The adversarial probes below were run
against public/root/module boundaries and canonical consumers independently
of the authored regressions.

No implementation, test, paper, result, state, board, notebook, or acceptance
token was edited. This review writes only this decision and its handoff.

## Executed evidence

| Check | Result |
|---|---:|
| Independent alias and tolerance probes | PASS |
| Focused `test_gate_a*.py` selection | `513 passed`, 3 warnings, 33.28 s |
| Full repository suite | `684 passed`, `2 skipped`, 145 warnings, 76.90 s |
| Clean Gate-A reporter | 479 Gate-labelled nodes; 36 `PASS` rows |
| Reporter mappings | 18 `UNIQUE`; 18 legitimate `DUPLICATE`; 0 `MISSING` |
| Typed evidence | 841 `VALUE`; 59 justified `N/A`; 900 total |
| Evidence validation | 0 schema errors; 0 decision failures |
| Coverage cross-validation | `PASS`; 0 mismatches |
| Provenance links | 0 errors; clean source tree at exact reviewed commit |
| Machine acceptance field | `accepted=false`; sole blocker was this independent review |

Commands used:

```powershell
$env:PYTHONPATH=(Resolve-Path -LiteralPath src).Path
$gateFiles=(Get-ChildItem -LiteralPath tests -Filter 'test_gate_a*.py' |
  Sort-Object Name | ForEach-Object {$_.FullName})
python -m pytest @gateFiles -q -p no:cacheprovider
python -m pytest tests -q -p no:cacheprovider
python scripts/report_gate_a.py
```

The three Gate warnings were the two upstream Python 3.14/PyTorch TorchScript
deprecations and the existing PyTorch sparse-invariant warning. The full suite
also emitted 142 upstream PyG/Python 3.14 annotation deprecations. The two
skips were the documented Windows symlink-privilege cases. None affects this
decision.

## GA-00 boundary adjudication

### Public aliases are isolated

For a dense validated token, I independently mutated values obtained from all
four public access paths:

- `token.tensor`;
- `token.to_dense()`;
- root-exported `gbdn.require_validated_laplacian(token)`;
- module-level `gbdn.core.require_validated_laplacian(token)`.

For every path I mutated the returned tensor through a NumPy view,
`Tensor.data`, a detached flattened view, and direct tensor storage. None
changed the token's dense value or the complete Chebyshev basis subsequently
computed from it. NumPy, `.data`, and direct-storage mutations remained
version-invisible on the public copy, reproducing the exact risk from the
fourth review while demonstrating that the repaired accessor isolates it.

The same outcome held for sparse tokens produced through the root normalized
Laplacian builder, the core validated builder, and the recorded
reciprocal-mean preprocessor. Mutating sparse copy values, indices, public
dense materializations, and the compatibility unwrap did not change the
certified token or canonical output.

### Private tampering fails before multiplication

I then reproduced adversarial mutations against the private stored tensor to
test defense in depth. Version-invisible NumPy, `.data`, and direct-storage
changes were rejected with `validated Laplacian storage content changed`.
A detached-view mutation incremented the tensor version and was rejected with
`validated Laplacian was modified in place`. These failures occurred before
all three independently exercised canonical consumption paths:

- `ChebyshevBasis`;
- `GBDNTight.analyze`;
- validated peeling through `tight_peel_sequence`.

The private internal unwrap is not root-exported. A shallow token copy does
not create a public writable alias; a deep copy currently fails closed because
its copied tensor mutation version is not the certified version. This is a
conservative usability behavior, not a route around validation.

The repair therefore closes the fourth review's premise-changing witness.
The content hash is checked on every canonical unwrap, including property
access used before multiplication, and the canonical graph object cannot be
silently changed while retaining its original certification. **GA-00 is
accepted.**

## GA-27 boundary adjudication

The root and module objects are identical for both exact diagnostics, and
their inspected signatures are now:

```text
reduced_blaschke_pole_diagnostic(roots)
frozen_scalar_cayleynet_comparator(c0, coefficients, scale)
```

For both root and module aliases, I attempted the former keywords plus
`cancellation_tol`, `tolerance`, `tol`, `atol`, `rtol`, `zero_tolerance`,
`pole_tolerance`, `threshold`, and `eps`, as well as an extra positional
tolerance. Every call was rejected with `TypeError`.

The frozen fourth-review witnesses retain their exact object:

```text
GBDN root:                 0.22 + 0.17i
zero--pole distance:       2.895653538364977
cancelled pairs:           0
reduced poles:             1
schema:                    gbdn-exact-blaschke-reduced-poles-v2

Cayley coefficients:       [0.7+0.2i, -0.4+0.3i, 0.15-0.25i]
declared/effective order:  3 / 3
reduced loci:              2, multiplicity 3 each
schema:                    gbdn-frozen-scalar-cayleynet-comparator-v2
```

The Blaschke policy is algebraic: admissible numerator zeros lie inside the
unit disk before Cayley inversion, whereas reciprocal-conjugate denominator
poles lie outside it, so they cannot coincide under the injective map. The
frozen scalar Cayley policy uses the highest exactly nonzero coefficient; its
leading principal part fixes the order at both Cayley pole loci. The authored
additional `1e-30` leading-coefficient regression confirms that numerical
magnitude no longer changes exact order.

These diagnostics remain scoped to equality of rational continuations on a
continuum with an accumulation point. They do not prove separation on a
finite graph spectrum or approximation, optimization, compute, or predictive
superiority. Within that scope, the exact premise can no longer be altered by
a caller tolerance. **GA-27 is accepted.**

## Mandatory-row adjudication

| ID | Verdict | Independent basis |
|---|---|---|
| GA-00 | **ACCEPT** | Public dense/sparse aliases are copies; version-invisible private tampering is hash-rejected before basis, model, and peel multiplication; the recorded graph policy and strict initial validators remain intact. |
| GA-01 | ACCEPT | Radial and center-width roots remain finite, jointly disk-admissible, capped, invertible, and gradient-tested. |
| GA-02 | ACCEPT | Scalar all-pass modulus, positive forward phase derivative, mapped geometry, and Lorentzian law retain exact typed evidence. |
| GA-03 | ACCEPT | Validated exact factors retain two-sided unitarity on all required graph/root fixtures. |
| GA-04 | ACCEPT | One-level complementary frame and matrix-feature energy identities still use complete operators. |
| GA-05 | ACCEPT | Pointwise multilevel partition covers the extended real interval and graph spectra. |
| GA-06 | ACCEPT | Residual-first complete exact analysis remains an isometry at required depths and fixtures. |
| GA-07 | ACCEPT | Dense singular values and condition numbers remain at one within the frozen tolerance. |
| GA-08 | ACCEPT | Additive reconstruction remains separated from unitarity and covers exact, shared finite, and nonunitary factors. |
| GA-09 | ACCEPT | Exact adjoint synthesis and finite defect-bounded synthesis remain explicitly distinct. |
| GA-10 | ACCEPT | Public residual-first order agrees with independent assembly and rejects silent permutation. |
| GA-11 | ACCEPT | Weighted Parseval retains `I`, `L`, `L^2`, fractional spectral, and repeated-eigenspace weights. |
| GA-12 | ACCEPT | Noncommuting node-projector counterexample preserves the non-nodewise boundary. |
| GA-13 | ACCEPT | The actual admissible-root channel retains its scoped separation and recovery inequalities. |
| GA-14 | ACCEPT | Exact complex recovery and full operator-norm approximation triangle bound remain valid. |
| GA-15 | ACCEPT | Exact and finite-polynomial complete coefficients remain permutation equivariant. |
| GA-16 | ACCEPT | Scalar functional calculus remains invariant under repeated-eigenspace basis rotation. |
| GA-17 | ACCEPT | Equal-sized nonisomorphic graphs remain distinct and rebuild graph-specific operators. |
| GA-18 | ACCEPT | First-kind DCT convention, interpolation nodes, zeroth coefficient, and independent recurrence agree. |
| GA-19 | ACCEPT | Sparse application materialized on the identity agrees with the independent dense polynomial operator. |
| GA-20 | ACCEPT | True operator error equals graph spectral maximum and measured errors obey the analytic certificate. |
| GA-21 | ACCEPT | One-level finite-frame spectra and defects use true operator errors and meet the derived bounds. |
| GA-22 | ACCEPT | Multilevel defect, `Delta_D`, spectra, additive reconstruction, and bounded adjoint synthesis retain required fixture/depth/degree coverage. |
| GA-23 | ACCEPT | Exact center-width geometry and the angular-anchor counterexample remain correctly separated. |
| GA-24 | ACCEPT | Exact target mapped poles remain distinct from the pole-free finite Chebyshev realization; the row remains descriptive. |
| GA-25 | ACCEPT | Stable nonzero-root Product-sum interpolation and its disclosed ill-conditioned boundary remain explicit. |
| GA-26 | ACCEPT | Repeated-eigenspace incompatible targets retain a substantive nonzero residual limitation. |
| GA-27 | **ACCEPT** | Root/module exact APIs reject all tested tolerance aliases and preserve the far Blaschke pole and arbitrarily small nonzero Cayley order under v2 algebraic schemas. |
| GA-28 | ACCEPT | Fixed-root aligned graph perturbations remain bounded by the explicit resolvent constant over the contracted margins/scales. |
| GA-29 | ACCEPT | Finite polynomial hop locality and generally dense exact rational response remain separately demonstrated. |
| GA-30 | ACCEPT | Instrumentation retains the `DK` complex-feature SpMV count and residual-first storage record. |
| GA-31 | ACCEPT | Exact and shared finite complete coefficients retain the scoped node-pair lower bound. |
| GA-32 | ACCEPT | The zero-mode counterexample continues to refute carried-state non-dissipation while retaining the residual. |
| GA-33 | ACCEPT | Exact complete-map global Jacobian column norms remain one. |
| GA-34 | ACCEPT | Connected, disconnected, and beyond-reach witnesses preserve the global-versus-target sensitivity distinction. |
| GA-35 | ACCEPT | Canonical variants retain parameter identity and optimizer membership through the first forward/backward. |

## Claim boundary and authorization

Gate A now supports only the frozen conclusions: exact complete-map algebra,
pointwise and weighted Parseval identities, conditioning and reconstruction,
finite-realization frame certificates, fixed-root aligned perturbation bounds,
and scoped locality/cost statements. The complete coefficient isometry is a
global injectivity/conditioning result. It is not a carried-state guarantee,
a target-specific sensitivity lower bound, or evidence that the trained model
solves oversmoothing or oversquashing.

Downstream work may proceed only after the orchestrator records this review
through the corrected acceptance-token mechanism and satisfies every other
independent infrastructure/protocol dependency. This review does not itself
authorize H100 execution and does not override baseline, official-protocol,
artifact, scheduler, evaluator, leakage, or run-plan gates.

## Acceptance-token note

Commit `a8be64d` adds all discovered `test_gate_a*.py` modules, including the
token regression itself, to `PROTECTED_PATHS`. I reviewed that small change
and its regression. Any acceptance token must bind this exact reviewed commit
or a separately re-reviewed descendant and must use the corrected protected
set. No token was created by this review.

