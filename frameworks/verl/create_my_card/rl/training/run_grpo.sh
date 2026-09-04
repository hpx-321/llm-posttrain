#!/usr/bin/env bash
set -euo pipefail

# Foreground GRPO launcher used by the pipeline command backend.  Unlike the
# standalone GSM8K helper, this script must not nohup: the runner owns process
# lifetime, logs, success detection, and stage manifests.

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
RL_DIR=$(cd -- "${SCRIPT_DIR}/.." && pwd)
PROJECT_ROOT=$(cd -- "${SCRIPT_DIR}/../../../../.." && pwd)

: "${MODEL_PATH:?MODEL_PATH is required.}"
: "${DATA_DIR:?DATA_DIR is required.}"
: "${SAVE_PATH:?SAVE_PATH is required.}"

REWARD_FUNCTION_PATH=${REWARD_FUNCTION_PATH:-${RL_DIR}/reward/verl_adapter.py}
REWARD_CONFIG=${REWARD_CONFIG:-${RL_DIR}/configs/reward_stage0.json}
TOKENIZER_PATH=${TOKENIZER_PATH:-${MODEL_PATH}}
PIPELINE_EXECUTION_MODE=${PIPELINE_EXECUTION_MODE:-smoke}

TRAIN_DEVICE=${TRAIN_DEVICE:-npu}
NPROC_PER_NODE=${NPROC_PER_NODE:-16}
TRAIN_BATCH_SIZE=${TRAIN_BATCH_SIZE:-4}
PPO_MINI_BATCH_SIZE=${PPO_MINI_BATCH_SIZE:-4}
PPO_MICRO_BATCH_SIZE_PER_GPU=${PPO_MICRO_BATCH_SIZE_PER_GPU:-1}
MAX_PROMPT_LENGTH=${MAX_PROMPT_LENGTH:-4096}
MAX_RESPONSE_LENGTH=${MAX_RESPONSE_LENGTH:-1536}
MAX_MODEL_LEN=${MAX_MODEL_LEN:-5632}
MAX_NUM_BATCHED_TOKENS=${MAX_NUM_BATCHED_TOKENS:-5632}
MAX_NUM_SEQS=${MAX_NUM_SEQS:-8}
ROLLOUT_N=${ROLLOUT_N:-8}
ROLLOUT_TP_SIZE=${ROLLOUT_TP_SIZE:-8}
ROLLOUT_GPU_MEMORY_UTILIZATION=${ROLLOUT_GPU_MEMORY_UTILIZATION:-0.15}
LEARNING_RATE=${LEARNING_RATE:-5e-7}
KL_LOSS_COEF=${KL_LOSS_COEF:-0.001}
ENTROPY_COEFF=${ENTROPY_COEFF:-0.001}
TOTAL_EPOCHS=${TOTAL_EPOCHS:-1}
SMOKE_STEPS=${SMOKE_STEPS:-20}

for path in "${MODEL_PATH}" "${DATA_DIR}/train.parquet" "${DATA_DIR}/validation.parquet" \
  "${REWARD_FUNCTION_PATH}" "${REWARD_CONFIG}"; do
  if [[ ! -e "${path}" ]]; then
    echo "Error: required GRPO input does not exist: ${path}" >&2
    exit 1
  fi
done
if [[ -e "${SAVE_PATH}" ]]; then
  echo "Error: GRPO output checkpoint already exists: ${SAVE_PATH}" >&2
  exit 1
fi
if [[ "${PIPELINE_EXECUTION_MODE}" == "train" && \
      "${CMC_ALLOW_UNVALIDATED_REWARD:-0}" == "1" ]]; then
  echo "Error: train mode cannot enable CMC_ALLOW_UNVALIDATED_REWARD." >&2
  exit 1
fi

if [[ "${PIPELINE_EXECUTION_MODE}" == "train" ]]; then
  python3 - "${REWARD_CONFIG}" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, encoding="utf-8-sig") as stream:
    config = json.load(stream)
required = {"contract", "content", "static_layout", "style", "efficiency"}
if config.get("status") != "validated_for_policy_update":
    raise SystemExit("Error: train mode requires a validated_for_policy_update reward config.")
if config.get("policy_update_enabled") is not True:
    raise SystemExit("Error: train mode requires policy_update_enabled=true.")
if set(config.get("calibrated_components", [])) != required:
    raise SystemExit("Error: train mode requires every reward component to be calibrated.")
PY
fi
if [[ "${PIPELINE_EXECUTION_MODE}" != "train" && \
      "${PIPELINE_EXECUTION_MODE}" != "smoke" ]]; then
  echo "Error: command GRPO supports only smoke or train execution modes." >&2
  exit 1
fi

export PYTHONUNBUFFERED=1
export HYDRA_FULL_ERROR=1
export CMC_REWARD_CONFIG="${REWARD_CONFIG}"
export CMC_TOKENIZER_PATH="${TOKENIZER_PATH}"
unset PYTORCH_NPU_ALLOC_CONF || true

