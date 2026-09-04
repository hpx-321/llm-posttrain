#!/usr/bin/env bash
set -euo pipefail

# Keep one stable pipeline boundary: use the in-repo veRL DPO adapter by
# default, while allowing an explicit external launcher for future backends.

: "${MODEL_PATH:?MODEL_PATH is required.}"
: "${TRAIN_FILE:?TRAIN_FILE is required.}"
: "${VALIDATION_FILE:?VALIDATION_FILE is required.}"
: "${SAVE_PATH:?SAVE_PATH is required.}"

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
DPO_LAUNCHER=${DPO_LAUNCHER:-}
TOKENIZER_PATH=${TOKENIZER_PATH:-${MODEL_PATH}}
PIPELINE_EXECUTION_MODE=${PIPELINE_EXECUTION_MODE:-smoke}
TRAIN_DEVICE=${TRAIN_DEVICE:-npu}
NPROC_PER_NODE=${NPROC_PER_NODE:-}
DPO_PYTHON_BIN=${DPO_PYTHON_BIN:-python3}
MASTER_ADDR=${MASTER_ADDR:-127.0.0.1}
MASTER_PORT=${MASTER_PORT:-29600}

DPO_MAX_LENGTH=${DPO_MAX_LENGTH:-5632}
DPO_MAX_PROMPT_LENGTH=${DPO_MAX_PROMPT_LENGTH:-4096}
DPO_LEARNING_RATE=${DPO_LEARNING_RATE:-5e-7}
DPO_NUM_TRAIN_EPOCHS=${DPO_NUM_TRAIN_EPOCHS:-1}
DPO_MAX_STEPS=${DPO_MAX_STEPS:-}
DPO_BETA=${DPO_BETA:-0.1}
DPO_PER_DEVICE_TRAIN_BATCH_SIZE=${DPO_PER_DEVICE_TRAIN_BATCH_SIZE:-1}
DPO_PER_DEVICE_EVAL_BATCH_SIZE=${DPO_PER_DEVICE_EVAL_BATCH_SIZE:-1}
DPO_GRADIENT_ACCUMULATION_STEPS=${DPO_GRADIENT_ACCUMULATION_STEPS:-8}

fail() {
  echo "Error: $*" >&2
  exit 1
}

is_positive_int() {
  [[ "$1" =~ ^[1-9][0-9]*$ ]]
}

[[ -d "${MODEL_PATH}" ]] || fail "DPO input checkpoint does not exist: ${MODEL_PATH}"
[[ -d "${TOKENIZER_PATH}" ]] || fail "DPO tokenizer does not exist: ${TOKENIZER_PATH}"
[[ -s "${TRAIN_FILE}" && -s "${VALIDATION_FILE}" ]] || \
  fail "DPO train/validation JSONL is missing or empty"
[[ ! -e "${SAVE_PATH}" ]] || fail "DPO output checkpoint already exists: ${SAVE_PATH}"
case "${PIPELINE_EXECUTION_MODE}" in smoke|train) ;; *)
  fail "PIPELINE_EXECUTION_MODE must be smoke or train"
esac
case "${TRAIN_DEVICE}" in cuda|npu) ;; *) fail "TRAIN_DEVICE must be cuda or npu" ;; esac
for value_name in DPO_MAX_LENGTH DPO_MAX_PROMPT_LENGTH DPO_PER_DEVICE_TRAIN_BATCH_SIZE \
  DPO_PER_DEVICE_EVAL_BATCH_SIZE DPO_GRADIENT_ACCUMULATION_STEPS; do
  value=${!value_name}
  is_positive_int "${value}" || fail "${value_name} must be a positive integer"
done

if [[ -z "${DPO_MAX_STEPS}" ]]; then
  if [[ "${PIPELINE_EXECUTION_MODE}" == "smoke" ]]; then
    DPO_MAX_STEPS=2
  else
    DPO_MAX_STEPS=-1
  fi
fi
if [[ "${DPO_MAX_STEPS}" != "-1" ]] && ! is_positive_int "${DPO_MAX_STEPS}"; then
  fail "DPO_MAX_STEPS must be -1 or a positive integer"
fi

export MODEL_PATH TOKENIZER_PATH TRAIN_FILE VALIDATION_FILE SAVE_PATH
export PIPELINE_EXECUTION_MODE TRAIN_DEVICE NPROC_PER_NODE DPO_PYTHON_BIN
export MASTER_ADDR MASTER_PORT
export DPO_MAX_LENGTH DPO_MAX_PROMPT_LENGTH DPO_LEARNING_RATE
export DPO_NUM_TRAIN_EPOCHS DPO_MAX_STEPS DPO_BETA
export DPO_PER_DEVICE_TRAIN_BATCH_SIZE DPO_PER_DEVICE_EVAL_BATCH_SIZE
export DPO_GRADIENT_ACCUMULATION_STEPS
if [[ -n "${DPO_LAUNCHER}" ]]; then
  [[ -f "${DPO_LAUNCHER}" && -x "${DPO_LAUNCHER}" ]] || \
    fail "DPO_LAUNCHER must be an executable file: ${DPO_LAUNCHER}"
  "${DPO_LAUNCHER}"
else
  command -v "${DPO_PYTHON_BIN}" >/dev/null || \
    fail "DPO_PYTHON_BIN is not executable: ${DPO_PYTHON_BIN}"
  [[ -f "${SCRIPT_DIR}/run_dpo_verl.sh" ]] || fail "missing ${SCRIPT_DIR}/run_dpo_verl.sh"
  bash "${SCRIPT_DIR}/run_dpo_verl.sh"
fi

if [[ "${PIPELINE_EXECUTION_MODE}" == "smoke" ]]; then
  [[ ! -e "${SAVE_PATH}" ]] || \
    fail "DPO smoke run unexpectedly produced a checkpoint: ${SAVE_PATH}"
  echo "DPO smoke run completed without saving a checkpoint."
  exit 0
fi

if [[ ! -f "${SAVE_PATH}/config.json" ]]; then
  fail "DPO trainer did not produce a Hugging Face config.json: ${SAVE_PATH}"
fi
if [[ ! -f "${SAVE_PATH}/tokenizer_config.json" ]]; then
  fail "DPO trainer did not save tokenizer files: ${SAVE_PATH}"
fi
if ! compgen -G "${SAVE_PATH}/*.safetensors" >/dev/null && \
   ! compgen -G "${SAVE_PATH}/pytorch_model*.bin" >/dev/null; then
  fail "DPO trainer did not produce Hugging Face model weights: ${SAVE_PATH}"
fi
