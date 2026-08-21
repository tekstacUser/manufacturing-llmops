# Activity 1 — Complete Solution — Instructor Notes

This ZIP (`activity1-complete-solution.zip`) contains the fully working
reference implementation for the Manufacturing Maintenance Intelligence
Platform lab. It shares the exact `manufacturing-llmops/` project structure
as `activity1-student-skeleton.zip`, with every TODO completed.

## Complete Architecture

```text
Browser
   |
   v
Frontend UI (Docker container)
   |
   v
Backend API (Docker container)
   |
   v
LiteLLM Gateway
   |
   +-------------------+
   |                   |
   v                   v
BentoML             BentoML
Small Model        Medium Model
   |                   |
   v                   v
llama.cpp            llama.cpp
   |                   |
   v                   v
Qwen2.5-0.5B GGUF   Qwen2.5-1.5B GGUF
                        |
                        v
                Qwen2.5-1.5B Q4
                     GGUF
                        |
                        v
                   Langfuse
                  OSS (:3030)
```

The core LLMOps stack (LiteLLM → BentoML → llama.cpp → GGUF models →
Langfuse) is unchanged from the original architecture and TCA coverage.
The frontend and backend are an additive layer on top, giving learners a
real chatbot UI to exercise that stack through.

## Why each technology is used

| Technology            | Reason |
|--------------------------|--------|
| **Frontend (nginx + static HTML/CSS/JS)** | Lightweight, dependency-free chatbot UI - no Node build step required inside Docker, fast to start on the CPU-only VM. |
| **Backend (FastAPI)**        | Thin API the frontend calls; resolves the simple/complex model alias from `config/routing.yaml` and forwards to LiteLLM, then returns response + token/latency/cost info for the UI to display. Not a graded component - it exists to make the graded components (routing, serving, cost) visible and testable through a UI. |
| **BentoML**                | Provides a clean, production-style Python serving wrapper (health checks, REST API, Docker packaging) around llama.cpp without requiring a heavier serving stack. |
| **llama.cpp** (`llama-cpp-python`) | CPU-only, no-GPU inference engine for GGUF models — fits the 4 vCPU / no-NVIDIA hardware constraint exactly. |
| **LiteLLM**                  | Lightweight OpenAI-compatible proxy/gateway that gives model aliasing, routing, timeouts, and fallback without an external managed router. |
| **Langfuse OSS**               | Self-hostable LLM observability (traces, token usage, latency) — explicitly required instead of Prometheus/Grafana. Exposed on host port **3030** (never 3000). |
| **Docker Compose**               | Matches the assessment VM exactly (Docker + Docker Compose, no Kubernetes). |

## Complete Setup

```bash
cd manufacturing-llmops
cp .env.example .env
# place pre-provisioned GGUF files under models/qwen-0.5b, models/qwen-1.5b,
# models/qwen-1.5b-q4 (see each folder's README.md)
docker compose up -d --build
```

This brings up `frontend`, `backend`, `bentoml-small`, `bentoml-medium`,
`litellm-gateway`, `langfuse-db`, and `langfuse`. Bring up the quantized
service only when needed (keeps the default footprint small on the 15 GiB
VM):

```bash
docker compose --profile quantization up -d --build bentoml-quantized
```

For Langfuse trace visibility, generate a local public/secret key pair
from the Langfuse UI at `http://localhost:3030` (Settings → API Keys) and
put them in `.env`, then `docker compose up -d --force-recreate
bentoml-small bentoml-medium` — see `README.md` → "Configuring your .env
file" for the exact walkthrough given to learners.

## Complete Execution / Verification

```bash
docker compose ps
bash scripts/run_all_tests.sh
```

Individual checks:

```bash
bash scripts/health_check.sh
bash scripts/test_models.sh
bash scripts/test_routing.sh
bash scripts/test_monitoring.sh
bash scripts/test_quantization.sh
bash scripts/test_cost.sh
python3 scripts/load_test.py
```

UI-level check: open `http://localhost:8001`, send a short prompt and a
long/detailed prompt, and confirm the info chip under each response shows
`small-model` and `medium-model` respectively. Then open
`http://localhost:3030` and confirm matching traces exist. Full step-by-
step is in `README.md` → "UI Validation".

## Expected Output

`scripts/run_all_tests.sh` prints a PASS/FAIL line per requirement and a
final `RESULT: PASS` once:

