#!/usr/bin/env python3
"""
Before/After optimization comparison (SK-JF5-09, Task 7).

"Before": every prompt sent to medium-model.
"After":  simple prompts routed to small-model, complex prompts to
          medium-model, per config/routing.yaml's word-count heuristic.

Sends the same prompt set through both configurations via the LiteLLM
gateway and reports average latency, total tokens, and estimated cost for
each so the student can see a measurable improvement.

Usage:
    python3 load_test.py [--host http://localhost:4000] [--key sk-local-dev-key]
"""

import argparse
import json
import statistics
import time
import urllib.request
import urllib.error

PROMPTS = [
    "What is preventive maintenance?",
    "List two common causes of motor bearing failure.",
    "Explain in detail the full lifecycle of a predictive maintenance program, from sensor installation through model retraining, for a mid-size manufacturing plant with mixed legacy and modern equipment.",
    "What does MTBF stand for?",
    "Describe, with specific examples, how vibration analysis, thermal imaging, and oil analysis can be combined into a single condition-monitoring strategy for CNC machining centers.",
    "Give one example of a manufacturing KPI.",
]


def classify(prompt: str) -> str:
    return "small-model" if len(prompt.split()) <= 12 else "medium-model"


def call(host: str, key: str, model: str, prompt: str) -> dict:
    body = json.dumps(
        {"model": model, "messages": [{"role": "user", "content": prompt}]}
    ).encode()
    req = urllib.request.Request(
        f"{host}/v1/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read())
            ok = True
    except urllib.error.URLError as exc:
        data = {"error": str(exc)}
        ok = False
    latency_ms = (time.perf_counter() - start) * 1000.0
    usage = data.get("usage", {}) if ok else {}
    return {
        "model": model,
        "success": ok,
        "latency_ms": latency_ms,
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
    }


PRICING = {
    "small-model": {"in": 0.0002, "out": 0.0004},
    "medium-model": {"in": 0.0005, "out": 0.0010},
}


def cost_of(record: dict) -> float:
    rates = PRICING.get(record["model"], {"in": 0.0, "out": 0.0})
    return (record["input_tokens"] / 1000.0) * rates["in"] + (
        record["output_tokens"] / 1000.0
    ) * rates["out"]


def run(host: str, key: str, label: str, model_for):
    print(f"\n--- {label} ---")
    records = []
    for prompt in PROMPTS:
        model = model_for(prompt)
        record = call(host, key, model, prompt)
        record["cost"] = cost_of(record)
        records.append(record)
        status = "ok" if record["success"] else "FAILED"
        print(
            f"  [{status}] model={record['model']:<14} "
            f"latency_ms={record['latency_ms']:.1f} "
            f"tokens={record['total_tokens']} cost={record['cost']:.6f}"
        )

    latencies = [r["latency_ms"] for r in records if r["success"]]
    total_tokens = sum(r["total_tokens"] for r in records)
    total_cost = sum(r["cost"] for r in records)

    summary = {
        "label": label,
        "avg_latency_ms": round(statistics.mean(latencies), 2) if latencies else None,
        "total_tokens": total_tokens,
        "total_cost": round(total_cost, 6),
    }
    print(f"  Summary: {summary}")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:4000")
    parser.add_argument("--key", default="sk-local-dev-key")
    args = parser.parse_args()

    before = run(args.host, args.key, "BEFORE (all requests -> medium-model)", lambda p: "medium-model")
    after = run(args.host, args.key, "AFTER (routed: simple -> small, complex -> medium)", classify)

    print("\n=================================")
    print("Optimization Result")
    print("=================================")
    print(json.dumps({"before": before, "after": after}, indent=2))

    if before["avg_latency_ms"] and after["avg_latency_ms"]:
        delta = before["avg_latency_ms"] - after["avg_latency_ms"]
        pct = (delta / before["avg_latency_ms"]) * 100 if before["avg_latency_ms"] else 0
        print(f"\nAvg latency change: {delta:+.2f} ms ({pct:+.1f}%)")
    if before["total_cost"] and after["total_cost"]:
        delta_cost = before["total_cost"] - after["total_cost"]
        print(f"Total cost change: {delta_cost:+.6f}")


if __name__ == "__main__":
    main()
