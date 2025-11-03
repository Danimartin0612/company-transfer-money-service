#!/usr/bin/env bash
set -euo pipefail

for i in {1..60}; do
  if curl -sf http://localhost:4566/_localstack/health | grep -q '"s3": *"running"'; then
    echo "LocalStack S3 está running."
    break
  fi
  echo "Esperando LocalStack S3... ($i/60)"
  sleep 2
done

if ! command -v aws >/dev/null 2>&1; then
  echo "Instalando AWS CLI v2 temporalmente..."
  curl -sSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip
  unzip -q /tmp/awscliv2.zip -d /tmp
  /tmp/aws/install -i /usr/local/aws-cli -b /usr/local/bin
fi

AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"
AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-eu-west-1}"
ENDPOINT_URL="${ENDPOINT_URL:-http://localhost:4566}"
S3_BUCKET="${S3_BUCKET:-pipeline-reports}"

# Crear el bucket
aws --endpoint-url "$ENDPOINT_URL" s3api head-bucket --bucket "$S3_BUCKET" 2>/dev/null || \
aws --endpoint-url "$ENDPOINT_URL" s3api create-bucket --bucket "$S3_BUCKET" \
  --create-bucket-configuration LocationConstraint="$AWS_DEFAULT_REGION"

echo "Bucket $S3_BUCKET listo en $ENDPOINT_URL"
