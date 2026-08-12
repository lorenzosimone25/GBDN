# REV-GATEA-FINAL-1 — independent adversarial Gate-A review

## Scope and binary verdict

- Implementation base: `e5edf72bfe2920834cfcbb8f4fec53935e6b719f`
- Review branch: `agent/reviewer/REV-GATEA-FINAL-1`
- Governing contract: `sub_plans/01_SCIENTIFIC_CONTRACT.md` and
  `math/theorem_to_test_contract.md`
- Reviewed in full: the theorem ledger, proof audit, counterexample register,
  Phase-0 math audit, prior Gate-A reviews and engineering handoffs, canonical
  `src/gbdn`, every `test_gate_a*.py` file, the Gate reporter, and the current
  manuscript theory as claim context
- Later theory-only context: `a19e9cd` / `708837e`, which adds the verified
  first-kind Chebyshev aliasing derivation and citation but no Gate-A code

**Binary verdict: GATE A IS BLOCKED.**

All 36 named IDs execute, and all numerical tests pass. That is useful
regression evidence, not scientific Gate-A acceptance. The machine-readable
report itself correctly returns `accepted=false`: 35 of 36 rows have no
structured residual/provenance record. Several mandatory rows also test a
weaker object than their contract, and a tracked, non-legacy-labeled helper in
`src/gbdn/synthetic.py` still constructs an asymmetric directed-kNN
“Laplacian” and applies a Hermitian eigensolver without validation.

I found no counterexample to the frozen exact algebra, the heterogeneous
finite-frame recurrence, the first-kind Chebyshev bound, the fixed-root
resolvent bound, or the negative oversquashing boundary. The block is an
implementation/evidence acceptance failure, not a rejection of the central
mathematical construction.

## Classification standard

- **ACCEPT:** the contracted observable, implementation binding, scope, and
  required machine-readable evidence are adequate at the reviewed commit.
- **CONDITIONAL:** the numerical/theoretical witness is substantively sound,
  but provenance, coverage, or public-API binding is incomplete.
- **REJECT:** the current row does not test the contracted object or a
  canonical package path violates the theorem premise.

## Stop-line findings

### 1. The reporter proves that Gate A has not produced its required evidence

The executed reporter found:

```text
tested commit: e5edf72bfe2920834cfcbb8f4fec53935e6b719f
collected Gate nodes: 410
GA-00--GA-35 execution: all passing
gate_a_acceptance.accepted: false
IDs without machine-readable residuals: 35 of 36
only ID with a structured residual: GA-23
duplicate-mapped IDs: GA-00,02,03,04,05,06,07,09,17,19,20,22,28,30,34,35
```

This is not merely a display issue. `PytestInventory` consumes only a property
named `gate_a_metrics` (`src/gbdn/gate_a_report.py:473`). GA-22, GA-28, and
GA-30 emit separate properties such as `predicted_delta`,
`observed_to_bound_ratio`, and `observed_spmv_count`, so the reporter silently
discards them (`tests/test_gate_a_approximation.py:376--383,671--674,765--773`).
The resulting report explicitly lists the missing graph hashes, roots,
dtype/device, residuals, and predicted bounds as a blocker
(`src/gbdn/gate_a_report.py:685`).

Fixture, root, and degree coverage are currently hard-coded declarations
(`gate_a_report.py:181,240,352`) rather than records derived from each executed
node. They happen to describe much of the current suite, but a renamed
parameter, changed fixture, or removed assertion can leave a green declaration
without corresponding evidence. The reporter responsibly keeps acceptance
blocked (`gate_a_report.py:743--744`), so no downstream claim-bearing work may
treat its zero process exit code as Gate acceptance.

### 2. GA-00 misses a live graph-contract bypass in the canonical package

The new core boundary is strong: it rejects asymmetric, negative, nonfinite,
and loop-containing direct inputs; the reciprocal-mean preprocessor records
duplicates, loop removal, isolates, and semantic hashes; external operators
receive a one-time self-adjoint/spectral audit and mutation-detecting token.

