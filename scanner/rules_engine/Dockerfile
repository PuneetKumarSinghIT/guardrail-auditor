FROM python:3.12-slim

WORKDIR /app

# Service-specific deps — HCL/CFN parsers needed; no awslambdaric (ECS task, not Lambda)
COPY rules_engine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Shared source code (models, parsers, adapters, rules, handlers)
COPY src/ ./src/
COPY __init__.py .

# ECS task entry point — reads MODE env var (always rules_engine for this image)
CMD ["python", "-m", "src.main"]
