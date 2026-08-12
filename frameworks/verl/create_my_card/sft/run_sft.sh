#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH=${BASH_SOURCE[0]}
SCRIPT_DIR=$(dirname -- "${SCRIPT_PATH}")
SCRIPT_DIR=$(cd -- "${SCRIPT_DIR}" && pwd)
PROJECT_ROOT=$(cd -- "${SCRIPT_DIR}/../../../.." && pwd)

MODEL_PATH=${MODEL_PATH:-/mnt/model/Qwen3.6-27B}
DATA_DIR=${DATA_DIR:-${SCRIPT_DIR}/data/parquet}
SFT_DATASET_PATH=${SFT_DATASET_PATH:-${SCRIPT_DIR}/qwen36_sft_dataset.py}
SAVE_PATH=${SAVE_PATH:-/mnt/data/checkpoints/qwen36-27b-create-my-card-sft}
OOM_PROBE_FILE=${OOM_PROBE_FILE:-${DATA_DIR}/oom_probe.parquet}
TRAIN_DEVICE=${TRAIN_DEVICE:-npu}

DRY_RUN=${DRY_RUN:-1}
DRY_RUN_STEPS=${DRY_RUN_STEPS:-2}

NPROC_PER_NODE=${NPROC_PER_NODE:-}
MASTER_ADDR=${MASTER_ADDR:-127.0.0.1}
MASTER_PORT=${MASTER_PORT:-29500}
SP_SIZE=${SP_SIZE:-1}
TRAIN_BATCH_SIZE=${TRAIN_BATCH_SIZE:-}
MICRO_BATCH_SIZE_PER_GPU=${MICRO_BATCH_SIZE_PER_GPU:-1}

MAX_LENGTH=${MAX_LENGTH:-4096}
MAX_TOKEN_LEN_PER_GPU=${MAX_TOKEN_LEN_PER_GPU:-8192}

LEARNING_RATE=${LEARNING_RATE:-}
TOTAL_EPOCHS=${TOTAL_EPOCHS:-3}
WEIGHT_DECAY=${WEIGHT_DECAY:-0.01}
WARMUP_RATIO=${WARMUP_RATIO:-0.03}

PARAM_OFFLOAD=${PARAM_OFFLOAD:-false}
OPTIMIZER_OFFLOAD=${OPTIMIZER_OFFLOAD:-false}
ACTIVATION_OFFLOAD=${ACTIVATION_OFFLOAD:-false}
MAX_CKPT_TO_KEEP=${MAX_CKPT_TO_KEEP:-1}
BEST_CKPT_MIN_DELTA=${BEST_CKPT_MIN_DELTA:-0}
LOG_DIR=${LOG_DIR:-/mnt/data/logs/qwen36-27b-create-my-card-sft}
PROJECT_NAME=${PROJECT_NAME:-qwen36-create-my-card-sft}
EXPERIMENT_NAME=${EXPERIMENT_NAME:-qwen36-27b-full-sft}

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
  case "$2" in
    true|false) ;;
    *) fail "$1 must be true or false, got: $2" ;;
  esac
}

validate_nonnegative_number() {
  [[ "$2" =~ ^([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$ ]] || \
    fail "$1 must be a non-negative finite number, got: $2"
}

[[ -d "${MODEL_PATH}" ]] || fail "MODEL_PATH does not exist: ${MODEL_PATH}"
[[ -f "${SFT_DATASET_PATH}" ]] || fail "SFT_DATASET_PATH does not exist: ${SFT_DATASET_PATH}"
[[ -f "${DATA_DIR}/train.parquet" ]] || fail "missing ${DATA_DIR}/train.parquet"
[[ -f "${DATA_DIR}/validation.parquet" ]] || fail "missing ${DATA_DIR}/validation.parquet"

case "${DRY_RUN}" in 0|1) ;; *) fail "DRY_RUN must be 0 or 1" ;; esac
case "${TRAIN_DEVICE}" in cuda|npu) ;; *) fail "TRAIN_DEVICE must be cuda or npu" ;; esac
validate_bool PARAM_OFFLOAD "${PARAM_OFFLOAD}"
validate_bool OPTIMIZER_OFFLOAD "${OPTIMIZER_OFFLOAD}"
validate_bool ACTIVATION_OFFLOAD "${ACTIVATION_OFFLOAD}"
validate_nonnegative_number BEST_CKPT_MIN_DELTA "${BEST_CKPT_MIN_DELTA}"

for value_name in DRY_RUN_STEPS MICRO_BATCH_SIZE_PER_GPU MAX_LENGTH MAX_TOKEN_LEN_PER_GPU SP_SIZE TOTAL_EPOCHS MAX_CKPT_TO_KEEP; do
  value=${!value_name}
  is_positive_int "${value}" || fail "${value_name} must be a positive integer, got: ${value}"
