FROM python:3.12-slim

WORKDIR /app

# Service deps — boto3 (Bedrock + DDB + EventBridge) + awslambdaric (Lambda RIC)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Source code (analyzer, bedrock_client, prompt templates)
COPY src/ ./src/
COPY __init__.py .

# Default CMD — overridden by CDK DockerImageCode.fromEcr(entrypoint + cmd).
# entrypoint: ["/usr/local/bin/python", "-m", "awslambdaric"]
# cmd:        ["src.analyzer.handler"]
CMD ["python", "-m", "awslambdaric", "src.analyzer.handler"]
