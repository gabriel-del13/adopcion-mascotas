#!/usr/bin/env bash
# Valida la sintaxis de todas las plantillas de infra/templates/ contra la
# API de CloudFormation. No despliega nada.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../templates" && pwd)"
ESTADO=0

for plantilla in "$DIR"/*.yaml; do
  [ -e "$plantilla" ] || continue

  region="eu-west-1"
  if [ "$(basename "$plantilla")" = "edge-us-east-1.yaml" ]; then
    region="us-east-1"
  fi

  echo "Validando $(basename "$plantilla") (región $region)..."
  if ! aws cloudformation validate-template \
    --region "$region" \
    --template-body "$(cat "$plantilla")" >/dev/null; then
    echo "FALLÓ: $(basename "$plantilla")" >&2
    ESTADO=1
  fi
done

exit $ESTADO
