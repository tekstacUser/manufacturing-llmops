"""
Shared Langfuse instrumentation (SK-JF5-05).

Wraps the Langfuse Python SDK so each serving container can log a trace for
every inference call: model, prompt, response, token counts, latency and
success/failure. Langfuse runs locally (docker-compose service `langfuse`) -
no cloud Langfuse is used.
"""

from __future__ import annotations

import os
import logging
from typing import Optional

logger = logging.getLogger("tracing")

LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "http://langfuse:3000")
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")

_client = None
_enabled = bool(LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)

if _enabled:
    try:
        from langfuse import Langfuse

        _client = Langfuse(
            host=LANGFUSE_HOST,
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
        )
    except Exception as exc:  # pragma: no cover - defensive, must never break serving
        logger.warning("Langfuse client could not be initialized: %s", exc)
        _client = None
        _enabled = False
else:
    logger.warning(
        "LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY not set - "
        "traces will be logged to stdout only."
    )


def log_trace(
    name: str,
    model: str,
    prompt: str,
    response_text: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: float,
    success: bool,
    input_cost: float = 0.0,
    output_cost: float = 0.0,
    estimated_cost: float = 0.0,
    error: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    """Log a single inference call as a Langfuse trace + generation."""

    total_tokens = input_tokens + output_tokens
    payload = {
        "name": name,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "latency_ms": round(latency_ms, 2),
        "estimated_cost": round(estimated_cost, 8),
        "success": success,
        "error": error,
    }

    if not _enabled or _client is None:
        logger.info("[trace:no-langfuse] %s", payload)
        return

    try:
        trace = _client.trace(
            name=name,
            input=prompt,
            output=response_text if success else None,
            metadata=metadata or {},
            tags=["manufacturing-llmops", model],
        )
        trace.generation(
            name=f"{name}-generation",
            model=model,
            input=prompt,
            output=response_text if success else None,
        
            usage={
                "unit": "TOKENS",
                "input": input_tokens,
                "output": output_tokens,
                "total": total_tokens,
                "input_cost": round(input_cost, 8),
                "output_cost": round(output_cost, 8),
                "total_cost": round(estimated_cost, 8),
            },
        
            metadata={
                "latency_ms": round(latency_ms, 2),
                "success": success,
                "error": error,
            },
        
            level="DEFAULT" if success else "ERROR",
        )
        _client.flush()
    except Exception as exc:  # pragma: no cover - never break serving on tracing failure
        logger.warning("Failed to log Langfuse trace: %s", exc)
