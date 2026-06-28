FROM python:3.12-slim

WORKDIR /app

# Service deps — boto3 (S3 GetObject) + awslambdaric (Lambda RIC for slim base).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Source — single static-host handler. `src` is a PEP 420 namespace package.
COPY src/ ./src/

# Default CMD — overridden by CDK DockerImageCode.fromEcr(entrypoint + cmd).
# entrypoint: ["/usr/local/bin/python", "-m", "awslambdaric"]
# cmd:        ["src.handler.handler"]
CMD ["python", "-m", "awslambdaric", "src.handler.handler"]
