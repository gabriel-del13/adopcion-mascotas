# adopcion-mascotas

Plataforma que conecta protectoras y guarderías de animales con personas
interesadas en adoptar. Arquitectura serverless en AWS, infraestructura como
código con CloudFormation.

**Región principal:** `eu-west-1` (Irlanda).
**Excepción obligatoria:** el certificado de ACM y el Web ACL de WAF asociados a
CloudFront viven en `us-east-1`, en un stack satélite aparte.

---

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/Plataforma_de_Adopcion_de_Mascotas.md`](docs/Plataforma_de_Adopcion_de_Mascotas.md) | Contexto de arquitectura: qué se construye, con qué servicios y por qué |
| [`docs/Guia_de_Arranque_Tecnico.md`](docs/Guia_de_Arranque_Tecnico.md) | Cómo se organiza el repo, cómo se estructura CloudFormation y en qué orden se despliega |

---

## Estructura

```
infra/          plantillas de CloudFormation, parámetros por entorno y scripts
backend/api/    FastAPI + Mangum — 5 funciones Lambda, 5 roles IAM
backend/event_lambdas/  funciones disparadas por evento (SQS, Streams, Cognito, correo)
backend/thumbnails/     Lambda con Pillow, empaquetada como imagen de contenedor
frontend/       React + Vite
buildspecs/     definiciones de build para CodeBuild
docs/           documentación de arquitectura
```

---

## Entornos

- **`prod`** — permanente, con dominio propio, certificado y WAF.
- **`dev`** — bajo demanda. Sin dominio propio (usa el de CloudFront), sin WAF y
  sin certificado. Se levanta con un despliegue y se tira con un borrado de
  stack.

Un único juego de plantillas para los dos, parametrizado por `Entorno`.

---

## Despliegue rápido

Requisitos: AWS CLI **v2** configurada con el perfil `adopcion-mascotas` y
región `eu-west-1`.

```bash
# Levantar dev
./infra/scripts/deploy-all.sh dev

# Tirar dev
aws cloudformation delete-stack --stack-name adopcion-mascotas-dev
```

Los buckets, la tabla de DynamoDB y el User Pool llevan `DeletionPolicy: Retain`
y sobreviven al borrado del stack: hay que limpiarlos a mano si se quiere
empezar de cero.

---

## Convención de nombres

`adopcion-mascotas-{entorno}-{recurso}`

- Stacks — `adopcion-mascotas-dev-database`
- Buckets — `adopcion-mascotas-dev-fotos-derivadas`
- Parámetros SSM — `/adopcion-mascotas/{entorno}/{servicio}/{clave}`
- Lambdas — `adopcion-mascotas-dev-api-publica`

---

## Estado

Proyecto en construcción. Progreso de la infraestructura:

- [ ] Fase 0 — Bootstrap de la cuenta y bucket de artefactos
- [x] Fase 1 — Repositorio y estructura
- [ ] Fase 2 — `budgets.yaml`
- [ ] Fase 3 — `database.yaml`, `storage.yaml`, `auth.yaml`, `ecr.yaml`
- [ ] Fase 4 — `compute-api.yaml`
- [ ] Fase 5 — `async.yaml`
- [ ] Fase 6 — `cdn-dns.yaml`
- [ ] Fase 7 — `main.yaml` y scripts de despliegue
- [ ] Fase 8 — `observability.yaml`
- [ ] Fase 9 — Dominio, SES y stack de borde en `us-east-1`
- [ ] Fase 10 — `cicd.yaml`
