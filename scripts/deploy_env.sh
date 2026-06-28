#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Intelligent, dependency-ordered environment bootstrap for the Guardrail Auditor.
#
# WHY THIS EXISTS — the ECR bootstrap deadlock:
#   lambda.DockerImageFunction.fromEcr needs its image to exist at CreateFunction
#   time, but the scanner stack also CREATES the ECR repos. A naive
#   `cdk deploy --all` therefore FAILS on a fresh environment (the first
#   staging/prod promotion would fail). This script sequences it correctly so a
#   clean environment comes up reliably every time:
#
#     1. cdk deploy --all (computeEnabled=false) -> repos + ECS + all infra, NO Lambdas
#     2. build + push all 4 images to THIS env's repos
#          Lambda images (ingest, aggregator): buildx docker-container driver,
#            --provenance=false, oci-mediatypes=false  (Docker 29 default OCI
#            index w/ provenance is rejected by Lambda)
#          ECS images (rules-engine, checkov): same path — uniform + reliable
#     3. cdk deploy --all (computeEnabled=true)  -> add the Lambdas, images now present
#     4. seed rules-catalog-{env} from rules/rules-catalog.json (else custom rules
#        never fire — only Checkov would)
#
# Idempotent — safe to re-run. This is the canonical path for BOTH initial dev
# setup AND dev->staging->prod promotion. Teardown is the inverse:
#   AWS_PROFILE=... npx cdk destroy --all --context env=<env> --force
#   (then delete any pre-CDK orphan ECR repos; KMS key auto-deletes after 7 days)
#
# AUTH: uses ambient AWS credentials.
#   Local:  AWS_PROFILE=aws-admin scripts/deploy_env.sh dev
#   CI:     OIDC role already assumed — no profile needed.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

ENV="${1:-${DEPLOY_ENV:-dev}}"
REGION="${AWS_REGION:-us-east-1}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
ECR="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"

echo "==> Bootstrapping env=${ENV} account=${ACCOUNT} region=${REGION}"

# ── Step 1: infra + ECR repos, but NOT the 2 Lambdas ─────────────────────────
echo "==> [1/4] cdk deploy --all (computeEnabled=false) — repos + ECS, no Lambdas"
( cd infrastructure && npx cdk deploy --all \
    --context env="${ENV}" --context computeEnabled=false --require-approval never )

# ── Step 2: build + push all 4 images to this env's repos ────────────────────
echo "==> [2/4] build + push 4 images"
aws ecr get-login-password --region "${REGION}" | docker login --username AWS --password-stdin "${ECR}"
docker buildx inspect lambdabuilder >/dev/null 2>&1 || docker buildx create --name lambdabuilder --driver docker-container
docker buildx use lambdabuilder

build_push() {  # $1=service  $2=dockerfile (rel)  $3=context (rel)
  local name="${ECR}/guardrail-$1-${ENV}:${ENV}-latest"
  echo "    -> ${name}"
  # oci-mediatypes=false + provenance=false => Docker v2s2 manifest Lambda accepts.
  # ECS accepts this too, so all four images use one uniform, reliable path.
  docker buildx build --provenance=false --sbom=false \
    --output "type=image,name=${name},oci-mediatypes=false,push=true" \
    -f "$2" "$3"
}

build_push ingest       "scanner/ingest/Dockerfile"       "scanner"
build_push aggregator   "scanner/aggregator/Dockerfile"   "scanner"
build_push rules-engine "scanner/rules_engine/Dockerfile" "scanner"
build_push checkov      "fargate/Dockerfile"              "fargate"
build_push ai-engine    "ai-engine/Dockerfile"            "ai-engine"

# ── Step 3: add the Lambdas (images now exist) ───────────────────────────────
echo "==> [3/4] cdk deploy --all (computeEnabled=true) — add Lambdas"
( cd infrastructure && npx cdk deploy --all \
    --context env="${ENV}" --require-approval never )

# ── Step 4: seed the rules catalog ───────────────────────────────────────────
echo "==> [4/4] seed rules-catalog-${ENV}"
python scripts/seed_rules_catalog.py --env "${ENV}" --region "${REGION}"

echo "==> DONE. env=${ENV} is fully provisioned, imaged, and seeded."
