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

## Array, graph, and split metadata audit

The pinned archives were opened in a separate local metadata-only process with
pickle disabled. The process emitted no raw feature, label, edge, or index
arrays. Array hashes below use `SHA256(len(header)||header||C-order-bytes)`,
where the canonical JSON header records NumPy dtype string, shape, and C order.
Graph hashes use stable lexicographic little-endian int64 edge rows. Each split
manifest hash commits the full ordered ten-row index hashes, partition sizes,
class-count vectors, and partition flags; those raw rows remain outside Git.

| Dataset | Features | Labels | Edges | Train masks | Validation masks | Test masks | Raw / expanded graph | Split manifest |
|---|---|---|---|---|---|---|---|---|
| Roman-empire | `57cc4eaca147661eed8e109eed6e502fb5495f4405b33a790db477697ddf650f` | `998ab2ade487eeddbebc2357587cf4986e6e2988e5dd1131b4b7825ad722467c` | `fe320b29326c66cdf07d95a930dc661b9a835fb42b9380c14bfcaf01ead59077` | `30e1b5d780eb6ff43ceb7b99b5ba9871b7067cb97c734a89278629d3de4acc1d` | `af1e8fff789ebf8314aeb1833d48a509e28b1815f7f114d75ebabc9f918afbf2` | `697e86865a17eb4e15b844f953a921b81c511f438bc1af91651a6fc089077880` | `a38be2bc4b8c8b9d03a3c4dc407e7b4be6fc5efcbc23028eda5a15e975f9179a` / `1096134adf66b46cd25944426625c6ebc421ecce5d8dd8d12977e7089dc90d50` | `a85c71a1bb76d6d1ae8d484858b944e74ab92109407eaa44112f6566b9669637` |
| Amazon-ratings | `6671bd714707679210693c2a5d7a4ed0205da2d51b39ed9dcea78429c7d0a084` | `459bd6846ab900361d0c7cd7c92aedaf11730d64b791c7ffe6cb4605d06b8538` | `639b03242157516691a60c490379d2947364911adae16b83ff57571f1be42f54` | `1e375534e23e6524369aee7982793369d4bbb6dc01eb860b5545eb5b86f2fabc` | `c7d9ccc1aaa85391a1e83d6bc4ecb7cd8b3af158283bbace5325746d39fd29aa` | `23a1150e0800ad093d7296dfe7b23311bb152c6afde2d37f73c794d4ea72e5e9` | `5f31df5ac0dc18c7fd6bfacdc35f8f328fc987d0c0f245ff99a5619a8c43b057` / `43a3a0ec59d75639eb1ced3b6e33e6b7fecf7cf92ef8bec773ca06ebc27a6c3c` | `0758498313008fd6483fbd1ef25c43edfb9920b81857de6b96346e373001325e` |
| Minesweeper | `94b4a7b985c7efc032c2257f97883db8df0c658dc7024cf39511dc8249a6fae2` | `acdfd465600a11a64552cf8ce846f24bc71e276c4e0dea9523a7c6baa5db3887` | `6b04520a037d00c9361c8ffa29a1989f1a710f64ef97e63b2e5f4e537e6aa22e` | `98c56dffc21de6658713cb98a5dd690ca7a8b44557c952bd280652524098bd4e` | `d6a30f935b3b63b2d371ad3f78db640e0f1451f4392245324f2ec29a54f31a43` | `89e0ebffbfa3b822c1788bb3ed66ff1e47edf8651322009b18330e30421d6376` | `6d8aee14222a04ff00a23d12106e4a644cebf390c0ac3230113746f78306e3fc` / `8974be716ddae54c20fdad5ff034ff99731bdf4aa224ff897d1ebb4d1ae18005` | `205071ffc140c50468143fbee1316db791cf692c1327fc6db457738638ea199c` |
| Tolokers | `6390afd1673d61969e599282827cd990735c3a3d77ee0bd929787bdc0836159e` | `304868dda1e5ad0b1e439817f93ed72be4d979227e989904191c50ebd3dcb183` | `d6993af4236813a1bd4e6ee20e4fd229cb64ecbaa64cc6ae2afa3856d06b2421` | `1c44a899b35374c924605f52be940e9361b4b7565e6414e4026300adaa5bb188` | `5b2ca9b8ea893aa814c62cab9486fa50ffb225d7108f656312c18fb44134fdaf` | `5b220eb5765b8373ce7e8d80670071df360ab30b6ccc4c95b5f307fde7c72760` | `bd80c60721e11373581539af0f96f4e10473370832d3a6c037b144bf365957e2` / `0de869a745efb0dd4de109fbe569155d022c4048a83a3c0db7719dc7b869f39f` | `28bf9665894776744b19b7d27e967bba2b9fe44c52e7646e34bf5f7ec82cfa50` |
| Questions | `791e0b004e33679e257803d6584c31529db1cd091e5fd12da502cc44d2a3dfcf` | `2af20c8b8ee2cb1b57546b52c70e8accdd905845926f1e7991ff95eb56933767` | `e85d1e41237d0fe02cff05eac07963e53ad716c3fe65a5d6eef52e8a07e881cb` | `dcd988d861d729359ccc2fcdcd4587903b7b4ddbd07d775839fe95d28aa81649` | `d6b95c30650af9135631cadb23f6ae063f0398d6d599b58323f18569e8dc05` | `369f8c96c34796535cc3918f1259ea90a45867cc5bcdca57f61b2585fa39d09a` | `b165be96dfb304ad2a2a779c09d729e5c23398aeeceecfffe8988558b8af022b` / `97104e2d7b7e992a5d1323c1479e165288fc9b9103d10eda56908c0609f1a039` | `bb0eee58e105bdbf5e7284ac283a58cb276627618dc567cc81b852dca4d15403` |

