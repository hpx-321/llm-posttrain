#!/usr/bin/env bash
# Generate real SFT candidates and test whether the candidate reward separates them.

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
RL_DIR=$(cd -- "${SCRIPT_DIR}/.." && pwd)
REPO_ROOT=$(cd -- "${RL_DIR}/../../../.." && pwd)

PYTHON_BIN=${PYTHON_BIN:-python3}
SFT_MODEL_PATH=${SFT_MODEL_PATH:-/mnt/model/qwen36-27b-create-my-card-sft-v1-merged}
TOKENIZER_PATH=${TOKENIZER_PATH:-/mnt/model/Qwen3.6-27B}
TENSOR_PARALLEL_SIZE=${TENSOR_PARALLEL_SIZE:-8}
GPU_MEMORY_UTILIZATION=${GPU_MEMORY_UTILIZATION:-0.90}
MAX_MODEL_LEN=${MAX_MODEL_LEN:-5632}
MAX_NEW_TOKENS=${MAX_NEW_TOKENS:-1536}
NUM_SAMPLES=${NUM_SAMPLES:-8}
TEMPERATURE=${TEMPERATURE:-0.7}
TOP_P=${TOP_P:-0.9}
SEED=${SEED:-42}
RUN_NAME=${RUN_NAME:-reward-separation-$(date +%Y%m%d-%H%M%S)}
OUTPUT_ROOT=${OUTPUT_ROOT:-${REPO_ROOT}/outputs/${RUN_NAME}}

TASKSPEC_FILE=${TASKSPEC_FILE:-${REPO_ROOT}/frameworks/verl/create_my_card/sft/data/source/taskspec.json}
LABELS_FILE=${LABELS_FILE:-${SCRIPT_DIR}/fixtures/content_labels_canary_16_diverse.json}
SYSTEM_PROMPT=${SYSTEM_PROMPT:-${REPO_ROOT}/frameworks/verl/create_my_card/sft/data/source/system_prompt.md}
BASELINE_CONFIG=${BASELINE_CONFIG:-${RL_DIR}/configs/reward_stage0.json}
VISUAL_CONFIG=${VISUAL_CONFIG:-${RL_DIR}/configs/reward_visual_candidate.json}

CANARY_PARQUET=${OUTPUT_ROOT}/canary-16-diverse.parquet
GENERATION_DIR=${OUTPUT_ROOT}/generation
RAW_CANDIDATES=${GENERATION_DIR}/raw_compact_dsl.jsonl
BASELINE_AUDIT=${OUTPUT_ROOT}/reward-baseline.jsonl
VISUAL_AUDIT=${OUTPUT_ROOT}/reward-l1-visual-reweighted.jsonl

fail() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

require_file() {
  [[ -f "$1" ]] || fail "required file does not exist: $1"
}

require_dir() {
  [[ -d "$1" ]] || fail "required directory does not exist: $1"
}

command -v "${PYTHON_BIN}" >/dev/null 2>&1 || fail "Python executable not found: ${PYTHON_BIN}"
require_dir "${SFT_MODEL_PATH}"
require_dir "${TOKENIZER_PATH}"
require_file "${TASKSPEC_FILE}"
require_file "${LABELS_FILE}"
require_file "${SYSTEM_PROMPT}"
require_file "${BASELINE_CONFIG}"
require_file "${VISUAL_CONFIG}"
[[ ! -e "${OUTPUT_ROOT}" ]] || fail "OUTPUT_ROOT already exists: ${OUTPUT_ROOT}"

mkdir -p "${OUTPUT_ROOT}"

printf '%s\n' \
  'CreateMyCard reward separation audit' \
  "Repository: ${REPO_ROOT}" \
  "SFT model: ${SFT_MODEL_PATH}" \
  "Tokenizer: ${TOKENIZER_PATH}" \
  "Output: ${OUTPUT_ROOT}" \
  "Candidates: 1 greedy + ${NUM_SAMPLES} sampled per TaskSpec" \
  "Sampling: temperature=${TEMPERATURE}, top_p=${TOP_P}, seed=${SEED}"

"${PYTHON_BIN}" "${SCRIPT_DIR}/build_reward_canary.py" \
  --taskspec-file "${TASKSPEC_FILE}" \
  --labels-file "${LABELS_FILE}" \
  --system-prompt "${SYSTEM_PROMPT}" \
  --output "${CANARY_PARQUET}"