- both `bentoml-small` and `bentoml-medium` respond successfully to
  `/generate`,
- the LiteLLM gateway is reachable and routes `small-model` /
  `medium-model` aliases correctly,
- Langfuse is reachable at `http://localhost:3030` (a trace should also be
  visible in its UI after any inference call — see `monitoring/README.md`),
- the quantized service (started via the `quantization` profile) responds,
- token counts and the simulated cost calculation in
  `scripts/test_cost.sh` match the numbers derivable from
  `config/pricing.yaml`,
- `scripts/load_test.py` prints a before/after summary showing the routed
  ("after") run's average latency and total cost differ measurably from
  routing everything to `medium-model` ("before"),
- the script's informational section additionally confirms `backend` and
  `frontend` are healthy and reachable.

Exact latency/token numbers are hardware- and model-file dependent and are
intentionally **not** hardcoded anywhere in this solution — they are
produced live by the scripts above against whatever GGUF files are
provisioned in your environment. If GGUF files are not present in a given
environment, `scripts/*.sh` will report `[FAIL]` / connection errors rather
than fabricated numbers — provision the models first.

## Troubleshooting

See `README.md` → Troubleshooting for the full beginner-facing list,
including frontend/backend-specific entries. From an instructor
perspective, the most common setup issue is a missing or mis-named GGUF
file — `config/models.yaml` and `.env.example` both name the exact
expected filenames.

## TCA Mapping

TCA coverage is unchanged from the original architecture - the frontend
and backend are not part of any graded competency, they exist only to
give learners a UI to exercise the platform through.

```text
SK-JF5-01 (LLM Serving Frameworks)              -> BentoML + llama.cpp
                                                     serving/{small,medium,quantized}/service.py
                                                     serving/common/llm_engine.py

SK-JF5-04 (Model Routing & Gateway)             -> LiteLLM
                                                     gateway/litellm_config.yaml
                                                     config/routing.yaml
                                                     scripts/test_routing.sh

SK-JF5-05 (LLM Monitoring)                      -> Langfuse OSS (local only, host port 3030)
                                                     serving/common/tracing.py
                                                     monitoring/README.md
                                                     scripts/test_monitoring.sh

SK-JF5-07 (Model Quantization)                  -> Qwen2.5-1.5B GGUF vs Qwen2.5-1.5B Q4 GGUF
                                                     serving/quantized/service.py
                                                     scripts/test_quantization.sh
                                                     results/quantization_notes.md

SK-JF5-09 (Token Cost Tracking & Optimization)  -> Token accounting + simulated pricing + before/after routing
                                                     config/pricing.yaml
                                                     serving/common/cost_tracker.py
                                                     scripts/test_cost.sh
                                                     scripts/load_test.py
```

## Notes on faithfulness to the requirements

- No Kubernetes, GPU scheduling, Prometheus, Grafana, Hugging Face
  auto-downloads, or cloud LLM APIs are used anywhere in this solution.
- All three model roles (`small-model`, `medium-model`, `quantized-model`)
  are pre-provisioned local GGUF files — nothing is downloaded at
  assessment time.
- The compose file keeps `bentoml-quantized` behind a profile so the
  default `docker compose up -d` does not run all three model instances
  concurrently on the 4 vCPU / ~15 GiB VM, while still letting students
  demonstrate all three during the quantization task.
- Langfuse is exposed on host port **3030** exclusively; host port 3000 is
  not used anywhere in this stack (the `langfuse` container's own internal
  listening port, 3000, is only ever reached container-to-container over
  the private `llmops-net` network, never from the host or the browser).
- The frontend and backend are fully implemented, run as their own Docker
  containers, and are explicitly out of scope for student edits - they
  exist to make the graded LLMOps work (serving, routing, monitoring,
  quantization, cost tracking) demonstrable through a real chat UI.


after deployed to trial2 
frontend/static/env.js.template
// Runtime configuration - values are substituted from environment variables
// by docker-entrypoint.sh when the container starts (see Dockerfile).
window.APP_CONFIG = {
  //BACKEND_URL: "${BACKEND_PUBLIC_URL}",
  //LANGFUSE_URL: "${LANGFUSE_PUBLIC_URL}",
  BACKEND_URL: `http://${window.location.hostname}:8002`,
  LANGFUSE_URL: `http://${window.location.hostname}:3030`
};
