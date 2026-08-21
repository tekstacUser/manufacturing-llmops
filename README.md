# Manufacturing Maintenance Intelligence Platform — Activity 1

A local, CPU-only LLMOps lab where you serve two Qwen2.5 models behind a
gateway, route requests intelligently, monitor them, quantize one model,
and track simulated token cost — all behind a chatbot UI, for a
manufacturing maintenance assistant use case.

## Introduction

A manufacturing plant wants an internal assistant that helps maintenance
technicians answer quick questions ("what does this error code mean?") and
work through longer diagnostic reasoning ("walk me through likely causes of
this vibration pattern"). Simple questions should be answered by a small,
fast model; complex questions should go to a larger model. Every request
must be observable (traced) and its cost must be tracked, and the platform
must run entirely on a modest on-prem CPU server — no GPU, no cloud APIs.

This lab builds exactly that platform, with a chatbot UI a technician could
actually use.

## Architecture

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

The **frontend** and **backend** are fully pre-built — you don't write or
edit any code there. They give you a real chatbot UI to exercise the
platform you *are* building (serving, routing, monitoring, quantization,
cost tracking). Every inference call is logged as a Langfuse trace, and its
token usage is used to compute a simulated cost using `config/pricing.yaml`.

## Prerequisites

- Docker
- Docker Compose (v2, i.e. the `docker compose` subcommand)
- Basic Linux command-line familiarity
- Basic YAML reading/editing
- Basic Python understanding (the serving code and scripts are Python)

No cloud accounts, API keys, or internet access are required. All three
models must already be present under `models/` before you start (see each
`models/*/README.md`).

## Project Structure

```text
manufacturing-llmops/
├── README.md              This file
├── TODO.md                Your task list (skeleton only)
├── docker-compose.yml      Orchestrates every service
├── .env.example             Copy to .env and adjust as needed
├── config/
│   ├── models.yaml          Model registry (paths, roles, engine settings)
│   ├── routing.yaml         Simple-vs-complex routing rules
│   └── pricing.yaml         Simulated per-1k-token pricing
├── models/                  Pre-provisioned GGUF files go here (not downloaded)
├── frontend/                 Chatbot UI (Docker container) - PRE-BUILT, do not edit
├── backend/                   API that the UI calls (Docker container) - PRE-BUILT, do not edit
├── serving/
│   ├── common/               Shared llama.cpp / cost / tracing code
│   ├── small/                 BentoML service for the 0.5B model
│   ├── medium/                 BentoML service for the 1.5B model
│   └── quantized/              BentoML service for the 1.5B Q4 model
├── gateway/
│   ├── litellm_config.yaml     LiteLLM aliases + routing + fallback
│   └── Dockerfile
├── monitoring/
│   └── README.md              How to set up Langfuse locally
├── scripts/                  Validation and load-test scripts
└── results/                  Where you record your quantization/optimization findings
```

`frontend/` and `backend/` are **not** TODO areas — they are complete,
working Docker containers provided so you have a real UI to test against.
All of your graded work happens in `serving/`, `gateway/`, and `config/`.

## Lab Workflow

```text
Environment Check
       ↓
LLM Serving
       ↓
LiteLLM Gateway
       ↓
Routing
       ↓
Langfuse Monitoring
       ↓
Quantized Model
       ↓
Token Cost
       ↓
Optimization
       ↓
Final Validation (incl. UI)
```

This maps to `TODO.md` Tasks 1–8 and to the 60-minute assessment timeline in
`SOLUTION_README.md` (Task 1 ≈ 05–15 min, Task 2–3 ≈ 15–27 min, Task 4 ≈
27–39 min, Task 5 ≈ 39–48 min, Tasks 6–7 ≈ 48–57 min, Task 8 ≈ 57–60 min).

## Execution

1. Confirm the model files exist under `models/qwen-0.5b/`,
   `models/qwen-1.5b/`, and `models/qwen-1.5b-q4/` (see each folder's README).
2. Copy the environment file:
   ```bash
   cp .env.example .env
   ```
2.1 Before build run download the models from hugging face
python3 -m pip install -U huggingface_hub
hf --version

hf download Qwen/Qwen2.5-0.5B-Instruct-GGUF \
  qwen2.5-0.5b-instruct-q4_k_m.gguf \
  --local-dir models/qwen-0.5b

hf download Qwen/Qwen2.5-1.5B-Instruct-GGUF \
  qwen2.5-1.5b-instruct-fp16.gguf \
  --local-dir models/qwen-1.5b

hf download Qwen/Qwen2.5-1.5B-Instruct-GGUF \
  qwen2.5-1.5b-instruct-q4_k_m.gguf \
  --local-dir models/qwen-1.5b-q4

3. Start the core stack (small model, medium model, gateway, backend,
   frontend, Langfuse):
   ```bash
   docker compose up -d --build
   ```
4. Check everything is healthy:
   ```bash
   docker compose ps
   bash scripts/health_check.sh
   ```
5. Set up Langfuse (one-time) — see **Configuring your .env file** below —
   then restart the serving containers so they pick up your keys.
6. When you reach the quantization task, also start the quantized service:
   ```bash
   docker compose --profile quantization up -d --build bentoml-quantized
   ```

## Configuring your `.env` file

Copy `.env.example` to `.env` before doing anything else — everything below
assumes you've done that. Most values already have sensible local defaults
and don't need to change. The values below **do** need action on your part:

| Variable | What it's for | Where to get the value | What to do after setting it |
|---|---|---|---|
| `SMALL_MODEL_PATH`, `MEDIUM_MODEL_PATH`, `QUANTIZED_MODEL_PATH` | Container-internal path to each GGUF file | These are pre-provisioned for you — confirm the filenames under `models/*/` match these paths exactly | Just make sure the file exists at that path before `docker compose up` |
| `LANGFUSE_PUBLIC_KEY` | Lets the serving containers authenticate to your local Langfuse | **Generated by you**, see step-by-step below | Restart the serving containers (command below) |
| `LANGFUSE_SECRET_KEY` | Same as above (secret half of the key pair) | **Generated by you**, see step-by-step below | Restart the serving containers (command below) |

### Step-by-step: getting your Langfuse keys

1. Start the stack once, without keys, so Langfuse itself comes up:
   ```bash
   docker compose up -d --build
   ```
2. Open the Langfuse UI in your browser at **http://localhost:3030**
   (this is fixed — do not use port 3000).
3. Click **Sign up** and create a local account. This account only exists
   in your local `langfuse-db` Postgres container — nothing leaves your
   machine.
4. Create a new **Project** (any name, e.g. `manufacturing-llmops`).
5. Inside the project, go to **Settings → API Keys**.
6. Click **Create new API key**. Langfuse will show you a **Public Key**
   (starts with `pk-lf-...`) and a **Secret Key** (starts with `sk-lf-...`).
   Copy both immediately — the secret key is only shown once.
7. Open your `.env` file and replace the placeholder values:
   ```
   LANGFUSE_PUBLIC_KEY=pk-lf-...   # paste your public key
   LANGFUSE_SECRET_KEY=sk-lf-...   # paste your secret key
   ```
8. Save `.env`, then restart the serving containers so they pick up the
   new keys:
   ```bash
   docker compose up -d --force-recreate bentoml-small bentoml-medium
   ```
   (also `bentoml-quantized` if you've already started it with the
   `quantization` profile)
9. Send any test request (e.g. `bash scripts/test_models.sh`, or a message
   through the chatbot UI) and confirm a new trace appears under
   **Traces** in the Langfuse UI within a few seconds.

If you skip this setup, the platform still runs end-to-end — requests just
won't show up in Langfuse (they're logged to each container's stdout
instead, see `serving/common/tracing.py`), so you can come back to this
step at any time.

## Verification

| Requirement          | How to verify                                   |
|------------------------|--------------------------------------------------|
| LLM Serving            | `bash scripts/test_models.sh`                    |
| LiteLLM Gateway/Routing| `bash scripts/test_routing.sh`                   |
| Langfuse Monitoring     | `bash scripts/test_monitoring.sh` + Langfuse UI at `http://localhost:3030` |
| Quantized Model         | `bash scripts/test_quantization.sh`               |
| Token Cost              | `bash scripts/test_cost.sh`                       |
| Optimization             | `python3 scripts/load_test.py`                     |
| Chatbot UI                | See **UI Validation** below                          |
| Everything at once        | `bash scripts/run_all_tests.sh`                     |

## UI Validation

Once the stack is up and healthy, validate the whole platform end-to-end
through the chatbot UI:

a. Start the application:
   ```bash
   docker compose up -d --build
   ```
b. Open the chatbot frontend in your browser at **http://localhost:8081**
   (or your `FRONTEND_PORT` value, if you changed it).
c. Enter a simple prompt, for example:
   > What does high motor temperature indicate?
d. Verify you get a response, and that the info chip under the response
   shows `model: small-model` (simple prompts route to the small model —
   this only works once Task 3 - Model Routing is complete).
e. Enter a complex prompt, for example:
   > Analyze this machine failure description and identify the likely
   > root cause, corrective action, and recommended maintenance steps.
f. Verify the info chip now shows `model: medium-model`.
g. Open Langfuse at **http://localhost:3030**.
h. Find the corresponding trace(s) under **Traces** (most recent at the
   top; match by timestamp or by the prompt text).
i. Verify the trace shows: prompt, response, model, input tokens, output
   tokens, total tokens, latency, and (once you've completed Task 6) the
   estimated cost/usage.
j. Start the quantized service and test it too:
   ```bash
   docker compose --profile quantization up -d --build bentoml-quantized
   ```
   then send a request with `"model_override": "quantized-model"` (via
   `scripts/test_quantization.sh`, since the chatbot UI itself only
   exposes simple/complex routing) and compare against the medium model
   in `results/quantization_notes.md`. Also run
   `python3 scripts/load_test.py` to see the before/after optimization
   comparison.
k. Run the full suite as a final check:
   ```bash
   bash scripts/run_all_tests.sh
   ```

## Ports

| Service            | Container port | Host port (default) | Env variable            |
|----------------------|-------------------|-------------------------|----------------------------|
| frontend                | 80                | 8001                     | `FRONTEND_PORT`               |
| backend                  | 8080              | 8002                     | `BACKEND_PORT`                  |
| bentoml-small          | 3000              | 3001                     | `SMALL_SERVICE_PORT`         |
| bentoml-medium          | 3000              | 3002                     | `MEDIUM_SERVICE_PORT`         |
| bentoml-quantized        | 3000              | 3003                     | `QUANTIZED_SERVICE_PORT`       |
| litellm-gateway            | 4000              | 4000                     | `LITELLM_PORT`                   |
| langfuse                      | 3000 (internal only) | **3030**              | `LANGFUSE_PORT`                     |
| langfuse-db (Postgres)          | 5432              | 5433                     | `LANGFUSE_DB_PORT`                     |

Langfuse is always reached at **http://localhost:3030** from your browser.
Port 3000 is never used for any host-exposed service in this stack.

## Troubleshooting

- **Container not starting** — run `docker compose logs <service>` to see
  the error; most often it's a missing model file (see next point).
- **Model file not found** — confirm the GGUF file is in the right
  `models/<name>/` folder and the filename matches `config/models.yaml` /
  your `.env`.
- **Port already in use** — another process is using that host port;
  change the relevant `*_PORT` variable in `.env` and re-run
  `docker compose up -d`.
- **Permission denied on scripts** — run `chmod +x scripts/*.sh`.
- **LiteLLM cannot reach BentoML** — confirm both containers are on the
  `llmops-net` network (`docker network inspect`) and that
  `gateway/litellm_config.yaml` uses the service names
  (`bentoml-small`, `bentoml-medium`, `bentoml-quantized`), not `localhost`.
- **Frontend shows "Backend unreachable"** — confirm the `backend`
  container is healthy (`docker compose ps`), and that `BACKEND_PORT` in
  `.env` matches what the frontend was built with (rebuild the frontend
  after changing it: `docker compose up -d --build frontend`).
- **Chat request fails from the UI** — this almost always means the
  backend can't reach LiteLLM, or LiteLLM can't reach a BentoML service.
  Check `docker compose logs backend` and `docker compose logs
  litellm-gateway`.
- **Langfuse trace not appearing** — confirm `LANGFUSE_PUBLIC_KEY` /
  `LANGFUSE_SECRET_KEY` are set in `.env` and the serving containers were
  restarted after setting them (see **Configuring your .env file** above).
- **Model loading too slowly** — the first request after container start
  pays the model-load cost; subsequent requests are fast. Watch
  `docker compose logs -f bentoml-small` while it loads.
- **Out-of-memory issue** — don't run all three model services at once on a
  small VM; stop `bentoml-quantized` when you're done with the
  quantization task (`docker compose stop bentoml-quantized`), and lower
  `LLAMA_CTX_SIZE` / `LLAMA_THREADS_*` in `.env` if needed.

No cloud services are used anywhere in this lab — everything above runs on
your local Docker host.
