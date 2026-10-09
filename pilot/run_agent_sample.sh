#!/usr/bin/env bash
# The agent run on the 100-pair sample. Resumable: an instance whose patch.diff
# already exists is skipped, so a crash or a rate limit costs nothing but time.
#
#   OPENROUTER_API_KEY=sk-or-... ./pilot/run_agent_sample.sh openai/gpt-5.1 [budget]
#
# The budget is a hard stop inside the runner, checked after every API call.
set -euo pipefail
cd "$(dirname "$0")/.."

MODEL="${1:?usage: run_agent_sample.sh <openrouter-model-id> [budget-usd]}"
BUDGET="${2:-10.00}"
TAG=$(echo "$MODEL" | tr -c 'A-Za-z0-9' '-' | sed 's/-\+/-/g; s/^-//; s/-$//')
OUT="pilot/agent_out_${TAG}"
LOG="pilot/logs/${TAG}.log"
mkdir -p "$OUT" "$(dirname "$LOG")"

export OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://openrouter.ai/api/v1}"
export OPENAI_API_KEY="${OPENROUTER_API_KEY:-${OPENAI_API_KEY:?set OPENROUTER_API_KEY}}"
export AGENT_BUDGET_USD="$BUDGET"
export AGENT_PROMPT="${AGENT_PROMPT:-neutral}"   # neutral | strict
export AGENT_HINT="${AGENT_HINT:-1}"             # 1 = give the importing files
export AGENT_CACHE="${AGENT_CACHE:-1}"           # mark the system prompt cacheable

echo "model=$MODEL budget=\$$BUDGET prompt=$AGENT_PROMPT hint=$AGENT_HINT out=$OUT" | tee -a "$LOG"
python3 pilot/agent_runner.py \
  pilot/agent_sample_dataset.jsonl \
  .cache/repo-data/python \
  "$OUT" \
  --model="$MODEL" \
  --ids-file=pilot/agent_sample_100.jsonl \
  --max-steps=40 2>&1 | tee -a "$LOG"

echo "--- patches produced: $(find "$OUT/python" -name patch.diff 2>/dev/null | wc -l) of 100" | tee -a "$LOG"
echo "next: python3 scripts/gh/prepare.py --set agent ... then the harness, then grade_agent.py" | tee -a "$LOG"