However, `src/gbdn/synthetic.py:42--66` remains tracked under the canonical
package and is not marked legacy. `sphere_graph_data` constructs a directed
kNN edge list, calls PyG `get_laplacian` directly, and passes the resulting
asymmetric matrix to `torch.linalg.eigh`. A read-only deterministic probe with
`n=50, k=4` produced:

```text
relative Frobenius asymmetry ||L-L^T||_F / ||L||_F = 0.228035
maximum entrywise asymmetry = 0.25
relative residual ||LU-U diag(lambda)||_F / ||L||_F = 0.161245
```

The returned vectors are therefore not eigenvectors of the stored operator.
This recreates the exact Phase-0 failure the validated core was intended to
eliminate. Being currently unused by a runner does not make an unlabeled
scientific helper safe. It must be routed through the recorded preprocessor or
moved behind an explicit legacy boundary before GA-00 can pass package-wide.

`src/gbdn/peel.py` is likewise an unlabeled pre-contract utility: it accepts
raw edges through `ChebyshevBasis` and uses a scaled Cayley angular anchor as an
“oracle” root. It should either be migrated to the validated convention or
quarantined with the legacy implementation.

### 3. Public analysis/synthesis correspondence is numerically correct but not a mandatory regression

GA-09 and GA-22 exercise the independent dense oracle, not
`GBDNTight.synthesize` (`src/gbdn/model.py:208`). GA-10 manually constructs a
`TightAnalysisOutput` sentinel (`test_gate_a_core_slice.py:266`) rather than
comparing coefficients emitted by `GBDNTight.analyze_complex` with an
independently assembled residual-first tuple. GA-30 exercises public analysis,
but checks names, count, shape, storage, and SpMVs rather than coefficient
values or synthesis.

A read-only independent probe at `D=3, K=5` found that the current code is
correct:

```text
max public-vs-dense component relative error = 3.41e-16
public-vs-dense adjoint synthesis relative error = 1.99e-16
public approximate reconstruction relative error = 3.049e-3
measured frame defect = 3.473e-3
additive reconstruction relative error = 1.05e-16
```

Thus this finding does not allege a present formula bug. It identifies a
mutation hole: public analysis order, coefficient values, conjugation, or
synthesis can regress while the named GA-09/10/22 rows remain green. The probe
must become a deterministic test, including the readout/artifact ordering
path.

### 4. Four mandatory observables remain weaker than their theorem contracts

#### GA-14: finite-factor recovery

`test_ga14_complex_recovery_identity_and_finite_factor_bound` constructs an
arbitrary response perturbation and uses its realized action norm as the
triangle term. It never constructs exact and finite Blaschke factors, measures
`epsilon_K = ||T_tilde-T||_op`, or verifies the advertised
`epsilon_K ||h||/2` contribution. The exact spectral decomposition is tested;
the finite-factor theorem binding is not.

This is the mandatory defect. A minimal accepting fixture must use one fixed
self-adjoint `L`, an exact factor `T=t(L)`, and its actual degree-`K`
realization `T_tilde`. With

```text
q       = (I - T) / 2,
q_tilde = (I - T_tilde) / 2,
epsilon_K = ||T_tilde - T||_op,
```

it must (i) evaluate the exact squared spectral recovery identity and (ii)
check

```text
||q_tilde h - h_S||_F
 <= sqrt(delta^2 ||h_S||_F^2 + eta^2 ||h_Sc||_F^2)
    + (epsilon_K / 2) ||h||_F,
```

where `delta=max_{lambda in S}|q(lambda)-1|` and
`eta=max_{lambda outside S}|q(lambda)|`. `epsilon_K` must be the full operator
norm, not a realized one-vector error. More roots, graphs, and signals are
useful robustness extensions; they are not the missing formula in this row.

#### GA-25: exact Product-sum interpolation and conditioning

The current stable five-point exact witness is mathematically valid: its roots
are nonzero and admissible, its evaluation matrix has rank `m` and condition
number below `1e8`, and the solved interpolation residual is below `1e-10`.
It nevertheless does not *report* its singular values, rank, condition number,
or residual, and it omits the explicitly contracted ill-conditioned case. An
independent clustered-spectrum probe gave minimum singular value `9.98e-17`
and condition number `5.01e16`, showing why the missing negative diagnostic is
material: exact full-rank existence is not stable expressivity.

