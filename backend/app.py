"""
Backend API — Manufacturing Maintenance Intelligence Platform.

This service is PRE-DEFINED and fully implemented. Students do not modify
this file. It exists purely to give the chatbot frontend a simple endpoint
to call; all of the graded LLMOps work (serving, routing, monitoring,
quantization, cost tracking) happens upstream of this service in
gateway/litellm_config.yaml and serving/*.

Flow:
  Frontend -> Backend (/api/chat) -> LiteLLM Gateway -> BentoML -> llama.cpp

Routing: uses the same simple/complex word-count heuristic documented in
config/routing.yaml, so the model alias the backend picks always matches
what scripts/test_routing.sh and scripts/load_test.py expect.

Cost: computed here purely for *display* in the UI, using the same
simulated pricing table (config/pricing.yaml) that serving/common/cost_tracker.py
uses server-side.
"""

from __future__ import annotations

import os
import time
import logging

import yaml
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

LITELLM_BASE_URL = os.environ.get("LITELLM_BASE_URL", "http://litellm-gateway:4000")
LITELLM_MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY", "sk-local-dev-key")
ROUTING_CONFIG_PATH = os.environ.get("ROUTING_CONFIG_PATH", "/app/config/routing.yaml")
PRICING_CONFIG_PATH = os.environ.get("PRICING_CONFIG_PATH", "/app/config/pricing.yaml")
SIMPLE_WORD_THRESHOLD = int(os.environ.get("SIMPLE_WORD_THRESHOLD", "12"))

app = FastAPI(title="Manufacturing Maintenance Intelligence Platform - Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_yaml(path: str, default: dict) -> dict:
    try:
        with open(path, "r") as fh:
            return yaml.safe_load(fh) or default
    except FileNotFoundError:
        logger.warning("Config file not found at %s, using defaults", path)
        return default


class ChatRequest(BaseModel):
    prompt: str
    model_override: str | None = None  # allows the UI's model picker to force an alias


def classify_alias(prompt: str, override: str | None) -> str:
    if override:
        return override
    word_count = len(prompt.split())
    return "small-model" if word_count <= SIMPLE_WORD_THRESHOLD else "medium-model"


def estimate_cost(model_alias: str, input_tokens: int, output_tokens: int) -> float:
    pricing = _load_yaml(PRICING_CONFIG_PATH, {"pricing": {}}).get("pricing", {})
    rates = pricing.get(model_alias, {"input_per_1k_tokens": 0.0, "output_per_1k_tokens": 0.0})
    input_cost = (input_tokens / 1000.0) * rates.get("input_per_1k_tokens", 0.0)
    output_cost = (output_tokens / 1000.0) * rates.get("output_per_1k_tokens", 0.0)
    return round(input_cost + output_cost, 8)


@app.get("/api/health")
def health():
    return {"status": "ok", "litellm_base_url": LITELLM_BASE_URL}


@app.get("/api/models")
def models():
    return {"aliases": ["small-model", "medium-model", "quantized-model"]}


@app.post("/api/chat")
def chat(req: ChatRequest):
    alias = classify_alias(req.prompt, req.model_override)

    start = time.perf_counter()
    try:
        resp = httpx.post(
            f"{LITELLM_BASE_URL}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {LITELLM_MASTER_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": alias,
                "messages": [{"role": "user", "content": req.prompt}],
            },
            timeout=90.0,
        )
        latency_ms = (time.perf_counter() - start) * 1000.0
        resp.raise_for_status()
        data = resp.json()

        message = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        return {
            "success": True,
            "model": alias,
            "response": message,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "latency_ms": round(latency_ms, 2),
            "estimated_cost": estimate_cost(alias, input_tokens, output_tokens),
        }
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000.0
        logger.exception("Chat request failed")
        return {
            "success": False,
            "model": alias,
            "response": None,
            "error": str(exc),
            "latency_ms": round(latency_ms, 2),
        }
