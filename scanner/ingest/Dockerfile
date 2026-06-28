FROM python:3.12-slim

WORKDIR /app

# Service-specific deps only — no parser libs needed by ingest
COPY ingest/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Shared source code (models, adapters, handlers)
COPY src/ ./src/
COPY __init__.py .

# Default CMD — overridden by CDK DockerImageCode.fromEcr(entrypoint + cmd)
CMD ["python", "-m", "awslambdaric", "src.handlers.ingest_handler.handler"]
