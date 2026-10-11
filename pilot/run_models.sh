#!/usr/bin/env bash
# Run several models over the agent sample, each with an early cost cutoff.
#
# The cutoff exists because a model's cost is its step count, not its token
# price: claude-sonnet-5.5 priced at ~$14 per 100 pairs and actually ran at
# $0.50 a pair, which is $50. So each model is stopped after a probe of
# PROBE pairs unless its measured rate is at or under MAX_RATE, and the probe
# costs at most PROBE x MAX_RATE x a small factor before anyone notices.
set -u
cd "$(dirname "$0")/.."

PROBE=${PROBE:-5}              # pairs to measure before committing
MAX_RATE=${MAX_RATE:-0.12}     # $/pair ceiling (gpt-5.1 measured 0.10)
ACCOUNT_CAP=${ACCOUNT_CAP:-38} # hard stop on total account spend
KEY="${OPENROUTER_API_KEY:?set OPENROUTER_API_KEY}"

spend() { curl -s https://openrouter.ai/api/v1/key -H "Authorization: Bearer $KEY" \
  | python3 -c "import json,sys;print(f\"{json.load(sys.stdin)['data']['usage']:.3f}\")" 2>/dev/null || echo ERR; }

export OPENAI_BASE_URL=https://openrouter.ai/api/v1 OPENAI_API_KEY="$KEY"
export AGENT_HINT=0 AGENT_CACHE=1 AGENT_PROMPT=neutral AGENT_RESERVE_USD=0.30

for MODEL in "$@"; do
  TAG=$(echo "$MODEL" | tr -c 'A-Za-z0-9' '-' | sed 's/-\+/-/g; s/^-//; s/-$//')
  OUT="pilot/agent_out_${TAG}"; LOG="pilot/logs/${TAG}.log"
  mkdir -p "$OUT" "$(dirname "$LOG")"
  START=$(spend)
  echo "=== $MODEL  (account \$$START)" | tee -a "$LOG"

  # --- probe: PROBE pairs, then decide
  head -$PROBE pilot/agent_sample_100.jsonl > /tmp/probe_ids.jsonl
  export AGENT_PRESPENT_USD="$START" AGENT_BUDGET_USD="$ACCOUNT_CAP"
  python3 pilot/agent_runner.py pilot/agent_sample_dataset.jsonl .cache/repo-data/python \
      "$OUT" --model="$MODEL" --ids-file=/tmp/probe_ids.jsonl --max-steps=40 2>&1 | tee -a "$LOG" | grep -E "finished=|spend:"
  AFTER=$(spend)
  DONE=$(find "$OUT/python" -name patch.diff 2>/dev/null | wc -l | tr -d ' ')
  if [ "$DONE" -eq 0 ]; then
    echo "  SKIP $MODEL: probe produced no patch (hung or failed); spent \$$(python3 -c "print(f'{$AFTER-$START:.3f}')")" | tee -a "$LOG"
    continue
  fi
  RATE=$(python3 -c "print(f'{($AFTER-$START)/$DONE:.4f}')")
  echo "  probe: $DONE pairs, \$$RATE/pair (ceiling \$$MAX_RATE), projects \$$(python3 -c "print(f'{($AFTER-$START)/$DONE*100:.2f}')") for 100" | tee -a "$LOG"
  if python3 -c "import sys; sys.exit(0 if $RATE > $MAX_RATE else 1)"; then
    echo "  SKIP $MODEL: too expensive, stopping after the probe" | tee -a "$LOG"
    continue
  fi

  # --- the rest, resumable (the probe's patches are kept and skipped)
  export AGENT_PRESPENT_USD="$(spend)"
  python3 pilot/agent_runner.py pilot/agent_sample_dataset.jsonl .cache/repo-data/python \
      "$OUT" --model="$MODEL" --ids-file=pilot/agent_sample_100.jsonl --max-steps=40 2>&1 | tee -a "$LOG" | grep -E "spend:"
  echo "  $MODEL done: $(find "$OUT/python" -name patch.diff | wc -l | tr -d ' ')/100 patches, account \$$(spend)" | tee -a "$LOG"
done
echo "ALL MODELS DONE, account \$$(spend)"
