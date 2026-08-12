# Dataset and baseline identity audit

Date: 2026-08-12

## Official dataset byte identity

Source repository: `https://github.com/yandex-research/heterophilous-graphs`

Pinned commit: `a431395582e929d88271309716bea4fe24ce6318`

The five files were downloaded to a uniquely named system-temporary directory
solely for whole-file SHA-256 computation. They were not deserialized, their
arrays/splits/labels were not opened, and no copy entered this repository.

| File | Bytes | Git blob SHA-1 | Whole-file SHA-256 |
|---|---:|---|---|
| `roman_empire.npz` | 20,401,489 | `1f9bae5e95b28e529015269e98acb237b65d8d3b` | `a58ba741d123bf892fe5c872138d07463d75a2e9012360b8dd78ac2d4766d428` |
| `amazon_ratings.npz` | 27,744,018 | `29647a8b0ff0ef856d73d683a8c3595bd5efbd38` | `4c3a3e3b9d9f6cba0fede4625a00aad8c5721c1a36ed771367f446763241c7dd` |
| `minesweeper.npz` | 135,045 | `cc2387032c65b92a5c520c473db1527cbb329d32` | `e664c8dacf1e8ac466c2c09ed4b237bd2c5541f47a6eae9c6092cb87f16412b3` |
| `tolokers.npz` | 1,329,769 | `b8375a91a8f3c9e32c84fed7c151bbaf6ea6f0c7` | `dacf3ac94cec53d03cd2adb5255c08b33dee1656c33ca8164a464bd9450a1667` |
| `questions.npz` | 47,369,919 | `4c7cb65057dbc9771af00fdfdee64a41b3875079` | `757ebd772bab1475c4dd951ca9e364400c6db161656cff9d21780ee874cf3074` |

Byte identity is resolved. Dataset-specific redistribution permission remains
unresolved: the source repository's MIT code license does not separately
enumerate the underlying Wikipedia/SNAP/Toloka/Yandex Q data rights. Therefore
`ready_for_acquisition` remains false in the canonical registry, and raw NPZs
must not be committed or redistributed.

The verified temporary path was
`C:\Users\Lough\AppData\Local\Temp\gbdn-dataset-hash-ccc5958284d64a2c8420671657158262`.
Windows command policy blocked its recursive cleanup; it was left untouched
outside the repository rather than removed through an unsafe workaround.

## Comparator repository license preflight

GitHub repository metadata and each pinned root directory were queried through
the GitHub API. At the audited commits, none exposes a detectable license SPDX
identifier or a root `LICENSE`, `LICENCE`, `COPYING`, or `NOTICE` file.

| Method | Pinned first-party repository commit | API SPDX | Root license files | Admission |
|---|---|---|---|---|
| ChebNetII | `ivam-he/ChebNetII@ded6c18cbe9673234071031767d17826ad632aca` | absent | none | BLOCKED |
| BernNet | `ivam-he/BernNet@79ef2bab5930477a12795f9c8530eb685e7c9262` | absent | none | BLOCKED |
| GPR-GNN | `jianhao2016/GPRGNN@4e0a7ee5435058b70eaec3c23c55fb96dc37f2d5` | absent | none | BLOCKED |
| WaveGC | `liun-online/WaveGC@ec8af1e5a4cd57dcf296fd6281f728fc6bd04be6` | absent | none | BLOCKED |

This does not prove that no permission can be obtained; it means no license was
published at the audited first-party roots. The code may not be vendored or
marked `VERIFIED` without author clarification or a separately licensed
upstream implementation, plus wrapper parity and resource accounting.
