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
  --region eu-west-1 \
  --stack-name "${PROYECTO}-${ENTORNO}-auth" \
  --template-file "$(ruta_windows "$DIR_RAIZ/infra/templates/auth.yaml")" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    Proyecto="$PROYECTO" \
    Entorno="$ENTORNO" \
    CodigoS3Bucket="$BUCKET" \
    CodigoS3KeyPostConfirmation="lambdas/post-confirmation.zip"

echo "Desplegando api.yaml en $ENTORNO..."
aws cloudformation deploy \
  --region eu-west-1 \
  --stack-name "${PROYECTO}-${ENTORNO}-api" \
  --template-file "$(ruta_windows "$DIR_RAIZ/infra/templates/api.yaml")" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    Proyecto="$PROYECTO" \
    Entorno="$ENTORNO" \
    CodigoS3Bucket="$BUCKET" \
    CodigoS3KeyApi="lambdas/api.zip"

echo "Forzando actualización de código (CloudFormation no lo hace si el S3Key no cambia)..."
aws lambda update-function-code \
  --function-name "${PROYECTO}-${ENTORNO}-post-confirmation" \
  --s3-bucket "$BUCKET" --s3-key "lambdas/post-confirmation.zip" \
  --region eu-west-1 --query "LastUpdateStatus" --output text
for FN in lectura-publica escritura-publica cliente guarderia admin decision; do
  aws lambda update-function-code \
    --function-name "${PROYECTO}-${ENTORNO}-${FN}" \
    --s3-bucket "$BUCKET" --s3-key "lambdas/api.zip" \
    --region eu-west-1 --query "LastUpdateStatus" --output text
done

echo "Endpoint de la API:"
aws cloudformation describe-stacks \
  --region eu-west-1 \
  --stack-name "${PROYECTO}-${ENTORNO}-api" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
  --output text
