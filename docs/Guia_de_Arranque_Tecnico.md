# Guía de Arranque Técnico

Punto de entrada técnico al proyecto: qué es, cómo está organizado y dónde
encontrar el resto de la documentación. Para el detalle de cada decisión de
arquitectura, ver `Plataforma_de_Adopcion_de_Mascotas.md`.

---

## Qué es

Plataforma que conecta protectoras de animales con personas interesadas en
adoptar. Backend serverless en AWS, construido como proyecto final de máster:
la arquitectura es lo que se evalúa.

| Capa | Tecnología |
|---|---|
| IaC | CloudFormation en YAML (sin CDK, sin SAM) |
| Backend | Python 3.12, Lambdas + API Gateway REST API |
| Frontend | HTML + CSS + JS estático, sin framework |
| Datos | DynamoDB On-Demand, dos tablas |
| Auth | Cognito User Pool con tres grupos |
| CI/CD | CodePipeline + CodeBuild (pendiente) |

**Región:** `eu-west-1`. Solo el certificado ACM y el Web ACL de WAF (pendientes)
irían en `us-east-1`, porque CloudFront lo exige.

---

## Cómo está construido

Ocho stacks de CloudFormation sueltos, conectados por `Fn::ImportValue` en vez
de nested stacks - cada uno se pudo desplegar y validar por separado sin
montar antes toda la tubería de empaquetado:

```
budgets.yaml          presupuesto mensual y alerta
dynamodb.yaml         las dos tablas (catalogo, solicitudes)
artefactos.yaml       bucket de artefactos (zips de las Lambdas)
auth.yaml             Cognito: User Pool, tres grupos, tres App Clients
notificaciones.yaml   cola SQS + DLQ, Lambda consumidora, SES
fotos.yaml            buckets de fotos originales/derivadas, Lambda de thumbnails
api.yaml              API Gateway + las seis Lambdas de la API
catalogo.yaml         DynamoDB Streams > Lambda regeneradora > JSON en S3
```

El resultado: Cognito real (sin cabeceras simuladas), seis Lambdas separadas
por rol IAM, un catálogo público que se regenera solo con cada cambio, avisos
por correo con enlaces de decisión de un solo uso, y fotos procesadas de
verdad con Pillow. Todo probado contra AWS real, no solo contra DynamoDB
Local.

---

## Estructura del repositorio

```
infra/templates/        las 8 plantillas de arriba
infra/scripts/          validación, empaquetado y despliegue
backend/api/             6 Lambdas, un rol IAM por función
backend/event_lambdas/   post_confirmation, regenerador_catalogo,
                         consumidora_sqs, thumbnails
frontend/                sitio estático (HTML/CSS/JS)
```

---

## Dónde seguir leyendo

| Para qué | Dónde |
|---|---|
| Desplegar el backend en una cuenta AWS | `Despliegue_Backend.md` |
| Consumir la API desde el frontend | `Backend_Endpoints.md` + `postman_collection.json` |

---

## Estado

Backend completo. Pendiente: CORS en la API, CloudFront + WAF + dominio propio,
y CI/CD - el despliegue hoy es manual. El entorno `dev` no queda encendido
