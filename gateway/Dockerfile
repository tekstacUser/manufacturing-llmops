# LiteLLM Gateway container (SK-JF5-04)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "litellm[proxy]==1.44.24"

WORKDIR /app
COPY litellm_config.yaml /app/litellm_config.yaml

EXPOSE 4000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -f http://localhost:4000/health/liveliness || exit 1

CMD ["litellm", "--config", "/app/litellm_config.yaml", "--host", "0.0.0.0", "--port", "4000"]
