# syntax=docker/dockerfile:1
# Build context: repository root  ->  docker build -f backend/Dockerfile .

# ---------- Stage 1: build dependencies into a virtualenv ----------
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

# ---------- Stage 2: slim runtime image ----------
FROM python:3.12-slim AS runtime
ARG GIT_SHA=dev
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GIT_SHA=${GIT_SHA} \
    APP_ENV=prod \
    LOG_JSON=true \
    DATA_DIR=/app/sample_data \
    KNOWLEDGE_DIR=/app/knowledge \
    CACHE_DIR=/tmp/datasets

# Run as an unprivileged user (security best practice; required by many K8s policies).
RUN groupadd --system app && useradd --system --gid app --home /app app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app backend/app ./app
COPY --chown=app:app sample_data ./sample_data
COPY --chown=app:app knowledge ./knowledge
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/healthz').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
