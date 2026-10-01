#!/usr/bin/env bash
# Construye la imagen de la Lambda de thumbnails (Pillow) y la sube al
# repositorio ECR de artefactos.yaml. No usa build-lambdas.sh: esta Lambda va
# como imagen de contenedor, no como zip 
#
# Requisito previo: deploy-all.sh <entorno> (crea el repositorio ECR en
# artefactos.yaml). Ejecutar esto ANTES de deploy-fotos.sh: fotos.yaml
# necesita la imagen ya subida para poder crear la Lambda (PackageType Image
# exige que la imagen exista en el momento de crear la función).
#
# Requiere Docker con soporte multiplataforma (buildx). En Windows/AMD64,
# construir para ARM64 necesita emulación QEMU — este script la registra si
# hace falta (comando idempotente, no rompe nada si ya estaba).
#
# Uso: ./infra/scripts/build-thumbnails-image.sh <dev|prod>
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
REGISTRO="${CUENTA}.dkr.ecr.eu-west-1.amazonaws.com"
URI_REPO="${REGISTRO}/${PROYECTO}-${ENTORNO}-thumbnails"
TAG="${ENTORNO}-latest"

echo "Registrando emulación QEMU para ARM64 (no-op si ya estaba)..."
docker run --privileged --rm tonistiigi/binfmt --install arm64 >/dev/null

echo "Iniciando sesión en ECR..."
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin "$REGISTRO"

echo "Construyendo la imagen (linux/arm64) desde backend/event_lambdas/thumbnails..."
docker buildx build \
  --platform linux/arm64 \
  --provenance=false \
  -t "${URI_REPO}:${TAG}" \
  --load \
  "$DIR_RAIZ/backend/event_lambdas/thumbnails"

echo "Subiendo ${URI_REPO}:${TAG}..."
docker push "${URI_REPO}:${TAG}"

echo "Listo. ImagenThumbnails=${URI_REPO}:${TAG}"
