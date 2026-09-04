#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd -- "${SCRIPT_DIR}/../../../../.." && pwd)

DPO_MAX_TOKEN_LEN_PER_GPU=${DPO_MAX_TOKEN_LEN_PER_GPU:-}
DPO_GLOBAL_PAIR_BATCH_SIZE=${DPO_GLOBAL_PAIR_BATCH_SIZE:-}
DPO_PARAM_OFFLOAD=${DPO_PARAM_OFFLOAD:-false}
DPO_OPTIMIZER_OFFLOAD=${DPO_OPTIMIZER_OFFLOAD:-false}
DPO_ACTIVATION_OFFLOAD=${DPO_ACTIVATION_OFFLOAD:-false}
DPO_FSDP_SAVE_PATH=${DPO_FSDP_SAVE_PATH:-${SAVE_PATH}-fsdp}
DPO_LOGGER=${DPO_LOGGER:-console}

export HYDRA_FULL_ERROR=1
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1
export PYTORCH_CUDA_ALLOC_CONF=${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}
export PYTORCH_NPU_ALLOC_CONF=${PYTORCH_NPU_ALLOC_CONF:-expandable_segments:True}

fail() {
  echo "Error: $*" >&2
  exit 1
}

is_positive_int() {
  [[ "$1" =~ ^[1-9][0-9]*$ ]]
}

validate_bool() {
  case "$2" in true|false) ;; *) fail "$1 must be true or false" ;; esac
}

validate_bool DPO_PARAM_OFFLOAD "${DPO_PARAM_OFFLOAD}"
validate_bool DPO_OPTIMIZER_OFFLOAD "${DPO_OPTIMIZER_OFFLOAD}"
validate_bool DPO_ACTIVATION_OFFLOAD "${DPO_ACTIVATION_OFFLOAD}"
[[ ! -e "${DPO_FSDP_SAVE_PATH}" ]] || \
  fail "DPO FSDP checkpoint path already exists: ${DPO_FSDP_SAVE_PATH}"

if [[ -z "${NPROC_PER_NODE}" ]]; then
  NPROC_PER_NODE=$(TRAIN_DEVICE="${TRAIN_DEVICE}" "${DPO_PYTHON_BIN}" - <<'PY'
import os
import torch

if os.environ["TRAIN_DEVICE"] == "cuda":
    print(torch.cuda.device_count())
else:
    import torch_npu  # noqa: F401
    print(torch.npu.device_count())
PY
  )
fi
is_positive_int "${NPROC_PER_NODE}" || fail "NPROC_PER_NODE must be a positive integer"

if [[ -z "${DPO_GLOBAL_PAIR_BATCH_SIZE}" ]]; then
  if [[ "${PIPELINE_EXECUTION_MODE}" == "smoke" ]]; then
    DPO_GLOBAL_PAIR_BATCH_SIZE=$((NPROC_PER_NODE * DPO_PER_DEVICE_TRAIN_BATCH_SIZE))
  else
    DPO_GLOBAL_PAIR_BATCH_SIZE=$((
      NPROC_PER_NODE * DPO_PER_DEVICE_TRAIN_BATCH_SIZE * DPO_GRADIENT_ACCUMULATION_STEPS
    ))
  fi
fi
is_positive_int "${DPO_GLOBAL_PAIR_BATCH_SIZE}" || \
  fail "DPO_GLOBAL_PAIR_BATCH_SIZE must be a positive integer"
((DPO_GLOBAL_PAIR_BATCH_SIZE % NPROC_PER_NODE == 0)) || \
  fail "DPO_GLOBAL_PAIR_BATCH_SIZE must be divisible by NPROC_PER_NODE"

if [[ -z "${DPO_MAX_TOKEN_LEN_PER_GPU}" ]]; then
  DPO_MAX_TOKEN_LEN_PER_GPU=$((DPO_MAX_LENGTH * 2))
fi
is_positive_int "${DPO_MAX_TOKEN_LEN_PER_GPU}" || \
  fail "DPO_MAX_TOKEN_LEN_PER_GPU must be a positive integer"
((DPO_MAX_TOKEN_LEN_PER_GPU >= DPO_MAX_LENGTH * 2)) || \
  fail "DPO_MAX_TOKEN_LEN_PER_GPU must fit one chosen/rejected pair"

