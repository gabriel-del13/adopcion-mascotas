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
IMAGEN="${CUENTA}.dkr.ecr.eu-west-1.amazonaws.com/${PROYECTO}-${ENTORNO}-thumbnails:${ENTORNO}-latest"

echo "Desplegando fotos.yaml en $ENTORNO..."
aws cloudformation deploy \
  --region eu-west-1 \
  --stack-name "${PROYECTO}-${ENTORNO}-fotos" \
  --template-file "$(ruta_windows "$DIR_RAIZ/infra/templates/fotos.yaml")" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    Proyecto="$PROYECTO" \
    Entorno="$ENTORNO" \
    ImagenThumbnails="$IMAGEN"

# CloudFormation no vuelve a desplegar la imagen si la cadena ImagenThumbnails
# no cambió, aunque la imagen en ECR sea distinta 
echo "Forzando actualización de código..."
aws lambda update-function-code \
  --function-name "${PROYECTO}-${ENTORNO}-thumbnails" \
  --image-uri "$IMAGEN" \
  --region eu-west-1 --query "LastUpdateStatus" --output text
