#!/usr/bin/env bash
# Health-checks every core service (SK-JF5-01).
set -uo pipefail

SMALL_PORT="${SMALL_SERVICE_PORT:-3001}"
MEDIUM_PORT="${MEDIUM_SERVICE_PORT:-3002}"
LITELLM_PORT="${LITELLM_PORT:-4000}"
BACKEND_PORT="${BACKEND_PORT:-8080}"
FRONTEND_PORT="${FRONTEND_PORT:-8081}"
LANGFUSE_PORT="${LANGFUSE_PORT:-3030}"

pass=0
fail=0

check() {
  local name="$1" url="$2" method="${3:-GET}"
  if [ "$method" = "POST" ]; then
    code=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{}' "$url")
  else
    code=$(curl -s -o /dev/null -w "%{http_code}" "$url")
  fi
  if [ "$code" = "200" ]; then
    echo "[PASS] $name ($url -> $code)"
    pass=$((pass+1))
  else
    echo "[FAIL] $name ($url -> $code)"
    fail=$((fail+1))
  fi
}

echo "================================="
echo "Health Check"
echo "================================="

check "Small model service"  "http://localhost:${SMALL_PORT}/healthz" POST
check "Medium model service" "http://localhost:${MEDIUM_PORT}/healthz" POST
check "LiteLLM gateway"      "http://localhost:${LITELLM_PORT}/health/liveliness"
check "Backend API"          "http://localhost:${BACKEND_PORT}/api/health"
check "Frontend UI"          "http://localhost:${FRONTEND_PORT}/healthz"
check "Langfuse"             "http://localhost:${LANGFUSE_PORT}/api/public/health"

echo "================================="
echo "Passed: $pass  Failed: $fail"
echo "================================="

[ "$fail" -eq 0 ]