The minimum accepting exact-row test is precise. For
`V[j,l]=q_l(mu_j)`, it must emit every singular value, numerical rank,
`kappa(V)`, and `||V c-y||/||y||`. A deterministic nonzero-admissible-root
witness must have rank `m` and residual at most `1e-10` when
`kappa(V)<=1e8`. A second deliberately ill-conditioned spectrum/root fixture
must emit its small singular value and large condition number without hiding,
discarding, or applying the stable residual threshold to it.

Finite raw-logit reachability is not a missing hypothesis of this exact E8
row when the directly supplied nonzero roots lie strictly inside the frozen
radius cap: GA-01 owns the parameterization map, and each such radial-polar
root has a finite preimage. Exercising that route is a useful API
correspondence check. Repeated/permuted roots are useful conditioning/basis
stress tests, while repeated eigenvalues have their own mandatory GA-26 row.
Most importantly, finite-`K` degradation belongs to the polynomial-realization
mechanism study, not the exact finite-spectrum interpolation theorem. None of
those useful extensions is used here as the reason for rejecting GA-25; the
rejection is solely the missing contracted conditioning report and
ill-conditioned diagnostic.

#### GA-27: reduced-pole comparison

The test proves that one GBDN target pole has nonzero real part, and its
`pole != zero` check is adequate to exclude cancellation for that single
linear factor. It does not encode the frozen scalar CayleyNet response,
learned shared scale, reduced comparator pole multiset, or effective order.
The off-axis witness is therefore only one side of T-F, not the contracted
reduced-pole comparison. The generic continuum theorem remains mathematically
valid, but GA-27 cannot promote a comparator-specific claim by itself.

A minimal acceptance test must freeze a machine-readable rational comparator
family `F_S` (including its allowed order and learned-scale convention), derive
and reduce its numerator/denominator, and report its reduced pole multiset
`S`. It must likewise reduce the exact GBDN factor or channel actually named in
the claim, demonstrate that a surviving mapped pole `p_alpha` is not in `S`,
and explicitly verify that the pole was not cancelled. The record must be
tagged `exact/continuum`; sampled-grid inequality is neither required nor
sufficient. If the family is named CayleyNet, its real-response formula and
scale convention first need the already-required primary-source audit; a
comment asserting the `+/- i/h` locus is not an executable frozen comparator.
Testing approximation efficiency remains Gate C work, not GA-27.

#### GA-10: coefficient correspondence

The sentinel catches a local `components` property permutation but does not
exercise model-emitted values, independent assembly, readout concatenation,
synthesis input, or artifact serialization. The frozen contract explicitly
requires correspondence across these consumers.

The narrow GA-10 row has a smaller mandatory core: run public
`GBDNTight.analyze_complex`, independently assemble
`(r_0,...,r_{D-1},h_D)` from the stored roots/operators, compare every named
component value and the concatenated public tuple in exactly that order, and
show that a deliberately carry-first (or otherwise permuted) tuple fails the
same semantic comparison unless an explicit tested permutation is applied.
Readout concatenation, synthesis ingestion, flatten/unflatten, and artifact
serialization are separate Gate-wide R3 integration guards required by the
preflight; their absence should not be confused with the narrower reason the
present GA-10 test fails, namely that it compares two hand-written sentinel
views rather than public output to an independent tuple.

### 5. Finite-realization coverage is narrower than the exact matrix

The exact graph/root/depth matrix is unusually thorough: two paths, even and
odd cycles, grid, star, complete, disconnected, deterministic weighted random
graph, five root families, and depths `1,2,4,8,16`. GA-19 also checks full
sparse operators at degrees `4,8,16,32,128` on several graphs.

By contrast, GA-20, GA-21, and GA-22 use paths only; GA-21 has one
root/degree, and the finite multilevel frame test has no cycle/repeated-spectrum,
weighted, or disconnected fixture. The theorem is valid for these cases, but
the user's Gate-A instruction requires the finite-frame tests on multiple
graph families and depths. Add at least a repeated-spectrum graph and a
nonuniform weighted graph to the finite-frame matrix.

