# GBDN Submission Execution Board

The orchestrator maintains this file. Agents may propose status changes in handoffs but do not mark their own work `DONE`.

## Status legend

- `BACKLOG`
- `READY`
- `IN_PROGRESS`
- `REVIEW`
- `BLOCKED`
- `REJECTED`
- `DONE`

## Milestone board

| ID | Task | Owner | Dependencies | Required output | Status |
|---|---|---|---|---|---|
| ORCH-001 | Record repository commit, tree, environment, and frozen legacy paths | Orchestrator | — | `PHASE0_AUDIT.md`; `results_submission/reports/phase_0_manifest.json` | DONE |
| ORCH-002 | Locate LaTeX source and map paper section files | Orchestrator | ORCH-001 | Path map in `PHASE0_AUDIT.md` | DONE |
| ORCH-003 | Create branch/ownership and handoff directories | Orchestrator | ORCH-001 | Orchestrator plus three isolated role worktrees | DONE |
| REV-001 | Audit current paper–repository correspondence | Reviewer | ORCH-001, ORCH-002 | `reviews/phase0_correspondence_review.md`; `handoffs/REV-001.md` | DONE |
| PH0-MATH-001 | Independently audit current theorem/proof state and candidate counterexamples | Math | ORCH-001, ORCH-002 | `math/phase0_theorem_audit.md`; `handoffs/PH0-MATH-001.md` | DONE |
| PH0-ENG-001 | Independently inventory legacy/canonical implementation, tests, notebooks, artifacts, and hazards | Engineer | ORCH-001 | `reviews/phase0_engineering_inventory.md`; `handoffs/PH0-ENG-001.md` | DONE |
| SCI-001 | Freeze canonical notation and method variants | Orchestrator + Math | REV-001 | Accepted scientific contract | DONE |
| MATH-001 | Audit all current theorem statements and proofs | Math | SCI-001 | `math/theorem_ledger.md`; proof/counterexample/test ledgers | DONE |
| MATH-002 | Add additive versus adjoint reconstruction distinction | Math | MATH-001 | Proof and paper patch | REVIEW |
| MATH-003 | Prove pointwise paraunitary partition | Math | MATH-001 | Theorem, proof, test contract | REVIEW |
| MATH-004 | Prove weighted spectral Parseval conservation | Math | MATH-003 | Theorem, proof, test contract | REVIEW |
| MATH-005 | Formalize conditioning and limited anti-collapse | Math | MATH-003 | Theorem/corollary | REVIEW |
| MATH-006 | Audit oversquashing; prove global statement and seek counterexample | Math | MATH-005 | Claim boundary and counterexample | REVIEW |
| MATH-007 | Derive multilevel finite-order frame bound | Math | MATH-003 | Theorem and observable | REVIEW |
| MATH-008 | Formalize root localization versus approximation | Math | MATH-001 | Proposition/corollary | REVIEW |
| MATH-009 | Prove generic movable-pole separation from Cayley filters | Math | MATH-008 | Theorem | REVIEW |
| MATH-010 | Derive graph perturbation stability or narrow replacement | Math | MATH-008 | Theorem or negative result | REVIEW |
| MATH-011 | State locality, degree, and SpMV complexity | Math | SCI-001 | Proposition | REVIEW |
| REV-NOVELTY-001 | Verify novelty and comparison-family pole loci from primary sources | Reviewer | MATH-001, SCI-001 | Source manifest and novelty adjudication | DONE |
| REV-CITATIONS-002 | Verify minimum comparator bibliography and Related Work positioning | Reviewer | REV-NOVELTY-001 | Verified bibliography, citation audit, compiled Related Work | DONE |
| REV-THEORY-PATCH | Independently audit the MATH-002--011 manuscript patch | Reviewer | MATH-002--MATH-011 | Theorem-by-theorem blocker report | DONE |
| MATH-PAPER-REPAIR-1 | Repair the theory patch against independent review | Math | REV-THEORY-PATCH | Corrected, compiling theory manuscript patch | DONE |
| MATH-CHEB-SOURCE-1 | Verify the exact first-kind Chebyshev interpolation bound | Math | MATH-PAPER-REPAIR-1 | Primary-source attribution and code-matched first-kind derivation | DONE |
| ENG-001 | Freeze or isolate legacy implementation and artifacts | Engineer | ORCH-001 | Trackability policy, legacy map, output guard, 10 tests | DONE |
| ENG-002 | Implement admissible roots and canonical symbols | Engineer | SCI-001 | `src/gbdn` core and tests | REVIEW |
| ENG-003 | Implement independent dense spectral oracle | Engineer | ENG-002 | Dense oracle tests | DONE |
| ENG-004 | Implement streaming Chebyshev/Clenshaw realization | Engineer | ENG-002 | Sparse implementation | BACKLOG |
| ENG-005 | Implement Tight GBDN analysis and synthesis | Engineer | ENG-003, ENG-004, MATH-002 | Canonical model and tests | BACKLOG |
| ENG-006 | Implement Product-sum GBDN | Engineer | ENG-002, ENG-004 | Model and tests | BACKLOG |
| ENG-007 | Implement GBDN+ separately | Engineer | ENG-004 | Relaxed model | BACKLOG |
| ENG-008 | Implement theorem-contract test suite | Engineer | ENG-005, MATH-003–MATH-011 | Contract tests | IN_PROGRESS |
| ENG-GATEA-EXACT-2 | Implement the second exact Gate-A test slice | Engineer | ENG-002, ENG-003, MATH-001 | GA-01/02/05--07/09/11--15/31--34 tests | DONE |
| ENG-GATEA-CLOSEOUT-1 | Add GA-23 and auditable Gate-A report/coverage inventory | Engineer | ENG-GATEA-EXACT-2, ENG-008 | GA-23 tests and deterministic report utility | DONE |
| REV-GATEA-APPROX-1 | Independently audit finite-order Gate-A diagnostics/tests | Reviewer | ENG-008, MATH-007--MATH-011 | Approximation theorem-test verdict | DONE |
| ENG-GATEA-APPROX-REPAIR-1 | Repair finite-order theorem-test semantic mismatches | Engineer | REV-GATEA-APPROX-1 | Correct GA-20/22/24/29/30 observables and diagnostics | DONE |
| ENG-GATEA-PROVENANCE-1 | Emit complete deterministic evidence for every Gate-A row | Engineer | ENG-GATEA-CLOSEOUT-1, ENG-GATEA-APPROX-REPAIR-1 | Validated row-level evidence schema and report | DONE |
| REV-GATEA-FINAL-1 | Independently adjudicate the complete Gate-A implementation | Reviewer | ENG-GATEA-CLOSEOUT-1, ENG-GATEA-APPROX-REPAIR-1 | Row-by-row verdict and binary gate decision | DONE |
| ENG-GATEA-SEMANTIC-REPAIR-1 | Repair package graph boundary and rejected GA-10/14/25/27 bindings | Engineer | REV-GATEA-FINAL-1, ENG-GATEA-PROVENANCE-1 | Canonical source/tests/evidence patch | IN_PROGRESS |
| REV-GATEA-REVIEW-2 | Independently re-adjudicate repaired Gate A | Reviewer | ENG-GATEA-SEMANTIC-REPAIR-1 | Clean-commit binary Gate-A decision | BACKLOG |
| OPS-RUNID-1 | Implement immutable run identities and artifact bundle validation | Engineer | ENG-001 | Deterministic IDs, non-overwrite/resume classifier, schema tests | DONE |
| REV-002 | Independently review mathematics and exact implementation | Reviewer | MATH-001–MATH-011, ENG-008 | Blocker report | BACKLOG |
| OPS-001 | Implement submission CLI and run identity | Engineer | ENG-008 | `run_submission.py` | BACKLOG |
| OPS-002 | Implement artifact schema and verifier | Engineer | OPS-001 | Artifact and verification tests | BACKLOG |
| OPS-003 | Implement H100 submission notebook | Engineer | OPS-001, OPS-002 | New notebook | BACKLOG |
| OPS-004 | Run H100 smoke and resume test | Engineer | OPS-003 | Smoke report | BACKLOG |
| EXP-001 | Run exact contract sweeps | Engineer | REV-002, OPS-004 | Gate-A artifacts | BACKLOG |
| EXP-002 | Run phase-sensitive mechanism study | Engineer | EXP-001 | Gate-B artifacts | BACKLOG |
| EXP-003 | Run mapped-pole approximation study | Engineer | EXP-001 | Pole/degree artifacts | BACKLOG |
| EXP-004 | Verify external response-efficiency baselines | Engineer | OPS-002 | Baseline registry | BACKLOG |
| EXP-005 | Run matched response-efficiency study | Engineer | EXP-002, EXP-003, EXP-004 | Gate-C artifacts | BACKLOG |
| REV-003 | Review mechanism claims and figures | Reviewer | EXP-005 | Mechanism review | BACKLOG |
| EXP-006 | Implement official heterophily task contract | Engineer | OPS-002 | Protocol tests | BACKLOG |
| EXP-007 | Verify primary heterophily baselines | Engineer | EXP-006 | `VERIFIED` registry entries | BACKLOG |
| EXP-008 | Freeze tuning policy and hyperparameter budgets | Orchestrator | EXP-007 | Run-plan decision | BACKLOG |
| EXP-009 | Run heterophily tuning | Engineer | EXP-008, OPS-004 | Frozen configs | BACKLOG |
| EXP-010 | Run all-split, multi-seed heterophily confirmation | Engineer | EXP-009 | Primary artifacts | BACKLOG |
| EXP-011 | Aggregate split-level statistics and compute | Engineer | EXP-010 | Primary tables/tests | BACKLOG |
| REV-004 | Review heterophily protocol, statistics, and interpretation | Reviewer | EXP-011 | Empirical review | BACKLOG |
| EXP-012 | Implement depth/rank instrumentation | Engineer | ENG-005 | Depth pipeline | BACKLOG |
| EXP-013 | Run independent-depth oversmoothing experiments | Engineer | EXP-012, EXP-008 | Gate-E artifacts | BACKLOG |
| EXP-014 | Implement source-target sensitivity and bottleneck tasks | Engineer | ENG-005, MATH-006 | Oversquashing pipeline | BACKLOG |
| EXP-015 | Run oversquashing/long-range experiments | Engineer | EXP-014 | Gate-F artifacts | BACKLOG |
| REV-005 | Review oversmoothing/oversquashing claims | Reviewer | EXP-013, EXP-015 | Phenomena review | BACKLOG |
| EXP-016 | Integrate optional official LRGB pipeline | Engineer | EXP-011 | LRGB artifacts | BACKLOG |
| PAPER-001 | Merge accepted method and theory patch | Orchestrator | REV-002 | Revised theory | BACKLOG |
| PAPER-002 | Generate all result tables and figures | Engineer | EXP-011, EXP-013, EXP-015 | `paper/generated` | BACKLOG |
| PAPER-003 | Rewrite experiments, related work, and limitations | Math + Reviewer | PAPER-001, PAPER-002, REV-004, REV-005 | Paper patch | BACKLOG |
| PAPER-004 | Rebuild paper and trace every number to run IDs | Orchestrator | PAPER-003 | Rebuilt PDF and trace report | BACKLOG |
| REV-006 | Simulated theory-heavy review | Reviewer | PAPER-004 | Review 1 | BACKLOG |
| REV-007 | Simulated empirical review | Reviewer | PAPER-004 | Review 2 | BACKLOG |
| SUB-001 | Complete code/data/license/compute audit | Orchestrator + Reviewer | REV-006, REV-007 | Audit | BACKLOG |
| SUB-002 | Create anonymized reproduction package | Engineer | SUB-001 | Submission archive | BACKLOG |
| SUB-003 | Execute final clean verification | Orchestrator | SUB-002 | PASS report | BACKLOG |
| SUB-004 | Freeze paper and code commits | Orchestrator | SUB-003 | Final SHAs | BACKLOG |

