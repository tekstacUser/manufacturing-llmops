"""
BentoML service exposing a llama.cpp-backed Qwen2.5 model (Quantized Variant).

This service runs the quantized model variant and points to its corresponding 
MODEL_ALIAS and MODEL_PATH defaults.

Endpoints:
  GET  /healthz                 -> health check
  POST /generate                -> simple {"prompt": "..."} inference
  POST /v1/chat/completions      -> OpenAI-compatible endpoint for LiteLLM routing
"""

import os
import sys
import time
import logging

import bentoml
from bentoml.io import JSON

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.llm_engine import LlamaCppEngine, ModelNotLoadedError  # noqa: E402
from common.cost_tracker import CostTracker, Timer  # noqa: E402
from common.tracing import log_trace  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("service")

# Quantized model default configurations
MODEL_ALIAS = os.environ.get("MODEL_ALIAS", "quantized-model")
MODEL_PATH = os.environ.get(
    "MODEL_PATH", "/models/qwen-1.5b-q4/qwen2.5-1.5b-instruct-q4_k_m.gguf"
)
N_CTX = int(os.environ.get("LLAMA_CTX_SIZE", "2048"))
N_THREADS = int(os.environ.get("LLAMA_THREADS", "2"))
MAX_TOKENS = int(os.environ.get("LLAMA_MAX_TOKENS", "256"))

engine = LlamaCppEngine(
    model_alias=MODEL_ALIAS,
    model_path=MODEL_PATH,
    n_ctx=N_CTX,
    n_threads=N_THREADS,
    max_tokens=MAX_TOKENS,
)
engine.load()

cost_tracker = CostTracker(model_alias=MODEL_ALIAS)

svc = bentoml.Service(name=f"bentoml-{MODEL_ALIAS}")


@svc.api(input=JSON(), output=JSON(), route="/generate")
def generate(payload: dict) -> dict:
    prompt = payload.get("prompt", "")
    max_tokens = payload.get("max_tokens")
    temperature = payload.get("temperature", 0.7)

    if not prompt:
        return {"error": "Field 'prompt' is required", "success": False}

    with Timer() as t:
        try:
            text, input_tokens, output_tokens = engine.generate(
                prompt, max_tokens=max_tokens, temperature=temperature
            )
            success, error = True, None
        except ModelNotLoadedError as exc:
            text, input_tokens, output_tokens = "", 0, 0
            success, error = False, str(exc)

    usage = cost_tracker.record(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=t.elapsed_ms,
        success=success,
        error=error,
    )

    # ----------------------------------------------------------------------
    # TODO: Log Observability Trace for /generate Endpoint
    # ----------------------------------------------------------------------
    # Instructions: Send execution details to Langfuse using `log_trace(...)`.
    # Map the following parameters:
    #   - name: "manufacturing-inference"
    #   - model: MODEL_ALIAS
    #   - prompt: prompt
    #   - response_text: text
    #   - input_tokens: input_tokens
    #   - output_tokens: output_tokens
    #   - latency_ms: t.elapsed_ms
    #   - input_cost: usage.input_cost
    #   - output_cost: usage.output_cost
    #   - estimated_cost: usage.estimated_cost
    #   - success: success
    #   - error: error
    #
    # Write the following block:
    log_trace(
        name="manufacturing-inference",
        model=MODEL_ALIAS,
        prompt=prompt,
        response_text=text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=t.elapsed_ms,
        input_cost=usage.input_cost,
        output_cost=usage.output_cost,
        estimated_cost=usage.estimated_cost,
        success=success,
        error=error,
    )

    return {
        "model": MODEL_ALIAS,
        "response": text,
        "success": success,
        "error": error,
        **usage.to_dict(),
    }


@svc.api(input=JSON(), output=JSON(), route="/v1/chat/completions")
def chat_completions(payload: dict) -> dict:
    """Minimal OpenAI-compatible endpoint so LiteLLM can proxy to this BentoML service."""
    messages = payload.get("messages", [])
    prompt = messages[-1]["content"] if messages else ""
    max_tokens = payload.get("max_tokens")
    temperature = payload.get("temperature", 0.7)

    with Timer() as t:
        try:
            text, input_tokens, output_tokens = engine.generate(
                prompt, max_tokens=max_tokens, temperature=temperature
            )
            success, error = True, None
        except ModelNotLoadedError as exc:
            text, input_tokens, output_tokens = "", 0, 0
            success, error = False, str(exc)

    usage = cost_tracker.record(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=t.elapsed_ms,
        success=success,
        error=error,
    )

    # ----------------------------------------------------------------------
    # TODO: Log Observability Trace for OpenAI Chat Completions Endpoint
    # ----------------------------------------------------------------------
    # Instructions: Send execution details to Langfuse using `log_trace(...)`.
    # Map the following parameters:
    #   - name: "manufacturing-inference-openai"
    #   - model: MODEL_ALIAS
    #   - prompt: prompt
    #   - response_text: text
    #   - input_tokens: input_tokens
    #   - output_tokens: output_tokens
    #   - latency_ms: t.elapsed_ms
    #   - input_cost: usage.input_cost
    #   - output_cost: usage.output_cost
    #   - estimated_cost: usage.estimated_cost
    #   - success: success
    #   - error: error
    #
    # Write the following block:
    log_trace(
        name="manufacturing-inference-openai",
        model=MODEL_ALIAS,
        prompt=prompt,
        response_text=text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=t.elapsed_ms,
        input_cost=usage.input_cost,
        output_cost=usage.output_cost,
        estimated_cost=usage.estimated_cost,
        success=success,
        error=error,
    )

    now = int(time.time())
    if not success:
        return {
            "error": {"message": error, "type": "model_not_loaded", "code": 503},
        }

    return {
        "id": f"chatcmpl-{now}",
        "object": "chat.completion",
        "created": now,
        "model": MODEL_ALIAS,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": usage.input_tokens,
            "completion_tokens": usage.output_tokens,
            "total_tokens": usage.total_tokens,
        },
    }