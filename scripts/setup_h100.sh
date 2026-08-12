#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"
GPU_INDEX="${GPU_INDEX:-0}"
TORCH_INDEX_URL="${TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu128}"

command -v nvidia-smi >/dev/null || { echo "nvidia-smi is required." >&2; exit 1; }
command -v "${PYTHON_BIN}" >/dev/null || {
  echo "Python 3.11 is required; set PYTHON_BIN to its executable." >&2
  exit 1
}

"${PYTHON_BIN}" - <<'PY'
import sys
assert sys.version_info[:2] == (3, 11), f"expected Python 3.11, got {sys.version}"
PY

GPU_NAME="$(nvidia-smi --query-gpu=index,name --format=csv,noheader,nounits | awk -F', ' -v index="${GPU_INDEX}" '$1 == index {print $2}')"
if [[ -z "${GPU_NAME}" ]]; then
  echo "GPU_INDEX=${GPU_INDEX} does not identify a GPU." >&2
  exit 1
fi
if [[ "${GPU_NAME^^}" != *H100* ]]; then
  echo "GPU_INDEX=${GPU_INDEX} is not an H100: ${GPU_NAME}" >&2
  exit 1
fi

"${PYTHON_BIN}" -m venv "${ROOT}/.venv"
PYTHON="${ROOT}/.venv/bin/python"
"${PYTHON}" -m pip install --upgrade pip==25.2
"${PYTHON}" -m pip install torch==2.11.0 --index-url "${TORCH_INDEX_URL}"
"${PYTHON}" -m pip install -r "${ROOT}/requirements.lock"
"${PYTHON}" -m pip install --no-deps --editable "${ROOT}"

export CUDA_VISIBLE_DEVICES="${GPU_INDEX}"
export PYTHONHASHSEED=0
export CUBLAS_WORKSPACE_CONFIG=:4096:8
"${PYTHON}" - <<'PY'
import torch
import torch_geometric
import gbdn
from sklearn.metrics import average_precision_score
from torch_geometric.datasets import HeterophilousGraphDataset, LRGBDataset
from torch_geometric.nn import AntiSymmetricConv, MixHopConv, SAGEConv, SGConv

assert torch.cuda.is_available(), "PyTorch cannot access CUDA"
assert torch.cuda.device_count() == 1, "exactly one CUDA device must be visible"
name = torch.cuda.get_device_name(0)
assert "H100" in name.upper(), f"expected H100, got {name}"
assert torch.cuda.get_device_capability(0) >= (9, 0), "Hopper capability is required"
print("torch:", torch.__version__)
print("CUDA runtime:", torch.version.cuda)
print("torch-geometric:", torch_geometric.__version__)
print("gbdn:", gbdn.__file__)
print("GPU:", name)
print("H100 environment preflight passed.")
PY

cd "${ROOT}"
"${PYTHON}" -m pytest tests -q -p no:cacheprovider
