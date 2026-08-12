# Independent review of the Gate-A finite-realization slice

## Scope and verdict

- Review task: `REV-GATEA-APPROX-1`
- Integrated base: `c0f58b52cf24bba2d867ecff03eb8f710f1c3997`
- Approximation commit: original `4145910c31af36c93ee89c399e0e783caf3213b7`,
  cherry-picked as `9c11ea9`
- Files under direct review: `src/gbdn/diagnostics.py` and
  `tests/test_gate_a_approximation.py`
- Contract: `math/theorem_to_test_contract.md`, especially GA-18 and
  GA-20--GA-30

**Verdict: BLOCKED.** The diagnostic formulas for the Bernstein ellipse,
conservative ellipse supremum, heterogeneous frame recurrence, and fixed-root
resolvent constant are mathematically valid for admissible inputs. The test
file is nevertheless not an acceptable Gate-A slice at the integrated commit:

1. GA-30 raises an `AttributeError`, so the file has 22 passes and one failure.
2. GA-24 omits both approximation error and $M_\varrho$, the two quantities
   that make its contracted observable an approximation-ordering diagnostic.
3. GA-22 renames the already-computed frame defect as an "adjoint
   reconstruction error" instead of exercising synthesis or a signal.
4. Several tests prove only that a generously inflated upper bound remains an
   upper bound. They do not independently pin the claimed formula and can
   false-pass materially wrong diagnostics.
5. None of these rows emits the machine-readable provenance required for a
   Gate-A PASS, and fixture/root coverage is only a small regression subset.

This verdict does not reject the underlying theorems. It rejects promotion of
these test names to GA-18/20--30 acceptance.

## Stop-line findings

### 1. GA-30 fails against the integrated validated-operator API

At `tests/test_gate_a_approximation.py:370`, the test calls
`laplacian.float()`. At the reviewed base, `normalized_laplacian` returns a
`ValidatedLaplacian`, which deliberately exposes a validated tensor through
its token API and has no `.float()` method. The test therefore fails before
instrumenting a single SpMV:

```text
AttributeError: 'ValidatedLaplacian' object has no attribute 'float'
```

The underlying `ChebyshevBasis` accepts the token and performs the dtype
conversion after validated unwrapping. The test must use the integrated API
without bypassing the token. This is an integration failure in the reviewed
tree, regardless of whether the original pre-token approximation branch once
passed.

Even after the crash is fixed, the row will remain partial: it checks one
`D=4, K=5` analysis and the number/order of component objects, but does not
record coefficient storage, bytes, complex-versus-real accounting, or multiple
depth/degree configurations.

### 2. GA-24 does not measure GA-24

The contract requires a descriptive record of approximation **error versus**
root radius, angle, pole ellipse, and $M_\varrho$. The implementation
`target_pole_diagnostics` returns only:

- root radius and angle;
- mapped zero/pole coordinates;
- interval pole margin;
- Bernstein parameter.

It returns neither a degree, a realized approximation error, a chosen
$\varrho$, nor $M_\varrho$ (or the explicitly named conservative upper
bound used in its place). The test checks only key names, finiteness, and
signs. A function returning fabricated but plausible constant geometry would
pass.

GA-24 is therefore **NOT IMPLEMENTED**, not PASS. It needs a configuration-level
record joining target geometry to degree, coefficients, graph/interval error,
chosen ellipse, and actual or certified ellipse supremum. Because GA-24 is
descriptive, no monotonic success threshold is required, but the emitted
quantities must be independently verified and provenance-complete.

### 3. GA-22's reconstruction assertion is tautologically duplicated

The test correctly materializes an approximate residual-first analysis matrix
and computes

```text
observed = ||A_tilde^* A_tilde - I||_op.
```

It then assigns the same matrix norm to a variable named
`adjoint_reconstruction_error` and repeats the same inequality. This is not an
independent synthesis observable. It neither applies the canonical adjoint
synthesis implementation nor evaluates

```text
||A_tilde^* A_tilde h - h|| / ||h||
```

on a deterministic signal. The operator defect is a stronger uniform upper
bound, but relabeling it does not test paper--implementation correspondence for
synthesis.

The test also omits:

- a case with `Delta_D >= 1` showing that no positive lower-frame statement is
  emitted;
- all singular values requested by the frame-validation details;
- shared-approximate additive reconstruction;
- an independent direct check of the exact heterogeneous prefix-product
  formula;
