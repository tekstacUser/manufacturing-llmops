# Monitoring — Langfuse OSS (SK-JF5-05)

Langfuse runs entirely locally via `docker-compose.yml` (services `langfuse`
and `langfuse-db`). No cloud Langfuse account is used or required.

## What gets traced

Every call to `/generate` or `/v1/chat/completions` on any of the three
BentoML services (`serving/common/tracing.py`) logs one Langfuse **trace**
containing a **generation** with:

- `model` — which alias served the request (small-model / medium-model / quantized-model)
- `input` — the prompt
- `output` — the model's response
- `usage.input`, `usage.output`, `usage.total` — token counts
- `latency_ms` — wall-clock inference latency
- `success` / `error` — whether the call succeeded

## First-time local setup

1. Start the stack: `docker compose up -d`
2. Open the Langfuse UI at `http://localhost:${LANGFUSE_PORT}` (default `3030`)
3. Create a local account (stored only in the local `langfuse-db` Postgres container)
4. Create a project, then go to **Settings → API Keys** and generate a
   public/secret key pair
5. Put those values into your `.env` file:
   ```
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   ```
6. Restart the serving containers so they pick up the new keys:
   ```
   docker compose up -d --force-recreate bentoml-small bentoml-medium bentoml-quantized
   ```
7. Send a test request (e.g. `scripts/test_models.sh`) and confirm a trace
   appears under **Traces** in the Langfuse UI within a few seconds.

If `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` are left blank, the services
still run — traces are simply logged to stdout instead
(see `serving/common/tracing.py`), so serving is never blocked by monitoring.
