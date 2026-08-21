#!/usr/bin/env bash
# Confirms Langfuse is reachable locally (SK-JF5-05).
# Note: this checks connectivity only. Confirming that a specific trace
# appears is a manual step in the Langfuse UI (see monitoring/README.md)
# because the public Langfuse API requires the project's own API keys.
set -uo pipefail

LANGFUSE_PORT="${LANGFUSE_PORT:-3030}"

echo "================================="
echo "Monitoring Connectivity Test"
echo "================================="

code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${LANGFUSE_PORT}/api/public/health")

if [ "$code" = "200" ]; then
  echo "[PASS] Langfuse is reachable at http://localhost:${LANGFUSE_PORT}"
  echo "Next: send a request via test_models.sh, then check the Traces tab"
  echo "in the Langfuse UI to confirm it appears (see monitoring/README.md)."
  exit 0
else
  echo "[FAIL] Langfuse did not respond (http_code=${code})"
  exit 1
fi