- a deliberately heterogeneous/noncommuting diagnostic that is sensitive to
  recurrence indexing.

With the selected same-(L) polynomial factors, the observed-to-predicted ratio
falls from approximately 0.524 at depth 1 to 0.028 at depth 16. A wrong but
larger recurrence can therefore pass easily. Add a closed-form diagnostic unit
case with heterogeneous errors and an adversarial matrix cascade, in addition
to the canonical graph case.

## Formula audit of `diagnostics.py`

### `multilevel_frame_bound`

**Formula verdict: correct.** It implements

\[
d_\ell=\epsilon_\ell+\epsilon_\ell^2/2,
\qquad
c_\ell=(1+\epsilon_\ell/2)^2,
\qquad
\Delta_D=\sum_\ell d_\ell\prod_{j<\ell}c_j.
\]

The prefix is updated after adding level `ell`, so the indexing agrees with
the residual-first recurrence. `positive_lower_bound` correctly uses the
strict condition `delta < 1`.

Robustness gaps:

- the helper accepts an empty error sequence and reports a successful positive
  lower bound, although Gate-A evaluated depths are nonempty;
- finite inputs can overflow the accumulated output without a final finiteness
  check;
- the test never checks the returned per-level defects/amplifications against
  an independent frozen formula.

These are diagnostic-contract issues, not a counterexample to T-D.

### `bernstein_ellipse_parameter`

**Formula verdict: correct.** For a shifted pole
$\xi=p-1$, taking the larger modulus of
$\xi\pm\sqrt{\xi^2-1}$ returns the parameter of the ellipse through the
point. Returning one for a point on `[-1,1]` is consistent with the limiting
case.

### `target_pole_ellipse_parameter`

**Formula verdict: correct for valid Blaschke roots.** Taking the minimum over
mapped target poles finds the first pole-limited ellipse. Pure finite Blaschke
products have upper-half-plane zeros and lower-half-plane poles, so factors do
not cancel one another's poles.

The helper does not validate finite complex roots or `|alpha|<1`. For example,
an inadmissible root of modulus 1.2 is accepted and produces a finite ellipse
parameter. Gate-facing diagnostics should reject configurations outside the
root contract rather than rely on every caller to do so.

### `conservative_ellipse_supremum_bound`

**Formula verdict: valid but deliberately restrictive.** Under
$x=\lambda-1$, the Bernstein ellipse is contained in
$|x|\le a=(\varrho+\varrho^{-1})/2$. For one reduced factor,

\[
\left|\frac{\lambda-z}{\lambda-p}\right|
\le
\frac{|z-1|+a}{|p-1|-a},
\]

when the denominator is positive; the omitted rational prefactor has modulus
one. Multiplying these bounds is valid. Rejecting a pole that lies outside the
ellipse but inside its circumscribed disk is conservative, not incorrect.

For the GA-20 root and `rho=1.5`, the helper gives $\overline M=3.468$,
while a 200,000-point ellipse sample gives approximately 1.474. The certified
quantity must therefore be named an upper bound on $M_\varrho$, not the
actual ellipse maximum.

### `chebyshev_interpolation_error_bound`

**Formula verdict: correct under the documented first-kind interpolation
theorem.** The code enforces `rho>1` through the supremum helper and
`rho<rho_pole` explicitly, then returns

\[
4\overline M_\varrho\varrho^{-K}/(\varrho-1).
\]

The current test does not validate the formula's components independently and
the bound is extremely loose for the selected easy root:

| Degree | Interval grid error | Certified bound | Bound/error |
|---:|---:|---:|---:|
| 4 | $3.95\times10^{-3}$ | 5.48 | $1.39\times10^3$ |
| 8 | $1.59\times10^{-5}$ | 1.08 | $6.83\times10^4$ |
| 16 | $2.55\times10^{-10}$ | $4.22\times10^{-2}$ | $1.66\times10^8$ |
| 32 | $8.28\times10^{-15}$ | $6.43\times10^{-5}$ | $7.77\times10^9$ |

Loose certified bounds remain valid, but inequality-only testing has low fault
detection. Add independent checks of the pole parameter, conservative
supremum, and final algebra; include multi-root and near-cap cases where the
analytic assumptions and failure modes matter. Emit both measured error and
bound rather than treating a pass as evidence of approximation quality.

### `distance_to_interval` and `fixed_root_perturbation_constant`

