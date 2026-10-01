#!/usr/bin/env bash
# Despliega catalogo.yaml (bucket + Lambda regeneradora + Streams), apuntando
# al zip que dejó build-lambdas.sh en el bucket de artefactos.
#
# Requisitos previos, en orden: deploy-all.sh <entorno> (crea dynamodb, cuyo
# stream ARN se importa aquí) y build-lambdas.sh <entorno> (sube el zip).
#
# Uso: ./infra/scripts/deploy-catalogo.sh <dev|prod>
set -euo pipefail

ENTORNO="${1:-}"
if [ "$ENTORNO" != "dev" ] && [ "$ENTORNO" != "prod" ]; then
  echo "Uso: $0 <dev|prod>" >&2
  exit 1
fi

DIR_RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

valor_parametro() {
  python -c "
import json, sys
with open(sys.argv[1]) as f:
    params = json.load(f)
for p in params:
    if p['ParameterKey'] == sys.argv[2]:
        print(p['ParameterValue'])
        break
" "$DIR_RAIZ/infra/parameters/$ENTORNO.json" "$1"
}

ruta_windows() {
  cygpath -w "$1" | tr '\\' '/'
}

PROYECTO="$(valor_parametro Proyecto)"
CUENTA="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${PROYECTO}-${ENTORNO}-artefactos-${CUENTA}"

echo "Desplegando catalogo.yaml en $ENTORNO..."
aws cloudformation deploy \
  --region eu-west-1 \
  --stack-name "${PROYECTO}-${ENTORNO}-catalogo" \
  --template-file "$(ruta_windows "$DIR_RAIZ/infra/templates/catalogo.yaml")" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    Proyecto="$PROYECTO" \
    Entorno="$ENTORNO" \
    CodigoS3Bucket="$BUCKET" \
    CodigoS3KeyRegenerador="lambdas/regenerador-catalogo.zip"

# CloudFormation no vuelve a subir el código si el S3Key no cambió, aunque el
# objeto en S3 sea distinto (compara la cadena, no el contenido). Como el key
# es siempre el mismo, hay que forzar la actualización a mano.
echo "Forzando actualización de código..."
aws lambda update-function-code \
  --function-name "${PROYECTO}-${ENTORNO}-regenerador-catalogo" \
  --s3-bucket "$BUCKET" --s3-key "lambdas/regenerador-catalogo.zip" \
  --region eu-west-1 --query "LastUpdateStatus" --output text
