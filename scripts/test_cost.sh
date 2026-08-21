#!/usr/bin/env bash
# Verifies token counting + simulated cost calculation (SK-JF5-09).
set -uo pipefail

SMALL_PORT="${SMALL_SERVICE_PORT:-3001}"

echo "================================="
echo "Token Cost Tracking Test"
echo "================================="

response=$(curl -s -X POST "http://localhost:${SMALL_PORT}/generate" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Summarize why token cost tracking matters for LLM platforms."}')

echo "$response"

python3 - "$response" << 'EOF'
import sys, json

resp = json.loads(sys.argv[1])
input_tokens = resp["input_tokens"]
output_tokens = resp["output_tokens"]
reported_cost = resp["estimated_cost"]

import yaml
#with open("../config/pricing.yaml") as fh:
with open("config/pricing.yaml") as fh:
    pricing = yaml.safe_load(fh)["pricing"]["small-model"]

expected_input_cost = (input_tokens / 1000.0) * pricing["input_per_1k_tokens"]
expected_output_cost = (output_tokens / 1000.0) * pricing["output_per_1k_tokens"]
expected_total = round(expected_input_cost + expected_output_cost, 8)

print(f"expected_cost: {expected_total}")
print(f"reported_cost: {reported_cost}")

if abs(expected_total - reported_cost) < 1e-6:
    print("[PASS] Reported cost matches manual calculation from pricing.yaml")
    sys.exit(0)
else:
    print("[FAIL] Reported cost does not match manual calculation")
    sys.exit(1)
EOF
