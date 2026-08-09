#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GPU_INDEX="${GPU_INDEX:-0}"
PYTHON="${ROOT}/.venv/bin/python"

if [[ ! -x "${PYTHON}" ]]; then
  echo "Missing ${PYTHON}; run bash scripts/setup_h100.sh first." >&2
  exit 1
fi

GPU_NAME="$(nvidia-smi --query-gpu=index,name --format=csv,noheader,nounits | awk -F', ' -v index="${GPU_INDEX}" '$1 == index {print $2}')"
if [[ -z "${GPU_NAME}" || "${GPU_NAME^^}" != *H100* ]]; then
  echo "GPU_INDEX=${GPU_INDEX} must select an H100; got ${GPU_NAME:-nothing}." >&2
  exit 1
fi

export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES="${GPU_INDEX}"
export PYTHONHASHSEED=25
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

LOG_DIR="${ROOT}/reproduction_logs"
mkdir -p "${LOG_DIR}"
LOG_PATH="${LOG_DIR}/$(date -u +%Y%m%dT%H%M%SZ).log"
exec > >(tee -a "${LOG_PATH}") 2>&1

echo "Physical GPU ${GPU_INDEX}: ${GPU_NAME}"
echo "Session log: ${LOG_PATH}"
exec "${PYTHON}" "${ROOT}/scripts/reproduce_legacy.py" "$@"
