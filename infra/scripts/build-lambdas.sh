#!/usr/bin/env bash
# Empaqueta backend/api y los event_lambdas (post_confirmation,
# regenerador_catalogo, consumidora_sqs, thumbnails) en zips listos para
# Lambda, y los sube al bucket de artefactos del entorno.
#
# Uso: ./infra/scripts/build-lambdas.sh <dev|prod>
#
# Las cinco Lambdas de la API comparten este mismo zip (solo cambia el
# Handler en api.yaml). El zip se construye con las dependencias de Linux
# ARM64 aunque se empaquete desde Windows: pip normalmente instala los
# wheels de la máquina donde corre, así que hace falta pedir explícitamente
# la plataforma de destino (--platform/--only-binary), o el zip tendría
# binarios de Windows que Lambda no puede cargar.
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

PROYECTO="$(valor_parametro Proyecto)"
CUENTA="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${PROYECTO}-${ENTORNO}-artefactos-${CUENTA}"

BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "$BUILD_DIR"' EXIT

echo "Empaquetando backend/api..."
API_BUILD="$BUILD_DIR/api"
mkdir -p "$API_BUILD"
python -m pip install \
  --platform manylinux2014_aarch64 \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all: \
  --no-compile \
  --target "$API_BUILD" \
  -r "$DIR_RAIZ/backend/api/requirements.txt" \
  --quiet
cp -r "$DIR_RAIZ/backend/api/app" "$API_BUILD/app"
python "$DIR_RAIZ/infra/scripts/zip_dir.py" "$API_BUILD" "$BUILD_DIR/api.zip"

echo "Empaquetando backend/event_lambdas/post_confirmation (solo boto3, ya está en el runtime de Lambda)..."
PC_BUILD="$BUILD_DIR/post_confirmation"
mkdir -p "$PC_BUILD"
cp "$DIR_RAIZ/backend/event_lambdas/post_confirmation/handler.py" "$PC_BUILD/handler.py"
python "$DIR_RAIZ/infra/scripts/zip_dir.py" "$PC_BUILD" "$BUILD_DIR/post-confirmation.zip"

echo "Empaquetando backend/event_lambdas/regenerador_catalogo (solo boto3)..."
RC_BUILD="$BUILD_DIR/regenerador_catalogo"
mkdir -p "$RC_BUILD"
cp "$DIR_RAIZ/backend/event_lambdas/regenerador_catalogo/handler.py" "$RC_BUILD/handler.py"
python "$DIR_RAIZ/infra/scripts/zip_dir.py" "$RC_BUILD" "$BUILD_DIR/regenerador-catalogo.zip"

echo "Empaquetando backend/event_lambdas/consumidora_sqs (solo boto3)..."
CS_BUILD="$BUILD_DIR/consumidora_sqs"
mkdir -p "$CS_BUILD"
cp "$DIR_RAIZ/backend/event_lambdas/consumidora_sqs/handler.py" "$CS_BUILD/handler.py"
python "$DIR_RAIZ/infra/scripts/zip_dir.py" "$CS_BUILD" "$BUILD_DIR/consumidor-notificaciones.zip"

echo "Empaquetando backend/event_lambdas/thumbnails (Pillow, wheel precompilado ARM64)..."
TH_BUILD="$BUILD_DIR/thumbnails"
mkdir -p "$TH_BUILD"
python -m pip install \
  --platform manylinux2014_aarch64 \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all: \
  --no-compile \
  --target "$TH_BUILD" \
  -r "$DIR_RAIZ/backend/event_lambdas/thumbnails/requirements.txt" \
  --quiet
cp "$DIR_RAIZ/backend/event_lambdas/thumbnails/handler.py" "$TH_BUILD/handler.py"
python "$DIR_RAIZ/infra/scripts/zip_dir.py" "$TH_BUILD" "$BUILD_DIR/thumbnails.zip"

echo "Subiendo a s3://$BUCKET/lambdas/..."
aws s3 cp "$BUILD_DIR/api.zip" "s3://$BUCKET/lambdas/api.zip"
aws s3 cp "$BUILD_DIR/post-confirmation.zip" "s3://$BUCKET/lambdas/post-confirmation.zip"
aws s3 cp "$BUILD_DIR/regenerador-catalogo.zip" "s3://$BUCKET/lambdas/regenerador-catalogo.zip"
aws s3 cp "$BUILD_DIR/consumidor-notificaciones.zip" "s3://$BUCKET/lambdas/consumidor-notificaciones.zip"
aws s3 cp "$BUILD_DIR/thumbnails.zip" "s3://$BUCKET/lambdas/thumbnails.zip"

echo "Listo. CodigoS3Bucket=$BUCKET CodigoS3KeyApi=lambdas/api.zip CodigoS3KeyPostConfirmation=lambdas/post-confirmation.zip CodigoS3KeyRegenerador=lambdas/regenerador-catalogo.zip CodigoS3KeyConsumidora=lambdas/consumidor-notificaciones.zip CodigoS3KeyThumbnails=lambdas/thumbnails.zip"