**Formula verdict: correct.** The interval distance handles poles whose real
part lies left, inside, or right of `[0,2]`, and the product constant is

\[
C_\mathcal R=\sum_{\alpha\in\mathcal R}
\frac{|p_\alpha-z_\alpha|}
{\operatorname{dist}(p_\alpha,[0,2])^2}.
\]

The selected perturbation cases are reasonably informative: observed/bound
ratios are about 0.864 for the one-root fixture and 0.760 for the two-root
fixture over all three perturbation scales. Thus GA-28 is not vacuous in the
same way as the analytic Chebyshev bound.

The test still never independently reconstructs the constant from recorded
zeros, poles, and margins. An erroneously inflated constant would pass. It
also asserts only the final inequality and does not emit the contracted ratio,
per-root margins, or provenance.

### `product_sum_evaluation_matrix`

**Formula verdict: correct.** It constructs columns
$(1,q_1,\ldots,q_D)$ with one nonzero admissible root per cumulative factor.
The stable five-eigenvalue witness verifies rank, conditioning, and a solved
interpolation residual.

The test does not exercise or report the mandated ill-conditioned case, finite
raw-parameter reachability, repeated-root behavior, or finite-Chebyshev
degradation. It is a good positive unit witness, not the complete Product-sum
contract.

### `target_pole_diagnostics`

**Individual geometry formulas: correct. Overall GA-24 interface: incomplete.**
Radius, angle, mapped coordinates, interval margin, and ellipse parameter are
computed correctly. The function accepts an empty root tensor and returns an
empty list, contrary to the Gate rule that empty evaluated sets must fail. It
also lacks the approximation/M-bound fields described above.

## Test-by-test adjudication

| Test | Verdict | Independence and theorem correspondence |
|---|---|---|
| GA-18 | **PASS as a unit fixture; not full Gate coverage** | Production node evaluation/DCT are cross-checked against the structurally separate dense matrix recurrence, so a shared zeroth-coefficient mistake is unlikely to self-validate. It uses one path and random coefficient vector only. |
| GA-20 | **PARTIAL** | Exact and approximate dense operators are independently materialized, and operator error equals graph spectral max. The analytic helper is valid, but its inequality is extremely loose, only one easy root/path is used, and assumptions/quantities are not emitted. |
| GA-21 | **PASS as a unit fixture; not full Gate coverage** | Epsilon is a true dense operator norm and the frame operator is assembled independently. One graph/root/degree does not satisfy the fixture matrix. |
| GA-22 | **PARTIAL / reconstruction observable FAIL** | The observed frame defect and `Delta_D` inequality are meaningful. The named reconstruction check is the same expression repeated; formula indexing and the `Delta_D>=1` boundary are not independently tested. |
| GA-24 | **FAIL / NOT IMPLEMENTED** | No approximation error or $M_\varrho$ is emitted; only plausible-sign geometry is checked. |
| GA-25 | **PARTIAL** | Correct stable nonzero-root interpolation witness. No ill-conditioned case is reported, and no independent factor-value check or finite realization is included. |
| GA-26 | **PARTIAL** | The two-row least-squares example proves the scalar algebraic impossibility, but it does not touch a repeated-eigenspace graph/operator fixture. |
| GA-27 | **PARTIAL, claim scope currently safe** | A single exact factor has an off-axis, noncancelled pole, which is outside the scalar CayleyNet imaginary-axis locus for every learned `h>0`. The test does not encode the frozen comparator response, effective order, cancellation rules, real-response pole pair, continuum identity scope, or exact-versus-Chebyshev tag. |
| GA-28 | **PASS as a theorem witness; provenance incomplete** | Fixed roots, aligned operators, multiple scales, and one-/two-root margins are used. Ratios are meaningful. The explicit constant itself is not independently checked or recorded. |
| GA-29 | **PARTIAL** | The polynomial outside-hop maximum is exactly zero. `max(abs(exact[outside]))>tol` proves only that the rational witness is not `K`-hop localized; it does not justify the stronger word "dense." A single nonzero far entry would pass. |
| GA-30 | **FAIL** | Crashes on `ValidatedLaplacian.float()`. After repair it still needs storage accounting and broader `(D,K)` coverage. |

GA-19 is implemented in a different test slice and was not re-adjudicated as
part of this commit-specific review.

## Comparator and claim-scope audit for GA-27

