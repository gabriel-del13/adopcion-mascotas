"""Lambda regeneradora del catálogo público, disparada por DynamoDB Streams
sobre la tabla `catalogo`.

Vuelca el catálogo entero (guarderías aprobadas + animales disponibles) a un
JSON en S3 con un hash en el nombre, y solo entonces actualiza el manifiesto
que apunta al fichero vigente - nunca al revés, para que no exista un
manifiesto apuntando a un catálogo que aún no está subido.

No lee el detalle del evento del stream: cualquier cambio en la tabla
regenera el catálogo completo. A esta escala (cientos de animales) es más
simple que aplicar el diff del evento, y el resultado es idéntico.
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr, Key

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

TABLA_CATALOGO = os.environ["TABLA_CATALOGO"]
BUCKET_CATALOGO = os.environ["BUCKET_CATALOGO"]

CLAVES_INTERNAS = {"PK", "SK", "GSI1PK", "GSI1SK", "GSI2PK", "GSI2SK"}


def _limpiar(item: dict) -> dict:
    return {clave: valor for clave, valor in item.items() if clave not in CLAVES_INTERNAS}


def _json_default(valor):
    if isinstance(valor, Decimal):
        return int(valor) if valor % 1 == 0 else float(valor)
    raise TypeError(f"No se sabe serializar {type(valor)}")


def lambda_handler(event, context):
    tabla = dynamodb.Table(TABLA_CATALOGO)

    animales = tabla.query(
        IndexName="GSI-Catalogo",
        KeyConditionExpression=Key("GSI1PK").eq("ESTADO#disponible"),
    )["Items"]

    # Mismo Scan que repositorio_catalogo.listar_guarderias_aprobadas: no hay
    # GSI para "guarderías por estado aprobada" porque solo lo necesita esta
    # Lambda, que corre en segundo plano, no en el camino de petición pública.
    guarderias = tabla.scan(
        FilterExpression=Attr("SK").eq("METADATA") & Attr("estado").eq("aprobada")
    )["Items"]

    generado_en = datetime.now(timezone.utc).isoformat()
    catalogo = {
        "generadoEn": generado_en,
        "animales": [_limpiar(a) for a in animales],
        "guarderias": [_limpiar(g) for g in guarderias],
    }

    cuerpo = json.dumps(catalogo, default=_json_default, ensure_ascii=False).encode("utf-8")
    hash_contenido = hashlib.sha256(cuerpo).hexdigest()[:12]
    clave_catalogo = f"data/catalogo-{hash_contenido}.json"

    # Primero el catálogo, luego el manifiesto: un manifiesto publicado nunca
    # puede apuntar a un fichero que todavía no existe.
    s3.put_object(
        Bucket=BUCKET_CATALOGO,
        Key=clave_catalogo,
        Body=cuerpo,
        ContentType="application/json",
        CacheControl="public, max-age=31536000, immutable",
    )
    s3.put_object(
        Bucket=BUCKET_CATALOGO,
        Key="data/manifest.json",
        Body=json.dumps({"catalogo": clave_catalogo, "generadoEn": generado_en}).encode("utf-8"),
        ContentType="application/json",
        CacheControl="public, max-age=60",
    )

    return {"catalogo": clave_catalogo, "animales": len(animales), "guarderias": len(guarderias)}
