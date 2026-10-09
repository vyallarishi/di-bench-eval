#!/bin/bash
# Recompute every census number from the harness result directories, in order.
# usage: census_update.sh RES_TRACE RES_TRACE_LARGE RES_BLIND RES_BLIND_LARGE RES_ALL RES_ALL_LARGE
# The first four are the downloads of the corrected trace and blind-side runs; the last two are
# the canonical screening results (flakiness --first). Writes under oracle-blindness/{data,results}.
set -euo pipefail
cd "$(dirname "$0")/../.."
T=$1; TL=$2; B=$3; BL=$4; A=$5; AL=$6
R=oracle-blindness/results
echo "== traces"
python3 scripts/gh/extract_traces.py "$T" "$TL" --out oracle-blindness/data/traces --clean --states $R/trace_states.json
python3 scripts/gh/trace_fidelity.py --traces oracle-blindness/data/traces | tee $R/trace_fidelity.txt
echo "== flakiness, blind side"
mkdir -p $R/flakiness
python3 scripts/gh/flakiness.py --first "$A" --second "$B" --patches-first predictions/all --patches-second predictions/repeat_blind --ignore-injected --out $R/flakiness/blind_regular.json
python3 scripts/gh/flakiness.py --first "$AL" --second "$BL" --patches-first predictions/all_large --patches-second predictions/repeat_blind_large --ignore-injected --out $R/flakiness/blind_large.json
echo "== activation (section 3.2 rule)"
python3 scripts/gh/activation.py --results "$B" "$BL" --out $R/activation.json
echo "== per-repository rates, with and without the excluded silent cases"
python3 scripts/gh/robustness.py --exclude $R/activation.json --out $R/robustness.json
echo "== three oracles"
python3 scripts/gh/oracle_overlap.py --exclude $R/activation.json --out $R/oracle_overlap.json
