#!/usr/bin/env bash
# Despliega auth.yaml y luego api.yaml, apuntando al zip que dejó
# build-lambdas.sh en el bucket de artefactos.
#
# Requisitos previos, en orden: deploy-all.sh <entorno> (crea dynamodb y el
# bucket de artefactos), build-lambdas.sh <entorno> (sube los zips) y
# deploy-notificaciones.sh <entorno> (api.yaml importa su cola y su tema de
# alertas).
#
# Uso: ./infra/scripts/deploy-auth-api.sh <dev|prod>
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

echo "Desplegando auth.yaml en $ENTORNO..."
aws cloudformation deploy \
  --region us-east-1 \
  --stack-name "${PROYECTO}-${ENTORNO}-auth" \
  --template-file "$(ruta_windows "$DIR_RAIZ/infra/templates/auth.yaml")" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    Proyecto="$PROYECTO" \
    Entorno="$ENTORNO" \
    CodigoS3Bucket="$BUCKET" \
    CodigoS3KeyPostConfirmation="lambdas/post-confirmation.zip"

echo "Desplegando api.yaml en $ENTORNO..."
# --s3-bucketssolo aquí, no en los demás deploy-*.sh: el árbol de
# recursos REST API hace que esta plantilla supere los 51200 bytes que CloudFormation
# admite como TemplateBody en líneas
aws cloudformation deploy \
  --region us-east-1 \
  --stack-name "${PROYECTO}-${ENTORNO}-api" \
  --template-file "$(ruta_windows "$DIR_RAIZ/infra/templates/api.yaml")" \
  --s3-bucket "$BUCKET" \
  --s3-prefix "plantillas" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    Proyecto="$PROYECTO" \
    Entorno="$ENTORNO" \
    CodigoS3Bucket="$BUCKET" \
    CodigoS3KeyApi="lambdas/api.zip"

echo "Publicando los cambios de rutas en el stage $ENTORNO..."
REST_API_ID="$(aws cloudformation describe-stacks \
  --region us-east-1 --stack-name "${PROYECTO}-${ENTORNO}-api" \
  --query "Stacks[0].Outputs[?OutputKey=='RestApiId'].OutputValue" --output text)"
aws apigateway create-deployment \
  --rest-api-id "$REST_API_ID" \
  --stage-name "$ENTORNO" \
  --region us-east-1 \
  --description "Deploy $(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --query "id" --output text

# CloudFormation no vuelve a subir el código si el S3Key no cambió, aunque el
# objeto en S3 sea distinto: solo compara la cadena "S3Bucket/S3Key" contra el
# estado anterior, no el contenido. Como estos scripts siempre usan la misma
# key fija, hay que forzar la actualización de código a mano tras cada deploy.
echo "Forzando actualización de código (CloudFormation no lo hace si el S3Key no cambia)..."
aws lambda update-function-code \
  --function-name "${PROYECTO}-${ENTORNO}-post-confirmation" \
  --s3-bucket "$BUCKET" --s3-key "lambdas/post-confirmation.zip" \
  --region us-east-1 --query "LastUpdateStatus" --output text
for FN in lectura-publica escritura-publica cliente guarderia admin decision; do
  aws lambda update-function-code \
    --function-name "${PROYECTO}-${ENTORNO}-${FN}" \
    --s3-bucket "$BUCKET" --s3-key "lambdas/api.zip" \
    --region us-east-1 --query "LastUpdateStatus" --output text
done

echo "Endpoint de la API:"
aws cloudformation describe-stacks \
  --region us-east-1 \
  --stack-name "${PROYECTO}-${ENTORNO}-api" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
  --output text