GA-24 now correctly joins measured graph/grid error, degree, chosen ellipse,
pole-limited ellipse, a clearly named conservative `M_rho` upper bound, and
geometry. Its serialized field `root_pole_geometry` should nevertheless be
renamed `target_root_pole_geometry` or paired with an explicit
`geometry_scope="exact-target"`: the same record is tagged `chebyshev-K`, whose
polynomial realization has no literal finite poles.

### 6. GA-35 passes lifecycle timing but not optimization usefulness

All parameters exist before optimizer construction and their identities remain
stable after the first forward/backward pass. GA-35 therefore tests its stated
lifecycle risk correctly. Separately, `GBDNProductSum` initializes all
nonconstant coefficients to zero (`src/gbdn/model.py:276--278`), so every root
gradient is exactly zero on the first backward pass. The coefficient gradients
are nonzero and can unlock roots after an update; this is not a GA-35 failure,
but it is a Gate-B optimization risk that should be measured rather than
mistaken for immediate root learning.

## Mathematical and claim-scope audit

### Results that survive

| Result | Classification | Independent assessment |
|---|---|---|
| Root admissibility and mapped center/width | **PROVED** | Radial-polar and bounded center-width maps are correct for finite parameters. |
| Unit modulus, mapped zero/pole, Lorentzian phase law | **PROVED** | Formula, conjugation, sign, and product additivity are correct. |
| Exact complementary split | **PROVED; algebraically standard** | Unitary functional calculus gives the Parseval half-split; neither channel is generally a projection. |
| Pointwise multilevel partition | **PROVED; algebraically standard** | Residual-first scalar telescoping is correct on the full real line. |
| Complete exact isometry, conditioning, adjoint synthesis | **PROVED** | Fixed roots and fixed self-adjoint `L`; complete tuple and analyzed lift only. |
| Weighted spectral Parseval | **PROVED WITH COMMUTATION** | Correct for positive weights commuting with every level, including functions of `L`; node projectors are excluded. |
| Nodewise coefficient lower bound | **PROVED; weak** | Follows from additive reconstruction, including shared approximate factors; not an anti-oversmoothing theorem. |
| Chebyshev mapped-pole bound (T-E) | **PROVED WITH ANALYTIC ASSUMPTIONS** | `M_rho` is indispensable; the bound is a certificate, not an efficiency result. |
| Heterogeneous finite-frame recurrence (T-D) | **PROVED WITH TRUE OPERATOR ERRORS** | Prefix-product indexing, `Delta_D<1` lower-bound condition, and adjoint-defect consequence are correct. |
| Product-sum finite-spectrum basis theorem | **PROVED WITH SCOPE LIMITS** | Continuity from the zero-root Vandermonde witness is sound; conditioning may be arbitrarily poor. |
| Generic reduced-pole separation (T-F) | **PROVED WITH ADDITIONAL ASSUMPTIONS** | Continuum identity, reduced noncancelled poles, and a frozen comparator locus are essential; no finite-spectrum or efficiency implication. |
| Fixed-root perturbation bound (T-G) | **PROVED WITH ADDITIONAL ASSUMPTIONS** | Resolvent constant and unitary product telescoping are correct for aligned self-adjoint operators and fixed roots. |
| Locality/cost (T-H) | **PROVED FOR THE DECLARED RECURRENCE** | Degree/reach at most `DK`; measured implementation uses exactly `DK` complex-feature sparse calls under its stated convention. |
| Global complete-analysis sensitivity | **PROVED** | Column norms are one for the fixed exact linear map; this is a global complete-output statement. |

### Later first-kind attribution patch

The theory-only derivation in `a19e9cd` / `708837e` is correct. With
`N=K+1`, first-kind angles `theta_j=(j+1/2)pi/N`, and
`m=2qN+s`, `0<=s<2N`, the aliases are

```text
I_K T_m = (-1)^q T_s                  for 0 <= s < N,
          0                            for s = N,
          (-1)^(q+1) T_(2N-s)         for N < s < 2N.
```

Thus `||I_K T_m||_infinity <= 1`. Combining this with the cited coefficient
bound `|a_m| <= 2 M_rho rho^{-m}` and summing from `m=N` gives
`4 M_rho rho^{-K}/(rho-1)`. The indexing and node convention match the code.
T-E is therefore not rejected for the former citation gap. This paper-only
patch does not change the implementation verdict at `e5edf72`.

