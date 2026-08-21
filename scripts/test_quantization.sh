#!/usr/bin/env bash
# Compares the non-quantized medium model against the quantized model on
# the same prompt: latency, tokens/sec, response size (SK-JF5-07).
#
# Requires the "quantization" compose profile to be running:
#   docker compose --profile quantization up -d bentoml-quantized
set -uo pipefail

MEDIUM_PORT="${MEDIUM_SERVICE_PORT:-3002}"
QUANTIZED_PORT="${QUANTIZED_SERVICE_PORT:-3003}"
PROMPT="Explain the difference between preventive and predictive maintenance in a factory."

run_and_report() {
  local name="$1" port="$2"
  echo "--- ${name} ---"
  start=$(date +%s%N)
  response=$(curl -s -X POST "http://localhost:${port}/generate" \
    -H "Content-Type: application/json" \
    -d "{\"prompt\": \"${PROMPT}\"}")
  end=$(date +%s%N)
  wall_ms=$(( (end - start) / 1000000 ))

  echo "$response" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"model: {d.get('model')}\")
print(f\"success: {d.get('success')}\")
print(f\"input_tokens: {d.get('input_tokens')}\")
print(f\"output_tokens: {d.get('output_tokens')}\")
print(f\"reported_latency_ms: {d.get('latency_ms')}\")
print(f\"estimated_cost: {d.get('estimated_cost')}\")
"
  echo "measured_wall_clock_ms: ${wall_ms}"
  echo ""
}

echo "================================="
echo "Quantization Comparison Test"
echo "================================="

echo "Model size on disk:"
du -h ../models/qwen-1.5b/*.gguf 2>/dev/null || echo "  (medium model file not found)"
du -h ../models/qwen-1.5b-q4/*.gguf 2>/dev/null || echo "  (quantized model file not found)"
echo ""

run_and_report "medium-model (fp16, non-quantized)" "$MEDIUM_PORT"
run_and_report "quantized-model (Q4_K_M)"          "$QUANTIZED_PORT"

echo "================================="
echo "Compare the numbers above: model size, tokens, and latency."
echo "The quantized model is expected to be smaller and faster, at a"
echo "small quality trade-off (discuss in results/quantization_notes.md)."
echo "================================="
