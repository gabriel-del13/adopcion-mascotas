# Requisitos:
Cuenta de AWS, AWS CLI v2, WSL2 instalado (si tienes windows)

# Configurando aws cli
aws configure --profile adopcion-mascotas   # region: eu-west-1
export AWS_PROFILE=adopcion-mascotas
# Editar infra/parameters/dev.json: EmailAlertas y EmailRemitenteSes con tu email
CORREO@gmail.com
# Despliegue, en este orden exacto
./infra/scripts/validate-templates.sh
./infra/scripts/deploy-all.sh dev              # budgets, dynamodb, artefactos
./infra/scripts/build-lambdas.sh dev           # empaqueta api, post-confirmation, regenerador-catalogo, thumbnails
./infra/scripts/deploy-notificaciones.sh dev   # SQS+DLQ, SES, consumidora
./infra/scripts/deploy-fotos.sh dev            # buckets de fotos
./infra/scripts/deploy-auth-api.sh dev         # auth + api
./infra/scripts/deploy-catalogo.sh dev         # catálogo precalculado

# Primer ADMIN, a mano
aws cognito-idp admin-create-user --user-pool-id <su-pool-id> --username <su-email> ...
aws cognito-idp admin-add-user-to-group --user-pool-id <su-pool-id> --username <su-email> --group-name ADMIN

# Output
URL de API
ID de Cognito
Para ver los endpoints, te deje el json 