if [[ "${PIPELINE_EXECUTION_MODE}" == "smoke" ]]; then
  DPO_REPEAT_TRAIN_TO_SIZE=${DPO_GLOBAL_PAIR_BATCH_SIZE}
  trainer_schedule=(
    "trainer.total_training_steps=${DPO_MAX_STEPS}"
    trainer.save_freq=-1
    trainer.test_freq=-1
    trainer.resume_mode=disable
    'checkpoint.save_contents=[]'
  )
else
  DPO_REPEAT_TRAIN_TO_SIZE=0
  trainer_schedule=(
    "trainer.total_epochs=${DPO_NUM_TRAIN_EPOCHS}"
    trainer.save_freq=-1
    trainer.test_freq=-1
    trainer.resume_mode=disable
    'checkpoint.save_contents=["model"]'
  )
fi
export DPO_REPEAT_TRAIN_TO_SIZE

cd "${PROJECT_ROOT}"
"${DPO_PYTHON_BIN}" -m torch.distributed.run \
  --nnodes=1 \
  --node_rank=0 \
  --nproc_per_node="${NPROC_PER_NODE}" \
  --master_addr="${MASTER_ADDR}" \
  --master_port="${MASTER_PORT}" \
  "${SCRIPT_DIR}/train_dpo_verl.py" \
  "data.train_files=${TRAIN_FILE}" \
  "data.val_files=${VALIDATION_FILE}" \
  "data.train_batch_size=${DPO_GLOBAL_PAIR_BATCH_SIZE}" \
  data.micro_batch_size_per_gpu=1 \
  "data.max_length=${DPO_MAX_LENGTH}" \
  "data.max_token_len_per_gpu=${DPO_MAX_TOKEN_LEN_PER_GPU}" \
  data.use_dynamic_bsz=true \
  data.pad_mode=no_padding \
  data.truncation=error \
  data.num_workers=0 \
  model=hf_model \
  "model.path=${MODEL_PATH}" \
  "model.tokenizer_path=${TOKENIZER_PATH}" \
  model.trust_remote_code=true \
  model.enable_gradient_checkpointing=true \
  "model.enable_activation_offload=${DPO_ACTIVATION_OFFLOAD}" \
  model.use_remove_padding=true \
  model.use_fused_kernels=false \
  model.lora_rank=0 \
  engine=fsdp \
  engine.strategy=fsdp \
  engine.dtype=bfloat16 \
  engine.model_dtype=fp32 \
  engine.reshard_after_forward=true \
  engine.ulysses_sequence_parallel_size=1 \
  "engine.param_offload=${DPO_PARAM_OFFLOAD}" \
  "engine.optimizer_offload=${DPO_OPTIMIZER_OFFLOAD}" \
  engine.use_torch_compile=false \
  optim=fsdp \
  "optim.lr=${DPO_LEARNING_RATE}" \
  optim.lr_scheduler_type=cosine \
  optim.lr_warmup_steps_ratio=0.03 \
  optim.weight_decay=0.01 \
  'optim.betas=[0.9,0.95]' \
  optim.clip_grad=1.0 \
  "trainer.default_local_dir=${DPO_FSDP_SAVE_PATH}" \
  trainer.project_name=create-my-card-dpo \
  trainer.experiment_name=taskspec-to-dsl-dpo \
  "trainer.logger=[\"${DPO_LOGGER}\"]" \
  "trainer.device=${TRAIN_DEVICE}" \
  trainer.nnodes=1 \
  "trainer.n_gpus_per_node=${NPROC_PER_NODE}" \
  "${trainer_schedule[@]}"

if [[ "${PIPELINE_EXECUTION_MODE}" == "smoke" ]]; then
  if compgen -G "${DPO_FSDP_SAVE_PATH}/global_step_*" >/dev/null; then
    fail "veRL DPO adapter smoke unexpectedly saved an FSDP checkpoint"
  fi
  exit 0
fi

PYTHON_BIN="${DPO_PYTHON_BIN}" \
SAVE_PATH="${DPO_FSDP_SAVE_PATH}" \
MERGED_MODEL="${SAVE_PATH}" \
CHECKPOINT_STEP=latest \
PIPELINE_EXECUTION_MODE=train \
  bash "${PROJECT_ROOT}/frameworks/verl/create_my_card/sft/training/merge_fsdp_checkpoint.sh"
