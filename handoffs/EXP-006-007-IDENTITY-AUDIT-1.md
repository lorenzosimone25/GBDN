# EXP-006/007-IDENTITY-AUDIT-1 handoff

- Pinned byte size, Git blob SHA-1, and whole-file SHA-256 for all five official
  NPZs without deserializing them or opening arrays/labels/splits.
- In a later metadata-only pass with pickle disabled, pinned six array hashes,
  raw/expanded graph hashes and invariants, and a canonical complete split-
  manifest hash for each dataset. No raw array or index row entered Git.
- Left dataset acquisition/publication blocked because dataset-specific
  redistribution terms remain unresolved.
- Audited pinned first-party roots for ChebNetII, BernNet, GPR-GNN, and WaveGC;
  GitHub reports no SPDX license and no root license/notice file for any of the
  four, so all remain `BLOCKED` for vendoring and primary admission.
- Temporary downloads were outside the repository. Cleanup was blocked by
  Windows command policy after exact path verification, so the explicit temp
  directory was left untouched rather than using an unsafe workaround.
- Protocol/run-plan/evaluator focused suite: 40 passed.
- No dataset file, baseline source, real registry/plan, experiment, H100 job,
  manuscript, or generated result was created.
