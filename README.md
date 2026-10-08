# adopcion-mascotas

Plataforma que conecta protectoras y guarderías de animales con personas
interesadas en adoptar.

**Región principal:** `eu-west-1` (Irlanda).
**Excepción obligatoria:** el certificado de ACM y el Web ACL de WAF para
CloudFront viven en `us-east-1` - pendiente, ver "Estado actual".

---

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/Guia_de_Arranque_Tecnico.md`](docs/Guia_de_Arranque_Tecnico.md) | Punto de entrada: qué es, cómo está construido, dónde seguir leyendo |
| `docs/Despliegue_Backend.md` | Comandos resumidos para desplegar el backend en una cuenta propia |
| `docs/Backend_Endpoints.md` | Contrato de la API para quien construye el frontend (rutas, auth, contrato de fotos) TEMPORAL |
| `docs/postman_collection.json` | Ejemplos de request/response contra la API real |

---

## Estructura

```
infra/templates/   8 plantillas de CloudFormation (una por stack, ver abajo)
infra/parameters/  parámetros por entorno (dev.json, prod.json)
infra/scripts/     validación, empaquetado y despliegue
backend/api/        6 funciones Lambda, un rol IAM por función
backend/event_lambdas/  funciones disparadas por evento:
  post_confirmation/     trigger de Cognito al confirmar registro
  regenerador_catalogo/  DynamoDB Streams > catálogo JSON en S3
  consumidora_sqs/       cola de notificaciones > SES
  thumbnails/            Pillow paar las fotos
frontend/           prototipo estático (HTML + JS vanilla)
buildspecs/         reservado para CodeBuild (CI/CD), vacío por ahora
docs/               documentación de arquitectura (pública, en git)
```

---

## Las 8 plantillas y su orden de dependencia

```
budgets.yaml        (sin dependencias)
dynamodb.yaml        (sin dependencias)
artefactos.yaml       (sin dependencias)
auth.yaml            (importa dynamodb.yaml)
notificaciones.yaml   (importa dynamodb.yaml)
fotos.yaml            (importa dynamodb.yaml)
api.yaml              (importa dynamodb.yaml, auth.yaml, notificaciones.yaml, fotos.yaml)
catalogo.yaml         (importa dynamodb.yaml)
```

No hay `main.yaml`: son stacks sueltos conectados por `Fn::ImportValue`, a propósito 

---

## Entornos

Un único juego de plantillas para `dev` y `prod`, parametrizado por `Entorno`
(`infra/parameters/{dev,prod}.json`).

---

## Despliegue rápido

Requisitos: AWS CLI **v2**

```bash
aws configure --profile adopcion-mascotas   # region eu-west-1
export AWS_PROFILE=adopcion-mascotas

./infra/scripts/validate-templates.sh
./infra/scripts/deploy-all.sh dev              # budgets, dynamodb, artefactos
./infra/scripts/build-lambdas.sh dev           # empaqueta api, post-confirmation regenerador-catalogo, thumbnails
./infra/scripts/deploy-notificaciones.sh dev   # SQS+DLQ, SES, consumidora
./infra/scripts/deploy-fotos.sh dev            # buckets de fotos
./infra/scripts/deploy-auth-api.sh dev         # auth + api
./infra/scripts/deploy-catalogo.sh dev         # catálogo precalculado
```

`UserPool` (stack `auth`) y las dos tablas DynamoDB (stack `dynamodb`) llevan
`DeletionPolicy: Retain` y sobreviven al borrado del stack - hay que
limpiarlos a mano si se quiere empezar de cero.

---

## Convención de nombres

`adopcion-mascotas-{entorno}-{recurso}`

- Stacks - `adopcion-mascotas-dev-api`
- Tablas - `adopcion-mascotas-dev-catalogo`, `adopcion-mascotas-dev-solicitudes`
- Buckets - `adopcion-mascotas-dev-fotos-derivadas-<id-de-cuenta>`
- Lambdas - `adopcion-mascotas-dev-api-cliente`

---

## Estado actual

**Backend completo y probado contra AWS real.** Los 8 stacks cubren todo el ciclo de vida: 
- Cognito con tres grupos (`CLIENTE`/`GUARDERIA`/`ADMIN`),
- Seis Lambdas de API separadas por rol IAM, 
- Catálogo público que se regenera solo (DynamoDB Streams > Lambda > JSON en S3), 
- Notificaciones por SQS+SES con enlaces de decisión de un solo uso
- Fotos procesadas con Pillow.

**Frontend: estático sin conectar.** `frontend/index.html` es un
único HTML con JS vanilla, con datos de ejemplo hardcodeados.

**Pendiente:**
- CloudFront + WAF + dominio propio - serviría en público el catálogo y las
  fotos (hoy en buckets privados); añade coste fijo, se monta solo si se pide
  explícitamente
- CI/CD (CodePipeline + CodeBuild) - el despliegue hoy es manual con los
  scripts de arriba; `buildspecs/` ya está reservado para esto