The repository's primary-source audit supports the narrow premise used here:
one published scalar finite-order CayleyNet response has a learned shared
scale `h>0`; its uncancelled rational-continuation poles lie on the imaginary
axis (`{-i/h,+i/h}` for the real response, `-i/h` for the analytic half). A
single admissible GBDN root with a nonzero mapped-pole real part is outside
that locus.

The test comment does not say that CayleyNet poles are globally fixed, and it
does not use equality on a grid, which is good. However, an assertion that a
GBDN pole has nonzero real part is only one premise of T-F. The paper theorem
must still state:

- exact GBDN target, not its Chebyshev polynomial;
- one scalar finite-order CayleyNet response or a frozen finite collection;
- learned but shared `h>0` and the corresponding restricted locus;
- effective order and nonremovable/reduced poles after cancellations;
- equality on a continuum with an accumulation point;
- no finite-spectrum, approximation, efficiency, or network-superiority
  conclusion.

Accordingly, this test may be called an off-axis pole-locus witness. It cannot
be the sole executable evidence for a baseline-specific separation claim.

## False-positive and mutation risks

1. **GA-24:** arbitrary finite values with the expected signs and keys pass;
   numeric correctness is not checked.
2. **GA-22:** multiplying `Delta_D` by a large constant still passes; no exact
   formula fixture constrains the helper, and the reconstruction line is
   duplicated.
3. **GA-20:** a materially wrong approximation can remain below the very loose
   analytic envelope, especially at low degree. Operator/spectral equality
   helps, but it does not validate the bound components.
4. **GA-28:** an inflated perturbation constant passes. The selected ratios
   would detect sufficient underestimation, but not the claimed formula.
5. **GA-29:** one nonzero outside-hop entry passes a test named "dense."
6. **GA-30:** instrumentation is tied to `torch.sparse.mm`; an implementation
   switching sparse kernels would evade the counter unless the instrumentation
   abstraction is updated.

These risks do not require every theorem test to be tight. They require an
independent equality check for diagnostic formulas plus inequality checks for
their consequences.

## Fixture and provenance gap

The file contains deterministic unit fixtures, but it does not satisfy the
Gate-wide acceptance matrix:

- GA-20--GA-22 and GA-29 use only paths;
- the analytic bound uses one moderate complex root, not real, multi-root,
  conjugate, near-cap, radial, and center-width fixtures;
- no high-order convergence case beyond degree 32 is present;
- no test record contains graph hashes, realization tags, root
  parameterization, source commit, absolute/relative residuals, or device;
- no machine-readable summary marks every required test PASS/FAIL/NOT_RUN;
- descriptive diagnostics are not saved as immutable artifacts.

Therefore even the individually sound tests must be classified as regression
evidence until the orchestrated matrix and report exist.

## Mandatory fixes before re-review

1. Repair GA-30 against the integrated validated-Laplacian API and parameterize
   multiple `(D,K)` pairs; record SpMV and coefficient-storage accounting.
2. Redesign GA-24 around a joined approximation diagnostic containing degree,
   interval/graph error, chosen `rho`, pole-limited `rho_*`, actual or certified
   `M_rho`, radius, angle, and target pole geometry.
3. Add independent exact-value tests for every diagnostic formula, including a
   heterogeneous `Delta_D` fixture and per-root perturbation constants.
4. Make GA-22 apply actual adjoint synthesis to deterministic analyzed
   coefficients/signals, test additive reconstruction separately, report all
   singular values, and include a `Delta_D>=1` boundary case.
5. Extend GA-20 to multi-root and near-pole cases, independently validate the
   conservative ellipse supremum, and emit how loose the certified bound is.
6. Freeze GA-27's comparator specification in data/metadata and label the test
   as an exact continuum pole-locus witness, not finite-spectrum separation.
7. Rename GA-29's exact assertion as "not finitely `K`-hop localized" or test a
   declared set of far entries before using "dense."
8. Add invalid/empty/nonfinite diagnostics tests and enforce admissible roots
   at public diagnostic boundaries.
9. Run the required graph/root/depth/degree fixture matrix and generate the
   machine-readable Gate-A report with immutable provenance.

## Final recommendation

Do not merge a Gate-A acceptance status for this slice. The production
diagnostic formulas are useful and, under valid inputs, mathematically sound.
After the GA-30 API break and GA-24/GA-22 observable mismatches are repaired,
this file can serve as a compact regression layer. It still needs the
orchestrated fixture/provenance layer before any of GA-18 or GA-20--GA-30 may
be marked globally PASS.