### Claims that remain limited or rejected

| Claim | Classification | Decision |
|---|---|---|
| Complete exact analysis is globally injective/conditioned | **PROVED** | Safe with fixed roots, fixed `L`, and complete representation. |
| Practical anti-oversmoothing | **EMPIRICAL ONLY** | Gate A supplies boundaries, not a depth-dependent empirical result. |
| Carried-state non-dissipation | **FALSE / REMOVE** | GA-32 correctly preserves the zero-mode annihilation counterexample. |
| Every-target source sensitivity | **FALSE / REMOVE** | Connected, disconnected, and finite-hop witnesses remain valid. |
| Tightness mitigates oversquashing | **FALSE / REMOVE** | Global norm preservation gives no target-block lower bound. |
| Movable poles improve approximation/SpMV efficiency | **UNSUPPORTED** | Requires matched Gate-B/C distributions, not T-E or T-F alone. |
| Heterophily implies high-frequency or long-range mechanism | **UNSUPPORTED / REMOVE** | Requires separate measurements. |

## Oracle independence, tolerances, and semantics

- `src/gbdn/oracle.py` does not import the sparse layer or production spectral
  recurrence. Its exact scalar factor, dense Chebyshev recurrence, block
  analysis, and adjoint recursion are structurally independent enough for
  small-graph checks.
- Production-to-oracle bridges exist for the scalar convention and full sparse
  polynomial operator. The public multilevel bridge is missing from the
  committed tests but passed the independent probe above.
- Exact tests use float64/complex128 and the contracted tolerances. Sparse
  tests materialize full operators rather than sampled vectors. GA-20 uses
  true operator error and independently reconstructs every analytic-bound
  component.
- Additive reconstruction and adjoint synthesis are now separated. The
  `Delta_D>=1` case correctly suppresses a positive lower-frame claim.
- GA-29 uses the narrow wording “not `K`-hop localized,” not universal
  density. GA-30 explicitly states that one complex-feature
  `torch.sparse.mm` call counts as one SpMV and reports coefficient tensor
  storage only.
- The perturbation tests hold roots fixed, align vertex spaces, rebuild
  symmetric normalized Laplacians, and do not imply retraining or unmatched
  graph stability.

## Row-by-row adjudication

