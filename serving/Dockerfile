# Shared Dockerfile for the small / medium / quantized BentoML services.
# The concrete service is selected at build time with --build-arg SERVICE_DIR=small|medium|quantized
# (see docker-compose.yml). CPU-only build - no CUDA toolchain.

FROM python:3.11-slim AS base

ARG SERVICE_DIR=small
ENV SERVICE_DIR=${SERVICE_DIR}
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Build tools required to compile llama-cpp-python's CPU backend.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
# CPU-only build of llama-cpp-python (no CUBLAS / GPU flags).
RUN CMAKE_ARGS="-DGGML_CUDA=off" pip install --no-cache-dir -r /app/requirements.txt

COPY common /app/common
COPY ${SERVICE_DIR} /app/service_src

WORKDIR /app/service_src

EXPOSE 3000

HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
    CMD curl -f -X POST -H "Content-Type: application/json" -d "{}" http://localhost:3000/healthz || exit 1

CMD ["bentoml", "serve", "service:svc", "--host", "0.0.0.0", "--port", "3000", "--production"]
