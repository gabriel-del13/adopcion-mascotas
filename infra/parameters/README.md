# Parámetros por entorno

`dev.json` y `prod.json` son los ficheros de parámetros de **`main.yaml`**, el
stack raíz. No sirven para desplegar plantillas sueltas: `aws cloudformation
deploy` falla si el fichero contiene un parámetro que la plantilla no declara.

Regla, entonces:

- **Stacks anidados dentro de `main.yaml`** → sus valores salen de estos
  ficheros, que `main.yaml` reparte a cada hijo.
- **Stacks que se despliegan sueltos** (`budgets.yaml` mientras `main.yaml` aún
  no existe, y `edge-us-east-1.yaml`, que vive en otra región) → los parámetros
  van inline en el comando, con `Clave=Valor`.

El fichero crece a medida que se añaden plantillas: cada parámetro nuevo que
declare `main.yaml` se añade aquí en la misma fase.

## Formato

Formato estándar de parámetros de CloudFormation (lista de
`ParameterKey`/`ParameterValue`). Consumirlo con `file://` en
`--parameter-overrides` requiere **AWS CLI v2**; la v1 solo acepta pares
`Clave=Valor` en la línea de comandos.

```bash
aws cloudformation deploy \
  --stack-name adopcion-mascotas-dev \
  --template-file infra/templates/main.yaml \
  --parameter-overrides file://infra/parameters/dev.json \
  --capabilities CAPABILITY_NAMED_IAM
```

## Valores pendientes

| Parámetro | Entorno | Cuándo se rellena |
|---|---|---|
| `EmailAlertas` | dev y prod | Fase 2, antes de desplegar `budgets.yaml` |
| `DominioRaiz` | prod | Fase 9, al comprar el dominio en Route 53 |
| `CertificadoArn` | prod | Fase 9, salida del stack `edge-us-east-1` |
| `WebAclArn` | prod | Fase 9, salida del stack `edge-us-east-1` |

En `dev` los tres últimos se quedan vacíos a propósito: no hay dominio propio,
ni certificado, ni WAF. `cdn-dns.yaml` los trata con `Conditions`.
