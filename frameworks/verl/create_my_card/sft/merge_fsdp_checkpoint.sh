#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd -- "${SCRIPT_DIR}/../../../.." && pwd)

SAVE_PATH=${SAVE_PATH:-/mnt/data/checkpoints/qwen36-27b-create-my-card-sft-v1}
CHECKPOINT_STEP=${CHECKPOINT_STEP:-best}
MERGED_MODEL=${MERGED_MODEL:-}

case "${CHECKPOINT_STEP}" in
  best) tracker="${SAVE_PATH}/best_checkpointed_iteration.txt" ;;
  *) tracker= ;;
esac
if [[ -n "${tracker}" ]]; then
  if [[ ! -f "${tracker}" ]]; then
    echo "Error: checkpoint tracker does not exist: ${tracker}" >&2
    exit 1
  fi
  step=$(tr -d '[:space:]' < "${tracker}")
else
  step="${CHECKPOINT_STEP}"
fi

if ! [[ "${step}" =~ ^[1-9][0-9]*$ ]]; then
  echo "Error: CHECKPOINT_STEP must be best or a positive integer, got: ${step}" >&2
  exit 1
fi

ckpt_dir="${SAVE_PATH}/global_step_${step}"
if [[ ! -f "${ckpt_dir}/fsdp_config.json" ]]; then
  echo "Error: invalid FSDP checkpoint directory: ${ckpt_dir}" >&2
  exit 1
fi
if ! compgen -G "${ckpt_dir}/model_world_size_*_rank_*.pt" >/dev/null; then
  echo "Error: no FSDP model shards found in ${ckpt_dir}" >&2
  exit 1
fi

if [[ -z "${MERGED_MODEL}" ]]; then
  MERGED_MODEL="/mnt/data/models/qwen36-27b-create-my-card-sft-v1-step${step}"
fi
if [[ -e "${MERGED_MODEL}" || -L "${MERGED_MODEL}" ]]; then
  echo "Error: merge target already exists: ${MERGED_MODEL}" >&2
  exit 1
fi

echo "Merging veRL FSDP checkpoint into Hugging Face format"
echo "  source: ${ckpt_dir}"
echo "  target: ${MERGED_MODEL}"
echo "  started: $(date '+%Y-%m-%d %H:%M:%S %z')"
echo "Loading and rebuilding 27B shards on CPU can remain quiet for tens of minutes."

cd "${PROJECT_ROOT}"
python3 -m verl.model_merger merge \
  --backend fsdp \
  --local_dir "${ckpt_dir}" \
  --target_dir "${MERGED_MODEL}" \
  --trust-remote-code \
  --use_cpu_initialization

python3 frameworks/verl/create_my_card/sft/validate_merged_model.py \
  --model-path "${MERGED_MODEL}"

echo "Merge completed at $(date '+%Y-%m-%d %H:%M:%S %z')"
echo "Inference model: ${MERGED_MODEL}"
