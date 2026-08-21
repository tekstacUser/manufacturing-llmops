"""
Shared token-cost tracking utility (SK-JF5-09).

Loads the simulated pricing table from config/pricing.yaml (mounted into
every serving container at /app/config/pricing.yaml) and computes
input/output/total cost for a single inference call.
"""

from __future__ import annotations

import os
import time
import yaml
from dataclasses import dataclass, asdict
from typing import Optional

PRICING_PATH = os.environ.get("PRICING_CONFIG_PATH", "/app/config/pricing.yaml")


@dataclass
class UsageRecord:
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: float
    input_cost: float
    output_cost: float
    estimated_cost: float
    success: bool
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class CostTracker:
    def __init__(self, model_alias: str, pricing_path: str = PRICING_PATH):
        self.model_alias = model_alias
        self._pricing = self._load_pricing(pricing_path)

    @staticmethod
    def _load_pricing(path: str) -> dict:
        try:
            with open(path, "r") as fh:
                data = yaml.safe_load(fh)
            return data.get("pricing", {})
        except FileNotFoundError:
            # Fail safe with zeroed pricing rather than crashing serving.
            return {}

    def rates_for(self, model_alias: Optional[str] = None) -> dict:
        alias = model_alias or self.model_alias
        return self._pricing.get(alias, {"input_per_1k_tokens": 0.0, "output_per_1k_tokens": 0.0})

    def record(
        self,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        success: bool = True,
        error: Optional[str] = None,
        model_alias: Optional[str] = None,
    ) -> UsageRecord:
        rates = self.rates_for(model_alias)
        input_cost = (input_tokens / 1000.0) * rates.get("input_per_1k_tokens", 0.0)
        output_cost = (output_tokens / 1000.0) * rates.get("output_per_1k_tokens", 0.0)
        total_cost = input_cost + output_cost

        return UsageRecord(
            model=model_alias or self.model_alias,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            latency_ms=round(latency_ms, 2),
            input_cost=round(input_cost, 8),
            output_cost=round(output_cost, 8),
            estimated_cost=round(total_cost, 8),
            success=success,
            error=error,
        )


class Timer:
    """Small context manager to measure wall-clock latency in milliseconds."""

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000.0