# Conversion failures are model outcomes, not infrastructure failures.  The
# exporter saves raw candidates before converting them, so retain and audit all
# rows even when some candidates cannot be rendered.
set +e
"${PYTHON_BIN}" "${REPO_ROOT}/frameworks/verl/create_my_card/sft/evaluation/export_renderable_a2ui.py" \
  --model-path "${SFT_MODEL_PATH}" \
  --producer-checkpoint "${SFT_MODEL_PATH}" \
  --tokenizer-path "${TOKENIZER_PATH}" \
  --input-file "${CANARY_PARQUET}" \
  --output-dir "${GENERATION_DIR}" \
  --tensor-parallel-size "${TENSOR_PARALLEL_SIZE}" \
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION}" \
  --max-model-len "${MAX_MODEL_LEN}" \
  --max-new-tokens "${MAX_NEW_TOKENS}" \
  --include-greedy \
  --num-samples "${NUM_SAMPLES}" \
  --temperature "${TEMPERATURE}" \
  --top-p "${TOP_P}" \
  --seed "${SEED}"
export_status=$?
set -e

require_file "${RAW_CANDIDATES}"
if (( export_status != 0 )); then
  printf 'Candidate conversion reported failures; raw candidates are retained for reward audit.\n' >&2
fi

"${PYTHON_BIN}" "${SCRIPT_DIR}/audit_rewards.py" \
  --input "${RAW_CANDIDATES}" \
  --taskspec-file "${TASKSPEC_FILE}" \
  --labels-file "${LABELS_FILE}" \
  --reward-config "${BASELINE_CONFIG}" \
  --output "${BASELINE_AUDIT}" \
  --fail-on-masked

"${PYTHON_BIN}" "${SCRIPT_DIR}/audit_rewards.py" \
  --input "${RAW_CANDIDATES}" \
  --taskspec-file "${TASKSPEC_FILE}" \
  --labels-file "${LABELS_FILE}" \
  --reward-config "${VISUAL_CONFIG}" \
  --output "${VISUAL_AUDIT}" \
  --fail-on-masked

set +e
"${PYTHON_BIN}" "${SCRIPT_DIR}/analyze_reward_groups.py" \
  --input "${BASELINE_AUDIT}" \
  --output-json "${OUTPUT_ROOT}/reward-baseline-analysis.json" \
  --output-md "${OUTPUT_ROOT}/reward-baseline-analysis.md" \
  --expected-samples "${NUM_SAMPLES}"
baseline_analysis_status=$?

"${PYTHON_BIN}" "${SCRIPT_DIR}/analyze_reward_groups.py" \
  --input "${VISUAL_AUDIT}" \
  --output-json "${OUTPUT_ROOT}/reward-l1-visual-reweighted-analysis.json" \
  --output-md "${OUTPUT_ROOT}/reward-l1-visual-reweighted-analysis.md" \
  --expected-samples "${NUM_SAMPLES}"
reweighted_analysis_status=$?
set -e

git_revision=$(git -C "${REPO_ROOT}" rev-parse HEAD 2>/dev/null || printf 'unknown')
"${PYTHON_BIN}" -c \
  'import json,sys; from pathlib import Path; p=Path(sys.argv[1]); p.write_text(json.dumps({"git_revision":sys.argv[2],"sft_model_path":sys.argv[3],"tokenizer_path":sys.argv[4],"num_samples":int(sys.argv[5]),"temperature":float(sys.argv[6]),"top_p":float(sys.argv[7]),"seed":int(sys.argv[8]),"baseline_machine_gate_passed":sys.argv[9]=="0","l1_reweighted_machine_gate_passed":sys.argv[10]=="0"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")' \
  "${OUTPUT_ROOT}/run-manifest.json" \
  "${git_revision}" "${SFT_MODEL_PATH}" "${TOKENIZER_PATH}" "${NUM_SAMPLES}" \
  "${TEMPERATURE}" "${TOP_P}" "${SEED}" \
  "${baseline_analysis_status}" "${reweighted_analysis_status}"

printf '%s\n' \
  '' \
  'Audit completed.' \
  "Baseline report: ${OUTPUT_ROOT}/reward-baseline-analysis.md" \
  "L1 visual-reweighted report: ${OUTPUT_ROOT}/reward-l1-visual-reweighted-analysis.md" \
  "Renderable candidates: ${GENERATION_DIR}/*.card.genui.jsonl" \
  '' \
  'A PASS only means the reward has measurable within-group variance.' \
  'Do not start policy updates until best/worst candidates pass visual review and selective L2 rendering.'
