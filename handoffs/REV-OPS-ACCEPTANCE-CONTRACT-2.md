# REV-OPS-ACCEPTANCE-CONTRACT-2 handoff

## Decision

**REJECT** the v2 contract design at exact source commit
`f6446aabe09a9850be80ea55a503ebe7a1b462dc`.

This does not accept claim-bearing operations or H100 execution. The canonical
worker and frozen execution inputs are absent and remain blocked.

## Blocking evidence

- A valid acceptance lineage continued to validate after committed,
  unreviewed mutations to `src/gbdn/heterophily_statistics.py` and
  `src/gbdn/__init__.py`. The protected runtime surface is incomplete.
- A wholly self-issued, unsigned direct-child review commit authored as
  `GBDN Author <author@example.org>` passed validation. Git topology and
  content hashes do not authenticate reviewer independence.
- Dot segments, repeated separators, and trailing separators in review paths
  are normalized and accepted instead of being rejected lexically.

The exact attack outputs, effective repairs, and required fixes are recorded in
`reviews/operations_acceptance_contract_second_review.md`.

## Positive findings

The repaired contract rejects dirty protected code, replacement/rehashed bound
review blobs, conditional scheduler-only scope, intermediate commits, extra
review-commit files, drive/backslash/parent escapes, duplicate keys, and
non-finite JSON. The focused suite passed 14 tests.

## Next gate

Close and freeze the complete runtime import boundary, add authenticated
reviewer provenance, make path validation lexically canonical, then obtain a
fresh independent contract review. Only after the actual worker and frozen
inputs exist may an unconditional claim-bearing operations review issue a
token.

## Files changed

Only this handoff and the second independent contract review were added. No
source, test, token, result, paper, plan, registry, notebook, or board file was
edited.