## Required decisions

Record each decision before dependent full runs.

| Decision | Options | Current |
|---|---|---|
| Primary title | foundational / heterophily-and-long-range | FOUNDATIONAL |
| Root parameterization | radial / exact center-width / both | PROVISIONAL: radial primary; evaluate exact center-width; reject `rho*phi(mu)` as exact center |
| Optional unitary routing | include / ablation / drop | DROP unless Gate B identifies a prespecified need |
| Primary baseline tier | minimum / extended | UNDECIDED |
| Tuning policy | upstream / equal-budget / both labeled | UNDECIDED |
| Trial budget | integer per model–dataset | UNDECIDED |
| Training seeds | fixed list | UNDECIDED |
| LRGB scope | none / subset / full | UNDECIDED |
| Application extension | none / 3D / medical graph | UNDECIDED |
| Primary statistical test | paired randomization / alternative | UNDECIDED |

## Phase exit records

The orchestrator appends:

```text
Phase:
Date:
Commit:
Passed gates:
Failed gates:
Accepted claims:
Rejected claims:
Artifacts:
Compute:
Next ready tasks:
```

```text
Phase: 0 — freeze and audit
Date: 2026-08-11
Commit: fcfa84111df8fcd66cd7266066bcd4c2aa97b852 (frozen public state); audit integration on agent/orchestrator/ORCH-001
Passed gates: Phase-0 inventory/read/correspondence deliverables only
Failed gates: Gate A; repository provenance; legacy artifact verification; official protocol/baseline admission; H100 submission infrastructure
Accepted claims: exact factor unitarity; exact complementary Parseval split; complete exact multilevel isometry and adjoint reconstruction; conditional mapped-pole Chebyshev envelope; finite-spectrum Product-sum existence
Rejected claims: tightness implies carried-state non-dissipation, no oversmoothing, oversquashing mitigation, target-specific sensitivity, benchmark superiority, or official long-range evidence
Artifacts: PHASE0_AUDIT.md; phase_0_manifest.json; independent math/reviewer/engineering audits and handoffs
Compute: local CPU audit only; 20 tests passed; legacy verifier failed with 28 problems; no new GPU experiment
Next ready tasks: SCI-001, MATH-001, ENG-001; claim-bearing Gate B/C and H100 runs remain blocked
```