All feature arrays are little-endian float32, labels/edges little-endian int64,
and masks Boolean. Shapes match the frozen registry. Every graph has exactly
one connected component, no stored self-loops, and no duplicate directed edge
after one reciprocal expansion. Every split row is pairwise disjoint and
covers every node. Sizes are exactly 50/25/25 up to the unavoidable one-node
remainder for odd node counts.

The metadata-only temporary path was
`C:\Users\Lough\AppData\Local\Temp\gbdn-npz-audit-e3104d6f97be43c78198e70c790ed803`;
it is outside the repository and intentionally untracked.

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

## Baseline admission decision

The canonical registry is now frozen at `gbdn-baseline-registry-v2`. An
implementation may enter the confirmatory primary scope through exactly one
of two declared routes:

1. `UPSTREAM_CODE`: the executed implementation is from a pinned source
   repository with a resolved SPDX license and preserved notice; or
2. `CLEAN_ROOM_EQUATIONS`: no upstream implementation code is used, the local
   implementation is derived from a pinpointed primary-paper equation, and an
   independent operator oracle and parity record verify it.

Both routes require a full source commit, paper URL and equation locator,
official-task verification, parameter and sparse-operator accounting, and
SHA-256 bindings for the license notice, implementation provenance, wrapper,
reference configuration, independent oracle, and typed parity evidence. The
parity evidence itself must agree exactly with the registry's method,
implementation kind, source commit, wrapper/oracle/configuration hashes,
dataset, metric, values, tolerance, and pass status.

PyTorch Geometric 2.8.0 is pinned in `requirements.lock` and provides a
licensed `ChebConv` implementation under MIT. It is therefore a viable route
for a **ChebNet** comparator after adapter, task, resource, and parity
verification. It must not be labeled ChebNetII. PyTorch Geometric 2.8.0 does
not supply the audited ChebNetII, BernNet, GPR-GNN, CayleyNet, or WaveGC model
implementations, so their prior license blockers are unchanged. A clean-room
route is permitted by the schema but does not become `VERIFIED` merely because
its files exist; the independent oracle and typed parity artifact remain
mandatory.