| ID | Verdict | Evidence and reason |
|---|---|---|
| GA-00 | **REJECT** | Core rejection/preprocessing tests are strong, but `src/gbdn/synthetic.py::sphere_graph_data` silently creates an asymmetric operator and invalid eigendecomposition outside the validated boundary. |
| GA-01 | **CONDITIONAL** | Radial cap, center-width inverse, endpoint-like logits, and finite gradients pass; required structured record is absent, and radial gradient evidence is not emitted. |
| GA-02 | **CONDITIONAL** | Production/oracle convention, unit modulus, mapped geometry, derivative, additivity, permutation, and all root fixtures pass; no row provenance. |
| GA-03 | **CONDITIONAL** | Two-sided exact unitarity passes the complete graph/root matrix; per-node graph hashes, roots, and residuals are absent. |
| GA-04 | **CONDITIONAL** | Operator split and multi-feature energy pass the complete matrix; evidence record absent. |
| GA-05 | **CONDITIONAL** | Full-real-grid and every fixture spectrum partition pass at depth 16; row metadata/residual absent. |
| GA-06 | **CONDITIONAL** | Dense block isometry and energy pass graph/root/depth cross-product; reporter records no observed defects. |
| GA-07 | **CONDITIONAL** | All singular values/condition numbers pass the same matrix; values are not retained in the report. |
| GA-08 | **CONDITIONAL** | Exact, approximate, and deliberately nonunitary shared splits telescope; only a dense/manual output path is recorded. |
| GA-09 | **CONDITIONAL** | Independent exact adjoint equals explicit `A*` and reconstructs across fixtures/depths; public `GBDNTight.synthesize` is not in the regression and provenance is absent. |
| GA-10 | **REJECT** | Manual dataclass sentinels never compare the public model tuple with independently assembled `(r_0,...,r_{D-1},h_D)`, and the permutation check is therefore not a public-value correspondence test. Readout/artifact consumers are separate Gate-wide R3 guards. |
| GA-11 | **CONDITIONAL** | `I`, `L`, `L^2`, `L^0.5`, and a whole repeated-eigenspace projector pass; no structured energies or commutator metadata. |
| GA-12 | **CONDITIONAL** | Deterministic noncommuting node-projector counterexample is correct; evidence record absent. |
| GA-13 | **CONDITIONAL** | Matrix-valued target/complement inequalities use a complete repeated eigenspace; results are not emitted. |
| GA-14 | **REJECT** | Exact decomposition passes, but the finite test does not construct actual `T,T_tilde`, measure `epsilon_K=||T_tilde-T||_op`, or verify the contracted `(epsilon_K/2)||h||` term. |
| GA-15 | **CONDITIONAL** | Exact and finite coefficient tuples permute with edges/features/operators; public model synthesis/diagnostics and row provenance are not covered. |
| GA-16 | **CONDITIONAL** | Complete-graph eigenspace rotation and scalar multiplier invariance pass; residual/basis metadata absent. |
| GA-17 | **CONDITIONAL** | Equal-size graph state safety and deterministic noncolliding validated hashes pass; report does not attach hashes to nodes. |
| GA-18 | **CONDITIONAL** | First-kind node/DCT zeroth convention and independent dense recurrence pass; only one degree-12 convention fixture and no structured residual. |
| GA-19 | **CONDITIONAL** | Full sparse-versus-dense operators pass degrees `4,8,16,32,128` on multiple graphs/roots; evidence remains static rather than node-bound. |
| GA-20 | **CONDITIONAL** | True operator error, graph spectral max, interval-grid max, pole ellipse, conservative `M_rho`, and final bound are independently checked for degrees `4,8,16,32` and three root families; path-only and no report payload. |
| GA-21 | **CONDITIONAL** | True epsilon and frame spectrum satisfy the one-level theorem; only one path/root/degree and no emitted diagnostic. |
| GA-22 | **CONDITIONAL** | Recurrence formula, depths, singular values, actual dense adjoint synthesis, additive reconstruction, and `Delta>=1` boundary are sound; path-only, public synthesis absent, and emitted properties are ignored by the reporter. |
| GA-23 | **ACCEPT** | Exact center, HWHM, pole, admissible ellipse, and frozen angular-anchor counterexample are correct and this is the only row with a complete structured `gate_a_metrics` record. |
| GA-24 | **CONDITIONAL** | Joined configuration and independent formulas are correct; rename serialized pole geometry as exact-target geometry and emit it through the Gate report. |
| GA-25 | **REJECT** | The stable exact witness passes, but its singular spectrum/condition/residual are not reported and the explicitly mandatory ill-conditioned case is absent. Finite-logit routing and finite-`K` degradation are broader checks, not defects in this exact row. |
| GA-26 | **CONDITIONAL** | The two-target scalar least-squares impossibility is algebraically correct; bind it to an actual repeated-eigenspace graph/operator and emit the residual. |
| GA-27 | **REJECT** | The one-factor GBDN pole is off-axis and noncancelled, but no executable frozen comparator formula, reduced comparator pole multiset, or scale/order convention is encoded. |
| GA-28 | **CONDITIONAL** | Independent constant and inequality pass one-/two-root cases and three perturbation scales; properties are discarded by the reporter and graph-family coverage is narrow. |
| GA-29 | **CONDITIONAL** | Polynomial outside-hop zeros and a non-`K`-localized exact witness are correctly scoped; no node-bound metric record. |
| GA-30 | **CONDITIONAL** | Actual canonical analysis passes four `(D,K)` pairs, exact `DK` complex-SpMV counts, residual-first storage/order, and byte accounting; reporter ignores the emitted properties and its degree declaration is stale. |
| GA-31 | **CONDITIONAL** | All selected pairs satisfy the exact/shared-approximate additive lower bound; one graph/depth and no emitted extrema. |
| GA-32 | **CONDITIONAL** | Zero-mode carry annihilation and residual preservation correctly refute carried-state non-dissipation; no structured residual. |
| GA-33 | **CONDITIONAL** | Dense exact Jacobian column norms equal one; no per-column extrema/provenance record. |
| GA-34 | **CONDITIONAL** | Connected endpoint, disconnected component, and beyond-reach polynomial boundaries all pass while global norm remains one; metrics are not retained. |
| GA-35 | **CONDITIONAL** | Parameter sets/IDs and optimizer membership are stable for all canonical variants; emit lifecycle evidence and separately track Product-sum's zero first-step root gradients in Gate B. |

