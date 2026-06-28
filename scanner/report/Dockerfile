FROM python:3.12-slim

WORKDIR /app

# Service-specific deps — reportlab (PDF) + boto3 + Lambda RIC. Shared by the
# report-handler, email-handler, and failure-handler Lambdas (one image, three
# handler entrypoints selected per-Lambda via CDK DockerImageCode cmd).
COPY report/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Shared source code (models, services, report_generator, handlers)
COPY src/ ./src/
COPY __init__.py .

# Default CMD — overridden by CDK DockerImageCode.fromEcr(entrypoint + cmd)
CMD ["python", "-m", "awslambdaric", "src.handlers.report_handler.handler"]
