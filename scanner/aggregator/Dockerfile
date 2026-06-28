FROM python:3.12-slim

WORKDIR /app

# Service-specific deps — dedup + DDB write + EventBridge; no parser libs needed
COPY aggregator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Shared source code (models, adapters, handlers)
COPY src/ ./src/
COPY __init__.py .

# Default CMD — overridden by CDK DockerImageCode.fromEcr(entrypoint + cmd)
CMD ["python", "-m", "awslambdaric", "src.handlers.aggregator.handler"]
