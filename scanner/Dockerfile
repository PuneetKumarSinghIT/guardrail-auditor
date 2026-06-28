# Debian slim — lighter, better apt package compatibility than Amazon Linux.
# awslambdaric (Lambda Runtime Interface Client) makes this image Lambda-compatible
# without needing the opinionated AWS base image.
#
# HOW THIS IMAGE IS USED:
#
#   Lambda (ingest-handler, aggregator):
#     CDK DockerImageCode sets:
#       entrypoint: ["/usr/local/bin/python", "-m", "awslambdaric"]
#       cmd:        ["src.handlers.ingest_handler.handler"]
#     awslambdaric imports the module and calls handler(event, context).
#     No Mangum — plain def handler(event, context) is native Lambda format.
#
#   ECS Fargate task (rules-engine):
#     CDK container definition sets:
#       entryPoint: ["python", "-m", "src.main"]
#     src/main.py reads MODE=rules_engine and dispatches to rules_engine.main().

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY __init__.py .

# Default CMD — never executed directly in AWS.
# Lambda overrides via imageConfig entrypoint+cmd in CDK.
# ECS overrides via container entryPoint in CDK.
CMD ["python", "-m", "src.main"]
