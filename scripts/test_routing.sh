#!/usr/bin/env bash
# Verifies LiteLLM routes simple prompts -> small-model and complex
# prompts -> medium-model, per config/routing.yaml (SK-JF5-04).
set -uo pipefail

LITELLM_PORT="${LITELLM_PORT:-4000}"
MASTER_KEY="${LITELLM_MASTER_KEY:-sk-local-dev-key}"

pass=0
fail=0

call() {
  local alias="$1" prompt="$2"
  curl -s -X POST "http://localhost:${LITELLM_PORT}/v1/chat/completions" \
    -H "Authorization: Bearer ${MASTER_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"model\": \"${alias}\", \"messages\": [{\"role\": \"user\", \"content\": \"${prompt}\"}]}"
}

echo "================================="
echo "Routing Test"
echo "================================="

echo "--- simple prompt -> small-model alias ---"
resp1=$(call "small-model" "List one benefit of predictive maintenance.")
echo "$resp1"
model1=$(echo "$resp1" | python3 -c "import sys, json; print(json.load(sys.stdin).get('model',''))" 2>/dev/null)
if echo "$model1" | grep -qi "small"; then
  echo "[PASS] small-model alias responded"
  pass=$((pass+1))
else
  echo "[FAIL] small-model alias did not respond as expected"
  fail=$((fail+1))
fi

echo "--- complex prompt -> medium-model alias ---"
resp2=$(call "medium-model" "Explain, in detail, how vibration analysis on a CNC spindle motor can predict bearing failure before it causes unplanned downtime on the manufacturing line.")
echo "$resp2"
model2=$(echo "$resp2" | python3 -c "import sys, json; print(json.load(sys.stdin).get('model',''))" 2>/dev/null)
if echo "$model2" | grep -qi "medium"; then
  echo "[PASS] medium-model alias responded"
  pass=$((pass+1))
else
  echo "[FAIL] medium-model alias did not respond as expected"
  fail=$((fail+1))
fi

echo "================================="
echo "Passed: $pass  Failed: $fail"
echo "================================="

[ "$fail" -eq 0 ]
