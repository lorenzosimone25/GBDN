# EXP-006-DATASET-ACQUISITION handoff

## Task

- **Task ID:** EXP-006-DATASET-ACQUISITION
- **Agent:** dataset_acquisition
- **Branch:** `agent/engineering/DATASET-ACQUISITION`
- **Starting commit:** `5a166957095f551949d863bd6bd1a5513782a80f`
- **Ending commit:** commit containing this handoff
- **Status proposed:** REVIEW

## Objective

Implement a local-only, pinned acquisition and identity verifier for the five
official Platonov heterophily archives. Do not run training, create claim-bearing
results, or commit raw data.

## Summary

The new acquisition module accepts only archive URLs under the frozen
`raw.githubusercontent.com` commit. It authenticates size, SHA-256, and Git blob
ID before parsing an immutable byte snapshot with `allow_pickle=False`. It then
checks exact keys, dtypes, shapes, labels, graph simplicity/connectivity,
one-time reciprocal expansion, and all ten supplied mask partitions. Array,
sorted-edge, and split-index hashes use named canonical serializations.

The strict JSON identity report records a local-acquisition-only policy and
explicitly says dataset redistribution rights are not asserted. Writers use
same-filesystem atomic creation and reject overwrite drift. The tracked Yandex
repository MIT notice is byte-identical to the pinned upstream notice; it is a
software-repository license record, not a broad dataset redistribution claim.

## Files changed

| File | Change | Ownership respected? |
|---|---|---|
| `src/gbdn/heterophily_acquisition.py` | Acquisition, structural verification, manifest generation/validation | Yes |
| `scripts/acquire_heterophily_data.py` | Thin acquire/offline-verify/manifest CLI | Yes |
| `tests/test_heterophily_acquisition.py` | Network-free synthetic and injected-downloader tests | Yes |
| `licenses/third_party/yandex_heterophilous_graphs_MIT.txt` | Exact pinned upstream repository notice | Yes |
| `handoffs/EXP-006-DATASET-ACQUISITION.md` | This handoff | Yes |

No notebook, H100 setup, paper, experiment result, token, or operations
acceptance file is changed. No `data/` directory or raw archive exists in the
worktree.

## Scientific impact

- Claims enabled: official dataset byte/structure/split identity can be proven
  before a runner consumes local archives.
- Claims narrowed: acquisition is local only; the upstream MIT notice does not
  establish separate rights to redistribute the underlying datasets.
- Claims rejected: none.
- Paper sections affected: none directly.

## Evidence

### Tests

```text
python -m pytest -q tests/test_heterophily_acquisition.py \
  tests/test_heterophily_contract.py tests/test_submission_verify.py \
  tests/test_repository_boundaries.py -p no:cacheprovider
52 passed

python -m pytest -q tests -p no:cacheprovider
764 passed, 2 skipped
```

The full suite was run before removal of non-owned notebook/setup wiring; those
two files were restored byte-for-byte to the starting commit, and the 52-test
focused suite was rerun afterward.

The verifier was also run read-only against the existing external audit cache
for all five real archives. All independent array/graph hashes, graph
invariants, and ten splits per dataset passed. No manifest or raw file was
written into the repository.

### Experiment artifacts

- run IDs: none
- result paths: none
- aggregate paths: none
- generated paper assets: none

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Exact commit-bound URLs | PASS | URL unit test and frozen registry check |
| Authenticate before parse | PASS | adversarial test patches `np.load` and proves it is not called on drift |
| Safe NPZ parsing and exact schema | PASS | dtype/key/object-array mutation tests |
| Graph and split invariants | PASS | synthetic adversarial tests plus all five real archives |
| Atomic no-overwrite writes | PASS | injected downloader and manifest drift tests |
| Offline verification | PASS | downloader-not-called test |
| Local-only licensing scope | PASS | strict manifest policy and exact notice hash |
| No raw data in Git/worktree | PASS | `.gitignore` test and final worktree inventory |

## Known limitations

- Raw NPZs remain ignored and must not be redistributed from this repository.
- The canonical H100/notebook caller is intentionally left for the orchestrator.
- The existing human-readable identity audit truncates the Questions
  `val_masks` digest. The verified 64-character value used by code is
  `d6b95c30650af9135631cadb23f6ae063f0398d6d6d599b58323f18569e8dc05`.
  This patch does not edit that shared report.

## Reviewer questions

1. Does the strict manifest schema bind every identity field required by the
   confirmatory run-plan generator?
2. Is the local-only license language sufficiently narrow for the intended
   artifact release?
3. Should the shared human-readable audit hash typo be corrected in a separate
   orchestrator-owned patch?

## Conflicts or decisions needed

The operator should call one of the commands below after GPU isolation and
environment installation. Notebook/setup ownership remains with the
orchestrator.

## Reproduction instructions

```text
# Download only missing pinned files, verify all files, create/compare manifest:
python scripts/acquire_heterophily_data.py acquire --repository-root <repo>

# No network; require all five local files and create/compare manifest:
python scripts/acquire_heterophily_data.py verify --repository-root <repo>

# Strictly validate existing canonical manifest against freshly verified data:
python scripts/acquire_heterophily_data.py validate-manifest --repository-root <repo>
```

The canonical report path is
`results_submission/reports/heterophily_dataset_identity.json`.

## Rollback

Revert the single bounded commit containing these five files. Raw data and run
artifacts are unaffected because none is tracked or created by this patch.
