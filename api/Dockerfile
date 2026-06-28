FROM python:3.12-slim

WORKDIR /app

# Service deps — boto3 (DDB + S3 presign) + awslambdaric (Lambda RIC) +
# python-jose[cryptography] (Cognito JWT validation at the app layer).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Source code (app dispatcher, routes, middleware)
COPY src/ ./src/
COPY __init__.py .

# Default CMD — overridden by CDK DockerImageCode.fromEcr(entrypoint + cmd).
# entrypoint: ["/usr/local/bin/python", "-m", "awslambdaric"]
# cmd:        ["src.app.handler"]
CMD ["python", "-m", "awslambdaric", "src.app.handler"]