done
if [[ -z "${NPROC_PER_NODE}" ]]; then
  NPROC_PER_NODE=$(TRAIN_DEVICE="${TRAIN_DEVICE}" python3 - <<'PY'
import os
import torch

device = os.environ["TRAIN_DEVICE"]
if device == "cuda":
    print(torch.cuda.device_count())
else:
    import torch_npu  # noqa: F401
    print(torch.npu.device_count())
PY
  )
fi
is_positive_int "${NPROC_PER_NODE}" || fail "NPROC_PER_NODE must be a positive integer"

((NPROC_PER_NODE % SP_SIZE == 0)) || fail \
  "NPROC_PER_NODE=${NPROC_PER_NODE} must be divisible by SP_SIZE=${SP_SIZE}"
DP_SIZE=$((NPROC_PER_NODE / SP_SIZE))

EFFECTIVE_MICRO_TOKEN_BUDGET=$((MAX_TOKEN_LEN_PER_GPU * SP_SIZE))
((EFFECTIVE_MICRO_TOKEN_BUDGET >= MAX_LENGTH)) || fail \
  "MAX_TOKEN_LEN_PER_GPU * SP_SIZE must be at least MAX_LENGTH"

if [[ -z "${TRAIN_BATCH_SIZE}" ]]; then
  TRAIN_BATCH_SIZE=$((DP_SIZE * 2))
fi
is_positive_int "${TRAIN_BATCH_SIZE}" || fail "TRAIN_BATCH_SIZE must be a positive integer"
((TRAIN_BATCH_SIZE % DP_SIZE == 0)) || fail \
  "TRAIN_BATCH_SIZE=${TRAIN_BATCH_SIZE} must be divisible by DP_SIZE=${DP_SIZE}"
LOCAL_BATCH_SIZE=$((TRAIN_BATCH_SIZE / DP_SIZE))
((LOCAL_BATCH_SIZE % MICRO_BATCH_SIZE_PER_GPU == 0)) || fail \
  "local batch ${LOCAL_BATCH_SIZE} must be divisible by micro batch ${MICRO_BATCH_SIZE_PER_GPU}"

if [[ -z "${LEARNING_RATE}" ]]; then
  LEARNING_RATE=1e-6
fi

if [[ "${DRY_RUN}" == "1" ]]; then
  [[ -f "${OOM_PROBE_FILE}" ]] || fail \
    "missing ${OOM_PROBE_FILE}; generate it with analyze_tokens.py before the dry run"
  TRAIN_FILE=${OOM_PROBE_FILE}
  TRAINER_ENTRY=("${SCRIPT_DIR}/sft_dry_run.py")
  CHECKPOINT_SUMMARY=disabled
else
  [[ -f "${SCRIPT_DIR}/best_sft_trainer.py" ]] || fail "missing best_sft_trainer.py"
  TRAIN_FILE=${DATA_DIR}/train.parquet
  TRAINER_ENTRY=("${SCRIPT_DIR}/best_sft_trainer.py")
  CHECKPOINT_SUMMARY="save best model weights only; keep ${MAX_CKPT_TO_KEEP} improvement(s)"
fi

export BEST_CKPT_MIN_DELTA

if [[ "${DRY_RUN}" == "0" ]] && \
  { compgen -G "${SAVE_PATH}/global_step_*" >/dev/null || \
    [[ -e "${SAVE_PATH}/latest_checkpointed_iteration.txt" ]] || \
    [[ -e "${SAVE_PATH}/best_checkpointed_iteration.txt" ]] || \
    [[ -e "${SAVE_PATH}/best_validation_metrics.json" ]]; }; then
  fail "${SAVE_PATH} already contains checkpoint state; use a new SAVE_PATH"
fi