## Minimal repair set for re-review

1. **Repair or quarantine every graph-contract bypass.** Route
   `sphere_graph_data` through `preprocess_reciprocal_mean` and its validated
   token, or move `synthetic.py`/`peel.py` behind an explicit legacy namespace
   that cannot feed canonical experiments. Add the asymmetric sphere witness
   to GA-00.
2. **Make every GA row emit one validated `gate_a_metrics` payload.** Include
   ID, realization tag, graph hash or explicit scalar N/A, roots and
   parameterization, depth, degree, dtype, device, absolute/relative residual,
   tolerance, predicted bound, observed quantity, source commit, and test
   node. Reject missing/nonfinite fields.
3. **Derive coverage from executed payloads.** Do not accept hard-coded fixture,
   degree, depth, or root declarations without matching node records. Make an
   acceptance-mode report exit nonzero whenever `accepted=false`.
4. **Bind the public method to the independent oracle.** For GA-10, compare
   public residual-first values with an independently assembled tuple and make
   a deliberate permutation fail. Also complete the broader R3 integration
   guards for readout concatenation, synthesis input, flatten/unflatten, and
   artifact serialization.
5. **Repair GA-14.** Construct an exact factor and its actual Chebyshev
   realization, set `epsilon=||T_tilde-T||_op`, and verify the exact squared
   identity plus the total bound containing `(epsilon/2)||h||`.
6. **Repair the exact GA-25 row.** Emit the stable witness's singular values,
   rank, condition number, and interpolation residual, then emit a deliberately
   ill-conditioned case without applying the stable threshold. Finite-logit
   routing, repeated/permuted-root stress, and finite-`K` degradation remain
   useful broader mechanism checks; they are not GA-25 acceptance predicates.
7. **Complete GA-27.** Freeze a machine-readable rational comparator family
   and scale/order convention; reduce both pole multisets, check
   noncancellation and `p_alpha not in S`, and tag the witness as
   exact/continuum-only.
8. **Broaden finite-frame fixtures.** Add repeated-spectrum and nonuniform
   weighted graph cases to GA-21/22 across representative depths/degrees.
9. **Make exact-target pole semantics explicit in serialized finite records.**
   Rename `root_pole_geometry` or add a required exact-target scope field.

After these repairs, rerun the full suite and reporter from a clean commit and
obtain a second independent review. Gate B smoke experiments may proceed only
after that review returns a binary pass.

## Execution evidence

```text
command: canonical .venv Python, PYTHONPATH=<review worktree>/src,
         pytest all six test_gate_a*.py files -q -p no:cacheprovider
result: 427 passed

command: canonical .venv Python, PYTHONPATH=<review worktree>/src,
         pytest tests -q -p no:cacheprovider
result: 447 passed, 2 upstream torch.jit deprecation warnings

command: canonical .venv Python, PYTHONPATH=<review worktree>/src,
         python scripts/report_gate_a.py
result: exit 0 for pytest execution; all IDs executed/passing;
        accepted=false; status=BLOCKED; 35 IDs lack structured residuals

command: independent public analysis/synthesis versus dense-oracle probe
result: component and synthesis correspondence approximately 1e-16;
        approximate reconstruction 3.049e-3 <= frame defect 3.473e-3

command: directed sphere-helper audit, n=50, k=4
result: relative asymmetry 0.228035; eigensystem residual 0.161245

command: Product-sum clustered-spectrum conditioning probe
result: sigma_min 9.98e-17; condition number 5.01e16
```

No H100 experiment, paper edit, source edit, test edit, or result mutation was
performed.
