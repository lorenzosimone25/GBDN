# EXP-007/008-ADMISSION-CONTRACT-1 handoff

## Scope

Implemented baseline-admission and confirmatory-plan validators with synthetic
fixtures only. No real baseline was marked verified, no primary comparator set
or practical tie threshold was chosen, and no real registry, plan, dataset,
benchmark, H100 process, or manuscript artifact was created.

## Admission contract

A primary baseline must provide a unique canonical name, first-party HTTPS
repository, full 40-hex commit, resolved SPDX license and notice, existing
wrapper and upstream configuration, wrapper-content SHA-256, heterophily
protocol coverage, passing parity within a declared tolerance, and verified
parameter/SpMV counts. `BLOCKED`, missing, extra, duplicate, unlicensed,
unmatched, or resource-unverified entries are rejected.

The confirmatory plan must bind the registry hash and freeze:

- exactly the five official datasets;
- all ten official split rows and seeds `[0,1,2]`;
- TightGBDN plus a nonempty primary comparator set;
- one positive equal validation-trial budget per method-dataset;
- test-isolated, validation-only selection and configuration freeze; and
- one predeclared practical tie threshold per dataset.

The live readiness verifier calls the plan/registry binding validator if both
files appear. It still blocks on the absent independent Gate-A token,
unimplemented scheduler/run-plan validator, and absent completion outputs.

## Verification

- Baseline/plan and verifier focused suite: 18 passed.
- Full repository suite: 628 passed, 1 Windows privilege skip, 3 known
  environment warnings.

## Remaining block

Primary-source repository/license audit, wrapper implementation, upstream
parity, exact comparator family, equal tuning budget magnitude, practical tie
thresholds, independent review, and the scheduler remain unresolved.
