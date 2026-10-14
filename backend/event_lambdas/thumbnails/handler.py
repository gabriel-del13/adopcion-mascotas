"""Lambda de thumbnails, disparada por el evento `s3:ObjectCreated` del bucket
de fotos originales.

Standalone: no importa nada de backend/api/app, igual que el resto de
event_lambdas — este va aparte porque necesita Pillow, que no está en el zip
de la API.

La clave del objeto es `animales/<guarderiaId>/<animalId>/<fotoId>` (server
decide la clave al emitir la presignada, ver
app/handlers/guarderia.py:_subir_foto). Incluir guarderiaId en la ruta es lo que
permite resolver la clave real de DynamoDB (`PK=GUARDERIA#<sub>`) con un
`UpdateItem` exacto, sin necesitar Scan ni Query.
"""
import io
import os
from urllib.parse import unquote_plus

import boto3
from PIL import Image, ImageOps

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

BUCKET_DERIVADAS = os.environ["BUCKET_FOTOS_DERIVADAS"]
TABLA_CATALOGO = os.environ["TABLA_CATALOGO"]

TAMANO_MINIATURA = (400, 400)
TAMANO_FICHA = (1200, 1200)


def procesar_imagen(datos: bytes) -> tuple[bytes, bytes] | None:
    """Verifica que `datos` sea una imagen real y genera dos derivadas WebP:
    una miniatura cuadrada de 400px y una ficha de hasta 1200px de lado mayor.
    Devuelve None si `datos` no es una imagen válida (el Content-Type
    declarado en la presignada se puede mentir, así que se verifica de
    verdad abriendo el fichero, no confiando en la extensión ni el header).

    Pillow no incluye los metadatos EXIF del original al guardar salvo que se
    pasen explícitamente con `exif=`, así que las derivadas salen limpias sin
    hacer nada especial para ello.
    """
    try:
        comprobacion = Image.open(io.BytesIO(datos))
        comprobacion.verify()
    except Exception:
        return None

    # Pillow exige reabrir el fichero tras verify(): deja la imagen en un
    # estado no utilizable para procesarla.
    imagen = Image.open(io.BytesIO(datos))
    if imagen.mode not in ("RGB", "RGBA"):
        imagen = imagen.convert("RGB")

    # ImageOps.fit recorta al cuadrado exacto (centrado) en vez de solo
    # limitar el lado mayor, para que el listado tenga todas las miniaturas
    # con el mismo tamaño (sección 2, "Fotos": "400 px cuadrado").
    miniatura = ImageOps.fit(imagen, TAMANO_MINIATURA)
    buffer_miniatura = io.BytesIO()
    miniatura.save(buffer_miniatura, format="WEBP")

    ficha = imagen.copy()
    ficha.thumbnail(TAMANO_FICHA)
    buffer_ficha = io.BytesIO()
    ficha.save(buffer_ficha, format="WEBP")

    return buffer_miniatura.getvalue(), buffer_ficha.getvalue()


def lambda_handler(event, context):
    for registro in event["Records"]:
        bucket_origen = registro["s3"]["bucket"]["name"]
        key = unquote_plus(registro["s3"]["object"]["key"])

        partes = key.split("/")
        if len(partes) != 4 or partes[0] != "animales":
            # El filtro de prefijo del bucket ya limita esto a "animales/",
            # pero sin esta comprobación una clave con forma inesperada
            # rompería el desempaquetado de abajo en vez de saltarse el
            # registro con un mensaje claro.
            print(f"Clave con forma inesperada, se ignora: {key}")
            continue
        _, guarderia_id, animal_id, foto_id = partes

        datos = s3.get_object(Bucket=bucket_origen, Key=key)["Body"].read()
        resultado = procesar_imagen(datos)

        if resultado is None:
            print(f"No es una imagen válida, se borra: {key}")
            s3.delete_object(Bucket=bucket_origen, Key=key)
            continue

        miniatura, ficha = resultado
        clave_base = f"animales/{guarderia_id}/{animal_id}/{foto_id}"
        s3.put_object(Bucket=BUCKET_DERIVADAS, Key=f"{clave_base}-400.webp", Body=miniatura, ContentType="image/webp")
        s3.put_object(Bucket=BUCKET_DERIVADAS, Key=f"{clave_base}-1200.webp", Body=ficha, ContentType="image/webp")

        dynamodb.Table(TABLA_CATALOGO).update_item(
            Key={"PK": f"GUARDERIA#{guarderia_id}", "SK": f"ANIMAL#{animal_id}"},
            UpdateExpression="SET fotos = list_append(if_not_exists(fotos, :vacia), :nueva)",
            ExpressionAttributeValues={":vacia": [], ":nueva": [foto_id]},
        )