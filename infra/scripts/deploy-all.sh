#!/usr/bin/env bash
# Despliega la infraestructura del proyecto en el entorno indicado.
#
# Uso: ./infra/scripts/deploy-all.sh <dev|prod>
#
# Cada plantilla se despliega suelta, con parámetros inline
# (infra/parameters/README.md: los stacks sueltos no usan file://). Los
# valores comunes se leen del fichero de parámetros del entorno para no
# duplicarlos a mano en la línea de comandos.

#
# auth.yaml, api.yaml, catalogo.yaml y notificaciones.yaml no están aquí: sus
# Lambdas necesitan un zip real en S3 (CodigoS3Bucket/CodigoS3Key), que
# produce y sube infra/scripts/build-lambdas.sh <entorno> (necesita que este
# script haya creado ya el bucket de artefactos). fotos.yaml tampoco: su
# Lambda de thumbnails necesita una imagen ya subida al repositorio ECR que
# sí crea este script (en artefactos.yaml), vía
# infra/scripts/build-thumbnails-image.sh <entorno>.
set -euo pipefail

ENTORNO="${1:-}"
if [ "$ENTORNO" != "dev" ] && [ "$ENTORNO" != "prod" ]; then
  echo "Uso: $0 <dev|prod>" >&2
  exit 1
fi

DIR_RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FICHERO_PARAMS="$DIR_RAIZ/infra/parameters/$ENTORNO.json"

valor_parametro() {
  python -c "
import json, sys
with open(sys.argv[1]) as f:
    params = json.load(f)
for p in params:
    if p['ParameterKey'] == sys.argv[2]:
        print(p['ParameterValue'])
        break
" "$FICHERO_PARAMS" "$1"
}

ruta_windows() {
  cygpath -w "$1" | tr '\\' '/'
}

PROYECTO="$(valor_parametro Proyecto)"

desplegar_artefactos() {
  echo "Desplegando artefactos.yaml en $ENTORNO..."
  aws cloudformation deploy \
    --region us-east-1 \
    --stack-name "${PROYECTO}-${ENTORNO}-artefactos" \
    --template-file "$(ruta_windows "$DIR_RAIZ/infra/templates/artefactos.yaml")" \
    --parameter-overrides \
      Proyecto="$PROYECTO" \
      Entorno="$ENTORNO"
}

desplegar_budgets() {
  local email_alertas presupuesto
  email_alertas="$(valor_parametro EmailAlertas)"
  presupuesto="$(valor_parametro PresupuestoMensualUSD)"

  echo "Desplegando budgets.yaml en $ENTORNO (presupuesto $presupuesto USD/mes, alertas a $email_alertas)..."
  aws cloudformation deploy \
    --region us-east-1 \
    --stack-name "${PROYECTO}-${ENTORNO}-budgets" \
    --template-file "$(ruta_windows "$DIR_RAIZ/infra/templates/budgets.yaml")" \
    --parameter-overrides \
      Proyecto="$PROYECTO" \
      Entorno="$ENTORNO" \
      EmailAlertas="$email_alertas" \
      PresupuestoMensualUSD="$presupuesto"
}

desplegar_dynamodb() {
  echo "Desplegando dynamodb.yaml en $ENTORNO..."
  aws cloudformation deploy \
    --region us-east-1 \
    --stack-name "${PROYECTO}-${ENTORNO}-dynamodb" \
    --template-file "$(ruta_windows "$DIR_RAIZ/infra/templates/dynamodb.yaml")" \
    --parameter-overrides \
      Proyecto="$PROYECTO" \
      Entorno="$ENTORNO"
}

desplegar_budgets
desplegar_dynamodb
desplegar_artefactos
