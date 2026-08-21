#!/usr/bin/env bash
# Master validation script - runs every check and prints a single summary.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

declare -A RESULTS

run_check() {
  local label="$1"; shift
  if "$@" > /tmp/"${label// /_}".log 2>&1; then
    RESULTS["$label"]="PASS"
  else
    RESULTS["$label"]="FAIL"
  fi
}

echo "================================="
echo "Activity 1 Validation"
echo "================================="

run_check "Small model serving"   bash -c './test_models.sh 2>&1 | grep -q "\[PASS\] small-model"'
run_check "Medium model serving"  bash -c './test_models.sh 2>&1 | grep -q "\[PASS\] medium-model"'
run_check "LiteLLM gateway"       bash -c 'curl -sf "http://localhost:${LITELLM_PORT:-4000}/health/liveliness" > /dev/null'
run_check "Model routing"         ./test_routing.sh
run_check "Langfuse connectivity" ./test_monitoring.sh
run_check "Quantized model"       ./test_quantization.sh
run_check "Token tracking"        ./test_cost.sh
run_check "Cost calculation"      ./test_cost.sh
run_check "Optimization"          bash -c 'python3 load_test.py > /tmp/load_test.log 2>&1'

overall="PASS"
for label in "Small model serving" "Medium model serving" "LiteLLM gateway" "Model routing" \
             "Langfuse connectivity" "Quantized model" "Token tracking" "Cost calculation" "Optimization"; do
  status="${RESULTS[$label]:-FAIL}"
  echo "[$status] $label"
  [ "$status" = "FAIL" ] && overall="FAIL"
done

echo "================================="
echo "RESULT: $overall"
echo "================================="

echo ""
echo "================================="
echo "Frontend / Backend UI (informational)"
echo "================================="
run_check "Backend API"  bash -c 'curl -sf "http://localhost:${BACKEND_PORT:-8080}/api/health" > /dev/null'
run_check "Frontend UI"  bash -c 'curl -sf "http://localhost:${FRONTEND_PORT:-8081}/healthz" > /dev/null'
echo "[${RESULTS['Backend API']:-FAIL}] Backend API"
echo "[${RESULTS['Frontend UI']:-FAIL}] Frontend UI"
echo "================================="

[ "$overall" = "PASS" ]