mkdir -p -- "${LOG_DIR}"
LOG_FILE=${LOG_FILE:-${LOG_DIR}/run-$(date +%Y%m%d-%H%M%S)-$$.log}
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "============================================================"
echo "Qwen3.6-27B CreateMyCard veRL SFT"
echo "Model:                        ${MODEL_PATH}"
echo "SFT dataset adapter:          ${SFT_DATASET_PATH}"
echo "Train file:                   ${TRAIN_FILE}"
echo "Validation:                   ${DATA_DIR}/validation.parquet"
echo "Checkpoint:                   ${SAVE_PATH}"
echo "Device processes / SP / DP:   ${NPROC_PER_NODE} / ${SP_SIZE} / ${DP_SIZE}"
echo "Max sequence length:           ${MAX_LENGTH}"
echo "Per-device token budget:       ${MAX_TOKEN_LEN_PER_GPU}"
echo "Effective SP token budget:     ${EFFECTIVE_MICRO_TOKEN_BUDGET}"
echo "Global / local / micro batch: ${TRAIN_BATCH_SIZE} / ${LOCAL_BATCH_SIZE} / ${MICRO_BATCH_SIZE_PER_GPU}"
echo "Training mode:                full-parameter"
echo "Gradient checkpointing:       true"
echo "Param / optimizer offload:    ${PARAM_OFFLOAD} / ${OPTIMIZER_OFFLOAD}"
echo "Activation offload:           ${ACTIVATION_OFFLOAD}"
echo "Learning rate / epochs:       ${LEARNING_RATE} / ${TOTAL_EPOCHS}"
echo "Dry run / steps:              ${DRY_RUN} / ${DRY_RUN_STEPS}"
echo "Checkpoint saving:            ${CHECKPOINT_SUMMARY}"
echo "Best-checkpoint min delta:    ${BEST_CKPT_MIN_DELTA}"
echo "Log:                          ${LOG_FILE}"
echo "============================================================"

extra_args=()
if [[ "${DRY_RUN}" == "1" ]]; then
  extra_args+=(
    "trainer.total_training_steps=${DRY_RUN_STEPS}"
    trainer.save_freq=-1
    trainer.test_freq=-1
    trainer.resume_mode=disable
    'checkpoint.save_contents=[]'
  )
else
  extra_args+=(
    "trainer.total_epochs=${TOTAL_EPOCHS}"
    trainer.save_freq=after_each_epoch
    trainer.test_freq=after_each_epoch
    "trainer.max_ckpt_to_keep=${MAX_CKPT_TO_KEEP}"
    trainer.resume_mode=disable
    'checkpoint.save_contents=["model"]'
  )
fi

cd "${PROJECT_ROOT}"

torchrun \
  --nnodes=1 \
  --node_rank=0 \
  --nproc_per_node="${NPROC_PER_NODE}" \
  --master_addr="${MASTER_ADDR}" \
  --master_port="${MASTER_PORT}" \
  "${TRAINER_ENTRY[@]}" \
  "data.train_files=${TRAIN_FILE}" \
  "data.val_files=${DATA_DIR}/validation.parquet" \
  "data.train_batch_size=${TRAIN_BATCH_SIZE}" \
  "data.micro_batch_size_per_gpu=${MICRO_BATCH_SIZE_PER_GPU}" \
  "data.max_length=${MAX_LENGTH}" \
  "data.max_token_len_per_gpu=${MAX_TOKEN_LEN_PER_GPU}" \
  data.use_dynamic_bsz=true \
  data.messages_key=messages \
  data.enable_thinking_key=enable_thinking \
  "data.custom_cls.path=${SFT_DATASET_PATH}" \
  data.custom_cls.name=CreateMyCardSFTDataset \
  data.pad_mode=no_padding \
  data.truncation=error \
  data.num_workers=2 \
  model=hf_model \
  "model.path=${MODEL_PATH}" \
  model.trust_remote_code=true \
  model.enable_gradient_checkpointing=true \
  "model.enable_activation_offload=${ACTIVATION_OFFLOAD}" \
  model.use_remove_padding=true \
  model.use_fused_kernels=false \
  model.lora_rank=0 \
  engine=fsdp \
  engine.strategy=fsdp \
  engine.dtype=bfloat16 \
  engine.model_dtype=fp32 \
  engine.reshard_after_forward=true \
  "engine.ulysses_sequence_parallel_size=${SP_SIZE}" \
  "engine.param_offload=${PARAM_OFFLOAD}" \
  "engine.optimizer_offload=${OPTIMIZER_OFFLOAD}" \
  engine.use_torch_compile=false \
  optim=fsdp \
  "optim.lr=${LEARNING_RATE}" \
  optim.lr_scheduler_type=cosine \
  "optim.lr_warmup_steps_ratio=${WARMUP_RATIO}" \
  "optim.weight_decay=${WEIGHT_DECAY}" \
  'optim.betas=[0.9,0.95]' \
  optim.clip_grad=1.0 \
  "trainer.default_local_dir=${SAVE_PATH}" \
  "trainer.project_name=${PROJECT_NAME}" \
  "trainer.experiment_name=${EXPERIMENT_NAME}" \
  'trainer.logger=["console"]' \
  "trainer.device=${TRAIN_DEVICE}" \
  trainer.nnodes=1 \
  "trainer.n_gpus_per_node=${NPROC_PER_NODE}" \
  "${extra_args[@]}" \
  "$@"
