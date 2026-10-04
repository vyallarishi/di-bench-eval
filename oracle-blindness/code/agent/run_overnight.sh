#!/bin/bash
# Overnight removal pilot: two models on the same 25 instances, then commit + dispatch the harness.
# Required env: OPENAI_API_KEY (OpenRouter key), OPENAI_BASE_URL=https://openrouter.ai/api/v1
# Optional: MODEL_A, MODEL_B, BUDGET_A, BUDGET_B, AGENT_PROMPT (neutral|strict)
set -u
cd "$(dirname "$0")/.."
PY=${PILOT_PYTHON:-python3.11}
MODEL_A=${MODEL_A:-deepseek/deepseek-v3.2}; MODEL_B=${MODEL_B:-qwen/qwen3-coder}
BUDGET_A=${BUDGET_A:-1.45}; BUDGET_B=${BUDGET_B:-1.45}
export AGENT_PROMPT=${AGENT_PROMPT:-neutral}
[ -n "${OPENAI_API_KEY:-}" ] || { echo "OPENAI_API_KEY not set"; exit 1; }
export OPENAI_BASE_URL=${OPENAI_BASE_URL:-https://openrouter.ai/api/v1}
mkdir -p pilot/logs predictions/agent/python
OUT=pilot/agent_out
for pair in "$MODEL_A:$BUDGET_A" "$MODEL_B:$BUDGET_B"; do
  model=${pair%:*}; budget=${pair##*:}
  echo "=== $(date -u +%H:%M) running $model budget \$$budget prompt=$AGENT_PROMPT ==="
  AGENT_BUDGET_USD=$budget $PY pilot/agent_runner.py .cache/dataset-dibench-regular.jsonl .cache/repo-data/python "$OUT" \
     --model="$model" --ids-file=${IDS_FILE:-pilot/agent_instances.jsonl} --max-steps=${MAX_STEPS:-16} 2>&1 | tee -a "pilot/logs/$(echo "$model" | tr '/' '_').log"
done
# collect: patches -> predictions/agent, dataset rows -> pilot/agent.jsonl
$PY - <<'PY'
import json, pathlib, shutil
out = pathlib.Path('pilot/agent_out'); dst = pathlib.Path('predictions/agent/python'); rows = []
seen = set()
for l in open(out / 'dataset.jsonl'):
    if not l.strip(): continue
    r = json.loads(l)
    if r['instance_id'] in seen: continue
    seen.add(r['instance_id']); rows.append(r)
    src = out / 'python' / r['instance_id']; d = dst / r['instance_id']; d.mkdir(parents=True, exist_ok=True)
    shutil.copy(src / 'patch.diff', d / 'patch.diff'); shutil.copy(src / 'trajs.json', d / 'trajs.json')
with open('pilot/agent.jsonl', 'w') as f:
    for r in rows: f.write(json.dumps(r) + '\n')
print('collected', len(rows), 'agent results')
PY
git add pilot/agent.jsonl predictions/agent pilot/logs 2>/dev/null
git commit -q -m "Removal pilot: agent patches ($MODEL_A, $MODEL_B, prompt=$AGENT_PROMPT)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" && GIT_TERMINAL_PROMPT=0 git push -q eval gh-eval:main
sleep 8
gh workflow run dibench-eval.yml -R vyallarishi/di-bench-eval -f set=agent -f shards=5 -f limit=0 && echo "harness dispatched (set=agent)"
sleep 10; gh run list -R vyallarishi/di-bench-eval --workflow dibench-eval.yml --limit 1 --json databaseId -q '.[0].databaseId' > pilot/logs/agent_run_id.txt
echo "=== $(date -u +%H:%M) done; harness run id $(cat pilot/logs/agent_run_id.txt) ==="
