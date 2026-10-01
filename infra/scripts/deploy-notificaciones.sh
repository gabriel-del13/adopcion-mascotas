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

echo "Desplegando notificaciones.yaml en $ENTORNO..."
aws cloudformation deploy \
  --region eu-west-1 \
  --stack-name "${PROYECTO}-${ENTORNO}-notificaciones" \
  --template-file "$(ruta_windows "$DIR_RAIZ/infra/templates/notificaciones.yaml")" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    Proyecto="$PROYECTO" \
    Entorno="$ENTORNO" \
    CodigoS3Bucket="$BUCKET" \
    CodigoS3KeyConsumidora="lambdas/consumidor-notificaciones.zip" \
    EmailAlertas="$(valor_parametro EmailAlertas)" \
    EmailRemitenteSes="$(valor_parametro EmailRemitenteSes)"

aws lambda update-function-code \
  --function-name "${PROYECTO}-${ENTORNO}-consumidora-notificaciones" \
  --s3-bucket "$BUCKET" --s3-key "lambdas/consumidor-notificaciones.zip" \
  --region eu-west-1 --query "LastUpdateStatus" --output text

echo "IMPORTANTE: revisa la bandeja de $(valor_parametro EmailRemitenteSes) y confirma el correo de verificación de SES antes de enviar de verdad."
