#!/usr/bin/env bash
# Directly exercises each BentoML /generate endpoint (SK-JF5-01).
set -uo pipefail

SMALL_PORT="${SMALL_SERVICE_PORT:-3001}"
MEDIUM_PORT="${MEDIUM_SERVICE_PORT:-3002}"

pass=0
fail=0

test_model() {
  local name="$1" port="$2"
  echo "--- ${name} ---"
  response=$(curl -s -X POST "http://localhost:${port}/generate" \
    -H "Content-Type: application/json" \
    -d '{"prompt": "In one sentence, what is preventive maintenance?"}')
  echo "$response"

  success=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('success', False))" 2>/dev/null)
  if [ "$success" = "True" ]; then
    echo "[PASS] ${name} responded successfully"
    pass=$((pass+1))
  else
    echo "[FAIL] ${name} did not respond successfully"
    fail=$((fail+1))
  fi
}

echo "================================="
echo "Model Serving Test"
echo "================================="

test_model "small-model"  "$SMALL_PORT"
test_model "medium-model" "$MEDIUM_PORT"

echo "================================="
echo "Passed: $pass  Failed: $fail"
echo "================================="

[ "$fail" -eq 0 ]