mode_args=()
inspection_args=()
if [[ "${PIPELINE_EXECUTION_MODE}" == "smoke" ]]; then
  export CMC_ALLOW_UNVALIDATED_REWARD=1
  mode_args+=(
  "trainer.total_training_steps=${SMOKE_STEPS}"
    trainer.total_epochs=1
    trainer.save_freq=1
    trainer.test_freq=-1
  )
else
  mode_args+=(
    "trainer.total_epochs=${TOTAL_EPOCHS}"
    trainer.save_freq=100
    trainer.test_freq=25
  )
fi
if [[ "${GRPO_CONFIG_ONLY:-0}" == "1" ]]; then
  inspection_args+=(--cfg job --resolve)
fi

mkdir -p -- "$(dirname -- "${SAVE_PATH}")"
cd "${PROJECT_ROOT}"

python3 -m verl.trainer.main_ppo \
  "data.train_files=${DATA_DIR}/train.parquet" \
  "data.val_files=${DATA_DIR}/validation.parquet" \
  "data.train_batch_size=${TRAIN_BATCH_SIZE}" \
  "data.max_prompt_length=${MAX_PROMPT_LENGTH}" \
  "data.max_response_length=${MAX_RESPONSE_LENGTH}" \
  data.dataloader_num_workers=0 \
  data.truncation=error \
  +data.apply_chat_template_kwargs.enable_thinking=false \
  "actor_rollout_ref.model.path=${MODEL_PATH}" \
  actor_rollout_ref.model.enable_gradient_checkpointing=true \
  actor_rollout_ref.model.enable_activation_offload=true \
  actor_rollout_ref.actor.strategy=fsdp2 \
  actor_rollout_ref.actor.fsdp_config.param_offload=true \
  actor_rollout_ref.actor.fsdp_config.optimizer_offload=true \
  "actor_rollout_ref.actor.optim.lr=${LEARNING_RATE}" \
  "actor_rollout_ref.actor.ppo_mini_batch_size=${PPO_MINI_BATCH_SIZE}" \
  "actor_rollout_ref.actor.ppo_micro_batch_size_per_gpu=${PPO_MICRO_BATCH_SIZE_PER_GPU}" \
  actor_rollout_ref.actor.ppo_epochs=1 \
  actor_rollout_ref.actor.use_kl_loss=true \
  "actor_rollout_ref.actor.kl_loss_coef=${KL_LOSS_COEF}" \
  actor_rollout_ref.actor.kl_loss_type=low_var_kl \
  "actor_rollout_ref.actor.entropy_coeff=${ENTROPY_COEFF}" \
  actor_rollout_ref.actor.calculate_entropy=true \
  actor_rollout_ref.actor.loss_agg_mode=token-mean \
  actor_rollout_ref.ref.strategy=fsdp2 \
  actor_rollout_ref.ref.fsdp_config.param_offload=true \
  actor_rollout_ref.ref.log_prob_micro_batch_size_per_gpu=1 \
  actor_rollout_ref.rollout.name=vllm \
  "actor_rollout_ref.rollout.tensor_model_parallel_size=${ROLLOUT_TP_SIZE}" \
  "actor_rollout_ref.rollout.n=${ROLLOUT_N}" \
  actor_rollout_ref.rollout.temperature=0.8 \
  actor_rollout_ref.rollout.top_p=0.95 \
  "actor_rollout_ref.rollout.max_model_len=${MAX_MODEL_LEN}" \
  "actor_rollout_ref.rollout.max_num_batched_tokens=${MAX_NUM_BATCHED_TOKENS}" \
  "actor_rollout_ref.rollout.max_num_seqs=${MAX_NUM_SEQS}" \
  "actor_rollout_ref.rollout.gpu_memory_utilization=${ROLLOUT_GPU_MEMORY_UTILIZATION}" \
  actor_rollout_ref.rollout.log_prob_micro_batch_size_per_gpu=1 \
  actor_rollout_ref.rollout.enforce_eager=true \
  actor_rollout_ref.rollout.free_cache_engine=true \
  algorithm.adv_estimator=grpo \
  algorithm.use_kl_in_reward=false \
  algorithm.norm_adv_by_std_in_grpo=true \
  "custom_reward_function.path=${REWARD_FUNCTION_PATH}" \
  custom_reward_function.name=compute_score \
  "trainer.device=${TRAIN_DEVICE}" \
  'trainer.logger=["console","tensorboard"]' \
  trainer.project_name=create-my-card-rl \
  trainer.experiment_name=taskspec-to-dsl-grpo \
  "trainer.n_gpus_per_node=${NPROC_PER_NODE}" \
  trainer.nnodes=1 \
  trainer.val_before_train=false \
  trainer.critic_warmup=0 \
  "trainer.default_local_dir=${SAVE_PATH}" \
  "${mode_args[@]}" \
  "${inspection_args[@]}" \
  "$@"
